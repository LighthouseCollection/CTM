# CTM screens → Plenix page templates

Status: **proposed** (2026-11-03). Plenix ships whole-page templates and state
components that CTM does not use yet; every CTM page is hand-composed from small
parts. Measured on main `9fa6386`: `RecordPage`, `ListingPage`,
`MasterDetailPage`, `SettingsLayout`, `FormFlow`, `Wizard`, `DraftState`,
`FilterBar`, `ActionBar`, `DataToolbar`, `Skeleton`, `useViewState`, `useRetry`,
`ReadOnly` all have 0 uses; `Notice` 230, `PropertyList` 129, `EmptyState` 52.

**Rule:** a new or reworked screen starts from the template in this table.
Hand-composing a page that has a template needs a recorded reason (in the slice
design.md) - usually a missing Plenix capability, which also goes into
`plenix-requests.md`. Before use, read the component's doc at the pinned
version: `<PLENIX_BASE>docs/<doc-id>.md`. Moving an existing screen onto a
template is a layout change: it needs an owner decision in
`decisions/screens.md` (the locked navigation and split list/detail patterns in
`build-spec/interface-contract.md` still win).

## Page templates

| CTM screen (route / page key) | Plenix template (doc id) | Components | Notes |
|---|---|---|---|
| App frame | `application-shell` | `AppShell`, `PageContent`, `useAppLayout` | Already used; keep the locked council navigation |
| Home (`/`, `home`) | `dashboard-grid`, `metric-card`, `resource-list` | dashboard grid, metric/resource cards | Next actions for the signed-in role first |
| Cases (`/cases/active`, `/cases/mine`, `/cases/past`) | `listing-page` + `filter-bar` + `data-grid` | `ListingPage`, `FilterBar`, `DataGrid`, `DataToolbar` | Cases are a workspace table, never nav entries |
| Archived (`/cases/archived`) | `listing-page` + `read-only-state` | `ListingPage`, `ReadOnly` | Closed proceedings read-only |
| Tribunal Sessions (`/sessions/*`) | `listing-page`; session detail `record-page` | `ListingPage`, `RecordPage`, `EntityHeader` | Agenda Part 1 / Part 2 as sections |
| Case Overview (`summary`, `timeline`, `parties`, `marriage`, `separation`) | `record-page` | `RecordPage`, `EntityHeader`, `PropertyList`, `Tabs` / `navigation-section-navigation` | Case number, parties, status, assigned manager in the header |
| Reports (`/reports`, case `reports`) | `master-detail-workspace` / `secondary-pane` | `MasterDetailPage`, `SplitView`, `ReadingPane` | Outlook-style split list/detail (locked) |
| Communications (`communications`, `calls`) | `master-detail-workspace` | `MasterDetailPage`, `ReadingPane` | Private per-party copies |
| Documents / Evidence | `master-detail-workspace` + `file-list` | `MasterDetailPage`, file list | Latest version default, history council-only |
| Search (`/search`) | `search-workspace` | `SearchWorkspace` | Already partly used (6) |
| Statistics and Reports (`statistics`) | `dashboard-grid` | metric cards, charts | |
| Decision & Voting (`decision`) | `record-page` + `form-section` | `Form`, `FormSection`, `FormActions`, `ActionBar` | Irreversible steps confirmed |
| Decree (`decree`) | `record-page` + `form-flow` | `FormFlow`, `ActionBar` | Admin/secretary only |
| Appeals (`appeals`) | `master-detail-workspace` | `MasterDetailPage` | Both parties' appeals, one hearing |
| Case Audit (`audit`) | `listing-page` (read-only) | `ListingPage`, `DataGrid`, `ReadOnly` | |
| Settings (`/settings/users`, `configuration`, `/account`) | `settings-page` | `SettingsLayout`, `SettingsSection`, `SettingsRow` | |
| Applicant filing (`/applications/new`, `application`) | `form-flow` / `wizard` + `draft-state` | `FormFlow` or `Wizard`, `DraftState`, `FormSection`, `FormActions` | Saved drafts, payment step, required files |
| Applicant appeal filing | `form-flow` + `draft-state` | `FormFlow`, `DraftState` | Append-only supplements |
| Notifications (`/notifications`) | `listing-page` / `resource-list` | `ListingPage` | |
| External priest report (`external-report.html`) | `one-column-layout` + `form-section` | `Form`, `FormSection` | Capability link page; fix CDN pin first (DR-001) |

## State components (every screen)

| State | Plenix | Use |
|---|---|---|
| Loading | `skeleton`, `view-state` | `Skeleton` shaped like the final layout; `useViewState` for loading/empty/error/ready |
| Empty (first use / filtered / cleared) | `empty-state`, `feedback-zero-state`, `feedback-no-results-state` | `EmptyState` with the next action |
| Error / retry | `error-state`, `retry-pattern` | `EmptyState` error variant, `useRetry`, `RetryNotice`; keep user input |
| Forbidden | `error-state` | Says what is not allowed, never reveals other parties' data |
| Closed proceeding | `read-only-state` | `ReadOnly` / `ReadOnlyProvider` instead of hiding controls one by one |
| Draft | `draft-state` | `DraftState` for applicant drafts and report drafts |
| Conflict (409, stale `expected_version`) | `section-message` | `Notice` with reload/compare action |
| Undo where safe | `undo-pattern` | `useUndo` for reversible actions only |
| Processing unavailable (OCR/audio) | `section-message` | `Notice` saying unavailable - never "processed" |
