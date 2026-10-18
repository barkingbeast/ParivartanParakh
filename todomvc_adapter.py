"""Pin and adapt an upstream persistence example; no upstream logic is rewritten."""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT/'vendor'/'todomvc'
COMMIT='d69828232d2ab3881d33d41d3a4df4ed7947c7d7'
UPSTREAM=REPO/'examples'/'vanilla-es6'


def prepare():
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    if actual != COMMIT:
        raise RuntimeError(f'Expected TodoMVC {COMMIT}, found {actual}. See TODOMVC_INTEGRATION.md.')
    manifest={'features':[
        {'id':'saved-tasks','module':'bundle.js','seed':[
            {'type':'fill','selector':'.new-todo','value':'Prepare hackathon demo'},
            {'type':'press','selector':'.new-todo','key':'Enter'},
            {'type':'fill','selector':'.new-todo','value':'Submit project'},
            {'type':'press','selector':'.new-todo','key':'Enter'},
            {'type':'check','selector':'.todo-list li:nth-child(1) .toggle'},
        ],'observe':'.todo-list li','observe_attributes':['class'],'observe_normalize_whitespace':True},
        {'id':'focus-view','module':'focus-view.js','trigger':['#preview-focus','#save-focus']},
    ]}
    panel='''<aside class="survival-lab" style="margin-top:50px;padding:18px;background:#fff;border:1px solid #ddd;font:13px/1.6 system-ui">
<strong>ParivartanParakh · controlled modification</strong><p>This focus-view extension is ours. It is not an upstream TodoMVC feature or a discovered upstream bug.</p>
<button id="preview-focus">Preview focus color</button> <button id="save-focus">Save focus view</button><p id="focus-status">Saved task titles and completion must survive.</p></aside>
<style>.focus-enabled .todo-list li.completed{opacity:.45}.survival-lab button{padding:8px;border:1px solid #ccc;border-radius:5px}</style>
<script src="focus-view.js"></script>'''
    old='''// ParivartanParakh extension; not upstream TodoMVC code.
document.querySelector('#preview-focus').onclick = () => {
  document.querySelector('.survival-lab').style.background = '#edf5ee';
};
document.querySelector('#save-focus').onclick = () => {
  document.body.classList.add('focus-enabled');
  localStorage.setItem('state-survival:focus-preference', 'enabled');
  document.querySelector('#focus-status').textContent = 'Focus view saved';
};
'''
    # Deliberately introduced bug: saving a filtered view replaces the source
    # collection, silently deleting completed tasks from persistent storage.
    broken=old.replace("  document.body.classList.add('focus-enabled');", "  const tasks = JSON.parse(localStorage.getItem('todos-vanilla-es6') || '[]');\n  localStorage.setItem('todos-vanilla-es6', JSON.stringify(tasks.filter(task => !task.completed)));\n  document.body.classList.add('focus-enabled');")
    fixed=old.replace("  document.body.classList.add('focus-enabled');", "  const tasks = JSON.parse(localStorage.getItem('todos-vanilla-es6') || '[]');\n  localStorage.setItem('todos-vanilla-es6', JSON.stringify(tasks.map(task => ({...task, focusVisible: !task.completed}))));\n  document.body.classList.add('focus-enabled');")
    # Track content identity even though the built bundle is served at the root
    # for the prototype's explicit flat-module attribution contract.
    provenance={'repository':'https://github.com/tastejs/todomvc','commit':COMMIT,'tag':'1.3.1',
        'example':'examples/vanilla-es6','bundle_sha256':hashlib.sha256((UPSTREAM/'dist'/'bundle.js').read_bytes()).hexdigest(),
        'disclosure':'Upstream application bundle is unchanged. Asset paths and lab UI are adapted. The focus extension and its faulty/fixed revisions are authored locally; this is a controlled injected regression, not an upstream defect discovery.'}
    for name,new in [('todomvc_focus_broken',broken),('todomvc_focus_fixed',fixed)]:
        folder=ROOT/'examples'/name
        for version,focus in [('old',old),('new',new)]:
            dest=folder/version
            dest.mkdir(parents=True,exist_ok=True)
            shutil.copy2(UPSTREAM/'dist'/'bundle.js',dest/'bundle.js')
            for package,file in [('todomvc-app-css','index.css'),('todomvc-common','base.css')]:
                target=dest/'node_modules'/package
                target.mkdir(parents=True,exist_ok=True)
                shutil.copy2(UPSTREAM/'node_modules'/package/file,target/file)
            html=(UPSTREAM/'index.html').read_text(encoding='utf-8')
            html=html.replace('src="dist/bundle.js"','src="bundle.js"')
            html=html.replace('<script src="node_modules/todomvc-common/base.js"></script>','')
            html=html.replace('</body>',panel+'\n</body>')
            (dest/'index.html').write_text(html,encoding='utf-8')
            (dest/'focus-view.js').write_text(focus,encoding='utf-8')
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        (folder/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
        shutil.copy2(REPO/'license.md',folder/'TODOMVC_LICENSE.md')
    return provenance


if __name__=='__main__':
    print(json.dumps(prepare(),indent=2))
