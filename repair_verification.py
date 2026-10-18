"""Prepare a repair replay without accepting a replacement preservation rule."""
import hashlib
import json
import shutil
from pathlib import Path
from prototype_engine import ROOT,RUNS


def validate_tree(folder):
    files=[]
    for path in folder.rglob('*'):
        if path.is_symlink(): raise ValueError('Repair snapshots must not contain symbolic links.')
        if path.is_file(): files.append(path)
    if len(files)>1000 or sum(path.stat().st_size for path in files)>30_000_000:
        raise ValueError('Repair snapshots support at most 1000 files / 30 MB per revision.')


def prepare(base_run,revision,identity,feature=None):
    file=RUNS/base_run/'evidence.json'
    base=json.loads(file.read_text(encoding='utf-8'))
    if base.get('verdict')!='FAIL': raise ValueError('Choose a completed failing investigation.')
    if not base.get('manifest') or not base.get('baseline_observations'):
        raise ValueError('This older run has no frozen declaration. Rerun it once before verifying a repair.')
    failures=[c for c in base['checks'] if c['verdict']=='FAIL']
    if feature is None and len(failures)!=1: raise ValueError('Choose which failed feature to verify.')
    check=next((c for c in failures if feature is None or c['feature']==feature),None)
    if not check: raise ValueError('That feature is not a retained failure.')
    original=Path(base['folder']).resolve(strict=True)
    for name,hashes in base['source_hashes'].items():
        p=original/'old'/name
        actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        if actual!=hashes['old']: raise ValueError('The failed run old source changed. Its old revision must be restored first.')
    revision=Path(revision).resolve(strict=True)
    new=revision/'new' if (revision/'new'/'index.html').is_file() else revision
    if not (new/'index.html').is_file(): raise ValueError('Supply a repair build folder containing index.html, or an old/new fixture folder.')
    validate_tree(original/'old')
    validate_tree(new)
    workspace=ROOT/'repair_workspaces'/identity
    workspace.mkdir(parents=True,exist_ok=False)
    shutil.copytree(original/'old',workspace/'old')
    shutil.copytree(new,workspace/'new')
    (workspace/'manifest.json').write_text(json.dumps(base['manifest'],indent=2),encoding='utf-8')
    provenance=original/'PROVENANCE.json'
    if provenance.is_file(): shutil.copy2(provenance,workspace/'PROVENANCE.json')
    for name in ['TODOMVC_LICENSE.md','THIRD_PARTY.md','LICENSE','license.md']:
        notice=original/name
        if notice.is_file(): shutil.copy2(notice,workspace/name)
    frozen=dict(base,_base_run=base_run,_feature_id=check['feature'],_actions=check['minimal_actions'])
    return str(workspace),frozen
