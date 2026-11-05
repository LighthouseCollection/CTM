# ctm3-48 — inventory: every CTM style → Plenix

Source: `static/ctm/ctm.css` on main `aec10de` (612 lines) and a search of
`static/ctm/*.js`, `static/ctm/*.html`, `tribunal/templates/` for inline
`style`. Plenix docs read at 0.86.0 (`<PLENIX_BASE>docs/<id>.md`). "Dead" =
no use found in `static/ctm/*.js`; delete, but grep for a template-string
build (`ctm-…-${x}`) first.

Legend: **Replace** = documented Plenix part exists; **Delete** = drop, the
Plenix default is the intended look; **Needs Plenix** = filed in
`plenix-requests.md`, with the interim Plenix-only composition to ship now.

## Inline styles

| Where | What | Result |
|---|---|---|
| `static/ctm/*.js` | none (`style:` hits in `applicant-filing.js:129`, `applicant-payments.js:51` are `Intl.NumberFormat` options) | Nothing to do |
| `tribunal/templates/tribunal/priest_request_print.html` | `<style>` A4 page: `@page A4 20mm`, ruled answer lines, `#000/#fff/#999` | **Keep** (print layout exception, issue #48). Needs Plenix: PLX-010 |

## ctm.css, rule by rule

| # | Rule(s) | Screen (file) | Plenix replacement | Kind |
|---|---|---|---|---|
| 1 | `.ctm-session-header-action` (fixed 10.5rem width) | Session / hearing header action (`council.js`, `council-case.js`) | `Button` in the `EntityHeader`/`PageActions` actions slot, natural width | Delete |
| 2 | `.ctm-spouse-header`, `__fact`, `__name` | Spouse header (`council-case.js`) | `EntityHeader` with `PropertyList layout="stacked"` facts, or `ProfileSummary` (`profile-summary`) | Replace |
| 3 | `.ctm-petition-header`, `__party`, `__name` | Petition header (`council-case.js`) | `Stack` + `EntityTitle` (`entity-title`); parties as `Avatar`+`Text` in a `Stack direction="row" wrap` | Replace |
| 4 | `.ctm-spouse-profile-section` accent var (`--plx-ref-color-orange-700`, `#9a4d00`), `__heading` color, `.plx-property-list__label` recolored blue | Spouse profile sections (`council-case.js`) | Plain `Panel` + `SectionHeading`; Plenix label colors. Orange/blue `ref` colors are not allowed (`ref` tokens, not `sys`/`comp`) | Delete |
| 5 | `.ctm-spouse-profile-section__edit` | — | Dead | Delete |
| 6 | `.ctm-spouse-profile-section__divider` (orange rule) | Spouse profile sections | `Divider` (`divider`) | Replace |
| 7 | `.ctm-decision-nav-icon`, `.ctm-decree-nav-icon` (custom SVG balance icon) | — | Dead in JS. Nav uses a Plenix icon; no balance/gavel glyph at 0.86.0 → PLX-011 (icon request); interim `description` / `article` | Delete |
| 8 | `.ctm-spouse-profile-section--two-columns .plx-property-list` grid + center rule, ≤42rem one column | Spouse profile | `Columns count={2} divided collapseBelow="medium"`, one `PropertyList layout="stacked"` per column | Replace |
| 9 | `.ctm-spouse-photo` (68px), `.plx-avatar__image` cover | Spouse photo | `Avatar size="2xl"` (64px); the 68px size is dropped | Replace |
| 10 | `.ctm-spouse-photo-control`, `__input` (visually hidden), `__change`, focus outline, `__error` | Spouse photo change | `AvatarUpload size="2xl"` (`avatar-upload`) with `strings` in EN/AR, `maxSize`, `disabled` while saving; errors through its own `tooLarge`/`notImage` | Replace |
| 11 | `.ctm-case-summary-person-pill` (`inline-flex/fit-content` ×3 `!important`) | Case summary participants (`council-case.js`) | `Tag`/`Badge` (content-sized by default); remove the cached-script workaround | Delete |
| 12 | `.ctm-case-summary-fields` 2-col grid, ≤48rem one column | Case summary | `Columns count={2} collapseBelow="wide"` with two `PropertyList layout="stacked"` | Replace |
| 13 | `.ctm-case-edit-grid` 3-col, ≤820px one | Case card edit forms | `FormSection` (`form-section`) + `Columns count={3} collapseBelow="wide"` | Replace |
| 14 | `.ctm-case-read-grid input[readonly]` (white bg, no pointer) | Case card read mode | `ReadOnlyField` (`read-only-field`) / `PropertyList` in read mode — never a disabled-looking input | Replace |
| 15 | `#ctm-root .plx-panel .plx-form-actions` transparent (2× `!important`) | Card edit actions | `FormActions` inside `Panel` as documented; if its surface still differs, that is a Plenix defect → report, don't override | Delete |
| 16 | `.ctm-session-form-grid` 2-col, `.ctm-session-form .plx-form-actions` transparent | New / edit tribunal session (`council.js`) | `Form` + `FormSection` + `Columns count={2} collapseBelow="wide"` + `FormActions` | Replace |
| 17 | `.ctm-calendar-add-icon` (two stacked icons, `#fff`, 999px) | "Add hearing to calendar" action (`council.js`) | `Button icon="event_available"` with a label naming the action; no composite icon. Glyph request in PLX-011 | Replace |
| 18 | `.ctm-report-party-cards`, `.ctm-report-party-card`, `.is-selected`, ≤42rem one column (7 raw colors) | Report recipients (`council-case.js`) | `ChoiceList` / checkbox `ChoiceCard`s (`choice-card`) in `Columns count={2} collapseBelow="medium"`; selection look is Plenix's | Replace |
| 19 | `.ctm-council-vote-table` + `__header/__row/__summary`, `.ctm-council-vote-member`, `.ctm-council-vote-choice` (native radios, `accent-color`) | Decision & Voting (`council-case.js`) | **Needs Plenix PLX-009** (choice matrix with totals). Ship now: `Table` (`table`) with Member column (`Avatar`+name) and one Vote column rendering `ButtonGroup` of three `Button`s with `tone="success"/"danger"/"neutral"` (Plenix "vote-screen-37"), `aria-pressed`; disabled when read-only via `ReadOnly` | Needs Plenix (interim Replace) |
| 20 | `.ctm-vote-total`, `--approve/--deny/--abstain` (`#15803d`, `#b91c1c`, `#9a7b43`) | Vote totals | `Badge tone="success"/"danger"/"neutral"` with icon + count, or `Metric`; never color alone | Replace |
| 21 | `.ctm-decree-template`, `.plx-panel` subtle bg | Decree editor (`council-decree.js`) | `Stack gap` of `Panel`s with the documented panel variant (`panel`); no background override | Replace |
| 22 | `.ctm-hearing-header .plx-entity-header__tile[data-plx-media-hue=green]` gradient | Current hearing header | `EntityHeader` tile as Plenix draws it + status `Badge tone="success" icon` "In progress" | Replace |
| 23 | `.plx-data-grid .plx-data-pill:not([data-plx-category])` grey → off-white | All DataGrids | Delete; Plenix owns pill colors. If grey reads as "disabled", report to Plenix | Delete |
| 24 | `.ctm-application-review__accept.plx-button--primary` green + hover | Application review "Accept" (`council-case.js`) | `Button variant="primary"` (one primary). If owner wants green: `tone="success"` is for chosen states, not rest → keep primary | Delete |
| 25 | `.ctm-demo-evidence-gallery`, `__item`, `img` hover zoom | — | Dead (demo). If revived: `AssetGallery lightbox` (`image-gallery`) | Delete |
| 26 | `.ctm-demo-document-list`, `__item`, `__type` | — | Dead (demo). If revived: `FileList` (`file-list`) | Delete |
| 27 | `.ctm-hearing-attendance-table` + `__header/__row`, `-member`, `-choice`, `--present` | Hearing attendance modal (`app.js`, `council.js`, `council-case.js`) | Same pattern as #19 (PLX-009). Ship now: `Table` in `Dialog`, Attendance column = `SegmentedControl` Present / Absent (`segmented-control`) | Needs Plenix (interim Replace) |
| 28 | `.ctm-demo-file-preview` (max 36rem, contain) | Document preview (`council-media.js`) | `Preview` / `ImageViewer` (`preview`, `specialized-image-viewer`) | Replace |
| 29 | `.ctm-past-hearings-table` + `__header/__row` | Past hearings (`council-case.js`) | `Table label=…` (static) or `DataGrid` | Replace |
| 30 | `.ctm-case-timeline` + `__year-group/__year` (vertical text) `/__events/__event/--marriage/__date/__marker/__body` | Case timeline (`council-case.js`) | `Timeline` (`timeline`): `time` via `Intl`, `dateTime` ISO, `icon` per event type (marriage gets its own icon from the Plenix set, checked in the icon bundle), status as `badge`; year grouping by `SectionHeading` per year | Replace |
| 31 | `.ctm-account-hero`, `__avatar` (`#fff`, numeric font) | My account (`ui-workspaces.js`) | `SettingsLayout` header with `ProfileSummary` / `Avatar size="2xl"` | Replace |
| 32 | `.ctm-account-grid` 3-col | My account | `SettingsSection` + `SettingsRow`s (`settings-page`) | Replace |
| 33 | All `@media (max-width: …)` blocks | many | Removed with their rules; `Columns collapseBelow` and Plenix breakpoints do it | Delete |

## Needs Plenix (summary)

| Request | Need | Interim in this slice |
|---|---|---|
| PLX-008 | Arabic RTL text: documented Arabic type rule (fonts.css ships IBM Plex Sans Arabic / Readex Pro but `typography` names only DM Sans) and confirmation that `LocaleProvider dir="rtl"` covers all components used here (extends PLX-004) | `LocaleProvider` as now (`applicant.js:426`) on every root; no local Arabic CSS needed |
| PLX-009 | Council vote / attendance table: per-row single choice across columns with a totals row | `Table` + `ButtonGroup` tone buttons / `SegmentedControl` (#19, #27) |
| PLX-010 | Printable A4 page: page size, margins, letterhead/seal slot, ruled answer lines, direction per field, on top of `usePrint` | Priest request print template keeps its `<style>`; decree/certificate prints unchanged |
| PLX-011 | Icons: calendar-add, balance/gavel (decision), seal/certificate (decree) | `event_available`, `description`, `article` |
