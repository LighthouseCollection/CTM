# Backend runtime identity and list continuation

**Final isolated PostgreSQL: 617 passed, 1 skipped.** No model drift; migration
rollback/reapply through0039. No protected architecture changes.

Continuation of issue #2 after ff85717's two hosted checks passed. Backend owns
these API/test changes; no UI/shell/report version changes, merge, deployment,
operational migration, credential change or shared-engine operation is included.

## Account-query investigation and denial contract

Tests can now use SESSION AUTHORIZATION instead of SET ROLE. The HTTP test connection
has current_user=session_user=ctm_app, NOSUPERUSER/NOBYPASSRLS/NOINHERIT and zero
memberships in domain-table owners. Applicant/member/admin repeated session reads,
own draft saving and own history are exercised with a five-second statement limit.
This proves those SQL identities under the isolated fixture. It does not recreate
the applicant harness's physical login handshake, role startup settings, independent
container/engine state or complete browser sequence. No role passwords are changed.

The reported account SELECT stall is not reproduced by this bounded suite. Its
cause and the applicant-owned stuck disposable container remain unresolved; this
stream did not stop/remove that container or restart Docker. Preserve the original
trace and failed/incomplete acceptance runs. A successful local reproduction attempt
is not a claim that their environment is fixed.

Under non-owner RLS, private draft-history rows are absent to an unauthorized
caller: known private and nonexistent IDs return the same404
resource_or_input_invalid body. An explicit permission rule on an otherwise visible
request returns403 forbidden; unauthenticated requests return401. Own draft save
returns201 (new revision) and own history returns200. This documents existing
behavior; no private existence query or owner bypass was introduced. Preserve the
previous strict403/404 finding; a future run must record the contract and successor
SHA it uses rather than retrospectively changing the earlier result.

## Pagination contract

| GET endpoint | Default limit | Existing authorization/projection |
| --- | --- | --- |
| /api/cases/ | 100 | Council case visibility; applicant only actual linked cases. Existing item fields retained. |
| /api/cases/{id}/audit/ | 250 | Staff plus actual case access; source correction privacy still applied. Existing actor/source fields retained. |
| /api/system/audit/ | 250 | Admin/secretary only; existing safe event fields retained. |

All three accept single ASCII decimal `offset` (default0, nonnegative signed64-bit
range) and `limit` (1–250). Duplicate parameters, signs, fractional values and
out-of-range values return422 validation errors. Responses retain `items` and add
`offset`, `limit`, `next_offset` (next visible offset or null). Follow next_offset
until null to recover rows beyond the previous caps. No total is exposed: lookahead
establishes continuation without scanning the full private history for a count.

Rows sort by descending server created_at then descending UUID id, so equal
timestamps have deterministic ordering. Audit source visibility is evaluated before
visible offsets, limits and lookahead; hidden correction events do not create empty
pages or leak through next_offset. Iteration retains only one visible page plus
lookahead in memory. Large audit offsets may require scanning prior authorized
candidates; the API does not promise a snapshot during concurrent inserts. A refresh
starts at offset0. No total-byte, file-count or case quota was introduced.

## Evidence and remaining work

Regressions exercise the actual app SQL session identity, identical hidden/absent
history denial, more than100 tied-timestamp cases and more than250 audit events,
applicant foreign-case exclusion, invalid/duplicate page parameters, and returned
corrections hidden before both case and system audit page selection. Original
permission and lifecycle tests remain in the full suite.

No model, route, grant or migration is added. Inventory remains63 domain models,
91 routes and63 forced-RLS tables, migrations through0039. UI must bind the returned
continuation fields and governance must integrate/retest the exact delivered SHA.
The unproven external stall and applicant Docker recovery remain separate from
approved content, normalized-schema work and live-service acceptance dependencies.

## Subsequent acceptance coordination

Governance authorizes coordinated testing on the existing fictional CTM VM database.
Disposable Docker recovery is not an acceptance prerequisite. Governance alone
serializes shared migrations/deployment; physical provider-authenticated acceptance
requires its designated identity/private harness. Historical stall evidence above
is preserved; passing isolated SQL-session tests does not establish its root cause.
