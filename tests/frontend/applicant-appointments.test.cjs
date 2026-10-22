const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};
const path='static/ctm/applicant-appointments.js';
if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
const A=context.window.CTMApplicantAppointments||{};
const invitation=()=>({id:'11111111-1111-4111-8111-111111111111',case_number:'T-2026-0001',
  starts_at:'2026-12-01T10:00:00-08:00',ends_at:'2026-12-01T10:30:00-08:00',
  instructions:'Private instructions',version:2,state:'invited',response:null,can_respond:true});

test('private invitation requires explicit version/capability and offset dates',()=>{
  assert.equal(A.validListing({items:[invitation()]}),true);
  for(const mutation of [r=>delete r.can_respond,r=>r.version=0,r=>r.starts_at='2026-12-01T10:00:00',
    r=>r.ends_at=r.starts_at,r=>r.response='maybe',r=>r.state='cancelled']){
    const row=invitation();mutation(row);assert.equal(A.validListing({items:[row]}),false);
  }
  const cancelled={...invitation(),state:'cancelled',can_respond:false};
  assert.equal(A.validListing({items:[cancelled]}),true);
  assert.equal(A.validListing({items:[invitation(),invitation()]}),false);
});

test('response sends only invitation id and exact version and locks after acknowledgement',async()=>{
  let calls=0;
  const session=A.createResponseSession(invitation(),async(url,options)=>{
    calls++;assert.equal(url,'/api/appointments/11111111-1111-4111-8111-111111111111/response/');
    assert.deepEqual(JSON.parse(options.body),{version:2,response:'reject',explanation:'Unavailable'});
    return {id:'response-id'};
  });
  assert.equal(await session.send('reject','Unavailable'),true);
  assert.equal(await session.send('confirm',''),false);
  assert.equal(calls,1);assert.equal(session.state.acknowledged,true);
});

test('in-flight, invalid and unavailable responses cannot make another request',async()=>{
  let calls=0,release;
  const api=()=>{calls++;return new Promise(resolve=>{release=resolve;});};
  const session=A.createResponseSession(invitation(),api);
  assert.equal(await session.send('maybe',''),false);
  const pending=session.send('confirm','');
  assert.equal(await session.send('reject',''),false);
  release({id:'response'});await pending;assert.equal(calls,1);
  const closed=A.createResponseSession({...invitation(),can_respond:false},api);
  assert.equal(await closed.send('confirm',''),false);assert.equal(calls,1);
});

test('uncertain and stale responses require authoritative refresh before another response',async()=>{
  for(const status of [undefined,422,403]){
    let calls=0;
    const session=A.createResponseSession(invitation(),async()=>{calls++;throw Object.assign(new Error('failed'),{status});});
    assert.equal(await session.send('reject','Reason'),false);
    assert.equal(await session.send('confirm',''),false);
    assert.equal(calls,1);assert.equal(session.state.locked,true);
    assert.equal(session.state.error,status===422?'stale':status===403?'denied':'uncertain');
  }
});
