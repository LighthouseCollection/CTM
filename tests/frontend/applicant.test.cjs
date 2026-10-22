const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { window: {}, structuredClone };
vm.runInNewContext(fs.readFileSync('static/ctm/applicant.js', 'utf8'), context);
const A = context.window.CTMApplicant;
const fixture = () => ({
  id: 'draft-a', status: 'draft', version: 3, can_edit: true,
  answers: { first_name: 'Original', future_field: { retained: true } },
  questionnaire: { id: 'form-a', version: 1, published: true, definition: { fields: [
    { code: 'first_name', type: 'text', required: true, label_en: 'First name', label_ar: 'الاسم الأول' },
    { code: 'grounds', type: 'list', label_en: 'Grounds', label_ar: 'الأسباب', choices: [
      { value: 'abuse', label_en: 'Abuse', label_ar: 'الإساءة' },
    ] },
  ] } },
});

test('bound published bilingual definition is required; no guessed labels or types', () => {
  assert.equal(A.definitionProblem(fixture()), null);
  for (const change of [
    a => delete a.questionnaire,
    a => a.questionnaire.published = false,
    a => delete a.questionnaire.definition.fields[0].label_ar,
    a => a.questionnaire.definition.fields[0].type = 'unsupported',
    a => a.questionnaire.definition.fields.push(a.questionnaire.definition.fields[0]),
    a => a.questionnaire.definition.fields[1].choices = ['abuse'],
  ]) {
    const app = fixture(); change(app);
    assert.equal(A.definitionProblem(app), 'definitionUnavailable');
  }
});

test('partial draft save preserves unknown answers and sends expected version', async () => {
  const app = fixture(); const requests = [];
  const draft = A.createDraftSession(app, async (url, options) => {
    requests.push([url, JSON.parse(options.body)]);
    return { version: 4 };
  });
  draft.change('first_name', '');
  assert.equal(draft.state.dirty, true);
  assert.equal(await draft.save(), true);
  assert.equal(requests[0][0], '/api/applications/draft-a/');
  assert.equal(requests[0][1].expected_version, 3);
  assert.equal(requests[0][1].answers.first_name, '');
  assert.equal(requests[0][1].answers.future_field.retained, true);
  assert.equal(app.answers.first_name, 'Original');
  assert.equal(draft.state.version, 4);
  assert.equal(draft.state.dirty, false);
});

test('failed save keeps local input/version and cannot report success', async () => {
  const draft = A.createDraftSession(fixture(), async () => { throw { status: 400 }; });
  draft.change('first_name', 'Local correction');
  assert.equal(await draft.save(), false);
  assert.equal(draft.state.answers.first_name, 'Local correction');
  assert.equal(draft.state.version, 3);
  assert.equal(draft.state.dirty, true);
  assert.equal(draft.state.error, 'saveFailed');
});

test('missing edit capability, missing definition and withdrawn state prevent writes', async () => {
  for (const change of [a => delete a.can_edit, a => a.can_edit = false,
    a => delete a.questionnaire, a => a.status = 'withdrawn']) {
    const app = fixture(); change(app); let calls = 0;
    const draft = A.createDraftSession(app, async () => { calls++; });
    draft.change('first_name', 'Forbidden');
    assert.equal(draft.state.answers.first_name, 'Original');
    assert.equal(await draft.save(), false);
    assert.equal(calls, 0);
  }
});

test('in-flight save blocks a second write and input mutation', async () => {
  let finish; let calls = 0;
  const draft = A.createDraftSession(fixture(), () => {
    calls++; return new Promise(resolve => { finish = resolve; });
  });
  draft.change('first_name', 'Sent');
  const saving = draft.save();
  draft.change('first_name', 'Not sent');
  assert.equal(await draft.save(), false);
  finish({ version: 4 }); await saving;
  assert.equal(calls, 1);
  assert.equal(draft.state.answers.first_name, 'Sent');
});

test('permission or expired-session save failure locks further editing', async () => {
  for (const status of [401, 403, 404]) {
    const draft = A.createDraftSession(fixture(), async () => { throw { status }; });
    draft.change('first_name', 'Keep unsaved'); await draft.save();
    assert.equal(draft.state.editable, false);
    assert.equal(draft.state.error, status === 401 ? 'expired' : 'accessDenied');
    assert.equal(draft.state.dirty, true);
  }
});

test('malformed save acknowledgement retains dirty data and original version', async () => {
  const draft = A.createDraftSession(fixture(), async () => ({ version: 3 }));
  draft.change('first_name', 'Local');
  assert.equal(await draft.save(), false);
  assert.equal(draft.state.version, 3);
  assert.equal(draft.state.dirty, true);
});

test('existing backend when conditions control display and preserve hidden answers', () => {
  const app = fixture();
  const field = app.questionnaire.definition.fields[0];
  field.when = { field: 'grounds', equals: 'abuse' };
  assert.equal(A.definitionProblem(app), null);
  assert.equal(A.isVisible(field, { grounds: 'abuse' }), true);
  assert.equal(A.isVisible(field, { grounds: 'other' }), false);
  field.when.field = 'missing';
  assert.equal(A.definitionProblem(app), 'definitionUnavailable');
});

test('malformed saved answer shapes block destructive coercion', () => {
  for (const answers of [{ first_name: { unexpected: true } }, { grounds: 'abuse' }]) {
    const app = fixture(); app.answers = answers;
    assert.equal(A.answerProblem(app), 'answersUnavailable');
    const draft = A.createDraftSession(app, async () => { throw new Error('must not write'); });
    assert.equal(draft.state.editable, false);
  }
});

test('backend primitive choices with approved bilingual labels remain supported', () => {
  const app = fixture();
  const field = app.questionnaire.definition.fields[1];
  field.choices = ['abuse'];
  field.choice_labels = { abuse: { label_en: 'Abuse', label_ar: 'الإساءة' } };
  assert.equal(A.definitionProblem(app), null);
  assert.equal(A.fieldChoices(field)[0].value, 'abuse');
});

test('invalid optimistic version blocks editing instead of sending a blind save', () => {
  for (const version of [undefined, -1, 1.5, '3']) {
    const app = fixture(); app.version = version;
    assert.equal(A.createDraftSession(app, async () => {}).state.editable, false);
  }
});

test('published boolean questions retain unanswered and explicit false states', async () => {
  const app=fixture();
  app.questionnaire.definition.fields.push({code:'has_order',type:'boolean',required:true,
    label_en:'Has order?',label_ar:'هل يوجد أمر؟'});
  assert.equal(A.definitionProblem(app),null);
  let saved;
  const draft=A.createDraftSession(app,async(url,options)=>{saved=JSON.parse(options.body);return{version:4};});
  assert.equal(draft.state.answers.has_order,undefined);
  draft.change('has_order',false); await draft.save();
  assert.equal(saved.answers.has_order,false);
});

test('draft creation delegates eligibility and reuse to server without posting local case claims', async () => {
  let payload;
  const result=await A.startDraft(async(url,options)=>{
    assert.equal(url,'/api/applications/'); payload=JSON.parse(options.body); return{id:'reused-draft'};
  });
  assert.deepEqual(payload,{kind:'petition'});
  assert.equal(result,'reused-draft');
});

test('repeat records preserve original IDs and opaque values during a nested correction', () => {
  const app=fixture();
  app.questionnaire.definition.fields.push({code:'children',type:'list',label_en:'Children',label_ar:'الأطفال',
    item_fields:[{code:'gender',type:'choice',label_en:'Gender',label_ar:'الجنس',choices:[
      {value:'unknown',label_en:'Unknown',label_ar:'غير معروف'}]}]});
  app.answers.children=[{id:'original-id',gender:'unknown',opaque:{retained:true}}];
  assert.equal(A.definitionProblem(app),null);
  assert.equal(A.answerProblem(app),null);
  const changed=A.updateRecord(app.answers.children,0,'gender','F');
  assert.equal(changed[0].id,'original-id');
  assert.equal(changed[0].opaque.retained,true);
  assert.equal(app.answers.children[0].gender,'unknown');
  assert.equal(A.updateRecord(app.answers.children,0,'id','replacement')[0].id,'original-id');
});

test('repeat schema rejects missing translations, nested records and malformed saved rows', () => {
  const app=fixture();
  const repeat={code:'orders',type:'list',label_en:'Orders',label_ar:'الأوامر',item_fields:[
    {code:'court',type:'text',label_en:'Court',label_ar:'المحكمة'}]};
  app.questionnaire.definition.fields.push(repeat);
  assert.equal(A.definitionProblem(app),null);
  delete repeat.item_fields[0].label_ar;
  assert.equal(A.definitionProblem(app),'definitionUnavailable');
  repeat.item_fields[0].label_ar='المحكمة';
  app.answers.orders=['invalid record'];
  assert.equal(A.answerProblem(app),'answersUnavailable');
});
