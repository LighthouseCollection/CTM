# CTM council navigation — locked structure

User confirmed: 2026-10-20. Information architecture locked; no production UI built. All components/layouts must follow the [pinned Plenix CDN contract](CTM-Plenix-CDN-contract.md). Exact shell/footer support is not yet verified against accessible CDN documentation; do not invent it if absent.

## Main workspace navigation

Home; Tribunal Sessions; Cases; Search; Archived; Statistics and Reports. Case lists live in the workspace, never inside a navigation tree. Opening a case switches navigation scope to its case workspace, with Back to Cases preserving list context.

## Case workspace navigation

- Back to Cases
- Case Overview
  - Summary
  - Timeline
  - Parties
  - Marriage
  - Separation
- Communications (single destination, immediately after Case Overview)
- Case Review
  - Petition
  - Reports
  - Hearings
  - Evidence
  - Documents
  - Professional Assessments
- Decision
  - Decision & Voting
  - Decree
  - Appeals
- Case Audit

Appeals lists separate appeal statuses and references its reports/hearings in their existing sections, rather than duplicating them. Professional Assessments is the medical/psychological section. Decree controls remain restricted to the authorized admin/secretary and president functions; case workers do not manage decrees. Read access and action permissions remain server-enforced.

## Account/system access

One avatar/name button in a persistent sidebar footer, outside the scrolling navigation region, when supported by the documented Plenix shell pattern. It is available in main and case workspaces. It opens My Profile, Account Settings, CTM Settings (authorized users), System Audit (admin/secretary), Sign Out. Do not permanently show those five entries or duplicate the trigger in the header. If documented Plenix support is missing, report that gap; do not implement a custom exception. Only temporary Arabic styling has its separately approved exception.

## Split-view mapping

Split view means a list/selector and the selected item's detail in the main content workspace, independent of the application sidebar. In Arabic it follows the documented RTL pattern. On narrow screens use the documented Plenix responsive list/detail behavior; do not invent fixed dimensions or a new layout component.

| Page | List / selector | Selected detail | Status |
|---|---|---|---|
| Case Reports | Completed reports with search/type/person filters | Report/answers, recording, transcripts/translations, attachments, edit history | Explicitly agreed. Requests remain a separate list/view, not mixed into completed reports. |
| Case Communications | Private correspondence threads/items | Selected conversation, recipients and response/compose area | Recommended earlier, included in current mapping; exact Plenix layout to verify. |
| Case Documents | Categories/files/current versions | Authorized document preview, metadata and council history | Recommended and supported by source prototype's explorer structure, not evidence of a finished PDF viewer. |
| Case Evidence | Evidence items by type/person | Authorized image/video/audio/PDF viewer and description | Recommended to reuse the same list/detail pattern; no new approval asserted. |
| Professional Assessments | Completed medical/psychological reports, separate from requests | Authorized original, OCR text, disclosure release and history | Recommended in existing medical workflow specification; confidentiality/release scope unchanged. |
| Appeals | Appeal entries/statuses | Statement, additions, fee/result and links to related reports/hearings | Confirmed by user; split view selected. |
| Search | Authorized results and filters | Selected-result preview | Confirmed by user; split view selected, inside the main workspace. |

Do not impose split view on every page. Summary is an overview, Timeline chronological, Parties/Marriage/Separation/Petition structured content, Decision & Voting an action workspace, Decree a document/action workspace, Case Audit a searchable event list. Hearings may use a list opening a detail page; its split-view status is not decided. Global Cases remains a list/table opening the case workspace, not a tree or an automatic split-view requirement. Statistics and Reports is global statistical reporting, not the individual case Reports screen.


## Council Home review — 2026-10-21

[Council Home dashboard](CTM-council-home-dashboard.md) records approved assigned-work/attention/session/request sections and a source-based review of the existing prototype dashboard, including recommended retention of session/submission content and relocation of large analytics to Statistics and Reports. Exact layouts remain subject to the pinned Plenix contract; no production dashboard was built.
