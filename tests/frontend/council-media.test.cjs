const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const context = { window: {} };
for (const file of ["council.js", "council-case.js", "council-decree.js", "council-media.js"])
  vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), context);
const source = fs.readFileSync("static/ctm/council-media.js", "utf8");
const C = context.window.CTMCouncil;

test("media module extends the namespace with guarded pages", () => {
  assert.equal(typeof C.ReportRecorder, "function");
  assert.match(C.ReportsReader.displayName, /^Guarded\(/);
  assert.match(C.CaseFilesWorkspace.displayName, /^Guarded\(/);
});

test("recorder prefers formats the server accepts, in order", () => {
  assert.equal(C.chooseMimeType((t) => t === "audio/webm;codecs=opus" || t === "audio/mp4"), "audio/webm;codecs=opus");
  assert.equal(C.chooseMimeType((t) => t === "audio/mp4"), "audio/mp4"); // Safari / iOS
  assert.equal(C.chooseMimeType((t) => t.startsWith("audio/ogg")), "audio/ogg;codecs=opus");
  assert.equal(C.chooseMimeType(() => false), "");
  assert.equal(C.chooseMimeType(() => { throw new Error("x"); }), "");
  assert.equal(C.chooseMimeType(undefined), "");
});

test("file extension and size limit follow the stored container", () => {
  assert.equal(C.extensionFor("audio/webm;codecs=opus"), "webm");
  assert.equal(C.extensionFor("audio/mp4"), "m4a");
  assert.equal(C.extensionFor("audio/ogg;codecs=opus"), "ogg");
  assert.equal(C.sizeLimitBytes("audio/webm"), 500 * 1024 * 1024);
  assert.equal(C.sizeLimitBytes("audio/mp4"), 500 * 1024 * 1024);
  assert.equal(C.sizeLimitBytes("audio/ogg;codecs=opus"), 100 * 1024 * 1024);
});

test("microphone failures map to clear messages", () => {
  assert.equal(C.microphoneProblem({ name: "NotAllowedError" }), "micDenied");
  assert.equal(C.microphoneProblem({ name: "NotFoundError" }), "micMissing");
  assert.equal(C.microphoneProblem({ name: "NotReadableError" }), "micBusy");
  assert.equal(C.microphoneProblem({ name: "SecurityError" }), "micInsecure");
  assert.equal(C.microphoneProblem(null, { secure: false }), "micInsecure");
  assert.equal(C.microphoneProblem(null, { supported: false }), "micUnsupported");
  assert.equal(C.microphoneProblem({ name: "Weird" }), "micFailed");
  for (const key of ["micDenied", "micMissing", "micBusy", "micInsecure", "micUnsupported", "micFailed"]) {
    assert.ok(C.mediaWords.en[key] && C.mediaWords.ar[key], key);
  }
});

test("elapsed time excludes paused periods and formats as clock time", () => {
  const segments = [{ start: 0, end: 60000 }, { start: 120000, end: null }];
  assert.equal(C.elapsedMs(segments, 150000), 90000);
  assert.equal(C.formatDuration(90000), "1:30");
  assert.equal(C.formatDuration(3723000), "1:02:03");
  assert.equal(C.formatDuration(-5), "0:00");
});

test("viewer choice follows MIME type; Word downloads", () => {
  assert.equal(C.viewerKind({ mime_type: "image/jpeg" }), "image");
  assert.equal(C.viewerKind({ mime_type: "audio/mpeg" }), "audio");
  assert.equal(C.viewerKind({ mime_type: "video/webm" }), "video");
  assert.equal(C.viewerKind({ mime_type: "application/pdf" }), "pdf");
  assert.equal(C.viewerKind({ mime_type: "application/msword" }), "download");
});

test("only authorized /api/files/ routes are used; storage URLs are never trusted", () => {
  assert.deepEqual(
    JSON.parse(JSON.stringify(C.fileUrls({ id: "f1", download_url: "/api/files/f1/", preview_url: "/api/files/f1/?view=1" }))),
    { download: "/api/files/f1/", inline: "/api/files/f1/?view=1" },
  );
  const forged = C.fileUrls({ id: "f 2", download_url: "https://storage.example/originals/x.pdf", preview_url: "//evil/x" });
  assert.equal(forged.download, "/api/files/f%202/");
  assert.equal(forged.inline, null);
  assert.doesNotMatch(source, /object_key|originals\/|MEDIA_URL/);
});

test("evidence and documents sections split by document purpose", () => {
  const rows = [{ id: 1, category: "MC" }, { id: 2, category: "REC" }, { id: 3, category: "PET" }, { id: 4, category: "EVD" }];
  assert.deepEqual(C.sectionFiles(rows, "documents").map((r) => r.id), [1, 3]);
  assert.deepEqual(C.sectionFiles(rows, "evidence").map((r) => r.id), [2, 4]);
});

test("recording submission order: upload, safety check, associate, finalize", () => {
  const i = (s) => source.indexOf(s);
  const upload = i('api("/api/files/", { method: "POST", body: form })');
  const scan = i("waitForScan(stored.id)");
  const associate = i('api("/api/recordings/", {');
  const finalize = i("/finalize/`");
  assert.ok(upload > 0 && scan > upload && associate > scan && finalize > associate);
  assert.match(source, /notice_recorded: true/);
  // Local audio is cleared only after the finalize call succeeds.
  assert.ok(i("await store.clear(storageKey).catch") > finalize);
});

test("media words cover both languages, every used key, and Plenix rules", () => {
  const en = Object.keys(C.mediaWords.en).sort();
  assert.deepEqual(Object.keys(C.mediaWords.ar).sort(), en);
  const known = new Set([...en, ...Object.keys(C.caseWords.en), ...Object.keys(C.words.en)]);
  for (const [, key] of source.matchAll(/\bt\("([A-Za-z0-9_]+)"[),]/g)) assert.ok(known.has(key), key);
  assert.doesNotMatch(source, /style\s*:/);
  assert.doesNotMatch(source, /#[0-9a-fA-F]{3,8}\b/);
  assert.doesNotMatch(source, /innerHTML/);
});

test("D19: revise authority comes only from the server's can_revise flag", () => {
  assert.equal(C.revisionAccess({ id: "r" }), "unknown"); // server without authorship
  assert.equal(C.revisionAccess({ can_revise: true }), "allowed");
  assert.equal(C.revisionAccess({ can_revise: false, author_id: "me" }), "denied");
  assert.equal(C.revisionAccess({ can_revise: "true" }), "denied"); // only literal true
  const tabs = source.slice(source.indexOf("function ReportDetailTabs("), source.indexOf("function ReportsReader("));
  assert.match(tabs, /access === "allowed" && latestShown/);
  assert.doesNotMatch(tabs, /author_id\s*===|role\s*===\s*"admin"/);
});

test("D19: text answers are editable; files and structured answers are carried unchanged", () => {
  const report = { questions: [{ code: "Q1" }, { code: "Q2" }, { code: "Q3" }] };
  const latest = { version: 2, answers: { Q1: "old one", Q2: "kept", files: ["f1"], extra: "loose text" }, observations: "obs" };
  assert.deepEqual([...C.revisionFields(report, latest)], ["Q1", "Q2", "Q3", "extra"]);
  const draft = C.revisionDraft(report, latest);
  assert.equal(draft.answers.Q3, "");
  assert.equal(C.revisionChanged(latest, draft), false);
  draft.answers.Q1 = "new one";
  draft.answers.files = "forged"; // never overrides a structured answer
  const payload = JSON.parse(JSON.stringify(C.revisionPayload(latest, draft)));
  assert.deepEqual(payload, { answers: { Q1: "new one", Q2: "kept", files: ["f1"], extra: "loose text" }, observations: "obs" });
  assert.equal(C.revisionChanged(latest, draft), true);
  assert.equal("Q3" in payload.answers, false); // an empty unanswered question is not added
  assert.equal(C.revisionChanged(latest, { answers: {}, observations: "obs 2" }), true);
});

test("D19: save re-reads history first and stops on a newer version; failures keep the text", () => {
  const editor = source.slice(source.indexOf("function ReportRevisionEditor("), source.indexOf("// ---------- Completed reports reader"));
  const read = editor.indexOf("const current = await api(url)");
  const staleCheck = editor.indexOf("newest.version !== base0.version");
  const post = editor.indexOf('method: "POST"');
  assert.ok(read > 0 && staleCheck > read && post > staleCheck);
  assert.match(editor, /error\.status === 403\) \{\s*setDenied\(true\)/);
  // The draft is never cleared on failure; only onSaved closes the editor.
  assert.doesNotMatch(editor, /setDraft\(\s*revisionDraft[^)]*\)\s*;\s*\}\s*catch/);
  assert.match(editor, /beforeunload/);
});

test("D19: answers read in the request's question order; a refused save refreshes the rows", () => {
  const report = { questions: [{ code: "BASIS-01" }, { code: "OPEN-01" }] };
  const answers = { attendance: ["applicant"], "OPEN-01": "b", "BASIS-01": "a" }; // PostgreSQL jsonb key order
  assert.deepEqual([...C.answerEntries(report, answers)].map(([k]) => k), ["BASIS-01", "OPEN-01", "attendance"]);
  const editor = source.slice(source.indexOf("function ReportRevisionEditor("), source.indexOf("// ---------- Completed reports reader"));
  assert.match(editor, /setDenied\(true\);\s*if \(onDenied\) onDenied\(\)/);
});
