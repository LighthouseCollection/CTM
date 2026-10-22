# Council member creation and display-name editing

Backend issue2, draft PR7. Only an existing active `admin` may use these APIs;
secretary, president, ordinary member and applicant access is denied. Council/UI
owns the forms and navigation. These APIs are not public enrollment.

## List

`GET /api/system/members/` returns council accounts only, including inactive
accounts, with bounded offset pagination (default100, maximum250). Names and
profile_version are selected in one SQL snapshot; no per-row version lookup.
The same admin-only rule applies. Applicant accounts are excluded.

## Create

`POST /api/system/members/`

```json
{"email":"member@example.test","first_name":"Given","last_name":"Family","role":"member"}
```

Allowed fields are email, first_name, last_name, optional role (member default;
member/president/secretary/admin) and optional preauthorized microsoft_subject.
Names must be nonblank text up to150 characters with no control characters.
The current `CTM_TRIBUNAL_ID` must identify an existing tribunal; no institution
is inferred or created. Unknown fields are rejected.

One transaction creates an account through the existing guarded enrollment
service, an explicit StaffMembership appointed by the actual administrator and a
matching enrollment StaffRole granted by that administrator. Each source retains
its actual creation time/actor and audit record.0050 adds baseline `member` to the
existing admin-only staff-role INSERT policy. Existing assignment-authority
resolution and role-revocation services keep their prior scope.

Email is normalized; an existing account with a case-insensitive matching email
returns422 rather than converting an applicant, replacing a council account or
merging identities. Duplicate immutable provider subjects return409. An identical
create retry does not return the old record; it encounters the duplicate email
check. The email lock and existing database uniqueness prevent duplicate creates.

The account has an unusable local password, no superuser flag and no fabricated
provider verification. Preauthorizing a Microsoft subject is not authentication:
the existing validated Microsoft tenant/subject callback must still succeed.
Creation sends no invitation and does not prove that the recipient can sign in.

Success201 returns id, first_name, last_name, email, role, active, email_verified,
profile_version0, membership_id and enrollment_role_id. It never returns a
password, provider subject or token.

The existing `POST /api/council/enroll/` remains a compatibility account-enrollment
API; it already existed and is not retroactively equivalent to explicit tribunal
membership. New member-management UI should use the new endpoint. Do not invent
historical appointments for legacy accounts without source evidence.

## Read/edit

`GET /api/system/members/{account_id}/` returns the safe profile above (without
the create-only membership/grant IDs). Applicant targets and unknown IDs return404.

`POST /api/system/members/{account_id}/`

```json
{"first_name":"Corrected","last_name":"Name","expected_version":0}
```

Supply either/both name fields and a mandatory nonnegative integer expected_version.
Profile version counts retained `council_member_profile_changed` account events;
it is separate from status_version and is not an all-attributes row version.
The target account is locked. Stale versions return409; a matching-version no-op
does not add another event. An actual change records before/after names, actual
administrator and incremented profile version in the same transaction. Audit
failure rolls back the edit. Existing inactive council accounts may have their
display names corrected without reactivation.

0050 adds a narrow branch to the existing account trigger: bound member_profile
operation, exact target, actual admin actor, existing council role, and only
first_name/last_name may differ. Other mutations retain their original guards.
Raw unbound changes, secretary changes, worker changes and attempts to change
role/email/provider/verification/status with the profile context are denied.
No new runtime table/function grants or new tables are added.

The account display name changes; the canonical Person record, signed submissions,
case identity, email, provider subject, roles, preferences and status are retained.
This is not a normalized person-version migration or factual identity correction.

## Integration, rollback and remaining scope

Governance applies0050 after0049 in its chosen successor build. UI's separate
unapplied metadata migration needs a unique0051-or-later identity; do not rename
applied history.0050 rollback restores the prior account guard and staff INSERT
policy, retaining existing names, role rows and audits; old code cannot make new
profile edits after rollback. Existing admin/secretary account directory and
status management APIs remain available separately.

Contact/portrait editing, email verification/provider changes, changing an
existing account's base role, membership termination UI, full normalized identity
history, and user self-profile edits remain unfinished. They are not enabled by
this name-edit endpoint. Council UI integration and independent QA against the
exact governance-selected successor SHA remain awaiting acceptance.

No live credential, email delivery, merge, deployment or shared-server migration
is part of this delivery.

## Validation

902 PostgreSQL tests passed,1 skipped on the final implementation; no model
drift. The full suite includes rollback/reapply through0050 and28 new member
checks: actual app/session role, directory continuation, creation roles, actual
appointment/grant actors, unverified provider-only account, edit CAS/no-op/Arabic,
identity retention, invalid/privilege fields, duplicate/applicant protection,
configuration dependency, atomic audit failures and raw SQL guard denials. The
member HTTP contract also passed separately on SQLite. No council frontend or
live provider acceptance is inferred from backend tests.
