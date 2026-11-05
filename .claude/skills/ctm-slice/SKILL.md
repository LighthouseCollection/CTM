---
name: ctm-slice
description: Run the CTM SDLC for one feature, change or bug - intake, spec (G1), design (G2), contract (G3), plan (G4), build, verify (G5a-e), localize and document (G6, G7), integrate, release (G8) - using the ctm-* roles. Use when the user asks to build, finish or fix a CTM workflow slice (e.g. "/ctm-slice decree release UI").
---

# CTM slice SOP

Full lifecycle: `docs/implementation/sdlc.md`. Sources: MetaGPT (artifact
schemas), ChatDev (loop caps, lessons file), obra/superpowers (writing-plans,
subagent-driven development, verification), agency-agents (roles).

## Rules for whoever runs this (lead session or `ctm-delivery-lead`)

- **Never stop to wait for the owner.** Intent questions become a decision card
  with the recommended option applied (`ctm-product-lead`, `decisions.yaml`).
  Church law, fees, deadlines and institutional wording are never invented:
  if no source exists, the item is parked with a decision issue and the rest
  continues.
- **Subagents see nothing of this conversation.** Every dispatch carries: one
  line of context, the slice folder, files to read first, the task, contract
  paths, rulings, owned and forbidden files, review points, commands, report path.
- **Model per role:** strongest for Product Lead, Design Director, Architect,
  i18n, Release and the final review; `sonnet` for re-reviews, auditors and
  mechanical tasks.
- **A report is a claim** until `git log <BASE>..HEAD --stat`,
  `check_ownership.cjs` and the RED/GREEN evidence confirm it.
- **Concurrency from `agent-limits.yaml`** (adjustable): 4 long-work sessions, plus any number of small tasks capped at about 15 minutes each.
- Evidence is reported as **Ran / Skipped / Planned / Manual** with a path.

## Size and route

| Type / size | Route |
|---|---|
| BUG | `ctm-debugger` reproduces as a failing test -> owning engineer -> G5 gates by path |
| XS (copy, one-liner) | engineer -> fast gates -> `ctm-code-reviewer` |
| S (one control on an existing API) | engineer -> QA + code review + path gates |
| M (workflow slice) | phases 1-8 below |
| L (new domain or schema) | split into M slices, backend contract first |

## Phases

0. **Prepare.** `git fetch origin`; branch `work/<area>-<id>` from
   `origin/main`; `docs/implementation/slices/<id>/ledger.md`; baseline the
   fast gates so pre-existing failures are recorded; read `docs/lessons.md`
   and the matching `review-points.md` entries.
1. **Spec (G1)** `ctm-product-lead` -> `brief.md` (P0/P1/P2, non-goals,
   acceptance IDs, no open "Anything unclear").
2. **Design (G2)** `ctm-design-director` with `ctm-screen-shape` -> screen spec
   fitting `DESIGN.md`, template and state matrix. Pictures only if the owner asked.
3. **Contract + plan (G3, G4)** `ctm-solution-architect` -> `design.md`,
   `contract/*.json`, ADR for any new table, permission row or public API
   field; `ctm-delivery-lead` -> `plan.md` with owners, conflict pre-scan and
   merge order. Run `check_slice_trace.cjs <id>`. Builder check: a fresh
   `ctm-code-reviewer` (sonnet) lists what a builder would have to guess; every
   item gets an answer or a ruling.
4. **Build.** One engineer per area in its own worktree (database -> backend ->
   frontend; frontend may start against `contract/*.json`). Test-first
   (`ctm-tdd`). Statuses DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT;
   BLOCKED gets more context, a stronger model, a split, `ctm-debugger` or a
   design fix, never an unchanged retry. Review after each task.
5. **Verify (G5).** Sync on `origin/main` first (`ctm-release-engineer`). Then in
   parallel, read-only:

   | Gate | Role | When |
   |---|---|---|
   | G5a code | `ctm-code-reviewer` | always |
   | G5b visual | `ctm-design-critic` | `static/ctm/*`, `tribunal/templates/` |
   | G5c a11y + RTL | `ctm-a11y-rtl-auditor` | any UI change |
   | G5d behaviour | `ctm-qa-engineer` | always |
   | G5e security + privacy | `ctm-security-reviewer` | policy, auth, db, migrations, services, APIs, files, search, messages, medical, identity, payments |
   | DB review | `ctm-database-engineer` | migrations, RLS, grants |

   Fix loop: one brief per engineer listing every blocker
   (`Attempt n/limit | ID | expected | actual | evidence | files`); re-run only
   the gates that raised blockers, in re-review mode. Limits: 2 rounds for
   reviews, 3 for QA, 5 per task, then `ctm-delivery-lead` re-plans. ENV
   failures never consume a round. Minor findings go to the ledger.
6. **Localize + document (G6, G7)** `ctm-i18n-engineer` (EN/AR, proposals file)
   and `ctm-technical-writer` (messages, guides, release notes). Overlaps 4-5.
7. **Integrate.** `ctm-release-engineer`: PR with the evidence table and the
   check screenshots, `check_slice_trace.cjs <id> --require-evidence`,
   `gh pr merge --squash --auto --delete-branch`.
8. **Release (G8).** Staging on merge; production on tag: backup -> build ->
   migrate -> restart -> health check -> automatic rollback.

## Record

`ctm-drift-auditor` (sonnet) in slice mode: status entry, review points from
confirmed blockers, screen decisions, spec gaps, glossary, privacy rows,
Plenix requests. Lessons that cost a round go to `docs/lessons.md`.

## Final report (on the issue and to the owner)

Outcome first, PR link, evidence summary (Ran / Skipped / Planned / Manual),
**Rulings I made**, decisions applied (ids), deferred minors, risks carried
forward. No "done" without command output from this session.
