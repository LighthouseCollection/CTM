const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const c={window:{}};if(fs.existsSync('static/ctm/applicant-notifications.js'))vm.runInNewContext(fs.readFileSync('static/ctm/applicant-notifications.js','utf8'),c);
const N=c.window.CTMApplicantNotifications||{},id='11111111-1111-4111-8111-111111111111';
const row=()=>({id,kind:'case_update',payload:{private:'not displayed'},read:false,timestamp:'2026-10-21T12:00:00Z',case_id:null,case_number:null});
test('notification pages require bounded exact metadata, boolean state and authoritative unread count',()=>{
 assert.equal(typeof N.validPage,'function');assert.equal(N.validPage({items:[row()],next_offset:null,unread_count:1},0),true);
 assert.equal(N.validPage({items:[{...row(),read:'false'}],next_offset:null,unread_count:1},0),false);
 assert.equal(N.validPage({items:[row()],next_offset:50,unread_count:1},0),false);
 assert.equal(N.validPage({items:[row()],next_offset:null,unread_count:-1},0),false);
});
test('read action requires explicit confirmation and literal acknowledgement; false never fabricates read state',async()=>{
 let calls=0;const s=N.createReadSession(async(url,options)=>{calls++;assert.equal(url,'/api/notifications/');assert.deepEqual(JSON.parse(options.body),{id});return{updated:false};});
 assert.equal(await s.send(row(),false),false);assert.equal(calls,0);
 assert.equal(await s.send(row(),true),false);assert.equal(s.state.confirmed,false);assert.equal(s.state.error,'refreshRequired');
 assert.equal(await s.send(row(),true),false);assert.equal(calls,1);
});
test('uncertain notification acknowledgement locks repeats and a valid true response confirms only the requested action',async()=>{
 const s=N.createReadSession(async()=>{throw Error('lost');});assert.equal(await s.send(row(),true),false);assert.equal(s.state.error,'uncertain');
 assert.equal(await s.send(row(),true),false);
 const t=N.createReadSession(async()=>({updated:true}));assert.equal(await t.send(row(),true),true);assert.equal(t.state.confirmed,true);
});
