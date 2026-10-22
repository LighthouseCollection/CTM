# Remaining applicant work

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

Current applicant head includes initial/returned filing, contextual originals,
payment history, private appointments and appeal entry. This queue does not claim
the full applicant portal is complete. Backend/shared shell changes stay with their
owners; applicant PR #5 remains draft.

| Order | Remaining task | Next concrete action / dependency |
| --- | --- | --- |
| 1 | Pending appeal supplements | UI prepared with review, safe evidence selection and uncertain-response locking. Actual owner supplement POST and staff denial verified; integration remains pending own supplement history and authoritative `can_supplement`. Existing POST additions accepts text/file IDs but has no idempotency key. |
| 2 | Released decree access — read integration verified | Backend 444bad8 supplies own active release rows. Actual browser shows bilingual metadata/exact PDF link, isolates linked spouse, and removes withdrawn release links. Retained full/range/preview/HEAD URLs revoke. Synthetic stored PDF only; real signing/issuance and PostgreSQL acceptance remain separate. |
| 3 | Request response/release operational acceptance | Actual fingerprint-bound intake and assessment responses, request originals, explicit published declaration consent and exact receipt recovery are integrated and locally verified at 480a246. Institution-approved wording, live clinical disclosure and PostgreSQL acceptance remain separate. |
| 4 | Checkout recovery — locally integrated | Actual retained candidate/version/attestation/declaration/expiry read verified at d724ba5. Exact safe URL resume performs no checkout POST; expiry/changed revisions/processing/reconciliation block resume and fresh charges. Live provider acceptance remains separate. |
| 5 | Filing actions — locally integrated | Authoritative capabilities and version checks now verified. Explicit draft deletion, returned withdrawal, lost acknowledgement, joint participant/last-filer closure and owner-only appeal withdrawal pass. Synthetic state and SQLite do not establish PostgreSQL/concurrency acceptance. |
| 6 | Complete approved bilingual forms | Technical candidate checker and source JSON inventory added. Reference seed contains 59 English questions and no Arabic wording; this is not a bound applicant form. Institution-approved questionnaire/declaration/repeat labels and backend nested repeat validation remain pending. Synthetic fixtures are test data, not approval of content. |
| 7 | Governance integration | Apply/reconcile shared shell patch serially, integrate applicant/council/backend branches and test the complete journey. No independent merge/deploy. |
| 8 | Acceptance outside local fixtures | PostgreSQL roles/RLS/races, real provider login/payment callbacks, live antivirus, live search/email, signed documents and delivery. Keep these separate from SQLite and controlled provider tests. |

## Appeal entry slice completed

`applicant-appeals.js` starts/resumes an appeal through actual POST applications,
validates same-case appeal acknowledgement, blocks duplicate in-flight starts and
ignores late acknowledgement after leaving the case. The proposed shell hook uses
an authorized closed-proceeding context, preserving the reopened-sibling exception;
the server still decides eligibility. No case status mutation is sent by the UI.

Actual browser/API tests cover published appeal form, saved new information,
required PET original, authorized fixture waiver/declaration/submit, draft reuse,
and no reopening on submission. A distinct previously non-filing linked spouse can
start an own appeal in a reopened-sibling state fixture. Closed/reopened state and
party linking are explicit fixtures, not proof of decree issuance, council appeal
acceptance or identity onboarding. Supplement UI is prepared; its own read/capability contract remains pending.


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
