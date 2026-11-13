# Issue 323, frontend task 1: Home statistics cards the same height

Role: ctm3-frontend-engineer (CTM3 · Frontend Engineer #323). Branch `agent/frontend-engineer-323`. Plenix CDN 1.6.1.

## Layout statement

- Template: the Home dashboard region 5 (design `ctm3-170-home/design.md` row 5). Plenix `WidgetGrid columns={2}`, each cell a `Panel` with a year `Select` in its actions and an "All statistics" footer. Nothing about the template changes.
- What leads: each chart. The bar chart (Cases per member) has no legend. The donut (Cases by reason) now has its legend beside the ring (`legendPosition="end"`), not under it.
- Density: unchanged. Both plots stay ChartFrame size `md`.

## Cause (posted on the issue)

| Symptom | Cause | Owner |
|---|---|---|
| The donut card was 44px taller (455 vs 411, EN and AR, 1280px wide) | CTM props: the bar chart has `legend: false`, the donut used the default `legendPosition: "bottom"`, so only the donut had a legend row (two rows at this width) under its plot | CTM, fixed here |
| The shorter card does not fill its grid cell, so the footers do not line up whenever the content heights differ | Plenix: `.plx-widget-grid__item` stretches to the row, but the `Panel` inside keeps its content height (no fill, and the body does not grow to push the footer down) | Plenix (PDS) |
| "Show the data" opens a table inside the card | Plenix default: ChartFrame always renders the table in an inline `Details` (chart-foundations.md `table`). BarChart and PieChart always pass a table. No prop turns it off or opens it in a Dialog | Plenix (PDS) |
| "Show the data" was English in Arabic | CTM props: CTM did not pass the ChartFrame strings `showData` and `table` | CTM, fixed here |
| Arabic bar chart: the value labels run into the member names | Plenix BarChart RTL placement | Plenix (PDS) |

## State matrix

| Region | Loading | Empty | All hidden | Error | Ready |
|---|---|---|---|---|---|
| Cases per member | LoadingState (loadingView) | EmptyState | EmptyState | Notice + Retry | BarChart in Panel |
| Cases by reason | LoadingState (loadingView) | EmptyState | EmptyState | Notice + Retry | PieChart (legend end) in Panel |

Unchanged states. The only change is the Ready state.

## Files

- `static/ctm/council.js`: `HomeStatChart` passes `legendPosition: "end"` to the PieChart and ChartFrame's `showData` and `table` strings to both charts. Two new keys in `en` and `ar`.
- `tests/frontend/council-lists.test.cjs`: new test "home statistics: the donut legend sits beside it and the chart data words are translated".
- `docs/i18n/arabic-proposals.md`: one row for the two keys (D-0012).

## Plenix doc ids used

`pie-chart`, `bar-chart`, `chart-foundations` (ChartFrame `legendPosition`, `table`, `strings`), `dashboard-grid`, `panel`.

## String keys added (EN/AR parity confirmed by the test and `check_i18n.cjs`)

- `statsShowData`: "Show the data" / "عرض البيانات"
- `statsDataTable`: "{title}: data" / "{title}: البيانات" (Plenix fills in `{title}`)

## TDD evidence

- Ran: the new test with the `council.js` change set aside failed (`not ok 20`, AssertionError, 19 pass 1 fail). With the change it passed (20 pass).
- Ran: `node --test tests/frontend/*.test.cjs`: 563 tests, 563 pass, 0 fail.

## Commands

- Ran: `node scripts/check_frontend_contract.cjs --base origin/main`: OK (Plenix CDN 1.6.1).
- Ran: `node scripts/check_i18n.cjs --base origin/main`: 0 problems, 0 new.
- Ran: `node scripts/check_ownership.cjs`: OK.
- Ran: `.tmp/i323/shot.py` (Playwright on a scratch page that renders the real `HomeStatChart` from `council.js` in the same `WidgetGrid` as `statsRegion`, fictional data in the `/api/statistics/summary/` shape). Before: panel heights [411, 455] in EN and AR. After: [411, 411] in EN and AR.
- Skipped: `browser_integration.py`. Its fixture has fewer than 5 cases per cell, so every count is hidden and no chart draws.
- Cache marker: not bumped. Static files use `CompressedManifestStaticFilesStorage` (hashed names).

## Screenshots (fictional data)

`ci-screenshots` branch, `preview-323/`: `before-en.png`, `before-ar.png`, `before-*-expanded.png`, `after-en.png`, `after-ar.png`, `after-*-expanded.png`.

## Scope self-check

- Only CTM-owned props changed. No custom CSS, inline style, className or Plenix lookalike.
- Not done, because it is Plenix (already sent to PDS by the PM): the data in a Dialog from a link, a Panel that fills its WidgetGrid cell, and the RTL bar value labels. The acceptance criterion "nothing expands inside the card" stays open until Plenix ships it.
- The duplicate member names in the owner's picture are live data (#299), out of scope.
