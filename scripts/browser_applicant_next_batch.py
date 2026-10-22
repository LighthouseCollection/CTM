"""Prepared response/lifecycle/recovery contracts; no real provider or institutional consent acceptance."""
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tmp/applicant-next-batch';OUT.mkdir(parents=True,exist_ok=True)
CDN='https://design-system.lighthouseway.org/cdn/0.58.0/'
HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script>
<script src="CDNplenix.js"></script><script src="/applicant-requests.js"></script><script src="/applicant-responses.js"></script><script src="/applicant-filing.js"></script><script src="/applicant-recovery.js"></script><script src="/applicant-lifecycle.js"></script><script src="/applicant-files.js"></script><script src="/applicant.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;
const api=async(url,options={})=>{const r=await fetch(url,options);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const [lang,setLang]=R.useState('en'),[view,setView]=R.useState({name:'Requests',key:0});const guard=R.useRef(null);
const register=R.useCallback(fn=>{guard.current=fn;},[]);const go=name=>{const move=()=>setView(v=>({name,key:v.key+1}));if(guard.current)guard.current(move);else move();};
R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.lang=lang;},[lang]);
return h(P.ThemeProvider,null,h(P.LocaleProvider,{locale:lang},h(P.PageContent,null,h(P.Stack,null,
h(P.Inline,{wrap:true},h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),...['Requests','Checkout','Lifecycle','Editor'].map(name=>h(P.Button,{key:name,onClick:()=>go(name)},name))),
view.name==='Requests'?h(CTMApplicantRequests.Requests,{key:view.key,caseId:'11111111-1111-4111-8111-111111111111',api,lang,onNavigationGuard:register}):
view.name==='Checkout'?h(CTMApplicantFiling.FilingActions,{key:view.key,application:window.currentApplication,api,lang,reviewed:true,onCheckout:url=>window.checkoutDestination=url}):
view.name==='Editor'?h(CTMApplicant.ApplicationEditor,{key:view.key,applicationId:window.currentApplication.id,api,lang,onBack:()=>go('Requests'),onNavigationGuard:register}):
h(CTMApplicantLifecycle.Actions,{key:view.key,application:window.currentApplication,api,lang,onRefresh:()=>go('Lifecycle')})
))));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>'''.replace('CDN',CDN)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        js=self.path.startswith('/applicant') and self.path.endswith('.js')
        self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
        self.wfile.write((ROOT/('static/ctm'+self.path)).read_bytes() if js else HTML.encode())
    def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
id='11111111-1111-4111-8111-111111111111';intent='22222222-2222-4222-8222-222222222222'
request={'id':id,'title':'Own response request','kind':'intake','state':'sent','instructions':'Own instructions','language':'both',
 'sent_at':'2026-10-21T12:00:00Z','can_respond':True,'request_version':'a'*64,'proceeding_id':intent,
 'questions':[{'code':'Q1','version':1,'en':'Bound response question','ar':'السؤال المحدد'}]}
application={'id':id,'kind':'petition','version':2,'status':'draft','can_checkout':True,'fee':{'status':'due','amount_minor':25000,'currency':'USD'},
 'questionnaire':{'id':id,'version':1,'published':True,'declaration_en':'New declaration','declaration_ar':'إقرار جديد'}}
history={'checkouts':[{'id':intent,'state':'pending','version':2,'timestamp':'2026-10-21T12:00:00Z'}]}
requests={'items':[request]};posts=[];errors=[];checks=[];complete_status=500;hold_action=False;held_action=None;hold_projection=False;held_projection=None;detail_reads=0
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1100})
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route_api(route):
            global held_action,held_projection,detail_reads
            url=route.request.url
            if route.request.method=='POST':
                posts.append({'url':url,'body':route.request.post_data_json})
                if hold_action and ('/delete-draft/' in url or '/withdraw/' in url):
                    held_action=route;return
                route.fulfill(status=complete_status if '/complete/' in url else 200,json={'id':intent if '/complete/' in url else id})
            elif '/requests/' in url:route.fulfill(json=requests)
            elif '/payments/' in url:route.fulfill(json=history)
            elif '/files/' in url:route.fulfill(json={'can_upload':False,'items':[],'requirements':[]})
            else:
                detail_reads+=1
                if hold_projection and detail_reads==3:
                    held_projection=route;page.evaluate("window.projectionReadPending=true");return
                route.fulfill(json=application)
        page.route('**/api/**',route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
        page.evaluate('(app)=>window.currentApplication=app',application)
        page.get_by_role('button',name='Respond to request',exact=True).click()
        page.get_by_label('Bound response question',exact=True).fill('<b>Own local response</b>')
        page.get_by_role('button',name='Checkout',exact=True).click()
        expect(page.get_by_text('Your local response has not been submitted.',exact=False)).to_be_visible()
        page.get_by_role('button',name='Keep editing',exact=True).click()
        expect(page.get_by_label('Bound response question',exact=True)).to_have_value('<b>Own local response</b>')
        assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
        page.get_by_role('button',name='Review response',exact=True).click()
        expect(page.get_by_text('<b>Own local response</b>',exact=True)).to_be_visible()
        page.get_by_role('button',name='Submit response',exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('The result is uncertain.')
        expect(page.get_by_role('button',name='Submit response',exact=True)).to_be_disabled()
        assert len(posts)==1 and posts[0]['body']=={'answers':{'Q1':'<b>Own local response</b>'},'expected_version':'a'*64}
        checks.append('Bound intake response reviews escaped answers, guards navigation/unload and locks uncertain attempt without observations or retry')
        page.get_by_role('button',name='العربية',exact=True).click();page.set_viewport_size({'width':390,'height':950})
        assert page.locator('[style]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(page.get_by_text('<b>Own local response</b>',exact=True)).to_be_visible()
        page.screenshot(path=str(OUT/'ar-response-390.png'),full_page=True,caret='initial')
        page.get_by_role('button',name='English',exact=True).click()
        checks.append('Arabic response review keeps local payload and fits mobile without inline styles')
        page.get_by_role('button',name='Checkout',exact=True).click();page.get_by_role('button',name='Discard local response',exact=True).click()
        expect(page.get_by_text('An existing payment attempt must be resolved',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Continue to secure payment',exact=True)).to_be_disabled()
        assert page.get_by_role('checkbox').count()==0
        assert page.get_by_role('button',name='Resume existing secure checkout',exact=True).count()==0
        checks.append('Actual payment history shape with pending candidate blocks fresh checkout and replacement signature when resume contract is absent')
        application['can_resume_checkout']=True;application['pending_checkout']={'id':intent,'version':2,'checkout_url':'https://checkout.stripe.com/c/pay/existing',
          'attestation':{'accepted':True,'name':'Original Signer'},'declaration_en':'Original retained declaration','declaration_ar':'الإقرار الأصلي المحفوظ'}
        page.get_by_role('button',name='Refresh existing checkout',exact=True).click()
        expect(page.get_by_text('Original retained declaration',exact=True)).to_be_visible()
        expect(page.get_by_text('Original signer: Original Signer',exact=True)).to_be_visible()
        page.get_by_role('button',name='Resume existing secure checkout',exact=True).click()
        assert page.evaluate('window.checkoutDestination')=='https://checkout.stripe.com/c/pay/existing'
        assert len(posts)==1
        history['checkouts'][0]['state']='processing'
        page.get_by_role('button',name='Refresh existing checkout',exact=True).click()
        expect(page.get_by_role('button',name='Resume existing secure checkout',exact=True)).to_have_count(0)
        checks.append('Proposed resume displays original declaration/signer and reopens only existing safe checkout; processing state removes resume without a POST')
        application['can_delete_draft']=True
        page.evaluate('(app)=>window.currentApplication=app',application)
        page.get_by_role('button',name='Lifecycle',exact=True).click()
        page.get_by_role('button',name='Delete unsubmitted draft',exact=True).click()
        assert len(posts)==1
        page.get_by_role('button',name='Cancel',exact=True).click();assert len(posts)==1
        page.get_by_role('button',name='Delete unsubmitted draft',exact=True).click()
        page.get_by_role('button',name='Confirm action',exact=True).click()
        expect(page.get_by_text('The server acknowledged your action.',exact=False)).to_be_visible()
        assert len(posts)==2 and posts[-1]['url'].endswith('/delete-draft/') and posts[-1]['body']=={'expected_version':2}
        expect(page.get_by_role('button',name='Confirm action',exact=True)).to_be_disabled()
        checks.append('Draft deletion requires explicit server capability and separate confirmation; cancel sends nothing and acknowledgement locks repeats')
        application.update(status='returned',can_delete_draft=True,can_withdraw=True)
        page.evaluate('(app)=>window.currentApplication=app',application);page.get_by_role('button',name='Lifecycle',exact=True).click()
        assert page.get_by_role('button',name='Delete unsubmitted draft',exact=True).count()==0
        page.get_by_role('button',name='Withdraw my filing',exact=True).click()
        expect(page.get_by_text('This withdraws only your filing.',exact=False)).to_be_visible()
        page.get_by_role('button',name='العربية',exact=True).click()
        assert page.locator('[style]').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.get_by_role('button',name='English',exact=True).click()
        page.get_by_role('button',name='Confirm action',exact=True).click()
        assert posts[-1]['url'].endswith('/withdraw/') and len(posts)==3
        checks.append('Returned filings never show draft deletion; withdrawal has separate retained-fee/case-effect wording and Arabic mobile confirmation')
        application.pop('can_withdraw');application.pop('can_delete_draft')
        page.evaluate('(app)=>window.currentApplication=app',application);page.get_by_role('button',name='Lifecycle',exact=True).click()
        assert page.get_by_role('button',name='Withdraw my filing',exact=True).count()==0
        checks.append('Missing lifecycle capabilities expose no destructive controls')
        application.update(status='draft',can_delete_draft=True,can_edit=True,can_submit=True,answers={'name':'Saved'})
        application['fee']['status']='waived';history['checkouts']=[]
        application['questionnaire']['definition']={'fields':[{'code':'name','type':'text','label_en':'Bound name','label_ar':'الاسم المحدد'}]}
        page.evaluate('(app)=>window.currentApplication=app',application)
        page.get_by_role('button',name='Editor',exact=True).click();page.wait_for_load_state('networkidle')
        page.get_by_role('button',name='Review answers',exact=True).click()
        page.get_by_role('checkbox',name='I have read and accept this declaration.',exact=True).check()
        page.get_by_label('Your full name',exact=False).fill('Own Signer')
        expect(page.get_by_role('button',name='Submit application',exact=True)).to_be_enabled()
        page.get_by_role('button',name='Delete unsubmitted draft',exact=True).click()
        hold_action=True
        page.get_by_role('button',name='Confirm action',exact=True).click()
        expect(page.get_by_role('button',name='Submit application',exact=True)).to_be_disabled()
        expect(page.get_by_role('button',name='Back',exact=True)).to_be_disabled()
        assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
        assert held_action is not None
        held_action.fulfill(json={'id':id});hold_action=False
        expect(page.get_by_text('The server acknowledged your action.',exact=False)).to_be_visible()
        expect(page.get_by_role('button',name='Submit application',exact=True)).to_be_disabled()
        checks.append('Combined editor blocks filing/navigation during delayed lifecycle action and keeps filing locked after acknowledgement until authoritative refresh')
        detail_reads=0;hold_projection=True
        page.get_by_role('button',name='Editor',exact=True).click()
        expect(page.get_by_label('Bound name',exact=True)).to_be_visible()
        page.wait_for_function("document.querySelector('input[type=text]')!==null")
        # Wait for the deliberately delayed read-only projection refresh to start.
        page.wait_for_function('window.projectionReadPending===true')
        assert held_projection is not None
        expect(page.get_by_label('Bound name',exact=True)).to_be_enabled()
        page.get_by_label('Bound name',exact=True).fill('Local while refreshing')
        expect(page.get_by_role('button',name='Saving…',exact=True)).to_be_disabled()
        held_projection.fulfill(json=application);hold_projection=False
        expect(page.get_by_role('button',name='Save draft',exact=True)).to_be_enabled()
        expect(page.get_by_label('Bound name',exact=True)).to_have_value('Local while refreshing')
        checks.append('Local typing survives a delayed background projection read while save and filing stay blocked until it settles')
        assert not errors,errors
        browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Prepared response/recovery/lifecycle capability fixtures; no real provider or signed release acceptance'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
