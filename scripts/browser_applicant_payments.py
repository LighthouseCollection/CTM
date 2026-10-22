"""Payment history contract fixtures; real Plenix CDN, no simulated provider acceptance."""
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tmp/applicant-payments';OUT.mkdir(parents=True,exist_ok=True)
CDN='https://design-system.lighthouseway.org/cdn/0.58.0/'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-payments.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url)=>{const r=await fetch(url);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const [lang,setLang]=R.useState('en');R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.lang=lang;},[lang]);
return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
h(CTMApplicantPayments.PaymentHistory,{applicationId:'own',api,lang}))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path=='/applicant-payments.js'
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/'static/ctm/applicant-payments.js').read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
data={'fee':{'status':'due','amount_minor':25000,'currency':'USD'},'verified_payment':False,'events':[],
 'checkouts':[{'id':'attempt','state':'processing','version':2,'timestamp':'2026-10-21T10:00:00Z'}]}
status=200;checks=[];errors=[];methods=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route_api(route):
            methods.append(route.request.method);route.fulfill(status=status,json=data)
        page.route('**/api/**',route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        expect(page.get_by_text('Payment processing · Answer version: 2',exact=True)).to_be_visible()
        expect(page.get_by_text('No verified provider payment is recorded.',exact=False)).to_be_visible()
        assert page.get_by_role('button').count()==2
        checks.append('Processing history is read-only and does not offer payment/reconciliation writes or claim filing success')
        data['checkouts'][0]['state']='needs_review'
        page.get_by_role('button',name='Refresh payment history',exact=True).click()
        expect(page.get_by_text('Payment requires tribunal reconciliation · Answer version: 2',exact=True)).to_be_visible()
        data['events']=[{'id':'refund','kind':'refunded','amount_minor':5000,'currency':'USD',
            'amount_basis':'cumulative_refunded','timestamp':'2026-10-21T12:00:00Z'}]
        page.get_by_role('button',name='Refresh payment history',exact=True).click()
        expect(page.get_by_text('Cumulative refunded total',exact=True)).to_be_visible()
        expect(page.get_by_text('Refund recorded · $50.00',exact=True)).to_be_visible()
        checks.append('Reconciliation and cumulative refund facts display without inventing a refund request or adding cumulative totals')
        page.get_by_role('button',name='العربية',exact=True).click()
        expect(page.get_by_text('إجمالي المبلغ المسترد التراكمي',exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':900})
        assert page.locator('[style]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(page.locator('bdi').first).to_have_attribute('dir','ltr')
        page.screenshot(path=str(OUT/'ar-390.png'),full_page=True,caret='initial')
        checks.append('Arabic mobile histories preserve timestamp direction without inline styles or horizontal overflow')
        page.get_by_role('button',name='English',exact=True).click()
        status=403
        page.get_by_role('button',name='Refresh payment history',exact=True).click()
        expect(page.get_by_text('Payment history is unavailable.',exact=False)).to_be_visible()
        assert page.get_by_text('Cumulative refunded total',exact=True).count()==0
        status=200;data['events'][0]['amount_minor']=-1
        page.get_by_role('button',name='Refresh payment history',exact=True).click()
        expect(page.get_by_text('Payment history is unavailable.',exact=False)).to_be_visible()
        assert all(m=='GET' for m in methods)
        assert not errors,errors
        checks.append('Denied/malformed history removes stale financial facts; all requests remain GET')
        browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Synthetic read-contract fixtures; no provider payment/antivirus acceptance'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
