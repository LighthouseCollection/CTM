const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),context={window:{}};
const path='static/ctm/applicant-requests.js';
if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
const Q=context.window.CTMApplicantRequests||{};
const id='11111111-1111-4111-8111-111111111111';
const data=()=>({items:[{id,title:'Own request',kind:'intake',state:'sent',instructions:'Private instructions',language:'both',
 sent_at:'2026-10-21T12:00:00Z',questions:[{code:'Q1',version:2,en:'English wording',ar:'النص العربي'}]}]});
test('own request list rejects staff-only/draft content and malformed bound questions',()=>{
 assert.equal(Q.validProjection(data()),true);assert.equal(Q.validProjection({items:[]}),true);
 for(const mutate of [d=>d.items.push(d.items[0]),d=>d.items[0].kind='interview',d=>d.items[0].kind='external_priest',
 d=>d.items[0].state='draft',d=>d.items[0].questions[0].version=0,d=>d.items[0].questions.push(d.items[0].questions[0]),
 d=>d.items[0].sent_at=null,d=>d.items[0].language='xx',d=>d.items[0].questions[0].ar='']){
  const d=data();mutate(d);assert.equal(Q.validProjection(d),false);
 }
});
test('question wording follows bound request language without inventing translations',()=>{
 const row=data().items[0],question=row.questions[0];
 assert.equal(Q.questionText(question,row,'ar'),'النص العربي');
 row.language='en';question.ar='';assert.equal(Q.validProjection({items:[row]}),true);
 assert.equal(Q.questionText(question,row,'ar'),'English wording');
 row.language='ar';assert.equal(Q.validProjection({items:[row]}),false);
});
test('closed requests remain readable without enabling response',()=>{
 const d=data();d.items[0].state='closed';assert.equal(Q.validProjection(d),true);
 d.items[0].sent_at=null;assert.equal(Q.validProjection(d),false);
});
