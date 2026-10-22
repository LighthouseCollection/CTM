// C-02 (#3): revision conflicts and safe retry, against the backend #7 contract:
//   POST /api/reports/{id}/revisions/ {expected_version, answers, observations}
//   201 {id, version} for a new save AND for an exact replay (same expected_version, same content, same author)
//   409 {error:"version_conflict", current_version} when stale; 409 {error:"conflict"} on a write race
//   403 {detail}, 422 {messages}, 401, 404; no status = network failure (outcome unknown)
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { harness, load, find, textareas, notices, buttons, dialogs, type, settle, byName, textOf } = require("./harness.cjs");

const report = { id: "rep-1", title: "Interview", kind: "interview", version: 1, can_revise: true,
  questions: [{ code: "Q1", en: "Question one?" }], answers: { Q1: "Original.", attendance: ["applicant"] }, observations: "Obs." };
const v1 = { version: 1, answers: report.answers, observations: "Obs.", actor: "Synthetic Author", timestamp: "2026-10-21T18:00:00Z" };
const v2other = { version: 2, answers: { Q1: "Edited in another session.", attendance: ["applicant"] }, observations: "Obs.", actor: "Synthetic Author", timestamp: "2026-10-21T19:00:00Z" };
const fail = (status, data = {}) => Object.assign(new Error(`HTTP ${status}`), { status, data });

// A scripted server: `history` is what GET returns (newest first); `onPost` decides each POST.
function server(history, onPost) {
  const calls = [];
  const api = async (url, options) => {
    if (options && options.method === "POST") {
      const body = JSON.parse(options.body);
      calls.push({ method: "POST", body });
      return onPost(body, calls.filter((c) => c.method === "POST").length);
    }
    calls.push({ method: "GET" });
    return { items: history() };
  };
  return { api, calls, posts: () => calls.filter((c) => c.method === "POST").map((c) => c.body) };
}

function editor(api, extra = {}) {
  const h = harness();
  const C = load(h);
  const events = { saved: [], cancelled: 0, denied: 0 };
  const props = {
    api, lang: extra.lang || "en", report, latest: v1, restored: false,
    onCancel: () => events.cancelled++, onSaved: (v) => events.saved.push(v), onHistory() {}, onDenied: () => events.denied++,
  };
  const ui = {
    C, events,
    tree: h.render(C.ReportRevisionEditor, props),
    rerender() { ui.tree = h.render(C.ReportRevisionEditor, props); return ui.tree; },
    typeAnswer(text) { type(textareas(ui.tree)[0], text); ui.rerender(); },
    async save() { await ui.tree.props.onSubmit({ preventDefault() {} }); await settle(); ui.rerender(); },
    click(label) { const b = buttons(ui.tree, label)[0]; assert.ok(b, `button "${label}"`); b.props.onClick(); ui.rerender(); },
    text() { return textareas(ui.tree)[0].props.value; },
    notes() { return notices(ui.tree).join(" | "); },
    saveButton() { return find(ui.tree, (n) => n.props && n.props.type === "submit")[0] || null; },
    dialog(title) { return dialogs(ui.tree).find((d) => d.props.open && (!title || d.props.title.includes(title))); },
  };
  return ui;
}

test("409 version_conflict: text kept, conflict explained, nothing resubmitted, Save withheld", async () => {
  let newest = [v1];
  const srv = server(() => newest, () => { newest = [v2other, v1]; throw fail(409, { error: "version_conflict", current_version: 2 }); });
  const ui = editor(srv.api);
  ui.typeAnswer("My unsaved narrative.");
  await ui.save();
  assert.equal(srv.posts().length, 1, "no automatic resubmission");
  assert.equal(srv.posts()[0].expected_version, 1);
  assert.equal(ui.text(), "My unsaved narrative.");
  assert.match(ui.notes(), /Version 2 was saved by .*Synthetic Author.* after you started editing\. Your text is kept/);
  assert.equal(ui.saveButton(), null, "plain Save is replaced by explicit choices");
  assert.equal(ui.events.saved.length, 0, "no false success");
  assert.equal(ui.C.unsavedDrafts.get("revision:rep-1").draft.answers.Q1, "My unsaved narrative.", "S10 retention during conflict");
});

test("conflict: the newer version can be inspected without losing or rebasing the text", async () => {
  const srv = server(() => [v2other, v1], () => assert.fail("must not POST"));
  const ui = editor(srv.api);
  ui.typeAnswer("My unsaved narrative.");
  await ui.save(); // early check finds v2
  assert.equal(srv.posts().length, 0);
  ui.click("Show version 2");
  const panel = byName(ui.tree, "Panel").map(textOf).join(" ");
  assert.match(panel, /Edited in another session\./);
  assert.equal(ui.text(), "My unsaved narrative.");
  ui.click("Hide version 2");
  assert.equal(byName(ui.tree, "Panel").length, 0);
});

test("conflict: saving over the newer version is deliberate, confirmed, and bound to that version", async () => {
  let created = null;
  const srv = server(() => (created ? [created, v2other, v1] : [v2other, v1]), (body) => {
    created = { version: 3, answers: body.answers, observations: body.observations };
    return { id: "rv-3", version: 3 };
  });
  const ui = editor(srv.api);
  ui.typeAnswer("My unsaved narrative.");
  await ui.save();
  ui.click("Save my text as a new version");
  assert.equal(srv.posts().length, 0, "nothing sent before confirmation");
  const confirm = ui.dialog("version 3");
  assert.ok(confirm, "confirmation names the new version");
  await confirm.props.onConfirm();
  await settle();
  assert.equal(srv.posts().length, 1);
  assert.equal(srv.posts()[0].expected_version, 2, "bound to the version the author reviewed");
  assert.equal(srv.posts()[0].answers.Q1, "My unsaved narrative.");
  assert.deepEqual([...srv.posts()[0].answers.attendance], ["applicant"]);
  assert.deepEqual(ui.events.saved, [3]);
});

test("conflict: discarding needs confirmation and clears the kept text", async () => {
  const srv = server(() => [v2other, v1], () => assert.fail("must not POST"));
  const ui = editor(srv.api);
  ui.typeAnswer("My unsaved narrative.");
  await ui.save();
  ui.click("Discard my changes");
  assert.equal(ui.events.cancelled, 0);
  ui.dialog("Discard").props.onConfirm();
  assert.equal(ui.events.cancelled, 1);
  assert.equal(ui.C.unsavedDrafts.has("revision:rep-1"), false);
});

test("lost acknowledgement: no false success; Try again resends the identical request and the server replay confirms it", async () => {
  let stored = null;
  const srv = server(() => (stored ? [stored, v1] : [v1]), (body, n) => {
    if (n === 1) {
      stored = { version: 2, answers: body.answers, observations: body.observations, actor: "Synthetic Author" };
      throw new TypeError("Failed to fetch"); // committed, but the reply never arrived
    }
    return { id: "rv-2", version: 2 }; // exact replay returns the retained revision
  });
  const ui = editor(srv.api);
  ui.typeAnswer("Narrative whose reply was lost.");
  await ui.save();
  assert.equal(ui.events.saved.length, 0, "network failure is not reported as a save");
  assert.match(ui.notes(), /did not confirm this save/);
  assert.equal(ui.text(), "Narrative whose reply was lost.");
  assert.equal(textOf(ui.saveButton()).trim(), "Try again");
  const getsBefore = srv.calls.filter((c) => c.method === "GET").length;
  await ui.save();
  assert.equal(srv.calls.filter((c) => c.method === "GET").length, getsBefore, "retry skips the early check that would misread our own save as a conflict");
  assert.equal(srv.posts().length, 2);
  assert.deepEqual(srv.posts()[1], srv.posts()[0], "identical version and content");
  assert.deepEqual(ui.events.saved, [2]);
  assert.equal(ui.C.unsavedDrafts.has("revision:rep-1"), false);
});

test("lost acknowledgement then edits: our earlier save is recognised, later edits stay unsaved, nothing auto-sent", async () => {
  let stored = null;
  const srv = server(() => (stored ? [stored, v1] : [v1]), (body) => {
    stored = { version: 2, answers: body.answers, observations: body.observations, actor: "Synthetic Author" };
    throw fail(504, {});
  });
  const ui = editor(srv.api);
  ui.typeAnswer("First text.");
  await ui.save();
  ui.typeAnswer("First text, then more.");
  await ui.save();
  assert.equal(srv.posts().length, 1, "no automatic second POST");
  assert.match(ui.notes(), /earlier save was received as version 2\. Changes you made after it are not saved yet/);
  assert.equal(ui.text(), "First text, then more.");
  assert.equal(textOf(ui.saveButton()).trim(), "Save as new version");
});

test("lost acknowledgement, retry answered 409 by our own stored save: confirmed, not a conflict", async () => {
  let stored = null;
  const srv = server(() => (stored ? [stored, v1] : [v1]), (body, n) => {
    if (n === 1) { stored = { version: 2, answers: body.answers, observations: body.observations }; throw fail(502); }
    throw fail(409, { error: "conflict", detail: "The operation conflicts with another saved record." });
  });
  const ui = editor(srv.api);
  ui.typeAnswer("Text.");
  await ui.save();
  await ui.save();
  assert.deepEqual(ui.events.saved, [2]);
});

test("403, 422, 401 and 404 keep the text with actionable messages; only 403/404 withhold Save", async () => {
  const cases = [
    [fail(403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." }), /not allowed/, false],
    [fail(422, { error: "validation", messages: ["Answer every requested question."] }), /Answer every requested question\. Correct the text and save again/, true],
    [fail(401, { error: "authentication_required" }), /session has ended/, true],
    [fail(404, { error: "resource_or_input_invalid" }), /no longer available/, false],
  ];
  for (const [error, message, saveShown] of cases) {
    const srv = server(() => [v1], () => { throw error; });
    const ui = editor(srv.api);
    ui.typeAnswer("Kept text.");
    await ui.save();
    assert.equal(ui.text(), "Kept text.", `status ${error.status}`);
    assert.match(ui.notes(), message, `status ${error.status}`);
    assert.equal(Boolean(ui.saveButton()), saveShown, `status ${error.status}`);
    assert.equal(ui.events.saved.length, 0);
    if (error.status === 403) assert.equal(ui.events.denied, 1, "rows refresh so Revise disappears");
  }
});

test("Arabic: conflict and retry messages are translated", async () => {
  const srv = server(() => [v2other, v1], () => assert.fail("must not POST"));
  const ui = editor(srv.api, { lang: "ar" });
  ui.typeAnswer("نص غير محفوظ.");
  await ui.save();
  assert.match(ui.notes(), /الإصدار 2/);
  assert.ok(buttons(ui.tree, "عرض الإصدار 2").length);
  assert.equal(ui.text(), "نص غير محفوظ.");
});
