"""Verify the pinned upstream app unchanged, without storage instrumentation."""
import hashlib
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
from todomvc_adapter import ROOT,UPSTREAM,COMMIT


def main():
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*_): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(UPSTREAM)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context()
            context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
            page=context.new_page()
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(origin+'/')
            for title in ['Prepare hackathon demo','Submit project']:
                page.locator('.new-todo').fill(title)
                page.locator('.new-todo').press('Enter')
            page.locator('.todo-list li:nth-child(1) .toggle').check()
            before=page.locator('.todo-list li label').all_text_contents()
            completed_before=page.locator('.todo-list .toggle').evaluate_all('(nodes)=>nodes.map(n=>n.checked)')
            state=context.storage_state()
            page.reload()
            after=page.locator('.todo-list li label').all_text_contents()
            completed_after=page.locator('.todo-list .toggle').evaluate_all('(nodes)=>nodes.map(n=>n.checked)')
            context.close()
            restored=browser.new_context(storage_state=state)
            restored.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
            fresh=restored.new_page()
            fresh.goto(origin+'/')
            in_new_context=fresh.locator('.todo-list li label').all_text_contents()
            completed_restored=fresh.locator('.todo-list .toggle').evaluate_all('(nodes)=>nodes.map(n=>n.checked)')
            fresh.screenshot(path=str(ROOT/'todomvc-upstream-baseline.png'),full_page=True)
            assert before==after==in_new_context==['Prepare hackathon demo','Submit project']
            assert completed_before==completed_after==completed_restored==[True,False]
            assert not errors,errors
            result={'commit':COMMIT,'instrumentation':False,'upstream_app_unchanged':True,'before':before,'after_reload':after,
                    'new_context':in_new_context,'completed_before':completed_before,'completed_after':completed_after,'completed_restored':completed_restored,
                    'errors':errors,'passed':True}
            (ROOT/'TODOMVC_BASELINE.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(result,indent=2))
            restored.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__=='__main__':main()
