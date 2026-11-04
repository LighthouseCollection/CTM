# CTM review points

A defect checklist built from CTM's own history. The team lead pastes the
points whose path tags match a slice into every brief. Reviewers cite a point id
(or `NEW`) for each finding. `ctm-drift-auditor` adds at most 3 points per
slice from confirmed blockers, bumps `hits` when a point catches something, and
proposes pruning points with no hits over many slices.

| Id | Rule | Path tags | Bad (from history) | Good | Hits |
|---|---|---|---|---|---|
| RP-MRG-01 | After resolving a shared-file conflict, every control/route/handler from both sides still exists | `static/ctm/council*.js`, `app.js`, `routes.js`, `api.py`, `urls.py` | Merge `83f5ebf` dropped C-05 priest-link controls; `b89e9d0` restored 382 lines | Grep the hotspot change-plan anchors after the merge | 0 |
| RP-MIG-01 | Every `RunSQL` has `reverse_sql`; every `RunPython` has `reverse_code` | `tribunal/migrations/` | `0057_admin_case_purge` irreversible | `check_migration_diff.cjs` passes | 0 |
| RP-MIG-02 | No demo/seed data in schema migrations | `tribunal/migrations/` | `0054_fictitious_demo_case`, `0061`-`0063` demo migrations | Gated `seed_demo` management command | 0 |
| RP-MIG-03 | Changing a guard trigger never weakens history protection | `tribunal/migrations/`, `tribunal/db/` | `0057` guard changed to `RETURN OLD`; restored later (`732ca05`, `c218b98`) | DB engineer review + test that history rows are still immutable | 0 |
| RP-RLS-01 | A guard trigger must not refuse a write that a runtime-role service needs | `tribunal/migrations/`, `tribunal/services/`, `auth.py` | First Microsoft sign-in wrote `microsoft_subject` as `ctm_app` and the core guard refused it (`6ad441c`) | List every service writing the table; Postgres test per service as the runtime role | 0 |
| RP-OWN-01 | UI streams never edit migrations, RLS, grants or services | `tribunal/migrations/`, `tribunal/db/`, `tribunal/services/`, `policy.py` | UI reconciliation stream added `0057` and the demo migrations | `check_ownership.cjs` passes; request backend changes on the backend issue | 0 |
| RP-API-01 | Frontend sends everything the server requires and reads only fields the server returns | `static/ctm/`, `scripts/council_fixture.cjs` | Editor sent no `expected_version`; five council fixes after real-API runs (`87f094f`, `65fa389`, `381701d`, `be9f738`, `0133b9d`) | Fixtures from `contract/*.json`; real-API browser check | 0 |
| RP-UI-01 | Unsaved edits survive in-app navigation or warn before leaving | `static/ctm/` editors | QA-01 run 2: navigation dropped unsaved text | Dirty-state guard + test | 0 |
| RP-UI-02 | Screen decisions are not toggled without a new dated owner decision | `static/ctm/` | Case-search icon changed 5x; spouse layout 2-col -> stacked -> 2-col | Check `decisions/screens.md` | 0 |
| RP-CDN-01 | Every Plenix CDN reference uses the `PLENIX_BASE` version | `static/ctm/`, `tribunal/templates/`, `scripts/`, `tests/` | `external-report.html` on 0.60.1 and 12 browser scripts on 0.61.0 while the shell used 0.68.0 | `check_frontend_contract.cjs` passes | 0 |
| RP-CSS-01 | No raw colors, `!important`, numeric font sizes or inline styles | `static/ctm/` | `ctm.css` holds ~50 hex colors and 5 `!important` (`dd5a08c` "Force transparent card form actions") | Plenix components/tokens; report missing ones | 0 |
| RP-I18N-01 | Every `en` key exists in `ar` | `static/ctm/*.js` | `app.js` has `calls`, `backNewApplications` only in English | Key-parity check | 0 |
| RP-I18N-02 | Read Arabic/bilingual data files as UTF-8 | `tribunal/`, `scripts/` | Arabic taxonomy read without UTF-8 (`c2ff46b`) | `encoding="utf-8"` everywhere | 0 |
| RP-PERM-01 | Authority changes are checked against the permission matrix rows | `tribunal/policy.py`, `services/`, roster UI | Roster restriction dropped F15 assignment authorities (`3721917` -> `3570995`) | Test per role for the action | 0 |
| RP-ENV-01 | Windows native Python crashes are ENV, not product failures | any | Hours lost re-running crashing local suites | Classify ENV, run on Linux/CI | 0 |
