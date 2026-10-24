// C-05 (#3): council records an external priest's paper response (backend 746e5a4).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, find, byName, notices, buttons, dialogs, settle, textOf } = require("./harness.cjs");

const sent = { id: "req-9", kind: "external_priest", state: "sent", title: "Report by Fr. Synthetic Priest", request_version: "v-7" };
const pdf = () => new File(["%PDF-1.4 synthetic"], "paper.pdf", { type: "application/pdf" });

function panel(request, routes, { lang = "en", canWrite = true, h: given } = {}) {
  const h = given || harness();
  const C = load(h, { FormData });
  const calls = [];
  const recorded = [];
  const api = async (url, options = {}) => {
    const body = options.body instanceof FormData ? Object.fromEntries([...options.body.entries()].map(([k, v]) => [k, typeof v === "string" ? v : `file:${v.name}`]))
      : options.body ? JSON.parse(options.body) : undefined;
    calls.push({ url, method: options.method || "GET", body });
    const out = routes(url, body);
    if (out instanceof Error || (out && out.status >= 400)) throw out;
    return out;
  };
  const props = { api, lang, request, canWrite, onRecorded: (n) => recorded.push(n) };
  const ui = {
    C, h, calls, recorded,
    tree: h.render(C.PaperCompletionPanel, props),
    rerender() { ui.tree = h.render(C.PaperCompletionPanel, props); return ui.tree; },
    async click(label) { const b = buttons(ui.tree, label)[0]; assert.ok(b, `button "${label}"`); await b.props.onClick(); await settle(); ui.rerender(); },
    async confirm() { const d = dialogs(ui.tree).find((x) => x.props.open); assert.ok(d, "confirmation"); await d.props.onConfirm(); await settle(); ui.rerender(); },
    choose(file) { byName(ui.tree, "FileInput")[0].props.onChange([file]); ui.rerender(); },
    date(value) { find(ui.tree, (n) => n.props && n.props.type === "date")[0].props.onChange({ target: { value } }); ui.rerender(); },
    tick() { byName(ui.tree, "Checkbox")[0].props.onChange({ target: { checked: true } }); ui.rerender(); },
    text() { return textOf(ui.tree); },
  };
  return ui;
}

const fail = (status, detail) => Object.assign(new Error(detail), { status, data: { detail } });

test("paper: validation needs a PDF, a received date not after today, and confirmation", () => {
  const C = load(harness());
  const today = "2026-10-24";
  const base = { chosen: pdf(), fileId: null, date: "2026-10-20", confirmed: true };
  assert.equal(C.paperProblem({ ...base, chosen: null }, today), "chooseFile");
  assert.equal(C.paperProblem({ ...base, chosen: new File(["x"], "paper.docx", { type: "application/msword" }) }, today), "pdfOnly");
  assert.equal(C.paperProblem({ ...base, chosen: { name: "big.pdf", type: "application/pdf", size: 26 * 1024 * 1024 } }, today), "paperTooLarge");
  assert.equal(C.paperProblem({ ...base, date: "" }, today), "receivedRequired");
  assert.equal(C.paperProblem({ ...base, date: "2026-10-25" }, today), "receivedFuture");
  assert.equal(C.paperProblem({ ...base, confirmed: false }, today), "confirmPaper");
  assert.equal(C.paperProblem(base, today), null);
  assert.equal(C.paperProblem({ ...base, chosen: null, fileId: "f-1" }, today), null, "an uploaded file needs no new choice");
});

test("paper: offered only to a writer on a sent priest request the server still allows", () => {
  const C = load(harness());
  assert.equal(C.paperAllowed(sent, true), true);
  assert.equal(C.paperAllowed(sent, false), false);
  assert.equal(C.paperAllowed({ ...sent, state: "draft" }, true), false, "the backend requires a sent request");
  assert.equal(C.paperAllowed({ ...sent, state: "completed" }, true), false);
  assert.equal(C.paperAllowed({ ...sent, kind: "interview" }, true), false);
  assert.equal(C.paperAllowed({ ...sent, external_link: { state: "active", can_cancel: true } }, true), true);
  assert.equal(C.paperAllowed({ ...sent, external_link: { state: "closed", can_cancel: false } }, true), false);
  const ui = panel({ ...sent, state: "draft" }, () => ({}));
  assert.equal(byName(ui.tree, "Panel").length, 0, "nothing rendered");
});

test("paper: upload bound to the request, wait for the check, confirm, then record with date and version", async () => {
  let scan = "pending";
  const ui = panel(sent, (url) => {
    if (url === "/api/files/") return { id: "fv-1", name: "paper.pdf", scan_state: "pending" };
    if (url === "/api/files/fv-1/status/") return { id: "fv-1", scan_state: scan };
    if (url === "/api/requests/req-9/paper-completion/") return { id: "rep-1" };
    throw new Error("unexpected " + url);
  });
  await ui.click("Record a paper response");
  ui.choose(pdf());
  ui.date("2026-10-20");
  await ui.click("Upload paper original");
  assert.equal(ui.calls.length, 0, "confirmation is required before uploading");
  assert.match(notices(ui.tree).join(" "), /Confirm that the PDF/);
  ui.tick();
  await ui.click("Upload paper original");
  assert.deepEqual(ui.calls[0], { url: "/api/files/", method: "POST", body: { file: "file:paper.pdf", category: "REPORT", request_id: "req-9", visibility: "council" } });
  assert.match(notices(ui.tree).join(" "), /being checked/);
  assert.equal(buttons(ui.tree, "Record paper response").length, 0, "no recording while the check is pending");
  await ui.click("Check again");
  assert.match(ui.text(), /still being checked/);
  scan = "clean";
  await ui.click("Check again");
  await ui.click("Record paper response");
  const dialog = dialogs(ui.tree).find((d) => d.props.open);
  assert.match(dialog.props.message, /private link will stop working/);
  assert.match(dialog.props.message, /cannot be replaced/);
  await ui.confirm();
  const last = ui.calls[ui.calls.length - 1];
  assert.deepEqual(last, { url: "/api/requests/req-9/paper-completion/", method: "POST", body: { file_id: "fv-1", completion_date: "2026-10-20", expected_version: "v-7" } });
  assert.deepEqual(ui.recorded, ["paperRecorded"]);
});

test("paper: a rejected file cannot be recorded; the council chooses another", async () => {
  const ui = panel(sent, (url) => (url === "/api/files/" ? { id: "fv-2", name: "paper.pdf", scan_state: "rejected" } : {}));
  await ui.click("Record a paper response");
  ui.choose(pdf());
  ui.date("2026-10-20");
  ui.tick();
  await ui.click("Upload paper original");
  assert.match(notices(ui.tree).join(" "), /failed the check/);
  assert.equal(buttons(ui.tree, "Record paper response").length, 0);
  await ui.click("Use a different file");
  assert.equal(byName(ui.tree, "FileInput").length, 1, "file choice is offered again");
  assert.ok(!ui.calls.some((c) => c.url.endsWith("/paper-completion/")));
});

test("paper: an upload without a file id is not treated as uploaded", async () => {
  const ui = panel(sent, () => ({ name: "paper.pdf" }));
  await ui.click("Record a paper response");
  ui.choose(pdf());
  ui.date("2026-10-20");
  ui.tick();
  await ui.click("Upload paper original");
  assert.match(notices(ui.tree).join(" "), /did not confirm the upload/);
  assert.equal(byName(ui.tree, "FileInput").length, 1);
});

test("paper: a refused completion (stale version) keeps the dialog open with the server's reason", async () => {
  const ui = panel(sent, (url) => {
    if (url === "/api/files/") return { id: "fv-3", name: "paper.pdf", scan_state: "clean" };
    return fail(409, "Reload the latest request before recording.");
  });
  await ui.click("Record a paper response");
  ui.choose(pdf());
  ui.date("2026-10-20");
  ui.tick();
  await ui.click("Upload paper original");
  await ui.click("Record paper response");
  await ui.confirm();
  const dialog = dialogs(ui.tree).find((d) => d.props.open);
  assert.ok(dialog, "still open");
  assert.match(textOf(dialog), /Reload the latest request/);
  assert.deepEqual(ui.recorded, []);
});

test("paper: an uploaded file awaiting its check survives in-app navigation (page memory only)", async () => {
  const h = harness();
  const ui = panel(sent, () => ({ id: "fv-4", name: "paper.pdf", scan_state: "pending" }), { h });
  await ui.click("Record a paper response");
  ui.choose(pdf());
  ui.date("2026-10-21");
  ui.tick();
  await ui.click("Upload paper original");
  // Same module instance (same page), new component instance: the upload is remembered.
  const again = h.render(ui.C.PaperCompletionPanel, { api: async () => ({}), lang: "en", request: sent, canWrite: true, onRecorded() {} });
  assert.ok(buttons(again, "Check again")[0]);
  assert.match(textOf(again), /paper\.pdf/);
  const src = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const panelSrc = src.slice(src.indexOf("const paperUploads"), src.indexOf("function RequestDetail("));
  assert.doesNotMatch(panelSrc, /localStorage|sessionStorage|indexedDB/);
});

test("paper: Arabic wording", async () => {
  const ui = panel(sent, () => ({}), { lang: "ar" });
  assert.match(ui.text(), /الرد الورقي/);
  await ui.click("تسجيل رد ورقي");
  assert.ok(buttons(ui.tree, "رفع الأصل الورقي")[0]);
});

// Completed reports: a paper report shows its retained original through the protected file route.
const paperReport = { id: "rep-p", title: "Report by Fr. Synthetic Priest", kind: "external_priest", subject: "Synthetic Applicant", date: "2026-10-20",
  questions: [], answers: { files: ["fv-1"] }, observations: null, version: 1, method: "paper", author: "Synthetic Secretary", author_id: "u-sec",
  submitted_at: "2026-10-24T07:00:00Z", can_revise: false };

function viewer(report, lang = "en") {
  const h = harness();
  const C = load(h, { FormData });
  const tabs = h.render(C.ReportDetailTabs, { api: async () => ({ items: [] }), lang, user: { id: "u-sec", portal: "council", role: "secretary" }, report, record: {}, onOriginal() {}, onRevised() {} });
  return byName(tabs, "Tabs")[0].props.items[0].content; // the answers tab
}

test("paper report: method, recorder and received date; the original opens in the PDF viewer, not as raw ids", () => {
  const tree = viewer(paperReport);
  const text = textOf(tree);
  assert.match(text, /Paper original recorded by the council/);
  assert.match(text, /Recorded by/);
  assert.match(text, /2026-10-20/);
  assert.doesNotMatch(text, /\["fv-1"\]/);
  const doc = byName(tree, "DocumentViewer")[0];
  assert.equal(doc.props.kind, "pdf");
  assert.equal(doc.props.src, "/api/files/fv-1/?view=1");
  assert.ok(find(tree, (n) => n.props && n.props.href === "/api/files/fv-1/").length >= 1, "authorized download");
  assert.match(text, /cannot be revised/);
  assert.doesNotMatch(text, /original council author/);
});

test("paper report: Arabic labels", () => {
  const text = textOf(viewer(paperReport, "ar"));
  assert.match(text, /أصل ورقي سجّله المجلس/);
  assert.match(text, /الأصل الورقي/);
});

test("non-paper reports keep their existing author label", () => {
  const text = textOf(viewer({ ...paperReport, method: "external", author: null, answers: { testimony: "Synthetic testimony." } }));
  assert.doesNotMatch(text, /Recorded by/);
  assert.match(text, /Written testimony/);
});

test("recording a paper response refreshes Completed reports from the server (wiring; browser-checked)", () => {
  const src = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.ok(src.includes('if (["paperRecorded", "recRecorded", "interviewRecorded"].includes(key)) onCompleted?.();'));
  assert.ok(src.includes("h(base.ReportsReader, { api, lang, user, caseId, reports, refreshKey: completedKey })"));
  const media = fs.readFileSync("static/ctm/council-media.js", "utf8");
  assert.ok(media.includes("if (refreshKey) reloadReports();"));
});
