import json
import tempfile
import unittest
from pathlib import Path
from regression_library import catalog,repair_brief


class LibraryTests(unittest.TestCase):
    def fixture(self):
        return {'id':'failure-1','verdict':'FAIL','folder':'example','graph':'graph-1',
                'manifest':{'features':[]},'baseline_observations':{'tasks':['Keep']},
                'storage_before':{'secret':'DO_NOT_EXPORT_SECRET'},
                'paths':[['new.js','key','old.js','tasks']],
                'source_hashes':{'new.js':{'old':'a','new':'b'}},
                'checks':[{'feature':'tasks','verdict':'FAIL','before':['Keep'],
                           'after_reload':[],'steps':['Click save','Reload'],
                           'minimal_actions':[{'selector':'#save'}]}]}

    def test_brief_uses_evidence_and_omits_raw_storage(self):
        brief=repair_brief(self.fixture())
        for text in ['Keep','#save','new.js','old.js','failure-1','Click save']:
            self.assertIn(text,brief)
        self.assertNotIn('DO_NOT_EXPORT_SECRET',brief)
        self.assertIn('Keep the approved declaration unchanged',brief)

    def test_non_failure_export_rejected(self):
        value=self.fixture();value['verdict']='PASS'
        with self.assertRaises(ValueError): repair_brief(value)

    def test_catalog_links_only_matching_case_and_survives_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            values=[self.fixture(),{'id':'repair-2','verdict':'PASS','repair':{
                'base_run':'failure-1','feature':'tasks','status':'VERIFIED_FOR_RETAINED_CASE',
                'baseline_reused':True,'manifest_reused':True,'actions_reused':True}},
                {'id':'unrelated','repair':{'base_run':'failure-1','feature':'other','status':'NOT_FIXED'}}]
            for value in values:
                folder=root/value['id'];folder.mkdir();(folder/'evidence.json').write_text(json.dumps(value))
            bad=root/'bad';bad.mkdir();(bad/'evidence.json').write_text('{')
            first=catalog(root)
            self.assertEqual(first,catalog(root))
            self.assertEqual(len(first),1)
            self.assertEqual(first[0]['latest_status'],'VERIFIED_FOR_RETAINED_CASE')
            self.assertEqual(len(first[0]['repairs']),1)
            self.assertTrue(first[0]['replay_ready'])

    def test_legacy_failure_flagged_and_latest_attempt_not_global_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);value=self.fixture();value.pop('manifest')
            values=[value]+[{'id':identity,'repair':{'base_run':'failure-1','feature':'tasks','status':status}}
                            for identity,status in [('repair-1','VERIFIED_FOR_RETAINED_CASE'),('repair-2','NOT_FIXED')]]
            for item in values:
                folder=root/item['id'];folder.mkdir();(folder/'evidence.json').write_text(json.dumps(item))
            case=catalog(root)[0]
            self.assertFalse(case['replay_ready'])
            self.assertEqual(case['latest_status'],'NOT_FIXED')


if __name__=='__main__': unittest.main()
