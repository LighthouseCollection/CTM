# CTM agent team — analysis and design

Date: 2026-11-03. Branch: `work/claude-agent-team`.

This document explains the Claude Code agent team in `.claude/agents/`, the SOP
in `CLAUDE.md` and `.claude/skills/ctm-slice/`, and the deterministic gates in
`scripts/check_*.cjs`. It covers four sources (MetaGPT, ChatDev, obra/superpowers,
the full agency-agents catalog) and evidence from how CTM 2.0 was actually built.

## 1. What CTM 2.0's history says (the problem to solve)

Measured from git across all refs (610 commits, 93% in about 36 hours on 10-21/22):

| # | Bottleneck | Evidence | Cost driver |
|---|---|---|---|
| 1 | Long-lived streams, then one huge merge | PR #26 brought ~540 commits into main. 32 "Integrate X" commits re-applied stream work. Duplicate migration numbers 0040/0042/0043/0044 needed merge migrations. `b89e9d0` restored 382 lines of C-05 controls lost in merge `83f5ebf`. 13 hand-refreshed `shell-integration.patch` commits. QA-01 ran four times because main moved. | Lost work, re-verification |
| 2 | Ownership broken: UI stream changed migrations, RLS and services | `0057_admin_case_purge` weakened history guards and had no reverse (fixed by `732ca05`, `c218b98`). First Microsoft sign-in could never succeed under RLS (`6ad441c`, fix `e32cc31` on hold). Demo data shipped as migrations 0054–0063. Roster/F15 authority regression `3721917` → `3570995`. | Regressions found after release |
| 3 | Shared-file hotspots and manual cache-busting | `shell.html` changed 161 times; 133 of those only touched `?v=` markers. `council-case.js` (4,252 lines), `council.js` (3,160), `council-media.js` (2,262) and `app.js` (2,028) are each edited by several streams. | Merge conflicts |
| 4 | Plenix CDN churn with scattered pins | Seven pins in nine days (0.58 → 0.60.1 → 0.61 → 0.65 → 0.68 → 0.70/0.72 → 0.75/0.76). Breaking renames (`headerSort` → `sortable`). On main today: shell 0.68.0, `external-report.html` 0.60.1, 12 applicant browser scripts 0.61.0. | Silent breakage |
| 5 | Synthetic fixture drift | Council slices passed on `council_fixture.cjs` and broke on the real API (`87f094f`, `65fa389`, `381701d`, `be9f738`, `0133b9d`). The editor sent no `expected_version`. 34 browser scripts, most with their own launcher, none in CI. | Rework after "done" |
| 6 | Visual flip-flops and design-rule violations | 34 icon commits and 17 pill commits in one day. Case-search icon changed 5×, spouse layout 2-col → stacked → 2-col. `static/ctm/ctm.css` has 46 raw hex colors and 5 `!important`. | Churn |
| 7 | Unreliable local validation | Windows native Python crashes. SQLite skips 41–42 Postgres-only tests. Stuck `DROP DATABASE` containers. | Wasted hours |
| 8 | Spec gap managed in prose | 151 planned tables vs about 63 models (3 implemented, 110 partial, 37 missing). Forced-RLS counts quoted as 23/49/50/55/56/63 in different docs. F01–F36 findings (9 × P0). 344 files in `docs/implementation/`. | Re-reading, stale status |

**Conclusion.** CTM was not slow because it lacked roles that write code. Three engineering streams wrote ~550 commits in 36 hours. It was slow because nothing caught problems early:

- Requirements and screen decisions weren't fixed before coding.
- Each stream's file ownership wasn't enforced.
- Integration didn't happen continuously.
- Cheap mechanical checks (CDN pin, styling, migration safety) weren't automated.
- Real-API verification wasn't run before calling work done.

The new team is designed around those gaps.

## 2. MetaGPT: what to take

MetaGPT's core idea is `Code = SOP(Team)`. Roles subscribe (`_watch`) to the typed outputs of earlier roles:

```
UserRequirement → ProductManager.WritePRD → Architect.WriteDesign
→ ProjectManager.WriteTasks → Engineer.WriteCode (+review) → SummarizeCode
→ IS_PASS? → QaEngineer (WriteTest/RunCode/DebugError, ≤5 rounds) or FixBug
```

| MetaGPT mechanism | Why it matters | CTM adoption |
|---|---|---|
| Structured artifacts per step (ActionNode schemas: PRD goals/user stories/requirement pool/"Anything UNCLEAR"; design: approach, file list, mermaid class and sequence diagrams; tasks: logic analysis, dependency-ordered task list, full API spec, shared knowledge) | The next role reads a fixed-shape document instead of chat history | `brief.md` → `design.md` → `evidence.md` per slice in `docs/implementation/slices/<id>/`. Every one has an "Anything unclear" section. |
| Team leader rule: "you are their sole info source; don't omit path, environment, constraints" | Subagents start with no context | Written into the `ctm-slice` skill and `CLAUDE.md` |
| T-shirt sizing; XS/S skip the full SOP | Process cost should match task size | XS/S/M/L routing table |
| "Assign an aggregated task, don't feed one member consecutive micro-tasks" | Less coordination overhead | One brief per engineer per slice |
| Incremental "Refined" nodes (merge legacy + new) | CTM is brownfield | Analyst lists "Already implemented"; architect extends existing modules |
| Bounded QA rounds (`test_round_allowed = 5`) | Prevents infinite fix loops | Max 3 gate/fix rounds, then escalate to the user |
| Engineer's `IS_PASS` summary gate before QA | Self-check before an expensive review | Engineers run the fast gates before reporting |
| Project Manager "Full API spec" shared by frontend and backend | Lets two builders work in parallel | Architect's API contract in `design.md`; frontend builds against it, never against mocks |

What I left out:

- Its defaults (Vite/React/MUI/Tailwind, greenfield file-per-task, generated competitive analysis) conflict with CTM's fixed stack and Plenix rule.
- It has no roles for security, privacy, i18n, database isolation or integration. Those are exactly CTM's failure areas, so they come from agency-agents and the history evidence.
- Its pub/sub message pool isn't needed. In Claude Code the main session is the team lead and passes artifact paths.

## 3. agency-agents: what to take (18 files reviewed)

| File | Fit | Kept | Dropped |
|---|---|---|---|
| identity-access-engineer | High | RLS block (FORCE, transaction-local `set_config(...,true)`, no BYPASSRLS, missing context denies). OIDC callback checklist. "Client is never the authority". Account linking on verified email. Failure paths first. | SAML, SCIM, passkeys, passwords/MFA reset |
| i18n-engineer | High | No concatenated fragments. Arabic six plural forms. `Intl` dates, and civil dates never time-zone shifted. `dir="auto"` isolation for names and ids. Key parity. Server-side i18n for PDF and email. | Custom RTL CSS (Plenix + `dir` only), TMS, CJK |
| ui-finish-gate-reviewer | High | Binary PASS/HOLD. Evidence before opinion. Ordered audit (fit → hierarchy → pattern → states → responsive → fidelity). Every required fix verifiable by state and viewport. | External reference catalogue, SaaS taste lens |
| code-reviewer | High | Blocker/suggestion/nit tiers, location/why/fix format, one complete review | "Suggest, don't demand" (it is a gate here) |
| software-architect | High | Modular monolith, trade-offs, reversible decisions, "always two options", dependency direction | Hexagonal/onion |
| database-optimizer | High | EXPLAIN before shipping, index FKs, reversible migrations, `CONCURRENTLY`, no N+1 | Supabase/PlanetScale examples |
| multi-agent-systems-architect | High (as a design guide) | Role template (receives / responsible / **not responsible** / produces / failure behavior / tools), least-privilege tool matrix, evaluator ≠ generator, ≤3 iterations, human gates for irreversible actions | Runtime-pipeline material (cost, vector DBs, circuit breakers) |
| git-workflow-master | High (as rules) | Branch from latest main, worktrees per parallel stream, never force-push shared branches, safe commands | `rebase -i` (non-interactive only) |
| backend-architect | Medium | API contract governance, expand/contract migrations, timeouts/retries/idempotency for external calls, stable error codes | Microservices, K8s, `password_hash`, invented SLAs |
| frontend-developer | Medium | Accessibility, error/feedback states, e2e for critical flows | Tailwind, styling choice, editor-integration noise |
| devops-automator | Medium-low | Gated pipeline order, secrets, rollback, "missing telemetry = unknown" | K8s, Terraform, cloud cost |
| technical-writer | Low-medium | Docs in the same PR, runnable commands, write allow-list | Docusaurus, marketing |
| ui-designer | Low | Component state checklist, contrast/keyboard/44px targets | All CSS and hex tokens (they push agents toward violations) |
| ux-architect | Low | IA and heading hierarchy, implementation handoff | CSS architecture, theme toggle, marketing pages |
| platform-engineer | Low | "One command per common task", "pick one, write an ADR" | Backstage, IDP, DORA |
| data-engineer | None as a role | Idempotent tasks, schema contracts, audit columns | Spark, Kafka, lakehouse |
| senior-developer | None | "Check the pinned library's docs", "no unrequested features" | Laravel, Three.js, glass effects |
| webassembly-engineer | None | "Benchmark before adopting" | Everything else (no Wasm workload) |

**What makes the good files work.** They have numbered rules you can check against a diff, a "when NOT to" table, an output template with a verdict, failure paths before the happy path, and code snippets only where they carry correctness.

**What makes the bad files fail.** Persona and "memory" sections, invented metrics, and large generic CSS or infra code that primes the agent toward the wrong stack. An agent shown hex tokens will write hex tokens. The CTM agent files follow the good pattern: responsible / not responsible / rules / workflow / short report. No persona, no metrics.

## 4. Second review: superpowers, full agency-agents catalog, ChatDev

A second pass read all four sources in full: obra/superpowers v7.0.1 (MIT), all
279 agency-agents files plus the NEXUS orchestration docs, the rest of MetaGPT
(review loops, incremental mode, experience pool, RoleZero safeguards) and
ChatDev 1.0 and 2.0 (roles, phase chain, loop limits, experiential
co-learning). The roster barely changed. The **protocol** changed a lot.

### What each source added

| Source | Mechanism adopted | Where it lives now |
|---|---|---|
| superpowers: subagent-driven-development | Status protocol DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT and how to handle each. Dispatch recipe (paths, not history). "Do not trust the report". Scoped re-review (ADDRESSED / NOT ADDRESSED). Fix-loop escalation to a stronger model. Rulings ledger. Explicit model per dispatch. | `ctm-slice` §0, §4, §5; all engineer and reviewer agents |
| superpowers: parallel implementers conflict | Parallel builders only in separate worktrees with non-overlapping owners, merged one at a time | `ctm-slice` §4, `ctm-integrator` |
| superpowers: TDD + writing-good-tests | RED/GREEN evidence block; fixtures mirror the complete real response; mutation check | new skill `ctm-tdd` |
| superpowers: systematic-debugging | Root cause before fix; trace across CTM layers; stop after 3 failed fixes | new skill `ctm-debug`, new agent `ctm-debugger` |
| superpowers: verification-before-completion | No completion claim without fresh output; verify reports with `git log` | `CLAUDE.md` rules, `ctm-slice` rules |
| superpowers: brainstorming builder check, writing-plans | Builder check before coding. Tasks with Interfaces and RED/GREEN steps. Global constraints. Review focus. No placeholders. | `ctm-slice` §3.5, `ctm-solution-architect` |
| superpowers: receiving-code-review | Verify findings, ask before implementing unclear ones, push back with reasons, report conflicts with owner decisions instead of toggling | engineer agents |
| agency: reality checker / evidence collector | Default NOT READY. Evidence tied to a commit SHA and stale after a rebase. Mutation flows need screenshot + API response + persisted state. NOT TESTED is distinct from FAIL. | `ctm-qa-engineer` |
| agency: codebase archaeologist | Drift registry; never mark Fixed without checking both sides; counts computed, not copied | new agent `ctm-drift-auditor` (replaces `ctm-tech-writer`), `drift-registry.md` |
| agency: AI-code auditor, privacy engineer | "RLS enabled" verified (FORCE, non-trivial policy). Wider leak surfaces (logs, Celery args, Redis, Meilisearch, OCR, backups, AI prompts). Stable finding ids. Rotate leaked secrets. | `ctm-security-reviewer` |
| agency: workflow architect, minimal-change engineer | Seven failure classes and observable states for async steps; Scope Self-Check; fix rounds change only listed issues | `ctm-solution-architect`, engineer agents |
| agency: test automation engineer, accessibility auditor | Browser harness rules (no sleeps, own data, artifacts, quarantine); WCAG criteria cited, keyboard-only journey, axe scan | `ctm-platform-engineer`, `ctm-ui-finish-gate` |
| agency: NEXUS handoff templates | QA-FAIL brief (attempt n/limit, expected / actual / evidence / files); five escalation options; risks carried forward | `ctm-slice` §5, `ctm-qa-engineer`, PR body |
| MetaGPT: WritePRD triage, IS_PASS self-check | `Type: BUG / NEW / CHANGE-TO`; reports list assumptions and remaining TODOs; gates wait until both are clear | `ctm-spec-analyst`, engineers, `ctm-slice` §4 |
| MetaGPT: RunCode blame routing, RoleZero repeat detection | QA failure table routed to backend / frontend / database / test / ENV; no-progress rule escalates at once | `ctm-qa-engineer`, `ctm-slice` §5 |
| MetaGPT: cr points + confirm pass; ChatDev ECL/IER | A CTM review-points checklist from real history, injected by path tags, hit-counted and pruned; every finding cites a point; a ±5-line confirm pass | `review-points.md`, reviewers, drift auditor |
| ChatDev: bounded phase loops, reflection, EnvironmentDoc | Review gates 2 rounds, QA 3. Decisions recorded once in a register. A runbook in `evidence.md`. | `ctm-slice`, `decisions/screens.md`, `ctm-qa-engineer` |
| ChatDev: dehallucination | Subagents can't ask mid-run, so questions move earlier: an analyst question table with default assumptions, the builder check, and NEEDS_CONTEXT | `ctm-spec-analyst`, `ctm-slice` |

### Rejected after review

- **From superpowers:** installing the whole plugin. Its skills write to their own folders, dispatch generic agents and impose "invoke a skill first", which clashes with this SOP. The visual-mockup server is also out.
- **From MetaGPT and ChatDev:**
  - 1:1 role-play chats, which double the cost;
  - one review comment per round;
  - rewriting a whole file on a failed review, which is dangerous on 4,000-line files;
  - LLM-scored experience caches and embedding memory;
  - greenfield Tailwind templates;
  - Art designer, CEO/CPO language choice, MacNet graphs.
- **From the NEXUS docs:** the seven-phase lifecycle, rosters of 15–30 agents, invented thresholds, "mark blocked and keep going", and merging at the end. That last one is the failure CTM already had.
- **From the rest of the agency-agents catalog:** about 250 agents are irrelevant to CTM (marketing, sales, game development, GIS, and so on).

## 5. The CTM team (14 agents)

The main session is the **team lead** (MetaGPT TeamLeader / NEXUS orchestrator). It triages, writes dispatches, verifies reports, records rulings, and holds the human gates.

| Agent | Role | Sources | Tools / model |
|---|---|---|---|
| `ctm-spec-analyst` | Brief, triage, screen decisions, question table | MetaGPT PM, ChatDev CEO/CPO, agency meeting-notes rules | read + write docs |
| `ctm-solution-architect` | Design, contract JSON, owners block, failure paths, tasks | MetaGPT Architect + PM, superpowers writing-plans, agency software/backend/workflow architect | read + write design |
| `ctm-database-engineer` | **Only** writer of migrations/RLS/grants; review mode for DB diffs | agency database-optimizer + identity RLS + DB reliability | full |
| `ctm-backend-engineer` | Services, API, tasks (test-first) | agency backend-architect + identity, superpowers implementer | full |
| `ctm-frontend-engineer` | Plenix UI modules (test-first, contract-driven) | agency frontend + a11y, superpowers implementer | full + WebFetch |
| `ctm-debugger` | Root cause, regression test | superpowers systematic-debugging | full |
| `ctm-qa-engineer` | Evidence by acceptance ID, routed failures | MetaGPT QA, ChatDev tester, agency reality checker / evidence collector | read + run + write evidence |
| `ctm-code-reviewer` | Spec compliance + quality; builder check; re-review | agency code-reviewer, superpowers task reviewer, MetaGPT WriteCodeReview | read-only |
| `ctm-security-reviewer` | Permissions, isolation, identity, RLS, AI egress | agency identity / AI-code auditor / privacy | read-only |
| `ctm-i18n-rtl-reviewer` | EN/AR parity, bidi, PDFs, institutional wording | agency i18n | read-only, Sonnet |
| `ctm-ui-finish-gate` | Workflow fit, Plenix fidelity, states, WCAG, locked decisions | agency finish-gate + accessibility auditor | read-only |
| `ctm-integrator` | Sync before gates, publish after; protects others' work | agency git-workflow, superpowers worktrees / finishing | full, no merge or main push |
| `ctm-drift-auditor` | Status, review points, registers, drift audits | agency codebase archaeologist, MetaGPT/ChatDev experience reuse | write allow-list, Sonnet |
| `ctm-platform-engineer` | Compose, CI, browser harness, Linux validation route | agency devops / platform / test automation | full, no deploy |

A typical M slice runs 7–9 of these. Database, debugger, platform and the conditional gates run only when their trigger applies.

### Flow for an M slice

```
team lead ─► spec-analyst ─► solution-architect ─► builder check
                                   │
         ┌─────────────────────────┼──────────────────────────┐  separate worktrees,
         ▼                         ▼                          ▼  non-overlapping owners
  database-engineer ─► backend-engineer        frontend-engineer (against contract/*.json)
         └─────────────────────────┼──────────────────────────┘
                                   ▼  verify reports (git log, check_ownership)
                       integrator: SYNC (rebase on origin/main)
                                   ▼
 qa ∥ code-review ∥ [security] ∥ [i18n-rtl] ∥ [ui-finish-gate]   gates chosen by changed paths
                                   │  QA-FAIL brief → owner; scoped re-review; 2/3 rounds
                                   ▼
               integrator: PUBLISH (draft PR + evidence) ─► drift-auditor
```

## 6. Deterministic gates (no LLM needed)

| Gate | Catches | Status on current main |
|---|---|---|
| `.claude/hooks/guard-protected.cjs` (PreToolUse) | Edits to `build-spec/`, the question bank, `.env*`, keys | Active in this repo |
| `scripts/check_frontend_contract.cjs` | CDN pin differs from `PLENIX_BASE`; raw colors, `!important`, numeric font sizes, inline styles in `static/ctm` (JS, HTML, CSS) and templates | **Fails today**: DR-001 and DR-003 in `drift-registry.md` |
| `scripts/check_migration_diff.cjs` | RunSQL/RunPython without reverse, demo data, `SECURITY DEFINER` without `search_path`, BYPASSRLS, number reuse (comments ignored) | Passes on this branch. Against the PR #26 range it flags exactly 0055 and 0057 (irreversible) and 0054/0061–0063 (demo data). |
| `scripts/check_ownership.cjs` | UI branches touching DB-owned paths; files outside a slice's `owners` block; files with two owners | New; used per role by engineers and the lead |
| `scripts/check_slice_trace.cjs` | Acceptance IDs in the brief missing from the design or evidence | New |
| `.claude/settings.json` deny rules | Push to main, force-push, `gh pr merge`, `git clean -fdx`, forced worktree removal, reading `.env` and SSH keys | Active (deny rules apply in bypass mode) |

## 7. Permissions

- `.claude/settings.local.json` (git-ignored, this machine only) sets `defaultMode: bypassPermissions`. Every agent sets `permissionMode: bypassPermissions`.
- Safety comes from deny rules, the guard hook, reviewer tool limits (no Edit/Write) and the ownership check, not from prompts.

## 8. Recommended next steps

1. Fix the existing gate failures (DR-001, DR-003, DR-005). Then add the four check scripts to `.github/workflows/backend.yml` as the first step.
2. Replace manual `?v=` cache markers with `ManifestStaticFilesStorage`. 133 commits changed only these markers.
3. Build the shared Playwright harness and a Linux validation container (`ctm-platform-engineer`).
4. Split `council-case.js` and `council.js` per screen, with an ownership map.
5. Seed `decisions/screens.md` from owner clarifications. Map F01–F36 to tests (GAP-002).
6. Run one real M slice with `/ctm-slice`. Tune prompts the superpowers writing-skills way: record the failure first, then make the smallest edit that fixes it. Keep `ctm-slice` under 20k characters so it survives compaction.
