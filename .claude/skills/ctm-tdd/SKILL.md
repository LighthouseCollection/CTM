---
name: ctm-tdd
description: Test-first rules for CTM engineers (backend, frontend, database). Use whenever writing or changing product code, fixing a bug, or adding a fixture. Requires RED then GREEN evidence in the report and fixtures that mirror real API responses.
---

# CTM test-first rules

Adapted from obra/superpowers `test-driven-development` (MIT, (c) 2025 Jesse Vincent).

## Iron law

No production code without a failing test that demands it. If you wrote code
first, delete it and start from the test. "I'll add tests after" is how CTM got
slices that passed against fixtures and broke on the real API.

## Cycle (per behavior)

1. **RED** - write one test for one behavior. Run it. It must fail **for the
   expected reason** (assertion on the missing behavior), not an import error,
   typo or fixture crash. Copy the command and the failing line into your report.
2. **GREEN** - write the smallest code that passes. Run the test; copy the result.
3. **Whole suite** - run the full relevant suite, not just your test
   (`uv run pytest -q`, `node --test tests/frontend/*.test.cjs`). Name every
   failure in the report, including ones you believe pre-existed.
4. **Refactor** only while green. Commit.

## What a good CTM test looks like

- Name the production change that would make it fail. If none would, it tests nothing.
- Expectations are hand-derived literals (`"20261020-01"`, `"DCR-20261020-01"`),
  not values recomputed with the code under test.
- Assert behavior, not mocks. Never assert only that a mock was called.
- **Fixtures mirror the complete real response.** Build them from the slice's
  `contract/*.json` examples or a captured real response; never hand-trim
  fields or invent ones the server does not send. Send what the server requires
  (`expected_version`, CSRF, capability token).
- Each permission rule gets a forbidden-path test: other applicant, unsubmitted
  draft, unrelated council member, closed proceeding, missing medical release,
  stale actor after reassignment - whichever apply.
- Postgres-only behavior (RLS, triggers, `select_for_update`) needs a test that
  runs on PostgreSQL; on SQLite it is skipped, so mark it CI-PENDING, not PASS.
- Time: freeze or pass explicit times; cover Los Angeles midnight for numbering.
- Mutation check before you finish: break the code on purpose (flip a
  condition); the test must fail. Restore.

## Red flags - stop and restart the cycle

"Too simple to test", "I tested it manually", "the test passes immediately"
(it is not testing the new behavior), "I'll mock the API to make it pass",
editing a test's expectation to match new output without a reason from the brief.

## Report block (required)

```
TDD evidence
RED:   <command>  ->  <failing assertion line>
GREEN: <command>  ->  <N passed>
Suite: <command>  ->  <N passed, M failed (names)>
Mutation check: <what you broke> -> test failed as expected
```
