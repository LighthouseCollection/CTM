"""Five repeat-family UI fixtures. Technical bindings/wording are NOT approved content."""
import copy,hashlib,json,subprocess,threading,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.tmp/applicant-repeat-sections';OUT.mkdir(parents=True,exist_ok=True)
MODULE=(ROOT/'static/ctm/applicant.js').read_bytes()
SOURCE_SHA=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
CDN='https://design-system.lighthouseway.org/cdn/0.58.0/'
HTML="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="CDNtheme-boot.js"></script><link rel="stylesheet" href="CDNfonts.css"><link rel="stylesheet" href="CDNplenix.css">
<script src="CDNvendor/react.production.min.js"></script><script src="CDNvendor/react-dom.production.min.js"></script><script src="CDNplenix.js"></script><script src="/applicant.js"></script></head><body><div id="root"></div><script>
const R=React,P=Plenix,h=R.createElement,api=async(url,options={})=>{const r=await fetch(url,options);if(!r.ok)throw {status:r.status};return r.json();};
function Harness(){const[lang,setLang]=R.useState('en');R.useEffect(()=>{document.documentElement.dir=lang==='ar'?'rtl':'ltr';document.documentElement.lang=lang;},[lang]);
return h(P.ThemeProvider,null,h(P.PageContent,null,h(P.Button,{onClick:()=>setLang(lang==='en'?'ar':'en')},lang==='en'?'العربية':'English'),h(CTMApplicant.ApplicationEditor,{applicationId:'fixture-repeat-app',api,lang,onBack:()=>{window.left=true;}})));}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));</script></body></html>""".replace('CDN',CDN)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  js=self.path=='/applicant.js';self.send_response(200);self.send_header('Content-Type','text/javascript' if js else 'text/html; charset=utf-8');self.end_headers();self.wfile.write(MODULE if js else HTML.encode())
 def log_message(self,*args):pass
families={'children':[('first_name','text'),('last_name','text'),('birth_date','date'),('gender','choice'),('lives_with','choice')],
 'restraining_orders':[('court','text'),('number','text'),('status','choice')],
 'prior_applications':[('record_date','date'),('council_or_diocese','text'),('outcome','text')],
 'prior_marriages':[('spouse_name','text'),('ecclesiastical_permit','text')],
 'counseling_priests':[('priest_name','text')]}
# These bindings are isolated technical fixtures, never a deployable publication payload.
def label(code,lang='en'):return ('Fixture ' if lang=='en' else 'حقل تجريبي ')+code
fields=[];answers={'unmapped_root':{'keep':[False,None,0,'source']}}
for family,children in families.items():
 item=[]
 for code,kind in children:
  field={'code':code,'type':kind,'label_en':label(family+'.'+code),'label_ar':label(family+'.'+code,'ar')}
  if kind=='choice':field['choices']=[{'value':'unknown' if family=='children' else 'active','label_en':'Fixture option','label_ar':'خيار تجريبي'}]
  item.append(field)
 fields.append({'code':family,'type':'list','label_en':label(family),'label_ar':label(family,'ar'),'item_fields':item})
 rows=[]
 for index in range(2):
  row={'id':str(uuid.uuid4()),'opaque':{'keep':[False,None,0], 'source_row':index}}
  for code,kind in children:row[code]='2010-01-02' if kind=='date' else ('unknown' if family=='children' else 'active') if kind=='choice' else 'Original '+family+' '+str(index)
  rows.append(row)
 answers[family]=rows
app={'id':'fixture-repeat-app','version':0,'status':'draft','can_edit':True,'answers':answers,'questionnaire':{'id':'fixture-not-approved','version':1,'published':True,'definition':{'fields':fields}}}
original=copy.deepcopy(app);writes=[];fail=False;errors=[];checks=[]
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1280,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
  def route_api(route):
   global app
   if route.request.method=='GET':route.fulfill(json=app);return
   payload=route.request.post_data_json;writes.append(payload)
   if fail:route.abort('failed');return
   assert payload['expected_version']==app['version'];app={**app,'version':app['version']+1,'answers':copy.deepcopy(payload['answers'])};route.fulfill(status=201,json={'version':app['version']})
  page.route('**/api/**',route_api);page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='networkidle')
  for family,children in families.items():
   region=page.get_by_role('region',name=label(family),exact=True)
   first,kind=children[0];region.get_by_label(label(family+'.'+first),exact=True).first.fill('2020-03-04' if kind=='date' else 'Corrected '+family)
   region.get_by_role('button',name='Add another entry',exact=True).click()
   for code,kind in children:
    control=region.get_by_label(label(family+'.'+code),exact=True).nth(2)
    if kind=='choice':control.select_option('unknown' if family=='children' else 'active')
    else:control.fill('2021-04-05' if kind=='date' else 'New '+family+' '+code)
  fail=True;page.get_by_role('button',name='Save draft',exact=True).click()
  expect(page.get_by_text('Your changes were not saved.',exact=False)).to_be_visible();assert len(writes)==1 and app['answers']==original['answers']
  frozen=copy.deepcopy(writes[0]['answers'])
  page.get_by_role('button',name='العربية',exact=True).click();page.set_viewport_size({'width':390,'height':1000})
  for family,children in families.items():
   region=page.get_by_role('region',name=label(family,'ar'),exact=True);code,kind=children[0]
   expect(region.get_by_label(label(family+'.'+code,'ar'),exact=True).first).to_have_value('2020-03-04' if kind=='date' else 'Corrected '+family)
  assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(OUT/'ar-five-repeats-390.png'),full_page=True,caret='initial')
  checks.append('Failed save retains all five locally edited repeat families; Arabic390px/language switch preserves values without styles or overflow and performs no automatic retry')
  fail=False;page.get_by_role('button',name='حفظ المسودة',exact=True).click();expect(page.get_by_text('تم حفظ إجاباتك.',exact=True)).to_be_visible()
  assert writes[-1]['answers']==frozen and len(writes)==2 and app['answers']['unmapped_root']==original['answers']['unmapped_root']
  for family,children in families.items():
   saved=app['answers'][family]
   assert len(saved)==3 and saved[0]['id']==original['answers'][family][0]['id'] and saved[0]['opaque']==original['answers'][family][0]['opaque']
   assert saved[1]==original['answers'][family][1]
   assert saved[2]['id'] not in [r['id'] for r in original['answers'][family]] and str(uuid.UUID(saved[2]['id']))==saved[2]['id']
   for code,kind in children:
    expected='2021-04-05' if kind=='date' else ('unknown' if family=='children' else 'active') if kind=='choice' else 'New '+family+' '+code
    assert saved[2][code]==expected
   for code,kind in children[1:]:assert saved[0][code]==original['answers'][family][0][code]
   checks.append(family+': edit/add persists current UUID and opaque originals, leaves untouched row/fields exact and allocates a distinct UUID for new row')
  page.get_by_role('button',name='مراجعة الإجابات',exact=True).click();assert '[object Object]' not in page.locator('body').inner_text()
  page.get_by_role('button',name='متابعة التعديل',exact=True).click()
  keep={family:copy.deepcopy(app['answers'][family][::2]) for family in families}
  for family in families:page.get_by_role('region',name=label(family,'ar'),exact=True).get_by_role('button',name='إزالة هذا السجل',exact=True).nth(1).click()
  page.get_by_role('button',name='حفظ المسودة',exact=True).click();expect(page.get_by_text('تم حفظ إجاباتك.',exact=True)).to_be_visible()
  for family in families:assert app['answers'][family]==keep[family]
  assert app['answers']['unmapped_root']==original['answers']['unmapped_root']
  page.reload(wait_until='networkidle')
  for family in families:
   region=page.get_by_role('region',name=label(family),exact=True)
   assert region.get_by_role('button',name='Remove this entry',exact=True).count()==2
   for index,row in enumerate(keep[family]):
    for code,kind in families[family]:expect(region.get_by_label(label(family+'.'+code),exact=True).nth(index)).to_have_value(row[code])
   assert app['answers'][family]==keep[family]
  checks.append('Arabic review/remove/save/reload across all five families retains surviving UUIDs and exact unmapped source values; no object coercion')
  retained=copy.deepcopy(app['answers']);del app['questionnaire']['definition']['fields'][0]['item_fields'][0]['label_ar']
  page.reload(wait_until='networkidle');expect(page.get_by_text('The approved application form is not available.',exact=False)).to_be_visible()
  assert app['answers']==retained and len(writes)==3
  checks.append('Missing nested Arabic label blocks form editing without inventing wording or mutating saved snapshots')
  assert not errors,errors;browser.close()
finally:server.shutdown()
result={'source_commit':SOURCE_SHA,'module_sha256':hashlib.sha256(MODULE).hexdigest(),'passed':len(checks),'checks':checks,'page_errors':errors,'scope':'Five-family synthetic UI fixtures with pinned Plenix0.58.0; not approved content, document evidence or backend validation acceptance','families':list(families)}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
