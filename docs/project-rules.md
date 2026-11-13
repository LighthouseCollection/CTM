# CTM: project rules

Written once by dispatch kit 3.4 (Project Plan 3.4); this file now belongs to the project. Every agent follows it together with `.agents/RULES.md`. It adds to those rules and never weakens them.

Add short, definitive rules here as the project needs them, each by a PR that links a recorded decision.

## Rules
- None yet.

## CTM specifics (added when CTM4 was set up, 2026-11-13)
- **CTM's standing rules are in `CLAUDE.md`** (generated from `.rulesync/rules/CLAUDE.md`): the non-negotiable rules, the Plenix upgrade, the validation commands and the shared records. Read it after `.agents/RULES.md`.
- **Every merge to `main` deploys the live site** (https://ctm.lighthouseway.org) through `.github/workflows/deploy.yml`, after the required checks pass. That is why a member merges (D-0074).
- **Decisions** go into `decisions.yaml` in CTM's own format, checked by `scripts/check_decisions.py` (the required check "Decisions have checks"). There is no `decisions/` folder in CTM. Take the next free number after `main` and every open PR (open PR #315 holds D-0065 to D-0073).
- **The old CTM3 framework is still checked by CI.** `agents.config.yaml`, `.claude/agents/ctm3-*.md`, `scripts/check_registry.cjs` and `tests/frontend/role-registry.test.cjs` stay until the team retires them in one PR that keeps every required check green, and updates D-0025 and D-0041 in the same PR.
- **Database paths:** `scripts/db_owner_guard.cjs` still asks for the label `agent:ctm3-database-engineer` on PRs that change `tribunal/migrations/`, `tribunal/db/` or `deploy/postgres/`.
- **The old team's notes** are in the project's notes folder on the agent host (`notes/`). They are history; the rules and decisions win.
