# CTM confirmed workflow database design

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Confirmed 2026-10-20. Documentation only: no application, SQL, migrations or infrastructure changes. This supplement is part of the table dictionary and permission specification. It consolidates the workflow decisions in `CTM-case-session-workflow.md`; later confirmed decisions supersede prototype behavior. All identifiers below are proposed table names, not implemented tables.

## 1. Aggregate relationships

One case has many participating applicants, proceedings, applications, hearings and historical decisions. The initial proceeding and every reopened appeal proceeding are distinct. Every proceeding has its own evidence, notes and findings; closing it freezes substantive records permanently. Reopening the case creates a new appeal section, not permission to edit the original proceedings. Case identity and number remain unchanged. All authorization joins use opaque keys, never display names/numbers.

Each appeal application belongs to exactly one case applicant and its own fee obligation, submission, attestation and evidence. Two applicants' appeals may share one hearing and one reopened proceeding, while retaining separate Accept/Decline results. A hearing is not duplicated per appeal. Applications and decree recipient rights are separate: payment or filing alone does not confer certificate access.

## 2. Proposed relational tables

| Table | Principal fields / relationships | Confirmed constraints |
|---|---|---|
| `case_proceedings` | case FK; initial/appeal kind; opened/closed times; initiating acceptance reference | One active proceeding within the open case; closed source proceedings remain immutable |
| `case_lifecycle_events` | case/proceeding; action; source review/approval/withdrawal/appeal/issuance; actor/time | Preserve every closure/reopening; same case number; enforce canonical-person open-case claims |
| `application_completeness_reviews` | application; exact submission/revision/manifest; Accept/Reject; correction explanation; reviewer/time | Admin/secretary only; Reject requires nonblank applicant-visible instructions; returned applications reuse case and paid/waived obligation |
| `application_resubmissions` | application; preceding submission; exact answer revision/manifest; actor/time | Immutable original and resubmissions; no new case, fee or signature for corrections |
| `case_assignments` | case; member; authorizing president; recording actor; decision/recording times; session when applicable; effective interval | Reuse existing assignment model; one current member; president selects/reassigns, admin/secretary records; full history |
| `council_sessions` | UUID; date; hidden `CSYYYYMMDD`; friendly name; lifecycle; creator/time | One session per date; display Council Session YYYY-MM-DD; admin/secretary create/reschedule |
| `agenda_requests` | case; requested session; assigned requesting member; time; placement reference | Member marks own assigned cases; admin/secretary manages agenda |
| `session_agenda_items` | session; case; part/order; hearing reference; disposition | Two ordered parts: new assignments, then ongoing case hearings; one hearing may cover both appeals |
| `agenda_transfer_events` | case; original date/reference values; destination agenda item; cause; actor/system/time | Retain case-level movement history; moving a planned meeting removes cancelled session, transfers all attached cases to a new dated session |
| `session_member_attendance` | session; member; presence; recorder/time | Admin/secretary records default attendance |
| `case_hearings` | case; proceeding; agenda item; actual presenter; hearing date/time; outcome | Only currently assigned member presents; title Case Hearing of first-name last-name vs. first-name last-name; no numerical quorum |
| `hearing_member_attendance` | hearing; member; presence; recorder/time | Confirm actual presence per hearing separately from session default; does not gate voting |
| `hearing_outcome_revisions` | hearing; internal rich text; next steps/recommendations; predecessor; actor/time | Admin/secretary/assigned member record and revise; every revision retained; corrections send no notifications |
| `testimony_appointments` | hearing/agenda; applicant; scheduled date/time; instructions; scheduler; revision/cancellation events | Admin/secretary/assigned member schedule; two applicants may appear in same session at separate times, never together |
| `testimony_invitation_responses` | appointment version; applicant; Confirm/Reject; optional rejection explanation; time | No applicant rescheduling; no additional testimony attendance-status feature |
| `testimony_events` | case/proceeding; applicant; appointment; recording references | Applicant attends testimony portion only; internal discussion stays private |
| `testimony_recordings` | event; immutable file version; microphone/upload origin; staff actor/time | Admin/secretary manages; required audio recording; council-only, including all derivatives |
| `testimony_processing_runs` | recording; task; provider/model; languages; status; input/output references; time | AI API transcription/translation requested; provider not selected; local PDF/image OCR policy unchanged |
| `testimony_text_versions` | recording/run; source/English/Arabic kind; text; source transcript version; predecessor; AI or editor identity/time | Original language transcript plus translation; mixed-language original plus full English and Arabic; admin/secretary may correct, all revisions retained |
| `testimony_text_segments` | text version; audio-relative times; speaker label; corresponding source segment | Applicant/council speaker labels, timestamped segments; translations trace to source audio |
| `case_decision_versions` | case/proceeding/hearing; type; grounds/reason; affected parties; conditions; actor/time; predecessor | Admin/secretary/assigned member enters; show type and grounds before voting; no separate proposal workflow |
| `council_votes` | exact decision version; voting member; Approve/Deny/Abstain; entering actor/time | Self-entry or admin/secretary on behalf; full roster visible regardless of attendance; council sees individual votes/tally; no additional voting workflow |
| `presidential_approvals` | exact decision version; approving president; entering actor/time | President directly or admin/secretary on behalf; valid with or without votes; changed type/grounds needs fresh approval and votes if taken |
| `party_withdrawal_events` | case party; petition; actual actor/time; on-behalf indicator | Applicant directly, no approval/reason; admin may act for all; two participants must both withdraw to close, sole participant withdrawal closes |
| `decree_template_versions` | template/type; locale/layout/content; predecessor; editor/time | Admin/secretary edits; immutable versions; prior issued certificates never change |
| `decrees` | case/proceeding; approved decision; `DCR-{case number}`; appeal suffix when applicable | First appeal decree `DCR-20261020-01-A1`; decree ID distinct from DEC attachment code |
| `decree_certificate_versions` | decree; template version; English/Arabic/both; prepared content; signed file version; signer/method; preparer/uploader/time | Admin/secretary prepares; both means one bilingual certificate; president Bishop/Metropolitan signs digitally or physical signed scan stored |
| `decree_issuance_events` | decree/certificate version; current approval; actual issuer/time; closure event | Stored signed certificate mandatory; issuance closes case atomically; never auto-exposes certificate |
| `decree_party_entitlements` | decree; case party; decree/official-notice disposition | Match approved type/party rights; do not infer both-party access from case membership |
| `decree_release_events` | certificate version; entitled party; release/withdraw action; admin/secretary/time | Explicit version-specific release; recipient view/download logged; release/withdraw permitted after closure |
| `appeal_applications` | case; applicant/party; private draft or retained submission; statement/reason; new information/evidence; fee; own declaration/signature | One draft or pending appeal per applicant/case; other applicant may file independently; each costs USD 250 under existing waiver/payment rules |
| `appeal_supplements` | appeal; immutable text/manifest; applicant actor/time | Additions only while pending; submitted statement unchanged; no staff supplementation on behalf |
| `hearing_appeals` | hearing; appeal FK | One hearing covers both appeals, without merging their ownership/evidence/results |
| `appeal_dispositions` | appeal; hearing; Accept/Decline; entering actor/time; optional applicant explanation | Admin/secretary/assigned member records council result; separate per appeal; no presidential approval/vote gate at intake |
| `proceeding_appeals` | reopened proceeding; accepted appeal | Multiple accepted applications can link to same reopening; rejecting sibling appeal cannot re-close case |
| `appeal_withdrawal_events` | appeal; owner actor/time | Applicant before Accept/Decline, no approval/refund; source case/decision unchanged |

Reuse existing file/version/manifest, application attestation, financial obligation, correspondence/recipient/delivery, audit and outbox tables. Do not create duplicate stores for those concepts. Existing findings/notes/evidence gain a proceeding FK and an appeal FK where applicable, with same-case/party constraints. Draft appeal files use private appeal ownership even though source case is closed; this does not unlock ordinary closed-case uploads. Retained submitted files and historical records never cascade-delete.

## 3. Workflow and permissions

- Initial application review is Accept/Reject by admin/secretary. Reject returns the same application with required correction instructions. Applicant corrects/resubmits under same number and fee, retaining all history. Accepted new cases enter assignment agenda.
- President assigns during council meeting; admin/secretary records. Reassignment follows same authority, notifies incoming/outgoing member immediately by portal/email, and informs applicants of their assigned member/name change.
- Admin/secretary closes sessions. Time-exhausted items automatically move to next dated session; without one they await manual placement. Deliberate deferral or absent assigned presenter always awaits manual placement. Planned meeting date changes create a new session, transfer all attached cases and testimony schedules, remove cancelled meeting, and retain case transfer audit facts. Completed hearing records are not removed by this planned-meeting rule.
- Case hearing outcomes can be next steps/recommendations without a decision. Internal and applicant-facing rich text are separate. Send records the update and sends default case-presented-on-date/still-pending text plus optional applicant text immediately by portal/email; delivered messages are immutable correspondence. No Save Draft/Finalize step. Authorized recommendation corrections are notification-free.
- Testimony invitations, changes/cancellation privately notify relevant applicant by portal/email. Applicant Confirm/Reject notifies assigned member and secretary immediately; optional rejection explanation. Rejection leaves case on agenda for discussion or deliberate deferral.
- President gives final decision approval with or without votes in same UI. Votes never substitute for approval. Revised type/grounds preserves earlier votes/approvals and requires fresh approval.
- Decree issuance closes case and sends private notices according to entitlement. Actual signed certificate remains hidden until admin/secretary releases it; release notifies entitled recipient by portal/email. Non-entitled party gets official decision notice only. Release/withdraw history retained. Clerical replacements retain same decree ID, require president re-signature and new explicit release; only corrected version accessible to recipient, originals council-only.
- Petition Denied closes case after presidential approval with official notice, no certificate. Withdrawal needs no approval or reason; reconciliation is handled as withdrawal, not a separate outcome. Withdrawal notifies assigned member/secretary immediately, never the other applicant. Admin on-behalf withdrawal is granted; secretary is not implicitly granted it.
- Admin/secretary/assigned member can send messages after closure; preserve all correspondence. This does not unlock substantive records. Each message can privately target either applicant or both, with separate delivery/replies.

## 4. Confirmed appeals lifecycle

Either linked applicant may appeal a decision at any time using statement/reason, new information/evidence, attachments and own declaration/signature. Each filing has USD 250 payment or existing authorized waiver; no refund except accidental duplicates. Payment/submission follows regular application finalization. Drafts remain private with 180-day inactivity expiry/seven-day warning; only one draft or pending appeal per applicant/case. Following questionnaire A02, either applicant may independently submit at any time, including while the other applicant appeal has reopened the same case; case closure is not a filing gate. Submitted appeals never expire/delete.

Submitted appeal enters agenda queue without reopening source case or changing decree/access. Original assigned member presents unless president reassigns. Applicant supplements preserve statement and prior evidence; only owner adds. Portal alerts to assigned member/secretary immediately, email after ten-minute inactivity. Applicant can withdraw pending appeal before disposition without approval; preserve all records and fee, notify assigned member/secretary immediately by portal/email, not the other applicant.

Council considers both appeals in one case hearing with separate Accept/Decline results. Decline generates official notice with optional additional explanation to appealing applicant by portal/email and leaves case closed unless another accepted appeal already reopened it. Accept reopens original case once under same number; notify both participating applicants privately by portal/email. Enforce universal one-open-case-per-person rule at commit; no silent override or second open case.

Reopening creates a new appeal section/proceeding for new evidence, notes and findings; original proceedings remain read-only. Apply regular case hearing, type/grounds, voting/approval and decree rules. First appeal decree uses A1 suffix; originals remain intact. Repeat appeal possible after later closure, after decline without another closure, or after withdrawal with a fresh filing fee; retain each original filing. Acceptance is not automatic reversal of the earlier decree. Any explicit change to decree/access is separately recorded.

## 5. Transactional and access requirements

Unique session date/identifier; atomic assignment intervals; applicant/case draft-and-pending appeal claim shared by draft creation/payment/submission; unique disposition per appeal; idempotent reopening shared by accepted sibling appeals; retained snapshot/attestation/evidence manifests. Acceptance acquires all participating canonical-person open-case claims using the same operation as new-case submission; if a claim conflicts, never leave accepted/reopened state partially committed. A conflicting different open case blocks acceptance/reopening for admin/secretary resolution. Accepting another appeal into an already reopened same case does not create a second open proceeding.

Decree issuance requires matching approved decision and retained signed version, then closes case and queues notices atomically. Explicit release checks entitlement and exact signed version; replacement release atomically revokes superseded recipient access. Staff on-behalf actions always preserve principal and actual actor separately. Pending-appeal supplements are narrow closed-case exceptions, never generic edit permissions. Cross-applicant answers/evidence/replies remain isolated; testimony audio/text and council deliberations remain council-only. AI API keys/provider payloads are service-only, not readable merely through council membership.

## 6. Remaining substantive decisions

Remaining clarification: certificate-based marriage match minimum, prior-decree voiding trigger/access interaction, and case-manager role terminology. Detailed certificate handover and applicant-portal design remain deferred. Questionnaire-confirmed rules for historical finalization, conditional/nullity entitlement, appeal numbering, open-case conflicts and unbounded testimony capture are in CTM-questionnaire-decisions-2026-10-20.md. Provider/deployment choices and physical SQL/RLS are later engineering work. No new vote workflows or speculative applicant fields are required.

## 7. Staff-added second applicant and email verification

Administrator or secretary adds the other party to an existing case using First Name, Last Name and email. CTM records a pending case association for that email; staff entry does not create a completed applicant account. The other party registers their own account using that email and completes email verification. Once registration and verification are complete, activate the case connection and make the applicant portal available to that party. This replaces the earlier standalone invitation-acceptance workflow: no separate Accept Invitation action is required. Record the actual adding staff actor/time, intended email, supplied names, pending case association, registration and verification events and activated account/person/party association.

Reuse account/email verification and stable person identity. Reserve `case_party_onboarding` with case FK, supplied first/last names, intended email, adding actor/time, account/person references, verification reference, pending/activated association and activation time. Do not activate case access before both account registration and verification of the exact pending recipient email. Merely entering the party into the case does not grant applicant access. Admin entry is not applicant attestation; preserve who supplied those names and do not fabricate birth dates, signatures or CTM identity components. Identity references requiring more details remain unallocated until those details are known.

The linked applicant retains independent ownership/visibility and cannot access the first applicant's answers, evidence, correspondence or histories. Email verification does not establish spouse facts as verified questionnaire answers. Enforce existing duplicate identity and one-open-case constraints before activation; no automatic identity merge or second open case.

User-portal behavior is explicitly deferred for a later discussion. Confirmed: if the supplied email already belongs to a registered, verified CTM account, automatically activate its case connection, subject to existing identity/open-case guards. Reuse the account/person, never create a duplicate. Preserve staff provenance and activation time.


## 8. Independently filed applications for the same marriage: matching under discussion

Confirmed scenario: both spouses can independently submit applications concerning the same marriage; these should be associated with the same case when the marriage identity is established. Exact marriage date is mandatory and the primary matching component, but is insufficient alone. User identified marriage location and spouse names as additional matching components. This is distinct from exact duplicate-person review; retain both applicants and their independent submissions/payment histories.

Confirmed matching components: exact marriage date (mandatory primary component), exact birth dates of both spouses compared with applicant/spouse positions reversed as needed, and marriage-certificate registration number when available. Do not require exact names, church/venue or location because spelling varies. Exact matching using the approved components automatically associates independently submitted applications with the shared case; no admin invitation or confirmation is required. Preserve independent accounts, submissions, ownership, payments and histories; association never exposes the other applicant answers/evidence. Unknown/missing values are not equality proof. Questionnaire L04 approves certificate-based matching as an alternative to missing or incorrect birth dates; the exact minimum certificate combination is awaiting focused confirmation. Confirmed: when the certificate registration number is unavailable, an exact match on marriage date and both spouses birth dates is sufficient for automatic association. Compare the birth dates as a spouse pair independent of which party filed; retain the actual applicant/party mapping. A missing spouse birth date does not satisfy the date-based route; it does not categorically block a certificate-based route under questionnaire L04. Multiple candidate marriage matches pause for admin/secretary review. Retain the first-created case number and keep other numbers as historical aliases. Admin/secretary may correct wrong associations with every source record preserved. Later answer corrections never automatically relink the application. Ambiguous party mapping pauses access for staff review; never merge distinct people. Check for a match before number allocation and recheck atomically at submission as the delegated engineering choice.


Confirmed matching precedence: exact marriage date plus exact birth dates for both spouses automatically links the applications even when certificate registration numbers differ. Preserve both supplied certificate numbers with their application sources; do not overwrite either assertion. If certificate numbers conflict and the exact three-date combination is not satisfied, route the candidate to administrator/secretary review rather than automatic linking. Certificate-based matching must now support missing/different birth dates per questionnaire L04; exact marriage date remains mandatory and the minimum certificate combination needs confirmation. Names/location are not exact-match gates.



## 9. Batch review questionnaire

The remaining scenario proposals are collected in [the interactive questionnaire](questionnaire/CTM-architecture-questionnaire.html), with a [Markdown alternative](questionnaire/questions.md). All 39 answers start unresolved; the worksheet is not an architecture approval. Exported answers and clarifications must be reconciled in the conversation before changing confirmed requirements. Applicant-portal design and deployment/provider choices remain deferred.


## 10. Questionnaire response reconciliation

The [questionnaire decision register](CTM-questionnaire-decisions-2026-10-20.md) records all 39 responses and clarifications and supersedes earlier conflicting statements in the workflow discussion. Confirmed additions include first-created case-number retention with aliases; controlled association correction; pending-recipient correction/cancellation; staff-initiated registration emails only; return notices/resubmission queue; assignment from first accepted application; conditional/nullity entitlement and A2/A3 numbering; historical entry workspaces/finalization/corrections; versioned system templates and failed-delivery visibility; fresh testimony responses after rescheduling; unlimited testimony capture using an open-source component; AI-text staff review before wider council access; and an open-source PDF-scanning requirement. No component is selected or installed.

Decree validity: one current valid decree per case, original numbers retained and replaced decrees marked void without deleting history. Validity and released-file access are distinct; precise voiding trigger remains a follow-up. Appeal applications remain independent even when the other appeal has reopened the same case. The standard closed-source-record locks and applicant privacy remain.

Relational additions in the register (`case_identifier_aliases`, `case_association_events`, `marriage_match_reviews`, `registration_invitation_events`, `historical_entry_workspaces`, `decree_validity_events`, `testimony_text_review_events`) are part of this dictionary supplement. Testimony text visibility now requires admin/secretary review of the exact generated version, independently of council access to source audio. Ordinary uploaded audio remains subject to its existing 100 MB limit; testimony capture/upload is the clarified no-fixed-cap exception.

## 11. Applicant portal and assigned-member interview review

The user requested separate decision worksheets for [applicant portal capabilities](questionnaire/applicant-portal-questionnaire.html) and [assigned case-owner interviews](questionnaire/case-interview-questionnaire.html), with Yes / No / Other and text alternatives. These topics are now under review rather than waiting for individual questions. The interview requirement includes template-based information gathering, in-application audio recording and automatic transcription. The returned answers are now reconciled in CTM-portal-interview-decisions.md, which defines template management, applicant-only interview participants, actual author/on-behalf entry, interview AI processing, assigned-member transcript review and council-only visibility. The existing prototype intake metadata and its interview log are source evidence; its permissive interviewer selector does not confer new role authority. Do not conflate private investigation interviews with council-session testimony or infer applicant access to either. No CTM feature has been implemented.

## 12. Confirmed applicant portal and investigation interviews

[All 64 portal/interview responses](CTM-portal-interview-decisions.md) supplement this workflow/table design and supersede earlier discussion placeholders. Portal home has one current-workflow view, safe timeline/actions and separate past cases; no combined dashboard of mutually exclusive work. Keep previously approved independent same-case appeals intact. Correct-location document attachments and context links are required, with existing filename/version rules; portal messages and email replies share private correspondence. Information requests accept submitted information/files automatically and flag them New; no staff acknowledgement or Request completed action. Released decree certificate is a PDF.

Only assigned member conducts applicant interviews; admin/secretary can enter/upload on behalf with separate actual actor. Applicants interviewed separately; no priest/witness directory/interview feature. Standardized bilingual versioned templates, optional case-specific questions, structured/narrative answers, interview drafts/logs and linked evidence are confirmed. Optional microphone/upload recording supports mobile web, pause/resume/recovery and no fixed cap, with informed-about-recording record. AI transcription/translation follows original/English/Arabic rules; no AI mapping into template answers. Assigned member reviews generated interview text before council access; typed answers remain separate. Interview draft narrative and completed records/audio/reviewed text are council-only; applicants never see interview material. Original author alone revises completed narrative subject to open-proceeding/current-assignment permissions; new member adds follow-ups. Closure locks original proceeding.

Tables and remaining explanations are detailed in the response supplement. The draft standardized guided interview content is a separate review artifact, not published policy or built UI.


### Guided interview template structure refinement

The user requires strategic factual discovery organized into categories, with identity opening at every interview/separately started recording; requested outcome and grounds before events; and application-information clarification in its own category. Draft revision 2 of CTM-guided-interview-template-draft.md reflects this. Template category IDs/question codes/order and repeatable ground/event blocks are proposed schema extensions; recording openings link to the actual capture. Requested outcome, applicant facts/source certainty, source evidence, transcript and council findings stay separate. No new canonical eligibility rules or applicant disclosure rights are introduced.

## 13. Catholic source study: proposals awaiting decisions

The user requested a comparative study of eight local Word samples and fourteen linked PDFs. The [study overview](reference-study/index.html), [application comparison](reference-study/application-review.html), [question/template review](reference-study/template-review.html) and [report](reference-study/study-report.md) contain source-linked proposals only. No new field, ground, requiredness, priest role/account, canonical process or applicant disclosure is approved by producing these artifacts. Existing application and guided template remain unchanged pending user responses. The newly suggested council-requested priest report is separate from the earlier rejected priest/witness interview feature and has its own review items. Retain all source attribution and distinguish adapted wording from verbatim source language.

## Latest reference-review reconciliation

CTM-reference-review-decisions.md and CTM-interview-category-bank.md now define the accepted category-driven interview model and application wording disposition. Add versioned category/question memberships, per-interview selection snapshots and structured report revisions referencing actual stored answers/evidence. No AI answer mapping or case export. Separate priest_testimony_requests/submissions identify marriage, subject party and author; scoped external submission link permits writing/recording only, with original audio/transcript/translation provenance and council-only review. Do not require a priest council/applicant account or grant case access. No general witness interview feature is revived.


## Investigation hierarchy, source context and evaluation releases

See CTM-investigation-model.md for petition nature -> template -> reusable common question family -> questions -> report. Add template/family memberships, exact source-question context links and confirmation events, linked evidence response references and category-based views over one dataset. Add conditional medical/psychiatric evaluation requests/reports and signed, versioned, scoped release attestations/disclosure events. No universal testing, new applicant evidence-description requirement, automatic answer rewriting or medical-document AI sharing. Detailed release text and sequencing require institutional confirmation.



## Current medical / psychological workflow authority — 2026-10-20

The user delegated completion of this section using prior CTM choices. [Medical and psychological report workflow](CTM-medical-psychological-report-workflow.md) is authoritative for requests, optional council-recommended doctors, alternative providers, signed release capture, private applicant uploads, council access within authorization, local OCR/search, case-manager-only routine notifications, revisions/follow-ups, reassignment and closure. It specifies architecture only; no production implementation exists.

This supersedes earlier conflicting admin/secretary on-behalf case-operation permissions for this section. Those roles support system-level/cross-program administration; they do not gain operational write access to assigned-case evaluation requests by role alone. Case-manager responsibility does not remove council case-read access or the signed report-disclosure scope. The exact institution-approved release text remains a document-content dependency. No external doctor portal, automatic clinical judgment or external medical-document AI processing is introduced.


## Confirmed template management and closed reports — 2026-10-20

[Template-management workflow](CTM-template-management-workflow.md) is the current authority for system-level shared-library publishing by admin/secretary; case-manager personal reusable templates; submission of personal templates for shared publication while keeping the personal original; retirement without loss of history; preserved unsent drafts with explicit refresh; and immutable sent-question snapshots.

Reports cannot be edited after case closure, including clerical corrections. Earlier report-author editing permissions apply only while the relevant case/proceeding is open. Reopening preserves the prior closed reports; new material follows the authorized appeal proceeding. These are documentation decisions, not implemented database permissions.


## Settings and translation authority — 2026-10-20

[Settings and translation architecture](CTM-settings-translation-architecture.md) records inspected prototype system/account settings and the newly requested translation configuration: exact editable/versioned Coptic Orthodox master prompt, primary/fallback AI slots, protected server-side API keys, and a future non-AI on-host engine mode. All translation outputs retain source/version provenance. Local OCR and medical-content restrictions override any provider fallback; prompt OCR instructions do not authorize external document uploads. Account settings cannot change system integrations. Shared question translations are reviewed/versioned before publishing. This specifies architecture only; no live integration or translated question bank was built.
