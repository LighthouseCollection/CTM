const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'); const vm = require('node:vm');
const context = {window:{}, FormData, Blob};
const path = 'static/ctm/applicant-files.js';
if (fs.existsSync(path)) vm.runInNewContext(fs.readFileSync(path,'utf8'), context);
const F = context.window.CTMApplicantFiles || {};
const req = () => ({category:'RO',context:'order-a',label_en:'Order copy',label_ar:'نسخة الأمر',required:true});

test('saved order captions bind approved labels and values to unique saved IDs',()=>{
  const app={answers:{restraining_orders:[{id:'order-a',court:'Court A',number:'A-1'}]},
    questionnaire:{definition:{fields:[{code:'restraining_orders',item_fields:[
      {code:'court',label_en:'Court',label_ar:'المحكمة'},
      {code:'number',label_en:'Case number',label_ar:'رقم القضية'}]}]}}};
  const details=F.savedOrderDetails(app);
  assert.equal(details[0].context,'order-a');assert.equal(details[0].fields[0].value,'Court A');
  assert.equal(details[0].fields[1].label_ar,'رقم القضية');
  app.answers.restraining_orders.push({...app.answers.restraining_orders[0],court:'Wrong ambiguous court'});
  assert.equal(F.savedOrderDetails(app).length,0);
  app.answers.restraining_orders.pop();delete app.questionnaire.definition.fields[0].item_fields[0].label_ar;
  assert.equal(F.savedOrderDetails(app)[0].fields.length,1);
});

test('context requirements need approved labels and per-order identity', () => {
  assert.equal(F.validRequirement(req()), true);
  for (const mutate of [r=>r.context='',r=>delete r.label_ar,r=>r.category='UNKNOWN']) {
    const r=req(); mutate(r); assert.equal(F.validRequirement(r),false);
  }
});
test('download links only expose clean current private originals', () => {
  const row={id:'11111111-1111-4111-8111-111111111111',scan_state:'clean',download_url:'/api/files/11111111-1111-4111-8111-111111111111/'};
  assert.equal(F.downloadURL(row),row.download_url);
  for (const bad of [{...row,scan_state:'pending'}, {...row,download_url:'https://evil.test/file'},
    {...row,download_url:'/api/files/22222222-2222-4222-8222-222222222222/'}])
    assert.equal(F.downloadURL(bad),null);
});
test('multipart upload preserves application/category/order context and original replacement id', async () => {
  let payload;
  const result=await F.uploadFile({applicationId:'own',requirement:req(),
    file:new Blob(['synthetic']),replacement:{attachment_id:'a',category:'RO',context:'order-a'},
    api:async(url,options)=>{assert.equal(url,'/api/files/'); payload=options.body;
      return {id:'file',scan_state:'pending'};}});
  assert.equal(payload.get('application_id'),'own');
  assert.equal(payload.get('context'),'order-a');
  assert.equal(payload.get('attachment_id'),'a');
  assert.equal(payload.get('visibility'),'own');
  assert.equal(result.scan_state,'pending');
});
test('cross-context replacement and oversized file never make a request', async () => {
  let calls=0; const api=async()=>{calls++;};
  for (const replacement of [{attachment_id:'a',category:'RO',context:'other'},
    {attachment_id:'a',category:'MC',context:'order-a'}]) {
    await assert.rejects(F.uploadFile({applicationId:'own',requirement:req(),file:new Blob(['x']),replacement,api}));
  }
  await assert.rejects(F.uploadFile({applicationId:'own',requirement:req(),file:{size:26*1024*1024},api}));
  assert.equal(calls,0);
});

test('malformed listings and duplicate attachment versions fail closed', () => {
  const row={id:'f',attachment_id:'a',category:'RO',context:'order-a',name:'Original.pdf',scan_state:'pending'};
  const listing={can_upload:true,requirements:[req()],items:[row]};
  assert.equal(F.validListing(listing),true);
  assert.equal(F.validListing({...listing,items:[null]}),false);
  assert.equal(F.validListing({...listing,items:[row,{...row,id:'older-version'}]}),false);
  assert.equal(F.validListing({...listing,requirements:[req(),req()]}),false);
});
