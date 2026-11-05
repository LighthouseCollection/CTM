// #97 slice 5: the applicant screens on the Plenix 0.86.0 templates (Wizard + DraftState, FileList,
// ResourceList, CTMShell Table/Workspace). Real module code in the minimal render harness.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { harness, find, textOf, byName, buttons, settle, nameOf } = require("./harness.cjs");

const PLENIX = Symbol.for("ctm.test.plenix");
const named = name => new Proxy(function () {}, { get: (_t, key) => key === PLENIX ? true : key === "displayName" ? name : named(`${name}.${String(key)}`) });
const Plenix = new Proxy({}, { get: (_t, key) => named(String(key)) });
const Shell = { Table: named("CTMShell.Table"), Workspace: named("CTMShell.Workspace"), Listing: named("CTMShell.Listing") };

function load(h, files, extra = {}) {
  const window = { React: h.React, Plenix, CTMShell: Shell, addEventListener() {}, removeEventListener() {},
    crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000000" }, ...extra };
  const context = { window, console, structuredClone, Intl, URL, FormData: class {} };
  for (const file of files) vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), context);
  return window;
}
const uuid = n => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const time = "2026-11-01T10:00:00Z";
async function draw(h, component, props, rounds = 3) {
  let tree = h.render(component, props);
  for (let i = 0; i < rounds; i++) { await settle(); tree = h.render(component, props); }
  return tree;
}

const application = () => ({
  id: "draft-a", status: "draft", version: 3, can_edit: true,
  answers: { first_name: "Original" },
  questionnaire: { id: "form-a", version: 1, published: true, definition: { fields: [
    { code: "first_name", type: "text", required: true, label_en: "First name", label_ar: "الاسم الأول" },
    { code: "story", type: "textarea", label_en: "Your statement", label_ar: "بيانك" },
    { code: "married_on", type: "date", label_en: "Marriage date", label_ar: "تاريخ الزواج" },
  ] } },
});

test("application form is a Wizard: answers in the server's order, documents, then the review summary", async () => {
  const h = harness();
  const w = load(h, ["applicant.js"], { CTMApplicantFiles: { ApplicationFiles: named("Files") }, CTMApplicantFiling: { FilingActions: named("Filing") } });
  const tree = await draw(h, w.CTMApplicant.ApplicationEditor, { applicationId: "draft-a", api: async () => application(), lang: "en" });
  const [wizard] = byName(tree, "Wizard");
  assert.ok(wizard, "the form renders a Plenix Wizard");
  assert.equal(wizard.props.steps.map(s => s.id).join("|"), ["answers", "documents"].join("|"));
  assert.equal(wizard.props.steps.map(s => s.label).join("|"), ["Your answers", "Documents"].join("|"));
  assert.equal(wizard.props.strings.complete, "Review answers");
  assert.equal(wizard.props.strings.next, "Next");
  // The questions keep the published order; required stays announced but never blocks an incomplete draft.
  const fields = byName(wizard.props.steps[0].content, "Field");
  assert.equal(fields.map(f => f.props.label).join("|"), ["First name", "Your statement", "Marriage date"].join("|"));
  assert.equal(fields[0].props.required, true);
  const input = byName(fields[0], "Input")[0];
  assert.equal(input.props.required, false);
  assert.equal(input.props["aria-required"], true);
  assert.equal(byName(wizard.props.steps[1].content, "Files").length, 1);
  assert.match(textOf(wizard.props.summary), /Original/);
  // Filing waits for the review, as before; completing the wizard is the review.
  assert.equal(byName(tree, "Filing")[0].props.reviewed, false);
  await wizard.props.onComplete();
  const after = h.render(w.CTMApplicant.ApplicationEditor, { applicationId: "draft-a", api: async () => application(), lang: "en" });
  assert.equal(byName(after, "Filing")[0].props.reviewed, true);
  assert.equal(byName(byName(after, "Wizard")[0].props.steps[0].content, "Input").length, 0, "reviewed answers are read-only");
  assert.equal(buttons(after, "Continue editing").length, 1);
});

test("DraftState shows the saved version and offers discard only for unsaved edits", async () => {
  const h = harness();
  let loads = 0;
  const api = async () => { loads++; return application(); };
  const w = load(h, ["applicant.js"]);
  const props = { applicationId: "draft-a", api, lang: "ar" };
  let tree = await draw(h, w.CTMApplicant.ApplicationEditor, props);
  let [draft] = byName(tree, "DraftState");
  assert.equal(draft.props.version, 3);
  assert.equal(draft.props.strings.draft, "مسودة");
  assert.equal(draft.props.onDiscard, undefined);
  const input = byName(byName(tree, "Wizard")[0].props.steps[0].content, "Input")[0];
  input.props.onChange({ target: { value: "Changed" } });
  tree = h.render(w.CTMApplicant.ApplicationEditor, props);
  [draft] = byName(tree, "DraftState");
  assert.equal(typeof draft.props.onDiscard, "function");
  assert.equal(draft.props.strings.confirm, "هل تريد تجاهل التغييرات غير المحفوظة؟");
  const before = loads;
  await draft.props.onDiscard();
  await draw(h, w.CTMApplicant.ApplicationEditor, props);
  assert.equal(loads, before + 1, "discard reloads the saved answers from the server");
});

test("read-only applications keep the review step and no draft controls", async () => {
  const h = harness();
  const w = load(h, ["applicant.js"]);
  const app = { ...application(), status: "accepted", can_edit: false };
  const tree = await draw(h, w.CTMApplicant.ApplicationEditor, { applicationId: "draft-a", api: async () => app, lang: "en" });
  assert.equal(byName(tree, "DraftState").length, 0);
  assert.equal(byName(tree, "Wizard").length, 1);
  assert.equal(buttons(tree, "Save draft").length, 0);
});

test("released decrees are a FileList that links only clean signed originals", async () => {
  const h = harness();
  const opened = [];
  const w = load(h, ["applicant-decrees.js"], { open: (...args) => opened.push(...args) });
  const caseId = uuid(1), fileId = uuid(2);
  const data = { id: caseId, released_decrees: [{ id: uuid(3), reference: "DCR-2026-001", language: "bilingual", released_at: time,
    signed_file: { id: fileId, name: "decree.pdf", scan_state: "clean", download_url: `/api/files/${fileId}/` } }] };
  const tree = await draw(h, w.CTMApplicantDecrees.ReleasedDecrees, { caseId, api: async () => data, lang: "en" });
  const [list] = byName(tree, "FileList");
  assert.ok(list);
  assert.equal(list.props.files[0].name, "DCR-2026-001");
  assert.equal(list.props.files[0].status.label, "English and Arabic");
  list.props.onOpen(list.props.files[0]);
  assert.equal(opened.join(" "), `/api/files/${fileId}/ _blank noopener,noreferrer`);
});

test("application documents list uploaded originals in a FileList per requirement", async () => {
  const h = harness();
  const w = load(h, ["applicant-files.js"]);
  const id = uuid(5);
  const listing = { can_upload: false, requirements: [{ category: "MC", context: "", required: true, label_en: "Marriage certificate", label_ar: "شهادة الزواج" }],
    items: [{ id, attachment_id: uuid(6), name: "mc.pdf", category: "MC", context: "", scan_state: "clean", download_url: `/api/files/${id}/` }] };
  const tree = await draw(h, w.CTMApplicantFiles.ApplicationFiles, { applicationId: "a", answerVersion: 1, api: async () => listing, lang: "en" });
  const [list] = byName(tree, "FileList");
  assert.ok(list);
  assert.equal(list.props.files[0].name, "mc.pdf");
  assert.equal(list.props.files[0].status.label, "Safety checks passed");
  assert.equal(list.props.hrefFor(list.props.files[0]), `/api/files/${id}/`);
});

test("notifications are a ResourceList with the read state and actions on each row", async () => {
  const h = harness();
  const w = load(h, ["applicant-notifications.js"]);
  const page = { items: [{ id: uuid(7), kind: "case_update", read: false, timestamp: time, case_id: uuid(8), case_number: "20261101-01" }], unread_count: 1, next_offset: null };
  const tree = await draw(h, w.CTMApplicantNotifications.Inbox, { api: async () => page, lang: "en" });
  const [list] = byName(tree, "ResourceList");
  assert.ok(list);
  assert.equal(list.props.items[0].name, "20261101-01");
  assert.match(textOf(list.props.items[0].meta), /Unread/);
  assert.equal(buttons(list.props.items[0].actions, "Mark notification as read").length, 1);
  assert.equal(buttons(list.props.items[0].actions, "Open case").length, 1);
});

test("appointments are a CTMShell workspace: invitations list and the chosen invitation", async () => {
  const h = harness();
  const w = load(h, ["applicant-appointments.js"]);
  const row = { id: uuid(9), case_id: uuid(10), case_number: "20261101-02", starts_at: "2026-11-10T10:00:00Z", ends_at: "2026-11-10T11:00:00Z",
    instructions: "Bring ID", version: 1, state: "invited", can_respond: true, response: null };
  const tree = await draw(h, w.CTMApplicantAppointments.Appointments, { api: async () => ({ items: [row] }), lang: "en" });
  const [workspace] = find(tree, n => nameOf(n.type) === "CTMShell.Workspace");
  assert.ok(workspace);
  assert.equal(workspace.props.rows[0].id, row.id);
  assert.equal(workspace.props.selected, row.id, "the first invitation opens by default");
});

test("requests are a CTMShell workspace with instructions in the reading pane", async () => {
  const h = harness();
  const w = load(h, ["applicant-requests.js"]);
  const row = { id: uuid(11), title: "Written questions", kind: "intake", state: "sent", language: "en", instructions: "Answer all", sent_at: time,
    questions: [{ code: "q1", version: 1, en: "Why?" }] };
  const tree = await draw(h, w.CTMApplicantRequests.Requests, { caseId: uuid(12), api: async () => ({ items: [row] }), lang: "en" });
  const [workspace] = find(tree, n => nameOf(n.type) === "CTMShell.Workspace");
  assert.ok(workspace);
  assert.equal(workspace.props.rows[0].title, "Written questions");
  assert.match(textOf(workspace.children), /Answer all/);
});

test("payment history shows checkout attempts and events as CTMShell tables, never a success of its own", async () => {
  const h = harness();
  const w = load(h, ["applicant-payments.js"]);
  const data = { fee: { amount_minor: 25000, currency: "USD", status: "due" }, verified_payment: false,
    checkouts: [{ id: "c1", state: "expired", version: 2, timestamp: time }],
    events: [{ id: "e1", kind: "refunded", amount_minor: 100, currency: "USD", timestamp: time, amount_basis: "cumulative_refunded" }] };
  const tree = await draw(h, w.CTMApplicantPayments.PaymentHistory, { applicationId: "a", api: async () => data, lang: "en" });
  const tables = find(tree, n => nameOf(n.type) === "CTMShell.Table");
  assert.equal(tables.length, 2);
  assert.match(textOf(tree), /No verified provider payment is recorded/);
});

test("answer history lists the changed saved values in one CTMShell table", async () => {
  const h = harness();
  const w = load(h, ["applicant-history.js"]);
  const data = { items: [{ id: uuid(13), version: 1, actor: "Applicant", timestamp: time, answers: { first_name: "A" } },
    { id: uuid(14), version: 2, actor: "Applicant", timestamp: time, answers: { first_name: "B" } }] };
  const tree = await draw(h, w.CTMApplicantHistory.History, { applicationId: uuid(15), currentVersion: 2, api: async () => data, lang: "en",
    currentFields: [{ code: "first_name", label_en: "First name", label_ar: "الاسم الأول" }] });
  const [table] = find(tree, n => nameOf(n.type) === "CTMShell.Table");
  assert.ok(table);
  assert.equal(table.props.rows[0].id, "/first_name");
  assert.equal(table.props.columns.map(c => c.render(table.props.rows[0])).join("|"), 'First name|/first_name|"A"|"B"');
});

test("an empty invitations or requests list is one EmptyState, not an empty split view", async () => {
  for (const [file, name, props] of [["applicant-appointments.js", "Appointments", {}], ["applicant-requests.js", "Requests", { caseId: uuid(16) }]]) {
    const h = harness();
    const w = load(h, [file]);
    const module = file.includes("appointments") ? w.CTMApplicantAppointments : w.CTMApplicantRequests;
    const tree = await draw(h, module[name], { ...props, api: async () => ({ items: [] }), lang: "ar" });
    assert.equal(find(tree, n => nameOf(n.type) === "CTMShell.Workspace").length, 0);
    assert.equal(byName(tree, "EmptyState").length, 1);
  }
});
