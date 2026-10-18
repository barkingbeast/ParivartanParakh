"""External-app integration and real local-model agent verification."""
import hashlib
import io
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from bounded_agent import AgentFailure, choose
from prototype_engine import ROOT,run_investigation
from test_prototype import execute
from todomvc_adapter import UPSTREAM,COMMIT
from verify_todomvc import main as verify_upstream


class TodoMVCChecks(unittest.TestCase):
    receipts=[]

    def remember(self,result):
        self.receipts.append({'id':result['id'],'verdict':result['verdict'],'selected':result['selected_checks'],
                              'agent_tools':[event['decision']['tool'] for event in result['agent']['steps'] if 'decision' in event]})
        return result

    def test_01_uninstrumented_upstream_persists(self):
        verify_upstream()
        evidence=json.loads((ROOT/'TODOMVC_BASELINE.json').read_text())
        self.assertTrue(evidence['passed'])
        self.assertEqual(evidence['completed_restored'],[True,False])

    def test_02_upstream_bundle_unchanged_and_attributed(self):
        original=(UPSTREAM/'dist'/'bundle.js').read_bytes()
        for name in ['todomvc_focus_broken','todomvc_focus_fixed']:
            folder=ROOT/'examples'/name
            for version in ['old','new']:
                self.assertEqual((folder/version/'bundle.js').read_bytes(),original)
            provenance=json.loads((folder/'PROVENANCE.json').read_text())
            self.assertEqual(provenance['commit'],COMMIT)
            self.assertEqual(provenance['bundle_sha256'],hashlib.sha256(original).hexdigest())
            self.assertIn('Permission is hereby granted',(folder/'TODOMVC_LICENSE.md').read_text())

    def test_03_real_agent_reproduces_injected_loss(self):
        r=self.remember(execute(sample='todo-broken',agent=True))
        self.assertEqual(r['verdict'],'FAIL')
        self.assertEqual(r['selected_checks'],['saved-tasks'])
        self.assertEqual(r['paths'][0],['focus-view.js','todos-vanilla-es6','bundle.js','saved-tasks'])
        check=r['checks'][0]
        self.assertEqual(check['before'],['Prepare hackathon demo [class=completed]','Submit project [class=]'])
        self.assertEqual(check['new_before_trigger'],check['before'])
        self.assertEqual(check['after_reload'],['Submit project [class=]'])
        self.assertEqual(check['minimal_actions'],[{'feature':'focus-view','selector':'#save-focus'}])
        tools=[event['decision']['tool'] for event in r['agent']['steps']]
        self.assertLess(tools.index('query_dependencies'),tools.index('run_check'))
        self.assertEqual(tools[-1],'finish')
        self.assertTrue(all(event['model']['provider']=='Ollama' for event in r['agent']['steps']))

    def test_04_real_agent_compatible_revision_passes(self):
        r=self.remember(execute(sample='todo-fixed',agent=True))
        self.assertEqual(r['verdict'],'PASS')
        self.assertEqual(r['checks'][0]['before'],r['checks'][0]['after_reload'])
        self.assertEqual(r['selected_checks'],['saved-tasks'])

    def test_05_agent_cannot_proceed_with_removed_edges(self):
        r=self.remember(execute(sample='todo-broken',agent=True,ablate=True))
        self.assertEqual(r['verdict'],'INCOMPLETE')
        self.assertEqual(r['checks'],[])
        self.assertTrue(r['graph_integrity']['missing'])

    def test_06_fabricated_target_rejected(self):
        raw={'message':{'content':json.dumps({'tool':'run_check','target':'fabricated-feature'})}}
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            with self.assertRaises(AgentFailure):
                choose({},['run_check'],['saved-tasks'])

    def test_07_early_finish_rejected(self):
        raw={'message':{'content':json.dumps({'tool':'finish','target':''})}}
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            with self.assertRaises(AgentFailure):
                choose({},['query_dependencies','refuse'],[])

    def test_08_model_outage_has_no_deterministic_agent_fallback(self):
        with patch('bounded_agent.choose',side_effect=AgentFailure('Model intentionally unavailable')):
            r=self.remember(run_investigation(ROOT/'examples'/'todomvc_focus_broken','test-model-outage-'+uuid4().hex[:8],agent_mode=True))
            self.assertEqual(r['verdict'],'INCOMPLETE')
            self.assertEqual(r['checks'],[])
            self.assertTrue(any('Model intentionally unavailable' in issue for issue in r['issues']))

    @classmethod
    def tearDownClass(cls):
        (ROOT/'TODOMVC_TEST_RECEIPTS.json').write_text(json.dumps(cls.receipts,indent=2),encoding='utf-8')


if __name__=='__main__':unittest.main(verbosity=2)
