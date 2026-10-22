const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Form {constructor(){this.values=[];}append(...args){this.values.push(args);}}
const context={window:{},structuredClone,FormData:Form};
for(const name of ['assessments','responses']){
 const path=`static/ctm/applicant-${name}.js`;if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
}
const A=context.window.CTMApplicantAssessments||{},Q=context.window.CTMApplicantResponses;
const id='11111111-1111-4111-8111-111111111111',proc='22222222-2222-4222-8222-222222222222',file='33333333-3333-4333-8333-333333333333';
const version='a'.repeat(64);
const row=()=>({id,proceeding_id:proc,request_version:version,kind:'medical',state:'sent',can_respond:false,can_upload:true,
 can_sign_release:true,language:'both',questions:[],release_status:'none',signed_releases:[],response:null,
 release_definition:{id:proc,version:1,definition:{},declaration_en:'Exact supplied release',declaration_ar:'التفويض المحدد'}});
const evidence=(purpose='consent')=>({id:file,attachment_id:proc,category:purpose==='consent'?'CONSENT':'MED',purpose,
 name:'Evidence.pdf',version:1,scan_state:'clean',download_url:`/api/files/${file}/`});
test('actual response identity is an opaque request fingerprint, never an inferred answer version',()=>{
 const request={...row(),kind:'intake',can_respond:true,questions:[{code:'Q',version:1,en:'Question',ar:'السؤال'}]};
 assert.equal(Q.canRespond(request),true);assert.equal(Q.canRespond({...request,request_version:undefined,response_version:2}),false);
});
test('request files must match request/proceeding/fingerprint and never link unsafe originals',()=>{
 const request=row(),listing={request_id:id,proceeding_id:proc,request_version:version,can_upload:true,items:[evidence()]};
 assert.equal(A.validFiles(listing,request),true);
 assert.equal(A.validFiles({...listing,request_version:'b'.repeat(64)},request),false);
 listing.items[0].scan_state='pending';assert.equal(A.safeURL(listing.items[0]),null);
 assert.equal(A.validFiles(listing,request),false);delete listing.items[0].download_url;
 assert.equal(A.validFiles(listing,request),true);
});
test('assessment completion requires retained exact-purpose consent, explicit response capability and report evidence',()=>{
 const request=row();request.can_respond=true;
 assert.equal(Q.canRespond(request),false);
 request.signed_releases=[{id:proc,declaration_id:proc,signature_file_id:file,signed_at:'2026-10-21T12:00:00Z',
  scope:{council:true,purpose:'medical',request_id:id,proceeding_id:proc}}];request.release_status='signed';
 assert.equal(Q.canRespond(request),true);
 request.signed_releases[0].scope.purpose='psychological';assert.equal(Q.canRespond(request),false);
});
test('consent signing requires literal acceptance, exact bound declaration and safe consent-purpose file; uncertainty freezes retries',async()=>{
 const request=row();let calls=0,body;
 const session=A.createConsentSession(request,async(url,options)=>{calls++;body=JSON.parse(options.body);throw Error('lost');});
 assert.equal(await session.sign(evidence(),false),false);assert.equal(calls,0);
 assert.equal(await session.sign(evidence('report'),true),false);assert.equal(calls,0);
 assert.equal(await session.sign(evidence(),true),false);
 assert.deepEqual(body,{expected_version:version,declaration_id:proc,accepted:true,file_id:file,scope:{council:true}});
 assert.equal(session.state.error,'uncertain');await session.sign(evidence(),true);assert.equal(calls,1);
});
test('request uploads send only request binding and purpose category; own context is not guessed',async()=>{
 let payload;await A.uploadRequestFile(row(),{name:'signed.pdf',size:30},'consent',async(url,options)=>{payload=options.body;return {id:file};});
 const values=Object.fromEntries(payload.values.map(([key,value])=>[key,value]));
 assert.equal(values.request_id,id);assert.equal(values.expected_request_version,version);assert.equal(values.category,'CONSENT');
 assert.equal('case_id' in values,false);assert.equal('application_id' in values,false);
 await assert.rejects(()=>A.uploadRequestFile({...row(),can_upload:false},{name:'x.pdf',size:30},'report',async()=>{}));
});
test('lost consent acknowledgement recovers only from matching retained declaration, original and scope',async()=>{
 const request=row(),session=A.createConsentSession(request,async()=>{throw Error('lost');});await session.sign(evidence(),true);
 const signed={...request,release_status:'signed',signed_releases:[{id:proc,declaration_id:proc,signature_file_id:file,
  signed_at:'2026-10-21T12:00:00Z',scope:{council:true,purpose:'medical',request_id:id,proceeding_id:proc}}]};
 assert.equal(session.reconcile({...signed,signed_releases:[{...signed.signed_releases[0],signature_file_id:proc}]}),false);
 assert.equal(session.reconcile(signed),true);assert.equal(session.state.recovered,true);assert.equal(session.state.error,null);
});
test('response refuses missing questions, consent as report evidence and changed request identity',async()=>{
 const request={...row(),kind:'intake',can_respond:true,questions:[{code:'Q',version:1,en:'Question',ar:'السؤال'}]};let calls=0;
 const session=Q.createResponseSession(request,async()=>{calls++;return {id:proc};});
 assert.equal(await session.send({Q:''}),false);
 assert.equal(await session.send({Q:'Answer',files:[file]},request,[evidence()]),false);
 assert.equal(await session.send({Q:'Answer',files:false}),false);
 assert.equal(await session.send({Q:'Answer'},{...request,request_version:'b'.repeat(64)}),false);
 assert.equal(calls,0);assert.equal(await session.send({Q:'Answer',files:[file]},request,[evidence('report')]),true);
});
