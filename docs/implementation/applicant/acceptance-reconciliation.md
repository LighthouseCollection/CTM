# Applicant acceptance reconciliation

## Current filing/recovery verification (2026-10-21)

The next ten batches integrate backend `d724ba56b8bd5cf501d55fbbca416470108f963a`
(including filing contracts introduced in acafe29). Own draft deletion and withdrawal
now use the server capabilities and current answer version. Original checkout recovery
uses the retained candidate, attestation, exact declaration and future provider expiry.
Local expiry removes resume only; it never reconciles a payment or enables a new charge.

Current checks: 68 frontend tests, 54 real API/browser scenario groups, 11 response/
recovery/lifecycle fixture groups and nine shell groups pass. The earlier 66/42 results
below are historical snapshots. All backend data is isolated/synthetic; one controlled
provider-create output verifies retained adapter behavior without network or a charge.
The second joint filing and pending appeal state are explicit fixtures. PostgreSQL,
live provider callbacks/antivirus, institutional wording and document issuance remain
outside this acceptance. [Report](filing-recovery-batch-report.md) and
[Download JSON](filing-recovery-batch-result.json).

## Earlier verification: first ten batches (2026-10-21)

Backend `480a246118cce8c4ac338c32c71c79cde74816d2` supplies the own request
fingerprint, capabilities, scoped originals, published declaration and retained
consent/response receipts. Intake and assessment workspaces now use these actual
contracts. The previously reported closure disclosure is resolved and independently
verified: never-sent drafts remain private; previously sent closed requests remain
readable, and exact submitted responses recover their original receipts after closure.
The default closure gate remains enabled.

Final local checks: 66 frontend tests, 42 real API/browser scenario groups, five
assessment interruption groups, nine next-batch groups, nine shell groups and four
request-reader groups pass. The real API runner uses isolated SQLite, synthetic
accounts/content, temporary backend archives and a scanner test policy. It does not
establish PostgreSQL, live provider/payment/antivirus, institutional wording approval,
signature issuance or operational delivery acceptance. See the consolidated ten-batch report and JSON evidence.

## Earlier evidence (historical snapshots)

Earlier missing-contract and closure-failure statements below describe their recorded backend versions; the current verification above supersedes those statuses.

Checked 2026-10-21 Pacific against backend `5cb1428c79b6d6ea48d8792add0430535adbb41e`.
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
on7684169 and is fixed in this test on e2f714a. The backend privacy and search test files were also independently executed in the
exact c16976c archive using settings_test SQLite:10 passed. It covers controlled search-hit filtering
and index suppression, private intermediate corrections, and obsolete queued-alert
discard with EmailMessage.send mocked and never called. Live search service, live
mail delivery and PostgreSQL RLS remain separate acceptance surfaces.

The earlier 31-group run passed. The expanded default run reaches 34 passing scenario groups, then FAILS the new request-closure privacy gate. An explicitly
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


Latest complete API/browser rerun: backend
`f0e21b4e0b5c76f1e99a4135c3701ea3e39a74d3`, 34 preceding scenario groups passed; closure privacy gate failed.
The added check verifies the missing own decree release-list projection cannot
expose certificate links. Supplement/decree successful read/write flows remain
proposed-contract fixtures; no real decree issuance/release/revocation acceptance.
Earlier per-feature evidence and saved privacy artifact retain their recorded SHAs.


Own request reading is integrated with the actual case request endpoint: bound
question/instruction rendering and server exclusion of staff drafts/interviews/
external requests pass. A linked spouse receives no other applicant requests.
Request setup is an explicit synthetic sent-snapshot fixture, not published
institution wording, notification/send or professional consent acceptance.
Own response submission and signed professional release remain pending contracts.


Current P1: actual close_case changes never-sent staff drafts to closed; applicant
request list filters only draft and returns these unsent rows. Frontend null-sent
stamp rejection is not API authorization. Default acceptance now asserts exclusion
and fails. Preserve this failed result until a backend fix is independently verified.
Prepared response/lifecycle controls remain disabled without own server capabilities;
original-attestation checkout resume remains disabled without its immutable snapshot.


Latest decree integration: backend 444bad8,35 preceding API/browser groups pass,
then default closure privacy still fails. Own active release read is no longer a
missing contract: actual EN/AR panel/exact PDF action, recipient isolation and
withdrawn-list refresh are verified with dedicated synthetic DEC bytes. Live
signature/issuance and PostgreSQL remain separate.
