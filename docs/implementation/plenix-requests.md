# Requests to the Plenix design system

Things CTM needs that it may not add locally (no custom CSS, tokens or
lookalike components). **Before filing, check the pinned docs**
(`<PLENIX_BASE>docs/index.json`) for an existing component, prop or `plx-`
class; close the row as "Exists: <doc id>" if found. Engineers and the UI
finish gate add rows; governance sends them to the Plenix team.

| Id | Need | Why (CTM screen / rule) | Checked in docs? | Status |
|---|---|---|---|---|
| PLX-001 | Tabular (fixed-width) numerals for counts, case numbers and amounts in tables | Case lists, payments, statistics | Not yet | Open |
| PLX-002 | Minimum target size options for icon buttons in dense tables (WCAG 2.5.8) | Case and session tables | Not yet | Open |
| PLX-003 | Sticky headers that keep focused rows visible on scroll (WCAG 2.4.11) | Long case/session tables | Not yet | Open |
| PLX-004 | Confirmed RTL mirroring for all page templates and state components | Arabic views | Not yet | Open |
| PLX-005 | Motion honors `prefers-reduced-motion` | Accessibility | Not yet | Open |
| PLX-006 | Scroll containment inside dialogs and drawers | Decision/decree dialogs | Not yet | Open |
| PLX-007 | `Card` icon support (earlier gap: `integration/card-icon-cdn-gap.md`) | Home / dashboards | Check 0.68+ | Open |
| PLX-008 | Arabic RTL text: a documented Arabic type rule (fonts.css ships IBM Plex Sans Arabic / Readex Pro; `typography` names only DM Sans) and confirmation that `DirectionProvider`/`LocaleProvider` cover every component CTM uses | Every Arabic screen; #48 (`slices/ctm3-48-remove-css`) | Yes, 0.86.0: `direction`, `typography`, `fonts.css` | Open: plenix-ds/pds#180 |
| PLX-009 | Choice matrix table: one single choice per row across option columns (vote Approve/Deny/Abstain, attendance Present/Absent) with a totals row | Decision & Voting, hearing attendance; #48 | Yes, 0.86.0: `table`, `data-display-editable-table`, `button` (`tone`), `segmented-control` — no matrix or totals row | Open: plenix-ds/pds#88 (interim: `Table` + tone `ButtonGroup`) |
| PLX-010 | Printable A4 page: page size and margins, letterhead/seal slot, ruled answer lines, per-field direction, on top of `usePrint` | Priest request print, decree certificate; #48 | Yes, 0.86.0: `print` (hook only) | Open: plenix-ds/pds#87 (print template keeps its `<style>`) |
| PLX-011 | Icons: calendar-add, balance/gavel (decision), seal/certificate (decree) | Sessions, case navigation; #48 | Yes, 0.86.0: `plenix-icons-plenix.js` | Open: plenix-ds/pds#181 |
| PLX-012 | `SplitWorkspace` and `ListingPage` usable inside an existing `AppShell` (no second 100dvh frame, `<main>` or skip link) | Every CTM list (`CTMShell.Workspace`/`Listing`, #97 slice 1): CTM draws the template bodies itself until then | Yes, 0.86.0: `listing-page`, `master-detail-workspace` (both always render `AppShell`) | Open |
| PLX-013 | `DataGrid` re-applies a changed `filter` (e.g. `useCollectionView` search) even when `data` is a new array with the same records | `CTMShell` search lists (#97 slice 1): measured locally, 0.86.0 keeps showing every row; CTMShell keeps the array stable until then | Yes, 0.86.0: `data-grid`, `use-collection-view` | Open |
| PLX-014 | `EntityHeader` (kind "section", `actionsLayout: "column"`, `actionLabels: "text"`) draws a "More actions" button with an empty menu even when every action fits and no `moreActions` are given | Case hearings section header (#97 slice 3, `CaseHearings`): measured locally on 0.86.0 with two actions; CTM keeps the two actions in the header and accepts the empty More until then | Yes, 0.86.0: `record-page` (EntityHeader) | Open |
| PLX-015 | `SignInForm` without a password: an SSO-only sign-in (providers only, no identifier/password form and no "or" divider), so a no-password app can use the whole sign-in template | Sign-in (#97 slice 4): CTM uses `Auth page` + `SsoButtons` alone; the button tone (Microsoft was primary) and a logo slot above the title are also missing | Yes, 0.86.0: `sign-in`, `single-sign-on` (`SignInForm` always draws a password field) | Open |
