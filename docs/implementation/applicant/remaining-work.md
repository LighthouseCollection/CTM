# Remaining applicant work

Current applicant head includes initial/returned filing, contextual originals,
payment history, private appointments and appeal entry. This queue does not claim
the full applicant portal is complete. Backend/shared shell changes stay with their
owners; applicant PR #5 remains draft.

| Order | Remaining task | Next concrete action / dependency |
| --- | --- | --- |
| 1 | Pending appeal supplements | UI prepared with review, safe evidence selection and uncertain-response locking. Actual owner supplement POST and staff denial verified; integration remains pending own supplement history and authoritative `can_supplement`. Existing POST additions accepts text/file IDs but has no idempotency key. |
| 2 | Released decree access — read integration verified | Backend 444bad8 supplies own active release rows. Actual browser shows bilingual metadata/exact PDF link, isolates linked spouse, and removes withdrawn release links. Retained full/range/preview/HEAD URLs revoke. Synthetic stored PDF only; real signing/issuance and PostgreSQL acceptance remain separate. |
| 3 | Applicant request responses and professional release | Actual own request reader implemented with bound questions/instructions; intake response editor prepared with review/guards/version payload. Response capability/version enforcement, approved release definition and signed scope remain pending. Closure currently exposes unsent drafts through the backend API (P1). Keep drafts/interviews/other spouse requests private; no signature or institutional wording invented. |
| 4 | Checkout recovery | Actual own payment history now blocks fresh checkout for unresolved/unknown candidates. Resume UI prepared; own pending candidate/original-attestation/resume contract is still missing. Recover an existing attempt without a new charge or signature; do not infer success from return URLs. |
| 5 | Draft deletion and withdrawal controls | Explicit confirmation UI prepared with single-attempt locks and parent filing/navigation protection. Authoritative action capabilities and version enforcement remain pending. Returned filings must never use draft deletion; joint withdrawal and shared claim closure must follow owner decisions. |
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


## Current acceptance blocker

The default real API suite now checks never-sent request privacy after actual case
closure and still fails at backend 444bad8 (previously f0e21b4): a staff draft changes to `closed`, then is
returned by the applicant request endpoint. The frontend rejects its null sent
stamp, but cannot repair API disclosure. See `request-closure-privacy-result.json`
and GitHub #2. Do not call the full acceptance suite green. An explicit
`CTM_APPLICANT_REQUEST_CLOSURE_AUDIT=0` run is baseline-only, not full acceptance.
