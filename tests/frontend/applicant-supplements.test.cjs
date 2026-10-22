const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');const context={window:{}};
const path='static/ctm/applicant-supplements.js';if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
const S=context.window.CTMApplicantSupplements||{};
const id='11111111-1111-4111-8111-111111111111',fileId='22222222-2222-4222-8222-222222222222';
const app=()=>({id,kind:'appeal',status:'submitted',can_supplement:true,supplements:[]});
const files=()=>[{id:fileId,name:'Evidence.pdf',scan_state:'clean',download_url:`/api/files/${fileId}/`}];
test('own supplement history requires an explicit server capability and unique attributed entries',()=>{
 assert.equal(S.validProjection(app()),true);const missing=app();delete missing.can_supplement;
 assert.equal(S.validProjection(missing),false);
 const row={id:fileId,text:'Earlier information',actor:'Applicant',timestamp:'2026-10-21T12:00:00Z',manifest:[]};
 assert.equal(S.validProjection({...app(),supplements:[row]}),true);
 assert.equal(S.validProjection({...app(),supplements:[row,row]}),false);
});
test('append freezes exact text/evidence and cannot be resent after acknowledgement',async()=>{
 let calls=0;const session=S.createSupplementSession(async(url,options)=>{
  calls++;assert.equal(url,`/api/appeals/${id}/additions/`);
  assert.deepEqual(JSON.parse(options.body),{text:'New information',file_ids:[fileId]});return{id:fileId};
 });
 assert.equal(await session.send(app(),'New information',[fileId],files()),true);
 assert.equal(await session.send(app(),'Changed',[],files()),false);assert.equal(calls,1);
});
test('missing capability, disposed appeals, unknown evidence and pending scans cannot append',async()=>{
 let calls=0;const api=async()=>{calls++;};
 for(const [projection,ids,evidence] of [[{...app(),can_supplement:false},[],files()],
  [{...app(),status:'accepted'},[],files()],[app(),[id],files()],
  [app(),[fileId],[{...files()[0],scan_state:'pending'}]]]){
  assert.equal(await S.createSupplementSession(api).send(projection,'Text',ids,evidence),false);
 }
 assert.equal(calls,0);
});
test('uncertain append and in-flight append never automatically retry',async()=>{
 let calls=0,release;const session=S.createSupplementSession(()=>{calls++;return new Promise(resolve=>{release=resolve;});});
 const first=session.send(app(),'Text',[],files());assert.equal(await session.send(app(),'Text',[],files()),false);
 release({id:fileId});await first;assert.equal(calls,1);
 const uncertain=S.createSupplementSession(async()=>{calls++;throw new Error('network');});
 assert.equal(await uncertain.send(app(),'Text',[],files()),false);
 assert.equal(await uncertain.send(app(),'Text',[],files()),false);assert.equal(calls,2);
 assert.equal(uncertain.state.locked,true);assert.equal(uncertain.state.error,'uncertain');
});
