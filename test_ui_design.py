"""Interaction and layout checks for the redesigned investigation workbench."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect


def main():
    receipt=json.loads(Path('LIVE_DEMO_RECEIPTS.json').read_text())[0]
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8772/')
        first=page.locator('[data-sample="todo-broken"]')
        first.wait_for()
        page.keyboard.press('Tab')
        expect(page.locator('.skip-link')).to_be_focused()
        first.focus();first.press('ArrowDown')
        expect(page.locator('[data-sample="todo-fixed"]')).to_have_attribute('aria-checked','true')
        page.locator('[data-sample="todo-fixed"]').press('ArrowUp')
        expect(first).to_have_attribute('aria-checked','true')
        expect(page.locator('#samples details')).not_to_have_attribute('open','')
        page.goto('http://127.0.0.1:8772/?run='+receipt['failure'])
        page.get_by_role('heading',name='The old behavior did not survive.',exact=True).wait_for()
        expect(page.locator('.missing-label')).to_have_text('Missing after change')
        expect(page.locator('.state.changed')).to_have_count(1)
        expect(page.locator('.graph-panel')).to_contain_text('Changed feature exercised')
        expect(page.locator('.graph-panel a')).to_have_attribute('href',__import__('re').compile(receipt['graphs']['failure']))
        for image in page.locator('.comparison img').all():
            image.scroll_into_view_if_needed()
            expect(image).to_be_visible()
            assert image.evaluate('(x)=>x.complete&&x.naturalWidth>0')
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path='ui-redesign-desktop.png')
        for width in [1440,1024,768,390]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        page.screenshot(path='ui-redesign-mobile.png')
        page.emulate_media(reduced_motion='reduce')
        assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto'
        page.locator('#library-search').fill(receipt['failure'])
        expect(page.locator('#regression-list article')).to_have_count(1)
        expect(page.locator('#regression-list')).to_contain_text(receipt['failure'])
        assert not errors,errors
        browser.close()
    Path('UI_DESIGN_RESULTS.json').write_text(json.dumps({'keyboard_sample_navigation':True,'skip_link':True,
        'missing_observation_highlight':True,'graph_link':True,'evidence_images_loaded':True,
        'widths_without_overflow':[1440,1024,768,390],'reduced_motion':True,'library_search':True,'page_errors':errors},indent=2))
    print('PASS: keyboard navigation, evidence images, difference highlight, graph link, responsive layout, reduced motion and search.')


if __name__=='__main__':main()
