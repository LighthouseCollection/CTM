# CTM lessons

Loaded at the start of every agent session (SessionStart hook). One line per
lesson that cost real rework, with the rule that prevents it. Add a lesson when
a mistake cost a review round, a failed deploy or a reverted merge.

| Id | What went wrong | Rule now |
|---|---|---|
| L-01 | A late, large merge silently dropped controls (`b89e9d0`) | Integrate small and often; before resolving a shared file, list what each side added, and grep both survived |
| L-02 | Plenix CDN pins drifted across files (0.58 / 0.60 / 0.61 / 0.65 / 0.68) | One command moves every pin (`bump_plenix.cjs`); `--verify` checks every CDN file exists |
| L-03 | UI layouts and icons flip-flopped because owner choices were never written down | Every choice is a decision in `decisions.yaml` + `decisions/screens.md`; an unrecorded reversal fails G5b |
| L-04 | Test fixtures were hand-trimmed and hid missing fields | Fixtures come from or are checked against `contract/*.json` |
| L-05 | Agent reports said DONE without proof | A report is a claim until `git log`, the diff and the checks confirm it |
| L-06 | Plenix 0.86 removed `icons-all.css`; string-only tests missed it | Upgrades fetch every referenced CDN file before merging |
| L-07 | `check \| tee log` under `bash -e` hid failures, so a broken upgrade nearly merged | Workflows use `shell: bash` (pipefail); a second guard re-verifies before commit |
| L-08 | The SQLite test pass cannot build CTM's database (PostgreSQL-only SQL); `browser_smoke.py` fell out of date with no CI job running it | Shell and backend tests run on PostgreSQL; every browser script that gates anything runs in CI (DR-009) |
| L-09 | `main` had no branch protection and stayed red for weeks | Required checks on `main`; red `main` is an S1 bug |
| L-10 | Two agent teams worked on CTM with different rules (one merging, one waiting for taps) | One team, one rulebook (`CLAUDE.md`, `decisions.yaml`); GitHub is the only channel |
