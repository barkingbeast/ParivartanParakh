"""Read-only case catalog and evidence-grounded repair handoff."""
import json
from pathlib import Path


def load_runs(root):
    runs=[]
    for path in Path(root).glob('*/evidence.json'):
        try:
            value=json.loads(path.read_text(encoding='utf-8'))
            if value.get('id')!=path.parent.name: continue
            runs.append(value)
        except (ValueError,OSError,AttributeError):
            continue
    return runs


def catalog(root):
    runs=load_runs(root)
    cases=[]
    for run in runs:
        if run.get('verdict')!='FAIL': continue
        for check in run.get('checks',[]):
            if check.get('verdict')!='FAIL': continue
            feature=check['feature']
            attempts=[]
            for other in runs:
                repair=other.get('repair',{})
                if repair.get('base_run')==run['id'] and repair.get('feature')==feature:
                    attempts.append({'id':other['id'],'status':repair['status'],
                                     'source_hashes':other.get('source_hashes',{}),
                                     'baseline_reused':repair.get('baseline_reused'),
                                     'manifest_reused':repair.get('manifest_reused'),
                                     'actions_reused':repair.get('actions_reused')})
            attempts.sort(key=lambda a:a['id'],reverse=True)
            cases.append({'run':run['id'],'feature':feature,'app':Path(run['folder']).name,
                          'graph':run.get('graph'),'expected':check.get('before',[]),
                          'actual':check.get('after_reload',[]),'actions':check.get('minimal_actions',[]),
                          'source_hashes':run.get('source_hashes',{}),'repairs':attempts,
                          'latest_status':attempts[0]['status'] if attempts else 'AWAITING_REPAIR',
                          'replay_ready':bool(run.get('manifest') and run.get('baseline_observations'))})
    return sorted(cases,key=lambda c:(c['run'],c['feature']),reverse=True)


def repair_brief(run):
    if run.get('verdict')!='FAIL': raise ValueError('A repair brief requires a completed failing investigation.')
    failures=[c for c in run.get('checks',[]) if c.get('verdict')=='FAIL']
    if not failures: raise ValueError('No reproduced failure is available.')
    lines=['# ParivartanParakh repair brief','',f"Run: {run['id']}",f"App folder: {run['folder']}",
           f"FalkorDB graph: {run.get('graph','unavailable')}",'',
           '## Repair task','',
           'Repair the supplied new revision so the original preservation expectations below hold. '
           'Keep the approved declaration unchanged. Supply the repaired build for retained-case verification; '
           'do not claim the repair is verified until that replay completes.','',
           '## Observed dependency paths','', '```json',json.dumps(run.get('paths',[]),indent=2),'```']
    for check in failures:
        lines+=['',f"## Failed behavior: {check['feature']}",'',
                'Expected observation:', '```json',json.dumps(check.get('before',[]),indent=2),'```',
                'Actual observation after reload:', '```json',json.dumps(check.get('after_reload',[]),indent=2),'```',
                'Reproduction:','']
        lines += [f'{i}. {step}' for i,step in enumerate(check.get('steps',[]),1)]
        lines += ['', 'Reduced changed-feature actions:', '```json',
                  json.dumps(check.get('minimal_actions',[]),indent=2),'```',
                  'Browser errors:', '```json',json.dumps(check.get('errors',[]),indent=2),'```']
        declaration=next((f for f in run.get('manifest',{}).get('features',[]) if f.get('id')==check['feature']),None)
        if declaration:
            lines+=['','Original preservation declaration (do not weaken):','```json',json.dumps(declaration,indent=2),'```']
    lines+=['','## Source revisions','', '```json',json.dumps(run.get('source_hashes',{}),indent=2),'```',
            '', '## Evidence and verification','',
            f"Local evidence: prototype_runs/{run['id']}/evidence.json",
            f"Local screenshots and report: prototype_runs/{run['id']}/", 
            'Open the original failing run in ParivartanParakh and use Verify a supplied repair. '
            'The original saved data, declaration and reduced actions must be reused.',
            '', '## Boundaries','',
            run.get('scope','Declared checks and exercised paths only.'),
            'The dependency path identifies risk, not a proven root cause. '
            'Observations and action text may contain private input: review before sharing. '
            'Raw localStorage values are deliberately omitted from this brief.']
    if run.get('provenance'):
        lines+=['','## Sample disclosure','',json.dumps(run['provenance'],indent=2)]
    return '\n'.join(lines)+'\n'
