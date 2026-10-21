# CTM medical and psychological report workflow

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Authority: user decisions and delegated completion using analogous CTM choices, 2026-10-20. Architecture specification only; no production workflow, forms, database or services were built. This document is the current authority for this section and supersedes earlier conflicting admin/secretary case-operation permissions here.

## Confirmed scope

The assigned case manager priest may ask a participating person to obtain a medical or psychological report. The council may provide recommended doctors for psychological reports; the person may choose another qualified doctor. The person uploads the completed report through their verified applicant portal, with its signed disclosure release. Medical and psychological reports have their own section, separate from ordinary Reports.

Admin and secretary have system-level/cross-program responsibilities; those roles alone grant no case-operation write permission. All authorized council members retain case read access, subject to report-specific signed disclosure authorization. Account administration does not authorize changing a person's report or signing their release. The current assigned case manager owns requests and receives routine case notifications.

## Completed workflow using established CTM choices

1. The case manager prepares a request, identifying case/proceeding, subject person, medical or psychological report type, relevant purpose and plain-language instructions. Support English, Arabic or both. Draft/save, preview, and send use the existing report-request behavior. Multiple requests are allowed; each has an opaque immutable identifier, date, status and optional display identifier. A request exists before attachments can be associated with it.
2. Optionally include council-recommended doctors. Recommendations are not mandatory, and selecting another doctor does not block submission. Record the chosen provider where known. Recommendations do not create provider logins or send case material to a doctor. Provider access or direct doctor submission is not added by this workflow.
3. Sending creates a private applicant action and immediate portal/email notification. Email gives the request/link, without medical information or attachments. Only the subject applicant can use that portal action; the other spouse receives neither access nor notification.
4. Present the relevant versioned disclosure form. Following the existing signature/upload pattern, support electronic signing in the portal or printing, signing and uploading the form. Retain exact text/version/language, subject and actual signer, purpose, intended recipients, signature evidence and timestamp. Staff cannot sign for the applicant. This is the specified capture workflow, not a claim about the legal sufficiency of unsigned draft release wording.
5. The applicant can save unfinished work, return later, upload the report and supporting files, and describe each attachment. The system recognizes file type, enforces existing per-file limits and private storage, and uses established case/document-code/timestamp naming. The request ID links every attachment; it need not be encoded in the filename. Preserve the original file. No separate charge is introduced.
6. Submission requires the report and its applicable signed release. Treat release capture and report receipt as separate records. A missing release cannot be inferred from an upload or a request. If a file reaches the system before authorization is complete, keep it restricted to the submitter/pending-authorization intake; do not expose its content, OCR or search snippets to council. Case-manager status can show a missing release without showing the report content. This does not hide the case itself from council.
7. On submission, preserve the exact response and file versions, mark the request completed and notify only the current assigned case manager immediately in the portal and by email. The original report becomes available to authorized council within the signed recipient/purpose scope. There is no separate case-manager acceptance step. OCR/extraction runs locally in English and Arabic after authorization, with queued/processing/ready/failed technical status. Processing failure does not undo submission; retry against the same original file.
8. Applicants see only their own submitted response, release and uploaded report read-only. All authorized council members can read appropriately authorized reports; other applicants cannot. Neither OCR text nor a council observation edits the clinician's original. Council search uses the same authorization rules, current versions by default, and an option for authorized version history. No medical documents are sent to external AI. Report PDFs/images/Word documents are not automatically interpreted or diagnosed.
9. New information, updated assessments or additional requests create a separate follow-up request/report, linked to the prior report and case. Do not let applicant updates overwrite a submitted response. Genuine revised clinical reports preserve version/source history. The already-approved exception for an accidentally wrong uploaded file permits removing that file and replacing it under the same request; retain the correction audit event but not the wrong content or its OCR/index derivatives. This is not general report deletion.
10. The case manager can cancel outstanding requests without sending a cancellation notification. Preserve history and disable submission. No completion deadline is imposed. Manual reminders use existing communication history and do not alter authorization. On case closure, outstanding requests stop accepting submissions. Previously saved work remains preserved. Reopening does not reactivate old requests; create new ones in the authorized appeal proceeding. A new assigned case manager inherits outstanding requests and future notifications; historical authors/signers remain unchanged.

## Section organization

Use separate Requests and completed Reports lists. Completed reports sort newest first by completion date, with filters and search. For uploaded paper reports, completion date is user-defined and upload timestamp remains server-recorded. Optional identifier text distinguishes same-date items. Uploading the completed document identifies the response as paper/uploaded automatically. The original file and OCR are separately accessible to authorized council. The shared split-view pattern may be reused with Report/original, OCR text, release and history panels; no new production UI is built here.

The signed disclosure and medical report are different documents even when uploaded together. Release status must be visible without implying that a recommendation, request, invoice, provider selection or applicant upload constitutes signed authorization. No new statutory release text or universal consent policy is invented. Final institution-approved release wording remains a document-content dependency, not another workflow questionnaire.

## Proposed data relationships

Reuse existing case, proceeding, participation, report-request, file-version, signature, communication, notification and audit entities rather than parallel standalone systems.

| Proposed entity / extension | Relationships and constraints |
|---|---|
| evaluation_requests | report_request_id unique; case/proceeding; subject_person_id; medical/psychological type; current assignment authorization; purpose; exact sent instructions/language; lifecycle timestamps. Subject must belong to the case. |
| recommended_providers | professional display name, specialty/contact information if supplied, active status; recommendations only, not a qualification/licensing verification service. |
| evaluation_request_provider_recommendations | request-to-provider references/snapshot; records recommendations actually sent, without sharing clinical content. |
| evaluation_provider_details | report/request-specific chosen provider identity and supplied professional details; may differ from recommended list. |
| release_form_versions | immutable bilingual definition, version and digest; recipient/purpose content; system publishing does not grant case access or attest consent. |
| evaluation_release_attestations | exact release version/text, evaluation subject and purpose, actual signer, signing method/time, retained signature file/evidence. No other spouse's release can satisfy the requirement. |
| evaluation_release_recipient_scopes | permitted recipients/purpose tied to the attestation; checked on original retrieval, OCR, index/search, report linking and disclosure. |
| evaluation_reports | request/proceeding/subject; author/provider metadata; completion date distinct from received/uploaded timestamp; latest retained file revision; applicable release reference; receipt and authorization states. |
| evaluation_report_file_links | described files and exact versions linked to the request/report; original versus release versus supporting document roles. |
| evaluation_processing_jobs | original file-version identity; local-only extraction/OCR language and status; restricted derived text/index; retry/error provenance without clinical content in logs. |
| evaluation_disclosure_events | actual accessor, report/file version, authorized scope, view/download action and timestamp; existing audit rules apply. |

Submitted report existence, response completion, release scope and OCR readiness are distinct state dimensions. Completion does not mean an AI or council has found a diagnosis valid. Enforce authorization transactionally; request cancellation/closure and submission must not race into accepting a closed request. Send notifications through existing idempotent delivery records. Reassignment changes the operational owner, not source authorship or signed recipients automatically.

## Validation criteria for eventual implementation

- Applicant A cannot access Applicant B's request, release, original report, OCR, snippets or guessed file URLs.
- Submission without the report or signed applicable release fails; drafts remain saveable.
- An unrelated release, different subject, purpose or file scope cannot authorize a report.
- Admin/secretary roles alone cannot initiate, complete, edit or cancel these case requests.
- Qualified-provider recommendations remain optional; another provider is accepted without a recommended-list gate.
- Case closure/cancellation blocks further submission; reopening leaves the old request closed.
- Only the current case manager receives routine submission/reminder outcome notifications; queued delivery resolves current assignment.
- Original files remain unchanged by local OCR; restricted content is absent from email, unauthorized search and external AI.
- Completion, signing, upload and access timestamps are distinct and preserved; follow-ups are separate linked records.
