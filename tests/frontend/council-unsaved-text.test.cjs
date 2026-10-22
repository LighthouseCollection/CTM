// Regression for QA-01 S10 (#15, #3): unsaved report text must survive in-app (sidebar) navigation.
// Sidebar navigation unmounts the report page; remounting must restore the typed text.
// Renders the real components with a minimal hook harness (no browser, no React package).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function harness() {
  let states = [];
  let index = 0;
  let effects = [];
  const React = {
    useState(init) {
      const i = index++;
      if (!(i in states)) states[i] = typeof init === "function" ? init() : init;
      return [states[i], (v) => { states[i] = typeof v === "function" ? v(states[i]) : v; }];
    },
    useEffect(fn) { effects.push(fn); },
    createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }),
  };
  return {
    React,
    render(component, props) {
      index = 0;
      effects = [];
      const tree = component(props);
      effects.forEach((f) => f());
      return tree;
    },
    unmount() { states = []; }, // what sidebar navigation does to the page's component state
  };
}

// Any Plenix component is a named placeholder; nested names (PropertyList.Item) work too.
const named = (name) => new Proxy(function () {}, { get: (_t, key) => (key === "displayName" ? name : named(`${name}.${String(key)}`)) });
const Plenix = new Proxy({}, { get: (_t, key) => named(String(key)) });
const nameOf = (type) => (type && type.displayName) || "";

function load(h) {
  const window = { React: h.React, Plenix, addEventListener() {}, removeEventListener() {} };
  const context = { window, console };
  for (const file of ["council.js", "council-case.js", "council-decree.js", "council-media.js"])
    vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), context);
  return window.CTMCouncil;
}

// Walks children and element-valued props (Tabs items[].content, SplitView first/second, ...).
function find(tree, predicate, out = []) {
  if (!tree || typeof tree !== "object") return out;
  if (Array.isArray(tree)) {
    for (const item of tree) find(item, predicate, out);
    return out;
  }
  if ("type" in tree && "props" in tree) {
    if (predicate(tree)) out.push(tree);
    for (const child of tree.children || []) find(child, predicate, out);
    for (const value of Object.values(tree.props)) if (value && typeof value === "object") find(value, predicate, out);
    return out;
  }
  for (const value of Object.values(tree)) if (value && typeof value === "object") find(value, predicate, out);
  return out;
}
const textareas = (tree) => find(tree, (n) => nameOf(n.type) === "Textarea");
const notices = (tree) => find(tree, (n) => nameOf(n.type) === "Notice").map((n) => n.children.join(""));
const buttons = (tree, label) => find(tree, (n) => nameOf(n.type) === "Button" && n.children.join("") === label);
const dialog = (tree) => find(tree, (n) => nameOf(n.type) === "ConfirmDialog")[0];
const type = (area, value) => area.props.onChange({ target: { value } });

const report = { id: "rep-1", title: "Interview", kind: "interview", version: 1, can_revise: true,
  questions: [{ code: "Q1", en: "Question one?" }], answers: { Q1: "Original.", attendance: ["applicant"] }, observations: "Obs." };
const latest = { version: 1, answers: report.answers, observations: "Obs." };

test("revision editor: typed text survives unmount (sidebar navigation) and is restored with a notice", () => {
  const h = harness();
  const C = load(h);
  const props = { api: async () => ({ items: [latest] }), lang: "en", report, latest, onCancel() {}, onSaved() {}, onHistory() {}, onDenied() {} };
  let tree = h.render(C.ReportRevisionEditor, props);
  type(textareas(tree)[0], "Unsaved narrative typed before navigating away.");
  tree = h.render(C.ReportRevisionEditor, props); // effects persist the draft
  h.unmount();
  // Reopening the report: the report tab reopens the editor by itself.
  const tabs = h.render(C.ReportDetailTabs, { api: props.api, lang: "en", user: { id: "u", portal: "council", role: "member" }, report, record: {}, onOriginal() {}, onRevised() {} });
  const editor = find(tabs, (n) => n.type === C.ReportRevisionEditor)[0];
  assert.ok(editor, "editor reopens automatically");
  assert.equal(editor.props.restored, true);
  h.unmount();
  tree = h.render(C.ReportRevisionEditor, { ...props, restored: true });
  assert.equal(textareas(tree)[0].props.value, "Unsaved narrative typed before navigating away.");
  assert.ok(notices(tree).some((n) => /restored/.test(n)));
});

test("revision editor: Cancel with unsaved text asks first; confirming discards the kept text", () => {
  const h = harness();
  const C = load(h);
  let cancelled = 0;
  const props = { api: async () => ({ items: [latest] }), lang: "en", report, latest, onCancel: () => cancelled++, onSaved() {}, onHistory() {}, onDenied() {} };
  let tree = h.render(C.ReportRevisionEditor, props);
  type(textareas(tree)[0], "Text to discard.");
  tree = h.render(C.ReportRevisionEditor, props);
  buttons(tree, "Cancel")[0].props.onClick();
  tree = h.render(C.ReportRevisionEditor, props);
  assert.equal(cancelled, 0, "nothing is discarded without confirmation");
  assert.equal(dialog(tree).props.open, true);
  dialog(tree).props.onConfirm();
  assert.equal(cancelled, 1);
  assert.equal(C.unsavedDrafts.has("revision:rep-1"), false);
});

test("revision editor: a successful save clears the kept text and keeps expected_version", async () => {
  const h = harness();
  const C = load(h);
  const posts = [];
  const api = async (url, options) => {
    if (options && options.method === "POST") { posts.push(JSON.parse(options.body)); return { id: "rv-2" }; }
    return { items: posts.length ? [{ ...latest, version: 2 }, latest] : [latest] };
  };
  let saved = null;
  const props = { api, lang: "en", report, latest, onCancel() {}, onSaved: (v) => { saved = v; }, onHistory() {}, onDenied() {} };
  let tree = h.render(C.ReportRevisionEditor, props);
  type(textareas(tree)[0], "Saved text.");
  tree = h.render(C.ReportRevisionEditor, props);
  assert.equal(C.unsavedDrafts.has("revision:rep-1"), true);
  await tree.props.onSubmit({ preventDefault() {} });
  assert.equal(posts.length, 1);
  assert.equal(posts[0].expected_version, 1); // integration's version binding is preserved
  assert.equal(posts[0].answers.Q1, "Saved text.");
  assert.deepEqual([...posts[0].answers.attendance], ["applicant"]);
  assert.equal(saved, 2);
  assert.equal(C.unsavedDrafts.has("revision:rep-1"), false);
});

test("revision editor: a failed save keeps the text for navigation and retry", async () => {
  const h = harness();
  const C = load(h);
  const api = async (url, options) => {
    if (options && options.method === "POST") { const e = new Error("x"); e.status = 500; e.data = {}; throw e; }
    return { items: [latest] };
  };
  const props = { api, lang: "en", report, latest, onCancel() {}, onSaved() {}, onHistory() {}, onDenied() {} };
  let tree = h.render(C.ReportRevisionEditor, props);
  type(textareas(tree)[0], "Must not be lost.");
  tree = h.render(C.ReportRevisionEditor, props);
  await tree.props.onSubmit({ preventDefault() {} });
  assert.equal(C.unsavedDrafts.get("revision:rep-1").draft.answers.Q1, "Must not be lost.");
});

test("interview answers: typed answers survive unmount and the form reopens with them", () => {
  const h = harness();
  const C = load(h);
  const request = { id: "rq-1", kind: "interview", state: "sent", title: "Interview", questions: [{ code: "Q1", en: "Question one?" }] };
  const props = { api: async () => ({}), lang: "en", request, onRecorded() {}, onCancel() {} };
  let tree = h.render(C.InterviewForm, props);
  type(textareas(tree)[0], "Interview answer typed before navigating away.");
  tree = h.render(C.InterviewForm, props);
  h.unmount();
  const detail = h.render(C.RequestDetail, { api: props.api, lang: "en", request, canWrite: true, onSent() {} });
  assert.ok(find(detail, (n) => n.type === C.InterviewForm).length, "answer form reopens automatically");
  h.unmount();
  tree = h.render(C.InterviewForm, props);
  assert.equal(textareas(tree)[0].props.value, "Interview answer typed before navigating away.");
  assert.ok(notices(tree).some((n) => /restored/.test(n)));
});

test("unsaved text stays in page memory only, never browser storage", () => {
  for (const file of ["council.js", "council-case.js", "council-media.js"]) {
    const source = fs.readFileSync(`static/ctm/${file}`, "utf8");
    assert.doesNotMatch(source, /localStorage|sessionStorage/, file);
  }
});
