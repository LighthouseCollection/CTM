# CTM software development lifecycle (SDLC)

Version 1.0 — 2026-11-04. Owner: Fr. Raphael Maher (product owner).

This is the lifecycle every CTM change follows, from the owner's request to
running in production and being maintained. Agents work autonomously (owner
decision 2026-11-04): they push, merge, migrate and deploy without asking.
Quality is therefore enforced by **automated gates**, not by approvals. A change
moves to the next phase only when its gate passes.

## 1. Lifecycle at a glance

| # | Phase | Owner (agent) | Output | Exit gate (all automated unless marked) |
|---|---|---|---|---|
| 0 | Intake | `ctm-intake` | GitHub issue + backlog row | Type, severity, area, assignee set |
| 1 | Requirements | `ctm-spec-analyst` | `brief.md` | **G1 Ready**: acceptance IDs, permission rows, no BLOCKING questions |
| 2 | Design | `ctm-solution-architect` (+ `ctm-screen-shape`, `ctm-owner-interview` for UI) | `design.md`, `contract/*.json`, owners block | **G2 Designed**: trace check, owners check, builder check answered |
| 3 | Build | `ctm-database-engineer`, `ctm-backend-engineer`, `ctm-frontend-engineer` | Commits on a short-lived branch | **G3 Commit**: pre-commit hook passes; RED→GREEN evidence |
| 4 | Verify | CI + `ctm-qa-engineer` + independent reviewers | Green PR, `evidence.md` | **G4 Done**: every required CI check green (section 4) |
| 5 | Stage | `ctm-integrator` | Merged to `main`, deployed to staging | **G5 Staged**: staging migrate + health + real-API browser smoke |
| 6 | Release | `ctm-integrator` | Version tag, release notes, production deploy | **G6 Released**: backup, migrate, health check; automatic rollback on failure |
| 7 | Operate | `ctm-platform-engineer`, `ctm-drift-auditor`, `ctm-intake` | Monitoring, incidents, drift audits, dependency updates | Incidents become phase-0 bugs |

Owner checkpoints are optional: the owner may look at staging at any time and
report UI or bug feedback to `ctm-intake`, which starts a new item at phase 0.

## 2. Phase details

### 0. Intake
The owner reports a bug, feature or UI improvement to `ctm-intake` (or any
agent, which forwards it). `ctm-intake` logs a GitHub issue (labels
`type:*`, `sev:S1–S4`, `area:*`, `agent:*`) and a row in `backlog.md`, sizes it
(BUG / XS / S / M / L) and assigns it.

### 1. Requirements — Definition of Ready (G1)
- Brief cites the spec (`build-spec/`, confirmed decisions, owner clarifications).
- Acceptance IDs listed (spec IDs such as SEC01/DEC02 plus slice IDs AC-n).
- Permission rows and derivative surfaces named.
- Screen spec for UI work; new personal data has a privacy-data-map row.
- No BLOCKING question open. XS/S items and bugs skip to phase 3 with the
  issue as their brief.

### 2. Design (G2)
- API contract with real example JSON; data mapped to `schema.json` names.
- `owners` block (one owner per file); failure paths for async steps.
- Test-first task list. `check_slice_trace` and `check_ownership` pass.
- Builder check: a fresh reviewer lists what a builder would have to guess;
  every item answered.

### 3. Build (G3)
- Short-lived branch `work/<stream>-<item>` from current `main`; rebase daily.
- Test-first (`ctm-tdd`): RED evidence, then GREEN.
- Pre-commit hook (`.githooks/pre-commit`): frontend contract check on changed
  files, migration lint, ownership, Semgrep on changed files when installed.
- Commits are small and conventional (`feat(council): …`, `fix(api): …`).

### 4. Verify — Definition of Done (G4)
A PR merges only when all required checks are green (section 4). On top of CI:
- `ctm-qa-engineer` maps every acceptance ID to evidence (`evidence.md`).
- **Independent review:** the author never reviews its own change. At least one
  reviewer that did not write the code: `ctm-code-reviewer` plus the gates the
  changed paths require (security, i18n/RTL, UI, database), and PR-Agent in CI.
- Fix rounds are capped (2 for reviews, 3 for QA), then escalate to the owner.

### 5. Stage (G5)
- Squash-merge to `main` (`gh pr merge --squash --delete-branch`).
- Automatic deploy to **staging**: separate Compose project on the CTM VM
  (`docker compose -p ctm-staging`, own database `ctm_staging`, port 8001,
  `staging.ctm.lighthouseway.org`), synthetic data only.
- Gate: migrations apply, health check passes, `browser_integration.py` passes
  against staging.

### 6. Release (G6)
- Semantic version tag `vMAJOR.MINOR.PATCH` on the staged commit; release notes
  generated from the merged PRs and linked issues.
- Production deploy: `pg_dump` + media snapshot → build → migrate → restart →
  health check → **automatic rollback** (previous image, restore dump) on failure.
- Issues move to `deployed`, then `closed` when the reporter's check passes.

### 7. Operate and maintain
- Health and error monitoring on production; failures open an S1/S2 bug.
- `ctm-drift-auditor` audit mode weekly: CDN pin, docs vs code counts,
  duplicate helpers, screens not on Plenix templates, glossary drift.
- Dependency updates (Dependabot / uv lock) go through the same lifecycle as
  any change. **Plenix CDN** updates are automatic: `plenix-upgrade.yml` detects
  a new release, bumps every pin, verifies every referenced CDN file exists,
  validates against the real CDN (frontend tests, shell tests, browser smoke
  with screenshots: `browser_cdn_smoke.py`, EN desktop, EN mobile, AR) and merges; a failure opens one bug issue with logs and
  screenshots.
- Retro after each M/L item: confirmed blockers become review points.

## 3. Environments

| Environment | Where | Data | Deployed by | When |
|---|---|---|---|---|
| Local / worktree | Developer machine, agent worktrees | Synthetic | — | Every edit |
| CI | GitHub Actions (PostgreSQL 16 service) | Synthetic | — | Every push and PR |
| Staging | CTM VM, Compose project `ctm-staging` | Synthetic (`seed_demo`) | `ctm-integrator` | Every merge to `main` |
| Production | CTM VM, Compose project `ctm`, `ctm.lighthouseway.org` | Real | `ctm-integrator` | Every release tag |

## 4. Required CI checks (branch protection on `main`)

| Check | Tool | Blocks on |
|---|---|---|
| Fast gates | `check_frontend_contract`, `check_migration_diff`, `check_ownership`, `check_slice_trace`, `check_agent_rules` | Any **new** problem (existing ones reported, not blocking) |
| Static analysis | **Semgrep** (CTM rules in `.semgrep/ctm.yml` + `p/django`, `p/python`, `p/javascript`, `p/secrets`) | Findings on added lines |
| Inline review comments | **reviewdog** | Posts Semgrep/lint findings on the changed lines of the PR |
| Quality gate | **SonarQube Community** (self-hosted) | New bugs, vulnerabilities, security hotspots, duplication or coverage below the gate on new code |
| Tests | `node --test`, `pytest` on PostgreSQL, `makemigrations --check`, `validate_spec.py` | Any failure |
| Build | Docker image build + container smoke | Any failure |
| AI review | **PR-Agent** (`/review`, `/describe`) | Advisory comments; blocking findings go to the author agent |

The existing `backend.yml` keeps the test/build jobs; `quality.yml` adds the rest.

## 5. Agent instructions stay in sync

`CLAUDE.md` is the single source. `scripts/sync_agent_rules.cjs` generates
`AGENTS.md` (read by Codex) from it, and the `check_agent_rules` CI step fails
if they differ. This gives Rulesync's benefit without another dependency.

## 6. Tool decisions (2026-11-04 review)

| Tool | Decision | Why |
|---|---|---|
| Semgrep | **Adopt** | Encodes CTM rules (Plenix styling, migrations, CSRF, secrets) as enforceable checks; SARIF output |
| SonarQube Community | **Adopt** (self-host on the VM) | Quality gate on new code: bugs, vulnerabilities, duplication, coverage |
| reviewdog | **Adopt** | Shows findings on the PR's changed lines only, so existing debt does not block new work |
| PR-Agent | **Adopt** (advisory) | Independent AI review and PR descriptions; needs an API key secret |
| OpenQodex | **Not adopted** | No official repository or documentation found; independent review is covered by CTM reviewers + PR-Agent |
| Coding Ethos | **Watch** | Policy-as-code from one source is the right idea, but it is pre-1.0; CTM's guard hook, pre-commit hook and Semgrep rules cover it today |
| Rulesync | **Replaced** by `sync_agent_rules.cjs` | Several unrelated projects use the name; a 40-line script does the one job CTM needs |

## 7. Setup still needed outside the repository

1. GitHub branch protection on `main`: require the checks in section 4.
2. Secrets: `SONAR_TOKEN`, `SONAR_HOST_URL`, and an AI key for PR-Agent
   (`ANTHROPIC_KEY` or `OPENAI_KEY`).
3. SonarQube Community container on the VM (or SonarQube Cloud).
4. Staging Compose project, database and DNS name.
5. `git config core.hooksPath .githooks` in each checkout (the hook is in the repo).
