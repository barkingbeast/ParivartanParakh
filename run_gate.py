"""Executable, local-only feasibility experiment. No model or API key needed."""
from __future__ import annotations
import hashlib
import json
import random
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from falkordb import FalkorDB
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs'
FIXTURES = ROOT / 'fixtures'
GRAPH = 'state_survival_feasibility'

INSTRUMENT = r"""(() => {
  window.__storageTrace = [];
  for (const op of ['getItem','setItem','removeItem','clear']) {
    const original = Storage.prototype[op];
    Storage.prototype[op] = function(...args) {
      const stack = new Error().stack || '';
      const matches = [...stack.matchAll(/https?:\/\/[^\s)]+\/([\w-]+\.js):\d+:\d+/g)];
      const module = matches.length ? matches[0][1] : null;
      const result = original.apply(this,args);
      if (this === window.localStorage) window.__storageTrace.push({
        op, key: args.length ? String(args[0]) : null,
        value: op === 'getItem' ? result : (args.length > 1 ? String(args[1]) : null), module
      });
      return result;
    };
  }
})();"""

QUERY = """MATCH (w:Module)-[:WRITES]->(k:StorageKey)<-[:READS]-(r:Module)-[:IMPLEMENTS]->(f:Feature)
WHERE w.changed = true AND w.id <> r.id
RETURN DISTINCT w.id, k.id, r.id, f.id ORDER BY f.id"""


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def build_fixture(name, mode, seed):
    rng = random.Random(seed)
    key = 'persist_' + ''.join(rng.choices('abcdefghjkmnpqrstuvwxyz23456789', k=12))
    other = key + '_memo'
    folder = FIXTURES / name
    manifest = {
        'features': [
            {'id': 'tasks', 'module': 'tasks.js', 'seed': '#seed-tasks', 'observe': '#tasks li'},
            {'id': 'notes', 'module': 'notes.js', 'trigger': '#save-note'},
        ]
    }
    html = '''<!doctype html><meta charset="utf-8"><title>Storage survival fixture</title>
<style>body{font:18px system-ui;max-width:800px;margin:60px auto}section{padding:20px;border:1px solid #ccc;margin:15px}button{padding:10px}</style>
<h1>Tasks and notes</h1><section><h2>Tasks</h2><button id="seed-tasks">Create tasks</button><ul id="tasks"></ul></section>
<section><h2>Notes</h2><button id="save-note">Save note</button><p id="note"></p></section>
<script src="/tasks.js"></script><script src="/notes.js"></script>'''
    tasks = '''const taskKey = KEY;
function renderTasks() {
  const raw = JSON.parse(localStorage.getItem(taskKey) || '{"tasks":[]}');
  document.querySelector('#tasks').replaceChildren(...(raw.tasks || []).map(t => {
    const li = document.createElement('li'); li.textContent = t; return li;
  }));
}
document.querySelector('#seed-tasks').onclick = () => {
  localStorage.setItem(taskKey, JSON.stringify({tasks:['Submit assignment','Buy groceries']}));
  renderTasks();
};
renderTasks();'''.replace('KEY', json.dumps(key))
    old_notes = '''document.querySelector('#save-note').onclick = () => {
  localStorage.setItem(KEY, JSON.stringify({note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};'''.replace('KEY', json.dumps(other))
    if mode == 'overwrite':
        new_notes = old_notes.replace(json.dumps(other), json.dumps(key))
    elif mode == 'merge':
        new_notes = '''document.querySelector('#save-note').onclick = () => {
  const saved = JSON.parse(localStorage.getItem(KEY) || '{}');
  localStorage.setItem(KEY, JSON.stringify({...saved, note:'Meeting at five'}));
  document.querySelector('#note').textContent = 'Meeting at five';
};'''.replace('KEY', json.dumps(key))
    elif mode == 'remove':
        new_notes = old_notes.replace('localStorage.setItem('+json.dumps(other)+', JSON.stringify({note:\'Meeting at five\'}));', 'localStorage.removeItem('+json.dumps(key)+');')
    elif mode == 'unrelated':
        new_notes = old_notes.replace('Meeting at five', 'Meeting at six')
    elif mode == 'unchanged':
        new_notes = old_notes
    else:
        raise ValueError(mode)
    for version, notes in [('old', old_notes), ('new', new_notes)]:
        target = folder / version
        target.mkdir(parents=True, exist_ok=True)
        for file, content in [('index.html', html), ('tasks.js', tasks), ('notes.js', notes)]:
            (target / file).write_text(content, encoding='utf-8')
    save(folder / 'manifest.json', manifest)
    return folder


class Handler(SimpleHTTPRequestHandler):
    active = None

    def translate_path(self, path):
        requested = urlparse(path).path.strip('/') or 'index.html'
        if requested not in {'index.html', 'tasks.js', 'notes.js'}:
            return str(ROOT / '__missing__')
        return str(self.active / requested)

    def log_message(self, *_):
        pass


def observe(page, feature):
    return page.locator(feature['observe']).all_text_contents()


def cypher_string(value):
    return json.dumps(value)


def populate(graph, manifest, traces, changed):
    graph.query('MATCH (n) DETACH DELETE n')
    for feature in manifest['features']:
        m, f = cypher_string(feature['module']), cypher_string(feature['id'])
        graph.query(f'MERGE (m:Module {{id:{m}}}) SET m.changed = {str(feature["module"] in changed).lower()} MERGE (f:Feature {{id:{f}}}) MERGE (m)-[:IMPLEMENTS]->(f)')
    unknown = []
    known = {f['module'] for f in manifest['features']}
    for trace in traces:
        if trace['module'] not in known or trace['key'] is None:
            unknown.append(trace)
            continue
        rel = 'READS' if trace['op'] == 'getItem' else 'WRITES'
        m, k = cypher_string(trace['module']), cypher_string(trace['key'])
        graph.query(f'MATCH (m:Module {{id:{m}}}) MERGE (k:StorageKey {{id:{k}}}) MERGE (m)-[:{rel}]->(k)')
    return unknown


def check_graph_integrity(graph, traces, manifest):
    """Validate persisted evidence, not a fallback for deciding affected checks."""
    known = {f['module'] for f in manifest['features']}
    expected = {(t['module'], 'READS' if t['op'] == 'getItem' else 'WRITES', t['key'])
                for t in traces if t['module'] in known and t['key'] is not None}
    actual = {tuple(row) for row in graph.query(
        'MATCH (m:Module)-[r]->(k:StorageKey) RETURN m.id, type(r), k.id').result_set}
    return {'missing': sorted(expected - actual), 'unexpected': sorted(actual - expected)}


def run_case(browser, graph, url, folder, ablate=False):
    manifest = json.loads((folder / 'manifest.json').read_text())
    old, new = folder / 'old', folder / 'new'
    changed = [p.name for p in new.glob('*.js') if p.read_bytes() != (old / p.name).read_bytes()]
    hashes = {p.name: {'old': hashlib.sha256((old/p.name).read_bytes()).hexdigest(), 'new': hashlib.sha256(p.read_bytes()).hexdigest()} for p in new.glob('*.js')}
    seeds = [f for f in manifest['features'] if 'seed' in f]
    triggers = [f for f in manifest['features'] if f['module'] in changed and 'trigger' in f]
    Handler.active = old
    context = browser.new_context()
    context.add_init_script(INSTRUMENT)
    page = context.new_page()
    page.goto(url)
    for feature in seeds:
        page.locator(feature['seed']).click()
    page.reload()
    before = {f['id']: observe(page, f) for f in seeds}
    state = context.storage_state()
    traces = page.evaluate('window.__storageTrace')
    context.close()
    Handler.active = new
    context = browser.new_context(storage_state=state)
    context.add_init_script(INSTRUMENT)
    page = context.new_page()
    page.goto(url)
    for feature in triggers:
        page.locator(feature['trigger']).click()
    traces += page.evaluate('window.__storageTrace')
    context.close()
    unknown = populate(graph, manifest, traces, changed)
    pre_ablation = graph.query(QUERY).result_set
    if ablate:
        graph.query('MATCH (:Module)-[r:READS]->(:StorageKey) DELETE r')
    integrity = check_graph_integrity(graph, traces, manifest)
    paths = graph.query(QUERY).result_set
    selected = sorted({row[3] for row in paths})
    checks = []
    for feature in seeds:
        if feature['id'] not in selected:
            continue
        context = browser.new_context(storage_state=state)
        context.add_init_script(INSTRUMENT)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(url)
        initial = observe(page, feature)
        for trigger in triggers:
            page.locator(trigger['trigger']).click()
        storage_after = page.evaluate('({...localStorage})')
        page.reload()
        after = observe(page, feature)
        verdict = 'FAIL' if errors or after != before[feature['id']] else 'PASS'
        artifact = OUT / folder.name
        artifact.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifact / 'after.png'), full_page=True)
        checks.append({'feature':feature['id'], 'verdict':verdict, 'before':before[feature['id']], 'new_before_trigger':initial, 'after_reload':after, 'errors':errors, 'storage_after':storage_after,
                       'steps':['Open old app', *[f"Click {f['seed']}" for f in seeds], 'Reload and capture saved state', 'Open new app with that state', *[f"Click {f['trigger']}" for f in triggers], 'Reload', f"Compare {feature['observe']} with old app"]})
        context.close()
    if integrity['missing'] or integrity['unexpected'] or unknown:
        verdict = 'INCOMPLETE'
    elif any(c['verdict'] == 'FAIL' for c in checks):
        verdict = 'FAIL'
    elif checks:
        verdict = 'PASS'
    else:
        verdict = 'NO_DEPENDENCY_SELECTED'
    result = {'case':folder.name,'verdict':verdict,'changed_modules':changed,'source_hashes':hashes,'traces':traces,'unattributed':unknown,'graph_integrity':integrity,'query':QUERY,'paths_before_ablation':pre_ablation,'paths':paths,'selected_checks':selected,'checks':checks,'ablation':ablate}
    save(OUT / folder.name / 'evidence.json', result)
    return result


def main():
    OUT.mkdir(exist_ok=True)
    graph = FalkorDB(host=os.environ.get('FALKORDB_HOST','::1'), port=int(os.environ.get('FALKORDB_PORT','6379')), socket_timeout=10).select_graph(GRAPH)
    # Validate the server; never silently use an in-memory fallback.
    graph.query('RETURN 1')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
    specifications = [('overwrite_alpha','overwrite',137,False),('overwrite_beta','overwrite',991,False),('safe_shared_merge','merge',813,False),('safe_separate_key','unrelated',455,False),('unchanged_control','unchanged',118,False),('delete_old_data','remove',712,False),('graph_ablation','overwrite',137,True)]
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, mode, seed, ablate in specifications:
                result = run_case(browser, graph, url, build_fixture(name, mode, seed), ablate)
                results.append(result)
                print(f'{name:24} {result["verdict"]:24} selected={result["selected_checks"]}', flush=True)
            # Leave useful intact dependency evidence available in the graph viewer.
            final = results[0]
            manifest = json.loads((FIXTURES / final['case'] / 'manifest.json').read_text())
            populate(graph, manifest, final['traces'], final['changed_modules'])
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    expected = ['FAIL','FAIL','PASS','NO_DEPENDENCY_SELECTED','NO_DEPENDENCY_SELECTED','FAIL','INCOMPLETE']
    success = [r['verdict'] for r in results] == expected
    save(OUT / 'summary.json', {'gate_passed':success,'expected':expected,'cases':results})
    lines = ['# ParivartanParakh — executed gate report', '', f'Gate passed: **{success}**', '', '| Case | Actual verdict | Selected checks |', '|---|---|---|']
    lines += [f'| {r["case"]} | {r["verdict"]} | {", ".join(r["selected_checks"]) or "None"} |' for r in results]
    lines += ['', '## What this establishes', '', '- Native browser storage operations produced dependency evidence; randomized keys were not supplied to the detector.', '- Cypher paths selected the older feature check. Sharing a key safely passed the behavioral check.', '- Two distinct overwrite fixtures and a deletion fixture reproduced task loss after reload.', '- Removing READS edges removed the selected check and produced INCOMPLETE, not a passing result. A provenance-to-graph integrity check independently detected the missing edges; the verdict does not depend on the ablation flag.', '', '## Limits', '', '- Constructed fixtures, two features, declared selectors/actions/observations. No real repository benchmark or independent hidden-test evaluation.', '- Fixture generator and detector are separate functions in one file, not a security boundary. The expected verdict list is only used after executions to score the gate.', '- Runtime paths only; unexercised code, property-style storage access, IndexedDB, asynchronous workflows and dynamic imports are not covered.', '- NO_DEPENDENCY_SELECTED means no check was selected from observed dependencies; it is not proof that an app is safe.', '- No LLM agent or autonomous requirement/action discovery is built. This establishes the deterministic investigation tools an agent could use.', '- Integrity checks detect missing graph edges relative to collected traces, not dependencies missing from the traces themselves.', '- Graph is restored to the first failing case after the run. Individual evidence files retain every case query result.', '', '## Inspect the graph', '', 'Select `state_survival_feasibility` in the FalkorDB browser and run:', '', '```cypher', 'MATCH (a)-[r]->(b) RETURN a,r,b', '```', '', '## Next decision', '', 'Proceed to a bounded prototype if this workflow is useful: add an independent app example, trace coverage accounting and an agent that selects from declared actions. Do not claim broad prevention of AI regressions.']
    (ROOT / 'GATE_REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'\nGate passed: {success}. Evidence: {OUT}')
    if not success:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
