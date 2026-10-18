"""Bounded static-app investigator. Graph queries, not fixture names, select checks."""
from __future__ import annotations

import hashlib
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from falkordb import FalkorDB
import os
from playwright.sync_api import Error as BrowserError, sync_playwright

from run_gate import INSTRUMENT, QUERY, check_graph_integrity, populate, save
from bounded_agent import AgentFailure, investigate as agent_investigate

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / 'prototype_runs'
RETAINED_QUERY = 'MATCH (c:RegressionCase)-[:REQUIRES_REPLAY]->(f:Feature) RETURN DISTINCT f.id ORDER BY f.id'


def load_manifest(folder):
    folder = Path(folder).resolve(strict=True)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('approval',{}).get('status')=='approved':
        content={key:value for key,value in manifest.items() if key!='approval'}
        actual=hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if manifest['approval'].get('manifest_digest')!=actual:
            raise ValueError('Approved declaration changed or predates integrity stamps. Record and approve it again.')
    features = manifest.get('features')
    if not isinstance(features, list) or not 1 <= len(features) <= 12:
        raise ValueError('Declare 1–12 features in manifest.json.')
    ids, modules = set(), set()
    for feature in features:
        for key in ['id', 'module']:
            if not isinstance(feature.get(key), str) or not feature[key]:
                raise ValueError(f'Each feature needs a nonempty {key}.')
        module = feature['module']
        if Path(module).name != module or not module.endswith('.js'):
            raise ValueError('Only flat .js module names are supported.')
        if feature['id'] in ids or module in modules:
            raise ValueError('Feature ids and module mappings must be unique.')
        ids.add(feature['id'])
        modules.add(module)
        for kind in ['seed', 'trigger']:
            if kind in feature:
                actions = feature[kind] if isinstance(feature[kind], list) else [feature[kind]]
                if not actions or len(actions) > 12:
                    raise ValueError(f'{kind} must contain 1–12 actions.')
                for action in actions:
                    validate_action(action)
        if 'seed' in feature and not isinstance(feature.get('observe'), str):
            raise ValueError('Every seeded feature needs an observation selector.')
        attributes=feature.get('observe_attributes',[])
        if not isinstance(attributes,list) or any(a not in ['class','aria-checked','aria-selected','data-state'] for a in attributes):
            raise ValueError('Observation attributes must use the documented attribute allowlist.')
    if not any('seed' in f for f in features):
        raise ValueError('At least one old feature must declare seed and observe.')
    for version in ['old', 'new']:
        if not (folder / version / 'index.html').is_file():
            raise ValueError(f'Missing {version}/index.html.')
    if any(not any((folder / v / m).is_file() for v in ['old', 'new']) for m in modules):
        raise ValueError('A declared module does not exist in either revision.')
    return folder, manifest


def actions(feature, key):
    value = feature.get(key, [])
    return value if isinstance(value, list) else [value]


def validate_action(action):
    if isinstance(action,str) and action:
        return
    if not isinstance(action,dict) or not isinstance(action.get('selector'),str) or not action['selector']:
        raise ValueError('Each action needs a CSS selector.')
    kind=action.get('type','click')
    if kind not in ['click','fill','press','check','uncheck']:
        raise ValueError('Supported actions: click, fill, press, check, uncheck.')
    if set(action)-{'selector','type','value','key'}:
        raise ValueError('Unexpected action fields.')
    if kind=='fill' and (not isinstance(action.get('value'),str) or len(action['value'])>2000):
        raise ValueError('Fill actions need a value of at most 2000 characters.')
    if kind=='press' and action.get('key') not in ['Enter','Escape','Tab']:
        raise ValueError('Press supports Enter, Escape and Tab.')


def normalize_action(action):
    return {'selector':action} if isinstance(action,str) else dict(action)


def perform(page, action):
    action=normalize_action(action)
    locator=page.locator(action['selector'])
    kind=action.get('type','click')
    if kind=='fill': locator.fill(action['value'])
    elif kind=='press': locator.press(action['key'])
    elif kind=='check': locator.check()
    elif kind=='uncheck': locator.uncheck()
    else: locator.click()


def describe(action):
    action=normalize_action(action)
    kind=action.get('type','click')
    extra=' '+json.dumps(action['value']) if kind=='fill' else ' '+action['key'] if kind=='press' else ''
    return f'{kind.capitalize()} {action["selector"]}{extra}'


def observe(page, feature):
    nodes=page.locator(feature['observe'])
    values=nodes.evaluate_all('(nodes)=>nodes.map(node=>String(node.value ?? ""))') if feature.get('observe_value') else nodes.all_text_contents()
    if feature.get('observe_normalize_whitespace',False):
        values=[' '.join(value.split()) for value in values]
    for attribute in feature.get('observe_attributes',[]):
        attributes=nodes.evaluate_all('(nodes, attr) => nodes.map(node => node.getAttribute(attr) || "")',attribute)
        values=[text+f' [{attribute}={value}]' for text,value in zip(values,attributes)]
    if feature.get('observe_checked'):
        checked=nodes.evaluate_all('''nodes=>nodes.map(node=>[...(node.matches('input[type="checkbox"]')?[node]:[]),...node.querySelectorAll('input[type="checkbox"]')].map(input=>String(input.checked)).join(','))''')
        values=[text+f' [checked={state}]' for text,state in zip(values,checked)]
    return values


def run_investigation(folder, run_id, notify=lambda _: None, ablate=False, agent_mode=False, frozen_case=None):
    folder, manifest = load_manifest(folder)
    provenance_file=folder/'PROVENANCE.json'
    provenance=json.loads(provenance_file.read_text(encoding='utf-8')) if provenance_file.is_file() else None
    output = RUNS / run_id
    output.mkdir(parents=True, exist_ok=False)
    graph_name = 'state_survival_' + run_id.replace('-', '_')
    notify('Connecting to FalkorDB')
    graph = FalkorDB(host=os.environ.get('FALKORDB_HOST','::1'), port=int(os.environ.get('FALKORDB_PORT','6379')), socket_timeout=10).select_graph(graph_name)
    graph.query('RETURN 1')

    class AppHandler(SimpleHTTPRequestHandler):
        active = folder / 'old'

        def translate_path(self, path):
            relative = unquote(urlparse(path).path).lstrip('/') or 'index.html'
            candidate = (self.active / relative).resolve()
            if not candidate.is_relative_to(self.active.resolve()) or not candidate.is_file():
                return str(ROOT / '__missing__')
            return str(candidate)

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), AppHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    url = origin + '/'
    files = sorted({p.name for v in ['old', 'new'] for p in (folder/v).glob('*.js')})
    hashes = {name: {v: hashlib.sha256((folder/v/name).read_bytes()).hexdigest() if (folder/v/name).exists() else None for v in ['old','new']} for name in files}
    changed = [name for name in files if hashes[name]['old'] != hashes[name]['new']]
    seeds = [f for f in manifest['features'] if 'seed' in f]
    triggers = [dict(normalize_action(a),feature=f['id']) for f in manifest['features'] if f['module'] in changed for a in actions(f, 'trigger')]
    if frozen_case:
        triggers=frozen_case['_actions']
    issues, trace = [], []
    checks = []
    agent_log=[]
    graph_stages=[]

    def capture_graph_stage(label):
        rows=graph.query('MATCH (a)-[r]->(b) RETURN a.id, type(r), b.id ORDER BY a.id, type(r), b.id').result_set
        previous={tuple(row) for row in graph_stages[-1]['edges']} if graph_stages else set()
        graph_stages.append({'label':label,'graph':graph_name,'edges':rows,
                             'added_edges':[list(row) for row in sorted({tuple(row) for row in rows}-previous)],
                             'source':'Actual FalkorDB query at this investigation stage'})

    def capture(page, phase):
        events = page.evaluate('window.__storageTrace.splice(0)')
        trace.extend(dict(t, phase=phase) for t in events)

    def context_for(browser, state=None):
        context = browser.new_context(**({'storage_state':state} if state else {}))
        context.set_default_timeout(4000)
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') else route.abort())
        context.add_init_script(INSTRUMENT)
        return context

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            notify('Seeding old build and capturing saved behavior')
            frozen_state={'cookies':[],'origins':[{'origin':origin,'localStorage':[{'name':k,'value':v} for k,v in frozen_case['storage_before'].items()]}]} if frozen_case else None
            context = context_for(browser,frozen_state)
            page = context.new_page()
            baseline_errors = []
            page.on('pageerror', lambda e: baseline_errors.append(str(e)))
            page.goto(url)
            if not frozen_case:
                for f in seeds:
                    for action in actions(f, 'seed'):
                        perform(page,action)
            capture(page, 'old_seed')
            page.reload()
            before = {f['id']:observe(page,f) for f in seeds}
            if baseline_errors:
                issues.append('Old build produced JavaScript errors: ' + '; '.join(baseline_errors))
            for feature, values in before.items():
                if not values:
                    issues.append(f'Old baseline for {feature} is empty; preservation cannot be established.')
            for feature in seeds:
                expected=feature.get('expected_baseline')
                if expected is not None and before[feature['id']]!=expected:
                    issues.append(f'Old baseline for {feature["id"]} does not match the approved recorded expectation.')
            if frozen_case and before!=frozen_case['baseline_observations']:
                issues.append('Retained old observations could not be reproduced from the frozen data.')
            page.screenshot(path=str(output/'baseline.png'), full_page=True)
            state = context.storage_state()
            storage_before = page.evaluate('({...localStorage})')
            if frozen_case and storage_before!=frozen_case['storage_before']:
                issues.append('Old build changed the frozen baseline storage before repair verification.')
            save(output/'baseline-storage.json',storage_before)
            capture(page, 'old_reload')
            context.close()
            populate(graph,manifest,trace,changed)
            capture_graph_stage('Old workflow observed')

            AppHandler.active = folder / 'new'
            notify('Exercising changed features and recording native storage calls')
            context = context_for(browser, state)
            page = context.new_page()
            page.goto(url)
            for action in triggers:
                perform(page,action)
            capture(page, 'new_discovery')
            context.close()
            unknown = populate(graph, manifest, trace, changed)
            capture_graph_stage('Changed feature exercised')
            if frozen_case:
                case_id=json.dumps(frozen_case['_base_run'])
                feature_id=json.dumps(frozen_case['_feature_id'])
                graph.query(f'MATCH (f:Feature {{id:{feature_id}}}) MERGE (c:RegressionCase {{id:{case_id}}}) MERGE (c)-[:REQUIRES_REPLAY]->(f)')
                capture_graph_stage('Retained failure requires replay')
            if unknown:
                issues.append(f'{len(unknown)} storage operations are unattributed or unsupported.')
            notify('Querying FalkorDB to select affected old features')
            paths_before = graph.query(QUERY).result_set
            if ablate:
                graph.query('MATCH (:Module)-[r:READS]->(:StorageKey) DELETE r')
                capture_graph_stage('Read edges removed for negative control')
            integrity = check_graph_integrity(graph, trace, manifest)
            if integrity['missing'] or integrity['unexpected']:
                issues.append('Stored graph dependencies disagree with recorded browser operations.')
            paths = graph.query(QUERY).result_set
            retained_targets=[row[0] for row in graph.query(RETAINED_QUERY).result_set] if frozen_case else []
            if frozen_case and retained_targets!=[frozen_case['_feature_id']]:
                issues.append('The retained regression obligation is missing from the graph.')
            selected = sorted({row[3] for row in paths}|set(retained_targets))
            seed_map = {f['id']: f for f in seeds}
            for feature_id in selected:
                if feature_id not in seed_map:
                    issues.append(f'Affected feature {feature_id} has no declared preservation check.')

            def replay(feature, sequence, artifact=False):
                ctx = context_for(browser, state)
                pg = ctx.new_page()
                errors = []
                pg.on('pageerror', lambda e: errors.append(str(e)))
                try:
                    pg.goto(url)
                    initial = observe(pg,feature)
                    for action in sequence:
                        perform(pg,action)
                    storage_after = pg.evaluate('({...localStorage})')
                    pg.reload()
                    after = observe(pg,feature)
                    if artifact:
                        pg.screenshot(path=str(output/f'after-{len(checks)}.png'), full_page=True)
                    return {'before': before[feature['id']], 'new_before_trigger': initial, 'after_reload':after,
                            'errors':errors, 'storage_after':storage_after,
                            'verdict':'FAIL' if errors or after != before[feature['id']] else 'PASS'}
                finally:
                    ctx.close()

            def check_selected(feature_id):
                if feature_id not in seed_map:
                    raise AgentFailure(f'No declared preservation check for {feature_id}.')
                feature = seed_map[feature_id]
                notify(f'Replaying old-data survival check: {feature_id}')
                check = replay(feature, triggers, artifact=True)
                minimal, attempts = list(triggers), 0
                if check['verdict'] == 'FAIL':
                    # Repeated deletion reduction: no remaining click can be removed
                    # without losing this outcome. Not a global shortest-path claim.
                    index = 0
                    while index < len(minimal):
                        candidate = minimal[:index] + minimal[index+1:]
                        attempts += 1
                        try:
                            trial = replay(feature, candidate)
                        except BrowserError:
                            # A deletion can remove a prerequisite click. An
                            # infeasible replay cannot replace the proven case.
                            index += 1
                            continue
                        same_failure = trial['after_reload'] == check['after_reload'] and trial['errors'] == check['errors']
                        if trial['verdict'] == 'FAIL' and same_failure:
                            minimal = candidate
                            index = 0
                        else:
                            index += 1
                check.update(feature=feature_id, screenshot=f'after-{len(checks)}.png',
                             original_actions=triggers, minimal_actions=minimal, reduction_replays=attempts,
                             steps=['Open old build', *(['Restore the retained failure localStorage snapshot'] if frozen_case else [describe(a) for f in seeds for a in actions(f,'seed')]),
                                    'Reload and preserve browser data', 'Open new build with that data',
                                    *[describe(a) for a in minimal], 'Reload',
                                    f'Compare {feature["observe"]} against the old baseline'])
                checks.append(check)
                return {'feature':feature_id,'verdict':check['verdict'],'before_items':len(check['before']),
                        'after_items':len(check['after_reload']),'minimal_actions':[describe(a) for a in minimal]}

            def query_dependencies():
                nonlocal paths,selected,retained_targets
                current_integrity=check_graph_integrity(graph,trace,manifest)
                if current_integrity['missing'] or current_integrity['unexpected']:
                    raise AgentFailure('Graph evidence changed or is incomplete.')
                paths=graph.query(QUERY).result_set
                retained_targets=[row[0] for row in graph.query(RETAINED_QUERY).result_set] if frozen_case else []
                if frozen_case and retained_targets!=[frozen_case['_feature_id']]:
                    raise AgentFailure('Retained replay obligation disappeared from FalkorDB.')
                selected=sorted({row[3] for row in paths}|set(retained_targets))
                return {'query':QUERY,'paths':paths,'retained_query':RETAINED_QUERY if frozen_case else None,'retained_targets':retained_targets}

            if agent_mode:
                if issues:
                    agent_log.append({'skipped':'Evidence integrity or baseline issues prevent agent execution.'})
                else:
                    try:
                        agent_investigate(changed,query_dependencies,check_selected,notify,agent_log)
                    except AgentFailure as error:
                        issues.append(str(error))
            else:
                for feature_id in selected:
                    if feature_id in seed_map:
                        check_selected(feature_id)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    verdict = 'INCOMPLETE' if issues else 'FAIL' if any(c['verdict']=='FAIL' for c in checks) else 'PASS' if checks else 'NO_DEPENDENCY_SELECTED'
    result = {'id':run_id,'folder':str(folder),'graph':graph_name,'verdict':verdict,'issues':issues,
              'provenance':provenance,
              'changed_modules':changed,'source_hashes':hashes,'selected_checks':selected,'query':QUERY,
              'paths':paths,'paths_before_ablation':paths_before,'graph_integrity':integrity,
              'traces':trace,'storage_before':storage_before,'checks':checks,'graph_stages':graph_stages,
              'manifest':manifest,'baseline_observations':before,'retained_targets':retained_targets,
              'agent':{'requested':agent_mode,'steps':agent_log,'verdict_authority':'Deterministic browser assertions; the model cannot issue a passing verdict.'},
              'scope':'Exercised native localStorage calls and declared preservation checks only.'}
    if frozen_case:
        target_check=next((c for c in checks if c['feature']==frozen_case['_feature_id']),None)
        verified=verdict=='PASS' and target_check is not None and target_check['verdict']=='PASS'
        result['repair']={'base_run':frozen_case['_base_run'],'feature':frozen_case['_feature_id'],
                          'status':'VERIFIED_FOR_RETAINED_CASE' if verified else 'NOT_FIXED' if verdict=='FAIL' else 'INCOMPLETE',
                          'baseline_reused':storage_before==frozen_case['storage_before'],
                          'manifest_reused':manifest==frozen_case['manifest'],'actions_reused':triggers==frozen_case['_actions'],
                          'retained_query':RETAINED_QUERY}
    save(output/'evidence.json', result)
    save(output/'agent.json',result['agent'])
    lines = ['# ParivartanParakh investigation', '', f'Verdict: **{verdict}**', '', f'Run: `{run_id}`', f'FalkorDB graph: `{graph_name}`', '',
             '## Why these checks', '', '```cypher', QUERY, '```', '', '| Changed writer | Storage key | Reader | Feature |', '|---|---|---|---|']
    lines += ['| ' + ' | '.join(str(cell).replace('|','\\|') for cell in row) + ' |' for row in paths]
    if provenance:
        lines += ['', '## Provenance and disclosure', '', json.dumps(provenance,indent=2)]
    if frozen_case:
        lines += ['', '## Retained-case repair verification', '', json.dumps(result['repair'],indent=2), '',
                  'The original localStorage data, observation rule and reduced sequence were retained. Current graph impact paths are supplemented by a RegressionCase → REQUIRES_REPLAY → Feature obligation. This verifies the retained case, not the whole application.']
    for c in checks:
        lines += ['', f'## {c["feature"]}: {c["verdict"]}', '', f'Before: `{json.dumps(c["before"])}`', f'After reload: `{json.dumps(c["after_reload"])}`', '', 'Reproduction:', '']
        lines += [f'{i}. {s}' for i,s in enumerate(c['steps'],1)]
        lines += ['', f'Reduction: {len(c["original_actions"])} → {len(c["minimal_actions"])} changed-feature clicks, {c["reduction_replays"]} extra browser replays.']
    if agent_mode:
        lines += ['', '## Local model tool loop', '', 'The model selected validated tools and graph targets. Browser assertions determined the verdict.', '']
        lines += ['- '+json.dumps(event,ensure_ascii=False) for event in agent_log]
    lines += ['', '## Incomplete evidence', '', *(['- '+i for i in issues] or ['None detected relative to collected traces.']), '',
              '## Rerun', '', 'From the project folder:', '', '```powershell', f'python investigate.py --folder "{folder}"'+(' --agent' if agent_mode else ''), '```', '',
              '## Boundaries', '', result['scope'], 'Feature mappings, seed actions, trigger actions and preservation expectations are declared. Local agent mode is optional; no automatic repair is used. An unselected check is not proof of safety. Controlled injected regressions are not upstream defect discoveries.']
    (output/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    notify('Evidence saved')
    return result
