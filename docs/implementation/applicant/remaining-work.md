# Remaining applicant work

Current applicant head includes initial/returned filing, contextual originals,
payment history, private appointments and appeal entry. This queue does not claim
the full applicant portal is complete. Backend/shared shell changes stay with their
owners; applicant PR #5 remains draft.

| Order | Remaining task | Next concrete action / dependency |
| --- | --- | --- |
| 1 | Pending appeal supplements | UI prepared with review, safe evidence selection and uncertain-response locking. Backend integration remains pending own supplement history and authoritative `can_supplement`. Existing POST additions accepts text/file IDs but has no idempotency key. |
| 2 | Released decree access | Read-only UI prepared; backend own actively released decree projection and real revocation acceptance remain pending. Never infer recipient entitlement from filing order; revocation must cover preview/range/download. |
| 3 | Applicant request responses and professional release | Actual own request reader implemented with bound questions/instructions; response capability, approved release definition and signed scope remain pending. Keep drafts/interviews/other spouse requests private; no signature or institutional wording invented. |
| 4 | Checkout recovery | Own pending candidate/original-attestation/resume contract is still missing. Recover an existing attempt without a new charge or signature; do not infer success from return URLs. |
| 5 | Draft deletion and withdrawal controls | Add authoritative action capabilities and explicit confirmation UI. Returned filings must never use draft deletion; joint withdrawal and shared claim closure must follow owner decisions. |
| 6 | Complete approved bilingual forms | Institution-approved questionnaire/declaration/repeat labels and backend nested repeat validation. Synthetic fixtures are test data, not approval of content. |
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
