# Defect report: Plenix 0.58.0 DocumentViewer cannot load PDF.js from the CDN

Status: **open, upstream (Plenix design system)**. CTM has made no workaround. Embedded PDF viewing in CTM is **not complete**. Council PDFs keep opening through the authorized browser-view fallback (`/api/files/{id}/?view=1`).

Investigated 2026-10-22 on branch `work/claude-council` (draft PR #6). This was a diagnosis only: no CDN files were changed and no PDF.js was added to CTM.

## 1. Pinned version and documented usage

- CDN: `https://design-system.lighthouseway.org/cdn/0.58.0/`, loaded by CTM `shell.html` as `plenix.js` (sha256 `eb1d0f2f…b471f`, 3,535,637 bytes per `bundle-manifest.json`).
- Documented usage (`docs/document-viewer.md` and the component header): `<DocumentViewer kind="pdf" src="/files/report.pdf" label="Report"/>`. The optional props are `pdfModuleUrl`/`pdfWorkerUrl` "when serving the vendor files separately".
- Component header note: "PDF.js 4.10.38 (Apache-2.0) is vendored beside this component … No remote PDF code is downloaded."

## 2. Expected versus actual

The loader code in `plenix.js` 0.58.0 (identical in 0.59.0):

```js
function vendorUrl(name) {
  const script = Array.from(document.scripts).find(s => /\/platform\/(?:dist\/)?platform(?:\.min)?\.js(?:[?#]|$)/.test(s.src));
  return new URL(script ? (script.src.includes('/dist/') ? '../components/' : 'components/') + 'DocumentViewer/vendor/' + name
                        : '../components/DocumentViewer/vendor/' + name, script ? script.src : document.baseURI).href;
}
// in DocumentViewer:
const moduleUrl = pdfModuleUrl || vendorUrl('pdf.js');
engine.GlobalWorkerOptions.workerSrc = pdfWorkerUrl || new URL('pdf.worker.js', moduleUrl).href;
```

| | URL | Result (verified) |
|---|---|---|
| Expected module (beside the component, CDN) | `…/cdn/0.58.0/components/DocumentViewer/vendor/pdf.js` | **404** |
| Expected worker | `…/cdn/0.58.0/components/DocumentViewer/vendor/pdf.worker.js` | **404** |
| Other candidates (`vendor/pdf.js`, `vendor/pdf.worker.js`, `.mjs` variants, `DocumentViewer/vendor/pdf.js`) | `…/cdn/0.58.0/…` | all **404** |
| Same paths in 0.59.0 | `…/cdn/0.59.0/…` | **404** |
| Actual request with documented default usage | `<app origin>/components/DocumentViewer/vendor/pdf.js` | Requested from the **application's own server**, not the CDN (404 in the reproduction) |
| Published bundle `plenix-0.58.0.tgz` (26 files, sha256 `544c4135…a20d8` matches `index.json`) | | Contains `vendor/tabulator/*`, `vendor/tiptap/*`, React, fonts. **No PDF.js and no PDF.js license notice.** |

UI result in both default and explicit-CDN cases: "The document could not be opened." with Try again (which repeats the same failing import). The page counter reads "Page 1 / 0".

### Minimal reproduction

Serve this page from any local origin together with any PDF at `/sample.pdf`:

```html
<link rel="stylesheet" href="https://design-system.lighthouseway.org/cdn/0.58.0/plenix.css">
<script defer src="https://design-system.lighthouseway.org/cdn/0.58.0/vendor/react.production.min.js"></script>
<script defer src="https://design-system.lighthouseway.org/cdn/0.58.0/vendor/react-dom.production.min.js"></script>
<script defer src="https://design-system.lighthouseway.org/cdn/0.58.0/plenix.js"></script>
<div id="root"></div>
<script>
addEventListener("DOMContentLoaded", () =>
  ReactDOM.createRoot(document.getElementById("root"))
    .render(React.createElement(Plenix.DocumentViewer, { kind: "pdf", src: "/sample.pdf", label: "Sample" })));
</script>
```

Observed in Chromium (built-in browser):

| Case | Requests | Outcome |
|---|---|---|
| A. Documented default (no URL props) | `GET <page origin>/components/DocumentViewer/vendor/pdf.js` | Failure state |
| B. `pdfModuleUrl` = CDN `components/DocumentViewer/vendor/pdf.js` | CDN 404 | Failure state |
| C. Control: unmodified CDN `plenix.js`, with `pdfModuleUrl`/`pdfWorkerUrl` pointing to a **second origin** serving upstream `pdfjs-dist@4.10.38` `build/pdf.mjs` and `build/pdf.worker.mjs` as `pdf.js`/`pdf.worker.js` (`text/javascript`, `Access-Control-Allow-Origin: *`) | module 200, worker 200, PDF 200 | **Renders**: "Page 1 / 2", thumbnails, page text exposed |
| D. Same as C, `pdfModuleUrl` only (worker derived) | module and derived `pdf.worker.js` 200 | **Renders** |
| E. As C, but `src` returns 404 | module and worker 200, PDF 404 | Same generic "could not be opened" as A/B |

The control (C/D) used upstream PDF.js only in a temporary diagnostic folder. It is not part of CTM.

## 3. Classification

Verified facts:
1. **Missing published assets.** PDF.js 4.10.38 module and worker are not on the 0.58.0 (or 0.59.0) CDN and not in the published bundle or its manifest, although the component says they are "vendored beside this component".
2. **Incorrect asset-base resolution.** `vendorUrl()` recognizes only the repository layout (`/platform/platform.js` or `/platform/dist/platform.js`). On the CDN the script is `plenix.js`, so it falls back to `document.baseURI` and requests code from the **consuming application's origin**. This contradicts "No remote PDF code is downloaded" in the sense that matters: the module comes from whatever the host app serves at that path. The Tabulator/Tiptap loader in the same file (`vendorBase()`) already recognizes `plenix(.global)(.min).js`, honors `window.PlenixVendorBase` and has a versioned npm fallback. DocumentViewer does not use it.
3. **Component logic is sound when assets exist.** Cross-origin module and worker load and render (C/D, Chromium).
4. **CTM integration is not the cause.** CTM never renders `kind="pdf"` without explicit URLs. It passes the documented `pdfModuleUrl`/`pdfWorkerUrl` only when `window.CTM_PDF_VIEWER` is configured (it is not), and otherwise shows the authorized browser-view fallback. No CTM usage correction is needed.

Hypothesis (not verified, no access to the Plenix repository): the CDN/bundle build copies the top-level `vendor/` folder but not `components/DocumentViewer/vendor/`. When the Tabulator/Tiptap loader was updated for the CDN layout, DocumentViewer's separate `vendorUrl()` was not.

Additional gap (verified, design-system API): DocumentViewer reports every failure with one message ("The document could not be opened.") and has no error callback or reason. A refused or revoked document (403/404/410) cannot be told apart from a missing engine or a corrupt file. The failure state also shows "Page 1 / 0".

## 4. Recommended upstream fix

1. Publish PDF.js **4.10.38** `pdf.js` (module, from `build/pdf.mjs` or `.min.mjs`) and `pdf.worker.js` (from the same release) at `cdn/<version>/components/DocumentViewer/vendor/`, or at `cdn/<version>/vendor/pdfjs/`, matching whatever the loader resolves. Serve them with a JavaScript MIME type and `Access-Control-Allow-Origin: *` like the other CDN files. Include the Apache-2.0 `LICENSE` and a provenance README (upstream version, source tarball and integrity) as is done for Tabulator and Tiptap. Add both files to the bundle and `bundle-manifest.json` with hashes.
2. Resolve the default path from the Plenix script itself, reusing `platformScript()`/`vendorBase()` (recognize `plenix.js`, honor `window.PlenixVendorBase`, versioned npm fallback). Never fall back to `document.baseURI`, which loads code from the host application.
3. Keep module and worker on one PDF.js version. Derive the worker beside the module (as now) and document that `pdfModuleUrl`/`pdfWorkerUrl` must be the same release (PDF.js rejects a mismatched worker).
4. Documentation: state the exact CDN URLs of the module and worker, the CSP needed (`script-src` for the CDN origin, and `worker-src` for the CDN origin plus `blob:` if PDF.js wraps a cross-origin worker), and that `src` is fetched with the page's credentials (same-origin cookies) and range requests.
5. Recommended API addition: `onError(reason)` (or a `reason` in the failure state) distinguishing engine load failure from document HTTP status (401/403/404/410) and parse/render failure, plus the ability to replace the failure message per reason. Hide the page counter in the failure state.

### Acceptance checks for the corrected release

- On the CDN, `components/DocumentViewer/vendor/pdf.js` and `pdf.worker.js` (or the documented location) return 200 with a JS MIME type and CORS, and both report `pdfjsVersion = "4.10.38"`.
- The minimal reproduction above, unchanged except for the version, renders a two-page PDF with **no** request to the page's own origin other than `src`.
- The bundle `.tgz` and `bundle-manifest.json` list the PDF.js files and license, with matching hashes.
- `vendorUrl` resolves correctly for the CDN `plenix.js`, the npm global build and the repository layout. `window.PlenixVendorBase` overrides it.
- Test in Chromium, Firefox and Safari (desktop and iOS), including a strict CSP page.
- A 403/404 `src` produces a distinguishable reason (if the API addition is accepted).

## 5. CTM changes still required after the corrected release

- Bump the pinned CDN version in `shell.html` (all Plenix tags together; coordinated with governance as a precise shell patch).
- In `council-media.js` `FilePreview`: render `DocumentViewer kind="pdf"` with `src` = the authorized `/api/files/{id}/?view=1` route and the CDN's default vendor resolution. Remove the `window.CTM_PDF_VIEWER` gate (or keep it only as an override), and keep the "Open in browser" authorized fallback link visible.
- Denied/revoked access: until the design system exposes a reason, CTM can only show the generic failure plus the fallback link, which then shows the server's own refusal. Revocation stops future loads only. A PDF that was already rendered or downloaded cannot be erased remotely.
- Arabic: pass translated `strings` (already done for images). Verify in RTL.
- Actual-backend acceptance in an isolated setup: permitted PDF renders through the authorized route with range requests, and denied, revoked and missing files are handled.

## Status by area

| Area | State |
|---|---|
| Workflow / Schema / Database | Not applicable (front-end asset dependency) |
| Coded | Defect report only. CTM PDF code unchanged; browser-view fallback in place. |
| Working | Embedded PDF viewing **not working** on the pinned CDN. Fallback works (fixture-verified earlier). |
| UI | No change |
| Testing-QA | Reproduction in Chromium against the live 0.58.0 CDN plus a local diagnostic control. Firefox/Safari and actual-backend PDF rendering not tested, since there is nothing to accept until the CDN is fixed. |
