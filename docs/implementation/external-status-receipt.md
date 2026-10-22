Current validation: **833 PostgreSQL passed, 1 skipped**, migration rollback/reapply through0047 and no model drift. Nineteen new physical-role status/receipt checks plus one cross-adapter endpoint lifecycle; SQLite lifecycle separately passed. Council UI/integration acceptance remains required.

# Capability-bound external report status and receipt

Backend issue #2 / council C05. Migration0047_external_status_receipt after0046.
New read-only GET `/external/reports/{request_id}/status/` requires the exact
issued `Authorization: Bearer <token>`; cookies, query tokens and account roles
cannot substitute for that capability. No frontend files are edited.

Success returns exactly `state`, `expires_at` and `receipt`. States are active,
expired, completed, cancelled, closed or unavailable. Receipt is null except for
an unexpired completed request with an actual authorless external Report, when it
contains only that report's ID and retained creation time (`completed_at`). It
never returns testimony, drafts, case or party identifiers, names, instructions,
email, token/hash or report history. Correct expired capabilities get expired
with no receipt. Completed receipt takes precedence over subsequent case closure
while the original capability remains unexpired; this confirms receipt only and
does not authorize any new report read or mutation.

Wrong/missing/cross-request/reissued capabilities and absent IDs all return the
same403 `{"error":"link_unavailable"}`. Never-issued requests cannot be enumerated.
Reissue invalidates the old digest. All non-GET methods return405. Private/no-store,
no-referrer and nosniff apply; responses vary on Authorization. Existing report
GET/POST semantics are unchanged: completed/expired links remain unusable there.
Status reads do not reopen links, create reports, mutate source content or extend
expiry. A lost submission acknowledgement can be checked without a second write.

0047 installs one stable read-only SECURITY DEFINER JSON projection with fixed
search_path. It selects only the request bound to the server's external context
and exact stored token digest, and joins only that request's proceeding/case/report.
It returns no ordinary row access. PUBLIC execute is revoked; only existingctm_app
is granted, neverctm_worker. For roles created after migrations, run0047.grant_runtime
after the documented0038/0043/0044/0046 grant plans. Reverse drops the function;
roll back matching service code too. No domain table/model or existing policy
changes. One additive URL. Coordinate unapplied UI metadata to unique later0048;
never alter applied0040–0046 history.

Nineteen physicalctm_app regressions cover lifecycle, minimum output, completed/
expired mutation denial, missing/wrong/cross-request/reissued/query/cookie/basic
auth concealment, original-source preservation, old GET behavior, worker/no-scope
function denial and read-only methods. One additional endpoint lifecycle contract
runs on PostgreSQL and SQLite; SQLite's active→completed→expired path also passed
separately. Test capabilities/content are synthetic and remain local.

Council owns using the new status/receipt API; old page behavior is not claimed
updated. Governance integrates/migrates serially, then council and independent QA
must record the exact combined SHA. Browser entry e0e95fd requires council static
assets; this projection does not deploy them. Recording, printable/paper completion
and actual invitation delivery remain unfinished; no delivery/scan/provider
success or approved content is invented. No operational database, merge or deploy
was performed by backend.
