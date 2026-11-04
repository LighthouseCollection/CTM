"""Actual-shaped own supplement interruption fixtures; pinned CDN."""
import json,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];CDN='https://design-system.lighthouseway.org/cdn/0.76.0/'
ID='11111111-1111-4111-8111-111111111111';FILE='22222222-2222-4222-8222-222222222222'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-files.js"></script><script src="/applicant-supplements.js"></script>
<script src="/applicant.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url,options)=>{const r=await fetch(url,options);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const [lang,setLang]=R.useState('en');R.useEffect(()=>{document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr';},[lang]);
return h(P.ThemeProvider,null,h(P.PageContent,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
h(CTMApplicant.ApplicationEditor,{applicationId:'APPID',api,lang,onBack:()=>{window.leftEditor=true;}})));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN).replace('APPID',ID)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path in {'/applicant.js','/applicant-files.js','/applicant-supplements.js'}
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/('static/ctm'+self.path)).read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
file={'id':FILE,'attachment_id':'attachment','category':'PET','context':'','name':'Clean evidence.pdf','scan_state':'clean','download_url':f'/api/files/{FILE}/'}
app={'id':ID,'kind':'appeal','status':'submitted','version':1,'can_edit':False,'can_supplement':True,
 'answers':{'new_information':'Original submitted information'},'supplements':[
 {'id':'33333333-3333-4333-8333-333333333333','text':'<img src=x onerror=alert(1)> Earlier supplement','idempotency_key':None,'timestamp':'2026-10-21T12:00:00Z','manifest':[]}],
 'questionnaire':{'id':'form','version':1,'published':True,'definition':{'fields':[
 {'code':'new_information','type':'textarea','label_en':'Submitted information','label_ar':'المعلومات المقدّمة'}]}}}
evidence={'can_upload':False,'items':[file,{**file,'id':'44444444-4444-4444-8444-444444444444','attachment_id':'pending','name':'Pending evidence.pdf','scan_state':'pending','download_url':None}],'requirements':[]}
mode='uncertain';read_denied=False;writes=[];pending=[];errors=[];checks=[]
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1100})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def api(route):
            if route.request.method=='GET':route.fulfill(status=403 if read_denied else 200,json={} if read_denied else evidence if route.request.url.endswith('/files/') else app)
            else:
                payload=route.request.post_data_json;writes.append(payload)
                row={'id':f'55555555-5555-4555-8555-{len(writes):012d}','text':payload['text'],'idempotency_key':payload['idempotency_key'],
                     'timestamp':'2026-10-21T13:00:00Z','manifest':[{'id':FILE,'sha256':'a'*64}] if payload['file_ids'] else []}
                if mode=='drop':route.abort('failed');return
                app['supplements'].append(row)
                if mode=='uncertain':route.abort('failed')
                elif mode=='pause':pending.append((route,row))
                else:route.fulfill(status=201,json={'id':row['id']})
        page.route('**/api/**',api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        expect(page.get_by_label('New additional information',exact=True)).to_be_visible()
        assert page.locator('img').count()==0
        assert page.get_by_role('checkbox',name='Pending evidence.pdf',exact=True).count()==0
        text='New information <script>alert(1)</script>'
        page.get_by_label('New additional information',exact=True).fill(text)
        page.get_by_role('checkbox',name='Clean evidence.pdf',exact=True).check()
        evidence['items'][0]['scan_state']='pending';evidence['items'][0]['download_url']=None
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        expect(page.get_by_text('Some selected originals are no longer available.',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Review supplement',exact=True)).to_be_disabled()
        expect(page.get_by_label('New additional information',exact=True)).to_have_value(text)
        assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
        page.get_by_role('button',name='Remove unavailable evidence selections',exact=True).click()
        evidence['items'][0]['scan_state']='clean';evidence['items'][0]['download_url']=f'/api/files/{FILE}/'
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        page.get_by_role('checkbox',name='Clean evidence.pdf',exact=True).check()
        checks.append('Unsafe evidence refresh preserves local intent/text, blocks review and requires explicit removal before reselection')
        page.get_by_role('button',name='Back',exact=True).click()
        expect(page.get_by_text('Reloading or leaving will discard your unsaved changes.',exact=True)).to_be_visible()
        page.get_by_role('button',name='Keep editing',exact=True).click()
        expect(page.get_by_label('New additional information',exact=True)).to_have_value(text)
        assert app['answers']=={'new_information':'Original submitted information'}
        checks.append('Supplement draft preserves immutable appeal answers, excludes pending evidence and participates in editor navigation guard')
        page.get_by_role('button',name='العربية',exact=True).click()
        expect(page.get_by_label('المعلومات الإضافية الجديدة',exact=True)).to_have_value(text)
        page.set_viewport_size({'width':390,'height':1000})
        assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.get_by_role('button',name='English',exact=True).click()
        page.get_by_role('button',name='Review supplement',exact=True).click()
        assert page.locator('img').count()==0
        page.get_by_role('button',name='Submit additional information',exact=True).click()
        expect(page.get_by_text('Submission was not confirmed.',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Submit additional information',exact=True)).to_be_disabled()
        assert len(writes)==1 and writes[0]['text']==text and writes[0]['file_ids']==[FILE] and writes[0]['expected_version']==1 and len(writes[0]['idempotency_key'])==36
        checks.append('EN/AR draft/review is escaped and mobile-safe; uncertain append freezes exact text/evidence without retry')
        evidence['items'][0]['scan_state']='pending';evidence['items'][0]['download_url']=None
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        expect(page.get_by_role('button',name='Clear local entry and start a new supplement',exact=True)).to_be_visible()
        frozen_review=page.get_by_role('region',name='Review supplement',exact=True)
        expect(frozen_review.get_by_text('Clean evidence.pdf',exact=True)).to_be_visible()
        assert frozen_review.get_by_role('link',name='Download supporting original',exact=True).count()==0
        evidence['items'][0]['scan_state']='clean';evidence['items'][0]['download_url']=f'/api/files/{FILE}/'
        assert len(writes)==1
        page.get_by_role('button',name='Clear local entry and start a new supplement',exact=True).click()
        expect(page.get_by_label('New additional information',exact=True)).to_have_value('')
        checks.append('Authoritative refresh shows received history; only explicit new-entry action clears frozen local payload')
        mode='drop'
        page.get_by_label('New additional information',exact=True).fill('Original interrupted retry')
        page.get_by_role('checkbox',name='Clean evidence.pdf',exact=True).check()
        page.get_by_role('button',name='Review supplement',exact=True).click()
        page.get_by_role('button',name='Submit additional information',exact=True).click()
        expect(page.get_by_text('Submission was not confirmed.',exact=False)).to_be_visible()
        evidence['items'][0]['scan_state']='pending';evidence['items'][0]['download_url']=None
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        expect(page.get_by_role('button',name='Retry original supplement',exact=True)).to_be_visible()
        assert page.get_by_role('button',name='Clear local entry and start a new supplement',exact=True).count()==0
        expect(page.get_by_text('This original was selected for this attempt; no current download is available.',exact=True)).to_be_visible()
        evidence['items'][0]['scan_state']='clean';evidence['items'][0]['download_url']=f'/api/files/{FILE}/'
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        mode='ack'
        page.get_by_role('button',name='Retry original supplement',exact=True).click()
        expect(page.get_by_text('The server received your supplement.',exact=False)).to_be_visible()
        assert len(writes)==3 and writes[-1]==writes[-2]
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        page.get_by_role('button',name='Clear local entry and start a new supplement',exact=True).click()
        checks.append('Missing receipt cannot create a fresh supplement; explicit retry reuses exact frozen key/version/text/files and acknowledges once')
        mode='pause';page.get_by_label('New additional information',exact=True).fill('Another supplement')
        page.get_by_role('button',name='Review supplement',exact=True).click()
        page.get_by_role('button',name='Submit additional information',exact=True).click()
        expect(page.get_by_role('button',name='Back',exact=True)).to_be_disabled()
        assert page.evaluate("() => { const e=new Event('beforeunload',{cancelable:true}); return !window.dispatchEvent(e); }")
        pending[0][0].fulfill(status=201,json={'id':pending[0][1]['id']})
        expect(page.get_by_text('The server received your supplement.',exact=False)).to_be_visible()
        checks.append('In-flight append blocks parent navigation and installs unload protection; acknowledgement is distinguished from read history')
        app['status']='accepted';app['can_supplement']=False
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        expect(page.get_by_text('This filing is not accepting additional information.',exact=True)).to_be_visible()
        expect(page.get_by_role('button',name='Submit additional information',exact=True)).to_be_disabled()
        del app['can_supplement']
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        expect(page.get_by_text('Additional filing information is unavailable.',exact=False)).to_be_visible()
        assert page.get_by_role('button',name='Submit additional information',exact=True).count()==0
        assert len(writes)==4 and not errors,errors
        checks.append('Disposition or missing capability disables append and malformed refresh clears history without deleting local appeal data')
        app.update(kind='petition',origin='closed_case_intake',status='submitted',can_supplement=True)
        page.reload(wait_until='networkidle')
        expect(page.get_by_label('New additional information',exact=True)).to_be_visible()
        expect(page.get_by_text('Your submitted filing stays unchanged.',exact=False)).to_be_visible()
        checks.append('Closed-case first-filing reconsideration uses the same explicit supplement capability without requiring appeal kind')
        page.get_by_label('New additional information',exact=True).fill('Local entry before denied refresh')
        read_denied=True
        page.get_by_role('button',name='Refresh supplement history and evidence',exact=True).click()
        expect(page.get_by_text('Additional filing information is unavailable.',exact=False)).to_be_visible()
        assert page.get_by_role('link',name='Download supporting original',exact=True).count()==0
        assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
        assert len(writes)==4
        checks.append('Denied own refresh clears private receipt/evidence views while retaining local dirty/navigation intent and sends no retry')
        browser.close()
finally:server.shutdown()
print(json.dumps({'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Actual-shaped own supplement interruption fixtures; synthetic API only'},indent=2))
