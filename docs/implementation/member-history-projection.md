# Council appointment and assignment-role history

Admin/secretary-only read APIs for existing council accounts, including inactive
accounts:
- GET /api/system/accounts/<uuid>/memberships/
- GET /api/system/accounts/<uuid>/role-history/

Both use offset/limit/next_offset (default50, maximum250), preserve retained records
and return account_id, account_role, account_active. account_role is the current
legacy Account projection; it is not an invented historical appointment/grant.
Applicant targets and nonexistent IDs return identical404; unauthorized callers
receive403, anonymous401. Other methods return405. Private/no-store headers remain.
No status, role, provider identity, session or underlying record is changed by GET.

Membership items: id, actual tribunal{id,code,name_en,name_ar}, appointed_by_id,
recorded_at(created_at), active_from, active_until and assignment_scope_current.
Order is descending active_from then UUID. Expired/future/other-tribunal records are
retained. The scope flag is true only when the target is active, the configured
current tribunal matches, and the stored interval includes the projection time.
It is not itself a permission grant.

Role items: id, membership_id, role, granted_by_id, recorded_at(created_at),
revoked_at, revocation_event and assignment_authority_current. Order is descending
created_at then UUID. The current flag requires a president/admin/secretary grant,
no revocation, and current membership scope. It describes that assignment grant,
not all system authority. Existing Account.role fallback and assignment services
remain authoritative; a legacy president can have no StaffRole rows. These flags
do not grant system administration or alter decree/approval permissions.

revocation_event is the actual latest retained assignment_authority_revoked event
for that StaffRole: id, actor_id and timestamp. If no retained event exists it is
null, even if revoked_at is recorded. A null actor stays null. No historical actor,
date or revocation evidence is inferred from the current administrator. Revocation
lookups use correlated queries and the existing source/source_id/action audit index.
Rows outside the requested account never enter pagination.

Current authorized account email remains available through the existing account
detail API. Phone, portrait, clinical/contact details and unsupported appointment
facts are not invented. No sample institution/content is seeded. This is projection
of existing retained StaffMembership/StaffRole/AuditEvent records, not completion
of normalized account/identity/provider history or institutional schema parity.

Twelve restrictedctm_app tests cover actual service-authored appointment/grant/
revocation records, real actors, admin/secretary viewers, inactive/ended/future/
other-or-missing-scope preservation, legacy unknown provenance, denied targets and
roles, read-only behavior and53-record pagination. Full PostgreSQL718 passed,1
skipped. No model/policy/grant/migration change;99routes/63domain models/63forced
RLS tables, migration leaf0041.

Governance owns serial integration; UI binds approved member/account screens and
labels; QA independently records the exact successor SHA. No backend merge/deploy.
Profile mutation/version rules, portrait/contact editing, provider/email history,
additional institutional canonical records and full semantic acceptance remain open.
