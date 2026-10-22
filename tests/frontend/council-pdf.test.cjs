// C-04 (#3): embedded PDF viewer on Plenix 0.60.1's documented DocumentViewer API, protected route, EN/AR failures,
// browser fallback kept, nothing cached in persistent browser storage.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, byName, textOf, buttons } = require("./harness.cjs");

const file = { id: "f-pdf", name: "20261001-01-MC-20261001-0900.pdf", mime_type: "application/pdf", category: "MC", version: 1,
  download_url: "/api/files/f-pdf/", preview_url: "/api/files/f-pdf/?view=1" };

function preview(lang = "en", extra = {}) {
  const h = harness();
  const C = load(h, extra);
  const props = { file, lang, images: [], onFullScreen() {} };
  return { h, C, props, tree: h.render(C.FilePreview, props) };
}

test("PDF renders in the documented DocumentViewer from the protected inline route, no extra configuration needed", () => {
  const { tree } = preview();
  const viewer = byName(tree, "DocumentViewer")[0];
  assert.ok(viewer, "embedded viewer shown");
  assert.equal(viewer.props.kind, "pdf");
  assert.equal(viewer.props.src, "/api/files/f-pdf/?view=1");
  assert.equal("pdfModuleUrl" in viewer.props, false, "PDF.js comes from the CDN vendor folder by default");
  assert.equal(typeof viewer.props.onError, "function");
});

test("reason-specific EN/AR failure strings; the catch-all 'failed' is not passed (it would replace all four)", () => {
  for (const lang of ["en", "ar"]) {
    const strings = byName(preview(lang).tree, "DocumentViewer")[0].props.strings;
    for (const key of ["failedEngine", "failedAccess", "failedParse", "failedRender", "loading", "retry"]) assert.ok(strings[key] && strings[key] !== key, `${lang} ${key}`);
    assert.equal("failed" in strings, false);
  }
  const ar = byName(preview("ar").tree, "DocumentViewer")[0].props.strings;
  assert.match(ar.failedAccess, /سُحب حق اطلاعك/);
});

test("open-in-browser fallback stays available on the same protected route", () => {
  const { tree } = preview();
  const open = buttons(tree, "Open in browser")[0];
  assert.equal(open.props.href, "/api/files/f-pdf/?view=1");
  assert.equal(open.props.target, "_blank");
  assert.equal(open.props.rel, "noopener noreferrer");
  assert.ok(buttons(tree, "Download")[0]);
});

test("viewer failures add the right hint: access mentions withdrawal; others point to the browser viewer", () => {
  const { h, C, props } = preview();
  let tree = h.render(C.FilePreview, props);
  byName(tree, "DocumentViewer")[0].props.onError({ reason: "access", cause: new Error("403") });
  tree = h.render(C.FilePreview, props);
  assert.match(textOf(tree), /refused too if access was withdrawn/);
  const other = preview();
  let t2 = other.h.render(other.C.FilePreview, other.props);
  byName(t2, "DocumentViewer")[0].props.onError({ reason: "engine" });
  t2 = other.h.render(other.C.FilePreview, other.props);
  assert.match(textOf(t2), /browser's own PDF viewer uses the same protected link/);
});

test("an explicit CTM_PDF_VIEWER override is still honoured", () => {
  const { tree } = preview("en", { CTM_PDF_VIEWER: { moduleUrl: "/x/pdf.js", workerUrl: "/x/pdf.worker.js" } });
  const viewer = byName(tree, "DocumentViewer")[0];
  assert.equal(viewer.props.pdfModuleUrl, "/x/pdf.js");
  assert.equal(viewer.props.pdfWorkerUrl, "/x/pdf.worker.js");
});

test("a forged storage URL is never used as the document source", () => {
  const h = harness();
  const C = load(h);
  const tree = h.render(C.FilePreview, { file: { ...file, preview_url: "https://storage.example/originals/x.pdf", download_url: "https://storage.example/x" }, lang: "en", images: [], onFullScreen() {} });
  const viewer = byName(tree, "DocumentViewer");
  assert.equal(viewer.length, 0, "no embedded viewer without an authorized inline route");
});

test("no persistent browser storage or cache APIs in council code", () => {
  for (const f of ["council.js", "council-case.js", "council-decree.js", "council-media.js"]) {
    const src = fs.readFileSync(`static/ctm/${f}`, "utf8");
    assert.doesNotMatch(src, /localStorage|sessionStorage|caches\.open|CacheStorage/, f);
  }
});
