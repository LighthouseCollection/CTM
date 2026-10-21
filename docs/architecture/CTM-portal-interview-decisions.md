# Applicant portal and investigation interviews: reconciled decisions

Source: user's returned `ctm-applicant-portal-review-v1` and `ctm-case-interview-review-v1` responses. Every response ID is represented below. Clarifications override selected choices and worksheet proposals. These are data/workflow requirements, not implemented features. This supplement is part of the architecture, table dictionary and permissions; earlier conflicting review placeholders are superseded.

## Applicant portal

| ID | Reconciled decision |
|---|---|
| P01 | One current-workflow view at a time; reject the proposal to place an open case, unfinished new application and pending appeal together as simultaneous dashboard work. Show the relevant current stage. This is a presentation clarification, not a new ban on the previously approved independent appeals against the same case. Past cases remain separate. |
| P02 | Separate past-cases list with permitted references, messages/appeals and released certificates; no unlocking of original closed substantive material. |
| P03 | Applicant-safe case timeline of key events, excluding council-only material. |
| P04 | Prioritize applicant actions requiring attention. |
| P05 | Explain that the case is closed and appeal is conditional on new information/evidence. This is appeal eligibility wording, not a new decree type called Conditional Appeal. |
| P06 | Draft completeness checklist by sections, required fields and documents. |
| P07 | Review own answers/attachments before declaration/signature and final payment. |
| P08 | Returned application leads with correction instructions and relevant form areas. |
| P09 | Explicit Save for a changed field/section after submission; retain committed history. |
| P10 | Portal draft-expiry warning in addition to existing warning policy. |
| P11 | Case information request can appear as an actionable item with applicant response area. |
| P12 | Applicant can attach requested documents directly while case/proceeding upload scope permits. |
| P13 | Clarified: information or documents submitted into CTM are automatically received and flagged New. No staff acknowledgement, acceptance or Request completed action is needed. Preserve submission/receipt actor/time and existing notifications. |
| P14 | Applicant can initiate case messages through the portal as recorded correspondence, not live chat. |
| P15 | Portal and email replies join one private correspondence history for that applicant. |
| P16 | Documents must attach to and display at their correct form/question/request location, not merely a generic category folder. Also group latest own documents by category and apply the existing case/applicant/category/upload-time naming convention. |
| P17 | Replacement upload identifies which document is being replaced; prior versions retained council-only. |
| P18 | Own fee/payment/waiver status and receipt per filing. No other-party financial disclosure or waiver-request feature. |
| P19 | Individual payment receipt download permitted; this is not case export. |
| P20 | Own testimony appointments area, existing Confirm/Reject behavior. |
| P21 | Staff-supplied address/map or remote attendance link for own appointment. No automatic video-hosting feature. |
| P22 | Automatic reminder one day before testimony. Channels were not separately specified; do not invent an SMS channel. |
| P23 | Own unread/read notifications and Mark Read; reading is not proof of legal service. |
| P24 | Own appeal statement, additions, fee and Accept/Decline result together. |
| P25 | Chronological own appeal supplements, no rewriting original statement. |
| P26 | Short confirmation before petition/appeal withdrawal, without approval or required reason. |
| P27 | Notice explains certificate unavailable until staff release, with no premature file exposure. |
| P28 | Released certificate is a PDF with decree ID, language, release date and View/Download under exact release entitlement. |
| P29 | Account settings contains notification language and verified email-change workflow. |
| P30 | Unresolved explanation requested: distinction between account contact updates and already-submitted application answers. Existing non-retroactive signed-submission/history rules stay in force; no automatic rewrite approved. |

## Assigned case-owner interviews

| ID | Reconciled decision |
|---|---|
| C01 | Investigation interview differs from rare applicant testimony to the council. Separate events/records; no automatic agenda/council-testimony workflow for ordinary interviews. |
| C02 | Only current assigned council member conducts/authors investigation interviews. |
| C03 | Admin/secretary may enter/upload on that member's behalf, preserving actual interviewer and actual entry/uploader separately. This is not substitution as interviewer. |
| C04 | Priest/witness interviewee list is not applicable; do not create those interview participant types from the prototype. |
| C05 | No priest/witness contact directory or accountless contact feature for this workflow. |
| C06 | Applicants interviewed separately. |
| C07 | Admin/secretary creates/version-controls templates, with standardized templates as the default; preserve exact version per interview. Clarification allows their own versions, not an unapproved new role permission. |
| C08 | Templates may vary by applicable interviewee type. In light of C04/C05, scope to case applicants/parties; do not infer priest/witness support from the worksheet examples. |
| C09 | English/Arabic versions of the same questions. |
| C10 | Assigned member may add case-specific follow-up questions without rewriting published template. |
| C11 | Structured fields plus rich-text answers supported. |
| C12 | Template is a guided questionnaire. Side-by-side prior application answer display was not confirmed and is not a requirement. |
| C13 | Person, actual interviewer, method, date/time, location and duration retained. |
| C14 | Save unfinished interview and resume later, distinct from council hearing Send behavior. |
| C15 | Completed interviews are separate entries in chronological case interview log. |
| C16 | Specific question/notes can reference exact discussed evidence versions. |
| C17 | Separate council observations/recommendations from the interviewee's statements. |
| C18 | Audio recording optional for ordinary interviews; council-session applicant testimony remains mandatory recording. |
| C19 | Record that participant was informed before recording starts; institutional wording not fabricated. |
| C20 | Microphone capture and audio upload, including directly from mobile web app. No native mobile app is built/implied. |
| C21 | Pause/resume and interruption recovery preserve captured portions and actual timeline/gaps. |
| C22 | No fixed duration/file-size cap for investigation recordings, like testimony. Ordinary applicant audio attachments remain a distinct purpose. |
| C23 | Optional question markers; questionnaire template/question references numbered. Preserve stable template/question IDs even if display ordering changes. No compulsory marking. |
| C24 | Saving recording queues AI API transcription; extends approved audio processing scope explicitly to investigation interviews. Provider/retention setup remains later work. |
| C25 | Same original/English/Arabic and mixed-language behavior, timestamps and speaker labels as testimony, original audio/AI output retained. |
| C26 | No AI mapping/suggestions from transcript passages into template-question answers. Markers/manual authoring only; no generated questionnaire answers. |
| C27 | Assigned member reviews/corrects generated interview text before other council can read it; retain versions/actor/time. This differs from admin/secretary review of council-testimony text. |
| C28 | Manually typed interview answers remain separate from transcript, including after review. |
| C29 | Unfinished interview record visible to all authorized council members ("anyone" reconciled with C31 council-only restriction). Not public or applicant-visible. Unreviewed AI text stays restricted by C27 even when draft narrative is visible. |
| C30 | Completed interviews/audio/reviewed transcripts readable by all authorized council. |
| C31 | All investigation interview material council-only; applicant requests go through ordinary case messages. |
| C32 | Original interviewer alone revises completed narrative while case open, with all versions preserved; current permission/assignment check still required. On-behalf initial entry C03 is not a blanket revision grant. |
| C33 | New assigned member adds follow-up interviews, does not rewrite former interviewer's narrative. |
| C34 | Unresolved explanation requested about selecting information for council briefing. Do not add automatic summarization, transcript redistribution or mandatory selection workflow. Existing approved council access remains. |

## Proposed relational structure and enforcement

Reuse case/proceeding, account/person, correspondence/recipient/delivery, documents/versions, template versioning, audit, notifications and AI-processing infrastructure; do not duplicate those domains.

| Record | Principal relationships / constraints |
|---|---|
| `case_information_requests` | case/proceeding; authorized requesting staff; specific recipient; message reference; instructions/time. Response links to existing correspondence and permitted upload targets. Submission is automatically received and flagged New; no staff completion/acknowledgement gate. |
| `information_request_responses` | request; own applicant; response message; evidence-manifest references; actor/time. Open-proceeding checks on new evidence. |
| `document_context_links` | exact file/version; case/party/proceeding; question/repeat-entry or information-request purpose. Correct-location retrieval and ownership checks; category alone does not establish attachment purpose. |
| `interview_templates` / `interview_template_versions` | stable template ID/display number; standardized or derivative lineage; applicable party scope; bilingual exact content; publishing admin/secretary/time. Published versions immutable. |
| `interview_template_questions` | stable question code/number; exact version/language text; order; structured/narrative field type. Case-specific follow-ups stored separately with actual author/time. |
| `case_interviews` | case/proceeding; interviewed applicant; assigned interviewer; actual entered-by actor; template version; method/date/location/duration; unfinished/completed; timestamps. Readable to council, applicant-denied. |
| `interview_answer_revisions` | interview/question or follow-up; typed answer or narrative; source actor/time; predecessor. Separate from application answers, findings and audio transcript. |
| `interview_observation_revisions` | interview; council-only observations/recommendations; author/time; history. Never attributed as the interviewee's words. |
| `interview_recordings` / `interview_capture_parts` | interview; informed-about-recording event; original immutable audio version(s); actual recorder/uploader; ordered segments/gaps; microphone/upload/mobile-web origin; checkpoints. No user-facing fixed capture cap; retain originals, operational provider chunking does not alter their meaning. |
| `interview_question_markers` | optional audio-relative time; stable template/follow-up question; author/time. Manual links only, not AI answer mapping. |
| `interview_text_versions` / `interview_text_segments` | recording/run; original/English/Arabic type; predecessor/source-version; text, audio times and speakers; AI/editor provenance. No automatic overwrite of guided-questionnaire answers. |
| `interview_text_review_events` | exact version; assigned reviewing member; review/correction/release time. Other council text retrieval/search requires reviewed version; underlying draft interview narrative/audio have independent scope. |

All foreign keys must validate same case/proceeding/applicant/source. Closed proceedings lock substantive interviews and audio/text sources; new appeal interviews belong to the new open proceeding. Original narrative revisions require author plus current assignment permission. Reassignment never rewrites prior authorship. Admin/secretary may enter/upload on behalf but may not bypass C02, C27 or C32. Interview captures and signed certificate files are not ordinary applicant uploads.

Portal workflows use projections of existing authoritative records, not another database copy. Current-workflow display does not enforce a new prohibition on independent same-case appeals. Notification read state is per recipient. Receipt is automatic and new submissions are flagged New; no staff completion status; closed-case correspondence does not unlock evidence uploads. All released decree certificates are PDFs and remain subject to recipient/version release checks.

## Templates and unresolved explanations

A [draft standardized guided interview template](CTM-guided-interview-template-draft.md) provides numbered English/Arabic questions and structured metadata for review. It is not published or institutionally approved, and no interview form has been implemented. Admin/secretary can maintain standardized/derivative versions once the content is agreed.

P13 is resolved: automatic receipt with a New flag, no staff completion action. Remaining worksheet explanations: P30 (profile versus submitted answers) and C34 (briefing selection). C12 side-by-side display remains unapproved and unnecessary for the guided questionnaire. P01 is interpreted as one current-workflow view, not a rewrite of prior independent-appeal rules. C08 is scoped to applicants, not rejected priest/witness types.


## Template refinement: strategic factual discovery

User directs categorized discovery rather than a flat narrative prompt list. Every interview and separately started recording identifies the applicant. Separate application-data confirmation from identity opening. Establish requested outcome (divorce/dissolution, annulment/nullity or other) and stated grounds before exploring events. The revised draft uses ordered categories: opening/identity, request/basis, application confirmation, chronology, each-ground factual inquiry, evidence/discrepancies, reconciliation/current context and closing clarification. Requested relief is an applicant assertion, not the approved council decision. Category/question identities and recording opening links are required in the future template model; substantive wording remains a draft for institutional review.

## Latest reference-review reconciliation

Later reference-review clarifications supersede the initial flat-template draft: accepted detailed category selection assembles interview reports, with Children/Money/Intimacy explicit. A separately requested free-form priest report by scoped link is now confirmed; it is not an added priest/witness interview type. See CTM-reference-review-decisions.md for all 60 source decisions and retained author/privacy/history boundaries.



## Approved applicant application flow — 2026-10-21

[Applicant application process](CTM-applicant-application-workflow.md) records the user-approved sequence: fee/document information, provider account, eligibility/resume, section-based form and contextual uploads, private saved draft, review/declaration, final payment and submission, confirmation, completeness review/return and council processing. It preserves existing identity/payment/privacy/history rules and uses the strict Plenix contract. This approval concerns the application process; earlier proposed applicant shell navigation and split views are not automatically locked. No production application was built.
