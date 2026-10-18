"""Loopback dashboard with serialized investigation jobs and static evidence exports."""
from __future__ import annotations
import json
import mimetypes
import queue
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from prototype_engine import ROOT, RUNS, load_manifest, run_investigation
import workflow_recorder as recorder
from repair_verification import prepare as prepare_repair
from regression_library import catalog, repair_brief

JOBS = {}
LOCK = threading.Lock()
QUEUE = queue.Queue()
SAMPLES = [
    {'id':'todo-broken','name':'TodoMVC · injected regression','description':'Pinned upstream app with our labelled focus-view modification. Completed tasks disappear after reload.','folder':str(ROOT/'examples'/'todomvc_focus_broken')},
    {'id':'todo-fixed','name':'TodoMVC · compatible revision','description':'The same upstream bundle and old data, with a compatible focus-view update.','folder':str(ROOT/'examples'/'todomvc_focus_fixed')},
    {'id':'basket-broken','name':'Basket + appearance','description':'Investigate a new settings feature against a saved shopping basket.','folder':str(ROOT/'examples'/'basket_settings')},
    {'id':'basket-fixed','name':'Basket + compatible update','description':'Check the compatible shared-storage revision.','folder':str(ROOT/'examples'/'basket_settings_fixed')},
    {'id':'tasks-broken','name':'Tasks + notes','description':'Reproduce a task-list regression after saving a note.','folder':str(ROOT/'fixtures'/'overwrite_alpha')},
    {'id':'tasks-fixed','name':'Tasks + compatible update','description':'Check a compatible shared-key update.','folder':str(ROOT/'fixtures'/'safe_shared_merge')},
    {'id':'separate','name':'Separate storage keys','description':'Control: a changed feature has no observed dependent reader.','folder':str(ROOT/'fixtures'/'safe_separate_key')},
]


def update(run_id, **values):
    with LOCK:
        JOBS[run_id].update(values)


def available_samples():
    return SAMPLES+recorder.approved_samples()


def source_folder(data):
    if data.get('sample'):
        sample=next((s for s in available_samples() if s['id']==data['sample']),None)
        if sample is None: raise ValueError('Unknown sample')
        return sample['folder']
    folder=data.get('folder','')
    if not isinstance(folder,str) or not folder: raise ValueError('Choose a sample or enter an app folder')
    return folder


def worker():
    while True:
        run_id, folder, ablate, agent_mode, frozen_case = QUEUE.get()
        update(run_id,status='running',phase='Starting isolated browser')
        try:
            result = run_investigation(folder,run_id,lambda message:update(run_id,phase=message),ablate=ablate,agent_mode=agent_mode,frozen_case=frozen_case)
            update(run_id,status='complete',phase='Complete',result=result)
        except Exception as error:
            message = f'{type(error).__name__}: {error}'
            update(run_id,status='error',phase='Investigation could not complete',error=message)
            directory = RUNS/run_id
            directory.mkdir(parents=True,exist_ok=True)
            (directory/'error.json').write_text(json.dumps({'id':run_id,'error':message}),encoding='utf-8')
        finally:
            QUEUE.task_done()


class Dashboard(BaseHTTPRequestHandler):
    def log_message(self,*_):
        pass

    def respond(self,status,body,kind='application/json; charset=utf-8'):
        raw = body if isinstance(body,bytes) else json.dumps(body).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path=unquote(urlparse(self.path).path)
        if path=='/api/samples':
            return self.respond(200,available_samples())
        if path=='/api/regressions':
            return self.respond(200,catalog(RUNS))
        if path.startswith('/api/repair-brief/'):
            identity=path.split('/')[-1]
            if not valid_id(identity): return self.respond(400,{'error':'Invalid run id'})
            try:
                value=json.loads((RUNS/identity/'evidence.json').read_text(encoding='utf-8'))
                brief=repair_brief(value)
            except FileNotFoundError:
                return self.respond(404,{'error':'Run not found'})
            except ValueError as error:
                return self.respond(400,{'error':str(error)})
            return self.respond(200,brief.encode('utf-8'),'text/markdown; charset=utf-8')
        if path.startswith('/api/recordings/'):
            identity=path.split('/')[-1]
            if identity not in recorder.SESSIONS: return self.respond(404,{'error':'Recording not found'})
            return self.respond(200,recorder.public(recorder.SESSIONS[identity]))
        if path=='/api/runs':
            saved={}
            for file in RUNS.glob('*/evidence.json'):
                try:
                    r=json.loads(file.read_text(encoding='utf-8'))
                    saved[r['id']]={'id':r['id'],'status':'complete','verdict':r['verdict'],'folder':r['folder'],'created_at':file.stat().st_mtime}
                except (ValueError,KeyError):
                    pass
            with LOCK:
                for key,j in JOBS.items():
                    saved[key]={k:v for k,v in j.items() if k!='result'}
                    if 'result' in j: saved[key]['verdict']=j['result']['verdict']
            return self.respond(200,sorted(saved.values(),key=lambda r:r.get('created_at',0),reverse=True))
        if path.startswith('/api/runs/'):
            run_id=path.split('/')[-1]
            if not valid_id(run_id): return self.respond(400,{'error':'Invalid run id'})
            with LOCK:
                job=JOBS.get(run_id)
                if job is not None: return self.respond(200,job)
            file=RUNS/run_id/'evidence.json'
            if file.is_file(): return self.respond(200,{'id':run_id,'status':'complete','result':json.loads(file.read_text(encoding='utf-8'))})
            return self.respond(404,{'error':'Run not found'})
        if path.startswith('/artifacts/'):
            parts=path.strip('/').split('/')
            if len(parts)!=3 or not valid_id(parts[1]): return self.respond(400,{'error':'Invalid artifact path'})
            file=(RUNS/parts[1]/parts[2]).resolve()
            if not file.is_relative_to(RUNS.resolve()) or file.suffix not in {'.json','.md','.png'} or not file.is_file():
                return self.respond(404,{'error':'Artifact not found'})
            kind=mimetypes.guess_type(file.name)[0] or 'text/plain'
            return self.respond(200,file.read_bytes(),kind)
        if path.startswith('/fonts/'):
            name=path.removeprefix('/fonts/')
            if name not in {'plex-400.ttf','plex-600.ttf','jetbrains-400.ttf'}:
                return self.respond(404,{'error':'Font not found'})
            file=ROOT/'prototype_ui'/'fonts'/name
            if not file.is_file(): return self.respond(404,{'error':'Font not found'})
            return self.respond(200,file.read_bytes(),'font/ttf')
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/workflow-ui.js':'workflow-ui.js','/library-ui.js':'library-ui.js','/fonts.css':'fonts.css'}
        if path in files:
            file=ROOT/'prototype_ui'/files[path]
            kind=mimetypes.guess_type(file.name)[0] or 'text/plain'
            return self.respond(200,file.read_bytes(),kind+'; charset=utf-8')
        self.respond(404,{'error':'Not found'})

    def do_POST(self):
        path=urlparse(self.path).path
        if path not in ['/api/runs','/api/recordings','/api/repairs'] and not path.startswith('/api/recordings/'):
            return self.respond(404,{'error':'Not found'})
        origin=self.headers.get('Origin')
        if origin and origin != f'http://{self.headers.get("Host")}':
            return self.respond(403,{'error':'Cross-origin requests are not accepted'})
        if not self.headers.get('Content-Type','').startswith('application/json'):
            return self.respond(415,{'error':'Use application/json'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 16384: raise ValueError('Request must be 1–16384 bytes')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('Expected a JSON object')
            if path=='/api/recordings':
                return self.respond(201,recorder.start(source_folder(data),f'http://{self.headers.get("Host")}'))
            if path.startswith('/api/recordings/'):
                parts=path.strip('/').split('/')
                if len(parts)!=4 or parts[2] not in recorder.SESSIONS: raise ValueError('Recording not found')
                identity,operation=parts[2:]
                if operation=='advance': result=recorder.advance(identity)
                elif operation=='suggest': result=recorder.suggest(identity)
                elif operation=='approve': result=recorder.approve(identity,data)
                elif operation=='cancel':
                    session=recorder.SESSIONS[identity]
                    session['phase']='cancelled';session['server'].shutdown();session['server'].server_close()
                    result=recorder.public(session)
                else: raise ValueError('Unknown recording action')
                return self.respond(200,result)
            folder=source_folder(data)
            frozen_case=None
            run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:8]
            if path=='/api/repairs':
                base_run=data.get('base_run','')
                if not valid_id(base_run): raise ValueError('Invalid failure run id')
                folder,frozen_case=prepare_repair(base_run,folder,run_id,data.get('feature'))
            folder,_=load_manifest(folder)
            ablate=data.get('ablate',False)
            if not isinstance(ablate,bool): raise ValueError('ablate must be boolean')
            agent_mode=data.get('agent',False)
            if not isinstance(agent_mode,bool): raise ValueError('agent must be boolean')
        except (ValueError,OSError,TypeError,KeyError) as error:
            return self.respond(400,{'error':str(error)})
        with LOCK:
            JOBS[run_id]={'id':run_id,'folder':str(folder),'status':'queued','phase':'Waiting for browser worker','created_at':time.time()}
        QUEUE.put((run_id,str(folder),ablate,agent_mode,frozen_case))
        self.respond(202,{'id':run_id})


def valid_id(value):
    return bool(value) and len(value)<80 and all(c.isalnum() or c in '-_' for c in value)


if __name__=='__main__':
    RUNS.mkdir(exist_ok=True)
    threading.Thread(target=worker,daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',8772),Dashboard)
    print('ParivartanParakh: http://127.0.0.1:8772/',flush=True)
    server.serve_forever()
