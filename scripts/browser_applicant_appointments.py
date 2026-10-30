"""Private-invitation proposed contract fixtures with the real pinned Plenix CDN.

No backend read-route acceptance is claimed. Run with uv run --group browser python.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tmp/applicant-appointments'
OUT.mkdir(parents=True,exist_ok=True)
CDN='https://design-system.lighthouseway.org/cdn/0.76.0/'
HTML='''<!doctype html><html lang="en" data-plx-density-policy="compact"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css">
<link rel="stylesheet" href="CDNplenix.css"><script src="CDNvendor/react.production.min.js"></script>
<script src="CDNvendor/react-dom.production.min.js"></script><script src="CDNplenix.js"></script>
<script src="/applicant-appointments.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url,options)=>{const response=await fetch(url,options);if(!response.ok)throw {status:response.status};return response.json();};
function Harness(){const [lang,setLang]=R.useState('en');
 R.useEffect(()=>{document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';},[lang]);
 return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,
 h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
 h(CTMApplicantAppointments.Appointments,{api,lang}))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));
</script></body></html>'''.replace('CDN',CDN)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path=='/applicant-appointments.js'
        content=(ROOT/'static/ctm/applicant-appointments.js').read_bytes() if js else HTML.encode()
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8')
        self.end_headers();self.wfile.write(content)
    def log_message(self,*args):pass

server=HTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
row=dict(id='11111111-1111-4111-8111-111111111111',case_number='T-2026-0001',version=2,
 starts_at='2026-12-01T10:00:00-08:00',ends_at='2026-12-01T10:30:00-08:00',
 instructions='<img src=x onerror=alert(1)> Private invitation only',state='invited',response=None,can_respond=True)
listing={'items':[row]};requests=[];mode='ok';checks=[];errors=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1280,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route_api(route):
            if route.request.method=='GET':
                route.fulfill(status=503 if mode=='unavailable' else 200,json=listing)
            else:
                requests.append(route.request.post_data_json)
                if mode=='uncertain':route.abort('failed')
                elif mode=='stale':route.fulfill(status=422,json={'error':'stale'})
                else:
                    row['response']=route.request.post_data_json['response']
                    route.fulfill(status=201,json={'id':'response'})
        page.route('**/api/appointments/**',route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        expect(page.get_by_text(row['instructions'],exact=True)).to_be_visible()
        assert page.locator('img').count()==0
        expect(page.locator('bdi[dir="ltr"]').filter(has_text=row['starts_at'])).to_be_visible()
        page.get_by_role('button',name='Confirm attendance',exact=True).click()
        expect(page.get_by_text('Your response was received.',exact=False)).to_be_visible()
        assert requests==[{'version':2,'response':'confirm','explanation':''}]
        expect(page.get_by_role('button',name='Reject invitation',exact=True)).to_be_disabled()
        page.get_by_role('button',name='Refresh invitations',exact=True).click()
        expect(page.get_by_text('Your current response: Confirmed',exact=True)).to_be_visible()
        checks.append('Escaped private instructions, exact offset times and version-bound confirmation; server refresh shows current response')
        mode='stale'
        page.get_by_label('Reason for rejecting (optional)',exact=True).fill('Unavailable')
        page.get_by_role('button',name='Reject invitation',exact=True).click()
        expect(page.get_by_text('This invitation has changed.',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Confirm attendance',exact=True)).to_be_disabled()
        assert requests[-1]=={'version':2,'response':'reject','explanation':'Unavailable'}
        row.update(version=3,response=None,starts_at='2026-12-02T10:00:00-08:00',ends_at='2026-12-02T10:30:00-08:00')
        page.get_by_role('button',name='Refresh invitations',exact=True).click()
        expect(page.get_by_text('Invitation version: 3',exact=True)).to_be_visible()
        expect(page.get_by_label('Reason for rejecting (optional)',exact=True)).to_have_value('')
        checks.append('Stale invitation locks response until refreshed new version; old response and explanation do not migrate')
        mode='uncertain'
        page.get_by_role('button',name='Confirm attendance',exact=True).click()
        expect(page.get_by_text('Your response was not confirmed.',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Reject invitation',exact=True)).to_be_disabled()
        assert requests[-1]['version']==3
        checks.append('Uncertain acknowledgement blocks both actions until authoritative refresh')
        mode='ok';row.update(state='cancelled',can_respond=False)
        page.get_by_role('button',name='Refresh invitations',exact=True).click()
        expect(page.get_by_text('This invitation is not accepting responses.',exact=True)).to_be_visible()
        assert page.get_by_role('button',name='Confirm attendance',exact=True).count()==0
        page.get_by_role('button',name='العربية',exact=True).click()
        expect(page.get_by_text('هذه الدعوة لا تقبل الردود حالياً.',exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':900})
        assert page.locator('html').get_attribute('dir')=='rtl'
        assert page.locator('[style]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT/'ar-390.png'),full_page=True,caret='initial')
        checks.append('Cancelled invitation exposes no actions; Arabic mobile RTL has no inline styles or horizontal overflow')
        page.get_by_role('button',name='English',exact=True).click()
        listing={'items':[row,row]}
        page.get_by_role('button',name='Refresh invitations',exact=True).click()
        expect(page.get_by_text('Your invitations are unavailable.',exact=False)).to_be_visible()
        assert page.get_by_text(row['instructions'],exact=True).count()==0
        listing={'items':[]}
        page.get_by_role('button',name='Refresh invitations',exact=True).click()
        expect(page.get_by_text('You have no appointment invitations.',exact=True)).to_be_visible()
        mode='unavailable'
        page.get_by_role('button',name='Refresh invitations',exact=True).click()
        expect(page.get_by_text('Your invitations are unavailable.',exact=False)).to_be_visible()
        checks.append('Malformed/duplicate and unavailable reads fail closed; only a valid empty list reports no invitations')
        assert not errors,errors
        browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Proposed private read contract fixtures; real pinned CDN; not backend appointment integration acceptance'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
