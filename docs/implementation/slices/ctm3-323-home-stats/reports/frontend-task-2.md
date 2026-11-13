# Issue 323, frontend task 2: council members as compact person tiles

Role: ctm3-frontend-engineer (CTM3 · Frontend Engineer #323). Branch `agent/frontend-engineer-323`, rebased on main after #334. Plenix CDN 1.7.0.

## Layout statement

- **Template:** the Home dashboard, region 4 (`ctm3-170-home/design.md` row 4). It is still a `Panel` "Council members" holding a Plenix `WidgetGrid` of `MetricCard type="person"`.
- **What leads:** each member's photo or initials, then the name and role. The active-case count is small, at the inline end.
- **Density:** compact. `layout="tile"` turns on the Plenix person tile (ADR 0056, pds#1240). `WidgetGrid itemSize="sm"` gives columns at least 200px wide, at most 6. `columns: 4` is removed because `columns` overrides `itemSize`.

## Items 1 and 2 of the issue (Plenix 1.7.0 defaults, checked)

| Check | main on 1.7.0 | this branch |
|---|---|---|
| The chart cards are the same height (1366 and 1920, EN and AR) | 463 / 463 (AR 1920: 443 / 443) | 419 / 419 |
| "Show the data" opens a Dialog | yes (Plenix default) | yes: one `dialog` role, EN and AR |

## Finding: Plenix 1.7.0 person-tile defect (blocks merging)

- **What happens:** the count and "ACTIVE CASES" are drawn beside the name, not on their own row under a divider as pds#1240 G2 specifies. The name gets squeezed to "Fr. Examp…". At 1366px in English the name runs into the count, and the unit is cut to "ACTIVE CAS".
- **Cause, measured:** the DOM is correct (`person-row`, `person-divider`, `person-body`). In plenix.css, `.plx-metric-card--tile { flex-direction: row }` comes later in the file (offset 663213) than `.plx-metric-card--person-tile { flex-direction: column }` (offset 641183). Both have the same specificity, so the tile rule wins. The computed style on the card is `display: flex; flex-direction: row`.
- **Whose:** Plenix (PDS). CTM may not add CSS. The fix goes in Plenix, for example by raising the person-tile selector's specificity or ordering it after the tile rule.

## State matrix

| Region | Loading | Empty | Error | Ready | Hidden count |
|---|---|---|---|---|---|
| Council members | LoadingState (loadingView) | EmptyState "No active council members" | Notice + Retry | MetricCard person tile in WidgetGrid sm | the word "Hidden" in the unit style (Plenix), with no unit |

The states are unchanged. Only Ready changes.

## Files

- `static/ctm/council.js`: `membersRegion` uses `WidgetGrid itemSize: "sm"` (no `columns`) and `MetricCard layout: "tile"`. The comment is updated.
- `tests/frontend/council-lists.test.cjs`: the council-members test also asserts `layout === "tile"`, `itemSize === "sm"` and no `columns`.

## Plenix doc ids used

`metric-card` (type person, layout tile), `dashboard-grid` (WidgetGrid `itemSize`), `panel`.

## String keys added

None.

## TDD evidence (Ran)

- RED: `node --test tests/frontend/council-lists.test.cjs` → 19 pass, 1 fail ("council home lists council members as person cards…").
- GREEN: `node --test tests/frontend/*.test.cjs` → 563 tests, 563 pass, 0 fail. One intermediate failure was the color-pattern rule matching "#1240" in a comment. The comment now says "issue 1240".

## Commands (Ran, this session)

- `node scripts/check_frontend_contract.cjs --base origin/main` → OK (Plenix CDN 1.7.0)
- `node scripts/check_i18n.cjs --base origin/main` → 0 problems
- `node scripts/check_ownership.cjs --slice ctm3-170-home --role ctm3-frontend-engineer` → flags only the docs files (`arabic-proposals.md` from task 1, and this report). `--slice ctm3-323-home-stats` reports that there is no design.md for that slice.
- Before/after harness `.tmp/i323b/shot.py` (not committed): the real `CouncilHome` from `council.js`, fictional data in the real response shapes, Plenix 1.7.0, 1366 and 1920, EN and AR. Before = `origin/main` council.js, after = this branch.
- Skipped: `browser_integration.py` (real API). The change is two props, and the harness renders the real component.

## Screenshots (fictional data; ci-screenshots 49b28f8)

Base: `https://raw.githubusercontent.com/LighthouseCollection/CTM/49b28f8ee1b0a3e6b56bddfbc73f1c629dd8c47f/preview-323-tiles/`

- `before-en-1366.png`, `after-en-1366.png`
- `before-ar-1366.png`, `after-ar-1366.png`
- `before-en-1920.png`, `after-en-1920.png`
- `after-en-data-dialog.png`, `after-ar-data-dialog.png`

## Scope self-check

- Only `council.js`, its test and this report changed. No backend, migrations, CSS or shared shell files.
- `ctm3-170-home/design.md` row 4 still says `WidgetGrid columns={4}`. It needs updating to `itemSize="sm"` with `layout="tile"` (owner request pds#1240). It belongs to ctm3-design-director, and I did not edit it.
- The locked screen decision (`decisions/screens.md`, 2026-11-07: "council members (person metric cards)") still holds.
