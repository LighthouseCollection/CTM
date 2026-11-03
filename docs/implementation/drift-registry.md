# Drift registry

Places where code, pins, docs or streams disagree. Never delete an entry: close
it as Fixed (both sides checked) or Won't Fix (with reason). Maintained by
`ctm-drift-auditor`.

| Id | Finding | Side A | Side B | Risk | Owner | Status |
|---|---|---|---|---|---|---|
| DR-001 | Plenix CDN pins differ | `ctm/settings.py` `PLENIX_BASE` 0.68.0 (main `9fa6386`) | `static/ctm/external-report.html` 0.60.1; 12 `scripts/browser_applicant*.py` 0.61.0; `scripts/browser_table_065.py` 0.65.0 | External priest form renders with an older design system; browser checks test the wrong version | council frontend / platform | Open |
| DR-002 | Docs name an old CDN pin | `PLENIX_BASE` 0.68.0 | `CLAUDE-START-HERE.md`, `parallel-build-handoff.md`, `stream-*.md` say 0.58.0 | New sessions follow stale instructions (CLAUDE.md now overrides) | governance | Open |
| DR-003 | Application CSS breaks the Plenix rule | Rule: no raw colors / `!important` | `static/ctm/ctm.css`: ~50 hex colors, 5 `!important` | Visual drift, CDN upgrades break overrides | council frontend | Open |
| DR-004 | Forced-RLS table counts disagree across docs | Count computed from migrations (not yet generated) | Docs quote 23 / 49 / 50 / 55 / 56 / 63 | Wrong security status reported | database | Open |
| DR-005 | Missing Arabic keys | `app.js` `en` dictionary | `app.js` `ar` lacks `calls`, `backNewApplications` | English text in Arabic UI | shell owner | Open |
| DR-006 | CDN upgrade branches ahead of main | main 0.68.0 | `origin/verify/cdn-0.72-on-27` pins 0.72.0 | Pins move again; run the contract gate on that branch | governance | Open |
