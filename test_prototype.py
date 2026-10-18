"""Integration checks against the running local prototype dashboard."""
import json
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from shutil import copytree
from unittest.mock import patch
from uuid import uuid4

from prototype_engine import ROOT, run_investigation

BASE='http://127.0.0.1:8772'


def request(path, data=None):
    body=json.dumps(data).encode() if data is not None else None
    req=urllib.request.Request(BASE+path,body,{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as response:
        return json.load(response)


def execute(**body):
    run=request('/api/runs',body)
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        job=request('/api/runs/'+run['id'])
        if job['status']=='complete': return job['result']
        if job['status']=='error': raise AssertionError(job['error'])
        time.sleep(.15)
    raise AssertionError('Investigation did not finish within 45 seconds')


class PrototypeChecks(unittest.TestCase):
    receipts=[]

    def remember(self,result):
        self.receipts.append({'id':result['id'],'verdict':result['verdict'],'folder':result['folder']})
        return result

    def test_01_independent_basket_regression_and_reduction(self):
        r=self.remember(execute(sample='basket-broken'))
        self.assertEqual(r['verdict'],'FAIL')
        self.assertEqual(r['selected_checks'],['shopping-basket'])
        c=r['checks'][0]
        self.assertEqual(c['before'],['Sourdough bread','Oat milk'])
        self.assertEqual(c['new_before_trigger'],c['before'])
        self.assertEqual(c['after_reload'],[])
        self.assertEqual(c['minimal_actions'],[{'feature':'appearance','selector':'#save-settings'}])
        with urllib.request.urlopen(BASE+'/artifacts/'+r['id']+'/report.md') as response:
            self.assertIn(b'# ParivartanParakh investigation',response.read())

    def test_02_compatible_shared_key(self):
        r=self.remember(execute(sample='basket-fixed'))
        self.assertEqual(r['verdict'],'PASS')
        self.assertEqual(r['checks'][0]['before'],r['checks'][0]['after_reload'])
        self.assertTrue(r['paths'])

    def test_03_no_dependency_is_not_a_pass(self):
        r=self.remember(execute(sample='separate'))
        self.assertEqual(r['verdict'],'NO_DEPENDENCY_SELECTED')
        self.assertEqual(r['checks'],[])

    def test_04_graph_ablation_detected_from_provenance(self):
        r=self.remember(execute(sample='basket-broken',ablate=True))
        self.assertEqual(r['verdict'],'INCOMPLETE')
        self.assertTrue(r['paths_before_ablation'])
        self.assertEqual(r['paths'],[])
        self.assertTrue(r['graph_integrity']['missing'])

    def test_05_unsupported_clear_does_not_pass(self):
        with tempfile.TemporaryDirectory(prefix='state-survival-') as temporary:
            folder=Path(temporary)/'app'
            copytree(ROOT/'examples'/'basket_settings',folder)
            file=folder/'new'/'appearance.js'
            source=file.read_text(encoding='utf-8')
            source=source.replace("localStorage.setItem('corner-shop:workspace', JSON.stringify({theme:'blue'}));",'localStorage.clear();')
            file.write_text(source,encoding='utf-8')
            r=self.remember(execute(folder=str(folder)))
            self.assertEqual(r['verdict'],'INCOMPLETE')
            self.assertTrue(any(t['op']=='clear' for t in r['traces']))

    def test_06_empty_baseline_refused(self):
        with tempfile.TemporaryDirectory(prefix='state-survival-') as temporary:
            folder=Path(temporary)/'app'
            copytree(ROOT/'examples'/'basket_settings',folder)
            manifest=json.loads((folder/'manifest.json').read_text())
            manifest['features'][0]['seed']='#change-color'
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            r=self.remember(execute(folder=str(folder)))
            self.assertEqual(r['verdict'],'INCOMPLETE')
            self.assertTrue(any('baseline' in message for message in r['issues']))

    def test_07_missing_manifest_rejected(self):
        with tempfile.TemporaryDirectory(prefix='state-survival-') as temporary:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                request('/api/runs',{'folder':temporary})
            self.assertEqual(raised.exception.code,400)
            raised.exception.close()

    def test_08_database_unavailable_has_no_fallback(self):
        with patch('prototype_engine.FalkorDB',side_effect=ConnectionError('Database intentionally unavailable')):
            with self.assertRaises(ConnectionError):
                run_investigation(ROOT/'examples'/'basket_settings','test-unavailable-'+uuid4().hex[:8])

    def test_09_cross_origin_launch_rejected(self):
        req=urllib.request.Request(BASE+'/api/runs',b'{"sample":"basket-broken"}',{'Content-Type':'application/json','Origin':'https://example.org'})
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(req)
        self.assertEqual(raised.exception.code,403)
        raised.exception.close()

    def test_10_reducer_keeps_prerequisite_actions(self):
        with tempfile.TemporaryDirectory(prefix='state-survival-') as temporary:
            folder=Path(temporary)/'app'
            copytree(ROOT/'examples'/'basket_settings',folder)
            for version in ['old','new']:
                html=folder/version/'index.html'
                html.write_text(html.read_text(encoding='utf-8').replace('id="save-settings"','id="save-settings" disabled'),encoding='utf-8')
                source=folder/version/'appearance.js'
                source.write_text(source.read_text(encoding='utf-8').replace("document.body.style.background = '#e8f0ff';", "document.body.style.background = '#e8f0ff'; document.querySelector('#save-settings').disabled = false;"),encoding='utf-8')
            r=self.remember(execute(folder=str(folder)))
            self.assertEqual(r['verdict'],'FAIL')
            self.assertEqual(len(r['checks'][0]['minimal_actions']),2)

    @classmethod
    def tearDownClass(cls):
        (ROOT/'prototype_test_receipts.json').write_text(json.dumps(cls.receipts,indent=2),encoding='utf-8')


if __name__=='__main__':
    unittest.main(verbosity=2)
