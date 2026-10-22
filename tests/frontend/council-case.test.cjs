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
  assert.deepEqual(plain(C.DECISION_TYPES.map((t) => t.code).sort()), [...serverTypes].sort());
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
  assert.equal(C.decisionProblem({ type: "deferred", grounds: "Reason", entitlements: {} }, parties), null);
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
  for (const [, key] of source.matchAll(/\bt\("([A-Za-z0-9_]+)"/g)) assert.ok(known.has(key), key);
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
