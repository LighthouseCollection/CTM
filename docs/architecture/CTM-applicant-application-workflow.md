# CTM applicant application process

Approved by the user, 2026-10-21. This describes the application flow, not an implemented form or deployed portal. Use Django with the pinned Plenix React CDN contract for all eventual controls/layouts. Existing detailed validation, retention, payment and privacy rules continue to apply.

## Approved flow

1. **Before starting:** explain required information/documents and the USD 250 filing fee before initiating the application. Each actual filing applicant pays separately unless an authorized waiver applies.
2. **Account:** create/sign in through Google or Apple, using the verified provider identity and established CTM account-link rules. No CTM password system. Account creation precedes the application process.
3. **Eligibility:** an existing open case blocks a new-case draft. Resume the person's one existing unfinished new-case draft instead of making another. A linked spouse may submit their own regular application within the existing marriage case; this is not a second open case. Linking/joining alone does not incur a filing fee.
4. **Application:** section-based questionnaire with progress/missing-required-item checklist covering personal/spouse details, marriage, children, separation, selected grounds and petition statement. Preserve the configured questionnaire version and approved Unknown options; do not invent an Unknown option for required restraining-order details.
5. **Uploads:** attach required files at their actual form locations. Marriage certificate, finalized civil divorce decree and applicant photo are required; spouse photo is optional when unavailable, and each reported restraining order requires its own copy. Petition statement may be typed or PDF/Word. Existing categories, naming, per-file limits and version/ownership rules apply. No baptism certificate requirement is introduced.
6. **Draft:** save/return with answers and uploads preserved. Drafts remain private and can be deleted before submission, subject to existing in-flight transaction guards. Expire after 180 days of inactivity with the agreed seven-day warning and portal notice.
7. **Review:** present all answers and attachments with missing requirements before signing the versioned declaration and proceeding to the final payment/submission step. Review does not expose the other applicant's private submission.
8. **Payment/submission:** run approved identity and marriage-matching checks, including exact duplicate-person review holds that pause payment/submission while saving remains possible. Require verified identity/email and successful payment or authorized waiver. Use the existing frozen submission/idempotency/recovery design; payment success must not leave a silently lost application or trigger duplicate fees.
9. **Confirmation:** show the retained case number, submission confirmation and applicable fee receipt/status. Submitted applications become available to council; unfinished drafts do not. Preserve original submission versions and CTM identifiers.
10. **Completeness review:** admin/secretary accepts or returns the application with specific correction instructions. A returned filing keeps its case number and history, and correction/resubmission does not require another fee. Use existing notifications and review states.
11. **Council process:** accepted new cases enter the session/assignment process. Applicants subsequently follow status, receive private communications and respond to their own requests through the portal. Prior rules allow the first accepted application to proceed while another filing is incomplete/returned.

## Layout direction

A section checklist with Save and continue supports non-linear completion over multiple visits. Review and final payment/signature remain clear distinct steps in the flow. Exact Plenix components and props must be read from the pinned published documentation; do not invent a custom stepper or style value if unavailable.

The proposed overall applicant shell is distinct from this approved application process. Its earlier navigation/page names and optional split views remain proposals unless separately confirmed. This approval does not lock a new applicant Home layout or expose council report/notes/audit areas.

## Existing constraints remain

Original submissions and subsequent permitted corrections are separate historical records. Applicants never gain another applicant's answers/files by sharing a case number. Required fees, waivers, nonrefundable-submission policy, wrong-file exceptions, historical-entry exceptions, matching precedence and closed-case/appeal rules remain in the current detailed architecture; this flow does not re-open or replace them.
