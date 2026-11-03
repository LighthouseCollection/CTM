---
name: ctm-debug
description: Root-cause debugging method for CTM. Use for any failing test, CI failure, browser-script failure, wrong data, permission bug or "works on fixture, fails on real API" problem - before proposing a fix. Stops after 3 failed fixes.
---

# CTM debugging method

Adapted from obra/superpowers `systematic-debugging` and `root-cause-tracing`
(MIT, (c) 2025 Jesse Vincent).

## Iron law

No fix without a confirmed root cause. A fix that makes the symptom go away
without an explanation is a guess, and guesses created most of CTM's rework.

## Phase 1 - Observe

- Read the whole error and stack trace. Reproduce it with one command.
- `git log --oneline -15 -- <files involved>`: what changed recently?
- **Classify the environment first.** Known environment signatures are not
  product bugs: Windows native Python crash, SQLite skipping Postgres-only
  tests, stuck `DROP DATABASE` containers, CDN unreachable / LAN resolver.
  Re-run once on Linux/CI if available; otherwise report `ENV` and stop.

## Phase 1b - Isolate Plenix vs CTM

For UI bugs, first decide whether the behavior comes from the Plenix component
itself or from CTM code around it: reproduce with the component's documented
example at the pinned version, then add CTM's props/data one at a time. A
Plenix defect goes to `plenix-requests.md`; never patch it with local CSS.

## Phase 2 - Trace across CTM's layers

Instrument each boundary until you find the first layer where data is wrong:

```
browser module (request body, headers, expected_version)
  -> URL route (ctm/urls.py) -> API view (auth, CSRF, parsing)
  -> policy check (tribunal/policy.py) -> service command (tribunal/services/)
  -> RLS context (tribunal/db/, current_setting(...)) -> SQL / trigger / policy
  -> projection / serializer -> response JSON -> browser rendering (t(), state)
```

- Fixture-vs-real mismatch: diff the fixture JSON against a real response
  (`browser_integration.py` or a pytest client call) before touching UI code.
- Permission/RLS bug: check which DB role ran the query and what actor context
  was set in that transaction; a guard trigger may refuse the runtime role.
- Walk backward from the bad value to its origin (root-cause tracing). Fix at
  the origin, then add validation at the layer that let it through.

## Phase 3 - Hypothesis

Write one sentence: "X happens because Y, shown by Z." Test it with the
smallest possible experiment. One hypothesis at a time. If wrong, return to
Phase 2 with what you learned - do not stack a second change on the first.

## Phase 4 - Fix

1. Before changing anything, write down what the change touches (records,
   notifications, outbox events, other screens) and how to roll it back.
2. Failing regression test that reproduces the root cause (follow `ctm-tdd`).
3. One fix at the origin. Test passes; whole suite passes.
4. Verify on the original case/record **and** on a second, unrelated one.

## Circuit breaker

After **3 failed fixes**, stop. The problem is probably the design or an
assumption, not the code. Report: what you tried, what each attempt showed,
and the question about the architecture/contract that must be answered.

## Parallel failures

Several independent failures (different files, different layers) may be split
across parallel agents: each gets the exact error text, the files in scope,
"change nothing outside scope", and a defined output. Afterwards check for
conflicting edits and run the whole suite once.

## Red flags

"Let me just try...", "probably a race", "add a sleep/retry", "skip this test
for now", widening a permission to make a test pass, catching and ignoring an
exception, "it's just Windows" without matching a known signature.

## Report

```
Status: ROOT CAUSE FOUND | ENV | BLOCKED
Symptom: ...
Root cause: <layer> <file:line> - explanation - evidence
Regression test: <test id> (RED output)
Fix: <file:line> or "recommended owner: backend|frontend|database"
Attempts: n/3
```
