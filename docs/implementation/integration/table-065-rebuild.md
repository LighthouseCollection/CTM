# CTM table rebuild — Plenix 0.65.0

The shared CTMShell.Table adapter renders the published native DataGrid for every collection, including read-only records. Every caller inherits compact density, native pill cells, resizing, sorting, column menus and wrapping headers. Screen-defined width constraints are preserved. Removed CSS overrides of table header type icons and hover reserves; the documented typeIcons option replaces the icon CSS patch.

Direct council table consumers use DataGrid, explicit compact density and pill cells. Case lists use actual pages mode with 25 records instead of setting pageSize on a fill grid. Person columns declare their type; custom agenda name pills use size md. Rich action cells remain React content, while shared scalar renderers produce md pills. Existing callbacks, labels, empty states, selection keys and split-view orientation are preserved. No API, schema or authorization changes.

Coverage: the shared adapter serves council sessions, hearings, reports, evidence, documents, notes, communications, decisions, appeals, audits, statistics and applicant table consumers wherever CTMShell.Table/Workspace is used. Direct DataTable usages were migrated; no legacy DataTable invocation remains under static/ctm.

Validation:
- Four behavior tests: read-only grid controls, interactive selection callback, custom cells/width preservation and bounded action columns.
- Real published CDN Chromium run: row click, keyboard Enter, zero values, 24px pills, compact 36px rows (37px including row divider), desktop and narrow RTL screenshots; no page errors.
- Shell/case/adapter suite: 62 passed, 3 failed outside table ownership (assignment authorization source assertion, summary request/decision fixture, spouse-card source assertion). This is not full council acceptance.
- Local sign-in page serves 0.65.0. No public deployment was performed.

Run: node --test tests/frontend/table-contract.test.cjs
Run: python scripts/browser_table_065.py

Screenshots are local ignored .tmp/table-065-en.png and .tmp/table-065-ar.png. These test native rendering using fictional rows; authenticated per-screen, real-backend acceptance remains separate.


## Corrective verification after owner feedback

The first rebuild incorrectly disabled resizing/sorting for callers marked isStatic, chose a non-resizable reference Table, and discarded documented width constraints. These mistakes are corrected: every shared collection uses native DataGrid with resizing, sorting, column menus and wrapHeaders enabled. Screen-defined width/minWidth/maxWidth survive. Action/status columns have a documented 240px size-token maximum to avoid absorbing an entire pane. Actions remain visible and are not sortable/groupable.

Actual authenticated localhost verification: Upcoming Session date column resized 152 -> 160 using ArrowRight and -> 220 using mouse drag. Current Session agenda exposes all 12 resize handles across its two grids. Case Reason for divorce header changed from124 to184 with native menu reserve enabled, and its text width remained107.97px before/after pointer hover (scrollWidth108), with full heading visible. No local CDN CSS override added.
