# Authorized request author display projection

## Confirmed blocker and correction

Governance/applicant reported exactdccbd638 private-clone acceptance stopped after
34outer groups: three valid sent requests were readable to their subject applicant,
but their administrator author Account was correctly hidden by RLS. Dereferencing
x.author.first_name/last_name raised Account.DoesNotExist and the endpoint converted
that to generic404. Backend reproduced this with real admin-authored intake/medical
and assigned-member-authored psychological requests, without replacing fixture authors.

GET /api/cases/<case>/requests/ retains its fields and author display string. It
materializes already-authorized request rows with subject only, then uses a bounded
request-ID-based author-name projection rather than dereferencing an Account FK.
No Account SELECT policy is widened; the administrator remains hidden before and
after successful projection. No subject, request author or historical record is changed.

0043_request_author_projection adds only ctm_request_author_names(uuid[]), a stable
SECURITY DEFINER read function with fixed pg_catalog/public path and explicit table
qualification. PUBLIC execute is revoked; only the existingctm_app runtime role is
granted execute. Workers are not granted it and are also denied by its caller check.
The function returns request_id plus the actual current staff display name only;
no Account row/id/email/role/provider subject/token is returned. This preserves the
previous current-name behavior; it does not invent a historical name snapshot.

Authorization is repeated inside the function: council may read council request
metadata; an applicant must be the real bound party for that request's case, and the
request must be sent, not draft, and neither external_priest nor interview. No actor,
unknown/foreign Account-or-request UUID and excluded request produce no result.
At most250 input IDs are accepted per call. The service batches larger lists without
silently dropping valid requests or changing request-state/capability behavior.
SQLite uses a filtered current-name lookup after the same endpoint filters. Neither
path fabricates an assigned author or opens an account directory.

## Evidence and integration

Twelve actualctm_app SQL-session tests cover three visible requests and hidden admin
Account, assigned member author, all four council roles, private/external/interview
exclusion, outsider hidden/absent404 equality and direct helper denial, no actor,
worker execute denial, inactive source author and batching/oversize limits.
Full PostgreSQL751 passed,1 skipped; rollback/reapply through0043. C05 privacy and
strict medical boolean consent tests remain in the full run. This is synthetic
isolated verification, not completion of the retained clone's broader acceptance.

0043 follows0042_council_request_file_privacy, which follows already-applied0041.
No new model, route, row policy, role or credential;99routes/63models/63forced tables.
For roles provisioned before migrations,0043 grants execute during install. If
ctm_app is created after migrations, run0043.grant_runtime in the migration-owner
provisioning context after the existing0038 grant plan; this is one new app-only
function privilege, not a broad Account grant. Named-role tests exercise this path.
Do not change published0038 or reuse applied0040/0041.

Governance serially integrates/apply0042 then0043 with recoverable snapshot and gives
applicant/QA the exact combined successor. UI PR22's separate unapplied competing
0040_session_workspace_metadata must be ported to a unique coordinated successor
(proposed0045after0044), not a parallel leaf or renamed applied migration. Backend
has not modified that UI branch or the server.

Applicant reruns the real administrator-authored request stage and later groups on
that exact successor, preserving focused7/7 and partial34-group history separately.
QA independently verifies both this projection and C05 clean-scan negative access.
No merge/deploy or operational migration by backend; broader provider/schema/content
and full acceptance work remains open.
