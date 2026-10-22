const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};const path='static/ctm/applicant-appeals.js';
if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
const A=context.window.CTMApplicantAppeals||{};
const caseId='11111111-1111-4111-8111-111111111111',appealId='22222222-2222-4222-8222-222222222222';
test('appeal entry preserves the reopened-sibling exception',()=>{
 assert.equal(A.hasAppealContext({status:'closed',proceedings:[]}),true);
 assert.equal(A.hasAppealContext({status:'open',proceedings:[{status:'closed',kind:'initial'},{status:'open',kind:'appeal'}]}),true);
 assert.equal(A.hasAppealContext({status:'open',proceedings:[{status:'open',kind:'initial'}]}),false);
});
test('appeal creation delegates exact case and filing kind; accepts reused own appeal',async()=>{
 const starter=A.createAppealStarter(caseId,async(url,options)=>{
  assert.equal(url,'/api/applications/');assert.deepEqual(JSON.parse(options.body),{kind:'appeal',case_id:caseId});
  return {id:appealId,case_id:caseId,kind:'appeal'};
 });
 assert.equal(await starter.start(),appealId);
});
test('concurrent starts do not create overlapping requests',async()=>{
 let release,calls=0;
 const starter=A.createAppealStarter(caseId,()=>{calls++;return new Promise(resolve=>{release=resolve;});});
 const first=starter.start();assert.equal(await starter.start(),null);
 release({id:appealId,case_id:caseId,kind:'appeal'});await first;assert.equal(calls,1);
});
test('malformed or different-case acknowledgements never open an application',async()=>{
 for(const result of [{id:appealId,case_id:caseId,kind:'petition'},{id:appealId,case_id:appealId,kind:'appeal'},{}]){
  const starter=A.createAppealStarter(caseId,async()=>result);assert.equal(await starter.start(),null);
  assert.equal(starter.state.error,'failed');
 }
});
test('access failures lock further starts; eligibility rejection preserves the case view',async()=>{
 for(const status of [401,403,404,422]){
  let calls=0;const starter=A.createAppealStarter(caseId,async()=>{calls++;throw {status};});
  assert.equal(await starter.start(),null);
  assert.equal(starter.state.error,status===401?'expired':[403,404].includes(status)?'denied':'failed');
  if(status!==422){assert.equal(await starter.start(),null);assert.equal(calls,1);}
 }
});
