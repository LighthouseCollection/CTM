# Frontend task 3 (issue 323): verify on Plenix 1.8.0, ready for review

Branch rebased onto `main` (Plenix CDN 1.8.0). The two earlier commits and the task 2 report are unchanged.

## Verified (Ran, this session)

A throwaway page (not committed) rendered the real `CouncilHome` from `council.js` on the live Plenix 1.8.0 CDN, fictional data, 1366px wide, desktop only.

| Check | EN | AR |
|---|---|---|
| Person tile `flex-direction` | column (the 1.7.0 defect is gone) | column |
| Tiles in one row | 6 (210px each) | 6 |
| Count on its own row under the name, unit visible, names not cut | yes | name and count yes; the unit is missing (see below) |
| "Cases per member" and "Cases by reason" card heights | 419px and 419px | 419px and 419px |

## Open, not caused by this change

In Arabic the tile shows the count in the unit style and drops the unit "قضايا نشطة". CTM passes the count as a formatted string (Arabic digits); Plenix 1.8.0 MetricCard treats a non-numeric string as a text value. Passing a plain number shows the unit but with Western digits, and MetricCard has no `format` prop. `main` behaves the same for this card. Needs a Plenix fix (MetricCard person: locale-formatted numbers), requested through the PM.

## Commands (Ran)

- `node --test tests/frontend/*.test.cjs`: 576 pass, 0 fail
- `node scripts/check_frontend_contract.cjs --base origin/main`: OK (1.8.0)
- `node scripts/check_i18n.cjs --base origin/main`: 0 problems
- Skipped: pytest and `browser_cdn_smoke.py` (no `uv` on this host); CI runs them.
