"""Appeal entry UI fixtures with real pinned CDN; no provider acceptance."""
import json,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
CDN='https://design-system.lighthouseway.org/cdn/0.58.0/'
CASE='11111111-1111-4111-8111-111111111111';APPEAL='22222222-2222-4222-8222-222222222222'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-appeals.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url,options)=>{try{const r=await fetch(url,options);if(!r.ok)throw {status:r.status};return await r.json();}finally{window.pendingFinished=true;}};
function Harness(){const [lang,setLang]=R.useState('en'),[visible,setVisible]=R.useState(true);
R.useEffect(()=>{document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';},[lang]);
return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,
h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
h(P.Button,{onClick:()=>setVisible(false)},'Leave case'),
visible?h(CTMApplicantAppeals.StartAppeal,{caseId:'CASE',api,lang,onOpen:id=>{window.openedId=id;}}):h(P.Text,null,'Case closed'))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN).replace('CASE',CASE)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path=='/applicant-appeals.js';self.send_response(200)
        self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/'static/ctm/applicant-appeals.js').read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[];errors=[];mode='reject';payloads=[];pending=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        def api(route):
            payloads.append(route.request.post_data_json)
            if mode=='pause':pending.append(route)
            else:route.fulfill(status=422 if mode=='reject' else 201,json={'error':'eligibility'} if mode=='reject' else {'id':APPEAL,'case_id':CASE,'kind':'appeal'})
        page.route('**/api/applications/',api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        page.get_by_role('button',name='Start or resume appeal',exact=True).click()
        expect(page.get_by_text('Unable to open an appeal.',exact=False)).to_be_visible()
        assert page.evaluate('window.openedId') is None
        page.get_by_role('button',name='العربية',exact=True).click()
        expect(page.get_by_text('تعذر فتح استئناف.',exact=False)).to_be_visible()
        page.set_viewport_size({'width':390,'height':900})
        assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        checks.append('Eligibility failure preserves case view and localized Arabic mobile UI without styles or overflow')
        page.get_by_role('button',name='English',exact=True).click()
        mode='ok';page.get_by_role('button',name='Start or resume appeal',exact=True).click()
        page.wait_for_function('window.openedId !== undefined')
        assert page.evaluate('window.openedId')==APPEAL and payloads[-1]=={'kind':'appeal','case_id':CASE}
        checks.append('Valid same-case appeal acknowledgement opens the bound editor without client case mutations')
        page.reload(wait_until='networkidle');mode='pause'
        page.get_by_role('button',name='Start or resume appeal',exact=True).click()
        expect(page.get_by_role('button',name='Opening appeal…',exact=True)).to_be_disabled()
        page.get_by_role('button',name='Leave case',exact=True).click()
        pending[0].fulfill(status=201,json={'id':APPEAL,'case_id':CASE,'kind':'appeal'})
        page.wait_for_function('window.pendingFinished === true')
        assert page.evaluate('window.openedId') is None
        checks.append('Late appeal start acknowledgement cannot navigate after leaving the case')
        assert not errors,errors
        browser.close()
finally:server.shutdown()
print(json.dumps({'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Synthetic API fixtures; real pinned CDN'},indent=2))
