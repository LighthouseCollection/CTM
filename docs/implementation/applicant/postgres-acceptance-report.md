# Applicant PostgreSQL runtime acceptance: incomplete

This checkpoint adds an isolated PostgreSQL browser/API runner and records failures. It does not claim a full PostgreSQL pass or change backend policies. Backend source is bf69dbc79aaeda6ecfa34433c075f28ba2e7b750; integrated shared frontend104e4fd is retained with the named applicant assets/minimal hook. This is a disposable review assembly, not a governance integration commit.

## Verified runtime facts

HTTP connections authenticate directly as ctm_app: current_user=session_user=ctm_app, no superuser, no bypass-RLS, NOINHERIT, zero memberships in a domain-table owner. All63 implemented domain tables have row security and forced RLS. Fixture setup uses a separate owner connection; the HTTP thread receives a copied connection configuration, not SET ROLE from a superuser session.

Existing services were not reused, restarted or stopped. Each test creates a uniquely labelled loopback-only postgres16 container and fresh synthetic roles/database, with no operational credentials or data. The first runs cleaned up normally. The last container has a cleanup blocker described below.

## Distinct run outcomes

| Run | Completed checks | Result / limit |
| --- | --- | --- |
| Original strict suite | Five scenario groups: draft start/save, file gating, language, concurrent version rejection and immutable history | Stopped at private history denial: expected403, received404 resource_or_input_invalid. No source history disclosed. Existing assertion remains unchanged. |
| Earlier focused run | Three groups: actual own draft browser save; outsider/council private-read and foreign-write denial; required-original upload/download and foreign-byte denial | Then declaration checkbox remained gated. This is an incomplete harness journey, not proof that submission failed server-side; later harness revisions explicitly wait for document and checkout readiness. |
| Latest focused run | No completed focused groups; strict prelude had completed five | Browser timed out waiting for the draft-save response. Own pg_stat_activity showed a ctm_app account SELECT active over100seconds, later190seconds, with no reported wait event. Cause unverified; cannot attribute it to policies, JIT, database or host without further evidence. |

Do not sum these overlapping groups. No payment, return/resubmission or notification acceptance is claimed from this PostgreSQL attempt. A fresh regression rerun passed all76 SQLite candidate groups and94 frontend tests after the harness changes. One earlier SQLite recovery-notice wait failed; the unchanged assertion passed on rerun, so that transient result is not hidden or treated as a new product fix. SQLite evidence remains scoped to SQLite.

[Strict interruption JSON](postgres-api-interrupted.json) | [Earlier focused partial JSON](postgres-focused-result.json) | [Runtime stall and cleanup JSON](postgres-runtime-stall.json)

The focused helper permits403 or404 only for explicit non-disclosure assertions, records every observed status, and checks no answers/items/source statement appear. It does not replace or relax the original strict403 suite. Backend/governance must resolve that outward status contract. The current applicant frontend already handles both403 and404 as unavailable/access denied.

## Cleanup blocker: exact dependency

Container ctm-applicant-test-a9460e5e2058 remains reported running after Docker refused both stop and force-remove with `tried to kill container, but did not receive an exit event`. Its ownership label was verified before cleanup actions. PostgreSQL cancellation/termination acknowledged but did not end the observed active backend; a container-specific process termination attempt did not recover it. The verified owned Windows Python test process tree was terminated. No governance/WordPress container or shared Docker engine was restarted.

Operator/governance must coordinate recovery of that one disposable container or engine state when other workloads can be protected. This stream does not authorize interrupting them. New runner preflight refuses to start another applicant container while one remains. Docker preflight/launch/readiness/port/cleanup calls, owner connect and test process are now bounded; cleanup verifies disappearance rather than assuming stop means removal. These safeguards are reviewed source changes; they have not been exercised in a new Docker run while the prior container is blocked. The cleanup path writes cleanup.json in the ignored target archive. Future fresh fixture roles have15s statement/5s lock timeouts; these are test controls, not production tuning and not proof of a fix for the already-stalled query.

## Reproduction and ownership

After resolving the owned-container cleanup blocker, run `uv run --group browser python scripts/browser_applicant_postgres.py`. It archives pinned sources, preserves integration-only UI/report-version fixes, captures applicant asset/patch hashes, migrates only its disposable DB and invokes the same applicant runner. Result JSON distinguishes full success from interrupted runs. Failures and owned-container cleanup errors deliberately return nonzero.

No product/shared/backend source, protected specification, migration or operational credential was changed. Runtime-created fixture passwords are not printed or persisted in evidence. The test has no real login, charges, recipients, institutional wording or scan-provider acceptance.

## Remaining

Backend/governance: decide denied-resource403/404 contract and investigate the observed account-query stall after environmental recovery. Institution/configuration owners: approved EN/AR bound fields/help/choices/declarations. Backend: authoritative repeat validation, textarea vocabulary, semantic/evidence binding and MC/CMC meanings. Governance: successor integration and complete exact-SHA runtime acceptance. These remain separate from the completed five-family UI fixture verification.

Independent review confirmed ownership isolation and the timeout/removal-verification corrections, with no further concrete findings. Live verification of the hardened cleanup remains blocked by the existing container state.
