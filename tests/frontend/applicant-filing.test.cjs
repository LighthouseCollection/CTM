const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { window: {}, URL };
const path = 'static/ctm/applicant-filing.js';
if (fs.existsSync(path)) vm.runInNewContext(fs.readFileSync(path, 'utf8'), context);
const F = context.window.CTMApplicantFiling || {};
const fixture = () => ({ id: 'own', version: 4, status: 'draft', can_checkout: true,
  can_submit: false, can_resubmit: false, duplicate_hold: false,
  fee: { amount_minor: 25000, currency: 'USD', status: 'due' },
  questionnaire: { id: 'q', version: 1, published: true,
    declaration_en: 'Approved fixture declaration', declaration_ar: 'إقرار تجريبي معتمد' } });

test('checkout needs explicit capability, genuine due fee and bilingual published declaration', () => {
  assert.equal(F.availability(fixture()).checkout, true);
  for (const mutate of [a => delete a.can_checkout, a => a.duplicate_hold = true,
    a => a.questionnaire.published = false, a => delete a.questionnaire.declaration_ar,
    a => a.fee.status = 'paid', a => a.fee.amount_minor = 1, a => a.status = 'returned']) {
    const app = fixture(); mutate(app);
    assert.equal(F.availability(app).checkout, false);
  }
});

test('checkout sends approved attestation and does not infer payment/submission success', async () => {
  let payload;
  const session = F.createFilingSession(fixture(), async (url, options) => {
    assert.equal(url, '/api/applications/own/checkout/'); payload = JSON.parse(options.body);
    return { intent: 'intent', checkout_url: 'https://checkout.stripe.com/c/pay/synthetic' };
  }, () => 'key');
  const url = await session.checkout({ accepted: true, name: 'Applicant' });
  assert.equal(url, 'https://checkout.stripe.com/c/pay/synthetic');
  assert.equal(payload.attestation.name, 'Applicant');
  assert.equal(payload.expected_version, 4);
  assert.equal(session.state.submitted, false);
});

test('untrusted checkout URL or invalid acknowledgement is never navigated', async () => {
  for (const checkout_url of ['javascript:alert(1)', 'https://checkout.stripe.com.evil.test/',
    'http://checkout.stripe.com/', 'https://user@checkout.stripe.com/', '/?payment=returned']) {
    const session = F.createFilingSession(fixture(), async () => ({intent: 'i', checkout_url}), () => 'k');
    assert.equal(await session.checkout({accepted: true, name: 'A'}), null);
    assert.equal(session.state.error, 'checkoutFailed');
    assert.equal(session.state.submitted, false);
  }
});

test('waived first submission requires attestation and uses same idempotency key after network failure', async () => {
  const app = fixture(); app.fee.status = 'waived'; app.can_submit = true;
  const requests = []; let attempts = 0;
  const session = F.createFilingSession(app, async (url, options) => {
    requests.push(JSON.parse(options.body)); if (++attempts === 1) throw new Error('network');
    return { id: 'submission' };
  }, () => 'stable-key');
  assert.equal(await session.submit({accepted: false, name: 'A'}), false);
  assert.equal(requests.length, 0);
  assert.equal(await session.submit({accepted: true, name: 'A'}), false);
  assert.equal(await session.submit({accepted: true, name: 'A'}), true);
  assert.equal(requests[0].idempotency_key, requests[1].idempotency_key);
  assert.equal(requests[1].expected_version, 4);
});

test('uncertain submission retry freezes the original attestation and reviewed version', async () => {
  const app = fixture(); app.fee.status = 'waived'; app.can_submit = true;
  const requests = [];
  const session = F.createFilingSession(app, async (url, options) => {
    requests.push(JSON.parse(options.body)); throw new Error('network');
  }, () => 'same');
  const attestation = {accepted:true,name:'Original signer'};
  await session.submit(attestation);
  attestation.name = 'Changed'; app.version = 9;
  await session.submit(attestation);
  assert.deepEqual(requests[0], requests[1]);
  assert.equal(session.state.attempted, true);
});

test('returned resubmission reuses signature and fee without checkout or new attestation', async () => {
  const app = fixture(); app.status = 'returned'; app.can_resubmit = true; app.fee.status = 'paid';
  let payload;
  const session = F.createFilingSession(app, async (url, options) => {
    assert.equal(url, '/api/applications/own/submit/'); payload = JSON.parse(options.body);
    return { id: 'resubmission' };
  }, () => 'return-key');
  assert.equal(F.availability(app).checkout, false);
  assert.equal(await session.submit(), true);
  assert.equal('attestation' in payload, false);
});

test('access loss locks further actions and concurrent/repeated successful submission is blocked', async () => {
  const app = fixture(); app.fee.status = 'paid'; app.can_submit = true;
  let finish; let calls = 0;
  const session = F.createFilingSession(app, () => { calls++; return new Promise(r => finish = r); }, () => 'k');
  const first = session.submit({accepted: true, name: 'A'});
  assert.equal(await session.submit({accepted: true, name: 'A'}), false);
  finish({id: 's'}); await first;
  assert.equal(await session.submit({accepted: true, name: 'A'}), false);
  assert.equal(calls, 1);
  const denied = F.createFilingSession(app, async () => { throw {status:403}; }, () => 'k');
  await denied.submit({accepted:true,name:'A'});
  assert.equal(denied.state.locked, true);
});
