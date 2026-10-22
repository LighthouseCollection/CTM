const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const context = { window: {} };
vm.runInNewContext(fs.readFileSync("static/ctm/council.js", "utf8"), context);
const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
vm.runInNewContext(source, context);
const C = context.window.CTMCouncil;
const plain = (value) => JSON.parse(JSON.stringify(value));

const parties = [
  { id: "p1", name: "Applicant One" },
  { id: "p2", name: "Spouse Two" },
];

test("case module extends the council namespace", () => {
  for (const name of ["ReportsWorkspace", "RequestsPanel", "DecisionWorkspace", "ReviewWorkspace"])
    assert.equal(typeof C[name], "function");
});

test("decision catalog matches the server types and exact prototype labels", () => {
  const prototype = JSON.parse(
    fs.readFileSync("docs/architecture/build-spec/prototype-decision-types.json", "utf8"),
  ).types;
  const server = fs.readFileSync("tribunal/services/decisions.py", "utf8");
  const serverTypes = [...server.match(/DECISION_TYPES = \{([^}]*)\}/)[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  // Every selectable type is a server type; deferral is a hearing outcome (F27).
  assert.deepEqual(plain(C.DECISION_TYPES.map((t) => t.code).sort()), serverTypes.filter((t) => t !== "deferred").sort());
  assert.equal(C.typeLabel("deferred"), "Decision Deferred — Further Investigation Required");
  for (const row of C.DECISION_TYPES) {
    const match = prototype.find((p) => p.prototype_code === row.code);
    assert.ok(match, row.code);
    assert.equal(row.label, match.prototype_label);
  }
  assert.ok(!C.DECISION_TYPES.some((t) => ["withdrawn", "reconciled"].includes(t.code)));
});

test("type and grounds are required before anything can be voted on", () => {
  assert.equal(C.decisionProblem({ type: "", grounds: "x", entitlements: {} }, parties), "chooseType");
  assert.equal(C.decisionProblem({ type: "imprisonment", grounds: "x", entitlements: {} }, parties), "chooseType");
  assert.equal(C.decisionProblem({ type: "denied", grounds: "  ", entitlements: {} }, parties), "groundsRequired");
  assert.equal(C.decisionProblem({ type: "denied", grounds: "Reason", entitlements: {} }, parties), null);
  assert.equal(C.decisionProblem({ type: "deferred", grounds: "Reason", entitlements: {} }, parties), "chooseType");
});

test("granting decisions need an explicit entitlement for every party", () => {
  const form = { type: "diss-applicant", grounds: "Reason", entitlements: { p1: "certificate" } };
  assert.equal(C.decisionProblem(form, parties), "entitlementRequired");
  form.entitlements.p2 = "notice_only";
  assert.equal(C.decisionProblem(form, parties), null);
  assert.equal(
    C.decisionProblem({ type: "null-granted", grounds: "R", entitlements: { p1: "certificate", p2: "notice_only" } }, parties),
    "nullityBoth",
  );
  assert.equal(
    C.decisionProblem({ type: "null-granted", grounds: "R", entitlements: { p1: "certificate", p2: "certificate" } }, parties),
    null,
  );
});

test("conditional decisions require stated conditions", () => {
  const form = { type: "diss-conditional", grounds: "R", entitlements: { p1: "certificate", p2: "notice_only" }, conditions: "" };
  assert.equal(C.decisionProblem(form, parties), "conditionsRequired");
  form.conditions = "Applicant One after completing counselling.";
  assert.equal(C.decisionProblem(form, parties), null);
});

test("payload sends entitlements only for granting types and trims text", () => {
  assert.deepEqual(
    plain(C.decisionPayload({ type: "denied", grounds: " Reason ", entitlements: { p1: "certificate" }, conditions: "x" }, parties)),
    { type: "denied", grounds: "Reason", entitlements: {}, conditions: "" },
  );
  assert.deepEqual(
    plain(C.decisionPayload({ type: "diss-both", grounds: "R", entitlements: { p1: "certificate", p2: "certificate", ghost: "x" }, conditions: "" }, parties)),
    { type: "diss-both", grounds: "R", entitlements: { p1: "certificate", p2: "certificate" }, conditions: "" },
  );
});

test("tally lists the whole roster and counts only the latest vote per member", () => {
  const roster = [
    { id: "m1", name: "A", role: "member" },
    { id: "m2", name: "B", role: "president" },
    { id: "m3", name: "C", role: "secretary" },
  ];
  const result = C.tally(
    [
      { member_id: "m1", choice: "deny" },
      { member_id: "m1", choice: "approve" },
      { member_id: "m2", choice: "abstain" },
    ],
    roster,
  );
  assert.equal(result.rows.length, 3);
  assert.deepEqual(plain(result.counts), { approve: 1, deny: 0, abstain: 1, none: 1 });
  assert.equal(result.rows[2].vote, null);
  assert.deepEqual(plain(C.councilRoster([{ id: "x", role: "applicant" }, ...roster]).map((r) => r.id)), ["m1", "m2", "m3"]);
});

const bank = [
  { code: "OPEN-01", version: 1, category: "Foundational questions", wording_en: "Name?", wording_ar: "", foundational: true },
  { code: "DM-02", version: 1, category: "Decision to marry", wording_en: "Old", wording_ar: "", foundational: false },
  { code: "DM-02", version: 2, category: "Decision to marry", wording_en: "New wording", wording_ar: "", foundational: false },
  { code: "DM-01", version: 1, category: "Decision to marry", wording_en: "Why?", wording_ar: "لماذا؟", foundational: false },
];

test("question groups use the latest version of each code within its category", () => {
  const groups = C.questionGroups(bank);
  assert.deepEqual(plain(groups.map((g) => g.category)), ["Foundational questions", "Decision to marry"]);
  assert.deepEqual(plain(groups[1].questions.map((q) => `${q.code}@${q.version}`)), ["DM-01@1", "DM-02@2"]);
  assert.equal(groups[1].questions[1].wording_en, "New wording");
  assert.deepEqual([...C.foundationalCodes(bank)], ["OPEN-01"]);
});

test("Arabic or bilingual requests need approved Arabic for every question sent", () => {
  assert.deepEqual([...C.missingArabic(["DM-01"], bank, "en")], []);
  assert.deepEqual([...C.missingArabic(["DM-01"], bank, "ar")], ["OPEN-01"]);
  assert.deepEqual([...C.missingArabic(["DM-02"], bank, "both")].sort(), ["DM-02", "OPEN-01"]);
});

test("request needs subject, title and language; payload is an intake for the open proceeding", () => {
  const form = { party: "", title: "", language: "en", selected: ["DM-01"], instructions: " Please answer. ", parent: "" };
  assert.equal(C.requestProblem(form, bank), "chooseSubject");
  form.party = "p1";
  assert.equal(C.requestProblem(form, bank), "titleRequired");
  form.title = "First intake";
  assert.equal(C.requestProblem(form, bank), null);
  assert.equal(C.requestProblem({ ...form, language: "ar" }, bank), "arabicMissing");
  assert.deepEqual(plain(C.requestPayload(form, "proc-1")), {
    proceeding_id: "proc-1",
    party_id: "p1",
    kind: "intake",
    title: "First intake",
    language: "en",
    instructions: "Please answer.",
    questions: ["DM-01"],
    parent_id: null,
  });
});

test("open proceeding is chosen from the case projection", () => {
  assert.equal(C.openProceeding({ proceedings: [{ id: "a", status: "closed" }, { id: "b", status: "open" }] }).id, "b");
  assert.equal(C.openProceeding({ proceedings: [{ id: "a", status: "closed" }] }), null);
});

test("English and Arabic case words cover the same keys and every used key", () => {
  const en = Object.keys(C.caseWords.en).sort();
  assert.deepEqual(Object.keys(C.caseWords.ar).sort(), en);
  for (const key of en) assert.ok(C.caseWords.ar[key].trim(), key);
  const known = new Set([...en, ...Object.keys(C.words.en)]);
  for (const [, key] of source.matchAll(/\bt\("([A-Za-z0-9_]+)"[),]/g)) assert.ok(known.has(key), key);
  for (const status of ["none", "signed", "out_of_scope"]) assert.ok(known.has("release_" + status), status);
});

test("case module follows Plenix rules", () => {
  assert.doesNotMatch(source, /style\s*:/);
  assert.doesNotMatch(source, /#[0-9a-fA-F]{3,8}\b/);
  assert.doesNotMatch(source, /!important/);
});

test("topic groups are an alternate view of the same selection", () => {
  const qs = [
    { code: "A-1", version: 1, category: "Cat A", foundational: false, topic_groups: [{ id: "TG02", title: "Common" }, { id: "TG03", title: "Annulment" }] },
    { code: "B-1", version: 1, category: "Cat B", foundational: false, topic_groups: [{ id: "TG02", title: "Common" }] },
  ];
  assert.equal(C.hasTaxonomy(qs), true);
  assert.equal(C.hasTaxonomy(bank), false);
  const view = C.topicGroupView(qs);
  assert.deepEqual(plain(view.map((g) => [g.id, g.questions.map((q) => q.code)])), [["TG02", ["A-1", "B-1"]], ["TG03", ["A-1"]]]);
  assert.equal(C.groupTitle({ title: "Common", title_ar: null }, "ar"), "Common");
  assert.equal(C.groupTitle({ category: "Cat A", category_ar: "فئة" }, "ar"), "فئة");
});

test("interview report keeps only answered questions and separates observations", () => {
  const questions = [{ code: "A" }, { code: "B" }];
  assert.equal(C.interviewProblem({ A: " " }, questions), "answerRequired");
  assert.equal(C.interviewProblem({ B: "said" }, questions), null);
  assert.deepEqual(plain(C.interviewPayload({ A: "  yes ", B: "", X: "ignored" }, " note ", questions)), { answers: { A: "yes" }, observations: "note" });
  assert.equal(C.requestPayload({ kind: "interview", party: "p", title: "t", language: "en", selected: [] }, "x").kind, "interview");
  assert.equal(C.requestPayload({ party: "p", title: "t", language: "en", selected: [] }, "x").kind, "intake");
});

test("audit labels are readable for known codes and verbatim otherwise", () => {
  assert.equal(C.auditLabel("decree_issued", "en"), "Decree issued");
  assert.equal(C.auditLabel("decree_issued", "ar"), "صدرت الشهادة");
  assert.equal(C.auditLabel("some_future_code", "en"), "some_future_code");
  const rows = C.auditRows(
    [
      { id: "1", action: "vote_recorded", actor: "m1", timestamp: "t" },
      { id: "2", action: "answers_saved", actor: "applicant-x", timestamp: "t" },
      { id: "3", action: "session_closed", actor: null, timestamp: "t" },
    ],
    [{ id: "m1", name: "Fr. A" }],
    "en",
  );
  assert.deepEqual(plain(rows.map((r) => r.actor)), ["Fr. A", null, "system"]);
  assert.deepEqual(plain(C.filterAudit(rows, "vote").map((r) => r.id)), ["1"]);
  assert.deepEqual(plain(C.filterAudit(rows, "fr. a").map((r) => r.id)), ["1"]);
  assert.equal(C.filterAudit(rows, "").length, 3);
});

test("a call record needs who, when (not future) and outcome", () => {
  const ok = { party: "p", occurred: "2026-10-20T10:00", outcome: "Spoke with applicant" };
  assert.equal(C.callProblem(ok), null);
  assert.equal(C.callProblem({ ...ok, party: "" }), "chooseCallParty");
  assert.equal(C.callProblem({ ...ok, occurred: "" }), "callTimeRequired");
  assert.equal(C.callProblem({ ...ok, occurred: "2999-01-01T10:00" }), "callTimeFuture");
  assert.equal(C.callProblem({ ...ok, outcome: " " }), "callOutcomeRequired");
});

test("English and Arabic audit labels cover the same codes", () => {
  const src = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const block = src.slice(src.indexOf("const AUDIT_LABELS"), src.indexOf("function auditLabel"));
  const en = block.slice(block.indexOf("en: {"), block.indexOf("ar: {"));
  const ar = block.slice(block.indexOf("ar: {"));
  const keys = (text) => [...text.matchAll(/^\s+([a-z_]+): "/gm)].map((m) => m[1]).sort();
  assert.deepEqual(keys(ar), keys(en));
});

test("assessments stay separate and hidden contents stay hidden", () => {
  const reqs = [{ id: 1, kind: "intake" }, { id: 2, kind: "medical" }, { id: 3, kind: "psychological" }, { id: 4, kind: "interview" }];
  assert.deepEqual(plain(C.assessmentRequests(reqs).map((r) => r.id)), [2, 3]);
  const reports = [{ id: "a", kind: "intake" }, { id: "b", restricted: true }, { id: "c", kind: "medical" }];
  assert.deepEqual(plain(C.assessmentReports(reports).map((r) => r.id)), ["b", "c"]);
  assert.equal(C.assessmentProblem({ party: "p", kind: "medical", title: "Evaluation" }), null);
  assert.equal(C.assessmentProblem({ party: "", kind: "medical", title: "x" }), "chooseSubject");
  assert.equal(C.assessmentProblem({ party: "p", kind: "intake", title: "x" }), "chooseAssessmentKind");
  assert.equal(C.assessmentProblem({ party: "p", kind: "psychological", title: " " }), "titleRequired");
});

test("ordinary report reader and requests exclude assessments", () => {
  const src = fs.readFileSync("static/ctm/app.js", "utf8");
  assert.match(src, /!\["medical", "psychological"\]\.includes\(row\.kind\) && !row\.restricted/);
});

test("ordinary Requests tab never lists assessment requests", () => {
  const src = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(src, /requests: requests\.items\.filter\(\(row\) => !\["medical", "psychological"\]\.includes\(row\.kind\)\)/);
});

test("adding the other party needs first name, last name and a valid email", () => {
  const ok = { first: "Mary", last: "Smith", email: "mary@example.test" };
  assert.equal(C.partyProblem(ok), null);
  assert.equal(C.partyProblem({ ...ok, first: " " }), "firstRequired");
  assert.equal(C.partyProblem({ ...ok, last: "" }), "lastRequired");
  assert.equal(C.partyProblem({ ...ok, email: "not-an-email" }), "emailInvalid");
});

test("petition page shows this case's petitions and the latest note revisions", () => {
  const apps = [{ id: "a", kind: "petition", case_id: "c" }, { id: "b", kind: "appeal", case_id: "c" }, { id: "d", kind: "petition", case_id: "x" }];
  assert.deepEqual(plain(C.casePetitions(apps, "c").map((a) => a.id)), ["a"]);
  const notes = C.latestNotes([
    { note_id: "n1", version: 1, text: "old" },
    { note_id: "n2", version: 1, text: "second" },
    { note_id: "n1", version: 2, text: "new" },
  ]);
  assert.deepEqual(plain(notes.map((n) => n.text)), ["second", "new"]);
});

test("timeline keeps milestones only, oldest first, with readable labels", () => {
  const rows = C.timelineRows(
    [
      { id: "3", action: "decree_issued", timestamp: "2026-10-23T00:00:00Z" },
      { id: "1", action: "application_submitted", timestamp: "2026-10-20T00:00:00Z" },
      { id: "2", action: "answers_saved", timestamp: "2026-10-21T00:00:00Z" },
      { id: "4", action: "vote_recorded", timestamp: "2026-10-22T00:00:00Z" },
    ],
    "en",
  );
  assert.deepEqual(plain(rows.map((r) => r.label)), ["Application submitted", "Decree issued"]);
});

test("follow-up parents exclude assessments even when readable by council", () => {
  const reports = [{ id: "a", kind: "intake" }, { id: "b", kind: "medical", restricted: false }, { id: "c", restricted: true }, { id: "d", kind: "psychological" }];
  assert.deepEqual(plain(C.ordinaryReports(reports).map((r) => r.id)), ["a"]);
});

test("assigned manager keeps write controls on servers without assigned_member_id", async () => {
  const member = { id: "m", name: "Fr. Member", role: "member", portal: "council" };
  assert.equal(C.writerFor(member, null, { assigned_member_id: "m" }), true);
  assert.equal(C.writerFor(member, null, { assigned_member_id: "x" }), false);
  assert.equal(C.writerFor(member, null, { assigned_member: "Fr. Member" }), true);
  assert.equal(C.writerFor(member, null, {}), false);
  const enriched = await C.withAssignee(async () => ({ items: [{ id: "c1", assigned_member: "Fr. Member" }] }), { id: "c1", parties: [] });
  assert.equal(enriched.assigned_member, "Fr. Member");
  const untouched = { id: "c1", assigned_member_id: "m" };
  assert.equal(await C.withAssignee(async () => { throw new Error("not called"); }, untouched), untouched);
});

test("findings show the latest revision per fact, sorted by code", () => {
  const rows = C.latestFindings([
    { fact_code: "B", version: 1, value: "old" },
    { fact_code: "A", version: 1, value: "a" },
    { fact_code: "B", version: 2, value: "new" },
  ]);
  assert.deepEqual(plain(rows.map((r) => `${r.fact_code}:${r.value}`)), ["A:a", "B:new"]);
});

test("templates pre-fill only published, non-foundational codes and skip retired ones", () => {
  const templates = [
    { id: "t1", retired: false, questions: [{ code: "OPEN-01" }, { code: "DM-01" }, { code: "GONE-9" }, { code: "DM-01" }] },
    { id: "t2", retired: true, questions: [{ code: "DM-02" }] },
    { id: "t3", retired: false, questions: [] },
    { id: "t4", retired: false },
  ];
  assert.deepEqual(plain(C.usableTemplates(templates).map((t) => t.id)), ["t1"]);
  assert.deepEqual(plain(C.templateSelection(templates[0], bank)), ["DM-01"]);
});

test("F19: votes of members no longer on the active roster stay counted as former members", () => {
  const roster = [{ id: "m1", name: "A", role: "member" }];
  const result = C.tally([{ member_id: "m1", choice: "approve" }, { member_id: "gone", choice: "deny" }], roster);
  assert.equal(result.rows.length, 2);
  assert.equal(result.rows[1].member.former, true);
  assert.deepEqual(plain(result.counts), { approve: 1, deny: 1, abstain: 0, none: 0 });
});
