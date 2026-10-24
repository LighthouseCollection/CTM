# Own active session administration

## API contract

GET `/api/account/sessions/` is available to any active authenticated account.
It returns items with only `handle`, `current` and `expires_at`, plus offset/limit/
next_offset (default50, maximum250). Ownership and valid authentication checks
precede pagination. A row must be unexpired, signed/decodable, use a configured
authentication backend, belong to the actual actor and carry a valid session auth
hash (including configured secret-key fallback). Foreign/malformed/expired/invalid
rows are excluded. Ordering is descending expiry with a deterministic server-only
session-key tie-breaker. Concurrent session creation/expiry can change offset pages.

POST `/api/account/sessions/<handle>/revoke/` accepts `{}` only, with normal CSRF.
No account ID or privilege claim is accepted. Handles are actor-bound HMAC-SHA256
values with a dedicated salt; no raw session key, authentication hash, token or
provider subject appears in the projection or audit. A handle cannot authenticate
or revoke another account's session, even for council/admin users or if a foreign
key is otherwise known. Expired, foreign, invalid and absent sessions return the
same404 resource_or_input_invalid response. A repeat after successful revocation
also returns404 rather than confirming historical existence.

Success returns `{revoked:true,current_session:boolean}`. The selected session is
deleted and an immutable account_session_revoked audit records the actual actor,
account source, opaque handle and current-session flag in one transaction. The
account row is locked and active status rechecked, coordinating with suspension.
Audit failure rolls back deletion. Revoking a different session leaves the caller
signed in. Revoking the caller's current session invalidates its next request;
the UI should leave the authenticated workspace immediately after success.
API responses retain private,no-store headers. The listing adds no session renewal or expiry mutation. No new inactivity timeout, auto-revocation schedule or provider claim is added.

## Evidence and limitations

Restrictedctm_app HTTP tests cover all five roles, safe projection, hidden/absent
responses, foreign-key handle forgery, selected/current revocation, retained actor
history, expired/corrupt/invalid-hash/unsupported-backend rows, ownership before
pagination, invalid pagination/body, authentication/CSRF and atomic audit rollback.

This uses existing Django session storage and app grants; no migration, new role,
provider credential, signup or RLS change. Existing suspension revocation remains.
Django sessions do not store reliable device/IP/creation/provider-expiry facts;
those are deliberately absent. expires_at is Django session expiry, not proof of
current provider validity. Existing provider authentication and suspension checks
remain authoritative. After SECRET_KEY rotation, refresh the list to obtain handles
under the new key. No handle survives as an independent authorization credential.

The adapter scans active Django sessions to filter ownership; it has no indexed
account-session foreign key. This is bounded response/memory, not constant-time
query cost. Normalized retained account_sessions/provider identity mapping, scalable
account indexing, provider validity/revocation metadata, explicit multi-provider
link/email verification and broader admin-session history remain unfinished.
Do not claim this adapter equivalent to the approved normalized schema.

Governance owns serial integration and test deployment, UI binds the exact contract,
and independent QA records its combined-build SHA. Backend does not merge/deploy.
