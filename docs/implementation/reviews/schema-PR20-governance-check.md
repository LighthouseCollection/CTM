# Governance review of schema PR20

Reviewed source PR20 at27c53cd against integrated backend48b80c4. This accepts the report as a complete structural inventory, not a completed schema or authorization assessment.

## Verified
- All151 approved table names appear exactly once; none missing or duplicated. Status counts reproduce3 implemented/110 partial/37 missing/1 decision-needed.141 rows are labelled code-based and10 inferred; do not present inferred rows as executed proof.
- Person identity fields are assigned in-place in applications.py435-439; formal answers remain versioned elsewhere, so the precise gap is missing independent canonical identity-version provenance, not loss of every submitted identity value.
- Django database sessions use framework storage without the approved app_sessions hash adapter. Framework session/provider tables have app-role grants. This is a design/least-privilege gap requiring a deliberate migration; raw-key storage alone is not proof of an exploit or data leakage.
- Provider adapter already enforces configured Microsoft tenant and preauthorized subject. The report's missing normalized issuer/tenant/revocation fields must NOT be described as absence of all tenant validation.
- Existing decree entitlements/medical scope/attestation have retained JSON and permission helpers. Missing approved normalized rows/provenance constraints remain gaps; absence of a dedicated table alone is not proof access is unguarded.

## Reconcile before implementation
- DN1: owner already approved the later-spouse closed-case queue/new-information behavior. Only representation in the approved petition/appeal schema remains a design mapping question; do not ask the owner to repeat the workflow.
- DN2: preserve existing own withdrawal and admin-on-behalf rules and joint agreement. Secretary unilateral authority was not approved. Do not grant it from a combined ambiguous answer.
- DN3/DN4: session metadata and profile-photo ownership remain documented gaps; prototype fields alone do not authorize arbitrary schema changes.
- DN5: unknown/missing states need field-specific rules; known required/no-Unknown restraining-order fields and permitted Unknown spouse/child fields are already decided.
- DN6: UUID/created_at exceptions for natural-key claims/counters are an explicit contract design reconciliation; do not silently change protected spec.

## Outcome and remaining work
Report is useful prioritized input, not a migration plan or release acceptance. Backend owns additive retained-history migrations; governance retains final semantic reconciliation. New account-status and returned-party policy0040/0041 postdate the report; refresh those claims before assigning work. Decree proceeding uniqueness, medical disclosure scope/provenance, link reissue history, identity/session migrations and normalized factual assertions require independently reviewed change designs and data-preserving backfills. No replacement table-by-table rewrite or permissions relaxation authorized here. Full semantic151-table parity remains unfinished.
