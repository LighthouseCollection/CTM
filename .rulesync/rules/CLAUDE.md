---
root: true
targets:
  - '*'
globs:
  - '**/*'
---
# CTM — instructions for Claude Code and Codex

CTM is run by the **CTM4** agent team, set up with the dispatch kit from 2026-11-13 (D-0074): same repository,
server and code. **Every agent first reads `.agents/RULES.md`**: the team's rules (roles, who merges, how work
is claimed, handed over and signed). Then it reads `docs/project-rules.md`, this file and `docs/lessons.md`.
Where this file and `.agents/RULES.md` differ on how the team works, `.agents/RULES.md` wins. This file holds
what is true about CTM itself. The design contract is `DESIGN.md`. The CTM3 team (`ctm3-*` agents,
`docs/implementation/sdlc.md` section 2) and the CTM 2.0 streams are retired history.

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
- Ownership: only the database engineer writes migrations, RLS and grants;
  services belong to the backend owner. UI work never edits
  `tribunal/migrations/`, `tribunal/db/`, `services/` or `policy.py`. Demo/seed
  data goes in the gated `seed_demo` command, never in a migration.
  (`scripts/db_owner_guard.cjs` still looks for the old label
  `agent:ctm3-database-engineer` on such PRs.)
- Never revive removed workflows (replacement decrees, passwords, fixed 17:00 send).
- The repository is **public**: never commit or screenshot real case data or secrets.

## Working rules that stay

- **Merging and deploying (D-0074):** agents push branches and open PRs; a member
  merges. Every merge to `main` deploys the live site through CI
  (`.github/workflows/deploy.yml`: required checks first, backup, health check,
  automatic rollback). The Plenix upgrade below merges itself.
- **GitHub is the only channel.** Work items are issues; status is generated from
  GitHub (the pinned "CTM dashboard" and "Daily summary" issues).
- **Never stop to wait for the owner (D-0003).** If intent can be read two ways,
  apply the recommended option and post a decision card; record it in
  `decisions.yaml` with the check that enforces it. Church law, fees, deadlines
  and institutional wording are never invented: park that item on a `decision`
  issue and continue with the rest.
- **Evidence** is reported as Ran / Skipped / Planned / Manual, each with a path.
  No completion claim without command output from this session.
- **Pictures** only when the owner asks (D-0004). Every screenshot a check already
  took is shared: `ci-screenshots` branch, the PR, the linked issue, the dashboard.
- Bugs: root cause before fixes; stop after 3 failed fixes. New behavior is test-first.
- The old CTM3 role registry `agents.config.yaml` and `.claude/agents/ctm3-*.md`
  stay only because CI still checks them (D-0025, D-0041). The team's registry is
  `.agents/agents.config.yaml`. Owner reports come in as GitHub issues and go to
  the PM, "CTM4 - PM".

Plenix CDN updates reach CTM automatically (`.github/workflows/plenix-upgrade.yml`:
every 30 minutes, bump every pin, verify every CDN file, run the frontend,
PostgreSQL shell and `browser_cdn_smoke.py` checks, auto-merge; a failure opens
one `Plenix <v> breaks CTM` bug, copied to `plenix-ds/pds` for the PDS team). Hold CTM on a version with
`"pins": {"ctm": "<v>"}` in the CDN's `cdn/latest.json`.

## Validation commands

```sh
node scripts/check_frontend_contract.cjs --base origin/main   # CDN pin + styling (changed files)
node scripts/check_migration_diff.cjs                         # migration lint vs origin/main
node scripts/check_i18n.cjs --base origin/main                 # EN/AR keys, new problems only
uv run --no-project --with pyyaml==6.0.3 python scripts/check_decisions.py  # every decision has a check
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
