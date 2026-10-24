# Council UI checks — runbook

How the council stream produced its frontend evidence, so anyone can repeat it. None of this replaces the PostgreSQL CI, real-API browser integration or provider-login acceptance.

## Unit tests (no install)

```sh
node --test tests/frontend/
```

Node's built-in runner only. The council suites (`council*.test.cjs`) cover permission display rules, request payload shapes, Los Angeles time/DST handling, EN/AR word coverage, duplicate-key and inline-style guards, the decision catalog against `decisions.py` and `prototype-decision-types.json`, and the shell script order.

## Synthetic browser fixture

```sh
node scripts/council_fixture.cjs 18850 secretary                 # current main contract
node scripts/council_fixture.cjs 18851 member --contract=pr7     # backend PR #7 projections
```

Then open `http://127.0.0.1:<port>/` in a browser. The fixture serves the real `shell.html`, `app.js` and council modules with the pinned Plenix CDN, and stubs the council endpoints in memory with synthetic records only. Roles: `secretary`, `member` (assigned to case `20261001-01`), `president`. Switch role without restarting:

```js
await fetch('/__role/', { method: 'POST', body: JSON.stringify({ role: 'member' }) }); location.reload();
```

Every POST the UI sends is recorded at `GET /__posts/` so payloads can be checked exactly. Closed case `20260901-01` carries a heard pending appeal and a later petition (F12); session `2026-11-05` is planned and empty.

### What each check verified

For each slice: validation blocks the request (nothing in `/__posts/`); the success path sends the exact payload; server error text is shown verbatim; member versus secretary versus president controls; Arabic (`dir=rtl`) and English at 1280 px and 390 px; zero application `[style]` attributes (DataTable column widths are Plenix's own); no horizontal overflow; no console errors apart from the expected 405 decision probe on the main contract.

## Combined shell patch check

`docs/implementation/council/shell-integration-after-applicant.patch` is the council shell hook rebased onto Desktop-R's applicant patch. To smoke-test both together: apply the applicant patch then this patch to a clean `main` worktree, copy in the applicant and council modules and the fixture, start the fixture, and open each council page (all rendered, no console errors, at the time of writing).

## Not covered here

Real Django APIs and database, PostgreSQL RLS, provider sign-in, file scanning, email delivery, payment providers, and server-side lifecycle rules. The server remains authoritative for every permission.
