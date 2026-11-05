# CTM UI vs Plenix CDN 0.86.0 — refresh audit

Measured on `local-site` origin/main `e645392` (after #96, the council session EntityHeader style 2). Docs: `https://design-system.lighthouseway.org/cdn/0.86.0/docs/<href>`. Read-only audit; nothing in the repo changed.

## Headline

- **Shell/navigation is already Plenix** (`AppShell`, `AppHeader` + `AppHeader.Account`, `NavPane` + `NavList` groups + `ToolRail` rail, case `SecondaryPane`). The gaps there are small.
- **Page templates are not used.** Uses in `static/ctm/*.js`: `ListingPage` 0, `SplitWorkspace` 0, `CommandBar` 0, `useCollectionView` 0, `RecordPage` 0, `SettingsLayout` 0, `FormFlow` 0, `Wizard` 0, `DraftState` 0, `Skeleton` 0, `useViewState` 0, `useRetry` 0, `ReadOnly` 0, `ResourceList` 0, `MetricCard` 0, `FileList` 0, `Auth`/`SignInForm` 0, `ActionBar` 0, `SidePanel` 0. `EntityHeader` 1 (session header only).
- **Every table goes through `window.CTMShell.Table`** (`shell-layout.js`). It wraps `P.DataGrid` but switches off what 0.86.0 gives by default: `narrow: "table"` (no row cards on phones, which data-grid.md now makes the default), `rowMenuButton: false` (actions are button columns, not `rowMenu`), `typeIcons: false`, and there is no `CommandBar`/`useCollectionView`. Search and filters are a hand-placed `Input`/`Checkbox` row above the grid. `CTMShell.Workspace` is a home-made `SplitView` + `ReadingPane`, which is what `SplitWorkspace` (listing-page.md) now does.
- **Hand-composed headers.** Pages open with `P.Text {as:"h1"}`, not `RecordPage.Header`/`EntityHeader`. `CaseHearings` builds `plx-entity-header__*` markup by hand (council-case.js:3504-3511). Loading is a `Spinner` + text (`loadingView`), not a `Skeleton`.
- **`ctm.css` has 612 lines.** It holds about 45 custom `ctm-*` blocks (vote table, timeline, spouse profile, hearing attendance, account hero, …) and overrides of `.plx-property-list`, `.plx-panel`, `.plx-form-actions`, `.plx-button`, `.plx-entity-header` and `.plx-data-grid`. DESIGN.md §1 says "no custom CSS", so most of these should go once the screens use templates.

## Inventory

Gap: none / S / M / L.

### Shared shell and sign-in

| Screen | File · function | Uses now | 0.86.0 target (doc) | Gap |
|---|---|---|---|---|
| App frame | app.js `App` (≈1312-2015) | `P.AppShell` (sets `page` itself), `AppHeader` with a hand-built brand span (`plx-app-header__name/product/app`), `AppHeader.Item` bell and language | application-shell.md, application-header.md | S |
| Main nav | app.js `App` → `nav` | `NavPane` + 4 `NavList` (sessions and cases groups) + `ToolRail.Item` rail; no `footer` (settings sits only in the account menu) | side-navigation.md, product-navigation.md | S |
| Case nav | app.js `caseNav` | `SecondaryPane` (collapsible, resizable, detailOpen) + 3 `NavList` + a ghost "Back" `Button` | secondary-pane.md, navigation-section-navigation.md | S (Back belongs to the `claimBack`/parent row) |
| Sign-in | app.js `App` (≈1275-1300) | `AppShell page=form` › `Center` › `Panel` › `Image` + `Text h2` + a stack of provider `Button`s | sign-in.md (`Auth page` + `SignInForm sso={SsoButtons}`), single-sign-on.md | M |
| Loading / error states | council.js `loadingView`, `loadFailure` (shared by all modules) | `Spinner` + `Text`; `Notice` + a hand-written retry | skeleton.md, view-state.md (`useViewState`), retry-pattern (`useRetry`) | M |
| Tables (all) | shell-layout.js `Table`, `Workspace` | Wrapped `DataGrid` (narrow table, no row menu, no CommandBar); `SplitView`+`ReadingPane` | data-grid.md, listing-page.md (`ListingPage`, `SplitWorkspace`), command-bar.md, use-collection-view.md | L |

### Council portal

| Screen | File · function | Uses now | 0.86.0 target (doc) | Gap |
|---|---|---|---|---|
| Home | council.js `CouncilHome`, `ReviewQueuePanel` | `Text h1` + 3 `Panel`s of `Card`s and text rows | dashboard-page.md / dashboard-grid.md (`WidgetGrid`), metric-card.md, resource-list.md | M |
| Sessions current / upcoming / archived | council.js `SessionList` | `CTMShell.Workspace`/`Table` ×3, hand-built create form (`Form`+`Columns`, `ctm-session-form*` CSS), `Toolbar` | listing-page.md (`ListingPage` + `CommandBar`), form-flow.md (create as `FormFlow surface="dialog"`) | L |
| Session detail | council.js `SessionWorkspace`, `AgendaItemCard`, dialogs | **`EntityHeader` style 2 (done)**; agenda via `CTMShell.Table` (`ctm-session-agenda-grid`) + `Tabs`; `SessionAttendance` (app.js) uses static `P.Table` | record-page.md (agenda Part 1/2 as sections), data-grid.md | S |
| New applications | council.js `NewApplicationsTable`; review `ReviewWorkspace`/`ReviewDetail` | `CTMShell.Table`; review = `SplitView`+`ReadingPane`+`Card`s+`PropertyList` | listing-page.md; master-detail-workspace.md (`SplitWorkspace`) | M |
| My / all active / archived cases | council.js `CasesTable` | raw `P.DataGrid mode=pages` + hand-placed search `Input` + "show closed" `Checkbox`; Open/Delete as button columns | listing-page.md + command-bar.md (search, `QuickFilter`), data-grid.md `rowMenu`; archived + read-only-state.md | L |
| Search | council.js `SearchWorkspace` | `Form`+`Input`+`Checkbox`+`CTMShell.Table` | search-workspace.md (`SearchWorkspace`) | M |
| Reports / statistics | council.js `StatisticsWorkspace` | `Panel`s of `PropertyList` | dashboard-grid.md + metric-card.md | M |
| Case overview (summary) | council-case.js `CaseSummary`, `ApplicationReviewActions` | `Text h1` (case number) + `Columns`/`Panel`/`DataPill`/`Timeline`; no case header on the other tabs | record-page.md (`RecordPage` + `EntityHeader`: number, parties, status, manager) | L |
| Timeline · parties · marriage · separation · petition | council-case.js `CaseTimeline`, `CaseParties` (+`SpouseProfileEditor/ContactSection/PhotoUpload`), `CaseMarriage`, `CaseSeparation`, `PetitionWorkspace`, `CouncilEditablePanel` | each tab its own `Text h1`; `Panel`/`PropertyList`/`Form`; panel toggle by DOM `.closest('.plx-panel__header')`; `ctm-spouse-*`, `ctm-case-*`, `ctm-petition-header` CSS | record-page.md body sections; form-section.md; read-only-state.md for closed cases | M |
| Hearings | council-case.js `CaseHearings`, `HearingAttendance` | **hand-built `plx-entity-header` markup**, `P.Table`, `ctm-hearing-*`/`ctm-past-hearings-table` CSS | `EntityHeader kind="section"` (record-page.md), data-grid.md | M |
| Notes · calls · assessments · audit | council-case.js `CaseNotesWorkspace`, `CallLog`, `AssessmentsWorkspace`, `CaseAudit` | `CTMShell.Workspace` + `Toolbar` + `Dialog` forms | master-detail-workspace.md (`SplitWorkspace` + `CommandBar`); audit = listing-page.md read-only | M |
| Decision and voting | council-case.js `DecisionWorkspace`, `DecisionForm`, `CouncilVoteRecord`, `DecisionVersion` | `Panel`/`Form`; vote grid is custom CSS (`ctm-council-vote-*`, `ctm-vote-total*`, `ctm-decision-voting-workspace`) | record-page.md + form-section.md + page-actions.md (`ActionBar`); votes as a `DataGrid` | L |
| Reports (case) / requests | council-case.js `ReportsWorkspace`, `RequestsPanel`, `RequestComposer`, `RequestDetail`, `InterviewForm`, `ExternalLinkPanel`, `ReturnedResponsePanel`; council-media.js `ReportsReader`, `ReportDetailTabs`, `ReportRecorder`, transcript parts; app.js `ReportReader`/`ReportDetail` | `Tabs` › `SplitView`/`ReadingPane` + `CTMShell.Table` + `Card`s; `ctm-report-party-card*` CSS | master-detail-workspace.md (`SplitWorkspace`), draft-state.md for report drafts | M |
| Documents / evidence | council-media.js `CaseFilesWorkspace`, `FilePreview`, `PdfPreview`; app.js `CaseFiles` | `SplitView` + `CTMShell.Table` + `MediaViewer`; **`<a class="plx-button plx-button--secondary">`** (media.js:2188); `ctm-demo-*` CSS | file-list.md (`FileList`) in `SplitWorkspace` | M |
| Decree | council-decree.js `DecreeWorkspace`, `DecreePreparation`, `IssuedDecree`, `DecreeTemplateDraft` | `Text h1` + `PropertyList` ×32 + `ProgressSteps`; `ctm-decree-*` CSS | record-page.md + form-flow.md + page-actions.md | M |
| Appeals | council-decree.js `AppealsWorkspace`, `AppealDetail` | hand-built `SplitView` + `CTMShell.Table` + `ReadingPane` | master-detail-workspace.md (`SplitWorkspace`) | M |
| Communications | app.js `CommunicationsWorkspace`, `MessageComposer` | `Tabs` + `CTMShell.Workspace` + `Toolbar` | master-detail-workspace.md | S (follows the foundation slice) |
| Notifications | app.js `NotificationInbox` | `Panel` + rows of `Button`s | listing-page.md / resource-list.md; DataGrid `unread` | M |
| Account | ui-workspaces.js `Profile`, `SecuritySessions` | `Panel`s, `ctm-account-hero`/`ctm-account-grid` CSS | settings-page.md (`SettingsLayout`) or record-page.md header + `SettingsSection` | M |
| Settings / admin (users, config, data, audit) | ui-workspaces.js `Administration`, `MemberDirectory`, `Enrollment`, `ConfigurationWorkspace`, `AuditFilters`; historical-entry.js | `Text h1` + `Tabs variant=contained` (should be a NavList); config = `Panel`s with raw JSON `Textarea`s; members = `Tabs` › `CTMShell.Table` | settings-page.md (`SettingsLayout nav={NavList}`, `SettingsSection`, `SettingsRow`, `CreatePage`/`EditPage`); members = listing-page.md | L |
| External priest report | external-report.js | `Center` + `Panel` + `Form` + `PropertyList` | one-column-layout.md + form-section.md | S |

### Applicant portal

| Screen | File · function | Uses now | 0.86.0 target (doc) | Gap |
|---|---|---|---|---|
| Home | app.js `content()` `page==="home" && !council` | `Text h1` + one `Card`/`Panel` or `EmptyState` | dashboard-page.md / resource-list.md (next action first) | M |
| Applications list | app.js `applicationCard`; applicant.js `StartApplication` | `Panel` per application with an inline fee `Notice` | listing-page.md or resource-list.md + `CommandBar` "New application" | M |
| Application form | applicant.js `ApplicationEditor` | one long `Stack`: fields, then saved/unsaved/review `Notice`s, then History, Files, Filing, Lifecycle, Payments, Supplements panels; a "Review" toggle | wizard.md or form-flow.md + draft-state.md (`DraftState`), form-section.md, form-actions.md | L |
| Filing / payment / lifecycle | applicant-filing.js, applicant-payments.js, applicant-lifecycle.js, applicant-recovery.js | `Panel` + `Text` + `Notice` lists | wizard step + data-grid.md (payment history) | M |
| Documents | applicant-files.js `ApplicationFiles` | `Panel` + `FileInput` | file-list.md + forms-file-upload.md (`DropZone`) | M |
| History | applicant-history.js `History` | `Select` + `Text` + `Dialog` | timeline.md or a listing-page.md version list | M |
| Appeals / petitions | applicant-appeals.js `StartAppeal`, `StartPetition`; applicant-supplements.js; applicant-responses.js | `Panel` + `Notice` + `Textarea` | form-flow.md + draft-state.md (append-only supplements) | M |
| Appointments | applicant-appointments.js | `Panel` + `Text` rows + `Textarea` | listing-page.md / resource-list.md | M |
| Decrees | applicant-decrees.js `ReleasedDecrees` | `Panel` + `Text` + `Button` | resource-list.md / file-list.md | S |
| Notifications | applicant-notifications.js `Inbox` | `Panel` + `Text` + `Button` | listing-page.md / resource-list.md | M |
| Messages | applicant-messages.js `Thread` | `Panel` + `Text` + `Textarea` | master-detail-workspace.md (reading pane + composer) | M |
| Case (past/current) | app.js `page==="case" && !council`, `caseList`; applicant-requests.js, applicant-assessments.js | `Text h1` + bullet `List`s + embedded module panels; past cases as `Card` stack | record-page.md (`RecordPage` + `EntityHeader`); past cases listing-page.md | M |

## Refresh slices (ordered by visible impact)

Each slice owns its files outright. Slice 1 must merge first, because every list goes through `CTMShell`. Slices 2–7 can then run in parallel. `ctm.css` is shared, so each slice records the selectors it no longer uses, and slice 8 deletes them in one pass.

| # | Slice | Files owned | CDN templates | Gap |
|---|---|---|---|---|
| 1 | **Collection foundation** (first, then the rest in parallel) | `static/ctm/shell-layout.js` | listing-page.md (`ListingPage`, `SplitWorkspace`), data-grid.md (narrow `auto` + row cards, `rowMenu`, `openKey`), command-bar.md, use-collection-view.md, skeleton.md | L |
| 2 | **Council lists and home** | `static/ctm/council.js` (`CouncilHome`, `SessionList`, `CasesTable`, `NewApplicationsTable`, `ReviewWorkspace`, `SearchWorkspace`, `StatisticsWorkspace`, `loadingView`/`loadFailure`, session agenda) | listing-page.md + command-bar.md, search-workspace.md, dashboard-grid.md + metric-card.md, form-flow.md (create session), read-only-state.md, view-state.md | L |
| 3 | **Case record** | `static/ctm/council-case.js` | record-page.md (`RecordPage` + `EntityHeader` case header on every tab; `kind="section"` for hearings), form-section.md, page-actions.md, read-only-state.md, master-detail-workspace.md (notes/calls/assessments/audit) | L |
| 4 | **Shell, sign-in and app.js views** | `static/ctm/app.js`, `tribunal/templates/tribunal/shell.html` | sign-in.md (`Auth` + `SignInForm` + `SsoButtons`), side-navigation.md (`footer`), application-shell.md, resource-list.md (notifications, applicant home/list), record-page.md (applicant case) | M |
| 5 | **Applicant filing and portal modules** | `static/ctm/applicant.js`, `applicant-*.js` | wizard.md / form-flow.md + draft-state.md, form-section.md, file-list.md, resource-list.md, data-grid.md | L |
| 6 | **Settings and account** | `static/ctm/ui-workspaces.js`, `static/ctm/historical-entry.js` | settings-page.md (`SettingsLayout`, `SettingsSection`, `SettingsRow`, `CreatePage`/`EditPage`), listing-page.md (members, audit) | L |
| 7 | **Documents, reports, decree, appeals** | `static/ctm/council-media.js`, `static/ctm/council-decree.js` | master-detail-workspace.md (`SplitWorkspace`), file-list.md, record-page.md + form-flow.md + page-actions.md (decree), draft-state.md | M |
| 8 | **CSS retirement and external page** (last) | `static/ctm/ctm.css`, `static/ctm/external-report.js` | one-column-layout.md; delete `ctm-*` blocks and `.plx-*` overrides left dead by slices 2–7 | M |

Notes for the slice owners:
- Moving a screen onto a template is a layout change, so it needs an owner entry in `decisions/screens.md` (plenix-page-templates.md). The locked council navigation and split list/detail patterns in `build-spec/interface-contract.md` still win.
- Slice 4 owns the `App` route switch in app.js. Slices 2, 3, 5, 6 and 7 keep their module exports (`CTMCouncil.*`, `CTMUI.*`, `CTMApplicant*`) with the same signatures, so they do not need to edit app.js.
- `AppShell` derives the layout mode from `page`, and patterns such as `SettingsLayout` claim it. Once templates are used, the hard-coded `page` list in `App` (app.js ≈2005) should go. That change is slice 4's.
