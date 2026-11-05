# #97 slice 7 — documents, reports, decree, appeals (council-media.js, council-decree.js)

| Screen | Before | After (CDN 0.86.0 doc) |
|---|---|---|
| Documents / evidence (`CaseFilesWorkspace`) | `Text h1` + `SplitView`(`CTMShell.Table`, `ReadingPane`); demo download a hand-built `<a class="plx-button">`, demo picture a raw `<img class="ctm-demo-file-preview">` | `RecordPage.Header` + `SplitView`(`FileList`, `ReadingPane`) (record-page.md, file-list.md); demo download `P.Button href download`, demo picture `DocumentViewer kind="images"` |
| Completed reports (`ReportsReader`) | hand-built `SplitView` + `CTMShell.Table` + `ReadingPane` | `CTMShell.Workspace` (master-detail-workspace.md) |
| Decree (`DecreeWorkspace`, `DecreePreparation`, `DecreeProtocolGuide`) | `Text h1`, approved decision panel above the body, step buttons in `Inline` | `RecordPage` (record-page.md): header with the decree ID badge, approved decision as the aside; step buttons in embedded `ActionBar`s (page-actions.md) |
| Decree draft (`DecreeTemplateDraft`) | English-only decree text written in the browser (preamble, canonical basis, statement) | only the approved decision's own type, grounds and conditions from the server, with the existing honest `templateNotice` (generation from approved templates not available yet). Template wording belongs to the later decree design (CTM-case-session-workflow.md). |
| Appeals (`AppealsWorkspace`) | `Text h1` + hand-built `SplitView` + `CTMShell.Table` + `ReadingPane` | `RecordPage.Header` (title + scope) + `CTMShell.Workspace`; columns appellant, status, submitted |

Why not `CTMShell.Workspace` for files: it only draws a DataGrid, so the files page draws the same `SplitView` + `ReadingPane` around the `FileList`.
Why not `FormFlow` for decree steps: PLX-018 (it replaces server failure messages with `strings.failed`) and PLX-020 (it always draws Cancel).

No behavior, data or permission change; every honest unavailable state kept (scan waiting, signature record, `readMissing`, `unknownIssued`, `supplementsPending`, `hearingsUnavailable`). Nothing was saved.

Screenshots (CTM 2.0 demo data, local port 8027, desktop only per owner instruction 2026-11-05): `before-*` / `after-*`: decree 20261020-06 (needs approval), -07 (issued, secretary and president), -08; appeals -08 (secretary and president); documents and evidence -06; reports -07. No console errors. The decree preparation steps (store PDF, safety check, signature, issue) have no demo case in that state and were not seen in the browser.
