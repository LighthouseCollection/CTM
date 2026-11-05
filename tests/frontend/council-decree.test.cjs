const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const context = { window: {} };
for (const file of ["council.js", "council-case.js", "council-decree.js"])
  vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), context);
const source = fs.readFileSync("static/ctm/council-decree.js", "utf8");
const C = context.window.CTMCouncil;
const plain = (v) => JSON.parse(JSON.stringify(v));

test("decree module extends the namespace", () => {
  assert.equal(typeof C.DecreeWorkspace, "function");
});

test("a decree needs the current, presidentially approved certificate decision", () => {
  const approved = { type: "diss-both", current: true, approval: { president_id: "p" } };
  assert.equal(C.decreeEligibility(approved), null);
  assert.equal(C.decreeEligibility(null), "noDecision");
  assert.equal(C.decreeEligibility({ ...approved, approval: null }), "needsApproval");
  assert.equal(C.decreeEligibility({ ...approved, current: false }), "notCurrent");
  assert.equal(C.decreeEligibility({ ...approved, type: "denied" }), "deniedNoCertificate");
  assert.equal(C.decreeEligibility({ ...approved, type: "deferred" }), "deferredNoCertificate");
});

test("the decree editor selects its template from the recorded decision type", () => {
  assert.equal(C.decreeTemplateFor({ type: "diss-applicant" }).kind, "dissolution");
  assert.equal(C.decreeTemplateFor({ type: "null-granted" }).kind, "nullity");
  assert.match(source, /function DecreeTemplateDraft\(/);
  assert.match(source, /ctm-decree-workspace/);
  assert.doesNotMatch(source.slice(source.indexOf("function DecreeWorkspace"), source.indexOf("// ---------- Appeals")), /window\.CTMShell\.Workspace/);
});

test("decree ID follows DCR-[case] and the appeal proceeding suffix", () => {
  assert.equal(C.decreeReference("20261020-01", { kind: "initial", sequence: 1 }), "DCR-20261020-01");
  assert.equal(C.decreeReference("20261020-01", { kind: "appeal", sequence: 1 }), "DCR-20261020-01-A1");
  assert.equal(C.decreeReference("", { kind: "initial" }), null);
});

test("release status follows the latest release or withdrawal for that recipient", () => {
  const releases = [
    { party_id: "a", action: "release" },
    { party_id: "b", action: "release" },
    { party_id: "a", action: "withdraw" },
  ];
  assert.equal(C.releaseStatus(releases, "a"), "withdrawn");
  assert.equal(C.releaseStatus(releases, "b"), "released");
  assert.equal(C.releaseStatus(releases, "c"), "notReleased");
  const parties = [{ id: "a" }, { id: "b" }];
  assert.deepEqual(plain(C.entitledParties({ entitlements: { a: "certificate", b: "notice_only" } }, parties)), [{ id: "a" }]);
});

test("issue is reachable only after a stored, clean, signature-recorded PDF", () => {
  assert.equal(C.decreeStep({}), 0);
  assert.equal(C.decreeStep({ file: { scan_state: "pending" } }), 1);
  assert.equal(C.decreeStep({ file: { scan_state: "clean" } }), 2);
  assert.equal(C.decreeStep({ file: { scan_state: "clean" }, attested: true }), 3);
});

test("only a PDF up to 25 MB is accepted as the signed certificate", () => {
  const pdf = { name: "signed.pdf", type: "application/pdf", size: 1000 };
  assert.equal(C.uploadProblem(pdf, "en"), null);
  assert.equal(C.uploadProblem(null, "en"), "chooseFile");
  assert.equal(C.uploadProblem(pdf, "fr"), "chooseLanguage");
  assert.equal(C.uploadProblem({ name: "x.docx", type: "application/msword", size: 1 }, "both"), "pdfOnly");
  assert.equal(C.uploadProblem({ ...pdf, size: 26 * 1024 * 1024 }, "ar"), "tooLarge");
});

test("signature record needs a method and explicit confirmation", () => {
  assert.equal(C.attestationProblem({ method: "digital", confirmed: true }), null);
  assert.equal(C.attestationProblem({ method: "", confirmed: true }), "chooseMethod");
  assert.equal(C.attestationProblem({ method: "signed_scan", confirmed: false }), "confirmSigned");
});

test("latest proceeding prefers the open one, else the latest sequence", () => {
  assert.equal(C.latestProceeding({ proceedings: [{ id: "a", status: "closed", sequence: 1 }, { id: "b", status: "open", sequence: 2 }] }).id, "b");
  assert.equal(C.latestProceeding({ proceedings: [{ id: "a", status: "closed", sequence: 1 }, { id: "b", status: "closed", sequence: 2 }] }).id, "b");
  assert.equal(C.latestProceeding({ proceedings: [] }), null);
});

test("no replacement or clerical-correction decree workflow is offered", () => {
  const shown = JSON.stringify(C.decreeWords);
  assert.doesNotMatch(shown, /replac|clerical|استبدال|تصحيح الشهادة/i);
  const calls = [...source.matchAll(/api\(`([^`]+)`/g)].map((m) => m[1]);
  for (const url of calls) assert.doesNotMatch(url, /replace|correct/i);
});

test("decree words cover both languages and every used key", () => {
  const en = Object.keys(C.decreeWords.en).sort();
  assert.deepEqual(Object.keys(C.decreeWords.ar).sort(), en);
  const known = new Set([...en, ...Object.keys(C.caseWords.en), ...Object.keys(C.words.en)]);
  for (const [, key] of source.matchAll(/\bt\("([A-Za-z0-9_]+)"[),]/g)) assert.ok(known.has(key), key);
  for (const status of ["draft", "submitted", "accepted", "declined", "withdrawn"]) assert.ok(known.has("appeal_" + status), status);
  assert.doesNotMatch(source, /style\s*:/);
  assert.doesNotMatch(source, /#[0-9a-fA-F]{3,8}\b/);
});

test("appeals list only this case's appeals, newest first", () => {
  const rows = [
    { id: "a", kind: "appeal", case_id: "c1", submitted_at: "2026-10-01" },
    { id: "b", kind: "petition", case_id: "c1", submitted_at: "2026-10-05" },
    { id: "c", kind: "appeal", case_id: "c2", submitted_at: "2026-10-03" },
    { id: "d", kind: "appeal", case_id: "c1", submitted_at: "2026-10-09" },
  ];
  assert.deepEqual(plain(C.caseAppeals(rows, "c1").map((r) => r.id)), ["d", "a"]);
});

test("appeal result needs a heard case hearing and an explicit Accept or Decline", () => {
  assert.equal(C.appealResultProblem({ hearing: "h", result: "accept" }), null);
  assert.equal(C.appealResultProblem({ hearing: "h", result: "decline" }), null);
  assert.equal(C.appealResultProblem({ hearing: "", result: "accept" }), "chooseHearing");
  assert.equal(C.appealResultProblem({ hearing: "h", result: "" }), "chooseResult");
});

test("heard hearings are collected from agendas for this case only", () => {
  const agendas = [
    { session: { date: "2026-11-05" }, items: [{ id: "i1", case_id: "c1", hearing_id: "h1" }, { id: "i2", case_id: "c2", hearing_id: "h2" }] },
    { session: { date: "2026-12-03" }, items: [{ id: "i3", case_id: "c1", hearing_id: "h3" }, { id: "i4", case_id: "c1", hearing_id: null }] },
  ];
  assert.deepEqual(plain(C.heardHearings(agendas, "c1").map((h) => h.id)), ["h3", "h1"]);
});

test("F12: later petitions on the closed case join appeals and use their own result endpoint", () => {
  const rows = [
    { id: "a", kind: "appeal", case_id: "c1", submitted_at: "2026-10-01" },
    { id: "l", kind: "petition", origin: "closed_case_intake", case_id: "c1", submitted_at: "2026-10-05" },
    { id: "p", kind: "petition", case_id: "c1", submitted_at: "2026-09-01" },
  ];
  assert.deepEqual(plain(C.caseAppeals(rows, "c1").map((r) => r.id)), ["l", "a"]);
  assert.equal(C.resultUrl(rows[1]), "/api/applications/l/closed-case-result/");
  assert.equal(C.resultUrl(rows[0]), "/api/appeals/a/result/");
  assert.equal(C.isLaterFiling(rows[2]), false);
  assert.deepEqual(plain(C.awaitingReview([{ kind: "petition", status: "submitted", origin: "closed_case_intake" }, { id: "x", kind: "petition", status: "submitted" }]).map((r) => r.id)), ["x"]);
});

test("decree and appeals pages are wrapped in an error boundary", () => {
  for (const name of ["DecreeWorkspace", "AppealsWorkspace"]) assert.match(C[name].displayName || "", /^Guarded\(/, name);
});

// #97 slice 7 (D-0034): the decree is a record page (record-page.md) with its step actions in an ActionBar
// (page-actions.md); the appeals are the shared split list and detail (master-detail-workspace.md).
const slice = (from, to) => source.slice(source.indexOf(from), source.indexOf(to, source.indexOf(from)));

test("slice 7: the decree page is a RecordPage with its header and the approved decision aside", () => {
  const page = slice("function DecreeWorkspace(", "// ---------- Appeals");
  assert.match(page, /h\(P\.RecordPage, \{/);
  assert.match(page, /header: h\(P\.RecordPage\.Header, \{ title: t\("decree"\)/);
  assert.match(page, /aside: approved/);
  assert.doesNotMatch(page, /as: "h1"/);
});

test("slice 7: every decree step keeps its buttons in an embedded ActionBar", () => {
  const steps = slice("function DecreePreparation(", "function DecreeProtocolGuide(");
  const bars = steps.match(/h\(P\.ActionBar, \{ label: t\("steps"\), sticky: false \}/g) || [];
  assert.equal(bars.length, 4);
  assert.doesNotMatch(steps, /h\(P\.Inline, null, h\(P\.Button/);
  const guide = slice("function DecreeProtocolGuide(", "function DecreeWorkspace(");
  assert.match(guide, /h\(P\.ActionBar, \{ label: t\("decree"\), sticky: false \}/);
});

test("slice 7: the decree draft shows only the recorded decision; decree wording is never invented here", () => {
  // Template catalogs and exact wording belong to the later decree design (CTM-case-session-workflow.md).
  assert.deepEqual(plain(C.decreeTemplateFor({ type: "diss-applicant" })), { kind: "dissolution" });
  assert.deepEqual(plain(C.decreeTemplateFor({ type: "null-granted" })), { kind: "nullity" });
  assert.deepEqual(plain(C.decreeTemplateFor({ type: "granted" })), { kind: "decision" });
  const draft = slice("function DecreeTemplateDraft(", "function DecreePreparation(");
  assert.doesNotMatch(source, /Preamble|Canonical basis|Decree statement|The Tribunal (grants|declares|issues|records)|Clerical Tribunal of/);
  assert.match(draft, /decision\.grounds/);
  assert.match(draft, /decision\.conditions/);
  assert.match(draft, /t\("templateNotice"\)/);
  assert.doesNotMatch(draft, /ctm-decree-template|label: "/);
});

test("slice 7: appeals use the shared CTMShell.Workspace under a record page header", () => {
  const page = slice("function AppealsWorkspace(", "  Object.assign(window.CTMCouncil");
  assert.match(page, /h\(window\.CTMShell\.Workspace, \{/);
  assert.match(page, /h\(P\.RecordPage\.Header, \{ title: t\("appeals"\), description: t\("appealsScope"\)/);
  assert.match(page, /selectionPrompt: t\("chooseAppeal"\)/);
  assert.doesNotMatch(page, /P\.SplitView|P\.ReadingPane|as: "h1"/);
  assert.match(page, /title: t\("statusLabel"\), field: "status"/);
});
