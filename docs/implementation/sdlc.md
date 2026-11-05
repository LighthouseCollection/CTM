# CTM delivery system: team, SDLC, intake, decisions, enforcement

Version 2.0 — 2026-11-04. Product owner: Fr. Raphael Maher. Same structure as
the PDS 1.0 plan, adapted to CTM: CTM is an application that consumes Plenix
from the CDN, so it has no token, package or CDN-publishing work of its own.

## 1. Rules for every role

- Post under your own identity: until the GitHub App exists (section 8), sign
  every GitHub comment `— <role>`.
- Write artifacts as files in the repo (`docs/implementation/slices/<id>/`),
  not in chat.
- Report evidence as **Ran / Skipped / Planned / Manual**, each with a path.
- GitHub is the only channel (section 4). Never stop to wait for the owner
  (section 5).

## 2. The team

Built from superpowers (workflow, gates), agency-agents (roles), MetaGPT
(artifact schemas), ChatDev (loop caps, lessons file) and the design-skill
sources. Definitions: `.claude/agents/`.

### Always-on (the Delivery Lead starts them by `agent-limits.yaml`: 4 long-work slots plus short tasks)

| Role | Model | Owns | Hard gate |
|---|---|---|---|
| `ctm-product-lead` | strongest | Intake and triage of every owner issue; specs (P0/P1/P2, non-goals); decision log; reports back with links and check screenshots | **G1 Spec written** |
| `ctm-design-director` | strongest | `DESIGN.md` (the CTM layer on Plenix), screen specs, state matrices, data display; pictures only when the owner asks | **G2 Design fits `DESIGN.md`** |
| `ctm-solution-architect` | strongest | API contracts (`contract/*.json`), data model, ADRs (`docs/adr/`) | **G3 Contract** |
| `ctm-delivery-lead` | strong | Plans with global constraints, file ownership, conflict pre-scan, ledger, rulings, merge order | **G4 Plan** |
| `ctm-database-engineer` | strong | Migrations, RLS, grants (sole owner) | Migration lint, reversible, red -> green |
| `ctm-backend-engineer` | strong | Services, APIs, tasks, payments | Red -> green per task |
| `ctm-frontend-engineer` | strong | Council and applicant screens on Plenix | Red -> green per task |
| `ctm-i18n-engineer` | strongest | EN/AR dictionaries, Arabic standard and proposals, locale checks | **G6 Locale** |
| `ctm-release-engineer` | strongest | CI, required checks, Compose, merge, staging and production deploys, Plenix auto-upgrade | **G8 Release integrity** |
| `ctm-technical-writer` | mid | Messaging standard, glossary, guides, release notes | **G7 Docs and messages** |

### On demand (spawned for a job, then gone)

| Role | Model | Job | Gate |
|---|---|---|---|
| `ctm-code-reviewer` | mid per task / strongest final | Spec compliance + quality; Critical / Important / Minor | **G5a** no next task with an open Critical/Important |
| `ctm-design-critic` | strong | Reads code and screenshots together against `DESIGN.md` and the screen spec -> ship / rework / reject | **G5b Visual** |
| `ctm-a11y-rtl-auditor` | mid | axe, keyboard journey, focus, names, contrast, RTL | **G5c a11y** |
| `ctm-qa-engineer` | mid | Behaviour evidence per acceptance ID; NOT TESTED recorded; 3 attempts then escalate | **G5d Behaviour** |
| `ctm-security-reviewer` | strongest | Permissions, privacy, applicant isolation, Professional Assessments, payments | **G5e Security** |
| `ctm-debugger` | strong | Root cause before any fix | Failing test first |
| `ctm-drift-auditor` | mid | Weekly: pins, duplicate logic, docs vs code, decisions without checks | Feeds the backlog |
| `ctm-media-pipeline-engineer` | mid | Audio/OCR (parked until they stop being placeholders) | — |

**Not adopted:** CEO/CPO role-play, NEXUS-full, extra coordinators
(chief-of-staff, studio-producer), workflow-optimizer, MetaGPT's runtime, paid
principle APIs, brand catalogs (CTM's look is Plenix).

## 3. The SDLC

| Phase | Entry | Work | Exit gate |
|---|---|---|---|
| **0. Foundation** (once) | This document | Required checks, branch protection, auto-merge, issue templates, `DESIGN.md`, `decisions.yaml`, dashboard, hooks, lessons | `main` protected; checks green on an empty change |
| **1. Spec** | Issue logged | `ctm-product-lead`: brief with P0/P1/P2, non-goals, acceptance IDs (Known / Inferred / Unknown, decision cards) | **G1** |
| **2. Design** | G1 | `ctm-design-director`: screen spec against `DESIGN.md`, template, state matrix, edge cases (long text, empty, 1,000+ rows; Arabic only if text or direction changes) | **G2** |
| **3. Contract + plan** | G2 | `ctm-solution-architect`: `design.md`, `contract/*.json`, ADR; `ctm-delivery-lead`: `plan.md` | **G3 + G4** |
| **4. Build** | G4 | One engineer per area in its own worktree; test-first; review after each task; fix loop capped at 5; rulings `what — why — cost if wrong` | All tasks done or parked with a ruling |
| **5. Verify** | Branch done | G5a-e in parallel; one whole-branch review; one fix wave | **G5a-e** |
| **6. Localize + document** (overlaps 4-5) | Stable text | `ctm-i18n-engineer` (proposals file), `ctm-technical-writer` | **G6 + G7** |
| **7. Integrate** | All green | `gh pr merge --squash --auto`; conflicts go back to the owning engineer | `main` green |
| **8. Release** (on demand) | Merged | Staging on merge; production on tag: backup -> build -> migrate -> restart -> health and live checks -> automatic rollback; release notes and "Rulings I made" on the issues; lessons updated | **G8** |

Sizes: BUG and XS skip phases 1-3 (the issue is the brief); L splits into M.
Full step list for one slice: `.claude/skills/ctm-slice/SKILL.md`.

**What runs on its own:** everything — spec, design, plan, build, review,
merge, migrations, release and deploy. Owner QA is a follow-up, never a block.

| Situation | Instead of stopping |
|---|---|
| Irreversible action | Backup first (database dump, git tag, media snapshot), then proceed |
| Security issue | Fix at once, log a `security` issue, include it in the daily summary |
| Plan broken beyond a reasonable guess | Re-plan, log a ruling, continue |
| `git clean -fdx` | Only inside the agent's own worktree |
| Database migration | Automatic backup, reversible migration, automatic rollback |
| Merge | `gh pr merge --auto` once required checks pass (bot PRs start `quality.yml` themselves) |
| Deploy | Health check after deploy; automatic rollback on failure |
| Church law, fees, deadlines, institutional wording missing | Never invented: park that item with a `decision` issue; the rest continues |

## 4. Owner intake: everything happens on GitHub

- **You** open an issue from a template (Bug, Feature, UI/UX, Question) in
  `LighthouseCollection/CTM`, or comment on any issue or PR. Plain words are
  enough; a screenshot helps. To get pictures back, say so ("show me options").
- **Agents** hand work to each other by assigning issues (`agent:` labels),
  mentioning roles in comments and reviewing PRs.
- **Daily summary**: one pinned issue, regenerated daily by
  `.github/workflows/dashboard.yml`: PRs merged, issues closed, decisions made,
  deploys, open S1/S2 bugs, link to the day's screenshots.
- **Dashboard**: one pinned issue, regenerated on every change (section 6).

| You report | Flow |
|---|---|
| A bug | Product Lead logs `type:bug` (severity, repro, your words) -> specialist reproduces as a failing test, fixes, merges -> reply with PR link and the check's screenshots -> closed when deployed |
| A feature | Product Lead logs `type:feature` and writes the spec -> Architect + Delivery Lead split it per area -> engineers build in parallel -> gates -> merge -> release -> spec and release link on your issue |
| A UI improvement | Product Lead logs `type:ui` -> Design Director decides the fix against `DESIGN.md` -> Frontend Engineer implements -> Design Critic reviews code and screenshots -> merge -> before/after screenshots on your issue |

## 5. How agents talk to the owner

Agents do not ask permission. They ask about intent only when a request can
be read more than one way, and even then they apply the recommended option at
once and post a decision card (`ctm-owner-interview` skill):

> **D-0123 · Hearings list: default sort**
> Context: one sentence of what we understood.
> **A (Recommended)** — next hearing first — risk: past hearings one click away
> **B** — newest case first — risk: upcoming hearings scroll off
> **Applied: A.** To switch, reply B. If switched, we redo: 1 sort default + snapshots.

- **Pictures:** screenshots CI already takes are always shared (PR, issue,
  dashboard). Extra pictures only when you ask.
- **Never ask twice:** every decision is a `decision` issue and an entry in
  `decisions.yaml` with the check that enforces it.
- **Feedback register:** each owner comment goes open -> accepted -> applied,
  with a link to the changed file.

## 6. The dashboard (pinned issue "CTM dashboard")

Generated, read-only, no backend, no login of its own:
`scripts/build_dashboard.cjs` rebuilds it from `decisions.yaml`, the latest
`main` check results and the `ci-screenshots` branch, on every push to `main`,
after every upgrade run and daily.

- **Decisions:** id, date, area, decision, why, decided by, status, the
  enforcing check with its live pass/fail on `main` (or "review only" and
  why), links. A list of decisions with no enforcing check.
- **Visual checks:** the latest screenshots per run, embedded.
- To change a decision, comment on its issue.

## 7. Enforcement: making rules real

| Rule | Check (CI job in `quality.yml`, required) |
|---|---|
| Plenix only, no custom styling, pinned CDN | `check_frontend_contract.cjs` (changed files) + Opengrep `.opengrep/ctm.yml` |
| Migrations reversible and owned | `check_migration_diff.cjs`, `check_ownership.cjs` |
| Acceptance traced | `check_slice_trace.cjs` |
| EN/AR keys complete | `check_i18n.cjs` (new problems only) |
| Every decision has a check | `check_decisions.py` |
| Claude and Codex instructions identical | Rulesync drift check (`rulesync generate` + `git diff --exit-code`) |
| Workflows safe (pinned actions, no injection) | zizmor |
| Frontend behaviour | `node --test tests/frontend/*.test.cjs` |
| Backend behaviour | `backend.yml` PostgreSQL suite (required once green, DR-009) |
| CDN still works | `plenix-upgrade.yml` (files exist, shell tests, `browser_cdn_smoke.py`) |

Local: lefthook runs the fast checks before commit (`lefthook.yml`).
Agent hooks: SessionStart loads `docs/lessons.md` and open decisions; a Stop
hook blocks "done" when UI files changed without a fresh check run.
reviewdog shows Opengrep findings on the PR's changed lines (presentation
only).

### Tool decisions (same review as PDS 1.0, 2026-11-03)

| Tool | Decision |
|---|---|
| Semgrep | **Replaced by Opengrep** (community fork, same rule format, unrestricted rules) |
| SonarQube Community | **Dropped**: no PR analysis without a plugin, 2-4 GB RAM; overlaps our checks |
| PR-Agent | **Dropped**: a third AI reviewer brings back comment noise; `ctm-code-reviewer` covers it |
| Rulesync | **Adopted**, pinned: one `.rulesync/` source -> `CLAUDE.md` + `AGENTS.md` |
| reviewdog | **Adopted**, presentation only, SHA-pinned |
| zizmor | **Adopted**: workflow security check |
| lefthook | **Adopted**: replaces `.githooks/` |
| OpenQodex | **Trial after 1.0**, local only |
| Coding Ethos | **Not adopted** (archived 2026-10-07) |
| Saguaro | **Not adopted** (npm 0.4.22 was malware) |

## 8. Environment

| Item | State | Change |
|---|---|---|
| Repo | `LighthouseCollection/CTM`, **public**, personal account | Branch protection + required checks + auto-merge on `main` (merge queue needs an organization) |
| Bot identities | Comments signed `— <role>` | GitHub App with one identity per role, created by the owner (section 9) |
| Permissions | Agents bypass permissions with full autonomy | Credentials stay in CI and deploy jobs; safety nets in section 3 replace approval |
| Staging | Not yet | `docker compose -p ctm-staging`, `ctm_staging` database, synthetic data |
| Production | CTM VM (`ctm.lighthouseway.org`) | Deploy on tag with backup and rollback |
| Screenshots | `ci-screenshots` branch (public) | Synthetic data only, never real case data |
| Old team | "CTM 2.0" team (Owner desk / Lead / Builder / Reviewer) | Stop it before the next merge: two teams with different rules (L-10) |

## 9. Setup outside the repo (owner)

1. Create the GitHub App (one per role, or one with role-signed comments) and
   install it on `LighthouseCollection/CTM`.
2. Stop the old CTM 2.0 team and its cron/tmux lines.
3. Staging Compose project, database and DNS.
4. Optional `CTM_BOT_TOKEN` secret so bot merges start the other workflows.
5. **PDS GitHub App** (D-0027): after PDS Phase 0 creates the app, install it on
   `LighthouseCollection/CTM` (Issues: read and write, Contents: read only) and add
   the repository secrets `PDS_APP_ID` and `PDS_APP_PRIVATE_KEY`. CTM then reports
   failed Plenix upgrades to `plenix-ds/pds`, and PDS sends `plenix-release` to CTM
   for an instant upgrade, both through that app. Note: GitHub only accepts
   `repository_dispatch` from a token with **Contents: write** on CTM. With
   Contents read only, the instant trigger is refused and CTM still upgrades
   within 30 minutes through the schedule.
