# CTM prototype-to-workflow follow-up review — 2026-10-20

Coverage: static inventory of top-level admin/public HTML pages, targeted source reads for sign-in, account/system settings, requisitions, decree and support; cross-check of workflow, permissions and returned questionnaire registers. This is not a rendered click-through test or proof that any backend behavior exists. Detailed source inventory is CTM-workflow-review-page-inventory.json. No prototype edits performed for this review.

## Disposition after latest user corrections

The previously listed questions are no longer an open workflow questionnaire. See [current access/workflow corrections](CTM-current-access-workflow-corrections.md).

- Admin/secretary have default functional authority; case worker does not manage decrees.
- Only an existing admin adds council members; no membership requests or self-enrollment.
- No CTM passwords/recovery. Microsoft manages council credentials; Google/Apple manage applicant credentials.
- Replacement-decree workflow removed from scope and the questions list.
- Exact marriage date plus both exact spouse DOBs automatically links applications, even when certificate numbers differ or are unavailable. Unmatched/ambiguous cases go to review; do not reopen the settled rule.

## Prototype items not to import as new requirements

- admin-management.html:476–502 exposes export/purge, already rejected for submitted cases.
- admin-user-account.html:185–190 inactivity timeout and :248 SMS do not override no idle timeout and confirmed portal/email channels.
- admin-case-decree.html:290 suggests vote-before-proceed; president approval remains permitted without votes. :418 Generate & issue cannot bypass signed-certificate retention, issuance/closure and separate recipient release.
- admin-support.html:42–46 says under development. No support-ticket workflow should be inferred from the placeholder.
- public-crown-* marriage-process pages are future-ecosystem scope, not missing divorce/annulment requirements to implement now.
- admin-case-requisition.html contains separate applicant/respondent petition statements, already covered by attributed private submissions; it does not authorize either applicant reading the other's statement.

## Core flows already covered

Draft and submission/payment; review/return/resubmit; exact-case linking and identity review; council assignment/agendas/hearings/attendance; testimony; reports/intakes/follow-ups/priest invitations; medical requests/releases; decisions/votes/presidential approval; decree signing/issuance/release/withdrawal; appeals; correspondence/notifications; attachments/OCR/search; closure/retention; shared/personal templates; bilingual UI and translations; admin-created council access and Microsoft sign-in.

The remaining work is primarily reconciling current authority and specifying exceptional transitions. Do not restart all settled workflow questions. Provider selection, backups, Linux distribution and actual Microsoft tenant setup are deployment dependencies, not missing case workflows.
