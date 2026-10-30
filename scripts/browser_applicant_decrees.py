"""Proposed released-decree read fixtures; no real signed document or release acceptance."""
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tmp/applicant-decrees';OUT.mkdir(parents=True,exist_ok=True)
CDN='https://design-system.lighthouseway.org/cdn/0.76.0/'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-decrees.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url)=>{const r=await fetch(url);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const [lang,setLang]=R.useState('en');R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.lang=lang;},[lang]);
return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
h(CTMApplicantDecrees.ReleasedDecrees,{caseId:'11111111-1111-4111-8111-111111111111',api,lang}))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path=='/applicant-decrees.js'
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/'static/ctm/applicant-decrees.js').read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
case='11111111-1111-4111-8111-111111111111';file='22222222-2222-4222-8222-222222222222'
row={'id':case,'reference':'DCR-<img src=x onerror=alert(1)>','language':'bilingual','released_at':'2026-10-21T12:00:00Z',
 'signed_file':{'id':file,'name':'Certificate.pdf','scan_state':'clean','download_url':f'/api/files/{file}/'}}
data={'id':case,'released_decrees':[row]};status=200;checks=[];errors=[];methods=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route_api(route):
            methods.append(route.request.method);route.fulfill(status=status,json=data)
        page.route('**/api/**',route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        expect(page.get_by_text(row['reference'],exact=True)).to_be_visible()
        link=page.get_by_role('link',name='View or download signed PDF',exact=True)
        expect(link).to_have_attribute('href',f'/api/files/{file}/')
        assert page.locator('img').count()==0
        checks.append('Only explicit released rows render exact signed-file links; references are escaped')
        page.get_by_role('button',name='العربية',exact=True).click()
        expect(page.get_by_role('link',name='عرض أو تنزيل ملف PDF الموقّع',exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':900})
        assert page.locator('[style]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(page.locator('bdi').first).to_have_attribute('dir','ltr')
        page.screenshot(path=str(OUT/'ar-390.png'),full_page=True,caret='initial')
        checks.append('Arabic mobile release metadata preserves timestamp direction without inline styles or overflow')
        page.get_by_role('button',name='English',exact=True).click()
        data['released_decrees']=[]
        page.get_by_role('button',name='Refresh released certificates',exact=True).click()
        expect(page.get_by_text('No certificate is currently released to your account.',exact=True)).to_be_visible()
        assert page.get_by_role('link').count()==0
        checks.append('Authoritative refresh removes withdrawn release links without inferring access from case state')
        data['released_decrees']=[row]
        page.get_by_role('button',name='Refresh released certificates',exact=True).click()
        expect(link).to_be_visible()
        status=403
        page.get_by_role('button',name='Refresh released certificates',exact=True).click()
        expect(page.get_by_role('alert')).to_be_visible()
        assert page.get_by_role('link').count()==0
        status=200;data={'id':case}
        page.get_by_role('button',name='Refresh released certificates',exact=True).click()
        expect(page.get_by_role('alert')).to_be_visible()
        assert page.get_by_role('link').count()==0
        assert all(m=='GET' for m in methods)
        assert not errors,errors
        checks.append('Denied or missing-contract refresh clears stale links; all requests remain GET')
        browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Proposed own release-list fixtures only; server revocation and actual signed PDFs remain separate acceptance'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
