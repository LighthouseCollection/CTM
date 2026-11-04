// C-05 (#3): external priest report page against backend #7's capability contract
// (tribunal/api.py external_report; services/reports.py external_request, complete_external).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, loadExternal, textareas, notices, buttons, dialogs, type, settle, find, textOf, byName } = require("./harness.cjs");

const REQ = "11111111-2222-4333-8444-555555555555";
const OTHER = "99999999-2222-4333-8444-555555555555";
const sample = { id: REQ, title: "Report by Fr. Synthetic Priest", case_number: "20261021-01", subject: "John Synthetic", instructions: "Please describe what you know.", language: "en", draft: {} };

function server(handler) {
  const calls = [];
  const fetchImpl = async (url, options) => {
    const call = { url, method: options.method, headers: options.headers, credentials: options.credentials, cache: options.cache,
      referrerPolicy: options.referrerPolicy, body: options.body ? JSON.parse(options.body) : undefined };
    calls.push(call);
    const out = handler(call, calls.length);
    if (out instanceof Error) throw out;
    const [status, data] = out;
    return { ok: status >= 200 && status < 300, status, json: async () => data };
  };
  return { fetchImpl, calls };
}
const unavailable = [403, { error: "link_unavailable" }];

function mount(handler, props = {}) {
  const h = harness();
  const { api } = loadExternal(h);
  const srv = server(handler);
  const link = props.link === undefined ? { requestId: REQ, token: "secret-token" } : props.link;
  const ui = {
    api, srv,
    tree: null,
    async render() { for (let i = 0; i < 3; i++) { ui.tree = h.render(api.ExternalReportPage, { link, fetchImpl: srv.fetchImpl, initialLang: props.lang || null }); await settle(); } return ui.tree; },
    text() { return textOf(ui.tree); },
    notes() { return notices(ui.tree).join(" | "); },
    async click(label) { const b = buttons(ui.tree, label)[0]; assert.ok(b, `button "${label}"`); await b.props.onClick(); await settle(); await ui.render(); },
    async submitForm() { const form = find(ui.tree, (n) => n.props && n.props.onSubmit)[0]; form.props.onSubmit({ preventDefault() {} }); await ui.render(); const d = dialogs(ui.tree).find((x) => x.props.open); await d.props.onConfirm(); await settle(); await ui.render(); },
    posts() { return srv.calls.filter((c) => c.method === "POST"); },
  };
  return ui;
}

test("fragment parsing: request id and token come only from #r=…&t=…", () => {
  const { api } = loadExternal(harness());
  assert.deepEqual({ ...api.parseFragment(`#r=${REQ}&t=abc-DEF_123`) }, { requestId: REQ, token: "abc-DEF_123" });
  assert.equal(api.parseFragment(`#r=${REQ}`), null);
  assert.equal(api.parseFragment("#t=abc"), null);
  assert.equal(api.parseFragment("#r=../../etc&t=x"), null);
  assert.equal(api.parseFragment(""), null);
});

test("every request uses the Bearer token, sends no cookies, no cache, no referrer, and only this request's URL", async () => {
  const ui = mount(() => [200, sample]);
  await ui.render();
  const get = ui.srv.calls[0];
  assert.equal(get.url, `/external/reports/${REQ}/`);
  assert.equal(get.headers.Authorization, "Bearer secret-token");
  assert.equal(get.credentials, "omit");
  assert.equal(get.cache, "no-store");
  assert.equal(get.referrerPolicy, "no-referrer");
  assert.ok(ui.srv.calls.every((c) => c.url === `/external/reports/${REQ}/` && !c.url.includes(OTHER)), "cross-request isolation");
});

test("authorized render shows only the request, case number, subject and instructions; a saved draft is restored", async () => {
  const ui = mount(() => [200, { ...sample, draft: { testimony: "Earlier draft text." } }]);
  await ui.render();
  const shown = ui.text();
  assert.match(shown, /Report by Fr\. Synthetic Priest/);
  assert.match(shown, /20261021-01/);
  assert.match(shown, /John Synthetic/);
  assert.match(shown, /Please describe what you know\./);
  assert.equal(textareas(ui.tree)[0].props.value, "Earlier draft text.");
  assert.doesNotMatch(shown, /observation|internal|spouse answers/i);
});

test("expired, wrong, reissued, cancelled or completed links (all 403) show one honest inactive state", async () => {
  const ui = mount(() => unavailable);
  await ui.render();
  assert.match(ui.notes(), /This link is not active\./);
  assert.match(ui.notes(), /expired \(links last 30 days\), been replaced by a newer link, been cancelled, or the report may already have been submitted/);
  assert.equal(textareas(ui.tree).length, 0);
});

test("an incomplete link never calls the server", async () => {
  const ui = mount(() => assert.fail("no request expected"), { link: null });
  await ui.render();
  assert.match(ui.notes(), /This link is incomplete/);
  assert.equal(ui.srv.calls.length, 0);
});

test("save draft posts {action:'save', answers:{testimony}} and confirms it is on the server", async () => {
  const ui = mount((c) => (c.method === "POST" ? [200, { saved: true }] : [200, sample]));
  await ui.render();
  type(textareas(ui.tree)[0], "Draft paragraph.");
  await ui.render();
  await ui.click("Save draft");
  assert.deepEqual(ui.posts()[0].body, { action: "save", answers: { testimony: "Draft paragraph." } });
  assert.match(ui.notes(), /Draft saved on the tribunal's server\./);
});

test("submit needs confirmation, posts {answers:{testimony}} once, then the link is closed", async () => {
  const ui = mount((c) => (c.method === "POST" ? [201, { submitted: true, report_id: "rep-x" }] : [200, sample]));
  await ui.render();
  type(textareas(ui.tree)[0], "My full report.");
  await ui.render();
  await ui.submitForm();
  assert.deepEqual(ui.posts().map((c) => c.body), [{ answers: { testimony: "My full report." } }]);
  assert.match(ui.notes(), /Thank you\. Your report was received/);
  assert.equal(textareas(ui.tree).length, 0, "no further editing after submission");
});

test("empty report is not submitted", async () => {
  const ui = mount(() => [200, sample]);
  await ui.render();
  await ui.submitForm();
  assert.equal(ui.posts().length, 0);
  assert.match(ui.notes(), /Write your report before submitting/);
});

test("lost acknowledgement: no false success, text kept; a later 403 says it may already be received", async () => {
  const ui = mount((c, n) => (c.method === "GET" ? [200, sample] : n === 2 ? new TypeError("Failed to fetch") : unavailable));
  await ui.render();
  type(textareas(ui.tree)[0], "Report whose reply was lost.");
  await ui.render();
  await ui.submitForm();
  assert.match(ui.notes(), /did not confirm your submission\. Your text is still here/);
  assert.equal(textareas(ui.tree)[0].props.value, "Report whose reply was lost.");
  await ui.submitForm(); // repeated submit: the server answers 403 because the first one completed the request
  assert.match(ui.notes(), /may already have been received\. Your text is still shown/);
  assert.equal(textareas(ui.tree)[0].props.value, "Report whose reply was lost.");
  assert.doesNotMatch(ui.notes(), /Thank you/);
});

test("a link that stops working while saving keeps the text", async () => {
  const ui = mount((c) => (c.method === "POST" ? unavailable : [200, sample]));
  await ui.render();
  type(textareas(ui.tree)[0], "Unsaved words.");
  await ui.render();
  await ui.click("Save draft");
  assert.match(ui.notes(), /draft was not saved\. Your text is still shown/);
  assert.equal(textareas(ui.tree)[0].props.value, "Unsaved words.");
});

test("Arabic: requests in Arabic open in Arabic, with an English switch", async () => {
  const ui = mount(() => [200, { ...sample, language: "ar" }]);
  await ui.render();
  await ui.render();
  assert.match(ui.text(), /تقريرك المكتوب/);
  assert.ok(buttons(ui.tree, "English")[0]);
});

test("no browser storage, cookies or token logging in the page module; boot page has no case data", () => {
  const src = fs.readFileSync("static/ctm/external-report.js", "utf8");
  assert.doesNotMatch(src, /localStorage|sessionStorage|indexedDB|document\.cookie|console\.log/);
  assert.match(src, /history\.replaceState\(null, "", window\.location\.pathname \+ window\.location\.search\)/, "token removed from the address bar");
  const html = fs.readFileSync("static/ctm/external-report.html", "utf8");
  assert.match(html, /<meta name="referrer" content="no-referrer">/);
  assert.match(html, /cdn\/0\.76\.0\/plenix\.js/);
  assert.doesNotMatch(html, /cdn\/(?!0\.76\.0)\d+\.\d+\.\d+/);
  assert.doesNotMatch(html, /\{\{|\{%|case_number|token=/);
  assert.doesNotMatch(src, /style\s*:/);
});

test("opening another link in the same tab (fragment change) restarts the page for that link (browser finding)", () => {
  const src = fs.readFileSync("static/ctm/external-report.js", "utf8");
  assert.match(src, /addEventListener\("hashchange", \(\) => window\.location\.reload\(\)\)/);
});
