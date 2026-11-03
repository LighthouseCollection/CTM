---
name: ctm-slice
description: Run the CTM team SOP for one feature slice or bug - triage, brief, design, builder check, build, sync, gates, publish, record - using the ctm-* subagents. Use when the user asks to build, finish or fix a CTM workflow slice (e.g. "/ctm-slice decree release UI").
---

# CTM slice SOP (team lead)

You plan, delegate, verify and decide; specialists do the work. Sources:
MetaGPT (SOP artifacts), ChatDev (bounded phase loops), obra/superpowers
(subagent-driven development, verification), agency-agents NEXUS (handoff
templates). Rationale: `docs/implementation/agent-team.md`.

## Rules for you

- **Subagents see nothing of this conversation.** Every dispatch contains: one
  line of slice context, the slice folder path and which files to read first,
  the task number, the interfaces/contract paths, your rulings on ambiguities,
  owned files and forbidden files, the matching review points, the commands to
  run, and the report path. Never paste conversation history.
- **Name the model** on every dispatch: strongest for architect and the round-1
  code/security review; `sonnet` for re-reviews, i18n, drift auditor and
  mechanical tasks.
- **A report is a claim.** Before believing DONE: `git log <BASE>..HEAD --stat`,
  `node scripts/check_ownership.cjs --slice <id> --role <role>`, and the RED/GREEN
  block present. "Agent said success" is not evidence.
- Never tell a reviewer what not to flag. Never re-dispatch a failed task unchanged.
- Policy, church-law, fee, wording or permission questions always go to the
  user. Technical ambiguities you may rule on; record each Ruling.

## 0. Prepare

1. `git fetch origin`. Work on a stream branch, never `main`
   (`git switch -c work/<stream>-<slice-id> origin/main`, then
   `git branch --unset-upstream`). Tree must be clean.
2. Create `docs/implementation/slices/<id>/ledger.md`. Append one line per event:
   `Step N: <agent> <status> (commits a..b)`, `Ruling: <decision> - <why> - <cost if wrong>`,
   `Minor (deferred): ...`, `Risk carried forward: ...`. After context
   compaction, trust the ledger and `git log`, not memory.
3. Baseline: run the fast gates (`check_frontend_contract`, `check_migration_diff`,
   `node --test`, `uv run pytest -q`). Ledger pre-existing failures so later
   failures are not ambiguous.
4. Collect review points: entries in `docs/implementation/review-points.md`
   whose path tags match the slice's likely paths. Paste them into every brief.

## 1. Triage and size

| Type / size | Route |
|---|---|
| BUG | `ctm-debugger` (or owning engineer if cause is obvious) reproduces as failing test -> fix -> qa + code-reviewer (+ path gates) |
| XS (copy, one-liner) | engineer -> fast gates -> code-reviewer |
| S (one control on existing API) | engineer -> qa + code-reviewer + path gates |
| M (workflow slice) | full SOP |
| L (new domain / schema) | split into M slices, backend contract first, run sequentially |
| CHANGE to an existing slice | reuse that slice folder; analyst updates brief, architect updates design |

## 2. Brief (M/L)

Dispatch `ctm-spec-analyst`. If its question table has BLOCKING items, ask the
user once, all questions together, then continue. NON-BLOCKING items proceed on
their stated default assumption.

## 2.5 Screens (UI slices)

The brief's screen spec comes from `ctm-screen-shape` and names a Plenix page
template from `docs/implementation/plenix-page-templates.md`. If it lists
`OWNER-Q` items, run `ctm-owner-interview` here, in the main session, before
design: one screen at a time, answers recorded as dated rows in
`decisions/screens.md`. Never let a builder decide an owner question.

## 3. Design (M/L)

Dispatch `ctm-solution-architect`. Then run
`node scripts/check_slice_trace.cjs <id>` and confirm: an `owners` block where
every shared file has exactly one owner; `contract/*.json` examples for every
new/changed endpoint; tasks with Interfaces and RED/GREEN steps.

## 3.5 Builder check

Dispatch a fresh read-only agent (`ctm-code-reviewer`, model sonnet): "You are
the engineer who must build this from brief.md + design.md and cannot ask the
architect. List only questions where a wrong guess would cause rework, ranked."
Sort answers: answered by docs / your technical Ruling / user's question. Fix
design gaps with the architect before building.

## 4. Build

- Record `BASE=$(git rev-parse HEAD)` in the ledger.
- Builders whose `owners` globs do not overlap run **in parallel, each in its
  own worktree** (Agent tool `isolation: "worktree"`). Never two writers in one
  checkout. Overlapping owners run sequentially.
- Order when there is a dependency: database (migrations/RLS) -> backend ->
  frontend; frontend may start in parallel against `contract/*.json`.
- Handle each returned status:
  - DONE -> verify (rules above), then merge the worktree branch into the
    slice branch one at a time, running fast gates after each merge.
  - DONE_WITH_CONCERNS -> read concerns; correctness/scope concerns are fixed
    before gates.
  - NEEDS_CONTEXT -> answer and re-dispatch with the answer in the brief.
  - BLOCKED -> one of: more context, stronger model, split the task,
    `ctm-debugger`, or a design fix by the architect. Never retry unchanged.
- Do not start gates while a report lists `Remaining TODOs` or unreviewed
  `Assumptions not in design.md`.

## 4.5 Sync before gates

Dispatch `ctm-integrator` in **sync mode**: rebase on `origin/main`, resolve
conflicts preserving both sides, run fast gates. Gates must review the code that
will actually ship.

## 5. Gates

Always: `ctm-qa-engineer` and `ctm-code-reviewer`. Add by changed paths
(`git diff --name-only origin/main...HEAD`):

| Changed paths | Add gate |
|---|---|
| `tribunal/policy.py`, `auth.py`, `db/`, `migrations/`, `services/`, `*_api.py`, `api.py`, `file_delivery.py`, settings, anything on files/search/messages/medical/identity/payments | `ctm-security-reviewer` |
| any `en:`/`ar:` dictionary, template, PDF, email text, question/declaration data | `ctm-i18n-rtl-reviewer` |
| `static/ctm/*`, `tribunal/templates/` | `ctm-ui-finish-gate` |
| `tribunal/migrations/`, RLS, grants | `ctm-database-engineer` in review mode |
| `tribunal/services/payments.py`, Stripe webhook, fees, waivers | `ctm-security-reviewer` in payments mode (`ctm-payments` skill) |
| media/OCR/transcription workers | `ctm-media-pipeline-engineer` in review mode |

Launch them in one message (read-only, parallel).

**Fix loop** (no gate verdict without command output; otherwise treat as UNVERIFIED):

1. Send all blockers in one QA-FAIL brief per owning engineer:
   `Attempt n/limit | ID | expected | actual | evidence | files to modify`.
   The engineer changes only the listed issues and runs the Scope Self-Check.
2. Re-run **only** the gates that raised blockers or whose paths changed, in
   **re-review mode**: each prior finding ADDRESSED / NOT ADDRESSED + new
   breakage on changed lines only. Do not restart full reviews.
3. Limits: review gates 2 rounds, QA test-fix 3 rounds. Resume the same engineer
   (SendMessage) for rounds 1-2; round 3 uses a fresh engineer on a stronger
   model or `ctm-debugger`.
4. No-progress rule: a finding NOT ADDRESSED with no change to its file ->
   escalate immediately. At attempt 2 ask: wrong agent or wrong approach?
5. ENV failures (see `ctm-debug`) never consume a round; mark CI-PENDING.
6. Minor findings go to the ledger as deferred, never into the loop.
7. Escalation after the limit, choose and ledger one: reassign, split, revise
   the design, accept with a documented limitation (user approval), or defer.

## 6. Publish

Dispatch `ctm-integrator` in **publish mode**: if `origin/main` moved and
touched slice files, sync again and re-run QA in integrated mode; push the
branch; open/update the draft PR with the evidence table, risks carried
forward and shared files touched. Run `node scripts/check_slice_trace.cjs <id> --require-evidence`.

## 7. Record

Dispatch `ctm-drift-auditor` (sonnet) in **slice mode**: status entry, issue
comment draft, up to 3 new review points from confirmed blockers (+ hit counts),
screen decisions, spec gaps, glossary terms, privacy data map rows and Plenix
requests touched. Post issue comments only if the user
approved posting for this stream.

## Final report to the user

Outcome first (done / partly / blocked), PR link, evidence summary (PASS /
FAIL / UNVERIFIED / CI-PENDING counts), **Rulings I made** (all, from the
ledger), deferred minors, risks carried forward, blockers with owners, next slice.
No "done" without the command output that proves it in this session.
