# QA-01 — report revisions against the actual backend

Work order: [#15](https://github.com/LighthouseCollection/CTM/issues/15). Independent QA stream (Claude). This directory holds QA tests, sanitized evidence and documentation only. No product code is changed by this stream.

**Result: FAIL** (run 2, latest heads). 9 scenarios pass and 3 fail. The backend's revision contract now holds under a real non-owner PostgreSQL role, including concurrency. But at the latest heads the council editor cannot save any revision, because it does not send the `expected_version` the backend now requires. In-app navigation also silently drops unsaved narrative.

## Runs and exact SHAs

Upstream moved while run 1 was in progress, so there are two clearly separate runs. Run 2 is the result of record.

| | Run 1 (pinned at start) | Run 2 (result of record) |
|---|---|---|
| main | `b38e70a15b85c0c28f98515ddcd73f5c48ebdf05` | same |
| Backend PR #7 | `db6dfa3493daa70520669ed14fd9a7331a5d385b` | `bb3e48b3e31844997c12e6234550a8ed1e5d07f5` |
| Council PR #6 | `e4d2fb334b88bb5d91208d08158f00b4650d8bc0` | `65fa3893758ab298beee8aa921a544a8cd489ebc` |
| Shell integration | `docs/implementation/council/shell-integration.patch` @ council SHA | same file @ `65fa389` |
| Local assembly commit (not pushed) | `40feef6` | `4ee49be` |
| HTTP/DB checks | 59 pass / 6 fail | 65 pass / 2 fail |
| Browser checks | 30 pass / 4 fail | 24 pass / 3 fail / 2 errors (saves impossible) |

The applicant PR #5 is not part of this assembly. Later heads (after run 2 started) are not covered.

## Assembly (local only, never pushed)

```sh
git clone https://github.com/LighthouseCollection/CTM.git CTM-QA
cd CTM-QA
git worktree add ../CTM-QA-assembly2 bb3e48b3e31844997c12e6234550a8ed1e5d07f5
cd ../CTM-QA-assembly2
git switch -c local/qa01-assembly-run2
git merge --no-edit origin/main                      # backend branch is based on da99591; main adds 4 commits, no conflicts
git show 65fa389:docs/implementation/council/shell-integration.patch > ../shell.patch
git apply ../shell.patch                              # changes static/ctm/app.js, tribunal/templates/tribunal/shell.html
for f in static/ctm/council.js static/ctm/council-case.js static/ctm/council-media.js static/ctm/council-decree.js \
         tests/frontend/council*.test.cjs; do git show 65fa389:$f > $f; done
```

Changed paths on top of backend+main: `static/ctm/app.js`, `tribunal/templates/tribunal/shell.html` (patch), plus the council-only modules and their tests. The patched `app.js` and `shell.html` are byte-identical to the council branch. No backend file was overlaid. `node --test tests/frontend/*.test.cjs`: 97/97 pass (run 1: 96/96).

## Environment

- Desktop-R, Windows 11. Python 3.12.11 (uv 0.8.12, `--frozen`), Node 22.23.1, Playwright 1.64.0 Chromium with the real Plenix 0.58.0 CDN.
- Disposable PostgreSQL 16 container on `127.0.0.1` only. Run 2 keeps its data on tmpfs (see limitations).
- Roles (`harness/bootstrap_db.py`, mirroring `deploy/postgres/init.sql`):
  - `qa_owner` owns the database and runs migrations.
  - `ctm_app` serves HTTP: LOGIN, NOSUPERUSER, NOBYPASSRLS, NOINHERIT. It is created before migrating, so migrations grant it function EXECUTE.
  - The repository has no production runtime table-grant script yet. Table grants mirror `tests/test_row_security.py`. Function grants are only reported, never added: none were missing.
  - `tribunal_report`, `tribunal_reportrequest` and `tribunal_reportrevision` have forced RLS (51/60 tribunal tables in both runs).
- HTTP server: `harness/serve.py`, a threaded WSGI server on `127.0.0.1:18870` connected as `ctm_app`, using `harness/qa01_settings.py` (built on `ctm.settings_test`; isolated only). Email uses locmem. Stripe and transcription have no credentials. Celery runs eagerly.
- **Authentication is test authentication.** Sessions come from Django `force_login` for synthetic users. This is not Microsoft/Google/Apple acceptance.
- Fixtures (`harness/seed.py`) are fictional. They use the backend's own services (`create_request`, `send_request`, `complete_request`, `revise_report`, `assign_case`, `close_case`). The "reopened" case reproduces exactly the state that the appeal-acceptance branch in `tribunal/services/decisions.py` writes: a new open `appeal` proceeding and the case reopened. The full appeal hearing flow is outside QA-01.

## Reproduce

```sh
# PostgreSQL 16 on loopback, superuser password in %TEMP%/ctmqa/secrets/pg_super (never committed)
docker run -d --name ctm-qa01-pg3 --tmpfs /var/lib/postgresql/data -p 127.0.0.1:55433:5432 \
  -e POSTGRES_USER=qa_super -e POSTGRES_PASSWORD="$(cat $TEMP/ctmqa/secrets/pg_super)" postgres:16
export ASSEMBLY=../CTM-QA-assembly2 QA01_RUN=run2
bash harness/reset.sh                                   # roles, migrate as owner, grants, fixtures
cd $ASSEMBLY && export PYTHONPATH="<harness>;<assembly>"  # ':' on Linux
uv run --frozen --python 3.12 python <harness>/serve.py &                 # runtime role ctm_app
uv run --frozen --python 3.12 --group browser python <harness>/browser_scenarios.py
bash <harness>/reset.sh                                 # fresh fixtures, then:
uv run --frozen --python 3.12 python <harness>/api_scenarios.py
uv run --frozen --python 3.12 python <harness>/owner_control.py           # same denials as table owner
```

The browser and API suites each expect fresh fixtures. Results go to `evidence/<run>/`. Cookies, CSRF values and passwords stay in `%TEMP%/ctmqa/secrets`.

## Results (run 2 unless noted)

| # | Scenario | Run 2 | Run 1 | Notes |
|---|---|---|---|---|
| 1 | Revise only when `can_revise` true; newest content | PASS | PASS | Literal `can_revise` respected; 4 non-author roles, applicant intake and secretary-authored report hidden. |
| 2 | Edit persists, one attributed version, prior values/files/non-text kept | **FAIL** | PASS | Server PASS. **UI cannot save**: editor sends no `expected_version` → `422 expected_version must be a non-negative integer.` |
| 3 | Unchanged save | PASS | PASS | UI sends no POST. Server would still append an identical body (observation). |
| 4 | Non-authors/forged HTTP denied; read ≠ write | PASS | PASS* | *Run 1: 15/16 denials returned 404 under the runtime role; fixed by the bb3e48b proceeding lock. |
| 5 | Applicant/external originals protected | PASS | PASS | External-priest originals not exercised. |
| 6 | Closed/reopened proceedings immutable | PASS | PASS | API 422 plus DB trigger. |
| 7 | Reassignment; follow-up is its own linked report | PASS | PASS | New manager's follow-up created over HTTP. |
| 8 | 403/500/lost-ack: text kept, no false success, no silent duplicate | **FAIL** | FAIL | Server retry recovery PASS (same receipt; 409 for a different body). UI lost-ack/real-denial paths cannot complete (S2 defect). Run 1: server duplicated on retry. |
| 9 | Real parallel writers | PASS | FAIL | Run 2: `[201, 409]`, one version. Run 1 reproduced the gap: `[201, 201]`, `expected_version` ignored. UI 409 handling untested. |
| 10 | Unsaved narrative on refresh/navigation | **FAIL** | FAIL | Refresh warns. Sidebar navigation silently discards the editor. |
| 11 | EN/AR, RTL, 390 px | PASS | PASS | Run 1 punctuation mirroring fixed in 65fa389. |
| 12 | Non-owner runtime role, RLS, audit | PASS | PASS | Raw SQL as `ctm_app` proves RLS/trigger enforcement below the API. |

Per-check detail: `evidence/run*/api-results.json` and `browser-results.json`. Scenario rollup: `results.json`.

### Confirmed defects at the latest heads

1. **Council editor vs. backend write contract (council #3).** Backend `bb3e48b` requires `expected_version` on `POST /api/reports/{id}/revisions/` and returns `409 {error: version_conflict, current_version}`. Council `65fa389` `revisionPayload` sends only `{answers, observations}`, and its pre-save re-read cannot replace the field.
   - Every save from the UI fails with 422.
   - The UI shows the generic "could not be completed … try again", so retrying can never succeed.
   - Reproduce: browser `s2_edit_persist`, or api check "council editor request body".
2. **Unsaved narrative lost on in-app navigation (council #3), in both runs.**
   - Steps: Revise, type text, click Documents in the case sidebar, return to Reports and reopen the report.
   - Result: the editor is gone and so is the text, with no warning.
   - Refresh and close are guarded by `beforeunload`.

### Observations (not filed as defects)

- The server appends a version for a body identical to the current version (`expected_version` = current). The council editor prevents this client-side.
- Run 1 findings fixed by `bb3e48b`: 404-instead-of-403 under RLS, missing concurrency check, duplicate retry versions, unvalidated `files` ids in revisions.

## Existing implementation reviewed vs. authored here

- **Reviewed, not changed:** backend report read/revision routes (`tribunal/api.py reports, report_revision`), `tribunal/services/reports.py revise_report`/`validate_revision_content`, `tribunal/policy.py`, RLS/trigger migrations `0007`, `0011`, `0019`, `0023`, council `council-media.js` D19 editor and the shell patch.
- **Authored by this stream (QA only):** everything under `harness/`, `evidence/`, `results.json`, and this README.

## Limitations

- Test-issued sessions only. No provider login.
- Two separate runs. Heads that moved after run 2 started are not covered.
- External-priest-authored reports, medical/psychological report revisions and files inside interview answers were not exercised. Interview file answers must be subject-owned, so the services can't seed them. Non-text answers were exercised instead.
- Simulated conditions are labelled: the 500, 403 and lost-ack cases use Playwright request interception. The mid-edit reassignment denial and all concurrency checks are real server behavior.
- Runtime table grants follow the backend's test fixture, because no production grant script exists yet.
- Environment incident:
  - During run 1 a runtime-role report-list query ran on CPU for more than 3 minutes and could not be cancelled.
  - The Docker VM later showed severe disk stalls: a 141 s checkpoint, then an unkillable backend.
  - After moving PostgreSQL data to tmpfs, all suites ran normally with no query over 10 s (`harness/watch_queries.py`).
  - The slow query was not reproduced under a parallel load test, so it is not claimed as an application defect.
  - Restarting the hung Docker engine also stopped another session's local container `ctm-governance-integration-pg`. It was restarted immediately with its data intact.
- No merge, deployment, operational migration, credential change or external message was performed.
