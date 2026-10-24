const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const c={window:{crypto:{randomUUID:()=>"stable-message-key"}}};
const path='static/ctm/applicant-messages.js';if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),c);
const M=c.window.CTMApplicantMessages||{},id='11111111-1111-4111-8111-111111111111',party='22222222-2222-4222-8222-222222222222',msg='33333333-3333-4333-8333-333333333333';
const record=()=>({id,can_message:true,parties:[{id:party,is_self:true}]});
const row=()=>({id:msg,body:'Own text',sender:'Sender',channel:'portal',timestamp:'2026-10-21T12:00:00Z',file_links:[],idempotency_key:null,receipts:[{party_id:party,read_at:null}]});
test('own message binding requires exact case, one own party and explicit send capability',()=>{
 assert.equal(typeof M.ownParty,'function');assert.equal(M.ownParty(record(),id),party);
 assert.equal(M.ownParty({...record(),id:msg},id),null);assert.equal(M.ownParty({...record(),parties:[...record().parties,{id:msg,is_self:true}]},id),null);
 assert.equal(M.canSend({...record(),can_message:undefined},id),false);
});
test('message history validates bounded continuation and own-only receipt projection',()=>{
 assert.equal(M.validPage({items:[row()],next_offset:null},0,party),true);
 assert.equal(M.validPage({items:[{...row(),receipts:[{party_id:msg,read_at:null}]}],next_offset:null},0,party),false);
 assert.equal(M.validPage({items:[row()],next_offset:50},0,party),false);
 assert.equal(M.validPage({items:[row(),row()],next_offset:null},0,party),false);
});
test('uncertain send freezes exact own portal routing/key, explicit retry and receipt recovery',async()=>{
 const bodies=[];let n=0;const s=M.createSendSession(id,async(url,options)=>{bodies.push(JSON.parse(options.body));if(++n===1)throw Error('lost');return{id:msg};});
 assert.equal(await s.send(record(),'Own text'),false);
 assert.deepEqual(bodies[0],{body:'Own text',party_ids:[party],channel:'portal',email_timing:'immediate',session_id:null,file_ids:[],idempotency_key:'stable-message-key'});
 assert.equal(await s.send(record(),'Changed'),false);assert.equal(bodies.length,1);
 assert.equal(await s.retry({...record(),can_message:false}),false);assert.equal(await s.retry(record()),true);assert.deepEqual(bodies[0],bodies[1]);
 assert.equal(await s.retry(record()),false);
});
test('matching own history recovers only the frozen original sender key/body/recipient',async()=>{
 const s=M.createSendSession(id,async()=>{throw Error('lost');});await s.send(record(),'Own text');
 assert.equal(s.reconcile([{...row(),idempotency_key:'wrong'}]),false);
 assert.equal(s.reconcile([{...row(),idempotency_key:'stable-message-key',body:'Changed'}]),false);
 assert.equal(s.reconcile([{...row(),idempotency_key:'stable-message-key'}]),true);assert.equal(s.state.receipt,msg);
});
test('read acknowledgement is explicit, intended-copy bound, validates response and locks uncertain repeats',async()=>{
 let calls=0;const s=M.createReadSession(async()=>{calls++;throw Error('lost');});
 assert.equal(await s.send(row(),party,false),false);assert.equal(calls,0);
 assert.equal(await s.send(row(),party,true),false);assert.equal(await s.send(row(),party,true),false);assert.equal(calls,1);
 const ok=M.createReadSession(async()=>({id:msg,read_at:'2026-10-21T13:00:00Z'}));
 assert.equal(await ok.send(row(),party,true),true);assert.ok(ok.state.read_at);
});
