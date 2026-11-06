---
root: true
targets:
  - '*'
globs:
  - '**/*'
---
# CTM 3.0 — instructions for Claude Code and Codex

CTM restarted as **CTM 3.0** on 2026-11-04 (D-0028): same repository, server and
code, one team (`ctm3-*` agents, sessions titled "CTM3 - <role>"). The CTM 2.0
streams and their docs (`CLAUDE-START-HERE.md`, `stream-*.md`, `governance.md`)
are retired history. This file is the operating manual every session and agent follows. The full delivery system (team, SDLC,
intake, decisions, enforcement) is `docs/implementation/sdlc.md`. The design
contract is `DESIGN.md`. Lessons from past mistakes: `docs/lessons.md`.

## Non-negotiable rules

- `docs/architecture/build-spec/` and `tribunal/reference/question-bank.json` are
  protected (a hook blocks edits). Conflicts go to GitHub, never into the spec.
- Precedence: owner clarifications and `decisions.yaml` (later dates win) >
  `docs/architecture/CTM-confirmed-decisions.md` > build-spec > prototype.
- Permissions are server-enforced, deny by default, and also cover derivatives,
  search snippets, counts, links and downloads (`build-spec/permissions.md`).
- Applicants never see another applicant's data, even in the same case.
  Professional Assessments never leak through documents, reports, search or AI.
- UI: React 18 + Plenix CDN at the version pinned in `ctm/settings.py`
  (`PLENIX_BASE`, the only source of truth; older docs say 0.58.0). Documented
  components and `--plx-sys-*`/`--plx-comp-*` tokens only. No raw colors,
  numeric font sizes, inline styles, `!important`, copied CDN files or other UI
  kits. The isolated RTL/Arabic bridge is the only styling exception.
- English and Arabic for every label, help text, validation, notice and prompt;
  RTL works. Arabic follows `docs/i18n/arabic.md`; institutional text is never
  improvised.
- Never fake success: no mock payment, email, scan, OCR or transcription result.
  Honest "unavailable" placeholders are fine for OCR/audio.
- No passwords. Council = Microsoft Entra preauthorized tenant/object id.
- Linux PostgreSQL CI is authoritative. Windows Python crashes are not app failures.
- Ownership: only `ctm3-database-engineer` writes migrations, RLS and grants;
  services belong to the backend owner. UI work never edits
  `tribunal/migrations/`, `tribunal/db/`, `services/` or `policy.py`. Demo/seed
  data goes in the gated `seed_demo` command, never in a migration.
- Never revive removed workflows (replacement decrees, passwords, fixed 17:00 send).
- The repository is **public**: never commit or screenshot real case data or secrets.

## Rules for every role

- **Autonomy (owner decision 2026-11-04, D-0001):** all permissions are bypassed.
  Every agent may push, merge, run `git clean -fdx` (own worktree only), deploy,
  run migrations against the real database and work with real data — the
  automated way: required checks green before merge (`gh pr merge --auto`),
  backup before migrations and deploys, health check and automatic rollback
  after deploy; never copy real case data into git or print secrets.
- **GitHub is the only channel.** Work items are issues; hand-offs are issue
  assignments (`agent:` labels), role mentions and PR reviews. Sign every
  GitHub comment `— <role>` until the GitHub App identities exist.
- **Never stop to wait for the owner.** If intent can be read two ways, apply
  the recommended option and post a decision card (`ctm-owner-interview`
  skill); record it in `decisions.yaml` with the check that enforces it. Do
  not ask when the answer is in `decisions.yaml`, the code, `DESIGN.md` or the
  build spec. Church law, fees, deadlines and institutional wording are never
  invented: park that item on a `decision` issue and continue with the rest.
- **Artifacts are files** in `docs/implementation/slices/<id>/`, not chat.
- **Evidence** is reported as Ran / Skipped / Planned / Manual, each with a path.
  No completion claim without command output from this session; another
  agent's report is a claim until `git log`, the diff and the checks confirm it.
- **Pictures** only when the owner asks. Every screenshot a check already took
  is shared: `ci-screenshots` branch, the PR, the linked issue, the dashboard.
- Integrate small and often: a change reaches a PR the same day.
- Bugs: root cause before fixes (`ctm-debug`); stop after 3 failed fixes. New
  behavior is test-first (`ctm-tdd`).
- Roles and concurrency come from the role registry `agents.config.yaml`
  (D-0025, D-0041, adjustable): at most `slots` sessions on long work, plus
  `short_tasks_max` small tasks, each capped at `short_task_cap_min` (then it
  queues for a long-work slot). Memory sets the real limit. Documents name a
  setting, never its value (`scripts/check_registry.cjs`).

## The team (details: `docs/implementation/sdlc.md` section 2)

| Always-on | Gate | On demand | Gate |
|---|---|---|---|
| `ctm3-product-lead` (intake, spec, decisions) | G1 | `ctm3-code-reviewer` | G5a |
| `ctm3-design-director` (`DESIGN.md`, screens) | G2 | `ctm3-design-critic` | G5b |
| `ctm3-solution-architect` (contracts, ADRs) | G3 | `ctm3-a11y-rtl-auditor` | G5c |
| `ctm3-delivery-lead` (plan, ledger, merge order) | G4 | `ctm3-qa-engineer` | G5d |
| `ctm3-database-engineer`, `ctm3-backend-engineer`, `ctm3-frontend-engineer` | red -> green | `ctm3-security-reviewer` | G5e |
| `ctm3-i18n-engineer` (EN/AR) | G6 | `ctm3-debugger` | failing test first |
| `ctm3-technical-writer` (messages, docs) | G7 | `ctm3-drift-auditor` | weekly audit |
| `ctm3-release-engineer` (CI, merge, deploy, Plenix upgrade) | G8 | `ctm3-media-pipeline-engineer` | parked |

Run one slice end to end with **`/ctm-slice <request>`**. Owner reports come in
as GitHub issues (templates: Bug, Feature, UI/UX, Question) and go to
`ctm3-product-lead`. Status lives on GitHub only: the pinned "CTM dashboard"
and "Daily summary" issues are generated by `.github/workflows/dashboard.yml`.

Plenix CDN updates reach CTM automatically (`.github/workflows/plenix-upgrade.yml`:
every 30 minutes, bump every pin, verify every CDN file, run the frontend,
PostgreSQL shell and `browser_cdn_smoke.py` checks, auto-merge; a failure opens
one `Plenix <v> breaks CTM` bug, copied to `plenix-ds/pds` for the PDS team). Hold CTM on a version with
`"pins": {"ctm": "<v>"}` in the CDN's `cdn/latest.json`.

## Validation commands

```sh
node scripts/check_frontend_contract.cjs --base origin/main   # CDN pin + styling (changed files)
node scripts/check_migration_diff.cjs                         # migration lint vs origin/main
node scripts/check_ownership.cjs --slice <id>                  # changed files vs owners block
node scripts/check_slice_trace.cjs <id>                        # acceptance IDs: brief -> design -> evidence
node scripts/check_i18n.cjs --base origin/main                 # EN/AR keys, new problems only
uv run --no-project --with pyyaml==6.0.3 python scripts/check_decisions.py  # every decision has a check
node scripts/check_registry.cjs                               # role registry + no setting values in docs
opengrep scan --config .opengrep/ctm.yml --baseline-commit origin/main --error
node --test tests/frontend/*.test.cjs                          # frontend contracts
uv run pytest --ds=ctm.settings_postgres_test -q               # needs isolated CTM_TEST_DATABASE_URL
uv run python manage.py makemigrations --check --dry-run --settings=ctm.settings_test
uv run python docs/architecture/build-spec/validate_spec.py
uv run --group browser python scripts/browser_cdn_smoke.py     # Plenix CDN + sign-in, EN/AR screenshots
```

`CLAUDE.md` and `AGENTS.md` are generated from `.rulesync/` (`npx rulesync@43.6.0
generate`); edit the source there. Enable local checks once per checkout with
`npx lefthook@2.2.2 install`.

Shared records (`docs/implementation/`): `review-points.md`,
`decisions/screens.md`, `spec-gaps.md`, `drift-registry.md`, `glossary.md`,
`privacy-data-map.md`, `plenix-page-templates.md`, `plenix-requests.md`.
