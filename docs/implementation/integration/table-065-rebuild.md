# CTM table rebuild — Plenix 0.65.0

The shared CTMShell.Table adapter now renders the published native Table for reference information, and DataGrid for selectable record workspaces. Every existing caller inherits compact density, native pill cells and CDN content-sized columns. Removed application column-width guesses and CSS overrides of table header type icons and hover reserves. The documented typeIcons option replaces the icon CSS patch.

Direct council table consumers use DataGrid, explicit compact density and pill cells. Case lists use actual pages mode with 25 records instead of setting pageSize on a fill grid. Person columns declare their type; custom agenda name pills use size md. Rich action cells remain React content, while shared scalar renderers produce md pills. Existing callbacks, labels, empty states, selection keys and split-view orientation are preserved. No API, schema or authorization changes.

Coverage: the shared adapter serves council sessions, hearings, reports, evidence, documents, notes, communications, decisions, appeals, audits, statistics and applicant table consumers wherever CTMShell.Table/Workspace is used. Direct DataTable usages were migrated; no legacy DataTable invocation remains under static/ctm.

Validation:
- Three behavior tests: reference data, interactive selection callback, custom cells and automatic widths.
- Real published CDN Chromium run: row click, keyboard Enter, zero values, 24px pills, compact 36px rows (37px including row divider), desktop and narrow RTL screenshots; no page errors.
- Shell/case/adapter suite: 62 passed, 3 failed outside table ownership (assignment authorization source assertion, summary request/decision fixture, spouse-card source assertion). This is not full council acceptance.
- Local sign-in page serves 0.65.0. No public deployment was performed.

Run: node --test tests/frontend/table-contract.test.cjs
Run: python scripts/browser_table_065.py

Screenshots are local ignored .tmp/table-065-en.png and .tmp/table-065-ar.png. These test native rendering using fictional rows; authenticated per-screen, real-backend acceptance remains separate.
