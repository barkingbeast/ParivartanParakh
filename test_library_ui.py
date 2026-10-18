"""Exercise the real catalog and repair-brief download against saved failures."""
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    base='http://127.0.0.1:8772'
    cases=json.load(urllib.request.urlopen(base+'/api/regressions'))
    assert cases,'Run a failing investigation before the library UI check.'
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base)
        first=page.locator('#regression-list article').first
        first.wait_for()
        identity=first.locator('[data-case]').get_attribute('data-case')
        first.locator('[data-case]').click()
        page.locator('#result .exports').wait_for()
        with page.expect_download() as downloaded:
            page.locator('#result .exports a',has_text='Repair brief').click()
        brief=Path(downloaded.value.path()).read_text(encoding='utf-8')
        assert '# ParivartanParakh repair brief' in brief and identity in brief
        page.locator('#library-search').fill('zz-no-such-case-zz')
        page.get_by_text('No matching retained failures.',exact=False).wait_for()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors,errors
        browser.close()
    print('PASS: library opens matching failure; real download; search; mobile layout; no JS errors.')


if __name__=='__main__': main()
