// D20 (#3): council recording status, transcript reading, review, correction and retry against the backend #7
// contract (docs/implementation/media-read-and-review.md, twenty-batch-continuation.md on work/vm-frm-backend).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { harness, load, find, textareas, notices, buttons, dialogs, type, settle, byName, textOf } = require("./harness.cjs");

const fail = (status, data = {}) => Object.assign(new Error(`HTTP ${status}`), { status, data });
const report = { id: "rep-1", kind: "interview", title: "Interview" };
const base = {
  id: "rec-1", file_id: "f-1", mime_type: "video/webm", byte_count: 2048, duration_ms: 95000, captured_by: "u-1",
  notice_recorded: true, created_at: "2026-10-21T18:00:00Z", finalized_at: "2026-10-21T18:01:00Z",
  download_url: "/api/files/f-1/", processing: null, transcripts: [], can_finalize: false,
};
const rec = (extra) => ({ ...base, ...extra });

function mount(component, props, routes) {
  const h = harness();
  const C = load(h);
  const calls = [];
  const api = async (url, options = {}) => {
    calls.push({ url, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : undefined });
    const handler = routes(url, options.method || "GET", options.body ? JSON.parse(options.body) : undefined, calls);
    if (handler instanceof Error) throw handler;
    return handler;
  };
  const ui = {
    C, calls,
    tree: null,
    async render() { ui.tree = h.render(C[component], { api, lang: "en", ...props }); await settle(); ui.tree = h.render(C[component], { api, lang: "en", ...props }); return ui.tree; },
    text() { return textOf(ui.tree); },
    notes() { return notices(ui.tree).join(" | "); },
    button(label) { return buttons(ui.tree, label)[0]; },
    async click(label) { const b = ui.button(label); assert.ok(b, `button "${label}"`); await b.props.onClick(); await settle(); await ui.render(); },
    posts() { return calls.filter((c) => c.method === "POST"); },
    unmount() { h.unmount(); },
  };
  return ui;
}

test("processing states map to honest messages; queued never claims success", () => {
  const C = load(harness());
  assert.equal(C.processingView(rec({ download_url: null })).key, "originalUnavailable");
  assert.deepEqual({ ...C.processingView(rec({ finalized_at: null, can_finalize: true })) }, { key: "statusNotQueued", tone: "info", finalize: true });
  assert.equal(C.processingView(rec({ finalized_at: null })).key, "statusNotQueuedNoAuthority");
  assert.equal(C.processingView(rec({ processing: null })).key, "statusMissing");
  assert.equal(C.processingView(rec({ processing: { state: "queued", attempt: 1 } })).key, "statusQueued");
  assert.equal(C.processingView(rec({ processing: { state: "running", attempt: 2 } })).attempt, "2");
  assert.equal(C.processingView(rec({ processing: { state: "succeeded", attempt: 1 } })).key, "statusSucceeded");
  const failed = C.processingView(rec({ processing: { state: "failed", attempt: 1, can_retry: true } }));
  assert.equal(failed.key, "statusFailed");
  assert.equal(failed.retry, true);
  assert.equal(C.processingView(rec({ processing: { state: "failed", attempt: 1, can_retry: false } })).retry, false);
  const queued = C.mediaTranslator("en")("statusQueued", { attempt: "1" });
  assert.match(queued, /may not be configured/);
  assert.doesNotMatch(queued, /finished|succeeded|complete/i);
});

test("versions group by language and kind, newest first; only well-formed timed segments are shown", () => {
  const C = load(harness());
  const groups = C.transcriptGroups([
    { id: "a1", language: "en", kind: "original", version: 1 },
    { id: "a2", language: "en", kind: "original", version: 2 },
    { id: "b1", language: "ar", kind: "translation", version: 1 },
  ]);
  assert.deepEqual([...groups].map((g) => g.key), ["ar|translation", "en|original"]);
  assert.deepEqual([...groups[1].versions].map((v) => v.id), ["a2", "a1"]);
  assert.deepEqual(
    [...C.timedSegments([{ start: 0, end: 2.5, text: "Hello" }, { start: "x", end: 1, text: "bad" }, { start: 3, end: 1, text: "backwards" }, { text: "" }, null])].map((s) => s.text),
    ["Hello"],
  );
  assert.equal(C.timedSegments("not a list").length, 0);
});

test("recording status: playback from the authorized route, length, notice, and a queued state", async () => {
  const ui = mount("RecordingStatusList", { report, refreshKey: 0 }, () => ({ items: [rec({ processing: { run_id: "run-1", state: "queued", attempt: 1, can_retry: false } })] }));
  await ui.render();
  const player = byName(ui.tree, "MediaPlayer")[0];
  assert.equal(player.props.src, "/api/files/f-1/");
  assert.equal(player.props.kind, "audio");
  assert.match(ui.text(), /1:35/);
  assert.match(ui.text(), /Confirmed/);
  assert.match(ui.notes(), /Waiting for transcription \(attempt 1\)\. The transcription service may not be configured/);
  assert.equal(ui.button("Retry transcription"), undefined);
});

test("recording status: retry a failed run creates the next attempt and reloads", async () => {
  let state = { run_id: "run-1", state: "failed", attempt: 1, can_retry: true, safe_error: "Processing failed; the original is retained." };
  const ui = mount("RecordingStatusList", { report, refreshKey: 0 }, (url, method) => {
    if (method === "POST" && url === "/api/processing/run-1/retry/") { state = { run_id: "run-2", state: "queued", attempt: 2, can_retry: false }; return { id: "run-2", attempt: 2, state: "queued" }; }
    return { items: [rec({ processing: state })] };
  });
  await ui.render();
  assert.match(ui.notes(), /Transcription failed \(attempt 1\)\. Processing failed; the original is retained\./);
  await ui.click("Retry transcription");
  assert.deepEqual(ui.posts().map((c) => [c.url, c.body]), [["/api/processing/run-1/retry/", {}]]);
  await ui.render();
  assert.match(ui.notes(), /Attempt 2 is queued/);
  assert.match(ui.notes(), /Waiting for transcription \(attempt 2\)/);
});

test("recording status: an unfinalized recording can be queued only when the server allows it", async () => {
  const ui = mount("RecordingStatusList", { report, refreshKey: 0 }, (url, method) =>
    method === "POST" ? { id: "run-1" } : { items: [rec({ finalized_at: null, can_finalize: true })] });
  await ui.render();
  await ui.click("Request transcription");
  assert.deepEqual(ui.posts().map((c) => c.url), ["/api/recordings/rec-1/finalize/"]);
  const denied = mount("RecordingStatusList", { report, refreshKey: 0 }, () => ({ items: [rec({ finalized_at: null, can_finalize: false })] }));
  await denied.render();
  assert.equal(denied.button("Request transcription"), undefined);
  assert.match(denied.notes(), /case manager can request it/);
  const unsafe = mount("RecordingStatusList", { report, refreshKey: 0 }, () => ({ items: [rec({ download_url: null })] }));
  await unsafe.render();
  assert.equal(byName(unsafe.tree, "MediaPlayer").length, 0);
  assert.match(unsafe.notes(), /not passed the automatic safety check/);
});

test("transcripts: nothing released yet is said plainly; no recording shows an empty state", async () => {
  const none = mount("TranscriptsPanel", { report, refreshKey: 0 }, () => ({ items: [] }));
  await none.render();
  assert.match(none.text(), /No recording has been submitted/);
  const unreleased = mount("TranscriptsPanel", { report, refreshKey: 0 }, () => ({ items: [rec({ processing: { run_id: "r", state: "succeeded", attempt: 1 } })] }));
  await unreleased.render();
  assert.match(unreleased.notes(), /No transcript is available to you yet/);
});

const detail = (extra) => ({ id: "tr-1", recording_id: "rec-1", run_id: "run-1", kind: "original", language: "en", version: 1,
  text: "Generated first paragraph.\n\nSecond paragraph.", segments: [{ start: 0, end: 2, text: "Generated" }], reviewed: false, can_review: true,
  timestamp: "2026-10-21T18:05:00Z", ...extra });

test("viewer: unreviewed text is marked, review is confirmed and posts {}", async () => {
  let reviewed = false;
  const ui = mount("TranscriptViewer", { revisionId: "tr-1", latestVersion: 1, onChanged() {} }, (url, method, body) => {
    if (method === "POST") { assert.deepEqual(body, {}); reviewed = true; return { id: "rv-1" }; }
    return detail({ reviewed });
  });
  await ui.render();
  assert.match(ui.notes(), /Generated text, not yet reviewed/);
  assert.match(ui.text(), /Generated first paragraph\./);
  assert.match(ui.text(), /0:00–0:02/);
  await ui.click("Mark as reviewed");
  assert.equal(ui.posts().length, 0, "confirmation first");
  const confirm = dialogs(ui.tree).find((d) => d.props.open);
  await confirm.props.onConfirm();
  await settle();
  await ui.render();
  assert.deepEqual(ui.posts().map((c) => c.url), ["/api/transcripts/tr-1/review/"]);
  assert.match(ui.notes(), /Version 1 is reviewed/);
});

test("viewer: readers without review authority get no review or correction controls", async () => {
  const ui = mount("TranscriptViewer", { revisionId: "tr-1", latestVersion: 1 }, () => detail({ reviewed: true, can_review: false }));
  await ui.render();
  assert.equal(ui.button("Mark as reviewed"), undefined);
  assert.equal(ui.button("Correct text"), undefined);
  assert.doesNotMatch(ui.notes(), /not yet reviewed/);
});

test("viewer: an earlier version is read-only history", async () => {
  const ui = mount("TranscriptViewer", { revisionId: "tr-1", latestVersion: 3 }, () => detail({ reviewed: true }));
  await ui.render();
  assert.match(ui.notes(), /earlier version\. The latest version is 3/);
  assert.equal(ui.button("Correct text"), undefined);
});

test("correction: bound to the shown version, creates the next unreviewed version, text kept across navigation", async () => {
  let changed = null;
  const props = { revisionId: "tr-1", latestVersion: 1, onChanged: (id) => { changed = id; } };
  const routes = (url, method, body) => (method === "POST" ? { id: "tr-2", version: 2, reviewed: false } : detail({}));
  const ui = mount("TranscriptViewer", props, routes);
  await ui.render();
  await ui.click("Correct text");
  type(textareas(ui.tree)[0], "Corrected by the case manager.");
  await ui.render();
  assert.equal(ui.C.unsavedDrafts.get("transcript:rec-1:en:original").text, "Corrected by the case manager.");
  ui.unmount(); // sidebar navigation
  await ui.render();
  assert.equal(textareas(ui.tree)[0].props.value, "Corrected by the case manager.", "editor reopens with the text");
  assert.match(ui.notes(), /unsaved correction was restored/);
  const form = find(ui.tree, (n) => n.props && n.props.onSubmit)[0];
  await form.props.onSubmit({ preventDefault() {} });
  await settle();
  assert.deepEqual(ui.posts()[0], { url: "/api/transcripts/tr-1/correct/", method: "POST", body: { expected_version: 1, text: "Corrected by the case manager.", segments: [] } });
  assert.equal(changed, "tr-2");
  assert.equal(ui.C.unsavedDrafts.has("transcript:rec-1:en:original"), false);
});

test("correction: a newer saved version is reported with the text kept; nothing is resent", async () => {
  const ui = mount("TranscriptViewer", { revisionId: "tr-1", latestVersion: 1, onChanged() {} }, (url, method) =>
    method === "POST" ? fail(422, { error: "validation", messages: ["A newer transcript version was saved. Reload before correcting."] }) : detail({}));
  await ui.render();
  await ui.click("Correct text");
  type(textareas(ui.tree)[0], "My correction.");
  await ui.render();
  const form = find(ui.tree, (n) => n.props && n.props.onSubmit)[0];
  await form.props.onSubmit({ preventDefault() {} });
  await settle();
  await ui.render();
  assert.match(ui.notes(), /A newer version of this transcript was saved\. Your text is kept/);
  assert.equal(textareas(ui.tree)[0].props.value, "My correction.");
  assert.ok(ui.button("Load latest version"));
  assert.equal(ui.posts().length, 1);
});

test("Arabic: status and viewer wording are translated", async () => {
  const ui = mount("RecordingStatusList", { report, refreshKey: 0, lang: "ar" }, () => ({ items: [rec({ processing: { run_id: "r", state: "queued", attempt: 1 } })] }));
  ui.tree = null;
  const h = harness();
  const C = load(h);
  const api = async () => ({ items: [rec({ processing: { run_id: "r", state: "queued", attempt: 1 } })] });
  let tree = h.render(C.RecordingStatusList, { api, lang: "ar", report, refreshKey: 0 });
  await settle();
  tree = h.render(C.RecordingStatusList, { api, lang: "ar", report, refreshKey: 0 });
  assert.match(notices(tree).join(" "), /في انتظار التفريغ \(المحاولة 1\)/);
  assert.match(textOf(tree), /التسجيلات المقدَّمة/);
  assert.ok(ui);
});
