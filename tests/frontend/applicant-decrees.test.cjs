const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),context={window:{}};
const path='static/ctm/applicant-decrees.js';
if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
const D=context.window.CTMApplicantDecrees||{};
const id='11111111-1111-4111-8111-111111111111',file='22222222-2222-4222-8222-222222222222';
const data=()=>({id,released_decrees:[{id,reference:'DCR-2026-001',language:'en',released_at:'2026-10-21T12:00:00Z',
 signed_file:{id:file,name:'Certificate.pdf',scan_state:'clean',download_url:`/api/files/${file}/`}}]});
test('decree projection requires own case identity and explicit released list',()=>{
 assert.equal(D.validProjection(data(),id),true);
 assert.equal(D.validProjection({id,released_decrees:[]},id),true);
 for(const mutate of [d=>delete d.released_decrees,d=>d.id=file,d=>d.released_decrees.push(d.released_decrees[0]),
 d=>d.released_decrees[0].released_at='2026-10-21',d=>d.released_decrees[0].language='unknown',
 d=>d.released_decrees[0].reference='']){
  const d=data();mutate(d);assert.equal(D.validProjection(d,id),false);
 }
});
test('only exact authorized clean signed original URLs are rendered',()=>{
 const row=data().released_decrees[0];assert.equal(D.downloadURL(row.signed_file),`/api/files/${file}/`);
 for(const mutate of [f=>f.scan_state='pending',f=>f.download_url='https://example.com/file.pdf',
 f=>f.download_url=`/api/files/${file}/?preview=1`,f=>f.id=id,f=>f.name='']){
  const d=data();mutate(d.released_decrees[0].signed_file);
  assert.equal(D.validProjection(d,id),false);assert.equal(D.downloadURL(d.released_decrees[0].signed_file),null);
 }
});
