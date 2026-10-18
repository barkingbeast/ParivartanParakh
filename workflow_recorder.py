"""Local, explicit-approval recorder. Does not infer arbitrary product intent."""
from __future__ import annotations
import hashlib
import copy
import json
import shutil
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler,SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlparse
from uuid import uuid4

from prototype_engine import ROOT,load_manifest,validate_action
from run_gate import INSTRUMENT

WORKFLOWS=ROOT/'recorded_workflows'
SESSIONS={}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def source_files(folder):
    files={}
    for version in ['old','new']:
        for p in (folder/version).rglob('*'):
            if p.is_symlink(): raise ValueError('Recording source must not contain symbolic links.')
            if not p.is_file(): continue
            if p.is_symlink() or not p.resolve().is_relative_to((folder/version).resolve()):
                raise ValueError('Recording source must not contain links outside its revision.')
            files[f'{version}/{p.relative_to(folder/version).as_posix()}']=p
    if len(files)>1000 or sum(p.stat().st_size for p in files.values())>30_000_000:
        raise ValueError('Recording supports static revisions up to 1000 files / 30 MB.')
    return files


def fingerprints(folder):
    return {name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in source_files(folder).items()}


def start(folder,dashboard):
    folder=Path(folder).resolve(strict=True)
    if any(not (folder/v/'index.html').is_file() for v in ['old','new']):
        raise ValueError('Recording needs old/index.html and new/index.html; a manifest is not required.')
    identity=uuid4().hex[:16]
    session={'id':identity,'folder':str(folder),'dashboard':dashboard,'phase':'seed','actions':{'seed':[],'trigger':[]},
             'traces':{'seed':[],'trigger':[]},'candidate':None,'draft':None,'issues':[],'lock':threading.RLock(),
             'source_hashes':fingerprints(folder),'approved':None,'created_at':time.time()}

    class Preview(SimpleHTTPRequestHandler):
        def log_message(self,*_): pass

        def translate_path(self,path):
            revision='old' if session['phase']=='seed' else 'new'
            base=(folder/revision).resolve()
            relative=unquote(urlparse(path).path).lstrip('/') or 'index.html'
            candidate=(base/relative).resolve()
            return str(candidate) if candidate.is_relative_to(base) else str(ROOT/'__missing__')

        def end_headers(self):
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'")
            super().end_headers()

        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/__record.js':
                config={'id':identity,'phase':session['phase'],'dashboard':dashboard}
                body=(ROOT/'prototype_ui'/'recorder.js').read_text(encoding='utf-8').replace('__RECORDER_CONFIG__',json.dumps(config)).encode()
                self.send_response(200);self.send_header('Content-Type','application/javascript');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                return
            if path in ['/','/index.html']:
                file=Path(self.translate_path('/index.html'))
                html=file.read_text(encoding='utf-8')
                injection='<script>'+INSTRUMENT+'</script><script src="/__record.js"></script>'
                if '<head>' in html: html=html.replace('<head>','<head>'+injection,1)
                else: html=injection+html
                body=html.encode()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                return
            super().do_GET()

        def do_POST(self):
            try:
                if urlparse(self.path).path!='/__record/events': raise ValueError('Unknown recording endpoint')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=200000: raise ValueError('Recording event is too large')
                value=json.loads(self.rfile.read(length))
                ingest(session,value)
                self.send_response(204);self.end_headers()
            except (ValueError,KeyError,TypeError):
                self.send_response(400);self.end_headers()

    server=ThreadingHTTPServer(('127.0.0.1',0),Preview)
    session['server']=server
    session['origin']=f'http://127.0.0.1:{server.server_port}'
    SESSIONS[identity]=session
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return public(session)


def ingest(session,value):
    with session['lock']:
        if session['phase'] not in ['seed','trigger']: return
        phase=value.get('phase')
        if phase not in ['seed','trigger']: raise ValueError('Unknown phase')
        kind=value.get('kind')
        if kind=='action':
            action=value['action'];validate_action(action)
            bucket=session['actions'][phase]
            if action.get('type')=='fill' and bucket and bucket[-1].get('type')=='fill' and bucket[-1]['selector']==action['selector']:
                bucket[-1]=action
            else:
                if len(bucket)>=12: raise ValueError('At most 12 actions per phase are supported')
                bucket.append(action)
            if phase=='seed': session['candidate']=None
            session['draft']=None
        elif kind=='trace':
            events=value.get('events',[])
            if not isinstance(events,list) or len(events)>1000: raise ValueError('Too many storage events')
            for event in events:
                if event.get('op') not in ['getItem','setItem','removeItem','clear']: raise ValueError('Unknown operation')
            if len(session['traces'][phase])+len(events)>5000: raise ValueError('Recording trace limit reached')
            session['traces'][phase].extend(events)
        elif kind=='pick':
            candidate=value['candidate']
            if phase!='seed' or not candidate.get('values') or not isinstance(candidate.get('selector'),str):
                raise ValueError('Select a nonempty old-build observation')
            if not all(isinstance(v,str) for v in candidate['values']): raise ValueError('Invalid observation')
            session['candidate']=candidate
            session['recorded_storage']=value.get('storage',{})
        elif kind=='unsupported':
            session['issues'].append(str(value.get('message','Unsupported action')))


def public(session):
    with session['lock']:
        return copy.deepcopy({'id':session['id'],'origin':session['origin'],'phase':session['phase'],'folder':session['folder'],
                'actions':session['actions'],'candidate':session['candidate'],'issues':session['issues'],
                'draft':session['draft'],'approved':session['approved']})


def advance(identity):
    session=SESSIONS[identity]
    with session['lock']:
        if session['phase']!='seed' or not session['candidate'] or not session['actions']['seed']:
            raise ValueError('Record old data and select the behavior to protect first.')
        session['phase']='trigger'
    return public(session)


def suggest(identity):
    session=SESSIONS[identity]
    with session['lock']:
        if session['phase']!='trigger' or not session['actions']['trigger']:
            raise ValueError('Record the changed-feature actions first.')
        if session['issues']: raise ValueError('Unsupported recorded actions must be resolved before approval.')
        reader_counts=Counter(t.get('module') for t in session['traces']['seed'] if t.get('op')=='getItem')
        writer_counts=Counter(t.get('module') for t in session['traces']['trigger'] if t.get('op') in ['setItem','removeItem'])
        folder=Path(session['folder'])
        valid=lambda m:isinstance(m,str) and Path(m).name==m and any((folder/v/m).is_file() for v in ['old','new'])
        readers=[m for m,_ in reader_counts.most_common() if valid(m)]
        writers=[m for m,_ in writer_counts.most_common() if valid(m)]
        if not readers or not writers: raise ValueError('No attributed storage reader/writer found in the recording.')
        pairs=[(r,w) for r in readers for w in writers if r!=w]
        if not pairs: raise ValueError('This prototype needs distinct reader and writer modules; this recording uses the same module.')
        candidate=session['candidate']
        draft={'id':identity,'rule':f'Preserve the selected {len(candidate["values"])} observed rows/fields, including captured checkbox states, after the changed workflow and reload.',
               'candidate':candidate,'seed_actions':session['actions']['seed'],'trigger_actions':session['actions']['trigger'],
               'reader_candidates':readers,'writer_candidates':writers,'reader':pairs[0][0],'writer':pairs[0][1],
               'source_hashes':session['source_hashes'],'association':'Module candidates come from observed storage calls, not inferred feature ownership.'}
        draft['digest']=digest(draft)
        session['draft']=draft
        session['phase']='review'
    return public(session)


def approve(identity,data):
    session=SESSIONS[identity]
    with session['lock']:
        draft=session['draft']
        if session['phase']!='review' or not draft: raise ValueError('Generate a suggestion first.')
        if data.get('approved') is not True: raise ValueError('Explicit approval is required.')
        if data.get('draft_digest')!=draft['digest']: raise ValueError('Suggestion is stale; review the latest draft.')
        if fingerprints(Path(session['folder']))!=draft['source_hashes']: raise ValueError('Source revisions changed after recording; record again.')
        reader=data.get('reader',draft['reader']);writer=data.get('writer',draft['writer'])
        if reader not in draft['reader_candidates'] or writer not in draft['writer_candidates'] or reader==writer:
            raise ValueError('Confirm distinct modules from the observed candidate lists.')
        candidate=draft['candidate']
        approval={'status':'approved','draft_digest':draft['digest'],'confirmed_at':time.time(),
                  'source':'automated-test' if data.get('test_approval') is True else 'explicit-local-confirmation'}
        manifest={'workflow_name':str(data.get('name') or 'Recorded workflow')[:100],'approval':approval,
                  'features':[{'id':'protected-behavior','module':reader,'seed':draft['seed_actions'],
                               'observe':candidate['selector'],'observe_normalize_whitespace':True,
                               'observe_checked':candidate['checked'],'observe_value':candidate['value'],
                               'expected_baseline':candidate['values'],'description':draft['rule']},
                              {'id':'changed-workflow','module':writer,'trigger':draft['trigger_actions']}]}
        approval['manifest_digest']=digest({key:value for key,value in manifest.items() if key!='approval'})
        folder=WORKFLOWS/identity
        folder.mkdir(parents=True,exist_ok=False)
        for version in ['old','new']: shutil.copytree(Path(session['folder'])/version,folder/version)
        if fingerprints(folder)!=draft['source_hashes']:
            raise ValueError('Source changed during the snapshot; start a new recording.')
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        provenance=Path(session['folder'])/'PROVENANCE.json'
        if provenance.is_file(): shutil.copy2(provenance,folder/'PROVENANCE.json')
        for name in ['TODOMVC_LICENSE.md','THIRD_PARTY.md','LICENSE','license.md']:
            notice=Path(session['folder'])/name
            if notice.is_file(): shutil.copy2(notice,folder/name)
        snapshot={k:v for k,v in session.items() if k not in ['lock','server','draft']}
        snapshot['approval']=approval
        (folder/'recording.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
        (folder/'approved-rule.json').write_text(json.dumps(draft,indent=2),encoding='utf-8')
        load_manifest(folder)
        session['approved']={'folder':str(folder),'sample':'workflow-'+identity,'name':manifest['workflow_name']}
        session['phase']='approved'
    return public(session)


def approved_samples():
    samples=[]
    for file in WORKFLOWS.glob('*/manifest.json'):
        try:
            manifest=json.loads(file.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            continue
        if manifest.get('approval',{}).get('status')=='approved' and manifest['approval'].get('manifest_digest'):
            samples.append({'id':'workflow-'+file.parent.name,'name':manifest.get('workflow_name','Recorded workflow'),
                            'description':'Approved recorded workflow; generated selectors and observed module associations.','folder':str(file.parent)})
    return samples
