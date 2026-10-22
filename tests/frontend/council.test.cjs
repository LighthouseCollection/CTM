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

test("a session adjourned today stays in Current through Los Angeles midnight", () => {
  const rows = [
    { id: "active", state: "planned", date: "2026-10-22" },
    { id: "adjourned", state: "closed", date: "2026-10-22", adjourned_at: "2026-10-22T19:30:00-07:00" },
    { id: "archived", state: "closed", date: "2026-10-21", adjourned_at: "2026-10-21T19:30:00-07:00" },
  ];
  const today = C.sessionBuckets(rows, "2026-10-22");
  assert.deepEqual([...today.current].map((row) => row.id), ["active", "adjourned"]);
  assert.deepEqual([...today.archived].map((row) => row.id), ["archived"]);
  const tomorrow = C.sessionBuckets(rows, "2026-10-23");
  assert.deepEqual([...tomorrow.current].map((row) => row.id), ["active"]);
  assert.deepEqual([...tomorrow.archived].map((row) => row.id), ["adjourned", "archived"]);
});

test("missing session metadata stays missing instead of becoming an epoch date", () => {
  assert.equal(C.formatSessionStart(null, "en"), null);
  assert.equal(C.formatSessionStart("", "ar"), null);
  assert.match(C.formatSessionStart("2030-01-02T10:00:00-08:00", "en"), /2030/);
});

test("one session per date and real calendar dates only", () => {
  const existing = [{ date: "2026-11-01" }];
  assert.equal(C.sessionDateProblem("2026-11-02", existing), null);
  assert.equal(C.sessionDateProblem("2026-11-01", existing), "dateTaken");
  assert.equal(C.sessionDateProblem("", existing), "dateRequired");
  assert.equal(C.sessionDateProblem("2026-02-30", existing), "dateRequired");
  assert.equal(C.sessionDateProblem("2026-13-01", existing), "dateRequired");
});

const visible = (text) => text.replace(/[⁦-⁩]/g, "");
test("hearing title uses exact contract wording and never invents names", () => {
  assert.match(C.hearingTitle(["John Smith", "Mary Smith"], "2026-10-20", t), /⁨John Smith⁩/);
  assert.equal(
    visible(C.hearingTitle(["John Smith", "Mary Smith"], "2026-10-20", t)),
    "Case Hearing of John Smith vs. Mary Smith on Council Session 2026-10-20",
  );
  assert.equal(
    visible(C.hearingTitle(["John Smith"], "2026-10-20", t)),
    "Case Hearing of John Smith vs. Unknown spouse on Council Session 2026-10-20",
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

test("session placement choices use the parties' names while retaining the case ID as their value", () => {
  assert.equal(C.casePlacementLabel({ number: "20261020-02", party_names: ["Mickey Mouse", "Minnie Mouse"] }), "Mickey Mouse | Minnie Mouse");
  assert.equal(C.casePlacementLabel({ number: "20261020-02", party_names: ["Mickey Mouse"] }), "Mickey Mouse");
  assert.equal(C.casePlacementLabel({ number: "20261020-02", party_names: [] }), "20261020-02");
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

test("session assignment metric counts Part 1 agenda rows still awaiting assignment", () => {
  const agenda = [
    { id: "a", part: 1, state: "scheduled" },
    { id: "b", part: 1, state: "assigned" },
    { id: "c", part: 2, state: "scheduled" },
  ];
  assert.equal(C.pendingAssignmentCount(agenda), 1);
  assert.equal(C.pendingAssignmentCount([...agenda, { id: "d", part: 1, state: "scheduled" }]), 2);
  assert.equal(C.pendingAssignmentCount(agenda.map((row) => row.id === "a" ? { ...row, state: "assigned" } : row)), 0);
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

test("agenda controls follow server capability flags when present", () => {
  const planned = { state: "planned", date: "2026-11-05", can_manage: true };
  const row = { part: 2, state: "scheduled", assigned_member_id: "m", can_present: false, can_record_outcome: false, hearing_id: null };
  const memberFlags = C.agendaActions(row, { ...planned, can_manage: false }, member, null);
  assert.equal(memberFlags.present, false);
  assert.equal(memberFlags.presentNeedsAttendance, true);
  assert.equal(memberFlags.testimony, true);
  assert.equal(C.agendaActions({ ...row, can_present: true }, planned, member, null).present, true);
  assert.equal(C.agendaActions(row, planned, { ...member, id: "other" }, null).testimony, false);
  assert.equal(C.agendaActions({ ...row, state: "heard", hearing_id: "h", can_record_outcome: true }, planned, member, null).outcome, true);
  assert.equal(C.agendaActions({ ...row, state: "heard", hearing_id: "h" }, planned, member, null).outcome, false);
  const part1 = { part: 1, state: "scheduled", assigned_member_id: null };
  assert.equal(C.agendaActions(part1, planned, admin, null).assign, true);
  assert.equal(C.agendaActions(part1, { ...planned, can_manage: false }, admin, null).assign, false);
  assert.equal(C.agendaActions(part1, { state: "closed", date: "2026-11-05" }, admin, null).assign, false);
});

test("agenda fallback for older servers uses role and shown name only for display", () => {
  const legacy = { part: 2, state: "scheduled" };
  const caseRow = { assigned_member: "Fr. Member" };
  assert.equal(C.agendaActions(legacy, { state: "planned" }, member, caseRow).present, true);
  assert.equal(C.agendaActions(legacy, { state: "planned" }, admin, caseRow).present, false);
  assert.equal(C.agendaActions(legacy, { state: "planned" }, member, caseRow).presentNeedsAttendance, false);
});

test("testimony needs applicant, ordered times and private instructions", () => {
  const ok = { party: "p", start: "10:00", end: "10:30", instructions: "Room 2" };
  assert.equal(C.testimonyProblem(ok, "2026-11-05"), null);
  assert.equal(C.testimonyProblem({ ...ok, party: "" }, "2026-11-05"), "chooseParty");
  assert.equal(C.testimonyProblem({ ...ok, start: "" }, "2026-11-05"), "timesRequired");
  assert.equal(C.testimonyProblem({ ...ok, end: "09:00" }, "2026-11-05"), "endAfterStart");
  assert.equal(C.testimonyProblem({ ...ok, end: "10:00" }, "2026-11-05"), "endAfterStart");
  assert.equal(C.testimonyProblem({ ...ok, instructions: " " }, "2026-11-05"), "instructionsRequired");
});

test("review labels come from the bound questionnaire and never invent wording", () => {
  const row = { questionnaire: { definition: { fields: [{ code: "first_name", label_en: "First name", label_ar: "" }] } } };
  assert.equal(C.fieldLabel(row, "first_name", "en"), "First name");
  assert.equal(C.fieldLabel(row, "first_name", "ar"), null);
  assert.equal(C.fieldLabel(row, "unknown_code", "en"), null);
  assert.equal(C.fieldLabel({}, "first_name", "en"), null);
});

test("search phrase length matches the server's 2–200 character rule", () => {
  assert.equal(C.searchProblem("ab"), null);
  assert.equal(C.searchProblem(" a "), "searchLength");
  assert.equal(C.searchProblem("x".repeat(201)), "searchLength");
  assert.equal(typeof C.SearchWorkspace, "function");
});

test("My cases match stable account IDs, never display-name equality", () => {
  const cases = [
    { id: "1", status: "open", assigned_member: "Fr. Member", assigned_member_id: "m" },
    { id: "2", status: "closed", assigned_member: "Fr. Member", assigned_member_id: "m" },
    { id: "3", status: "open", assigned_member: "Fr. Member", assigned_member_id: "other" },
    { id: "4", status: "open", assigned_member: null },
  ];
  assert.deepEqual([...C.myCases(cases, member)].map((c) => c.id), ["1"]);
  assert.equal(C.myCases([{id:"5",status:"open",assigned_member:member.name}],member).length,0);
});

test("word tables have no duplicate keys that would silently override text", () => {
  for (const file of ["council.js", "council-case.js", "council-decree.js"]) {
    const src = fs.readFileSync(`static/ctm/${file}`, "utf8");
    for (const lang of ["en", "ar"]) {
      const start = src.indexOf(`    ${lang}: {`, src.indexOf("const words = {"));
      const end = src.indexOf("\n    },", start);
      const keys = [...src.slice(start, end).matchAll(/^      ([A-Za-z0-9_]+):/gm)].map((m) => m[1]);
      const dupes = keys.filter((k, i) => keys.indexOf(k) !== i);
      assert.deepEqual(dupes, [], `${file} ${lang}`);
    }
  }
});

test("cases table filters open or archived cases by number or manager", () => {
  const cases = [
    { id: "1", number: "20261020-01", status: "open", assigned_member: "Fr. Mark" },
    { id: "2", number: "20261020-02", status: "open", assigned_member: null },
    { id: "3", number: "20260901-01", status: "closed", assigned_member: "Fr. Mark" },
  ];
  assert.deepEqual([...C.caseRows(cases, false, "")].map((c) => c.id), ["1", "2"]);
  assert.deepEqual([...C.caseRows(cases, true, "")].map((c) => c.id), ["3"]);
  assert.deepEqual([...C.caseRows(cases, false, "mark")].map((c) => c.id), ["1"]);
  assert.deepEqual([...C.caseRows(cases, false, "-02")].map((c) => c.id), ["2"]);
});

test("statistics are plain counts, flagged partial at the list limit, never rates", () => {
  const cases = [
    { status: "open", assigned_member: "Fr. A" },
    { status: "open", assigned_member: "Fr. A" },
    { status: "open", assigned_member: null },
    { status: "closed", assigned_member: "Fr. B" },
  ];
  const s = C.caseStatistics(cases, [{ state: "planned" }, { state: "closed" }, { state: "closed" }]);
  assert.equal(s.open, 3);
  assert.equal(s.unassigned, 1);
  assert.equal(s.closed, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(s.byManager)), [["Fr. A", 2]]);
  assert.equal(s.plannedSessions, 1);
  assert.equal(s.closedSessions, 2);
  assert.equal(s.partial, false);
  assert.equal(C.caseStatistics(Array(100).fill({ status: "open" }), []).partial, true);
  const src = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.doesNotMatch(src.slice(src.indexOf("function caseStatistics"), src.indexOf("function StatisticsWorkspace")), /\/|percent|rate/i);
});

test("Los Angeles times carry the right daylight-saving offset", () => {
  assert.equal(C.laIso("2026-11-05", "10:30"), "2026-11-05T10:30:00-08:00");
  assert.equal(C.laIso("2026-10-20", "09:00"), "2026-10-20T09:00:00-07:00");
  assert.equal(C.laIso("2026-03-09", "09:00"), "2026-03-09T09:00:00-07:00");
  assert.equal(C.laIso("2026-03-07", "23:30"), "2026-03-07T23:30:00-08:00");
  assert.equal(C.laIso("bad", "09:00"), null);
});

test("reschedule needs a new free date, a reason and non-overlapping times for every invitation", () => {
  const items = [
    { id: "i1", testimony: [{ id: "t1", state: "scheduled" }, { id: "t0", state: "cancelled" }] },
    { id: "i2", testimony: [{ id: "t2", state: "scheduled" }] },
  ];
  const appts = C.activeAppointments(items);
  assert.deepEqual(appts.map((a) => a.id), ["t1", "t2"]);
  const sessions = [{ date: "2026-11-05" }, { date: "2026-11-12" }];
  const ok = { date: "2026-11-19", reason: "Bishop travelling", times: { t1: { start: "10:00", end: "10:30" }, t2: { start: "10:30", end: "11:00" } } };
  assert.equal(C.rescheduleProblem(ok, appts, sessions, "2026-11-05"), null);
  assert.equal(C.rescheduleProblem({ ...ok, date: "2026-11-12" }, appts, sessions, "2026-11-05"), "dateTaken");
  assert.equal(C.rescheduleProblem({ ...ok, date: "2026-11-05" }, appts, sessions, "2026-11-05"), "sameDate");
  assert.equal(C.rescheduleProblem({ ...ok, reason: " " }, appts, sessions, "2026-11-05"), "reasonRequired");
  assert.equal(C.rescheduleProblem({ ...ok, times: { t1: ok.times.t1 } }, appts, sessions, "2026-11-05"), "replacementTimes");
  assert.equal(C.rescheduleProblem({ ...ok, times: { ...ok.times, t2: { start: "10:15", end: "10:45" } } }, appts, sessions, "2026-11-05"), "replacementOverlap");
  const payload = JSON.parse(JSON.stringify(C.reschedulePayload(ok, appts)));
  assert.deepEqual(payload, {
    date: "2026-11-19",
    reason: "Bishop travelling",
    appointments: {
      t1: { starts_at: "2026-11-19T10:00:00-08:00", ends_at: "2026-11-19T10:30:00-08:00" },
      t2: { starts_at: "2026-11-19T10:30:00-08:00", ends_at: "2026-11-19T11:00:00-08:00" },
    },
  });
});

test("search posts the phrase in the body and falls back to GET only on 405", async () => {
  const calls = [];
  const modern = async (url, options) => { calls.push([url, options?.method, options?.body]); return { items: [] }; };
  await C.runSearch(modern, "Smith", false);
  assert.deepEqual(calls[0], ["/api/search/", "POST", JSON.stringify({ q: "Smith", history: false })]);
  const legacyCalls = [];
  const legacy = async (url, options) => {
    legacyCalls.push(url);
    if (options?.method === "POST") throw Object.assign(new Error("x"), { status: 405 });
    return { items: [] };
  };
  await C.runSearch(legacy, "Smith Jr", true);
  assert.deepEqual(legacyCalls, ["/api/search/", "/api/search/?q=Smith%20Jr&history=true"]);
  await assert.rejects(C.runSearch(async () => { throw Object.assign(new Error("x"), { status: 422 }); }, "ab", false));
});

test("F15: assignment authorizers and recorders follow server flags; one person may hold both", () => {
  const legacy = [{ id: "p", role: "president" }, { id: "s", role: "secretary" }];
  assert.deepEqual([...C.assignmentAuthorizers(legacy)].map((m) => m.id), ["p"]);
  assert.equal(C.canRecordAssignment(admin, legacy), true);
  assert.equal(C.canRecordAssignment(member, legacy), false);
  const flagged = [
    { id: "a", role: "admin", can_authorize_assignment: true, can_record_assignment: true },
    { id: "m", role: "member", can_authorize_assignment: false, can_record_assignment: false },
    { id: "p", role: "president", can_authorize_assignment: true, can_record_assignment: true },
  ];
  assert.deepEqual([...C.assignmentAuthorizers(flagged)].map((m) => m.id), ["a", "p"]);
  assert.equal(C.canRecordAssignment({ id: "p", role: "president", portal: "council" }, flagged), true);
  assert.equal(C.canRecordAssignment({ id: "m", role: "member", portal: "council" }, flagged), false);
  // Same person as authorizer and recorder is valid.
  assert.equal(C.assignmentProblem("m", "a", flagged), null);
  // President approval list is unchanged by the assignment flags.
  assert.deepEqual([...C.presidents(flagged)].map((m) => m.id), ["p"]);
  const part1 = { part: 1, state: "scheduled" };
  assert.equal(C.agendaActions(part1, { state: "planned", can_manage: false }, { id: "p", role: "president" }, null, { canRecordAssignment: true }).assign, true);
  assert.equal(C.agendaActions(part1, { state: "planned", can_manage: true }, admin, null, { canRecordAssignment: false }).assign, false);
});

test("F12: council consideration queue is pending appeals plus closed-case later petitions", () => {
  const rows = [
    { id: "a", kind: "appeal", status: "submitted" },
    { id: "b", kind: "appeal", status: "accepted" },
    { id: "c", kind: "petition", status: "submitted", origin: "closed_case_intake" },
    { id: "d", kind: "petition", status: "submitted" },
  ];
  assert.deepEqual([...C.considerationQueue(rows)].map((r) => r.id), ["a", "c"]);
});


test("F34: names, numbers and emails are isolated inside RTL text; empty stays empty", () => {
  assert.equal(C.isolate("20261020-01"), "⁨20261020-01⁩");
  assert.equal(C.isolate("mary@example.test"), "⁨mary@example.test⁩");
  assert.equal(C.isolate(""), "");
  assert.equal(C.isolate(null), "");
});

test("sessions split into upcoming (soonest first) and past (latest first)", () => {
  const rows = [
    { id: "a", date: "2026-11-05", state: "planned" },
    { id: "b", date: "2026-10-01", state: "closed" },
    { id: "c", date: "2026-10-15", state: "planned" },
    { id: "d", date: "2026-12-03", state: "planned" },
  ];
  const g = C.splitSessions(rows, "2026-10-21");
  assert.deepEqual(g.upcoming.map((s) => s.id), ["a", "d"]);
  assert.deepEqual(g.past.map((s) => s.id), ["c", "b"]);
  assert.match(C.todayInLosAngeles(new Date("2026-10-22T05:00:00Z")), /^2026-10-21$/);
});

test("sessions are separated into current, upcoming, and archived destinations", () => {
  const rows = [
    { id: "future-near", date: "2026-11-05", state: "planned" },
    { id: "archived-old", date: "2026-10-01", state: "closed" },
    { id: "current-old", date: "2026-10-15", state: "planned" },
    { id: "future-far", date: "2026-12-03", state: "planned" },
    { id: "current-today", date: "2026-10-21", state: "planned" },
    { id: "archived-new", date: "2026-10-20", state: "closed" },
  ];
  const buckets = C.sessionBuckets(rows, "2026-10-21");
  assert.deepEqual(buckets.current.map((row) => row.id), ["current-today", "current-old"]);
  assert.deepEqual(buckets.upcoming.map((row) => row.id), ["future-near", "future-far"]);
  assert.deepEqual(buckets.archived.map((row) => row.id), ["archived-new", "archived-old"]);
});

test("every notification kind the backend sends has EN and AR labels in the shell", () => {
  const app = fs.readFileSync("static/ctm/app.js", "utf8");
  const kinds = ["report_requested", "report_received", "file_uploaded", "answer_changed", "applicant_message", "case_message", "assignment_changed",
    "submission_received", "intake_submitted", "decree_available", "case_reopened", "filing_withdrawn", "appeal_added", "testimony_response",
    "testimony_invited", "testimony_rescheduled", "testimony_cancelled", "closed_intake_submitted", "application_accepted", "application_returned",
    "appeal_accept", "appeal_decline", "decree_issued", "petition_denied", "petitions_withdrawn", "payment_finance_review", "paid_filing_review"];
  for (const kind of kinds) assert.equal((app.match(new RegExp("event_" + kind + ":", "g")) || []).length, 2, kind);
});


test("adjournment requires an editable end time and sends it to the session endpoint", () => {
  assert.match(source, /label: t\("adjournEndTime"\)/);
  assert.match(source, /JSON\.stringify\(\{ adjourned: true, ended_at:/);
});
