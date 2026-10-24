"""Own history and notification interruption fixtures against real pinned Plenix."""
import json,threading,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.tmp/applicant-history-notifications';OUT.mkdir(parents=True,exist_ok=True)
ID='11111111-1111-4111-8111-111111111111';CHILD='22222222-2222-4222-8222-222222222222';OTHER='33333333-3333-4333-8333-333333333333';CDN='https://design-system.lighthouseway.org/cdn/0.61.0/'
HTML="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css"><script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script><script src="CDNplenix.js"></script><script src="/applicant-history.js"></script><script src="/applicant-notifications.js"></script><script src="/applicant.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement,api=async(url,options={})=>{const r=await fetch(url,options);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const[lang,setLang]=R.useState('en'),[view,setView]=R.useState('History'),guard=R.useRef(null),register=R.useCallback(fn=>guard.current=fn,[]);
R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';},[lang]);const go=name=>guard.current?guard.current(()=>setView(name)):setView(name);
return h(P.ThemeProvider,null,h(P.PageContent,null,h(P.Inline,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),h(P.Button,{onClick:()=>go('History')},'History'),h(P.Button,{onClick:()=>go('Notifications')},'Notifications'),h(P.Button,{onClick:()=>go('Left')},'Leave')),
view==='History'?h(CTMApplicant.ApplicationEditor,{applicationId:'CASEID',api,lang,onBack:()=>go('Left'),onNavigationGuard:register}):view==='Notifications'?h(CTMApplicantNotifications.Inbox,{api,lang,onCase:id=>window.openedCase=id,onNavigationGuard:register}):h(P.Text,null,'Left workspace')));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>""".replace('CDN',CDN).replace('CASEID',ID)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  js=self.path in ['/applicant.js','/applicant-history.js','/applicant-notifications.js'];self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
  self.wfile.write((ROOT/('static/ctm'+self.path)).read_bytes() if js else HTML.encode())
 def log_message(self,*args):pass
first={'name':'Original <script>literal</script>','active':False,'nullable':None,'children':[{'id':CHILD,'name':'First'},{'id':OTHER,'name':'Second'}],'future':{'a/b~c':0}}
second={**first,'name':'Saved current','children':[{'id':OTHER,'name':'Second changed'},{'id':CHILD,'name':'First'}]}
history={'items':[{'id':str(uuid.uuid4()),'version':1,'answers':first,'actor':'Actual editor 1','timestamp':'2026-10-21T12:00:00Z'},{'id':str(uuid.uuid4()),'version':2,'answers':second,'actor':'Actual editor 2','timestamp':'2026-10-21T13:00:00Z'}]}
app={'id':ID,'version':2,'status':'draft','kind':'petition','can_edit':True,'answers':second,'questionnaire':{'id':'form','version':1,'published':True,'definition':{'fields':[{'code':'name','type':'text','label_en':'Current name label','label_ar':'عنوان الاسم الحالي'},{'code':'active','type':'boolean','label_en':'Current active label','label_ar':'عنوان الحالة الحالي'},{'code':'children','type':'list','label_en':'Children','label_ar':'الأطفال','item_fields':[{'code':'name','type':'text','label_en':'Child name','label_ar':'اسم الطفل'}]}]}}}
notices=[{'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'notice'+str(i))),'kind':'internal_unknown_kind','payload':{'secret':'NEVER RENDER THIS PAYLOAD'},'read':False,'timestamp':'2026-10-21T12:00:00Z','case_id':ID,'case_number':'CASE-SYNTHETIC'} for i in range(51)]
mode='false';deny_history=False;bad_history=False;deny_notices=False;bad_notices=False;held=[];posts=[];errors=[];checks=[]
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  def api(route):
   path=route.request.url
   if '/notifications/' in path:
    if route.request.method=='POST':
     payload=route.request.post_data_json;posts.append(payload);row=next(n for n in notices if n['id']==payload['id'])
     if mode=='false':route.fulfill(json={'updated':False})
     elif mode=='drop':row['read']=True;route.abort('failed')
     elif mode=='pause':held.append((route,row))
     else:row['read']=True;route.fulfill(json={'updated':True})
    else:
     if deny_notices:route.fulfill(status=403,json={});return
     offset=int(path.split('offset=')[-1]);items=notices[offset:offset+50]
     if bad_notices:items=[notices[0],notices[0]]
     route.fulfill(json={'items':items,'next_offset':offset+50 if len(notices)>offset+50 else None,'unread_count':sum(not n['read'] for n in notices)})
   elif '/history/' in path:
    route.fulfill(status=403 if deny_history else 200,json={} if deny_history else {'items':[history['items'][0],history['items'][0]]} if bad_history else history)
   else:route.fulfill(json=app)
  page.route('**/api/**',api);page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
  page.get_by_role('button',name='Current name label: /name',exact=True).click();region=page.get_by_role('dialog',name='My saved answer history',exact=True)
  expect(region.get_by_text('Recorded by: Actual editor 2',exact=True)).to_be_visible()
  expect(region.get_by_text('/name',exact=True)).to_be_visible()
  assert region.get_by_text('/children/$order',exact=True).count()==0
  region.get_by_role('button',name='Current name label: /name',exact=True).click()
  expect(region.get_by_text('/children/@'+OTHER+'/name',exact=True)).to_be_visible();expect(region.get_by_text('/children/$order',exact=True)).to_be_visible()
  assert page.locator('script').filter(has_text='Original <script>literal</script>').count()==0 and not posts
  checks.append('Own history exposes attributed saved versions and UUID-based repeat/order changes without editing originals or executing saved markup')
  region.get_by_label('Saved version',exact=True).select_option('1')
  expect(region.get_by_text('Recorded by: Actual editor 1',exact=True)).to_be_visible();expect(region.get_by_text('Historical question wording is not supplied',exact=False)).to_be_visible()
  expect(region.get_by_text('/future/a~1b~0c',exact=True)).to_be_visible()
  assert region.get_by_text('Selected saved value: false',exact=True).count()==1 and region.get_by_text('Selected saved value: null',exact=True).count()==1
  assert region.get_by_role('button',name='Download own answer history JSON',exact=True).count()==0
  region.get_by_role('button',name='Current active label: /active',exact=True).click()
  expect(region.get_by_text('Selected saved value: false',exact=True)).to_be_visible()
  checks.append('Changed-field indicators open retained values in the documented modal; absent/null/false/zero and current-label provenance remain distinct')
  page.keyboard.press('Escape')
  expect(page.get_by_role('button',name='Current name label: /name',exact=True).first).to_be_focused()
  page.get_by_role('textbox',name='Current name label',exact=True).fill('Local unsaved name');page.get_by_role('button',name='View saved answer history',exact=True).click();region.get_by_role('button',name='Refresh answer history',exact=True).click()
  expect(region.get_by_text('Recorded by: Actual editor 2',exact=True)).to_be_visible();expect(page.get_by_role('textbox',name='Current name label',exact=True)).to_have_value('Local unsaved name')
  page.keyboard.press('Escape');page.get_by_role('button',name='العربية',exact=True).click();page.get_by_role('button',name='عرض سجل الإجابات المحفوظة',exact=True).click();page.set_viewport_size({'width':390,'height':1000})
  expect(page.get_by_role('textbox',name='عنوان الاسم الحالي',exact=True)).to_have_value('Local unsaved name')
  assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.get_by_role('dialog',name='سجل إجاباتي المحفوظة',exact=True).screenshot(path=str(OUT/'ar-history-390.png'),caret='initial')
  page.keyboard.press('Escape');page.get_by_role('button',name='English',exact=True).click();page.get_by_role('button',name='View saved answer history',exact=True).click();checks.append('History refresh/language switching preserves dirty editor input and ENAR mobile layout without inline styles or overflow')
  deny_history=True;region.get_by_role('button',name='Refresh answer history',exact=True).click();expect(region.get_by_text('Saved answer history is unavailable',exact=False)).to_be_visible()
  assert region.get_by_text('Recorded by: Actual editor 2',exact=True).count()==0
  deny_history=False;bad_history=True;region.get_by_role('button',name='Refresh answer history',exact=True).click();expect(region.get_by_text('Saved answer history is unavailable',exact=False)).to_be_visible()
  expect(page.get_by_role('textbox',name='Current name label',exact=True)).to_have_value('Local unsaved name')
  page.keyboard.press('Escape');page.get_by_role('button',name='Notifications',exact=True).click();page.get_by_role('button',name='Discard unsaved changes',exact=True).click()
  checks.append('Denied/malformed history clears private snapshots while local draft/navigation guard remains intact')
  expect(page.get_by_role('button',name='Load more notifications',exact=True)).to_be_visible();assert page.get_by_text('NEVER RENDER THIS PAYLOAD',exact=False).count()==0
  page.get_by_role('button',name='Load more notifications',exact=True).click();expect(page.get_by_role('button',name='Load more notifications',exact=True)).to_have_count(0)
  assert page.get_by_role('button',name='Mark notification as read',exact=True).count()==51 and not posts
  page.get_by_role('button',name='Open case',exact=True).first.click();assert page.evaluate('window.openedCase')==ID
  checks.append('Notification inbox loads bounded pages, displays generic case update metadata, opens normal case route and never renders private payload internals')
  page.get_by_role('button',name='Mark notification as read',exact=True).first.click();expect(page.get_by_text('Read status was not confirmed.',exact=False)).to_be_visible()
  assert page.get_by_text('Read',exact=True).count()==0 and len(posts)==1
  page.get_by_role('button',name='Refresh notifications',exact=True).click();mode='drop';page.get_by_role('button',name='Mark notification as read',exact=True).first.click()
  expect(page.get_by_text('Acknowledgement was not confirmed.',exact=False)).to_be_visible();assert len(posts)==2
  page.get_by_role('button',name='Refresh notifications',exact=True).click();expect(page.get_by_text('Read',exact=True)).to_be_visible();assert len(posts)==2
  checks.append('False acknowledgement never marks a notice read; committed lost acknowledgement recovers only from explicit authoritative refresh without retry')
  mode='pause';page.get_by_role('button',name='Mark notification as read',exact=True).first.click();expect(page.get_by_role('button',name='Refresh notifications',exact=True)).to_be_disabled()
  page.get_by_role('button',name='Leave',exact=True).click();assert page.get_by_text('Left workspace',exact=True).count()==0 and len(held)==1
  assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
  held[0][1]['read']=True;held[0][0].fulfill(json={'updated':True});expect(page.get_by_role('button',name='Refresh notifications',exact=True)).to_be_enabled()
  assert page.get_by_text('Unread notifications:',exact=False).count()==0
  checks.append('Delayed acknowledgement blocks navigation/competing controls and unload; unread count is withheld until refreshed rather than decremented speculatively')
  page.get_by_role('button',name='العربية',exact=True).click();assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(OUT/'ar-notices-390.png'),full_page=True,caret='initial');page.get_by_role('button',name='English',exact=True).click()
  deny_notices=True;page.get_by_role('button',name='Refresh notifications',exact=True).click();expect(page.get_by_text('Notifications are unavailable',exact=False)).to_be_visible()
  assert page.get_by_role('button',name='Open case',exact=True).count()==0
  deny_notices=False;bad_notices=True;page.get_by_role('button',name='Refresh notifications',exact=True).click();expect(page.get_by_text('Notifications are unavailable',exact=False)).to_be_visible()
  assert page.get_by_role('button',name='Mark notification as read',exact=True).count()==0 and len(posts)==3
  checks.append('Notification ENAR layout remains clean; denied/malformed refresh removes private list/count/case actions and never resends acknowledgement')
  assert not errors,errors;browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Synthetic own history/notification fixtures; pinned real Plenix0.61.0'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
