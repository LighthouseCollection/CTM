// Issue 199 (D-0048): the case summary keeps each child's first name, last name and date of birth.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, byName, find, textOf } = require("./harness.cjs");

const [h, C] = (() => { const x = harness(); x.React.Component = class { constructor(p) { this.props = p; } }; x.React.Component.prototype.isReactComponent = {}; return [x, load(x, { document: { documentElement: { lang: "en" } } })]; })();
const plain = (v) => JSON.parse(JSON.stringify(v));
const t = C.caseTranslator("en"), ar = C.caseTranslator("ar");

test("a child saved as a name only is split so the council can complete it", () => {
  assert.deepEqual(plain(C.childForm({ name: "Mary Anne Hayes" })), { first_name: "Mary Anne", last_name: "Hayes", date_of_birth: "" });
  assert.deepEqual(plain(C.childForm("Peter")), { first_name: "Peter", last_name: "", date_of_birth: "" });
  assert.deepEqual(plain(C.childForm({ name: "x", first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" })), { first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" });
});

test("each child needs first name, last name and a date of birth that is not in the future", () => {
  const ok = { first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" };
  assert.equal(C.childProblem(ok, "2026-11-07"), null);
  assert.equal(C.childProblem({ ...ok, first_name: " " }, "2026-11-07").key, "childFirstRequired");
  assert.equal(C.childProblem({ ...ok, last_name: "" }, "2026-11-07").key, "childLastRequired");
  assert.equal(C.childProblem({ ...ok, date_of_birth: "" }, "2026-11-07").key, "childBirthRequired");
  assert.equal(C.childProblem({ ...ok, date_of_birth: "2026-11-08" }, "2026-11-07").key, "childBirthFuture");
  // Well before the marriage only warns.
  assert.equal(C.childWarning({ date_of_birth: "2009-01-01" }, "2010-06-01"), "childBirthBeforeMarriage");
  assert.equal(C.childWarning({ date_of_birth: "2009-07-01" }, "2010-06-01"), null);
  for (const key of ["childFirstRequired", "childLastRequired", "childBirthRequired", "childBirthFuture", "childBirthBeforeMarriage", "addChild", "noChildrenShort", "dateOfBirth", "edit", "save", "remove", "childrenIncomplete"])
    assert.notEqual(ar(key), t(key), key);
});

test("age counts whole years on civil dates", () => {
  assert.equal(C.ageOn("2015-03-04", "2026-03-03"), 10);
  assert.equal(C.ageOn("2015-03-04", "2026-03-04"), 11);
});

test("the summary form sends all three fields per child and no hard-coded English is left", () => {
  const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(source, /children: summaryForm\.children\.map\(\(child\) => \(\{ first_name: child\.first_name, last_name: child\.last_name, date_of_birth: child\.date_of_birth \}\)\)/);
  assert.doesNotMatch(source, /One child per line/);
  assert.doesNotMatch(source, /onClick: startSummaryEdit \}, "Edit"\)/);
  assert.doesNotMatch(source, /disabled: summaryPending \}, "Save"\)/);
  assert.doesNotMatch(source, /P\.Textarea, \{ rows: 4, value: summaryForm\.children/);
});

test("the child editor: No children with Add child; rows with Edit and Remove; Remove drops the row", () => {
  let list = [];
  const draw = (children) => h.render(C.ChildrenEditor, { lang: "en", children, onChange: (next) => { list = next; }, disabled: false, marriageDate: "2010-06-01" });
  let tree = draw([]);
  assert.equal(byName(tree, "EmptyState")[0].props.title, "No children");
  assert.match(textOf(byName(tree, "EmptyState")[0].props.action), /Add child/);
  tree = draw([{ first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" }, { first_name: "John", last_name: "Hayes", date_of_birth: "2017-05-06" }]);
  const buttons = byName(tree, "Button").map((b) => textOf({ children: b.children }).trim());
  assert.deepEqual(buttons.filter((b) => b === "Edit").length, 2);
  assert.deepEqual(buttons.filter((b) => b === "Remove").length, 2);
  byName(tree, "Button").find((b) => textOf({ children: b.children }).trim() === "Remove").props.onClick();
  assert.deepEqual(plain(list), [{ first_name: "John", last_name: "Hayes", date_of_birth: "2017-05-06" }]);
  assert.match(textOf(tree), /Mary Hayes/);
});

// D-0050 (#217 G2, G5): the Separation cards and the editable case cards have EN and AR words, no English literals.
test("separation cards and editable case cards are EN/AR", () => {
  const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const start = source.indexOf("  function CaseSeparation(");
  const sep = source.slice(start, source.indexOf("\n  }\n", start));
  assert.ok(sep.includes("t(\"separationDetails\")"), "the real CaseSeparation body");
  assert.doesNotMatch(sep.replace(/\/\/.*$/gm, ""), /"[A-Z][a-z]+[ ?]/, "no English labels or titles");
  const panel = source.slice(source.indexOf("  function CouncilEditablePanel("), source.indexOf("  function CouncilEditablePanel(") + 3000);
  assert.doesNotMatch(panel, /\}, "Edit"\)|\}, "Save"\)/);
  for (const key of ["separationDetails", "civilDivorce", "restrainingOrder", "reconciliation", "maritalStatus", "initiatedBy", "courtName", "courtLocation", "civilCaseNumber", "civilDivorceStatus", "orderFiled", "orderNameListed", "orderCaseNumber", "orderStatus", "reconciliationAttempted", "permitPreviouslyApplied", "permitWhen", "permitWhere", "decisionOutcome"])
    assert.notEqual(ar(key), t(key), key);
});

// D-0050 (#217 G11): the applicant's application status and case reference are description-list items.
test("applicant application status is a Badge in a PropertyList; applicant panels have icons", () => {
  const app = fs.readFileSync("static/ctm/applicant.js", "utf8");
  assert.doesNotMatch(app, /`\$\{t\("status"\)\}: /);
  assert.doesNotMatch(app, /`\$\{t\("caseReference"\)\}: `/);
  assert.match(app, /h\(P\.PropertyList\.Item, \{ label: t\("status"\) \}, h\(P\.Badge,/);
  assert.match(app, /h\(P\.PropertyList\.Item, \{ label: t\("caseReference"\), data: true \}, record\.case_number\)/);
  assert.match(fs.readFileSync("static/ctm/applicant-appeals.js", "utf8"), /h\(P\.Panel,\{icon:"doc-text",title:t\("title"\)\}/);
  assert.match(fs.readFileSync("static/ctm/applicant-history.js", "utf8"), /h\(P\.Panel,\{icon:'progress',title:t\('title'\)\}/);
});

// D-0050 (#217 G6, G8, G9, G10, G13): status as a Badge, details as description-list items, every card with an icon.
test("council read views use Badge for status and PropertyList for label/value pairs", () => {
  const read = (f) => fs.readFileSync(f, "utf8");
  const council = read("static/ctm/council.js"), cc = read("static/ctm/council-case.js"), media = read("static/ctm/council-media.js"), decree = read("static/ctm/council-decree.js"), hist = read("static/ctm/historical-entry.js");
  assert.match(council, /h\(P\.Panel, \{ icon: "folder", title: t\("assignedCases"\) \}/);
  assert.match(council, /h\(P\.Panel, \{ icon: "event_available", title: t\("casesPresented"\) \}/);
  assert.doesNotMatch(cc, /`\$\{t\("recordedBy"\)\}: /);
  assert.doesNotMatch(cc, /`\$\{t\("president"\)\}: /);
  assert.match(media, /label: t\("noticeState"\) \}, h\(P\.Badge,/);
  assert.doesNotMatch(media, /h\(P\.Text, \{ variant: "secondary" \}, label\(code\)\)/);
  assert.match(decree, /label: t\("fee"\) \}, h\(P\.Badge,/);
  assert.match(hist, /key === "status" \? h\(P\.Badge,/);
});

// D-0050 groups (groups.md): read and edit use the same groups in the same order.
test("case summary, marriage and request detail are grouped as decided", () => {
  const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const order = (text, keys) => { let at = -1; for (const key of keys) { const i = text.indexOf(key, at + 1); assert.ok(i > at, key); at = i; } };
  const s0 = source.indexOf("const summaryGroups = [");
  order(source.slice(s0, source.indexOf("];", s0)), ['t("groupCase")', '"case_number"', '"filing_date"', '"status"', '"assigned_member"', '"last_hearing_date"', 't("groupSpouses")', '"applicant"', '"respondent"', 't("marriageTitle")', '"marriage_duration"', '"children"', '"reason"']);
  order(source.slice(source.indexOf("h(P.Form, { onSubmit: saveSummary"), source.indexOf("summaryFailure ? h(P.Notice")), ['t("groupCase")', 't("assignedCouncilMember")', 't("marriageTitle")', "ChildrenEditor", 't("reasonForDivorce")']);
  const m0 = source.indexOf("const marriageGroups = (withDuration) => [");
  order(source.slice(m0, source.indexOf("const fields = marriageGroups(false)")), ['t("churchMarriage")', '"church_marriage_date"', '"marriage_duration"', '"officiating_priest"', '"church_name"', '"church_location"', '"diocese"', 't("groupOutsideCoptic")', '"outside_coptic_church"', '"outside_denomination"', '"outside_marriage_date"']);
  assert.match(source, /groupedEdit\(P, h, marriageGroups\(false\)/);
  const r0 = source.indexOf("// D-0050 groups (groups.md): Request · Record.");
  order(source.slice(r0, source.indexOf("externalNoQuestions", r0)), ['t("groupRequest")', 't("title")', 't("method")', 't("language")', 't("groupRecord")', 't("preparedBy")', 't("createdAt")', 't("parent")']);
  for (const key of ["groupCase", "groupSpouses", "groupOutsideCoptic", "groupRequest", "groupRecord"]) assert.notEqual(ar(key), t(key), key);
});

// D-0055 (owner): a heading that introduces a table or block is a card header, never a bare section heading.
test("D-0055: other sessions' agenda parts are cards; card-internal headings are group headings or the card title", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const part = council.slice(council.indexOf("    const part = (n) =>"), council.indexOf("    const part = (n) =>") + 300);
  assert.match(part, /P\.Panel,\s*\{ key: n, icon: n === 1 \? "folder" : "event_available", title: t\(`part\$\{n\}`\) \}/);
  assert.doesNotMatch(council, /h\(P\.Text, \{ as: "h2", variant: "heading" \}, t\("agenda"\)\)/);
  assert.match(council, /h\(P\.SectionHeading, \{ level: 3 \}, confirmedText\(data, t\)\)/);
  const decree = fs.readFileSync("static/ctm/council-decree.js", "utf8");
  assert.match(decree, /\{ icon: "doc-text", title: t\("decreeProtocolTitle"\) \}/);
  assert.doesNotMatch(decree, /h\(P\.Text, \{ as: "h2", variant: "heading" \}, t\("decreeProtocolTitle"\)\)/);
});

// D-0058 (issue 242): the case timeline model: eight case areas, grouped by year, latest first; the server's area and
// date win; upcoming events are marked.
test("timeline model: area from the server or the audit action, years latest first, upcoming marked", () => {
  const events = [
    { id: "a", action: "application_submitted", timestamp: "2025-03-01T10:00:00Z", label: "Filed" },
    { id: "b", action: "case_assigned", timestamp: "2026-02-01T10:00:00Z", label: "Assigned" },
    { id: "c", category: "marriage", timestamp: "2010-06-05", label: "Church marriage" },
    { id: "d", action: "report_submitted", area: "comms", date: "2026-12-01", timestamp: "2026-01-01T00:00:00Z", label: "Server area" },
  ];
  const model = C.timelineModel(events, "en", t, "2026-11-08");
  assert.deepEqual(plain(model.groups.map((g) => [g.year, g.items.map((i) => [i.id, i.area, i.upcoming])])), [
    ["2026", [["d", "comms", true], ["b", "assign", false]]],
    ["2025", [["a", "application", false]]],
    ["2010", [["c", "marriage", false]]],
  ]);
  assert.deepEqual(plain(model.areas), ["marriage", "application", "assign", "comms"]);
  assert.equal(model.groups[0].items[1].areaLabel, "Assignment");
  for (const area of ["marriage", "application", "filing", "assign", "hearing", "decision", "decree", "comms"])
    assert.notEqual(ar(`timelineArea_${area}`), t(`timelineArea_${area}`), area);
});

// The timeline API (backend PR 258): CTM words for known kinds with their params, the server title otherwise, English
// descriptions only in English, and events without a date first as Pending.
test("timeline API items: own EN/AR title per kind, pending first", () => {
  const items = [
    { id: "x", kind: "manager_assigned", area: "assign", date: "2026-03-01", params: { member: { name: "Fr. Example" } }, title: "Assigned", description: "By the clerk" },
    { id: "y", kind: "decision_pending_approval", area: "decision", date: null, pending: true, params: {}, title: "Awaiting approval" },
    { id: "z", kind: "something_new", area: "comms", date: "2026-04-01", params: {}, title: "Server words" },
    { id: "w", kind: "child_born", area: "marriage", date: "2015-01-02", params: {}, title: "Child born" },
  ];
  const events = C.timelineApiEvents(items, "en", t);
  assert.deepEqual(plain(events.map((e) => [e.id, e.label, e.description ?? null])), [
    ["x", "Assigned to Fr. Example", "By the clerk"], ["y", "Awaiting the president's approval", null], ["z", "Server words", null], ["w", "Child born", null],
  ]);
  assert.equal(C.timelineApiEvents(items, "ar", ar)[0].description, null);
  const model = C.timelineModel(events, "en", t, "2026-11-08");
  assert.deepEqual(plain(model.groups.map((g) => [g.year, g.items.map((i) => i.id)])), [["Pending", ["y"]], ["2026", ["z", "x"]], ["2015", ["w"]]]);
});
