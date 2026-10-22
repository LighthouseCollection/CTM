// C-05 (#3): council composer and private-link handoff for an external priest report.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, find, textareas, notices, buttons, dialogs, settle, byName, textOf } = require("./harness.cjs");

test("external request: priest name required; payload is free-form with no questions and a 'Report by Fr.' title", () => {
  const C = load(harness());
  const form = { kind: "external_priest", party: "p-1", title: "", language: "both", instructions: "  Describe the marriage.  ", selected: ["DM-01"], parent: "", priest: "" };
  assert.equal(C.requestProblem(form, []), "priestRequired");
  form.priest = "  Synthetic Priest ";
  assert.equal(C.requestProblem(form, []), null);
  const payload = JSON.parse(JSON.stringify(C.requestPayload(form, "proc-1")));
  assert.deepEqual(payload, { proceeding_id: "proc-1", party_id: "p-1", kind: "external_priest", title: "Report by Fr. Synthetic Priest", language: "both",
    instructions: "Describe the marriage.", questions: [], parent_id: null });
  assert.equal(C.priestFromTitle("Report by Fr. Synthetic Priest"), "Synthetic Priest");
});

test("the private link keeps the token in the fragment of the static boot page", () => {
  const C = load(harness());
  assert.equal(C.priestLink("https://ctm.example", "req-1", "tok/en+"), "https://ctm.example/static/ctm/external-report.html#r=req-1&t=tok%2Fen%2B");
});

function panel(request, routes, extra = {}) {
  const h = harness();
  const clipboard = [];
  const C = load(h, { location: { origin: "https://ctm.example" }, navigator: { clipboard: { writeText: async (v) => clipboard.push(v) } }, ...extra });
  const calls = [];
  const changed = [];
  const api = async (url, options = {}) => {
    calls.push({ url, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : undefined });
    const out = routes(url, options);
    if (out instanceof Error) throw out;
    return out;
  };
  const props = { api, lang: extra.lang || "en", request, canWrite: true, onChanged: (n) => changed.push(n) };
  const ui = {
    C, calls, changed, clipboard,
    tree: h.render(C.ExternalLinkPanel, props),
    rerender() { ui.tree = h.render(C.ExternalLinkPanel, props); return ui.tree; },
    async click(label) { const b = buttons(ui.tree, label)[0]; assert.ok(b, `button "${label}"`); await b.props.onClick(); await settle(); ui.rerender(); },
    async confirm() { const d = dialogs(ui.tree).find((x) => x.props.open); assert.ok(d, "confirmation"); await d.props.onConfirm(); await settle(); ui.rerender(); },
    text() { return textOf(ui.tree); },
    input(label) { return find(ui.tree, (n) => n.props && n.props.label === label)[0]; },
  };
  return ui;
}

const draft = { id: "req-1", kind: "external_priest", state: "draft", title: "Report by Fr. Synthetic Priest", request_version: 3 };

test("issuing asks first, sends name and email, shows the link once and says it was not emailed", async () => {
  const ui = panel(draft, () => ({ id: "req-1", token: "secret-token" }));
  await ui.click("Issue private link");
  assert.equal(ui.calls.length, 0, "confirmation first");
  await ui.confirm();
  assert.deepEqual(ui.calls[0], { url: "/api/requests/req-1/send/", method: "POST", body: { external_name: "Synthetic Priest", external_email: "" } });
  const field = find(ui.tree, (n) => n.props && n.props.readOnly === true)[0];
  assert.equal(field.props.value, "https://ctm.example/static/ctm/external-report.html#r=req-1&t=secret-token");
  assert.match(textOf(ui.tree), /shown only once/);
  assert.match(textOf(ui.tree), /does not email the link/);
  await ui.click("Copy link");
  assert.deepEqual(ui.clipboard, [field.props.value]);
  assert.ok(buttons(ui.tree, "Copied")[0]);
});

test("a missing token is never presented as a sent link", async () => {
  const ui = panel(draft, () => ({ id: "req-1", token: null }));
  await ui.click("Issue private link");
  await ui.confirm();
  assert.equal(find(ui.tree, (n) => n.props && n.props.readOnly === true).length, 0);
  assert.match(notices(ui.tree).join(" "), /did not return a link/);
});

test("reissue warns that the earlier link stops working; cancel sends the request version", async () => {
  const sent = { ...draft, state: "sent" };
  const ui = panel(sent, (url) => (url.endsWith("/send/") ? { id: "req-1", token: "new-token" } : { id: "req-1" }));
  await ui.click("Issue a new link");
  const reissue = dialogs(ui.tree).find((d) => d.props.open);
  assert.match(reissue.props.message, /earlier link stops working immediately/);
  await ui.confirm();
  assert.match(find(ui.tree, (n) => n.props && n.props.readOnly === true)[0].props.value, /t=new-token$/);
  await ui.click("Cancel request");
  await ui.confirm();
  assert.deepEqual(ui.calls.at(-1), { url: "/api/requests/req-1/cancel/", method: "POST", body: { expected_version: 3 } });
  assert.deepEqual(ui.changed.at(-1), "externalCancelled");
});

test("completed or cancelled requests offer no link controls", async () => {
  const done = panel({ ...draft, state: "completed" }, () => assert.fail("no call"));
  assert.equal(buttons(done.tree, "Issue private link").length + buttons(done.tree, "Issue a new link").length, 0);
  assert.match(notices(done.tree).join(" "), /submitted\. It appears under Completed reports/);
  const closed = panel({ ...draft, state: "cancelled" }, () => assert.fail("no call"));
  assert.match(notices(closed.tree).join(" "), /request is closed/);
});

test("Arabic wording for the link panel", async () => {
  const ui = panel(draft, () => ({ id: "req-1", token: "t" }), { lang: "ar" });
  assert.match(ui.text(), /الرابط الخاص بالكاهن/);
  assert.ok(buttons(ui.tree, "إصدار رابط خاص")[0]);
});

test("the token is never stored, logged or put in messages by council code", () => {
  for (const f of ["council.js", "council-case.js", "council-decree.js", "council-media.js"]) {
    const src = fs.readFileSync(`static/ctm/${f}`, "utf8");
    assert.doesNotMatch(src, /localStorage|sessionStorage|console\.log\([^)]*token/, f);
  }
  const src = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const panelSrc = src.slice(src.indexOf("function ExternalLinkPanel("), src.indexOf("function RequestDetail("));
  assert.doesNotMatch(panelSrc, /unsavedDrafts|\/api\/cases\/[^`]*messages/);
});

// Backend c377706: council rows carry external_link {priest_name, expires_at, state, can_issue, can_reissue, can_cancel}.
const projected = (link, state = "sent") => ({ ...draft, state, external_link: { priest_name: "Synthetic Priest", expires_at: null, can_issue: false, can_reissue: false, can_cancel: false, ...link } });

test("link controls follow the server's projection, not the client's guess", () => {
  const C = load(harness());
  const c = C.linkControls(projected({ state: "active", expires_at: "2026-11-21T08:00:00Z", can_reissue: true, can_cancel: true }), false);
  assert.deepEqual({ ...c }, { projected: true, state: "active", priestName: "Synthetic Priest", expiresAt: "2026-11-21T08:00:00Z", issue: false, reissue: true, cancel: true });
  // canWrite=true on the client does not grant what the server withholds (e.g. closed case).
  const closed = C.linkControls(projected({ state: "closed" }), true);
  assert.equal(closed.reissue || closed.cancel || closed.issue, false);
  // Older servers without the projection keep the request-state fallback.
  assert.equal(C.linkControls({ ...draft, state: "sent" }, true).reissue, true);
  assert.equal(C.linkControls({ ...draft, state: "sent" }, true).projected, false);
});

test("projected active link: priest, state and expiry shown; only permitted controls offered", () => {
  const ui = panel(projected({ state: "active", expires_at: "2026-11-21T08:00:00Z", can_reissue: true, can_cancel: true }), () => ({}));
  assert.match(ui.text(), /Synthetic Priest/);
  assert.match(ui.text(), /Active/);
  assert.match(ui.text(), /Expires/);
  assert.ok(buttons(ui.tree, "Issue a new link")[0]);
  assert.ok(buttons(ui.tree, "Cancel request")[0]);
  assert.equal(buttons(ui.tree, "Issue private link").length, 0);
});

test("projected expired link explains itself; reissue only when the server allows it", () => {
  const allowed = panel(projected({ state: "expired", expires_at: "2026-10-01T08:00:00Z", can_reissue: true, can_cancel: true }), () => ({}));
  assert.match(notices(allowed.tree).join(" "), /This link has expired\. Issue a new link/);
  assert.match(allowed.text(), /Expired on/);
  assert.ok(buttons(allowed.tree, "Issue a new link")[0]);
  const reader = panel(projected({ state: "expired", expires_at: "2026-10-01T08:00:00Z" }), () => ({}));
  assert.match(notices(reader.tree).join(" "), /assigned case manager can issue a new link/);
  assert.equal(buttons(reader.tree, "Issue a new link").length, 0);
});

test("projected terminal and unavailable states show no controls", () => {
  for (const [state, pattern] of [["completed", /submitted/], ["cancelled", /request is closed/], ["closed", /request is closed/], ["unavailable", /cannot be used/]]) {
    const ui = panel(projected({ state }), () => assert.fail("no call"));
    assert.match(notices(ui.tree).join(" "), pattern, state);
    assert.equal(buttons(ui.tree, "Issue private link").length + buttons(ui.tree, "Issue a new link").length + buttons(ui.tree, "Cancel request").length, 0, state);
  }
});

test("Arabic link states", () => {
  const ui = panel(projected({ state: "active", can_reissue: true }), () => ({}), { lang: "ar" });
  assert.match(ui.text(), /نشط/);
  assert.ok(buttons(ui.tree, "إصدار رابط جديد")[0]);
});

test("expiry is shown only for an active or expired link (real-backend finding)", () => {
  const cancelled = panel(projected({ state: "cancelled", expires_at: "2026-11-21T08:00:00Z" }), () => ({}));
  assert.doesNotMatch(cancelled.text(), /Expires|Expired on/);
  const active = panel(projected({ state: "active", expires_at: "2026-11-21T08:00:00Z" }), () => ({}));
  assert.match(active.text(), /Expires/);
});
