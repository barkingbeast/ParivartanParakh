"""Live demo rehearsal: real model -> graph tool -> browser -> retained repair."""
import json
from pathlib import Path
from falkordb import FalkorDB
import os
from test_prototype import execute,request
from test_record_repair_guards import repair


def verify(prefix,broken,fixed):
    failure=execute(sample=broken,agent=True)
    assert failure['verdict']=='FAIL',failure.get('issues')
    stages=failure['graph_stages']
    assert len(stages)==2
    assert any(e[1]=='WRITES' and e[0] in failure['changed_modules'] for e in stages[1]['added_edges'])
    tool=next(s for s in failure['agent']['steps'] if s.get('decision',{}).get('tool')=='query_dependencies')
    assert tool['result']['query']==failure['query']
    assert tool['result']['paths']==failure['paths']
    good=repair(failure['id'],sample=fixed,agent=True)
    assert good['repair']['status']=='VERIFIED_FOR_RETAINED_CASE',good.get('issues')
    again=repair(failure['id'],sample=broken,agent=True)
    assert again['repair']['status']=='NOT_FIXED',again.get('issues')
    for candidate in [good,again]:
        assert all(candidate['repair'][k] for k in ['baseline_reused','manifest_reused','actions_reused'])
        graph=FalkorDB(host=os.environ.get('FALKORDB_HOST','::1'),port=int(os.environ.get('FALKORDB_PORT','6379'))).select_graph(candidate['graph'])
        actual=graph.query('MATCH (a)-[r]->(b) RETURN a.id, type(r), b.id ORDER BY a.id, type(r), b.id').result_set
        assert actual==candidate['graph_stages'][-1]['edges']
        assert any(row[1]=='REQUIRES_REPLAY' for row in actual)
    cases=request('/api/regressions')
    original=next(c for c in cases if c['run']==failure['id'])
    assert len(original['repairs'])==2
    assert original['latest_status']=='NOT_FIXED'
    return {'name':prefix,'failure':failure['id'],'repair':good['id'],'reintroduced':again['id'],
            'graphs':{name:run['graph'] for name,run in [('failure',failure),('repair',good),('reintroduced',again)]},
            'outcomes':['FAIL','VERIFIED_FOR_RETAINED_CASE','NOT_FIXED'],
            'agent_query_validated':True,'graph_snapshots_match_database':True,
            'same_data_rule_actions':True}


if __name__=='__main__':
    results=[verify('TodoMVC with disclosed injected focus-view bug','todo-broken','todo-fixed'),
             verify('Independent controlled Corner Shop fixture','basket-broken','basket-fixed')]
    Path('LIVE_DEMO_RECEIPTS.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
