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
