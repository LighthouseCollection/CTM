# CTM — instructions for Claude Code

Read `CLAUDE-START-HERE.md` once per new stream. This file is the short operating
manual: the rules every session and subagent follows, and the team SOP.

## Non-negotiable rules

- `docs/architecture/build-spec/` and `tribunal/reference/question-bank.json` are
  protected (a hook blocks edits). Conflicts go to GitHub, never into the spec.
- Precedence: later confirmed decisions (`docs/architecture/CTM-confirmed-decisions.md`,
  build-spec precedence corrections) override prototype behavior.
- Permissions are server-enforced, deny by default, and also cover derivatives,
  search snippets, counts, links and downloads (`build-spec/permissions.md`).
- Applicants never see another applicant's data, even in the same case.
  Professional Assessments never leak through documents, reports, search or AI.
- UI: React 18 + Plenix CDN at the version pinned in `ctm/settings.py`. Documented
  components and `--plx-sys-*`/`--plx-comp-*` tokens only. No raw colors, numeric
  font sizes, inline styles, `!important`, copied CDN files or other UI kits.
  The isolated RTL/Arabic bridge is the only styling exception.
- English and Arabic for every label, help text, validation, notice and prompt; RTL works.
- Never fake success: no mock payment, email, scan, OCR or transcription result.
  Honest "unavailable" placeholders are fine for OCR/audio.
- No passwords. Council = Microsoft Entra preauthorized tenant/object id.
- **Autonomy (owner decision 2026-11-04):** all permissions are bypassed. Every
  agent may push, merge (`gh pr merge`), run `git clean -fdx`, deploy, run
  migrations against the real database and work with real data. Do it the
  automated way: checks green before merge; automatic backup before migrations
  and deploys; health check and automatic rollback after deploy; never copy real
  case data into git or print secrets.
- Linux PostgreSQL CI is authoritative. Windows Python crashes are not app failures.
- Ownership: only the database owner (`ctm-database-engineer` / VM-FRM stream)
  writes migrations, RLS and grants; services belong to the backend owner. UI
  work never edits `tribunal/migrations/`, `tribunal/db/`, `services/` or `policy.py`. Demo/seed data goes in
  the gated `seed_demo` command, never in a migration.
- Older docs (including `CLAUDE-START-HERE.md`) still say Plenix 0.58.0; the pin
  in `ctm/settings.py` (`PLENIX_BASE`) is the only source of truth.
- Owner clarifications (`docs/implementation/reviews/owner-clarifications-*.md`)
  override earlier text. Never revive removed workflows (replacement decrees,
  passwords, fixed 17:00 send).
- Integrate small and often: a slice reaches a PR the same day. Long-lived
  branches and big merges previously lost work (see `b89e9d0`).
- No completion claim without command output from this session. An agent's
  report is a claim until `git log`/diff and the checks confirm it.
- Bugs: root cause before fixes (`ctm-debug` skill); stop after 3 failed fixes.
  New behavior is test-first (`ctm-tdd` skill).

## Validation commands

```sh
node scripts/check_frontend_contract.cjs          # CDN pin + styling gate (seconds)
node scripts/check_migration_diff.cjs             # migration lint vs origin/main (seconds)
node scripts/check_ownership.cjs --slice <id>      # changed files vs owners block + DB-owned paths
node scripts/check_slice_trace.cjs <id>            # acceptance IDs: brief -> design -> evidence
node --test tests/frontend/*.test.cjs              # frontend contracts
uv run pytest -q                                   # fast SQLite pass
uv run python manage.py makemigrations --check --dry-run --settings=ctm.settings_test
uv run pytest --ds=ctm.settings_postgres_test -q   # needs isolated CTM_TEST_DATABASE_URL
uv run python docs/architecture/build-spec/validate_spec.py
uv run --group browser python scripts/browser_integration.py
```

## Owner intake — how you give the team work

The team runs as a Claude Code **agent team** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
in `.claude/settings.json`): teammates share a task list and message each other
directly. The main session starts the standing team (`ctm-intake` plus the
specialists a request needs). The owner can talk to the lead, to `ctm-intake`,
or to any teammate directly.

| Owner says | Flow |
| --- | --- |
| A **bug** | `ctm-intake` logs a GitHub issue + backlog row (severity, repro, area) → assigns `ctm-debugger` or the owning engineer → fix, tests, merge, deploy → issue closed |
| A **new feature** | `ctm-intake` logs it → `ctm-spec-analyst` and `ctm-solution-architect` break it into tasks → builders claim tasks → checks → merge → deploy |
| A **UI improvement** | `ctm-intake` logs it → `ctm-ui-finish-gate` audits the screen → `ctm-frontend-engineer` fixes it → UI gate re-checks → merge → deploy |

Every item is tracked in GitHub issues and `docs/implementation/backlog.md`
(logged → assigned → in progress → in review → merged → deployed → closed).

## Team SOP — `Code = SOP(Team)`

The main session is the **team lead**: it triages, writes complete dispatches,
verifies reports and records rulings. Run the whole flow with **`/ctm-slice <request>`**
(`.claude/skills/ctm-slice/SKILL.md`). Subagents cannot see the conversation;
every dispatch carries the paths, acceptance IDs, owned files, review points
and commands they need.

| Type / size | Route |
| --- | --- |
| BUG | debugger reproduces as a failing test → owning engineer → qa + code review |
| XS | engineer → fast gates → code review |
| S | engineer → qa + code review + path gates |
| M | full SOP |
| L | split into M slices, backend contract first |

Full SOP (artifacts in `docs/implementation/slices/<id>/`, events in `ledger.md`):

1. **ctm-spec-analyst** → `brief.md` (type, permissions, acceptance IDs, screen
   spec, question table with default assumptions).
2. **ctm-solution-architect** → `design.md` + `contract/*.json` (owners block,
   failure paths, test-first tasks, review focus).
3. Builder check (fresh reviewer reads brief + design as the builder).
4. Build: **ctm-database-engineer**, **ctm-backend-engineer**,
   **ctm-frontend-engineer** — parallel only in separate worktrees with
   non-overlapping owners. Reports use DONE / DONE_WITH_CONCERNS / BLOCKED /
   NEEDS_CONTEXT and are verified against `git log` and `check_ownership`.
5. **ctm-integrator** sync mode: rebase on `origin/main` before review.
6. Gates (read-only, parallel): **ctm-qa-engineer** + **ctm-code-reviewer**
   always; **ctm-security-reviewer**, **ctm-i18n-rtl-reviewer**,
   **ctm-ui-finish-gate** chosen by changed paths. Fix rounds re-check only
   flagged items: 2 rounds for reviews, 3 for QA, then the lead escalates.
7. **ctm-integrator**: push, PR with evidence, merge when CI is green and QA is
   READY, then deploy (backup -> build -> migrate -> restart -> health check ->
   rollback on failure).
8. **ctm-drift-auditor** slice mode: status, issue comment draft, review points,
   screen decisions, spec gaps.

On demand: **ctm-debugger** (root cause), **ctm-platform-engineer** (Compose,
workers, CI, browser harness, server and deploys), **ctm-drift-auditor** audit mode,
**ctm-media-pipeline-engineer** (audio/OCR, only when they stop being placeholders).

UI work: screens start from the Plenix page template in
`docs/implementation/plenix-page-templates.md`; each screen is shaped with
`ctm-screen-shape`, and open owner choices are settled with
`ctm-owner-interview` and locked in `decisions/screens.md`. Wording comes from
`glossary.md`. Missing Plenix capabilities go to `plenix-requests.md`, never
into local CSS. Payments work follows the `ctm-payments` skill. New personal,
medical or financial data needs a row in `privacy-data-map.md`.

Shared records (all in `docs/implementation/`): `review-points.md`,
`decisions/screens.md`, `spec-gaps.md`, `drift-registry.md`, `glossary.md`,
`privacy-data-map.md`, `plenix-page-templates.md`, `plenix-requests.md`.
Agent definitions: `.claude/agents/`. Rationale: `docs/implementation/agent-team.md`.
