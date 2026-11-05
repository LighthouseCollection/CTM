// Council lists and home on the Plenix 0.86.0 page templates (#97 slice 2, D-0034): listings with a command bar
// and row menus (phone row cards), FormFlow for sessions, SearchWorkspace, dashboard MetricCards in a
// WidgetGrid, Skeleton loading and read-only archives. Renders the real components with the test harness.
const { test } = require("node:test");
const assert = require("node:assert/strict");

const { harness, load, find, byName, settle, textOf } = require("./harness.cjs");

// CTMShell stand-ins (shell-layout.js has its own tests): they keep their props; Workspace draws the open item.
function Listing() { return null; }
function Table() { return null; }
function Workspace(props) {
  const draw = Array.isArray(props.children) ? props.children[0] : props.children;
  const chosen = (props.rows || []).find((row) => row.id === props.selected);
  return chosen && typeof draw === "function" ? draw(chosen) : null;
}
const shell = { CTMShell: { Listing, Table, Workspace } };
// The council pages are wrapped in an error boundary (a class component); the harness only needs its base.
function boot() {
  const h = harness();
  h.React.Component = class { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  return [h, load(h, shell)];
}
// Values from the module come from another realm, so compare them as data.
const same = (actual, expected) => assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected);
const one = (tree, type) => find(tree, (n) => n.type === type)[0];
const secretary = { id: "sec", portal: "council", role: "secretary" };
const admin = { id: "adm", portal: "council", role: "admin" };

async function rendered(h, C, component, props) {
  h.render(component, props);
  await settle();
  return h.render(component, props);
}

const cases = [
  { id: "c1", number: "20261020-01", status: "open", applicant_name: "James Carter", respondent_name: "Emily Carter", grounds: ["abandonment", "abuse"], reason: "abandonment; abuse", assigned_member: "Fr. David" },
  { id: "c2", number: "20261020-02", status: "closed", applicant_name: "Daniel Brooks", respondent_name: "Olivia Brooks", closed_at: "2026-10-30T10:00:00Z" },
];

test("loading is a Skeleton announced as busy, not a spinner", () => {
  const [h, C] = boot();
  const view = C.loadingView(new Proxy({}, { get: (_t, k) => k }), (type, props, ...children) => ({ type, props, children }), C.translator("en"));
  assert.equal(view.type, "Stack");
  assert.equal(view.props.role, "status");
  assert.equal(view.props["aria-busy"], "true");
  assert.equal(view.props["aria-label"], "Loading…");
  assert.ok(view.children.length >= 3 && view.children.every((child) => child.type === "Skeleton"));
});

test("case lists are a Listing with a searched command bar, row menu actions and row cards", () => {
  const [h, C] = boot();
  const opened = [];
  let tree = h.render(C.CasesTable, { api: async () => ({}), user: admin, cases, archived: false, view: "active", title: "All Active Cases", lang: "en", onOpen: (id) => opened.push(id) });
  let list = one(tree, Listing);
  assert.ok(list, "CTMShell.Listing");
  same(list.props.rows.map((row) => row.id), ["c1"]);
  assert.equal(list.props.search.placeholder, "Find a case by number or case manager");
  assert.match(list.props.search.storageKey, /cases\.active$/);
  assert.match(list.props.search.text(list.props.rows[0]), /James Carter/);
  assert.ok(!list.props.columns.some((column) => column.field === "open_action"), "no button column");
  const menu = list.props.rowMenu;
  same(menu.map((item) => item.label || "—"), ["Open", "—", "Delete"]);
  assert.equal(menu[2].danger, true);
  menu[0].onSelect(list.props.rows[0]);
  list.props.onOpen(list.props.rows[0]);
  same(opened, ["c1", "c1"]);
  same(list.props.cardCount, { one: "{n} case", other: "{n} cases" });
  assert.equal(list.props.template.title, "number");
  // "Show closed cases" is a toggle command in the bar
  const toggle = list.props.commandBar.actions.find((action) => action.id === "closed");
  assert.equal(toggle.toggle, true);
  assert.equal(toggle.pressed, false);
  toggle.onSelect(true);
  tree = h.render(C.CasesTable, { api: async () => ({}), user: admin, cases, archived: false, view: "active", title: "All Active Cases", lang: "en", onOpen() {} });
  same(one(tree, Listing).props.rows.map((row) => row.id), ["c1", "c2"]);
  // Delete opens the confirmation
  one(tree, Listing).props.rowMenu[2].onSelect({ id: "c1" });
  tree = h.render(C.CasesTable, { api: async () => ({}), user: admin, cases, archived: false, view: "active", title: "All Active Cases", lang: "en", onOpen() {} });
  assert.equal(byName(tree, "ConfirmDialog")[0].props.open, true);
});

// #120, D-0035: a case's grounds are shown as their EN/AR labels, never the stored code; the old code
// "desertion" from earlier filings reads as Abandonment; text that is not a ground code is shown as is.
test("case grounds show their English and Arabic labels, and the legacy desertion code reads as Abandonment", () => {
  const [h, C] = boot();
  const rows = [
    { ...cases[0] },
    { id: "c3", number: "20261020-03", status: "open", applicant_name: "A", respondent_name: "B", grounds: ["desertion", "infidelity", "faith", "addiction", "concealment"], reason: "desertion; infidelity; faith; addiction; concealment" },
    { id: "c4", number: "20261020-04", status: "open", applicant_name: "C", respondent_name: "D", grounds: [], reason: "Typed by an earlier filing" },
  ];
  const reasons = (lang) => {
    const tree = h.render(C.CasesTable, { api: async () => ({}), user: admin, cases: rows, archived: false, view: "active", title: "x", lang, onOpen() {} });
    return one(tree, Listing).props.rows.map((row) => row.reason);
  };
  same(reasons("en"), [
    "Abandonment; Abuse",
    "Abandonment; Infidelity; Leaving or changing the faith; Addiction; Misrepresentation or concealment before marriage",
    "Typed by an earlier filing",
  ]);
  same(reasons("ar"), [
    "الهجر؛ الإساءة",
    "الهجر؛ الخيانة الزوجية؛ ترك الإيمان أو تغييره؛ الإدمان؛ التحريف أو الإخفاء قبل الزواج",
    "Typed by an earlier filing",
  ]);
  for (const lang of ["en", "ar"]) for (const reason of reasons(lang)) assert.doesNotMatch(reason, /desertion|abandonment/);
  // the row is found by the words on screen
  const tree = h.render(C.CasesTable, { api: async () => ({}), user: admin, cases: rows, archived: false, view: "active", title: "x", lang: "ar", onOpen() {} });
  const list = one(tree, Listing);
  assert.match(list.props.search.text(list.props.rows[0]), /الهجر/);
  // every ground code has a distinct, non-English Arabic label
  const en = C.translator("en"), ar = C.translator("ar");
  for (const code of ["infidelity", "abandonment", "abuse", "faith", "addiction", "concealment"]) {
    assert.notEqual(ar(`ground_${code}`), `ground_${code}`);
    assert.notEqual(ar(`ground_${code}`), en(`ground_${code}`));
  }
});

test("members get Open only; archived cases are read-only and Arabic card counts use the six forms", () => {
  const [h, C] = boot();
  const tree = h.render(C.CasesTable, { api: async () => ({}), user: { id: "m", role: "member" }, cases, archived: true, view: "archived", title: "الأرشيف", lang: "ar", onOpen() {} });
  const readOnly = byName(tree, "ReadOnly")[0];
  assert.ok(readOnly, "ReadOnly region");
  assert.equal(readOnly.props.reason, "القضايا المغلقة للاطلاع فقط.");
  const list = one(readOnly, Listing);
  same(list.props.rows.map((row) => row.id), ["c2"]);
  same(list.props.rowMenu.map((item) => item.label), ["مفتوحة"]);
  assert.equal(list.props.commandBar, undefined);
  same(Object.keys(list.props.cardCount), ["zero", "one", "two", "few", "many", "other"]);
});

const sessionsApi = (sessions) => async (url) => url.startsWith("/api/sessions/") && !url.includes("/agenda/")
  ? { items: sessions }
  : url.startsWith("/api/council/members/") ? { items: [{ id: "pres", name: "H.E. Metropolitan Serapion", role: "president" }] }
  : { items: [] };
const future = [
  { id: "s1", date: "2099-01-10", state: "draft", starts_at: "2099-01-10T18:00:00Z" },
  { id: "s2", date: "2099-02-10", state: "planned", starts_at: "2099-02-10T18:00:00Z" },
];

test("upcoming sessions: Create in the command bar, Open/Edit/Delete in the row menu, the form is a FormFlow dialog", async () => {
  const [h, C] = boot();
  const opened = [];
  const props = { api: sessionsApi(future), lang: "en", user: secretary, mode: "upcoming", onOpen: (id) => opened.push(id), onCase() {} };
  let tree = await rendered(h, C, C.SessionList, props);
  const list = one(tree, Listing);
  assert.ok(list, "CTMShell.Listing");
  const create = list.props.commandBar.actions[0];
  assert.equal(create.label, "Create session");
  assert.equal(create.primary, true);
  const draftMenu = list.props.rowMenu(list.props.rows[0]);
  const plannedMenu = list.props.rowMenu(list.props.rows[1]);
  same(draftMenu.map((item) => item.label || "—"), ["Open", "Edit council session", "—", "Delete"]);
  assert.equal(draftMenu[3].danger, true);
  assert.equal(draftMenu[3].disabled, false);
  assert.equal(plannedMenu[3].disabled, true, "only draft sessions can be deleted");
  list.props.onOpen(list.props.rows[1]);
  same(opened, ["s2"]);
  // the form: closed until Create, then a FormFlow dialog inside a ToastProvider
  let flow = byName(tree, "FormFlow")[0];
  assert.equal(flow.props.open, false);
  assert.equal(flow.props.surface, "dialog");
  assert.ok(find(byName(tree, "ToastProvider"), (n) => n === flow).length, "FormFlow sits in a ToastProvider");
  create.onSelect();
  tree = h.render(C.SessionList, props);
  flow = byName(tree, "FormFlow")[0];
  assert.equal(flow.props.open, true);
  assert.equal(flow.props.mode, "create");
  assert.equal(flow.props.initialValue.location, "St. George Coptic Orthodox Church, Bellflower, California");
  assert.ok(flow.props.validate({ date: "", time: "10:00", location: "Church" }), "a missing date is refused");
  assert.equal(flow.props.validate({ date: "2099-03-01", time: "10:00", location: "Church" }), "");
  // Edit loads the row into the form in edit mode
  one(tree, Listing).props.rowMenu(one(tree, Listing).props.rows[1])[1].onSelect();
  tree = h.render(C.SessionList, props);
  flow = byName(tree, "FormFlow")[0];
  assert.equal(flow.props.mode, "edit");
  assert.equal(flow.props.initialValue.date, "2099-02-10");
  assert.equal(flow.props.strings.save, "Save changes");
  // Cancel closes it again
  flow.props.onCancel();
  tree = h.render(C.SessionList, props);
  assert.equal(byName(tree, "FormFlow")[0].props.open, false);
});

test("a refused session save keeps the server's reason in the form and rethrows for FormFlow", async () => {
  const [h, C] = boot();
  const base = sessionsApi(future);
  const api = async (url, options) => {
    if (options && options.method === "POST") { const error = new Error("taken"); error.status = 409; throw error; }
    return base(url);
  };
  const props = { api, lang: "en", user: secretary, mode: "upcoming", onOpen() {}, onCase() {} };
  let tree = await rendered(h, C, C.SessionList, props);
  one(tree, Listing).props.commandBar.actions[0].onSelect();
  tree = h.render(C.SessionList, props);
  await assert.rejects(byName(tree, "FormFlow")[0].props.onSubmit({ date: "2099-03-01", time: "10:00", location: "Church" }));
  tree = h.render(C.SessionList, props);
  const flow = byName(tree, "FormFlow")[0];
  const fields = flow.children[0]({ value: flow.props.initialValue, setValue() {}, busy: false });
  assert.match(textOf(fields), /already/i);
});

test("members see upcoming sessions without Create or edit commands", async () => {
  const [h, C] = boot();
  const tree = await rendered(h, C, C.SessionList, { api: sessionsApi(future), lang: "en", user: { id: "m", role: "member" }, mode: "upcoming", onOpen() {}, onCase() {} });
  const list = one(tree, Listing);
  assert.equal(list.props.commandBar, undefined);
  same(list.props.rowMenu.map((item) => item.label), ["Open"]);
  assert.equal(byName(tree, "FormFlow").length, 0);
});

test("archived sessions are a split workspace whose reading pane is read-only", async () => {
  const [h, C] = boot();
  const past = [{ id: "a1", date: "2020-01-10", state: "closed", starts_at: "2020-01-10T18:00:00Z" }];
  const props = { api: sessionsApi(past), lang: "en", user: secretary, mode: "archived", onOpen() {}, onCase() {} };
  let tree = await rendered(h, C, C.SessionList, props);
  const workspace = one(tree, Workspace);
  assert.ok(workspace, "CTMShell.Workspace");
  assert.equal(workspace.props.rows[0].title, "Council Session 2020-01-10");
  workspace.props.onSelect("a1");
  h.render(C.SessionList, props);
  await settle();
  tree = h.render(C.SessionList, props);
  const readOnly = byName(tree, "ReadOnly")[0];
  assert.ok(readOnly, "the archived record is read-only");
  assert.equal(readOnly.props.reason, "Archived sessions are read-only.");
  const tables = find(readOnly, (n) => n.type === Table);
  assert.equal(tables.length, 2);
  assert.ok(tables.every((table) => table.props.rowMenu[0].label === "Open"));
  assert.ok(tables.every((table) => !table.props.columns.some((column) => column.field === "case_id")), "no button column");
});

test("council home is a dashboard: MetricCards in a WidgetGrid, a missing count is never zero", async () => {
  const [h, C] = boot();
  const api = async (url) => url === "/api/dashboard/" ? { my_cases: 2, review_queue: 10, upcoming_sessions: [{ id: "s1", date: "2099-01-10" }] }
    : url === "/api/notifications/" ? { unread_count: 0 }
    : url.startsWith("/api/applications/") ? { items: [] } : { items: [] };
  let reviewed = 0;
  const tree = await rendered(h, C, C.CouncilHome, { api, lang: "en", user: secretary, onCase() {}, onSession() {}, onReview: () => reviewed++, onNotifications() {}, onCases() {} });
  const grids = byName(tree, "WidgetGrid");
  assert.equal(grids.length, 2);
  const metrics = grids[0].props.items;
  same(metrics.map((item) => item.id), ["mine", "unread", "review", "consideration"]);
  const card = grids[0].props.renderItem(metrics[0]);
  assert.equal(card.type.displayName, "MetricCard");
  assert.equal(card.props.value, "2");
  assert.equal(grids[0].props.renderItem(metrics[2]).props.value, "10");
  metrics[2].menu.props.onSelect();
  assert.equal(reviewed, 1);
  // a member: no review metrics; a count the server did not send stays empty ("–"), never 0
  const [h2, C2] = boot();
  const memberApi = async (url) => url === "/api/dashboard/" ? { my_cases: null, review_queue: null, upcoming_sessions: [] } : url === "/api/notifications/" ? { unread_count: 1 } : { items: [] };
  const member = await rendered(h2, C2, C2.CouncilHome, { api: memberApi, lang: "en", user: { id: "m", role: "member" }, onCase() {}, onSession() {}, onReview() {}, onNotifications() {}, onCases() {} });
  const memberGrid = byName(member, "WidgetGrid")[0];
  same(memberGrid.props.items.map((item) => item.id), ["mine", "unread"]);
  assert.equal(memberGrid.props.renderItem(memberGrid.props.items[0]).props.value, undefined);
});

test("search is a SearchWorkspace in a form: nothing is sent before Search, results open their case from the row", async () => {
  const [h, C] = boot();
  const calls = [];
  const opened = [];
  const api = async (url, options) => { calls.push(url); return url === "/api/search/" ? { items: [{ file_id: "f1", name: "Petition.pdf", case_id: "c1" }] } : { items: [{ id: "c1", number: "20261020-01" }] }; };
  let tree = h.render(C.SearchWorkspace, { api, lang: "en", user: secretary, onCase: (id) => opened.push(id) });
  let ws = byName(tree, "SearchWorkspace")[0];
  assert.ok(ws, "Plenix SearchWorkspace");
  assert.equal(byName(tree, "Form")[0].children.includes(ws) || find(byName(tree, "Form")[0], (n) => n === ws).length > 0, true);
  assert.equal(ws.props.count, 0);
  assert.equal(ws.props.strings.noMatchFilters, "Enter a search phrase, then choose Search.");
  ws.props.onQueryChange("Petition");
  same(calls, []);
  tree = h.render(C.SearchWorkspace, { api, lang: "en", user: secretary, onCase: (id) => opened.push(id) });
  await byName(tree, "Form")[0].props.onSubmit({ preventDefault() {} });
  tree = h.render(C.SearchWorkspace, { api, lang: "en", user: secretary, onCase: (id) => opened.push(id) });
  ws = byName(tree, "SearchWorkspace")[0];
  assert.equal(ws.props.count, 1);
  const results = one(tree, Table);
  assert.equal(results.props.rowMenu[0].label, "Open");
  results.props.onSelect("f1");
  results.props.rowMenu[0].onSelect(results.props.rows[0]);
  same(opened, ["c1", "c1"]);
});

test("statistics are MetricCards in a WidgetGrid; the per-manager counts are a ranked list card", async () => {
  const [h, C] = boot();
  const api = async (url) => url === "/api/cases/" ? { items: cases.concat([{ id: "c3", status: "open", assigned_member: "Fr. David" }]) } : { items: [{ state: "planned" }] };
  const tree = await rendered(h, C, C.StatisticsWorkspace, { api, lang: "en" });
  const grid = byName(tree, "WidgetGrid")[0];
  const cards = grid.props.items.map((item) => grid.props.renderItem(item));
  assert.ok(cards.every((card) => card.type.displayName === "MetricCard"));
  assert.equal(cards[0].props.value, "2");
  const list = cards.find((card) => card.props.type === "list");
  same(list.props.items.map((item) => [item.label, item.value]), [["Fr. David", "2"]]);
});

test("new applications and the completeness review use the listing and split workspace templates", async () => {
  const [h, C] = boot();
  const apps = { items: [{ id: "a1", case_id: "c9", case_number: "DEMO-NEW-01", kind: "petition", status: "submitted", applicant_name: "Noah Anderson" }] };
  const opened = [];
  let tree = await rendered(h, C, C.NewApplicationsTable, { api: async () => apps, lang: "en", user: secretary, onOpen: (...args) => opened.push(args) });
  const list = one(tree, Listing);
  assert.ok(list);
  list.props.rowMenu[0].onSelect(list.props.rows[0]);
  list.props.onOpen(list.props.rows[0]);
  same(opened, [["c9", "a1"], ["c9", "a1"]]);
  assert.ok(!list.props.columns.some((column) => column.field === "open_action"));
  let back = 0;
  const [h2, C2] = boot();
  tree = await rendered(h2, C2, C2.ReviewWorkspace, { api: async () => apps, lang: "en", user: secretary, onCase() {}, onBack: () => back++ });
  const workspace = one(tree, Workspace);
  assert.ok(workspace, "the review queue renders (no undefined selection)");
  assert.equal(workspace.props.rows[0].title, "DEMO-NEW-01");
  workspace.props.commandBar.actions[0].onSelect();
  assert.equal(back, 1);
});

test("a refused search shows its reason even though the workspace has no results to draw", async () => {
  const [h, C] = boot();
  const api = async (url) => { if (url === "/api/search/") { const error = new Error("off"); error.status = 422; error.body = { error: "Search engine is not configured." }; throw error; } return { items: [] }; };
  const props = { api, lang: "en", user: secretary, onCase() {} };
  let tree = h.render(C.SearchWorkspace, props);
  byName(tree, "SearchWorkspace")[0].props.onQueryChange("petition");
  tree = h.render(C.SearchWorkspace, props);
  await byName(tree, "Form")[0].props.onSubmit({ preventDefault() {} });
  tree = h.render(C.SearchWorkspace, props);
  const form = byName(tree, "Form")[0];
  const ws = byName(tree, "SearchWorkspace")[0];
  const notice = byName(form, "Notice")[0];
  assert.ok(notice, "a notice in the form");
  assert.equal(find(ws, (n) => n === notice).length, 0, "not inside the workspace results");
});
