const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("static/ctm/council.js", "utf8");
const context = { window: {} };
vm.runInNewContext(source, context);
const C = context.window.CTMCouncil;
const t = C.translator("en");

const admin = { id: "a", portal: "council", role: "secretary", name: "Sec Retary" };
const member = { id: "m", portal: "council", role: "member", name: "Fr. Member" };
const applicant = { id: "p", portal: "applicant", role: "applicant", name: "App" };

test("module loads without React and exposes views and logic", () => {
  for (const name of ["ReviewQueuePanel", "ReviewWorkspace", "SessionList", "SessionWorkspace"])
    assert.equal(typeof C[name], "function");
});

test("only admin/secretary council accounts manage review and sessions", () => {
  assert.equal(C.canManage(admin), true);
  assert.equal(C.canManage({ ...admin, role: "admin" }), true);
  assert.equal(C.canManage(member), false);
  assert.equal(C.canManage({ ...member, role: "president" }), false);
  assert.equal(C.canManage(applicant), false);
  assert.equal(C.canManage({ portal: "applicant", role: "admin" }), false);
  assert.equal(C.canManage(null), false);
});

test("review queue holds submitted petitions only", () => {
  const rows = [
    { id: 1, kind: "petition", status: "submitted" },
    { id: 2, kind: "petition", status: "accepted" },
    { id: 3, kind: "petition", status: "returned" },
    { id: 4, kind: "appeal", status: "submitted" },
    { id: 5, kind: "petition", status: "draft" },
    null,
  ];
  assert.deepEqual([...C.awaitingReview(rows)].map((r) => r.id), [1]);
  assert.equal(C.awaitingReview(undefined).length, 0);
});

test("return for correction always needs an explanation; accept does not", () => {
  assert.equal(C.reviewProblem("accept", ""), null);
  assert.equal(C.reviewProblem("reject", "Upload the finalized civil decree."), null);
  assert.equal(C.reviewProblem("reject", ""), "returnRequired");
  assert.equal(C.reviewProblem("reject", "   \n "), "returnRequired");
  assert.equal(C.reviewProblem("deny", "x"), "reviewChoose");
  assert.equal(C.reviewProblem(undefined, "x"), "reviewChoose");
});

test("session naming follows the contract", () => {
  assert.equal(C.sessionLabel("2026-10-20", t), "Council Session 2026-10-20");
  assert.equal(C.sessionReference("2026-10-20"), "CS20261020");
  assert.equal(C.sessionReference("20-10-2026"), null);
  assert.equal(
    C.sessionLabel("2026-10-20", C.translator("ar")),
    "جلسة المجلس 2026-10-20",
  );
});

test("one session per date and real calendar dates only", () => {
  const existing = [{ date: "2026-11-01" }];
  assert.equal(C.sessionDateProblem("2026-11-02", existing), null);
  assert.equal(C.sessionDateProblem("2026-11-01", existing), "dateTaken");
  assert.equal(C.sessionDateProblem("", existing), "dateRequired");
  assert.equal(C.sessionDateProblem("2026-02-30", existing), "dateRequired");
  assert.equal(C.sessionDateProblem("2026-13-01", existing), "dateRequired");
});

test("hearing title uses exact contract wording and never invents names", () => {
  assert.equal(
    C.hearingTitle(["John Smith", "Mary Smith"], "2026-10-20", t),
    "Case Hearing of John Smith vs. Mary Smith on Council Session 2026-10-20",
  );
  assert.equal(
    C.hearingTitle(["John Smith"], "2026-10-20", t),
    "Case Hearing of John Smith vs. Unknown party on Council Session 2026-10-20",
  );
});

test("Part 1 offers open unassigned cases not already on the agenda", () => {
  const cases = [
    { id: "c1", status: "open", assigned_member: null, number: "20261020-01" },
    { id: "c2", status: "open", assigned_member: "Fr. Member", number: "20261020-02" },
    { id: "c3", status: "closed", assigned_member: null, number: "20261020-03" },
    { id: "c4", status: "open", assigned_member: null, number: "20261020-04" },
  ];
  const agenda = [{ case_id: "c4", part: 1 }];
  assert.deepEqual([...C.part1Candidates(cases, agenda)].map((c) => c.id), ["c1"]);
});

test("Part 2 offers assigned open cases; members see only their own", () => {
  const cases = [
    { id: "c1", status: "open", assigned_member: "Fr. Member" },
    { id: "c2", status: "open", assigned_member: "Fr. Other" },
    { id: "c3", status: "open", assigned_member: null },
    { id: "c4", status: "closed", assigned_member: "Fr. Member" },
  ];
  assert.deepEqual([...C.part2Candidates(cases, [], member)].map((c) => c.id), ["c1"]);
  assert.deepEqual([...C.part2Candidates(cases, [], admin)].map((c) => c.id), ["c1", "c2"]);
  assert.deepEqual([...C.part2Candidates(cases, [{ case_id: "c1" }], member)].map((c) => c.id), []);
});

test("assignment requires a council member and an authorizing President", () => {
  const members = [
    { id: "m1", role: "member" },
    { id: "p1", role: "president" },
    { id: "s1", role: "secretary" },
  ];
  assert.equal(C.assignmentProblem("m1", "p1", members), null);
  assert.equal(C.assignmentProblem("", "p1", members), "chooseMember");
  assert.equal(C.assignmentProblem("m1", "", members), "choosePresident");
  assert.equal(C.assignmentProblem("m1", "s1", members), "choosePresident");
  assert.equal(C.assignmentProblem("ghost", "p1", members), "chooseMember");
});

test("agenda groups keep part and position order", () => {
  const groups = C.groupAgenda([
    { id: "b", part: 2, position: 2 },
    { id: "a", part: 1, position: 3 },
    { id: "c", part: 2, position: 1 },
  ]);
  assert.deepEqual([...groups[1]].map((r) => r.id), ["a"]);
  assert.deepEqual([...groups[2]].map((r) => r.id), ["c", "b"]);
});

test("server explanations are shown, never replaced by a fake success", () => {
  assert.equal(
    C.serverMessage({ status: 422, data: { messages: ["Reject requires correction instructions."] } }, t),
    "Reject requires correction instructions.",
  );
  assert.equal(
    C.serverMessage({ status: 403, data: { detail: "Administrator or secretary required." } }, t),
    "Administrator or secretary required.",
  );
  assert.equal(C.serverMessage({ status: 401 }, t), t("expired"));
  assert.equal(C.serverMessage({ status: 409 }, t), t("conflict"));
  assert.equal(C.serverMessage(new Error("network"), t), t("actionFailed"));
});

test("answers render verbatim and empty answers are labelled", () => {
  assert.equal(C.answerText("Exact text", t), "Exact text");
  assert.equal(C.answerText(["abuse", "addiction"], t), "abuse, addiction");
  assert.equal(C.answerText("", t), "Not answered");
  assert.equal(C.answerText(null, t), "Not answered");
  assert.equal(C.answerText({ a: 1 }, t), '{"a":1}');
});

test("English and Arabic word tables cover the same keys with real text", () => {
  const en = Object.keys(C.words.en).sort();
  const ar = Object.keys(C.words.ar).sort();
  assert.deepEqual(ar, en);
  for (const key of en) {
    assert.ok(C.words.en[key].trim(), `en.${key}`);
    assert.ok(C.words.ar[key].trim(), `ar.${key}`);
  }
  // Exact communication option wording is not the business of this module, but
  // every t("…") key used in the module must exist.
  const used = new Set([...source.matchAll(/\bt\("([A-Za-z0-9_]+)"/g)].map((m) => m[1]));
  for (const key of used) assert.ok(key in C.words.en, `missing word ${key}`);
});

test("module follows Plenix rules: no inline styles, raw colors or copied CSS", () => {
  assert.doesNotMatch(source, /style\s*:/);
  assert.doesNotMatch(source, /#[0-9a-fA-F]{3,8}\b/);
  assert.doesNotMatch(source, /!important/);
  assert.doesNotMatch(source, /<link|\.css['"]/);
});
