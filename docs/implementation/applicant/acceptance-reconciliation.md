# Applicant acceptance reconciliation

Checked 2026-10-21 Pacific against backend `e2f714a711b3bd84880c537fabb743628181ec00`.
References: GitHub #9, original Fxx/AS-Fxx acceptance review and later direct-owner
clarifications on main. External review findings are hypotheses until verified.
All checks below use isolated synthetic records; no live provider/antivirus claim.

| Finding | Current evidence | Status |
| --- | --- | --- |
| F03 repeats | Renderer preserves record IDs/opaque fields and creates UUIDs for new records. Real browser/API scenario saves two orders with distinct UUIDs; each requires its own safe copy, one copy cannot satisfy both, and cross-context replacement returns403 without changing either original. Upload slots show matching saved court/case number using bound bilingual labels and exact saved version. Full approved repeat labels and nested backend validation remain dependencies. | Partial |
| F04 own current files | Actual browser upload/list/download/replacement; old bytes retained, owner old-version download denied; latest pending scan event blocks current download and checkout. Earlier404 report is stale. | Addressed within isolated API/browser scope |
| F08 / AS-F08-1 | Direct-owner D1 requires last formal submission only to council until resubmission. Default real HTTP probe now passes all13 pre-resubmission privacy predicates plus2 owner-access and5 post-resubmission predicates on backend e2f714a. | Addressed within tested API/browser scope |
| F09 resubmit | Actual returned instructions, review and browser resubmit reuse original fee/signature. Pending required-file scan rejects resubmit with422 atomically; submission count/fee stay unchanged. Successful resubmit creates a new submission referencing the original attestation, which remains unchanged. No attestation in resubmit payload. Concurrent staff review and complete snapshot linkage remain separate backend acceptance. | Partial |
| F25 / AS-F25-1 | AS-F25-1 now independently exercised: replacement latest scan is pending; formal manifest/listing and prior clean-file download remain available, while owner/council pending bytes are denied. Clean replacement privacy and exact resubmission manifest remain covered. | Addressed within tested API/browser scope |
| F34 / AS-F34-1 | Chrome/errors/notices EN/AR; authored instructions stay unchanged. Applicant case reference and invitation/payment timestamps use bidi isolation. Submitted state no longer prompts new filing. Notification/email localization scenario not claimed. | Partial |
| F35 duplicate hold | Actual browser save succeeds with an explicitly set synthetic hold. Projection blocks checkout/submit; submit HTTP422 rejects duplicate hold; real checkout-preparation service rejects eligibility before creating an intent. Checkout HTTP is independently blocked by unconfigured provider. EN/AR notice respects edit permission. Exact person matching and hold assignment/release lifecycle remain backend acceptance. | Partial |
| F36 lifecycle | Actual process_drafts ignores a returned filing with500 idle days; status/revision/file counts unchanged. Actual draft-delete HTTP422 rejects returned filing and original bytes survive. Returned UI has no draft-delete/expiry action or new signature/payment. Shared withdrawal/claim closure and PostgreSQL worker acceptance remain separate. | Partial |

## Returned-correction privacy regression

The default `scripts/browser_applicant_api.py` run now includes this regression.
It creates a fresh isolated backend archive/database, submits and returns a filing,
assigns a synthetic manager through the real API, saves a corrected answer through
the browser and uploads a same-context MC correction. No provider operation or
actual message delivery is invoked.

All13 pre-resubmission predicates pass: council detail/version/history preserve
formal answers, current list/manifest/download retain the formal original, pending
bytes are denied through download/range/preview/HEAD, audit excludes pending source
IDs and the assigned manager receives no early correction notification/outbox job.
Two owner checks confirm saved answers and pending original remain accessible.
Five pending-scan predicates cover AS-F25-1: the later pending original does not
displace formal manifest/list/download, and its bytes are denied to owner/council.
Five post-resubmission predicates confirm council sees corrected answers/exact new
manifest/download while earlier submitted original bytes are retained.

[JSON evidence](returned-privacy-result.json) records exact predicates and backend
SHA without personal records or credentials. The original7/8 failure was reproduced
on7684169 and is fixed in this test on e2f714a. The backend privacy test file was also independently executed in the exact isolated
archive using settings_test SQLite:4 passed. It covers controlled search-hit filtering
and index suppression, private intermediate corrections, and obsolete queued-alert
discard with EmailMessage.send mocked and never called. Live search service, live
mail delivery and PostgreSQL RLS remain separate acceptance surfaces.

All24 real API/browser scenario groups pass in the default mode. An explicitly
selected baseline-only mode (`CTM_APPLICANT_ACCEPTANCE=baseline`) omits this privacy
scenario and is not full returned-privacy acceptance. No shared backend or protected
specification changes are made in the applicant stream.

## Private appointment integration

Backend `7684169` supplies the owner-only read route. Actual HTTP/browser checks
cover staff scheduling, owner confirmation, rescheduling to version2, stale-version
422, owner rejection with reason and cancellation. Outsiders receive an empty list
and403 on response; applicant council-session read is403. The projection does not
include other-party or council agenda details. This replaces the former missing-read
dependency; PostgreSQL invitation policies and real notification delivery remain
separate acceptance surfaces.
