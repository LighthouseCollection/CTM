# Code review (G5a): PR #319 and PR #315

Reviewer: ctm3-code-reviewer (#314), 2026-11-10. Mode: full (round 1).

## PR #319: CI speed budget (#314)

Head commit `f3931dd19f633a7dfbbeb6d9ad5d599045b0caee`. **Pass.**

```
SPEC: COMPLIANT    QUALITY: APPROVE
```

**Strengths**
- This change and main are served side by side, and the page loads alternate, so both sides see the same machine load.
- A missing number counts as a failure (`check_perf_budget.py:69-72, 84-86, 94-95`), so an unknown result never passes.
- The budgets and noise floors live in one file (`scripts/perf_budgets.json`).
- The fictional seeders run on a disposable database that the script creates and drops (`browser_perf_budget.py:57-69, 159-160`). The session cookies are never printed.
- The workflow uses least privilege: `permissions: {}` at the top level, `persist-credentials: false`, and `pipefail` through `shell: bash`, so the verdict's exit code reaches the job.
- Acceptance from #314 is met:
  - the check runs on every PR and on every push to main;
  - the numbers appear in the PR (sticky comment and job summary);
  - the budgets live in one config file;
  - the 6 pages are measured, with LCP, TBT (as the INP stand-in), requests and JavaScript bytes.

**Missing / Extra / Misunderstood:** none.

**Blockers:** none.

**Minor**
- [scripts/check_perf_budget.py:97] NEW: the failure message is misleading when main measured 0.
  - Main's TBT is 0 on 3 of the 6 pages. On those pages, a new 101 to 199 ms of blocking fails with "TBT new vs main", not with the size of the change.
  - Verified with synthetic inputs: 0 to 199 ms gives exit 1 and "TBT new vs main".
  - Fix: show the absolute change, for example `+199 ms`.
- [.github/workflows/performance.yml:90] NEW: the sticky-comment lookup matches any comment that starts with the marker, whoever wrote it.
  - Fix: also filter on `.user.login == "github-actions[bot]"`.
- [.github/workflows/performance.yml:55] NEW: main is measured with this change's Python environment (`uv sync` runs only on the head checkout).
  - A PR that changes `uv.lock` (for example, removes a package that main still imports) can make the main side fail to start. The job then reports "No measurements for main" and fails.
  - Fix: either note this in the job summary or run a separate `uv sync` for the base worktree.
- [.github/workflows/performance.yml:83-95] NEW: on a fork PR, `GITHUB_TOKEN` is read-only. The comment step then fails the job even when the verdict passed.
  - Fix: skip the step when `github.event.pull_request.head.repo.fork` is true.
- [scripts/perf_budgets.json:21-25] NEW: the `"manager"` account is a council **member** (`role="member"`, `browser_perf_budget.py:104-109`).
  - The secretary's or president's Home and Current session pages may be heavier.
  - Fix: rename the key to `member`. Consider measuring the secretary as well.

**Cannot verify from diff (for QA)**
- Whether the check stays free of false alarms over a week of runs before it becomes required (#314 "Manual" row).

**Declined to judge (for the lead)**
- The existing-debt rule: a page already over budget on main blocks only when it gets slower. This matches the owner's words ("fails the build when a page gets slower"), but not the literal wording of #314, D-0071 and `performance.md:90` ("fails when a page passes its budget").
  - Today, Current session's TBT is about 4.6 times its budget and still passes.
  - I accept the rule as reasonable. The docs must say it (see the #315 Minor finding).

## PR #315: performance standard, D-0065..D-0073 (#311)

Head commit `fe673f53f379f1cf9c2007effd415d8d15f3cb0a`. **Fail** (2 Important findings).

```
SPEC: NOT COMPLIANT    QUALITY: REQUEST CHANGES
```

**Strengths**
- Each of the 8 owner rules has one decision. Every `why` quotes the owner exactly.
- D-0073 is honestly recorded as an agent decision, with its options and a decision card on #311.
- Earlier decisions are kept in force: the D-0064 spinner and the server-side permission checks.
- The rule 8 exclusions explain why each one exists. For example, a prefetch of a file would record an audited view that never happened.
- No decision ID collides with the other open PRs (#130 and #162 use D-0039..D-0041). CI "Decisions have checks" is green on `fe673f5`.

**Blockers**
- [PR body, line 1] NEW: "Closes #311" would close the tracking issue before its acceptance is met.
  - Why: #311's acceptance requires every rule's implementation issue (#308, #312, #313, #314) to close with before-and-after numbers. Merging this docs PR auto-closes #311 and loses the tracker. The author flagged this on #311 but left the keyword in.
  - Fix: change the PR body to "Part of #311".
- [decisions.yaml:643-652] NEW: D-0071 credits the owner with numbers the owner never gave.
  - Why: the decision is `decided_by: owner`, but its text includes "more than 10% slower than main" and "budgets in one config file". These come from the PM's issue #314, not from the owner's words on #311 ("a check that fails the build when a page gets slower"). The team rule is "Record only what the owner actually said". Once 10% is recorded as an owner decision, tuning `max_ratio` in `scripts/perf_budgets.json` would look like it needs the owner.
  - Fix: keep D-0071 to the owner's words (LCP 2.5 s, INP 0.2 s, fails when a page gets slower). Record the 10% regression ratio, the noise floors and the existing-debt rule either as an agent decision (like D-0073) or as a clause marked `(agent, #314)`.

**Minor**
- [decisions.yaml:586] NEW: D-0065 says "immutable one-year caching", but `max-age=315360000` is 10 years (`ctm/settings.py:135`; `performance.md:21-22` states the header correctly).
  - Fix: say "immutable (max-age 315360000)".
- [docs/implementation/performance.md:89-91] NEW: rule 7 says the check fails "when a page passes its budget". PR #319 exempts pages that are already over budget on main unless they get slower.
  - Fix: add one bullet stating the existing-debt rule.
- [docs/implementation/performance.md:135, decisions.yaml D-0071 review_only] NEW: when #319 merges, D-0071 should get `check: { kind: ci-job, ... }` pointing at the "Speed budget" job.
  - `check_decisions.py` checks that the reference exists, so whichever PR merges second makes this change.

**Cannot verify from diff:** none (docs and decisions only; CI checks green).

## Evidence

| | What | Path |
|---|---|---|
| Ran | `git diff origin/main...` of both PR heads, read in full | this file |
| Ran | `check_perf_budget.py` on synthetic inputs: identical, existing debt, 0 to 199 ms TBT, 2490 to 2510 ms LCP, missing page, +10% JS. Exit codes were as expected; the message issue is listed above | scratchpad (session) |
| Ran | `gh pr checks 319` / `315`: all green; Speed budget ran on `f3931dd` (run 42866132031) | GitHub |
| Skipped | Full test suites (owned by QA; neither PR changes app code) | none |
