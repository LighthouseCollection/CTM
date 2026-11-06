# CTM confirmed database decisions

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Status: consolidated business-data decision register, 2026-10-20. This document is authoritative over older proposals in `CTM-data-architecture.md` and the prototype. It is not an executable schema, implemented security system or deployment approval. No application has been built.

## 1. Application boundary

CTM serves one council/tribunal through an applicant portal and a private council portal. All authorized active council members can view submitted cases, including both applicants' independent submissions. Applicants never see each other's questionnaire answers, corrections, evidence or communications.

PostgreSQL is approved. Initial deployment is a dedicated Linux VM on the user's server, with one disk and separate application/database/private-file directories. Distribution and operational setup are deferred. CTM must be portable to another VM, Azure or AWS without mandatory cloud-specific database/storage dependencies. Files are private, outside the public web root; PostgreSQL records ownership, relationships and versions. Plenix CDN is the future presentation layer, not a case-document store. No visuals or prototype redesign are part of this database review.

The future marriage ecosystem shares stable person/account identity through explicit boundaries. Marriage-preparation workflows are not built now and do not inherit access to CTM evidence.

## 2. Stable identity, account and case relationships

- Opaque permanent database keys identify people, accounts, applications, case participation, documents and versions. Display references are not authorization credentials.
- One applicant account spans all that person's cases. Google, Apple and email/password link to that account. New cases have new answers/uploads/signatures: nothing is prefilled from an old case or account profile into the questionnaire.
- Account creation and verified email precede application initiation. An email change requires verification before activation and preserves account/case history; it does not rewrite prior questionnaire contact answers.
- Council sign-in is email/password only. Council access cannot be gained through an applicant's Google/Apple sign-in. Two-factor authentication is not required. Neither council nor applicants have inactivity timeouts; sign-out, suspension/deactivation and authorized revocation remain effective.
- A person may have many historical cases but never two open cases. This includes open historical cases and applies across all verified linked accounts. An open case also blocks starting another new-case draft.
- When no case is open, at most one unfinished new-case draft exists per applicant. Resume that draft rather than create duplicates. Enforce uniqueness and case-state checks transactionally against stable/canonical identity.
- A case can have one participating applicant when the spouse has deserted or is absent. No fictional spouse account/application/signature is required. CTM does not handle same-gender marriage situations. Referenced spouse facts are not automatically verified identities or access grants.
- Two participating spouses share one case number and retain separate application/participation records. Admin/secretary adds the other party with first name, last name and email. CTM stores a pending association for that email and waits for the other party to register their own account and verify the same email; only then does CTM activate the existing-case link and applicant portal availability. Staff entry alone does not create a completed applicant account or grant access. This supersedes separate invitation acceptance. Preserve independent submissions/privacy and actual staff provenance. If that email already belongs to a registered, verified account, link it automatically subject to existing identity/open-case guards, without creating a duplicate account. User-portal design is deferred. See CTM-workflow-database.md.

## 3. Identifiers

New case: `YYYYMMDD-##`, values 01–99 per day. Use actual creation time in `America/Los_Angeles`, including daylight saving, regardless of applicant/server location. Allocate atomically, prevent duplicate allocation on retry, never recycle numbers, and preserve the authoritative UTC timestamp and captured local date.

Internal temporary applicant label: first/last initials + DOB YYYYMMDD + M/F, e.g. `JS19850314M`. It is not exposed and is not a unique database key. English-spelled first and last names are required for initials even in Arabic applications; middle names are excluded. Do not auto-transliterate.

Assigned CTM applicant reference: case number + identifier component, e.g. `20261020-01-JS19850314M`. This is case-specific, not ecosystem-wide. Once issued it never changes after identity-detail corrections. Current details and all corrections are stored separately.

## 4. Draft privacy, deletion and retention

Applicant-owned unfinished drafts are private: no council browsing/search of their contents. Scoped workers may scan/extract them privately. The narrowly authorized duplicate review exposes minimum matching identity information, not general draft access. Staff-prepared on-behalf applications require the later workflow design.

Applicants may delete their unfinished, never-submitted drafts and eligible draft files. A draft expires after 180 days of inactivity, with the policy/deadline disclosed and an email warning seven days before expiry. Committed applicant edits/uploads reset the deadline; merely viewing/logging in or administrative questionnaire migration does not. Reminder jobs must follow the current deadline and stop after submission/deletion/expiry.

Once submitted, nothing in the submitted application/case history is deleted. Cases are retained permanently. Keep original answers, all revisions, signatures/declarations, attachments and versions, findings/notes, appeals, financial events and audit provenance. No case purge or user-facing export feature exists. Temporary abandoned transfer chunks and derived caches are separate operational artifacts and cannot erase retained submitted evidence.

## 5. Questionnaire and declaration

Admin/secretary manage questionnaire questions, requiredness and English/Arabic declaration text. Published versions are immutable; edits create a new version. Preserve exact question/choice meanings, declaration language/text/digest and accepted version with every signed submission. Do not reinterpret old answers when labels/types change.

Unfinished drafts move to a newly published questionnaire version with entered answers preserved. Inform the applicant of new required questions. Submitted applications and subsequent corrections stay pinned to their original version. Use stable field codes and repeat-entry UUIDs rather than display labels or array positions. No incompatible migration may silently erase or reinterpret an answer.

English/Arabic questionnaires and declarations share the same semantic fields. Applicants may answer in either language, with original Unicode text preserved. Account-level English/Arabic preference controls future system emails/notifications, independently of answer language. Preserve the actual sent language/template version.

Applicant and council displays use one authoritative answer model. Additional questions must remain visible in version-driven council review even without a fixed prototype display slot. Council findings and operational records are separate from applicant assertions. The detailed current-field mapping is in `questionnaire-council-reconciliation.md`.

## 6. Confirmed questionnaire reconciliation

| Area | Confirmed requirement |
|---|---|
| Birthplace | Country only for applicant/spouse; no city/town question |
| Unknown spouse facts | Allow explicit Unknown without blocking submission |
| Spouse church | Add parish and Father of Confession; Unknown allowed |
| Spouse immigration | Add status; Unknown allowed |
| Spouse residence | Add country of residence; Unknown allowed; do not ask who spouse lives with |
| Children | Repeat name, DOB, gender and who child lives with; require answers for gender/residence but accept Unknown; age derived; no child testimony/accounts |
| Church marriage | Add ceremony diocese, Unknown allowed; distinct from current applicant diocese |
| Separation initiator | Applicant, Spouse, Both or Unknown, relative to source applicant |
| Marital status | Keep Married and Separated; do not add Civilly divorced |
| Civil divorce | Existing date, court name and civil case number required, plus finalized CDD upload; court-address requiredness not changed |
| Restraining orders | Multiple entries; court name, case number and current status required with no Unknown; each order requires its own uploaded copy |
| Reconciliation clergy | Repeating priest name only; no role/parish/contact/date/outcome fields |
| Prior applications | Multiple entries, each with date, council/diocese and outcome; external/pre-CTM history supported |
| Petition statement | Nonblank typed text OR uploaded PDF/DOCX satisfies requirement; both permitted |
| Grounds | Multiple selections from the approved list; still require statement |

Approved grounds, preserving the user's wording:

1. Infidelity
2. Desertion / abandonment
3. Abuse
4. Leaving or changing the faith
5. Addiction
6. Misrepresentation / concealment prior marriage

Imprisonment is excluded from new selections. Retain historical code/label provenance rather than delete historical values. Claimed grounds are not council findings or automatic eligibility decisions.

## 7. Submitted corrections and histories

While open, applicants may correct their own answers and upload additional/corrected attachments. No reason or new signature is required. Preserve original signed submission and every committed change, actual actor and server timestamp. A correction must not be represented as retroactively signed original text.

Admin/secretary may correct answers on behalf of the applicant while open, recording themselves as actors. These staff corrections send no notifications. Applicants and council can view the permitted answer history: applicants only their own, while open. A changed-field history icon opens a modal; soft-yellow emphasis is a later UI preference, not stored business data.

Contradictory answers from the two parties remain separate and attributed. Council findings do not overwrite them. Only current assigned council member/admin/secretary may record/revise findings, preserving every revision; all authorized council members can read them, applicants cannot.

Only current assigned council member/admin/secretary may add internal notes while open. Each person edits only their own notes, subject to current permission. Preserve all note versions with actor/time. At closure, findings and notes are read-only for everyone; new substantive material belongs to the separate appeal process.

## 8. Required uploads and file policies

Required before new petition checkout/submission: church marriage certificate (MC), civil marriage certificate (CMC), finalized civil divorce decree (CDD), applicant photograph, petition statement if not typed, and a copy for every reported restraining order. Fee waivers do not waive these requirements. Spouse photo: upload if available, absence does not block submission. Baptism certificates: not needed.

| File type | Per-file maximum |
|---|---:|
| PDF, image, Word DOCX | 25 MB |
| Ordinary audio attachment | 100 MB; testimony recording/upload is the later no-fixed-cap exception |
| Video | 500 MB |

No fixed attachment-count limit and no approved total-byte quota. Enforce safe types, actual received size, upload integrity and malware checks; no council acceptance gate. Completed safe uploads become current automatically. An unsafe/pending replacement never displaces the prior safe version.

Keep every submitted original/replacement as an immutable file version. Applicants see latest own version only; attachment-version history is council-only. Staff may upload corrected applicant attachments while open if assigned/admin/secretary, preserving applicant ownership and actual staff uploader/time. Staff corrections send no notifications.

Council-side uploads while open are restricted to assigned member/admin/secretary. Others can view/download. Log views/downloads with actor, exact version and timestamp. After closure, ordinary uploads stop. Access to original proceedings is locked; own appeals, correspondence/invitations and explicitly released decree certificates use the narrow scopes in CTM-workflow-database.md. Certificate access is party- and version-specific, never a generic redacted-copy rule.

### Filename presentation

Applicant file: `20261020-01-JS19850314M-CDD-20261022-1430.pdf`.

Case-wide council file: `20261020-01-DEC-20261022-1430.pdf`.

Use upload date plus HHMM in Los Angeles time, not document sequence. Case number retains its own sequence. Identical display names within a minute do not overwrite bytes: UUID/version keys and opaque storage locations distinguish files. Preserve full UTC upload timestamp.

Admin/secretary manage document categories/codes and changes update existing presented/download filenames. Preserve original upload filename and prior assigned names in history. Stable category purpose/UUID, source file/version, original manifests and file bytes remain unchanged; a code rename does not reclassify evidence. Confirmed codes: MC, CMC, CDD, DEC. Other codes can be configured later.

## 9. Processing and search

Run English/Arabic text extraction and OCR entirely on the CTM server. No case documents sent to external processing services. Extract PDF/DOCX text and automatically OCR scanned PDFs/images; preserve originals and store version-linked derivatives. Mixed-language text supported. Testimony audio is now approved for AI-API transcription and English/Arabic translation, with source/mixed transcript retained, complete language versions, timestamps/speakers and admin/secretary correction history. All testimony derivatives are council-only. The local-only PDF/image/document processing requirement remains; no general video transcription is approved.

Council search includes open and closed cases, structured fields, filenames and document text. Default to latest safe document version; a council option includes older versions. Counts/snippets/results obey the same permissions. Closed search results remain read-only. Extraction is asynchronous; failure is visible to council but does not invalidate an otherwise accepted upload. Validate Arabic search behavior in implementation rather than assume English indexing handles it.

## 10. Payments

Each person filing a petition pays USD 250; if both spouses file, each pays. Merely responding/joining without filing does not incur a filing fee. Each appeal filing is USD 250. Historical administrative entries are exempt.

Disclose fees before initiation. Final payment occurs only after application requirements are complete; verified success automatically finalizes the frozen submission idempotently. No normal pay-now/submit-later path. Preserve and reconcile technical failures after charging without a second charge. An authorized recorded admin/secretary waiver satisfies that filing's fee obligation without a fake payment.

Admin/secretary arrange waivers outside the applicant application and record them privately. No applicant waiver-request option. Fees are non-refundable after submission except accidental duplicate payments; admin/secretary authorize those refunds with full event history. All council members can view case financial details; viewing does not grant refund/waiver authority. No card security codes/raw card data stored.

Record verified provider chargebacks/reversals as immutable financial events; immediately alert admin/secretary and preserve the submitted application. Their processing consequences are deferred. Stripe Checkout is preferred, not finally onboarded. Payment provider integration stays replaceable.

## 11. Historical records and duplicate identity

Admin enters historical cases per spouse without filing fees. Both open/closed cases supported; open ones count toward the same one-open-case invariant. Keep original case numbers and existing applicant IDs. Assign new-format applicant references only when no prior ID exists and required details are known. Unknown/missing historical details and documents are marked unavailable; new filing requiredness does not block historical entry.

Admin/secretary may link historical participation to a verified account after identity verification, preserving original IDs/history and current access restrictions. Linking does not reopen a case or expose another spouse's data.

Possible duplicates require exact match of identity details including names, DOB and address, not fuzzy matching or email equality. Exact match pauses payment/submission, allows existing draft saving, and creates an immediate portal/email review alert to admin/secretary. Expose minimum identity-review fields, not general unfinished drafts. A matching candidate is not automatic proof or permission to merge.

Admin/secretary may confirm and consolidate duplicates under canonical identity, select a verified primary account and disable duplicate login/sessions. Preserve all source IDs/submissions/actor history; never delete a submission. Consolidation cannot leave two open cases. No-match does not prove different real-world identity; verified canonical identity remains the consistency key.

## 12. Case closure and appeal boundary

Issued decrees automatically close the case; approved Petition Denied closes without a certificate. Withdrawal closes when all participating parties withdraw, or the sole participant withdraws. No approval/reason for withdrawal; admin can withdraw for all. Reconciliation is withdrawal, not a separate outcome. Original substantive proceedings are locked; own appeal submissions, correspondence/invitations and released certificates have explicit portal scopes. Cases are never deleted.

Appeals may be submitted with no deadline, with petition/evidence and USD 250 payment or authorized waiver. They stay part of the original case and use its existing case number; no new public appeal number or applicant ID. Opaque internal appeal/submission keys preserve distinct history. Submission enters council review queue and does not open/reopen a case. Either applicant may submit an appeal independently at any time, including while the other appeal has reopened the same case (questionnaire A02). A different open case blocks acceptance/reopening for admin/secretary resolution; it must never produce two open cases. The confirmed appeals lifecycle and table/permission design are in CTM-workflow-database.md. Council acceptance reopens the same case into a new appeal section, preserving original proceedings read-only. One pending appeal or draft per applicant/case; separate applicants may file and be heard together with separate dispositions. Each appeal has its own declaration/signature, fee and permanent history. Applicant-only supplements are additions, not edits to the submitted statement. Pending appeal withdrawal requires no approval/refund. Decline sends an automatic notice with optional explanation; acceptance notifies both privately. The regular hearing/decision/decree process applies, with the first appeal decree suffix A1.

## 13. Communications and notification policy

CTM sends case emails/stage updates; private portal chat is not approved. Assigned member/admin/secretary may manually send case emails, with actual sender/time preserved. Confirmed hearing, testimony, withdrawal, appeal and decree notification triggers are specified in CTM-workflow-database.md. Messages may target either applicant or both with private deliveries/replies, including after closure.

Keep exact sent subject/body, recipient/address snapshot, actor, timestamps, language/template and delivery attempts. Automatically capture incoming applicant reply bodies, correctly linked to case/participation through validated routing; ambiguous routing is held for review. Preserve reply history; a reply is not a formal submission or answer correction.

No attachments accepted by email. Return incoming attachments with notice directing portal submission; never index or serve them as accepted case evidence. Restricted transient return handling is not a permanent case-document intake route. Outbound case documents use authorized portal links except the explicit rejection/return operation.

| Event | Recipients and timing |
|---|---|
| Applicant committed answer correction/new or corrected upload | Assigned member + secretary; portal immediate, email summary after ten minutes without further qualifying changes |
| Staff answer/attachment correction | No notifications; history/audit preserved |
| Duplicate-review hold created | Admin + secretary; immediate portal and email |
| Chargeback/reversal | Admin + secretary; immediate alerts |
| Applicant suspension/reactivation | Applicant email, selected language |
| Draft expiry warning | Applicant email seven days before current deadline |

No assigned member means secretary receives the applicant-update notice. Deduplicate one account holding multiple recipient roles. Notices avoid sensitive answer/file content and DOB-bearing references. Persistent outbox/batch state supports retries without duplicate messages.

## 14. Permission summary

| Operation | Permitted authority |
|---|---|
| Read submitted cases, both parties, findings/notes, case audit and financial records | All authorized active council members |
| Read system-wide audit | Council admin/secretary only |
| Read applicant unfinished drafts | Applicant owner only; narrowly scoped identity-review exception |
| Edit applicant answers on behalf while open | Admin/secretary |
| Record/revise findings while open | Assigned member/admin/secretary; all changes retained |
| Add internal notes while open | Assigned member/admin/secretary |
| Edit internal note | Original author with current role/assignment permission; open case only |
| Council uploads/replacements/manual case emails | Assigned member/admin/secretary; applicable lifecycle checks |
| Council account create/deactivate/reactivate/role change | Admin/secretary |
| Applicant suspend/reactivate; verified duplicate consolidation/linking | Admin/secretary |
| Fee waiver/accidental duplicate refund authorization | Admin/secretary |
| Questionnaire/declaration/category-code administration | Admin/secretary |
| Applicant own answers/history/own latest attachments | Applicant owner while open; no other-party access |
| Applicant closed case | Released entitled certificate; own appeal, correspondence and invitation scopes only; original proceedings locked |
| Case purge or export | Not available |

Permissions are server-enforced and backed by appropriately scoped database roles/policies, checked foreign keys and transactional invariants. Hosted VM/database administration alone is not an application council role. Account deactivation preserves authorship and ends sessions. No automatic inactivity timeout removes the need for revocation checks.

## 15. Physical design work still required

Documentation reconciliation is complete in [database tables](CTM-database-tables.md), [permissions](CTM-permissions.md) and the [architecture overview](CTM-data-architecture.md). The earlier proposal is archived; its superseded exports/purge/chat or draft-reading assumptions are not current requirements. No executable schema or migrations were created. Future physical design must implement and validate the reconciled relationships and guards after the deferred workflows are agreed.

Use unique keys and guarded transactions for one open case, one new-case draft, one assigned member, daily case counters, idempotent filings/payments/events, and correct same-case/party/version relationships. Signed snapshots are immutable. Current views never become competing sources of truth. RLS is defense in depth and needs real tests, including connection-pool identity isolation and bypass-role restrictions.

The detailed schema/permission documentation has been reconciled against this register and source mapping; see [reconciliation report](CTM-reconciliation-report.md). Before production implementation, test concurrency, false identity matches, payment retry recovery, file/DB reconciliation, closed-case locks, no cross-party retrieval, historical data exceptions and Arabic extraction/search. No test database or physical migrations have been created; documentary review is not enforcement validation.

## 16. Confirmed workflows and remaining decisions

The [workflow database supplement](CTM-workflow-database.md) is authoritative alongside this register and forms part of the [table dictionary](CTM-database-tables.md) and [permissions](CTM-permissions.md). It consolidates every confirmed initial-review, assignment, session/agenda, attendance/testimony, transcript, hearing outcome, voting/presidential approval, withdrawal, decree/template/signature/release/replacement and appeal rule. The [workflow discussion record](CTM-case-session-workflow.md) preserves the decision detail; superseded questions are not requirements.

Identifiers: council session hidden CSYYYYMMDD, display Council Session YYYY-MM-DD, one/date; moving a planned meeting creates a new dated session, transfers all attached cases, and removes cancelled meeting while preserving case transfer audit facts. Decree DCR-{case number}, first appeal decree -A1; DEC remains the attachment category code. Certificate language selectable English/Arabic/both; both means one bilingual document.

Only president authorizes assignments/reassignments; admin/secretary records. Only assigned member presents; absence causes manual deferral. Voting stays prototype-simple Approve/Deny/Abstain, full member list regardless of attendance, individual votes/tally council-visible; president final approval with or without votes. Exact type and grounds precede voting; revised content requires fresh approval. Principal versus actual entering actor is always preserved.

Admin/secretary prepares certificates; president Bishop/Metropolitan signs. Signed file must be stored before issuance/automatic closure. Issuance notices do not expose certificate. Explicit recipient/version release sends availability notice; view/download logged. Clerical corrections retain decree ID, require re-signing and fresh release; superseded versions council-only. Release/withdrawal/correction administration and authorized correspondence are narrow post-closure exceptions.

Remaining business boundaries: responding-spouse onboarding/linking; historical-entry finalization; exact conditional/nullity recipient mapping; subsequent appeal decree numbering; long testimony recordings; open-case conflicts at appeal reconsideration. These are not permission to reopen settled voting or appeal questions.

Later engineering choices: Linux distribution/VM capacity, backup destination/schedule/recovery targets, framework/auth integration, exact OCR/search packages, email and AI providers, Stripe account setup and physical SQL/RLS/concurrency validation. Institutional declaration/template wording still needs institution-supplied content. No application, SQL or migrations have been built.







## 17. Independent spouse filings: marriage association

Independently filed applications for the same marriage automatically link without an invitation or staff confirmation when the confirmed exact marriage-identity combination matches: marriage date, both spouses birth dates (roles may be reversed), and marriage-certificate registration number when available. Names and church/location spelling are not exact-match gates. This is distinct from duplicate-person consolidation; retain separate applicants, submissions, payments and privacy. If certificate number is unavailable, exact marriage date plus both spouses birth dates is sufficient for automatic linking; collision/conflict and existing-case-number handling remain unresolved. See CTM-workflow-database.md section 8.



Matching precedence clarification: exact marriage date and both spouses birth dates are sufficient even if supplied certificate numbers differ. Preserve both numbers/source assertions. If conflicting certificate numbers lack that exact three-date match, administrator/secretary reviews. Certificate-number equality alone does not establish an approved alternative match rule.


## 18. Questionnaire response authority

The [questionnaire decision register](CTM-questionnaire-decisions-2026-10-20.md) incorporates every answer and clarification from the user's returned worksheet. It is authoritative over earlier conflicting limits/assumptions. The linked workflow database supplement contains the associated relationships and integrity gates. Confirmed key changes: certificate-based marriage matching must be supported as an alternative to birth dates (minimum combination awaiting clarification); first case number retained with historical aliases; two applicants' appeals remain independent even during reopening; one current valid decree with retained void history; no fixed testimony capture/upload size or duration cap; open-source audio recording and PDF scanning requirements; generated testimony text reviewed by admin/secretary before wider council visibility. Decree-certificate handover and applicant portal details remain explicitly deferred.

Historical transcription corrections, template administration, return/resubmission notices, conditional/nullity recipient mapping, subsequent appeal decree suffixes, appeal refiling and account-association rules are detailed in the register. Earlier broad unresolved lists must not reopen those settled questions. Only identified interpretation boundaries remain open; no application/database has been built.

## 19. Applicant portal and assigned-member interview decisions

[Returned portal/interview responses](CTM-portal-interview-decisions.md) are authoritative for the newly discussed scope. Portal: one current-workflow view, past cases, safe event timeline/actions, completeness/review/correction screens, explicit field/section Save, expiry warnings, case information requests, private portal/email correspondence, contextual documents, own fees/receipts, appointments/reminder/read notifications, own appeal additions/results, withdrawal confirmation and explicitly released PDF decree. No applicant case export, council interview disclosure or other-party access is added. Requested submissions are automatically received and flagged New, with no staff acknowledgement/completion step. Profile-versus-case-field behavior still needs explanation; no unconfirmed write is inferred.

Investigation interviews are distinct from rare council testimony. Only assigned member conducts/authors; admin/secretary may enter/upload on behalf. Only case applicants are in scope, interviewed separately; prototype priest/witness types not approved. Standardized bilingual versioned guided templates permit structured/rich text and added numbered follow-ups. Preserve metadata, save/resume, chronological log, exact evidence links and separate observations. Optional informed microphone/upload recording, including mobile web, no fixed cap, interruption recovery; automatic API transcription/translation with timestamps/speakers and assigned-member review. No AI mapping into questionnaire answers. All authorized council can see unfinished interview narrative, completed records/audio and reviewed text; unreviewed AI text restricted. Applicants cannot access interviews. Author/current-permission/open-proceeding checks govern revisions; reassigned member adds follow-up instead of rewriting prior narrative.

The [standard interview template draft](CTM-guided-interview-template-draft.md) is proposed wording for review, not an approved published questionnaire. P13 is resolved as automatic receipt/New flag, without staff completion; P30 and C34 remain unresolved explanations.


## Latest reference-review reconciliation

The returned 60 reference-review responses in CTM-reference-review-decisions.md supersede pending source-study proposals. Application remains concise: accepted narrative/final-divorce/priest wording and blood relationship only; prior marriage narrow spouse-name/permit clarification; pre-acquaintance religious affiliation with Coptic/typed-other branch; specified topics move to interview. Rejected fields/labels/modules are not added. Interview uses selected detailed categories, explicitly Children/Money/Intimacy, and assembled report sections. Priest may submit a separately requested, explicitly subject-identified free-form written or recorded testimony through a scoped link. Exact medical wording, priest link verification and external-report AI reviewer remain focused follow-ups. No application code has been built.


## Investigation organization and evaluation releases

CTM-investigation-model.md records the user-directed petition nature/template -> reusable Common question family -> detailed question -> report model, alternative council views over the same records, exact application-answer confirmation and evidence integrated as questionnaire context. Add conditional medical/psychiatric tests/evaluation records on applicant and council sides with signed release disclosure, exact scope/version/signature, no universal testing or automatic medical AI sharing. Final release wording/access sequencing remains for institutional confirmation. Previous rejected applicant evidence-description field and applicant isolation remain unchanged.



## Adopted contextual questioning — 2026-10-20

The user accepted the complete [Context-Sensitive Investigative Questions companion](CTM-context-sensitive-investigative-questions.md) for the question bank, intake-template preparation and reporting workflow. This supersedes the earlier presentation rule that every optional probe must be folded into the main question. The 59 existing main questions and agreed category names remain unchanged. The companion headings do not rename or split those categories. No retired question is reactivated; no removed standalone EVD section is restored. References to EVD mean existing evidence/file-version links, not a new EVD questionnaire.

The assigned case manager priest chooses Topic group → Question categories → Questions, with the current foundational questions retained, and can add case-specific questions. Each stable question ID has versioned conditional prompts, a trigger and avoid/reuse guidance. Ask only for missing relevant facts after checking the application, earlier responses, chronology and authorized evidence. Prompts are optional, not required fields or proof thresholds; no automatic branching or automatic inference is adopted. A completed response is referenced rather than collected again. Keep each party's account and evidence permissions separate.

Template preparation and council interviewing can use these prompts as interviewer aids. They are not automatically inserted as extra applicant questions; the case manager may explicitly select or adapt a relevant clarification before sending. The exact sent questions and their order are preserved; the recipient's submitted response remains locked as already agreed. Sending freezes questions, not a copy of all guidance. Follow-up investigations create separate linked intakes/reports. Main wording changes still require an explicit decision; acceptance of the companion does not apply the separate seven-revision review.

Interviewer-only avoid/reuse instructions and the separate council assessment guide remain guidance, not answers, applicant-facing report content or automatic findings. The original main question, optional prompt definition/version and any clarification actually asked must be distinguishable. Human council findings remain separate from attributed answers, source evidence, transcript and priest testimony. No credibility scoring or canonical decision automation is introduced.

Medical signed-release, restricted disclosure and local document processing rules continue. Audio transcription authorization does not authorize external medical-document AI processing. No extra mandatory uploads, child interviews, general witness module or broad medical-history collection is added.

The planner now shows available prompts in collapsed **Conditional follow-up prompts** under the corresponding questions, with no empty helper section. This is a planning artifact only. Full trigger/avoid-reuse guidance and council assessment text remain available in the adopted companion.


## Current medical / psychological workflow authority — 2026-10-20

The user delegated completion of this section using prior CTM choices. [Medical and psychological report workflow](CTM-medical-psychological-report-workflow.md) is authoritative for requests, optional council-recommended doctors, alternative providers, signed release capture, private applicant uploads, council access within authorization, local OCR/search, case-manager-only routine notifications, revisions/follow-ups, reassignment and closure. It specifies architecture only; no production implementation exists.

This supersedes earlier conflicting admin/secretary on-behalf case-operation permissions for this section. Those roles support system-level/cross-program administration; they do not gain operational write access to assigned-case evaluation requests by role alone. Case-manager responsibility does not remove council case-read access or the signed report-disclosure scope. The exact institution-approved release text remains a document-content dependency. No external doctor portal, automatic clinical judgment or external medical-document AI processing is introduced.


## Confirmed template management and closed reports — 2026-10-20

[Template-management workflow](CTM-template-management-workflow.md) is the current authority for system-level shared-library publishing by admin/secretary; case-manager personal reusable templates; submission of personal templates for shared publication while keeping the personal original; retirement without loss of history; preserved unsent drafts with explicit refresh; and immutable sent-question snapshots.

Reports cannot be edited after case closure, including clerical corrections. Earlier report-author editing permissions apply only while the relevant case/proceeding is open. Reopening preserves the prior closed reports; new material follows the authorized appeal proceeding. These are documentation decisions, not implemented database permissions.


## Settings and translation authority — 2026-10-20

[Settings and translation architecture](CTM-settings-translation-architecture.md) records inspected prototype system/account settings and the newly requested translation configuration: exact editable/versioned Coptic Orthodox master prompt, primary/fallback AI slots, protected server-side API keys, and a future non-AI on-host engine mode. All translation outputs retain source/version provenance. Local OCR and medical-content restrictions override any provider fallback; prompt OCR instructions do not authorize external document uploads. Account settings cannot change system integrations. Shared question translations are reviewed/versioned before publishing. This specifies architecture only; no live integration or translated question bank was built.


## Arabic user interface — confirmed 2026-10-20

The user explicitly extends the same translation service and editable master prompt to Arabic localization of both applicant and council interfaces. This adds English/Arabic interface-language selection, not just questionnaire or notification translation. UI preference is an account preference and remains distinct from notification language, source-answer language and a report translation target. Language selection must also be available on public/sign-in screens before authentication, then honor the saved account preference after sign-in.

Translate versioned resource keys for navigation, headings, buttons, field labels, validation and error messages, statuses, instructions, dialogs and accessibility labels. Generate drafts through the configured translation route and prompt version, review and publish bilingual resource bundles through system-level content management. UI pages read published resources locally; they do not call AI on page load or send current case data for label translation. Missing or failed translations use the available English resource rather than displaying an empty control or fabricated text.

Preserve interpolation variables, plural rules, HTML safety, route/API identifiers and stable status values. Never translate executable code, keys, user identifiers, case numbers, filenames, monetary values or original user answers as part of UI-label localization. Supplied source text and runtime variables remain separate; render escaped data, not provider-generated executable markup. Publish resource version, source/prompt/provider provenance and reviewer history; updating interface wording does not rewrite case records or sent messages.

Arabic mode uses right-to-left page flow and bidirectional handling of mixed Arabic/English text, with readable Latin case numbers, dates, email addresses, names and file codes. Use the Plenix design system's supported localization/layout capabilities when implementation begins, verifying support then. Interface controls may mirror where appropriate; media playback and content-specific direction must retain their intended meaning. No conversion of identifiers or stored timestamps follows merely from choosing Arabic. Exact Arabic register/terminology for UI resources is configured and reviewed without inventing a default in this design.

Proposed records: ui_message_keys (stable key/context and source version), ui_translation_versions (locale/register/text, placeholders, job/output and review/publication provenance), ui_resource_bundle_versions (published immutable resource set and rollback history), and account_preferences.ui_language. Public pre-login choice is presentation-only and grants no access. Interface language and rights are independent; all existing case privacy, release scope and council/applicant authorization applies in either language. No new application UI or actual Arabic resource bundle has been built in this documentation step.


## Required package capability: council Microsoft sign-in — 2026-10-20

User confirmed inclusion of Microsoft sign-in in the delivery package. [Council Microsoft sign-in](CTM-microsoft-council-sign-in.md) supersedes the earlier council email/password-only restriction by adding organizational Microsoft authentication. Admin preauthorizes the CTM member and role; a Microsoft/lacopts email alone never grants access. Provider configuration belongs to admin system settings, identity links use validated tenant/object identity, and applicant/external-priest authentication remains separate. This is specified, not deployed; actual tenant/app registration, credentials and callback configuration are required before a live connection.


## Consolidated technology register — 2026-10-20

[Technology, open-source tools and deployment plan](CTM-technology-and-open-source-stack.md) is the current consolidated reference for Django/Rails/Frappe comparison, performance considerations, the Plenix-aligned processing/search stack, browser recorder/viewers, private storage responsibilities, container/service reuse and unresolved technical choices. It distinguishes agreed requirements, reuse baseline, candidates and external services. No application framework or pinned tool version is selected by documenting this register. No installation or performance benchmark has been run.


## Hosting clarification — 2026-10-20

Latest user decision: final hosting will be either Azure or a private server at a designated location with VPN access. The choice and network-access details will be discussed later. Do not treat an Azure migration in one week, public internet availability, or a specific VPN product as a committed deployment requirement. The immediate objective is a fully working functional demonstration for approximately 10 users. Use one dedicated Linux CTM VM containing multiple containers managed as one deployment package, with private persistent storage and a tested backup/restore plan. Keep hosting-specific endpoints, secrets, storage paths and provider callbacks configurable so the same application package can be deployed to either destination. Framework selection, VM sizing, distribution and exact software versions remain pending; this hosting clarification does not finalize them.


## Selected Django + Plenix React CDN — 2026-10-20

The user selected Django with Plenix CDN and identified Plenix as React-based. [Django–Plenix integration](CTM-Django-Plenix-integration.md) defines the compatible browser/server roles, same-origin deployment recommendation, protected endpoints and CDN integration verification. Earlier framework comparisons remain decision history; Django versus Rails/Frappe is no longer an open choice. Exact dependency versions, provider configuration and hosting remain deployment details. No actual application was built by recording this selection.


## Initial VM deployment address — confirmed 2026-10-20

The user will initially install CTM on their own VM and access it at **https://ctm.lighthouseway.org**. Both applicant and council portals belong to this application origin; exact portal route paths are implementation details. Django sessions, CSRF origin checks, reverse-proxy/HTTPS settings and approved identity-provider callback registrations must use this canonical address. Payment/email callbacks use the same configured public application base URL where applicable. Do not invent a VM IP, DNS record, reverse proxy product or active provider connection from the supplied hostname.

Application availability at this address does not make case data public. Authentication, admin-only council enrollment, applicant isolation and private file/search access remain required. Database, search, processing services and storage management endpoints stay private. Whether network access will also be restricted by VPN must follow the final access decision; browser reachability and external provider webhook reachability must be configured explicitly rather than assumed.

This selects the initial own-VM deployment, while a later Azure/private-server move remains a separate future discussion. No DNS, certificate, VM, deployment or network setting was changed or verified by documenting the URL. All host-specific settings remain configurable for portability.


## Locked council navigation and layout map — 2026-10-20

[Council navigation and layout](CTM-council-navigation-and-layout.md) records the user's locked hierarchy, Communications directly after Case Overview, Appeals beneath Decision, no case list in navigation, and the persistent sidebar avatar/name trigger with a hidden account/system menu subject to documented Plenix support. It distinguishes agreed case-report split view from proposed evidence/document/communication/assessment layouts and optional search/appeal previews. No unverified custom Plenix shell or component has been built.


## In-app communications and call workflow — 2026-10-20

User explicitly requests in-app messaging, email and calling under Communications. [Communications workflow](CTM-communications-workflow.md) supersedes older email-only/no-chat statements and distinguishes reliable device-dial initiation logging from integrated telephony answered/duration/recording events. Asterisk is an optional open-source candidate only; normal tel links cannot record the other party's telephone audio. Search and Appeals split-view previews are now confirmed in the navigation/layout map. No phone system or UI was installed.


## Confirmed native messaging policy — 2026-10-20

[Communications workflow](CTM-communications-workflow.md) now records permanent sent messages, corrections by new message, existing/new document links backed by normal case storage, no council-only chat, existing-account/case access without separate messaging accounts, immediate portal availability, and immediate or 17:00 America/Los_Angeles email-summary delivery. This does not change other workflow-specific notification schedules. No live messaging service was built.


## Web calling scope finalized — 2026-10-20

Manual call log only: person, actual call date/time, outcome and notes, with separate automatic entry actor/timestamp. No dialling, phone-system integration, automatic duration or telephone recording in the web package. Asterisk is not a selected dependency. Communications uses the exact actions **Send Immediately** and **Send after council session**. See [current Communications rules](CTM-communications-workflow.md).


## Approved applicant application flow — 2026-10-21

[Applicant application process](CTM-applicant-application-workflow.md) records the user-approved sequence: fee/document information, provider account, eligibility/resume, section-based form and contextual uploads, private saved draft, review/declaration, final payment and submission, confirmation, completeness review/return and council processing. It preserves existing identity/payment/privacy/history rules and uses the strict Plenix contract. This approval concerns the application process; earlier proposed applicant shell navigation and split views are not automatically locked. No production application was built.
