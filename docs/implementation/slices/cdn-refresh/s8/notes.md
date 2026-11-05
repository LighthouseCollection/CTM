# #97 slice 8 — cleanup (last slice)

| Item | Before | After |
|---|---|---|
| `static/ctm/ctm.css` | 612 lines; only `.ctm-report-party-card(s)` still used, plus overrides of `.plx-data-pill`, `.plx-form-actions` | **deleted** with its `<link>` in `shell.html`. No RTL bridge lived in it (Arabic comes from Plenix `DirectionProvider` and `dir`/`lang`), and nothing left needs a Plenix gap, so no block stayed |
| Report request spouse choice (`ReportPartySelector`) | CTM card CSS around `Checkbox` | Plenix `ChoiceList control="checkbox"` (carried over from PR #87, #48 row 18) |
| External priest report (`external-report.js`) | `Center maxWidth="md"` + hand-made header row | One-column layout (one-column-layout.md): `AppShell page="form"` with an `AppHeader` (tribunal name, language switch) and `PageContent`; the form keeps the form-flow parts (Form, Field, FormActions, primary last). `FormFlow` itself is not used: PLX-018, PLX-020. The link handling is unchanged (D-0033) |
| Case numbers in Arabic | undocumented Plenix `kind: "id"` laid `DEMO-NEW-09` out as `٠٩-NEW-DEMO` and `20261020-04` right to left | tables: documented `kind: "data"` (Latin digits, LTR); PropertyList values: `data` + `<bdi dir="ltr">` (PLX-023) |
| Cache stamps | 17 scripts had none; several stale | every `static/ctm` script `?v=ctm97s8-20261105` (test in app-shell-templates) |
| `plenix-requests.md` | ids already unique on main (slice 2 had renumbered to PLX-021/022) | test keeps them unique; workaround comments now name their id (PLX-015, 018, 021, 022) |
| `scripts/browser_login_branding.py` | `.plx-panel` | `.plx-auth__card`; provider stub matches `"providers": []`; centering asserted from 600px up (the phone header is in flow by design) |

Older #48 PRs: #83 was already merged; #87 (part 4) is superseded except the ChoiceList change above.

Screenshots (CTM 2.0 demo data, port 8028, desktop 1440×900, read-only: every non-GET call aborted): `before-*` / `after-*` in this folder. The external page was shown with a stubbed demo request (no real link or token).

**Density (CTM#113, owner "it feels smaller than the cdn tab"):** `shell.html` and `external-report.html` set `data-plx-density-policy="compact"` app-wide (CTM 2.0, never a recorded decision). Removed, so CTM renders at the CDN default (density.md: standard when unset). DataGrid keeps its own compact rows (its default, owner 2026-10-22); the account menu's density choice is unchanged. `before-*` shots of the case summary, report maker, users settings and applicant home show compact; `after-*` standard.

Report maker: the spouse `ChoiceList` legend is the visible name and the `Field` label is screen-reader only, so the name is not drawn twice; the required star now shows only for screen readers on that one field.
