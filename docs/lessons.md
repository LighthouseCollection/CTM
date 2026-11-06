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
| L-11 | Two engineers built the same issue; one finished PR was thrown away (template A-01) | Claim before building: comment "claiming" and check for an open PR that mentions the issue; the first claim wins |
| L-12 | A required check was blocked by its own cancelled run (template A-02) | Required checks never use `cancel-in-progress` |
| L-13 | The owner was re-asked after each answer and each answer ran as its own chain (template A-10) | The owner's answer is final: act on the sensible reading, say it in one line, handle all answers in one pass |
| L-14 | The owner pointed at a working example and a different one was built (template A-11) | When the owner points at a working example, ship that example first, then improve it |
| L-15 | A queued PR's branch is locked; a "pushed" report was wrong (template A-12) | Check the push result before reporting; dequeue first, push, then re-queue |
| L-16 | A PR merged with an open gate change because the label arrived after it entered the queue (template A-13) | Before adding a "changes requested" label, look at the merge queue and dequeue the PR if it is there |
| L-17 | Settings quoted in prose drift from the config (template A-16) | Settings live only in the registry file; documents name the setting, never its value |
| L-18 | 2026-11-06: the Plenix upgrade PR opened with `GITHUB_TOKEN` had its checks held and its merge started no deploy (template A-17) | Events caused by `GITHUB_TOKEN` start no workflows except `workflow_dispatch` / `repository_dispatch`; hand-offs use an App token or end in an explicit dispatch (#148) |
| L-19 | 2026-11-06: the first live deploy was refused because the `production` environment allowed only `v*.*.*` tags | When a deploy trigger changes, update the environment's allowed branches/tags in the same change |
