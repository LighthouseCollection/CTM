const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync('static/ctm/ui-workspaces.js', 'utf8'), context);
const U = context.window.CTMUI;
test('system administration never opens to applicant/member/president; enrollment is admin only', () => {
  for (const role of ['applicant', 'member', 'president', undefined]) {
    assert.equal(U.canAdminister({role}), false);
    assert.equal(U.canEnroll({role}), false);
  }
  assert.equal(U.canAdminister({role:'secretary'}), true);
  assert.equal(U.canEnroll({role:'secretary'}), false);
  assert.equal(U.canEnroll({role:'admin'}), true);
});
test('audit structured filters combine actor, source, action and inclusive calendar dates', () => {
  const rows = [
    {id:'1',actor:'Member A',action:'report_revised',source:'report',timestamp:'2026-10-21T23:59:59Z'},
    {id:'2',actor:'Member B',action:'report_revised',source:'report',timestamp:'2026-10-22T07:00:00Z'},
    {id:'3',actor:'Member A',action:'case_created',source:'case',timestamp:'2026-10-21T07:00:00Z'},
  ];
  assert.deepEqual(Array.from(U.filterAudit(rows,{actor:'Member A',source:'report',action:'report_revised',to:'2026-10-21'}),x=>x.id),['1']);
  assert.deepEqual(Array.from(U.filterAudit(rows,{from:'2026-10-22'}),x=>x.id),['2']);
  assert.equal(U.filterAudit(rows,{query:'Member B'}).length,1);
  assert.equal(U.filterAudit([{actor:'Same name',actor_id:'a',timestamp:'2026-10-21T12:00:00Z'},{actor:'Same name',actor_id:'b',timestamp:'2026-10-21T12:00:00Z'}],{actor:'a'}).length,1);
});
test('invalid enrollment fields do not produce a request payload; names/email are not fabricated', () => {
  assert.equal(U.enrollmentProblem({email:'not-email',first_name:'A',last_name:'B',role:'member'}),'emailInvalid');
  assert.equal(U.enrollmentProblem({email:'a@example.test',first_name:'A',last_name:'B',role:'applicant'}),'roleRequired');
  assert.equal(U.enrollmentProblem({email:'a@example.test',first_name:'A',last_name:'B',role:'member'}),null);
});
test('session filters distinguish past planned sessions from upcoming and combine date bounds', () => {
  const rows = [{id:'1',state:'planned',date:'2026-10-20'}, {id:'2',state:'planned',date:'2026-10-22'}, {id:'3',state:'closed',date:'2026-10-23'}];
  assert.deepEqual(Array.from(U.filterSessions(rows,{view:'upcoming'},'2026-10-21'),r=>r.id),['2']);
  assert.deepEqual(Array.from(U.filterSessions(rows,{view:'past',from:'2026-10-21'},'2026-10-21'),r=>r.id),['3']);
});
test('historical adapter preserves retained identifiers and unknown payload data without guessing account links', () => {
  vm.runInNewContext(fs.readFileSync('static/ctm/historical-entry.js','utf8'),context);
  const H=context.window.CTMHistorical;
  const payload={number:'Legacy / 07',status:'closed',extra:{retained:true},parties:[{slot:'A',name:'Person',legacy_reference:'ABC-07',account_id:'verified-account'}]};
  const form=H.formFrom(payload);
  form.parties[0].name='Corrected';
  const after=H.payloadFrom(form,payload);
  assert.equal(after.number,payload.number);
  assert.equal(after.extra.retained,true);
  assert.equal(after.parties[0].account_id,'verified-account');
  assert.equal(after.parties.length,1);
  const retained={number:'Old-2',status:'closed',parties:[{slot:'A',import_notes:'Keep historical research'}]};
  assert.equal(H.payloadFrom(H.formFrom(retained),retained).parties[0].import_notes,'Keep historical research');
  assert.equal(H.problem({...form,closed_at:'2020-01-01T12:00'}),'timestampRequired');
  assert.equal(H.problem({...form,closed_at:'2020-01-01T12:00:00-08:00'}),null);
  assert.equal(H.validPayload({number:55,parties:[]}),false);
  assert.equal(H.validPayload(retained),true);
});

test('member enrollment uses the explicit membership endpoint', () => {
  const source = fs.readFileSync('static/ctm/ui-workspaces.js', 'utf8');
  assert.doesNotMatch(source, /api\("\/api\/council\/enroll\//);
  assert.match(source, /api\("\/api\/system\/members\/", \{ method: "POST"/);
});
