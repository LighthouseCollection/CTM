"""Own request presentation fixtures; no signed release or response submission."""
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tmp/applicant-requests';OUT.mkdir(parents=True,exist_ok=True)
CDN='https://design-system.lighthouseway.org/cdn/0.60.1/'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-requests.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url)=>{const r=await fetch(url);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const [lang,setLang]=R.useState('en');R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.lang=lang;},[lang]);
return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
h(CTMApplicantRequests.Requests,{caseId:'11111111-1111-4111-8111-111111111111',api,lang}))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path=='/applicant-requests.js'
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/'static/ctm/applicant-requests.js').read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
case='11111111-1111-4111-8111-111111111111'
row={'id':case,'title':'Own request <img src=x onerror=alert(1)>','kind':'intake','state':'sent','instructions':'Private <script>instruction</script>',
 'language':'both','sent_at':'2026-10-21T12:00:00Z','questions':[{'code':'Q1','version':2,'en':'Bound English question','ar':'سؤال عربي معتمد'}]}
data={'items':[row]};status=200;checks=[];errors=[];methods=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route_api(route):
            methods.append(route.request.method);route.fulfill(status=status,json=data)
        page.route('**/api/**',route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        expect(page.get_by_text(row['title'],exact=True)).to_be_visible()
        expect(page.get_by_text(row['instructions'],exact=True)).to_be_visible()
        expect(page.get_by_text('Bound English question',exact=True)).to_be_visible()
        assert page.locator('img,input,textarea').count()==0
        checks.append('Own bound questions and instructions display escaped with no unsupported response editor')
        page.get_by_role('button',name='العربية',exact=True).click()
        expect(page.get_by_text('سؤال عربي معتمد',exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':900})
        assert page.locator('[style]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(page.locator('bdi').first).to_have_attribute('dir','ltr')
        page.screenshot(path=str(OUT/'ar-390.png'),full_page=True,caret='initial')
        checks.append('Bound bilingual questions switch to Arabic with mobile RTL and no inline styles or overflow')
        page.get_by_role('button',name='English',exact=True).click()
        row['kind']='medical';row['questions']=[]
        page.get_by_role('button',name='Refresh my requests',exact=True).click()
        expect(page.get_by_text('Medical assessment request · Awaiting response',exact=True)).to_be_visible()
        expect(page.get_by_text('An assessment report and its signed, scoped release are separate requirements.',exact=False)).to_be_visible()
        assert page.get_by_role('checkbox').count()==0
        checks.append('Assessment request distinguishes report from signed scoped release without fabricating consent or signature')
        status=403
        page.get_by_role('button',name='Refresh my requests',exact=True).click()
        expect(page.get_by_role('alert')).to_be_visible()
        assert page.get_by_text(row['instructions'],exact=True).count()==0
        status=200;row['kind']='interview'
        page.get_by_role('button',name='Refresh my requests',exact=True).click()
        expect(page.get_by_role('alert')).to_be_visible()
        data={'items':[]}
        page.get_by_role('button',name='Refresh my requests',exact=True).click()
        expect(page.get_by_text('No requests are currently listed for you.',exact=True)).to_be_visible()
        assert all(m=='GET' for m in methods)
        assert not errors,errors
        checks.append('Denied or invalid staff-only projection removes old content; authoritative empty list and GET-only transport')
        browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Own read presentation fixtures; no response submission, approved release wording or medical disclosure acceptance'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
