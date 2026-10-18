"""Real recorder UI → explicit test approval → failing run → supplied repair."""
import json
import tempfile
import urllib.error
from pathlib import Path
from shutil import copytree,copy2
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright,expect
from prototype_engine import ROOT
from test_prototype import request


def response_for(path):
    return lambda response:urlparse(response.url).path==path and response.request.method=='POST'


def main(source_folder=None):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1100})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8772/')
        page.locator('[data-sample="todo-broken"]').wait_for()
        page.locator('#agent-mode').uncheck()
        if source_folder:
            page.get_by_text('Use your own static app',exact=True).click()
            page.locator('#folder').fill(str(source_folder))
        with page.expect_response(response_for('/api/recordings')) as started:
            page.locator('#record-start').click()
        session=started.value.json()
        frame=page.frame_locator('#record-frame')
        frame.locator('.new-todo').wait_for()
        for title in ['Keep completed item','Keep active item']:
            frame.locator('.new-todo').fill(title)
            frame.locator('.new-todo').press('Enter')
        frame.locator('.todo-list li:nth-child(1) .toggle').check()
        page.locator('#pick-behavior').click()
        frame.locator('.todo-list li label').first.click()
        expect(page.locator('#record-next')).to_be_enabled(timeout=10000)
        page.locator('#record-next').click()
        frame.locator('#preview-focus').click()
        frame.locator('#save-focus').click()
        page.locator('#record-suggest').click()
        page.locator('#approve-rule').wait_for()
        assert not page.locator('#approve-rule').is_checked()
        assert not page.locator('#save-workflow').is_enabled()
        draft=request('/api/recordings/'+session['id'])['draft']
        assert draft['candidate']['values']==['Keep completed item [checked=true]','Keep active item [checked=false]'],draft
        try:
            request('/api/recordings/'+session['id']+'/approve',{'approved':False,'draft_digest':draft['digest']})
            raise AssertionError('Unapproved draft was accepted')
        except urllib.error.HTTPError as error:
            assert error.code==400
            error.close()
        page.locator('#recording').screenshot(path=str(ROOT/'recording-review-ui.png'))
        page.locator('#workflow-name').fill('Automated UI test · recorded TodoMVC')
        # Label automation explicitly; this tests the approval control and does
        # not claim the human user approved this test recording.
        def mark_test(route):
            body=json.loads(route.request.post_data)
            body['test_approval']=True
            route.continue_(post_data=json.dumps(body))
        page.route('**/api/recordings/'+session['id']+'/approve',mark_test)
        page.locator('#approve-rule').check()
        page.locator('#save-workflow').click()
        page.locator('#run-recorded').wait_for()
        with page.expect_response(response_for('/api/runs')) as launched:
            page.locator('#run-recorded').click()
        failed_id=launched.value.json()['id']
        page.get_by_role('heading',name='The old behavior did not survive.').wait_for(timeout=45000)
        failure=request('/api/runs/'+failed_id)['result']
        assert failure['verdict']=='FAIL',failure
        assert failure['selected_checks']==['protected-behavior']
        page.locator('#repair-sample').select_option('todo-fixed')
        with page.expect_response(response_for('/api/repairs')) as launched:
            page.locator('#verify-repair').click()
        repair_id=launched.value.json()['id']
        page.get_by_role('heading',name='The declared behavior survived.').wait_for(timeout=45000)
        repair=request('/api/runs/'+repair_id)['result']
        assert repair['repair']['status']=='VERIFIED_FOR_RETAINED_CASE',repair
        assert repair['storage_before']==failure['storage_before']
        assert repair['manifest']==failure['manifest']
        assert repair['retained_targets']==['protected-behavior']
        assert not errors,errors
        page.locator('#result').screenshot(path=str(ROOT/'repair-verification-ui.png'))
        page.set_viewport_size({'width':390,'height':844})
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        receipt={'recording':session['id'],'approval_actor':'automated-test','input_had_manifest':(Path(source_folder)/'manifest.json').exists() if source_folder else True,'failure_run':failed_id,'repair_run':repair_id,
                 'recorded_seed_actions':len(draft['seed_actions']),'recorded_trigger_actions':len(draft['trigger_actions']),
                 'expectation':draft['candidate']['values'],'reader':draft['reader'],'writer':draft['writer'],
                 'failure':'FAIL','repair':repair['repair'],'page_errors':errors,'mobile_horizontal_overflow':False}
        (ROOT/'RECORD_APPROVE_REPAIR_UI_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print(json.dumps(receipt,indent=2))
        browser.close()


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='record-no-manifest-') as temporary:
        folder=Path(temporary)/'unconfigured-app'
        original=ROOT/'examples'/'todomvc_focus_broken'
        for version in ['old','new']:copytree(original/version,folder/version)
        for name in ['PROVENANCE.json','TODOMVC_LICENSE.md']:copy2(original/name,folder/name)
        assert not (folder/'manifest.json').exists()
        main(folder)
