// #97 slice 3: every council case tab is a Plenix RecordPage under one case header (EntityHeader, record-page.md),
// hearings use an EntityHeader section, closed cases are a ReadOnly region, page actions use ActionBar.
// Synthetic data only.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, find, byName, textOf, settle, nameOf } = require("./harness.cjs");

const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
const secretary = { id: "u-sec", role: "secretary", name: "Synthetic Secretary" };
const member = { id: "u-mem", role: "member", name: "Synthetic Member" };
const manager = { id: "u-mgr", role: "member", name: "Synthetic Manager" };

function caseRecord(extra = {}) {
  return {
    id: "c1", number: "20261020-04", status: "open", assigned_member_id: "u-mgr", assigned_member: "Synthetic Manager",
    assignment_history: [{ id: "a1", member_id: "u-mgr", member: "Synthetic Manager" }],
    parties: [
      { id: "p1", slot: "A", name: "Applicant Synthetic", gender: "F", can_receive: true },
      { id: "p2", slot: "B", name: "Respondent Synthetic", gender: "M", can_receive: true },
    ],
    proceedings: [{ id: "pr1", status: "open", sequence: 1 }],
    marriage: {}, separation: {}, summary: {},
    ...extra,
  };
}

// A scripted read-only server: GET paths answer from `routes`; a missing route is a 404, a function may throw.
function server(routes) {
  const seen = [];
  const api = async (url, options) => {
    if (options && options.method && options.method !== "GET") throw new Error(`unexpected write ${url}`);
    seen.push(url);
    const path = url.split("?")[0];
    const route = routes[path];
    if (route === undefined) throw Object.assign(new Error(`HTTP 404 ${path}`), { status: 404 });
    return typeof route === "function" ? route() : route;
  };
  return { api, seen };
}

async function mount(name, props) {
  const h = harness();
  // The error boundary is a class; the harness renders its children in place.
  h.React.Component = class Component { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  const C = load(h, { document: { documentElement: { lang: "en" } }, CTMShell: { Workspace: function Workspace() { return null; }, Table: function Table() { return null; } }, CTMUI: { filterAudit: (rows) => rows, AuditFilters: function AuditFilters() { return null; } } });
  let tree = h.render(C[name], props);
  for (let i = 0; i < 4; i++) { await settle(); tree = h.render(C[name], props); }
  return { tree, rerender: () => h.render(C[name], props) };
}

const caseHeaders = (tree) => byName(tree, "EntityHeader").filter((n) => n.props.kind !== "section");

function assertCaseHeader(tree, record) {
  const pages = byName(tree, "RecordPage");
  assert.equal(pages.length, 1, "one RecordPage");
  const headers = caseHeaders(tree);
  assert.equal(headers.length, 1, "one case header");
  const header = headers[0].props;
  assert.match(String(header.title), new RegExp(record.number));
  assert.match(String(header.subtitle), /Applicant Synthetic/);
  assert.match(String(header.subtitle), /Respondent Synthetic/);
  assert.equal(header.status.label, record.status === "open" ? "Active" : "Closed");
  assert.ok(header.facts.some((fact) => fact.value === "Synthetic Manager"), "the case manager is a fact");
  return header;
}

const routesFor = (record, more = {}) => ({
  [`/api/cases/${record.id}/`]: record,
  [`/api/cases/${record.id}/audit/`]: { items: [] },
  [`/api/cases/${record.id}/requests/`]: { items: [] },
  [`/api/cases/${record.id}/reports/`]: { items: [] },
  [`/api/cases/${record.id}/calls/`]: { items: [] },
  [`/api/proceedings/pr1/notes/`]: { items: [] },
  [`/api/proceedings/pr1/decision/`]: { items: [] },
  "/api/council/members/": { items: [] },
  "/api/cases/": { items: [] },
  "/api/applications/": { items: [] },
  "/api/sessions/": { items: [] },
  "/api/report-questions/": { items: [] },
  ...more,
});

for (const name of ["CaseSummary", "CaseTimeline", "CaseParties", "CaseMarriage", "CaseSeparation", "CaseNotesWorkspace", "CallLog", "AssessmentsWorkspace", "CaseAudit", "PetitionWorkspace", "CaseHearings", "DecisionWorkspace", "ReportsWorkspace"]) {
  test(`${name}: a RecordPage under the case header (number, spouses, status, manager)`, async () => {
    const record = caseRecord();
    const { api } = server(routesFor(record));
    const { tree } = await mount(name, { api, lang: "en", user: secretary, caseId: record.id, reports: [], renderReports: () => null, onSession() {}, onDecision() {} });
    assertCaseHeader(tree, record);
    assert.equal(find(tree, (n) => nameOf(n.type) === "Text" && n.props.as === "h1").length, 0, "the case header is the only h1");
  });
}

test("Arabic case header: status and manager words in Arabic; the case number stays an isolated Latin value", async () => {
  const record = caseRecord({ assigned_member: null, assignment_history: [] , assigned_member_id: null });
  const { api } = server(routesFor(record));
  const { tree } = await mount("CaseMarriage", { api, lang: "ar", user: secretary, caseId: record.id });
  const header = caseHeaders(tree)[0].props;
  assert.equal(header.title, "⁨20261020-04⁩");
  assert.equal(header.status.label, "نشطة");
  assert.ok(header.facts.some((fact) => fact.value === "لم يُعيَّن بعد"));
  assert.match(header.subtitle, / ضد /);
  assert.equal(header.strings.status, "الحالة");
});

test("a closed case is a ReadOnly region with its reason; an open case is not", async () => {
  const closed = caseRecord({ status: "closed", proceedings: [{ id: "pr1", status: "closed", sequence: 1 }] });
  for (const name of ["CaseMarriage", "CaseSeparation", "CaseSummary", "CaseNotesWorkspace", "CallLog"]) {
    const { api } = server(routesFor(closed));
    const { tree } = await mount(name, { api, lang: "en", user: secretary, caseId: closed.id });
    const regions = byName(tree, "ReadOnly");
    assert.equal(regions.length, 1, `${name}: one ReadOnly region`);
    assert.equal(regions[0].props.reason, "This case is closed and read-only.");
    assert.equal(find(tree, (n) => nameOf(n.type) === "Button" && textOf({ children: n.children }).trim() === "Edit").length, 0, `${name}: no Edit`);
  }
  const open = caseRecord();
  const { api } = server(routesFor(open));
  const { tree } = await mount("CaseMarriage", { api, lang: "en", user: secretary, caseId: open.id });
  assert.equal(byName(tree, "ReadOnly").length, 0);
});

test("notes and calls: the count carries its add action (header style 2) only for a writer on an open case", async () => {
  const record = caseRecord();
  const notes = { items: [{ note_id: "n1", version: 1, text: "Synthetic note", timestamp: "2026-10-20T10:00:00Z" }] };
  for (const [name, label, more] of [["CaseNotesWorkspace", "Add an internal note", { "/api/proceedings/pr1/notes/": notes }], ["CallLog", "Record a call", {}]]) {
    const writer = await mount(name, { api: server(routesFor(record, more)).api, lang: "en", user: manager, caseId: record.id });
    const fact = caseHeaders(writer.tree)[0].props.facts.find((f) => f.action);
    assert.ok(fact, `${name}: a fact with an action`);
    assert.equal(fact.action.label, label);
    assert.equal(fact.data, true);
    assert.equal(byName(writer.tree, "Toolbar").length, 0, `${name}: no separate toolbar`);
    const reader = await mount(name, { api: server(routesFor(record, more)).api, lang: "en", user: member, caseId: record.id });
    assert.ok(caseHeaders(reader.tree)[0].props.facts.every((f) => !f.action), `${name}: a member who is not the manager gets no action`);
  }
  const counted = await mount("CaseNotesWorkspace", { api: server(routesFor(record, { "/api/proceedings/pr1/notes/": notes })).api, lang: "en", user: member, caseId: record.id });
  assert.ok(caseHeaders(counted.tree)[0].props.facts.some((f) => f.value === "1"), "the note count");
});

test("Professional Assessments stay on their own tab: no other case header shows an assessment", async () => {
  const record = caseRecord();
  const restricted = { items: [{ id: "r1", kind: "medical", restricted: true, title: "Synthetic Assessment Title" }] };
  const { api } = server(routesFor(record, { [`/api/cases/${record.id}/reports/`]: restricted }));
  const own = await mount("AssessmentsWorkspace", { api, lang: "en", user: manager, caseId: record.id });
  const fact = caseHeaders(own.tree)[0].props.facts.find((f) => f.action);
  assert.equal(fact.action.label, "New assessment request");
  assert.doesNotMatch(JSON.stringify(caseHeaders(own.tree)[0].props), /Synthetic Assessment Title/);
  for (const name of ["CaseSummary", "CaseMarriage", "CaseAudit", "CaseNotesWorkspace"]) {
    const { tree } = await mount(name, { api, lang: "en", user: secretary, caseId: record.id });
    const header = JSON.stringify(caseHeaders(tree)[0].props);
    assert.doesNotMatch(header, /assessment|Synthetic Assessment Title|medical/i, name);
  }
  const reader = await mount("AssessmentsWorkspace", { api, lang: "en", user: member, caseId: record.id });
  assert.ok(caseHeaders(reader.tree)[0].props.facts.every((f) => !f.action));
});

test("a tab that loads the case for its header still opens when the case read is refused", async () => {
  const record = caseRecord();
  const routes = routesFor(record, { [`/api/cases/${record.id}/`]: () => { throw Object.assign(new Error("HTTP 403"), { status: 403 }); } });
  const { tree } = await mount("CaseAudit", { api: server(routes).api, lang: "en", caseId: record.id });
  assert.equal(caseHeaders(tree).length, 0, "no header, no data hints");
  assert.equal(byName(tree, "RecordPage").length, 1);
  assert.ok(find(tree, (n) => nameOf(n.type) === "Text" && n.props.as === "h2" && textOf({ children: n.children }).includes("Case Audit")).length);
});

test("hearings: the current hearing is an EntityHeader section, not hand-built plx-entity-header markup", async () => {
  const hearing = source.slice(source.indexOf("function CaseHearings"), source.indexOf("function HearingAttendance"));
  assert.doesNotMatch(hearing, /plx-entity-header/);
  const record = caseRecord();
  const routes = routesFor(record, {
    "/api/sessions/": { items: [{ id: "s1", date: "2026-11-10", state: "planned" }] },
    "/api/sessions/s1/agenda/": { items: [{ id: "i1", case_id: "c1", part: 2, state: "scheduled", hearing_id: "h1", party_names: ["Applicant Synthetic", "Respondent Synthetic"] }] },
  });
  const opened = [];
  const { tree } = await mount("CaseHearings", { api: server(routes).api, lang: "en", user: secretary, caseId: record.id, onSession: (id) => opened.push(id), onDecision() {} });
  const sections = byName(tree, "EntityHeader").filter((n) => n.props.kind === "section");
  assert.equal(sections.length, 1);
  const section = sections[0].props;
  assert.deepEqual(JSON.parse(JSON.stringify(section.media)), { icon: "calendar", hue: "green" });
  assert.match(section.title, /Applicant Synthetic/);
  assert.equal(section.actionLabels, "text");
  assert.deepEqual([...section.actions].map((a) => a.label), ["Reschedule this hearing", "Council attendance"]);
  section.actions[0].onClick();
  assert.deepEqual([...opened], ["s1"]);
});

test("application review: Decline and Accept are page actions in an ActionBar, the primary last", async () => {
  const record = caseRecord();
  const { tree } = await mount("CaseSummary", { api: server(routesFor(record)).api, lang: "en", user: secretary, caseId: record.id, reviewApplicationId: "app1" });
  const bars = byName(tree, "ActionBar");
  assert.equal(bars.length, 1);
  const labels = byName(bars[0], "Button").map((b) => textOf({ children: b.children }).trim());
  assert.deepEqual(labels, ["Decline", "Accept"]);
  assert.equal(byName(bars[0], "Button").at(-1).props.variant, "primary");
});
