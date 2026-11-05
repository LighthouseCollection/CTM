# #97 slice 3 — case record (council-case.js)

Screens and CDN 0.86.0 templates:

| Screen | Before | After |
|---|---|---|
| Every case tab in council-case.js (summary, timeline, spouses, marriage, separation, calls, notes, petition, reports, hearings, assessments, decision, audit) | `Text h1` per tab, no case header | `RecordPage` + case `EntityHeader` (record-page.md), header style 1 Structured: case number, spouses, Status tile, case manager; the tab title is an h2 |
| Calls, notes, Professional Assessments | `Toolbar` with an add button | the count fact carries the add action (header style 2, `facts[].action`), only for the writer of an open case |
| Hearings | hand-built `plx-entity-header` markup | `EntityHeader kind="section"` with text actions in a column |
| Application review (case summary) | `Inline` of Accept / Decline | `ActionBar` (page-actions.md), Decline first, Accept primary last |
| Add a spouse | `Inline` button | embedded `ActionBar` |
| Closed case (summary, marriage, separation, notes, assessments, calls) | actions hidden only | `ReadOnly` region with its reason (read-only-state.md); actions still hidden |
| Notes, calls, assessments, audit | `CTMShell.Workspace` | unchanged split list/detail (`CTMShell.Workspace`, master-detail-workspace.md) inside the record page |

Permissions: the case header reads only `GET /api/cases/{id}/` (what the summary tab already shows). Tabs that did not load the case (audit, petition, hearings, reports) load it for the header and leave the header out if the read is refused. The assessment count appears only on the assessments tab, where the same rows are listed.

`ctm.css` selectors already unused before this slice (for slice 8): `.ctm-hearing-header`, `.ctm-hearing-attendance-*`, `.ctm-past-hearings-table*`. `ctm-decision-voting-workspace` is still set (pinned by a test) but has no CSS.

Screenshots (CTM 2.0 demo data, local port 8023): `before-*` and `after-*` in this folder. Arabic was switched on the page only (the settings POST was answered in the browser, nothing saved).
