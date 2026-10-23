"""Private message interruption fixtures using the pinned real Plenix CDN."""
import json,threading,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.tmp/applicant-messages';OUT.mkdir(parents=True,exist_ok=True)
ID='11111111-1111-4111-8111-111111111111';PARTY='22222222-2222-4222-8222-222222222222'
CDN='https://design-system.lighthouseway.org/cdn/0.61.0/'
HTML="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script><script src="CDNplenix.js"></script>
<script src="/applicant-messages.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement;const api=async(url,options={})=>{const r=await fetch(url,options);if(!r.ok)throw{status:r.status};return r.json();};
function Harness(){const[lang,setLang]=R.useState('en'),[left,setLeft]=R.useState(false),guard=R.useRef(null);const register=R.useCallback(fn=>guard.current=fn,[]);
R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';},[lang]);
return h(P.ThemeProvider,null,h(P.PageContent,null,h(P.Inline,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),h(P.Button,{onClick:()=>guard.current?guard.current(()=>setLeft(true)):setLeft(true)},'Leave')),
left?h(P.Text,null,'Left thread'):h(CTMApplicantMessages.Thread,{caseId:'CASEID',api,lang,onNavigationGuard:register})));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>""".replace('CDN',CDN).replace('CASEID',ID)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  js=self.path=='/applicant-messages.js';self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers()
  self.wfile.write((ROOT/'static/ctm/applicant-messages.js').read_bytes() if js else HTML.encode())
 def log_message(self,*args):pass
record={'id':ID,'can_message':True,'parties':[{'id':PARTY,'is_self':True}]}
def message(n,body=None,key=None):return {'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'message'+str(n))),'body':body or f'Private message {n}','sender':'Council <safe>',
 'channel':'portal','timestamp':'2026-10-21T12:00:00Z','file_links':[],'idempotency_key':key,'receipts':[{'party_id':PARTY,'read_at':None}]}
rows=[message(n) for n in range(51)];writes=[];reads=[];checks=[];errors=[];mode='lost';read_mode='ok';held=[];deny=False;bad_page=False
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  def api(route):
   path=route.request.url
   if route.request.method=='GET':
    if deny:route.fulfill(status=403,json={});return
    if '/messages/' in path:
     offset=int(path.split('offset=')[-1]);items=rows[offset:offset+50]
     if bad_page:items=[rows[0],rows[0]]
     route.fulfill(json={'items':items,'next_offset':offset+50 if len(rows)>offset+50 else None})
    else:route.fulfill(json=record)
   elif path.endswith('/read/'):
    reads.append(route.request.post_data_json)
    if read_mode=='drop':route.abort('failed');return
    row=next(r for r in rows if '/'+r['id']+'/' in path);row['receipts'][0]['read_at']='2026-10-21T14:00:00Z'
    route.fulfill(json={'id':row['id'],'read_at':row['receipts'][0]['read_at']})
   else:
    payload=route.request.post_data_json;writes.append(payload)
    if mode=='drop':route.abort('failed');return
    row=message(100+len(writes),payload['body'],payload['idempotency_key']);rows.append(row)
    if mode=='pause':held.append((route,row));return
    if mode=='lost':route.abort('failed')
    else:route.fulfill(status=201,json={'id':row['id']})
  page.route('**/api/**',api);page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
  expect(page.get_by_text('Private message 49',exact=True)).to_be_visible();assert page.get_by_text('Private message 50',exact=True).count()==0
  assert not reads and not writes
  page.get_by_role('button',name='Load more messages',exact=True).click();expect(page.get_by_text('Private message 50',exact=True)).to_be_visible()
  assert page.get_by_role('button',name='Load more messages',exact=True).count()==0
  checks.append('Bound own receipt history loads 50-row pages explicitly with no automatic read or send mutation')
  page.get_by_role('button',name='Mark my copy as read',exact=True).first.click()
  expect(page.get_by_text('2026-10-21T14:00:00Z',exact=True)).to_be_visible();assert reads==[{}]
  checks.append('Explicit own-copy acknowledgement sends empty body and displays portal read time separately from email delivery')
  read_mode='drop';page.get_by_role('button',name='Mark my copy as read',exact=True).first.click()
  expect(page.get_by_text('Read acknowledgement was not confirmed.',exact=False)).to_be_visible()
  read_mode='ok';page.get_by_role('button',name='Refresh thread',exact=True).click()
  expect(page.get_by_role('button',name='Mark my copy as read',exact=True).first).to_be_enabled()
  page.get_by_role('button',name='Mark my copy as read',exact=True).first.click();assert len(reads)==3
  checks.append('Uncertain read action never repeats automatically; explicit authoritative refresh permits a new intended-copy acknowledgement')
  page.get_by_label('Your message',exact=True).fill('<script>Own frozen message</script>')
  page.get_by_role('button',name='Leave',exact=True).click();expect(page.get_by_text('Your local message has not been confirmed.',exact=False)).to_be_visible()
  page.get_by_role('button',name='Keep editing',exact=True).click()
  assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
  page.get_by_role('button',name='Review message',exact=True).click();page.get_by_role('button',name='Send private message',exact=True).click()
  expect(page.get_by_text('Sending was not confirmed.',exact=False)).to_be_visible();assert len(writes)==1
  page.get_by_role('button',name='Refresh thread',exact=True).click();expect(page.get_by_role('button',name='Load more messages',exact=True)).to_be_visible()
  assert page.get_by_role('button',name='Start a new message',exact=True).count()==0
  page.get_by_role('button',name='Load more messages',exact=True).click();expect(page.get_by_text('The server received your message.',exact=True)).to_be_visible()
  assert len(writes)==1 and writes[0]['party_ids']==[PARTY] and writes[0]['channel']=='portal' and writes[0]['email_timing']=='immediate'
  checks.append('Dirty message guards navigation/unload; lost acknowledgement recovers matching own key after explicit continuation without another send')
  page.get_by_role('button',name='Start a new message',exact=True).click();mode='drop'
  page.get_by_label('Your message',exact=True).fill('Original retry');page.get_by_role('button',name='Review message',exact=True).click();page.get_by_role('button',name='Send private message',exact=True).click()
  expect(page.get_by_text('Sending was not confirmed.',exact=False)).to_be_visible();page.get_by_role('button',name='Refresh thread',exact=True).click()
  expect(page.get_by_role('button',name='Retry original message',exact=True)).to_be_visible();mode='ack';page.get_by_role('button',name='Retry original message',exact=True).click()
  expect(page.get_by_text('The server received your message.',exact=True)).to_be_visible();assert writes[-1]==writes[-2] and len(writes)==3
  checks.append('Uncommitted uncertainty permits only explicit original replay with unchanged key/text/recipient/routing')
  page.get_by_role('button',name='Refresh thread',exact=True).click();page.get_by_role('button',name='Start a new message',exact=True).click()
  mode='pause';page.get_by_label('Your message',exact=True).fill('Delayed own message')
  page.get_by_role('button',name='Review message',exact=True).click();page.get_by_role('button',name='Leave',exact=True).click()
  page.get_by_role('button',name='Send private message',exact=True).click()
  expect(page.get_by_role('button',name='Discard local message',exact=True)).to_be_disabled()
  page.get_by_role('button',name='Leave',exact=True).click();assert page.get_by_text('Left thread',exact=True).count()==0
  assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
  assert len(held)==1
  held[0][0].fulfill(status=201,json={'id':held[0][1]['id']})
  expect(page.get_by_text('The server received your message.',exact=True)).to_be_visible()
  page.get_by_role('button',name='Keep editing',exact=True).click();page.get_by_role('button',name='Refresh thread',exact=True).click()
  page.get_by_role('button',name='Start a new message',exact=True).click()
  checks.append('Pending discard and route navigation are blocked through a delayed message write, with unload protection and exact acknowledgement')
  page.get_by_label('Your message',exact=True).fill('Local Arabic switch')
  page.get_by_role('button',name='العربية',exact=True).click();page.set_viewport_size({'width':390,'height':1000})
  expect(page.get_by_label('رسالتك',exact=True)).to_have_value('Local Arabic switch')
  assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(OUT/'ar-message-390.png'),full_page=True,caret='initial');page.get_by_role('button',name='English',exact=True).click()
  checks.append('EN/AR message draft persists with escaped history and mobile RTL without inline styles or overflow')
  deny=True;page.get_by_role('button',name='Refresh thread',exact=True).click();expect(page.get_by_text('This private thread is unavailable.',exact=False)).to_be_visible()
  assert page.get_by_text('Private message 0',exact=True).count()==0 and len(writes)==4
  assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
  deny=False;page.get_by_role('button',name='Refresh thread',exact=True).click();expect(page.get_by_label('Your message',exact=True)).to_have_value('Local Arabic switch')
  bad_page=True;page.get_by_role('button',name='Refresh thread',exact=True).click();expect(page.get_by_text('This private thread is unavailable.',exact=False)).to_be_visible()
  assert page.get_by_text('Private message 0',exact=True).count()==0
  checks.append('Denied or malformed refresh clears private history and capabilities while local message intent/guards survive; no automatic retry')
  assert not errors,errors;browser.close()
finally:server.shutdown()
result={'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Synthetic message API interruption fixtures, real Plenix0.61.0'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
