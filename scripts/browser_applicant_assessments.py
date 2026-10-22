"""Own request interruption and guard fixtures; no real consent acceptance."""
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tmp/applicant-assessments';OUT.mkdir(parents=True,exist_ok=True)
CDN='https://design-system.lighthouseway.org/cdn/0.60.1/'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-assessments.js"></script><script src="/applicant-responses.js"></script><script src="/applicant-requests.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url,options={})=>{const r=await fetch(url,options);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const [lang,setLang]=R.useState('en'),[left,setLeft]=R.useState(false);const guard=R.useRef(null),register=R.useCallback(fn=>{guard.current=fn;},[]);R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.lang=lang;},[lang]);
return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),
h(P.Button,{onClick:()=>{const move=()=>setLeft(true);if(guard.current)guard.current(move);else move();}},'Leave workspace'),left?h(P.Text,null,'Left workspace'):h(CTMApplicantRequests.Requests,{caseId:'11111111-1111-4111-8111-111111111111',api,lang,onNavigationGuard:register}))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path.startswith('/applicant-') and self.path.endswith('.js')
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/('static/ctm'+self.path)).read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
id='11111111-1111-4111-8111-111111111111';proc='22222222-2222-4222-8222-222222222222'
signature='33333333-3333-4333-8333-333333333333';report='44444444-4444-4444-8444-444444444444';release='55555555-5555-4555-8555-555555555555';version='a'*64
row={'id':id,'proceeding_id':proc,'request_version':version,'title':'Own assessment','instructions':'Own instructions','kind':'medical','state':'sent',
 'language':'both','sent_at':'2026-10-21T12:00:00Z','questions':[],'can_respond':False,'can_upload':True,'can_sign_release':True,
 'release_status':'none','signed_releases':[],'response':None,'release_definition':{'id':proc,'version':1,'definition':{},
 'declaration_en':'Bound disclosure <b>as supplied</b>','declaration_ar':'تفويض مرتبط كما ورد'}}
files={'request_id':id,'proceeding_id':proc,'request_version':version,'can_upload':True,'items':[
 {'id':signature,'attachment_id':signature,'name':'Signed release.pdf','category':'CONSENT','purpose':'consent','version':1,'scan_state':'clean','download_url':f'/api/files/{signature}/'},
 {'id':report,'attachment_id':report,'name':'Private report.pdf','category':'MED','purpose':'report','version':1,'scan_state':'clean','download_url':f'/api/files/{report}/'}]}
posts=[];errors=[];checks=[];hold_upload=False;held_upload=None;read_status=200
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1100});page.on('pageerror',lambda e:errors.append(str(e)))
        def route_api(route):
            global held_upload
            url=route.request.url
            if route.request.method=='POST':
                posts.append(url)
                if '/release/' in url:
                    row.update(can_respond=True,can_sign_release=False,release_status='signed',signed_releases=[{'id':release,'declaration_id':proc,
                     'signature_file_id':signature,'signed_at':'2026-10-21T12:01:00Z','scope':{'council':True,'purpose':'medical','request_id':id,'proceeding_id':proc}}])
                    route.fulfill(status=500,json={'error':'synthetic lost acknowledgement'})
                elif hold_upload:held_upload=route
                else:route.fulfill(json={'id':report})
            elif '/requests/'+id+'/files/' in url:route.fulfill(status=read_status,json=files)
            else:route.fulfill(status=read_status,json={'items':[row]})
        page.route('**/api/**',route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        page.get_by_role('button',name='Open request',exact=True).click()
        expect(page.get_by_text('Bound disclosure <b>as supplied</b>',exact=True)).to_be_visible()
        page.get_by_label('Choose the signed release original',exact=True).select_option(signature)
        page.get_by_role('checkbox',name='I have read and accept this exact disclosure declaration for the council and this request.',exact=True).check()
        page.get_by_role('button',name='Review disclosure consent',exact=True).click()
        page.get_by_role('button',name='Confirm disclosure consent',exact=True).click()
        expect(page.get_by_text('The result is uncertain.',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Confirm disclosure consent',exact=True)).to_be_disabled()
        assert len(posts)==1
        expect(page.get_by_role('group',name='Report or response evidence',exact=True).locator('input[type=file]')).to_be_disabled()
        page.get_by_role('button',name='Refresh request and files',exact=True).click()
        expect(page.get_by_text('A signed release for this request and purpose is recorded.',exact=True)).to_be_visible()
        assert len(posts)==1
        checks.append('Exact declaration text is escaped; explicit consent uncertainty locks retry and own read recovers retained scope without another POST')
        selected=page.get_by_role('checkbox',name='Private report.pdf',exact=True);selected.check()
        page.get_by_role('button',name='Refresh request and files',exact=True).click()
        expect(selected).to_be_checked()
        assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
        checks.append('Evidence-only local response and unload guard survive successful authoritative refresh')
        page.get_by_role('button',name='Back to requests',exact=True).click()
        expect(page.get_by_role('button',name='Discard local response',exact=True)).to_be_visible()
        slot=page.get_by_role('group',name='Report or response evidence',exact=True)
        slot.locator('input[type=file]').set_input_files({'name':'more.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.7 synthetic'})
        hold_upload=True;slot.get_by_role('button',name='Upload original',exact=True).click()
        expect(page.get_by_role('button',name='Discard local response',exact=True)).to_be_disabled()
        assert held_upload is not None
        assert page.get_by_text('Left workspace',exact=True).count()==0
        held_upload.fulfill(json={'id':report});hold_upload=False
        expect(page.get_by_role('button',name='Discard local response',exact=True)).to_be_enabled()
        page.get_by_role('button',name='Keep editing',exact=True).click()
        expect(selected).to_be_checked()
        checks.append('Already-open discard confirmation cannot leave during delayed upload; selection remains after upload refresh')
        page.get_by_role('button',name='العربية',exact=True).click();page.set_viewport_size({'width':390,'height':1100})
        expect(page.get_by_text('تفويض مرتبط كما ورد',exact=True)).to_be_visible()
        assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT/'ar-workspace-390.png'),full_page=True,caret='initial')
        page.get_by_role('button',name='English',exact=True).click()
        checks.append('Private workspace, retained consent and local evidence render in Arabic mobile without runtime styles or overflow')
        read_status=403
        page.get_by_role('button',name='Refresh request and files',exact=True).click()
        expect(page.get_by_text('This request or its files cannot be verified.',exact=False)).to_be_visible()
        assert page.get_by_role('link').count()==0
        page.get_by_role('button',name='Leave workspace',exact=True).click()
        expect(page.get_by_role('button',name='Discard local response',exact=True)).to_be_visible()
        assert len(posts)==2
        checks.append('Denied refresh clears private original links while preserving local response guard; no automatic response or consent resend')
        assert not errors,errors;browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Interruption/refresh fixtures; real request integration is checked separately'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
