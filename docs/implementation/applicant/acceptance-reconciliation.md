# Applicant acceptance reconciliation

Checked 2026-10-21 Pacific against backend `7684169d998cd2678757f8431378eaec8fdd1258`.
References: GitHub #9, original Fxx/AS-Fxx acceptance review and later direct-owner
clarifications on main. External review findings are hypotheses until verified.
All checks below use isolated synthetic records; no live provider/antivirus claim.

| Finding | Current evidence | Status |
| --- | --- | --- |
| F03 repeats | Renderer preserves record IDs/opaque fields and creates UUIDs for new records; browser/API persistence covered. Full approved repeat labels and nested backend validation remain dependencies. | Partial |
| F04 own current files | Actual browser upload/list/download/replacement; old bytes retained, owner old-version download denied; latest pending scan event blocks current download and checkout. Earlier404 report is stale. | Addressed within isolated API/browser scope |
| F08 / AS-F08-1 | Direct-owner D1 requires last formal submission only to council until resubmission. Opt-in real HTTP probe below fails7/8 predicates. | Verified current backend gap |
| F09 resubmit | Actual returned instructions, review and browser resubmit reuse original fee/signature. Pending required-file scan rejects resubmit with422 atomically; submission count/fee stay unchanged. Successful resubmit creates a new submission referencing the original attestation, which remains unchanged. No attestation in resubmit payload. Concurrent staff review and complete snapshot linkage remain separate backend acceptance. | Partial |
| F25 / AS-F25-1 | Staff manifest retains formal file ID after correction, but current listing/download exposes a pending, unsubmitted correction. This probe uses a technically clean replacement, not the full pending-scan AS-F25-1 variant. | Partial; F08 byte boundary fails |
| F34 / AS-F34-1 | Chrome/errors/notices EN/AR; authored instructions stay unchanged. Applicant case reference and invitation/payment timestamps use bidi isolation. Submitted state no longer prompts new filing. Notification/email localization scenario not claimed. | Partial |
| F35 duplicate hold | Actual browser save succeeds with an explicitly set synthetic hold. Projection blocks checkout/submit; submit HTTP422 rejects duplicate hold; real checkout-preparation service rejects eligibility before creating an intent. Checkout HTTP is independently blocked by unconfigured provider. EN/AR notice respects edit permission. Exact person matching and hold assignment/release lifecycle remain backend acceptance. | Partial |
| F36 lifecycle | Actual process_drafts ignores a returned filing with500 idle days; status/revision/file counts unchanged. Actual draft-delete HTTP422 rejects returned filing and original bytes survive. Returned UI has no draft-delete/expiry action or new signature/payment. Shared withdrawal/claim closure and PostgreSQL worker acceptance remain separate. | Partial |

## Returned-correction privacy probe

Run `scripts/browser_applicant_api.py` with environment variable
`CTM_APPLICANT_ACCEPTANCE=returned_privacy`. It creates a fresh isolated backend
archive/database, performs real initial submission and completeness return, saves
a corrected first name through the browser and uploads a same-context MC correction.
Before resubmission, an authenticated administrator calls actual detail/history,
case-file listing and file download/range/preview routes. This mode intentionally
exits unsuccessfully until all eight privacy predicates pass. It is separate from
the20 passing baseline scenario groups and must not be counted as a pass.

Current result: council detail/version/history expose pending answers, case listing
exposes the pending file and direct/range/preview requests return pending bytes.
Only the formal manifest predicate passes. [JSON evidence](returned-privacy-result.json)
records exact booleans and backend SHA without personal records or credentials.
Search, routine correction notifications and PostgreSQL RLS remain untested here.

VM-FRM owns the correction across projections, byte authorization, search and alerts.
Hiding frontend links cannot repair access through authorized HTTP requests. Applicant
own correction access must remain usable; resubmission must expose the new formal
snapshot while preserving earlier submissions/originals. No shared backend or
protected specification changes are made in the applicant stream.

## Private appointment integration

Backend `7684169` supplies the owner-only read route. Actual HTTP/browser checks
cover staff scheduling, owner confirmation, rescheduling to version2, stale-version
422, owner rejection with reason and cancellation. Outsiders receive an empty list
and403 on response; applicant council-session read is403. The projection does not
include other-party or council agenda details. This replaces the former missing-read
dependency; PostgreSQL invitation policies and real notification delivery remain
separate acceptance surfaces.
