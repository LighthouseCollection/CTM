# ctm3-48 — design: screen-by-screen plan (G2)

Inputs: `brief.md`, `inventory.md` (row numbers `#n` below), `DESIGN.md`,
`plenix-page-templates.md`. Plenix 0.86.0. Owner choice D-0022: one change,
one preview at the end — no per-screen previews.

**Scope rule.** This slice swaps styling for Plenix parts. It does not move
any screen onto a new page template (that is a layout change needing a
`decisions/screens.md` entry, per `plenix-page-templates.md`). Where a CTM
region is replaced, it uses the component the template map already names for
that screen, so the later template move is smaller. States, words, routes,
API calls and permissions stay exactly as they are; no new strings except
`AvatarUpload`/`Timeline` labels, each in EN and AR.

## 1. Screens

| Screen (file) | Lead / primary action (unchanged) | Changes (inventory rows) | Template (later move) |
|---|---|---|---|
| App root (`app.js`, `shell-layout.js`) | — | Wrap the council root in `DirectionProvider follow` (or `root`) instead of only setting `documentElement.dir` (`app.js:1111`), same as applicant `LocaleProvider` (`applicant.js:426`). Remove the `ctm.css` link from `shell.html` | `application-shell` |
| Tribunal sessions: list, new/edit form, header (`council.js`) | Session list; "Create session" | #1, #16, #17 | `listing-page` / `record-page` |
| Hearing attendance dialog (`app.js`, `council.js`, `council-case.js`) | Roster; "Save attendance" | #27 → `Dialog` + `Table` + `SegmentedControl` per member | `form-dialog` |
| Case Overview: summary, parties, marriage, separation (`council-case.js`) | Case header; edit per card | #2, #3, #4, #5, #6, #8, #9, #10, #11, #12, #13, #14, #15 | `record-page` |
| Case timeline (`council-case.js`) | Timeline | #30 → `Timeline`, one per year under a `SectionHeading` | `record-page` |
| Current / past hearings (`council-case.js`) | Hearing header | #22, #29 | `record-page` |
| Reports: recipient picker (`council-case.js`) | "Send report" | #18 | `master-detail-workspace` |
| Decision & Voting (`council-case.js`) | Vote table; "Record decision" | #19, #20, #7 | `record-page` + `form-section` |
| Application review (`council-case.js`) | "Accept application" (primary) | #24 | `record-page` |
| Decree editor (`council-decree.js`) | Template panels; "Issue decree" | #21 | `form-flow` |
| Documents / media preview (`council-media.js`) | Preview | #28 | `master-detail-workspace` |
| All DataGrids | — | #23 (delete override) | `listing-page` |
| My account (`ui-workspaces.js`) | Profile | #31, #32 | `settings-page` |
| Priest request print (`priest_request_print.html`) | — | none (kept, PLX-010) | `print` |
| Dead / demo rules | — | #5, #7, #25, #26 deleted | — |

## 2. Vote and attendance tables (the only real redesign)

Today: CSS grid, one native radio per option column, totals row, colored dots.
Plenix has no choice matrix (PLX-009). Ship now, Plenix only:

- `Table label="Council votes"` / `"Attendance"` (EN/AR), columns: Member
  (`Avatar size="sm"` + name, `kind: "name"`), Vote (`ButtonGroup` of
  Approve / Deny / Abstain, `Button tone="success" | "danger" | "neutral"`,
  pressed = chosen, `aria-pressed`), or Attendance (`SegmentedControl`
  Present / Absent).
- Totals under the table: three `Badge`s with icon + count (`tone` success /
  danger / neutral). Never color alone.
- Keyboard: Tab to each group, arrows inside it; same submit as today.
- Read-only (decision recorded / proceeding closed): wrap in `ReadOnly`;
  buttons not rendered as editable.
- When Plenix ships PLX-009, swap to it in a follow-up; no CTM CSS meanwhile.

## 3. State matrix (unchanged; confirm nothing regresses)

| Region | Loading | Empty | Error | Forbidden | Read-only | Draft | Conflict | Unavailable |
|---|---|---|---|---|---|---|---|---|
| Case cards (edit/read) | as today | as today | `Notice` as today | as today | `ReadOnlyField` (#14) | edit state as today | `Notice` as today | n/a (no processing) |
| Vote / attendance table | as today | `Table empty=` text (EN/AR) if no members | `Notice` as today | as today | `ReadOnly` | n/a (submit at once) | `Notice` as today | n/a |
| Spouse photo | — | initials (`AvatarUpload` without `src`) | `AvatarUpload` strings | control hidden | `disabled` | n/a | n/a | n/a |
| Timeline | as today | `EmptyState` as today | as today | as today | n/a | n/a | n/a | n/a |
| Report recipients | n/a | n/a | validation as today | as today | hidden | n/a | n/a | n/a |

"As today" = the existing behavior is kept; this slice adds no states.
Unreachable spec states stay listed as missing elsewhere, not built here.

## 4. Preview (AC-7, the one preview)

At the end, run `uv run --group browser python scripts/browser_cdn_smoke.py`
(and the frontend tests). Post on #48: EN desktop screenshots of every screen
in §1; AR desktop + EN 390px for Case Overview, Decision & Voting, attendance
dialog, timeline (direction and layout changed there). Seed data only
(`seed_demo`), never real case data.

## 5. Choices the builder must not invent

- No new colors, accents or sizes (the orange/blue section accents and 68px
  photo are dropped on purpose; inventory #4, #9).
- If a Plenix default looks wrong (pill grey #23, form-actions surface #15),
  report it to `plenix-ds/pds`; do not override.
- Words: new labels come from `docs/content/messaging.md` and
  `docs/i18n/arabic.md`; anything institutional → ask `ctm3-technical-writer`.

## Tests

| ID | Check |
|---|---|
| AC-1 | `test -f static/ctm/ctm.css` fails; `grep ctm.css tribunal/templates` empty; `tests/frontend/council-shell.test.cjs` rewritten to assert Plenix components instead of reading `ctm.css` |
| AC-2 | `grep -rhoE "ctm-[a-z]" static/ctm/*.js` returns only non-styling ids (`ctm-root`) |
| AC-3 | `node scripts/check_frontend_contract.cjs --base origin/main`; opengrep `.opengrep/ctm.yml` |
| AC-4 | `node --test tests/frontend/*.test.cjs`; PostgreSQL pytest in CI |
| AC-5 | `node scripts/check_i18n.cjs --base origin/main`; AR screenshots from §4 |
| AC-6 | Only `<style>` left: `priest_request_print.html`; PLX-008..011 rows in `plenix-requests.md` |
| AC-7 | Screenshots linked on #48 |

```owners
ctm3-frontend-engineer: static/ctm/**, tribunal/templates/tribunal/shell.html, tests/frontend/**
ctm3-design-director: docs/implementation/slices/ctm3-48-remove-css/**, docs/implementation/plenix-requests.md
```
