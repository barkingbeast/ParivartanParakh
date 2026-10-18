"""Negative controls for declaration approval and retained-case repair checks."""
import json
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from shutil import copytree
from prototype_engine import ROOT,RUNS
from test_prototype import request


def post_event(session,value):
    data=json.dumps(value).encode()
    req=urllib.request.Request(session['origin']+'/__record/events',data,{'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as response: assert response.status==204


def draft_for(folder=None):
    session=request('/api/recordings',{'folder':str(folder)} if folder else {'sample':'basket-broken'})
    # Synthetic event packets test API validation only. Browser-recorded
    # declarations are tested separately in test_record_approve_repair_ui.py.
    post_event(session,{'phase':'seed','kind':'action','action':{'type':'click','selector':'#seed-tasks'}})
    post_event(session,{'phase':'seed','kind':'trace','events':[{'module':'basket.js','op':'getItem','key':'test'}]})
    # Basket example uses basket.js, unlike the unrelated tasks generator.
    post_event(session,{'phase':'seed','kind':'pick','candidate':{'selector':'#basket li','values':['Synthetic validation row'],'checked':False,'value':False},'storage':{}})
    request('/api/recordings/'+session['id']+'/advance',{})
    post_event(session,{'phase':'trigger','kind':'action','action':{'type':'click','selector':'#save-settings'}})
    post_event(session,{'phase':'trigger','kind':'trace','events':[{'module':'appearance.js','op':'setItem','key':'test'}]})
    return request('/api/recordings/'+session['id']+'/suggest',{})


def repair(base,**values):
    job=request('/api/repairs',{'base_run':base,**values})
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        status=request('/api/runs/'+job['id'])
        if status['status']=='complete':return status['result']
        if status['status']=='error':raise AssertionError(status['error'])
        time.sleep(.15)
    raise AssertionError('Repair verification timed out')


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((ROOT/'RECORD_APPROVE_REPAIR_UI_RECEIPT.json').read_text())
        cls.base=cls.receipt['failure_run']
        cls.failure=json.loads((RUNS/cls.base/'evidence.json').read_text())
        cls.results=[]

    def assert_rejected(self,path,body):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            request(path,body)
        self.assertEqual(raised.exception.code,400)
        raised.exception.close()

    def test_01_ineffective_repair_still_fails(self):
        result=repair(self.base,sample='todo-broken')
        self.results.append({'id':result['id'],'verdict':result['verdict'],'repair':result['repair']})
        self.assertEqual(result['repair']['status'],'NOT_FIXED')
        self.assertEqual(result['storage_before'],self.failure['storage_before'])
        self.assertEqual(result['manifest'],self.failure['manifest'])

    def test_02_removed_dependency_cannot_skip_retained_case(self):
        with tempfile.TemporaryDirectory(prefix='retained-repair-') as temporary:
            revision=Path(temporary)/'restored-old-code'
            copytree(Path(self.failure['folder'])/'old',revision)
            result=repair(self.base,folder=str(revision),agent=True)
        self.results.append({'id':result['id'],'verdict':result['verdict'],'repair':result['repair']})
        self.assertEqual(result['paths'],[])
        self.assertEqual(result['changed_modules'],[])
        self.assertEqual(result['retained_targets'],['protected-behavior'])
        self.assertEqual(len(result['checks']),1)
        self.assertEqual(result['checks'][0]['original_actions'],self.failure['checks'][0]['minimal_actions'])
        self.assertEqual(result['repair']['status'],'VERIFIED_FOR_RETAINED_CASE')
        tools=[event['decision']['tool'] for event in result['agent']['steps']]
        self.assertIn('run_check',tools)

    def test_03_repair_manifest_cannot_weaken_rule(self):
        with tempfile.TemporaryDirectory(prefix='retained-repair-') as temporary:
            revision=Path(temporary)/'weakened-manifest'
            copytree(ROOT/'examples'/'todomvc_focus_broken',revision)
            (revision/'manifest.json').write_text('{"features": []}',encoding='utf-8')
            result=repair(self.base,folder=str(revision))
        self.results.append({'id':result['id'],'verdict':result['verdict'],'repair':result['repair']})
        self.assertEqual(result['repair']['status'],'NOT_FIXED')
        self.assertEqual(result['manifest'],self.failure['manifest'])

    def test_04_stale_approval_rejected(self):
        session=draft_for(ROOT/'examples'/'basket_settings')
        self.assert_rejected('/api/recordings/'+session['id']+'/approve',{'approved':True,'draft_digest':'stale'})
        request('/api/recordings/'+session['id']+'/cancel',{})

    def test_05_approval_requires_explicit_true(self):
        session=draft_for(ROOT/'examples'/'basket_settings')
        self.assert_rejected('/api/recordings/'+session['id']+'/approve',{'draft_digest':session['draft']['digest']})
        request('/api/recordings/'+session['id']+'/cancel',{})

    def test_06_source_change_invalidates_approval(self):
        with tempfile.TemporaryDirectory(prefix='record-source-') as temporary:
            folder=Path(temporary)/'fixture'
            copytree(ROOT/'examples'/'basket_settings',folder)
            session=draft_for(folder)
            with (folder/'old'/'basket.js').open('a',encoding='utf-8') as file:file.write('\n// source changed after recording\n')
            self.assert_rejected('/api/recordings/'+session['id']+'/approve',{'approved':True,'draft_digest':session['draft']['digest']})
            request('/api/recordings/'+session['id']+'/cancel',{})

    def test_07_a_passing_run_is_not_a_failed_case(self):
        self.assert_rejected('/api/repairs',{'base_run':self.receipt['repair_run'],'sample':'todo-fixed'})

    def test_08_changed_approved_declaration_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='approval-drift-') as temporary:
            folder=Path(temporary)/'edited-rule'
            copytree(Path(self.failure['folder']),folder)
            manifest=json.loads((folder/'manifest.json').read_text())
            manifest['features'][0]['expected_baseline']=['Weakened expectation']
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            self.assert_rejected('/api/runs',{'folder':str(folder)})

    @classmethod
    def tearDownClass(cls):
        (ROOT/'RECORD_REPAIR_GUARD_RECEIPTS.json').write_text(json.dumps(cls.results,indent=2),encoding='utf-8')


if __name__=='__main__':unittest.main(verbosity=2)
