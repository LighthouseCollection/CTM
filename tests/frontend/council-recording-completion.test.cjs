// C-05 (#3): council completes an external priest request from its own recording (backend fcf03a2).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { harness, load, find, byName, notices, buttons, dialogs, settle, textOf } = require("./harness.cjs");

const sent = { id: "req-5", kind: "external_priest", state: "sent", title: "Report by Fr. Synthetic Priest", request_version: "v-2" };
const record = { id: "case-1" };
const audio = (name = "talk.mp3", type = "audio/mpeg", size = 1000) => Object.assign(new File(["synthetic"], name, { type }), size > 1000 ? {} : {});

// A media element stub: reports the given duration (seconds), or fails, when its src is set.
function mediaWindow(duration) {
  return {
    FormData,
    URL: { createObjectURL: () => "blob:rec", revokeObjectURL() {} },
    setTimeout: (fn, ms) => (ms >= 8000 ? 0 : setTimeout(fn, ms)),
    clearTimeout() {},
    document: {
      createElement: () => {
        const el = {};
        Object.defineProperty(el, "src", { set() { setTimeout(() => (duration === "error" ? el.onerror() : ((el.duration = duration), el.onloadedmetadata())), 0); } });
        return el;
      },
    },
  };
}

function panel(request, routes, { lang = "en", duration = 61.4 } = {}) {
  const h = harness();
  const C = load(h, mediaWindow(duration));
  const calls = [];
  const recorded = [];
  const api = async (url, options = {}) => {
    const body = options.body instanceof FormData ? Object.fromEntries([...options.body.entries()].map(([k, v]) => [k, typeof v === "string" ? v : `file:${v.name}`]))
      : options.body ? JSON.parse(options.body) : undefined;
    calls.push({ url, method: options.method || "GET", body });
    const out = routes(url, body);
    if (out instanceof Error) throw out;
    return out;
  };
  const props = { api, lang, request, record, canWrite: true, onRecorded: (n) => recorded.push(n) };
  const ui = {
    C, calls, recorded,
    tree: h.render(C.RecordingCompletionPanel, props),
    rerender() { ui.tree = h.render(C.RecordingCompletionPanel, props); return ui.tree; },
    async click(label) { const b = buttons(ui.tree, label)[0]; assert.ok(b, `button "${label}"`); await b.props.onClick(); await settle(); await settle(); ui.rerender(); },
    async confirm() { const d = dialogs(ui.tree).find((x) => x.props.open); assert.ok(d, "confirmation"); await d.props.onConfirm(); await settle(); ui.rerender(); },
    choose(file) { byName(ui.tree, "FileInput")[0].props.onChange([file]); ui.rerender(); },
    date(value) { find(ui.tree, (n) => n.props && n.props.type === "date")[0].props.onChange({ target: { value } }); ui.rerender(); },
    tick(label) { const box = byName(ui.tree, "Checkbox").find((c) => c.props.label.includes(label)); assert.ok(box, label); box.props.onChange({ target: { checked: true } }); ui.rerender(); },
    text() { return textOf(ui.tree); },
  };
  return ui;
}

async function fill(ui) {
  await ui.click("Record a recorded response");
  ui.choose(audio());
  ui.date("2026-10-19");
  ui.tick("recording of the priest's report");
  ui.tick("told the conversation was being recorded");
}

test("recording: validation covers file type and size, date, and both declarations", () => {
  const C = load(harness(), mediaWindow(1));
  const today = "2026-10-24";
  const ok = { chosen: audio(), fileId: null, date: "2026-10-20", confirmed: true, informed: true };
  assert.equal(C.returnedProblem("recording", { ...ok, chosen: null }, today), "chooseRecording");
  assert.equal(C.returnedProblem("recording", { ...ok, chosen: new File(["x"], "notes.pdf", { type: "application/pdf" }) }, today), "audioOnly");
  assert.equal(C.returnedProblem("recording", { ...ok, chosen: { name: "a.wav", type: "audio/wav", size: 101 * 1024 * 1024 } }, today), "recTooLargeAudio");
  assert.equal(C.returnedProblem("recording", { ...ok, chosen: { name: "a.webm", type: "video/webm", size: 300 * 1024 * 1024 } }, today), null);
  assert.equal(C.returnedProblem("recording", { ...ok, chosen: { name: "a.mp4", type: "video/mp4", size: 501 * 1024 * 1024 } }, today), "recTooLargeVideo");
  assert.equal(C.returnedProblem("recording", { ...ok, date: "2026-10-25" }, today), "receivedFuture");
  assert.equal(C.returnedProblem("recording", { ...ok, confirmed: false }, today), "confirmRecording");
  assert.equal(C.returnedProblem("recording", { ...ok, informed: false }, today), "confirmInformed");
  assert.equal(C.returnedProblem("recording", ok, today), null);
});

test("recording: case-original upload (no request_id), check, declaration and measured duration sent on completion", async () => {
  let scan = "pending";
  const ui = panel(sent, (url) => {
    if (url === "/api/files/") return { id: "fv-r1", name: "talk.mp3", scan_state: "pending" };
    if (url === "/api/files/fv-r1/status/") return { id: "fv-r1", scan_state: scan };
    if (url === "/api/requests/req-5/recording-completion/") return { id: "rep-r", recording_id: "rc-1", method: "recording", completion_date: "2026-10-19" };
    throw new Error("unexpected " + url);
  });
  await fill(ui);
  await ui.click("Upload recording");
  assert.deepEqual(ui.calls[0], { url: "/api/files/", method: "POST", body: { file: "file:talk.mp3", category: "AUDIO", case_id: "case-1", visibility: "council" } });
  assert.ok(!("request_id" in ui.calls[0].body), "the backend requires a case original, not a request upload");
  assert.match(ui.text(), /1:01/, "measured length shown");
  assert.equal(buttons(ui.tree, "Record recorded response").length, 0);
  scan = "clean";
  await ui.click("Check again");
  await ui.click("Record recorded response");
  const dialog = dialogs(ui.tree).find((d) => d.props.open);
  assert.match(dialog.props.message, /declaration that the priest was informed/);
  assert.match(dialog.props.message, /queued for transcription/);
  await ui.confirm();
  assert.deepEqual(ui.calls[ui.calls.length - 1], { url: "/api/requests/req-5/recording-completion/", method: "POST",
    body: { file_id: "fv-r1", completion_date: "2026-10-19", recording_notice: { acknowledged: true }, duration_ms: 61400, expected_version: "v-2" } });
  assert.deepEqual(ui.recorded, ["recRecorded"]);
});

test("recording: when the browser cannot measure the length, duration is sent as null, never guessed", async () => {
  const ui = panel(sent, (url) => (url === "/api/files/" ? { id: "fv-r2", name: "talk.mp3", scan_state: "clean" } : { id: "rep" }), { duration: "error" });
  await fill(ui);
  await ui.click("Upload recording");
  assert.match(ui.text(), /Not measured by this browser/);
  await ui.click("Record recorded response");
  await ui.confirm();
  assert.equal(ui.calls[ui.calls.length - 1].body.duration_ms, null);
});

test("recording: without the 'priest was informed' declaration nothing is uploaded", async () => {
  const ui = panel(sent, () => ({}));
  await ui.click("Record a recorded response");
  ui.choose(audio());
  ui.date("2026-10-19");
  ui.tick("recording of the priest's report");
  await ui.click("Upload recording");
  assert.equal(ui.calls.length, 0);
  assert.match(notices(ui.tree).join(" "), /told about the recording/);
});

test("recording: a refused completion keeps the dialog open with the server's reason", async () => {
  const ui = panel(sent, (url) => (url === "/api/files/" ? { id: "fv-r3", name: "talk.mp3", scan_state: "clean" }
    : Object.assign(new Error("x"), { status: 422, data: { detail: "Use a validated current original not already associated with another recording." } })));
  await fill(ui);
  await ui.click("Upload recording");
  await ui.click("Record recorded response");
  await ui.confirm();
  const dialog = dialogs(ui.tree).find((d) => d.props.open);
  assert.ok(dialog);
  assert.match(textOf(dialog), /already associated with another recording/);
  assert.deepEqual(ui.recorded, []);
});

test("recording: hidden unless a writer has a sent priest request", () => {
  for (const [request, canWrite] of [[{ ...sent, state: "draft" }, true], [{ ...sent, state: "completed" }, true], [sent, false]]) {
    const h = harness();
    const C = load(h, mediaWindow(1));
    const tree = h.render(C.RecordingCompletionPanel, { api: async () => ({}), lang: "en", request, record, canWrite, onRecorded() {} });
    assert.equal(byName(tree, "Panel").length, 0);
  }
});

test("recording: Arabic wording", async () => {
  const ui = panel(sent, () => ({}), { lang: "ar" });
  assert.match(ui.text(), /الرد المسجَّل/);
  await ui.click("تسجيل رد مسجَّل");
  assert.ok(buttons(ui.tree, "رفع التسجيل")[0]);
  assert.ok(byName(ui.tree, "Checkbox").some((c) => /أُبلغ الكاهن/.test(c.props.label)));
});

// Completed reports viewer for a recorded response.
const recReport = { id: "rep-r", title: "Report by Fr. Synthetic Priest", kind: "external_priest", subject: "Synthetic Applicant", date: "2026-10-19",
  questions: [], answers: { files: ["fv-r1"] }, observations: null, version: 1, method: "recording", author: "Synthetic Secretary", author_id: "u-sec",
  submitted_at: "2026-10-24T07:00:00Z", can_revise: false };
function tabs(report, lang = "en") {
  const h = harness();
  const C = load(h, mediaWindow(1));
  return byName(h.render(C.ReportDetailTabs, { api: async () => ({ items: [] }), lang, user: { id: "u-sec", portal: "council", role: "secretary" }, report, record: {}, onOriginal() {}, onRevised() {} }), "Tabs")[0].props.items;
}

test("recorded report: player through the authorized route, recorder and date, no capture controls, transcripts tab enabled", () => {
  const items = tabs(recReport);
  const answers = items[0].content;
  const text = textOf(answers);
  assert.match(text, /Recording made by the council/);
  assert.match(text, /Recorded by/);
  assert.match(text, /Recorded on/);
  assert.doesNotMatch(text, /\["fv-r1"\]/);
  const player = byName(answers, "MediaPlayer")[0];
  assert.equal(player.props.src, "/api/files/fv-r1/");
  assert.match(text, /cannot be revised/);
  assert.equal(items[1].content.type.name, "RecordingStatusList", "recording list only; no capture recorder for a completed recorded response");
  assert.equal(byName(items[2].content, "EmptyState").length, 0, "transcripts tab is not 'not an interview'");
});
