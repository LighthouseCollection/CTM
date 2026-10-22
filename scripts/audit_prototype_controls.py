"""Read local prototype screens and expose safe tabs/disclosures/dialogs.

Only local synthetic prototype interactions; never saves/submits/sends/deletes.
Output contains control labels, not input values or sample case/profile contents.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import re
import threading
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True)
parser.add_argument("--output", default=".tmp/ui-prototype-controls.json")
args = parser.parse_args()
root = Path(args.root).resolve()
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"
snapshot = """() => [...document.querySelectorAll('input,select,textarea,button,[role=tab],summary')].map((e,index)=>({index,tag:e.tagName,type:e.type||'',id:e.id,label:(e.getAttribute('aria-label')||[...(e.labels||[])].map(l=>l.textContent).join(' ')||e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,180),visible:!!(e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden')}))"""
records=[]
trigger_selector = '[data-tab], [role=tab], button[aria-expanded], button[onclick*="openModal"], button[onclick*="switchUserTab"], div[onclick^="DF.goSec"], summary'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1100})
        page.set_default_timeout(1500)
        page.on("dialog",lambda dialog:dialog.dismiss())
        def restrict(route):
            if route.request.url.startswith(base) and route.request.method=="GET": route.continue_()
            else: route.abort()
        page.route("**/*",restrict)
        files = sorted((root/"ctm-admin").glob("admin-*.html")) + sorted(file for file in (root/"ctm-public").glob("public-*.html") if not file.name.startswith("public-crown-"))
        for file in files:
            url=base+"/"+file.relative_to(root).as_posix()
            page.goto(url,wait_until="load")
            initial=page.evaluate(snapshot)
            triggers=page.locator(trigger_selector)
            candidates=triggers.evaluate_all("es=>es.map((e,i)=>({index:i,label:(e.textContent||e.getAttribute('aria-label')||'').trim(),action:e.getAttribute('onclick')||e.getAttribute('data-tab')||''}))")
            exercised=[]
            for candidate in candidates[:40]:
                if re.search(r'purge|delete|export|send|save|submit|sign.?out|password|payment',candidate['label']+' '+candidate['action'],re.I): continue
                page.goto(url,wait_until="load")
                target=page.locator(trigger_selector).nth(candidate['index'])
                if not target.is_visible(): continue
                try:
                    target.click()
                    after=page.evaluate(snapshot)
                    nested = []
                    if file.name == 'public-petition.html':
                        for radio in page.locator('input[type=radio][onchange*="showCond"]').all():
                            if radio.is_visible() and 'true' in (radio.get_attribute('onchange') or ''):
                                radio.check(force=True)
                                nested.append({'id':radio.get_attribute('id'),'action':'conditional reveal','controls': [c for c in page.evaluate(snapshot) if c['visible']]})
                        child = page.locator('button[onclick^="DF.addChild"]')
                        if child.count() and child.is_visible():
                            child.click()
                            nested.append({'action':'add child repeat','controls':[c for c in page.evaluate(snapshot) if c['visible']]})
                    before_ids={(c['tag'],c['id'],c['label']) for c in initial if c['visible']}
                    revealed=[c for c in after if c['visible'] and (c['tag'],c['id'],c['label']) not in before_ids]
                    exercised.append({**candidate,'revealed':revealed,'nested_triggers':nested})
                except Exception as error:
                    exercised.append({**candidate,'blocked':type(error).__name__})
            source = file.read_text(encoding='utf-8')
            for control in initial:
                match = re.search(r'\bid=[\"\x27]'+re.escape(control['id'])+r'[\"\x27]', source) if control['id'] else None
                control['source_line'] = source.count('\n',0,match.start())+1 if match else None
            records.append({'page':file.relative_to(root).as_posix(),'controls':initial,'safe_triggers':exercised,'candidate_count':len(candidates),'coverage':'Safe visible tabs/disclosures/modal-open triggers only; submission/destructive/provider actions excluded; future Crown screens excluded'})
            print(json.dumps({'page':file.name,'controls':len(initial),'triggers':len(exercised)}),flush=True)
        browser.close()
finally:
    server.shutdown();server.server_close()
out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'root':str(root),'pages':records},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pages':len(records),'output':str(out)}))
