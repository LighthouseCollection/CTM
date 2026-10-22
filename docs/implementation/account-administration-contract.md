# Account administration and returned filing continuation

## Completed implementation

Admin/secretary APIs:
- GET `/api/system/accounts/`: bounded pagination (100 default, 250 maximum), optional role and active filters.
- GET `/api/system/accounts/<uuid>/`: safe account projection.
- POST `/api/system/accounts/<uuid>/status/`: exact enabled boolean and mandatory expected_version integer.
- GET `/api/system/accounts/<uuid>/status-history/`: bounded actual suspension/reactivation audit history.

The projection includes identity, role, active/verified flags, UI/notification languages,
creation time, status_version and permitted status controls. It excludes passwords,
provider subjects, tokens and invented profile/contact/appointment fields.
status_version counts retained status changes; it is not Account.row_version or a
version of all account attributes. Stale changes return409. Self suspension and
suspension of the last active administrator remain denied. Suspension revokes the
target's Django sessions atomically. No-op requests create no duplicate status event
or notice. Status history retains real actor/time and returns null for absent legacy
metadata. Directory queries batch status counts;0040 adds account_status_events_idx.

Case listings additionally return assigned_member_id (UUID or null), preserving the
existing display name so duplicate names do not determine My Cases identity.

## Source-bound applicant notices

Applicant status changes require the configured account_suspended/account_reactivated
email template and the recipient's en/ar notification language before any mutation.
Missing/invalid content returns422 without changing status, sessions or audit history.
Subject/body/language/template revision are frozen into the queued notice. No sample
wording is seeded. Subjects reject CR/LF. API notice_queued is not delivery evidence.

Notification/Outbox INSERT policies validate the exact actor, account status event,
current status/version, recipient, canonical key and retained template revision.
The worker receives only the proven destination and frozen message through its
existing private getter; it gains no broad account/settings read permission.
A valid status notice can reach a suspended applicant, but still requires a verified
email and successful SMTP acknowledgement. Obsolete status jobs are superseded.
Tampered payloads fail proof and roll back the entire change. Other email kinds keep
their existing delivery behavior. Credentials remain operator-managed dependencies.

## Returned petition policy correction

Applicant10654a7 reported Party.save() RLS failure after return when optional spouse
DOB was absent. The regression reproduced it.0041 adds a narrow returned-filing
branch to ctm_filing_case: eligible own filing, original submitted petition, same
bound owner/person/party/case/proceeding, open case and proceeding, and retained
owner-authored Submission. It does not depend on optional or subsequently corrected
DOB matching the frozen case identity. Other filing checks remain unchanged.
Four actual ctm_app SQL-session HTTP regressions cover spouse DOB present/absent and
name/DOB corrections, return, resubmit and replay, preserving original submission
answers/manifest/attestation/actor, party reference and case identity snapshot.

## Integration and remaining work

Governance owns serial application of0040 then0041, with database/media backups and
no concurrent operational migration.0040 builds a normal transactional index; plan
its table-lock window.0041 reverses to the original helper. No new role, credential,
public authentication bypass, merge or deployment is included.

Awaiting exact successor-SHA UI binding and authenticated integrated acceptance.
Profile/contact/portrait edits, verified email/provider administration, explicit
session inventory/revocation UI, membership/appointment history and normalized
approved schema facts remain separate unfinished contracts. The151-table field
inventory is reconciliation evidence, not schema equivalence acceptance.
