# CTM application

This is the new Django application repository. The earlier prototype is preserved separately in `LighthouseCollection/ctm-alpha`.

**Current delivery: tested backend with an initial Plenix browser shell, not a complete public application.** Full applicant/council workflows, schema reconciliation, remaining row policies, live providers, complete Arabic acceptance and processing remain unfinished. See [implementation status](docs/implementation/status.md) before deploying.

The approved requirements remain in [the consolidated build contract](docs/architecture/build-spec/README.md). That contract contains 151 planned physical tables; the initial Django migrations implement only part of it. Do not run the structural SQL beside Django migrations or treat the present smaller model set as an approved replacement architecture.

## Development

Use Python 3.12 and `uv`:

```powershell
uv sync --frozen
uv run pytest -q
uv run python manage.py check --settings=ctm.settings_test
uv run python manage.py makemigrations --check --dry-run --settings=ctm.settings_test
```

SQLite tests are a fast secondary check. PostgreSQL is the authoritative validation target, including concurrency and database triggers:

```powershell
$env:CTM_TEST_DATABASE_URL='postgres://isolated_test_user:password@localhost:5432/ctm_validation'
uv run pytest --ds=ctm.settings_postgres_test -q
```

Use a dedicated disposable database/account with CREATEDB for pytest, never the operational CTM database. Do not use `settings_test` or `settings_postgres_test` for a public service. Their relaxed transport and scan settings exist only for isolated validation.

## Contents

- `tribunal/models.py`, `tribunal/migrations/`: initial persistent domain model and guarded PostgreSQL history.
- `tribunal/services/`: explicit authorized workflow commands.
- `tribunal/api.py`, `ctm/urls.py`: authenticated JSON endpoints; mutation requires CSRF, except scoped external capabilities and signed payment webhooks.
- `tribunal/reference/question-bank.json`: 59 accepted English questions, copied exactly.
- `deploy/`: Compose/Docker packaging, separate validation image, environment example and initialization scripts.
- `tests/`: lifecycle, privacy, payment, report, appeal, historical, concurrency and safety regressions.
- `.github/workflows/backend.yml`: PostgreSQL CI validation.

No application passwords or demo login bypass are provided. Provider logins require protected configuration. The reference seed keeps declarations unpublished until approved bilingual text is supplied. `seed_demo` is explicitly gated and creates fictional accounts with unusable passwords.

`python manage.py check_readiness` deliberately fails while public-deployment blockers remain. A successful container build or health response is not proof of production readiness.

## Browser checks

The root and `/accounts/login/` serve the same pinned Plenix 0.58.0 React shell. Sign-in providers appear only when configured. Existing APIs provide role routing, initial case/session/application views, case communications and self-service language settings. Disabled destinations are not implemented yet; the filing and report editors remain unfinished.

```powershell
uv sync --frozen --group browser
uv run --group browser playwright install chromium
uv run --group browser python scripts/browser_smoke.py
```

The smoke test starts a loopback-only temporary server, loads real CDN components and intercepts authenticated API responses with fictional fixtures. It checks UI interactions, not Microsoft/Google authentication. For the current LAN resolver workaround, set `CTM_CDN_LAN_IP=10.0.0.20`; normal TLS validation remains enabled and production CDN links are unchanged. `CTM_BROWSER_EXECUTABLE` optionally selects an already installed compatible Chromium executable. Screenshots go to ignored `.tmp/`.
