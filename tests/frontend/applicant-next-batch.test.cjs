const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const context={window:{},URL,structuredClone};
for(const name of ['responses','recovery','lifecycle']){
 const path=`static/ctm/applicant-${name}.js`;
 if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
}
const id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222';
const response=()=>({id,kind:'intake',state:'sent',can_respond:true,proceeding_id:other,request_version:"a".repeat(64),
 language:'both',questions:[{code:'Q1',version:1,en:'Question',ar:'السؤال'}]});
test('response controller requires explicit capability and freezes uncertain response without retry',async()=>{
 const Q=context.window.CTMApplicantResponses;const row=response();let calls=0,payload;
 assert.equal(Q.canRespond(row),true);assert.equal(Q.canRespond({...row,can_respond:undefined}),false);
 assert.equal(Q.canRespond({...row,kind:'medical'}),false);
 const session=Q.createResponseSession(row,async(url,options)=>{calls++;payload=JSON.parse(options.body);throw Error('lost');});
 assert.equal(await session.send({Q1:'Own answer'}),false);
 assert.equal(payload.expected_version,"a".repeat(64));assert.deepEqual(payload.answers,{Q1:'Own answer'});
 assert.equal('observations' in payload,false);assert.equal(session.state.error,'uncertain');
 await session.send({Q1:'Changed'});assert.equal(calls,1);
});
test('response only sends bound question keys and accepts a report acknowledgement once',async()=>{
 const Q=context.window.CTMApplicantResponses;let calls=0;
 const s=Q.createResponseSession(response(),async()=>{calls++;return {id:other};});
 assert.equal(await s.send({unbound:'Wrong'}),false);assert.equal(calls,0);
 // Existing complete endpoint acknowledges the new report, not the request.
 assert.equal(await s.send({Q1:'Answer'}),true);assert.equal(s.state.received,true);
 await s.send({Q1:'Again'});assert.equal(calls,1);
});
const history=(state='pending')=>({checkouts:[{id:other,state,version:2,timestamp:'2026-10-21T12:00:00Z'}]});
const candidate=()=>({id,version:2,status:'draft',can_resume_checkout:true,pending_checkout:{id:other,version:2,
 checkout_url:'https://checkout.stripe.com/c/pay/test',expires_at:new Date(Date.now()+3600000).toISOString(),attestation:{accepted:true,name:'Original Name'},
 declaration_en:'Original declaration',declaration_ar:'الإقرار الأصلي'}});
test('checkout history blocks fresh payment on unresolved or unknown candidates and missing history',()=>{
 const C=context.window.CTMApplicantRecovery;
 for(const state of ['pending','processing','paid','needs_review','future'])assert.equal(C.blocksNewCheckout(history(state)),true);
 assert.equal(C.blocksNewCheckout({}),true);assert.equal(C.blocksNewCheckout({checkouts:[]}),false);
 assert.equal(C.blocksNewCheckout(history('finalized')),false);
});
test('checkout resume requires same pending candidate/version, explicit permission and exact safe provider host',()=>{
 const C=context.window.CTMApplicantRecovery;assert.equal(C.resumeURL(candidate(),history()),'https://checkout.stripe.com/c/pay/test');
 for(const mutate of [d=>delete d.can_resume_checkout,d=>d.pending_checkout.id=id,d=>d.pending_checkout.version=1,
 d=>d.pending_checkout.attestation.accepted=false,d=>d.pending_checkout.declaration_ar='',
 d=>d.pending_checkout.checkout_url='https://checkout.stripe.com.evil.example/c/test']){
  const d=candidate();mutate(d);assert.equal(C.resumeURL(d,history()),null);
 }
 assert.equal(C.resumeURL(candidate(),history('processing')),null);
 const unknown=history();unknown.checkouts.push({id,version:2,state:'future',timestamp:'2026-10-21T12:00:00Z'});
 assert.equal(C.resumeURL(candidate(),unknown),null);
});
test('lifecycle capabilities never infer withdrawal/delete from status or allow returned draft deletion',async()=>{
 const L=context.window.CTMApplicantLifecycle;
 const app={id,version:2,kind:'petition',status:'draft',can_delete_draft:true};
 assert.equal(L.actionScope(app),L.actionScope({...app}));
 assert.notEqual(L.actionScope(app),L.actionScope({...app,version:3}));
 assert.notEqual(L.actionScope(app),L.actionScope({...app,can_delete_draft:false}));
 assert.equal(L.available(app,'delete'),true);assert.equal(L.available({...app,status:'returned'},'delete'),false);
 assert.equal(L.available({...app,can_delete_draft:undefined},'delete'),false);
 assert.equal(L.available({...app,status:'submitted',can_withdraw:true},'withdraw'),true);
 let calls=0;const s=L.createActionSession(app,async(url,options)=>{calls++;assert.deepEqual(JSON.parse(options.body),{expected_version:2});return {id};});
 assert.equal(await s.send('delete',false),false);assert.equal(calls,0);
 assert.equal(await s.send('delete',true),true);await s.send('delete',true);assert.equal(calls,1);
});
test('uncertain lifecycle operation locks repeats and wrong acknowledgement never claims completion',async()=>{
 const L=context.window.CTMApplicantLifecycle;let calls=0;
 const s=L.createActionSession({id,version:2,kind:'appeal',status:'submitted',can_withdraw:true},async()=>{calls++;return {id:other};});
 assert.equal(await s.send('withdraw',true),false);assert.equal(s.state.error,'uncertain');
 await s.send('withdraw',true);assert.equal(calls,1);
});


test('retained checkout requires a future explicit provider expiry and rejects raw URL controls',()=>{
 const C=context.window.CTMApplicantRecovery,now=Date.now();
 const app=candidate();app.pending_checkout.expires_at=new Date(now+60000).toISOString();
 assert.ok(C.resumeURL(app,history(),now));
 for(const value of [undefined,'invalid','2030-01-01T10:00:00',new Date(now).toISOString(),new Date(now-1).toISOString()]){
  const changed=structuredClone(app);changed.pending_checkout.expires_at=value;
  assert.equal(C.resumeURL(changed,history(),now),null);
 }
 for(const url of ['https://checkout.stripe.com/\nunsafe',' https://checkout.stripe.com/x','https://checkout.stripe.com/with space']){
  const changed=structuredClone(app);changed.pending_checkout.checkout_url=url;
  assert.equal(C.resumeURL(changed,history(),now),null);
 }
 assert.equal(C.resumeURL(app,history(),now+60000),null);
});

test('owner lifecycle confirmation must be a literal explicit acceptance',async()=>{
 const L=context.window.CTMApplicantLifecycle;let calls=0;
 const app={id,version:2,kind:'petition',status:'draft',can_delete_draft:true};
 const s=L.createActionSession(app,async()=>{calls++;return {id};});
 for(const value of ['true',1,{},null,false])assert.equal(await s.send('delete',value),false);
 assert.equal(calls,0);assert.equal(await s.send('delete',true),true);
});
