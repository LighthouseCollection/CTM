# CTM consolidated build specification

Version: ctm-build-contract-2026-10-21-v1. Status: implementation specification; no production database or application provisioned.

## Authority and scope

This is the current entry point for building CTM. It consolidates the conversation and the architecture documents recorded in `source-register.json`. Earlier worksheets, Catholic reference forms, prototype demo arrays and research proposals are not competing requirements. The latest explicit user decision wins. Existing files remain intact for provenance. This package supersedes their conflicting build instructions without automatically changing prototype screens or the accepted wording of any question.

CTM is one church tribunal application, with one PostgreSQL database, one signed-in entry point and role-routed applicant/council workspaces. It must support a functional ten-user demonstration on a Linux CTM VM. Deployment is one Compose package containing separate app, worker and supporting service containers, with durable private volumes. Initial address: https://ctm.lighthouseway.org. Future Azure or private-server/VPN relocation remains possible. It is not a second marriage-management application; a later ecosystem can reference stable person/marriage identifiers without making CTM identifiers global identity keys.

## Resolved precedence corrections

| Earlier statement | Current build rule |
|---|---|
| Local email/password and recovery | No CTM passwords. Microsoft organizational sign-in for authorized council; Google/Apple for applicants. Providers handle recovery. |
| Admin/secretary restricted entirely to system tasks | Default functional case-operation authority restored; keep explicit author-only, signature, president and decree boundaries. |
| Secretary always gets routine assigned-case alerts | Only current case manager receives routine activity notifications once assigned. Intake/finance/security administration keeps its separate routing. |
| Secretary can add council members | Only an existing admin creates council membership. No public enrollment/request workflow. |
| Certificate number provides an alternative automatic marriage match | Automatic linking uses exact marriage date and both exact DOBs; other/ambiguous cases go to review. Certificate conflict does not defeat an exact three-date match. |
| Replacement/clerical correction decree workflow | Removed. Preserve existing documents and normal appeal decrees; do not build replacement/voiding orchestration. |
| Attachment name includes applicant identifier | Latest convention has case number, document code and upload date/time HHMM, without applicant ID. Ownership is stored separately. |
| All report records always hidden from applicant | Council reports remain private. Applicant may read only their own submitted request answers/response, not internal observations, transcript or other reports. |
| 78-question bank or all prompts combined into every question | Accepted current bank has 59 primary questions, with separately adopted conditional guidance. Do not resurrect removed EVD blocks or rewrite main wording. |
| Draft form and report-template updates behave identically | Applicant application drafts migrate with preserved answers; unsent intake/report drafts change only on explicit refresh. Sent questions are frozen. |
| Device dialer/Asterisk | Manual call records only. No dialer or call recording in current scope. |
| Deferred communications always sent at fixed 17:00 | Exact action is Send after council session; use selected session close event. No invented daily/next-day deadline. |

## Domain hierarchy

```text
Tribunal
  Accounts / provider identities / staff memberships and roles
  People / CTM applicant identities / historical aliases
  Shared versioned configuration and bilingual question/template library
  Cases
    Case identifiers and participating parties (including absent/unregistered spouse context)
    Independent applicant applications, answer revisions and submission manifests
    Fees/payments, completeness reviews and returns
    Assignment history and council-session agenda links
    Proceedings: initial, then new appeal proceedings
      Reports / requests / follow-ups / answers / originals / recordings / reviewed text
      Professional Assessments / signed release / protected original and local OCR
      Findings / notes / contextual evidence and documents
      Case hearings / attendance / testimony appointments
      Decision versions / votes / presidential approvals
      Decree / stored signed PDF / entitlement / explicit recipient release
    Independent appeals / additions / fee / hearing result
    Private communications / channel deliveries / manual call log
    Case audit
  System audit / integration settings / translation / recovery manifests
```

Use ordinary relational state plus immutable revisions and audit events. This is a modular Django monolith, not a microservices or full event-sourcing requirement. Each module owns its mutations; database transactions coordinate shared invariants. The transactional outbox drives durable background work.

## Identity, login and privacy

Use opaque UUIDs for internal relationships. A user-facing case/applicant/decree reference is never a password, token, storage path or authorization decision. Provider identities are keyed by validated issuer and stable subject, with Microsoft tenant restrictions. Only existing admin enrolls council members; admin/secretary can manage previously authorized status/roles within existing scope. President's authority does not automatically grant system administration.

One primary applicant account is retained across all cases. Link multiple providers only with proof of account control. Matching email alone cannot merge accounts or grant staff roles. New email must be verified before activation; preserve previous contact history. Apple private-relay email cannot be treated as equal to a staff-entered different address. Suspensions revoke CTM access and notify applicant; history remains. No application inactivity logout is added, but provider validity, explicit revocation, secure session renewal and suspension checks still apply.

Applicants never see the other party's answers, files, medical material, private messages or corrections. Council reads all formally submitted cases, including closed ones; applicant drafts remain private. All read surfaces enforce ownership: direct URLs, downloads, previews, media ranges, OCR, search snippets/facets/counts and linked context. Staff working on a historical entry has its separate staging workspace, not access to an applicant's private draft by default.

Staff adds a second party using first/last name and email. Record a pending association; do not create an authenticated applicant account on their behalf. Matching registered verified email activates the link automatically. Otherwise wait for provider registration and verification. Registration emails are staff-initiated. No separate Accept Invitation action. Admin/secretary may correct/cancel pending associations with history. Linking/responding alone incurs no fee; filing an independent petition does.

## Case and marriage invariants

Each applicant may have many lifetime cases, but at most one open case. Starting another new-case draft is blocked while they have an open case; allow the other spouse's independent filing into the same existing case. One unfinished new-case draft per applicant. A pending appeal is not an open case. Enforce these invariants under canonical-person locks, including historical cases and account consolidation, not just client validation.

Match independent filings using exact marriage date and the unordered pair of both spouses' known exact DOBs. Preserve role mapping independently. Exact names/church/location spelling is not required; certificate numbers are evidence for review, not an additional automatic route. Multiple candidates or ambiguous person mapping require admin/secretary review before activating access. Date equality does not authorize person merging. Later corrections do not automatically relink. Retain first-created case number and aliases when correcting duplicate case associations.

New case reference is `YYYYMMDD-##`, Los Angeles case-creation date, daily 01–99. Allocate atomically on finalization after matching; do not consume a new case number for second-party filings into the same case. Legacy references remain verbatim; source namespace distinguishes unresolved historical collisions.

CTM applicant reference is frozen upon case assignment/linkage: `20261020-01-JS19850314M`. Before issuance, initials+DOB+M/F temporary label stays internal and is not guaranteed unique. Identity UUID remains stable; DOB/name corrections do not regenerate issued reference. Historical IDs are preserved; missing historical details do not require fabricated IDs. No DOB reference in storage keys, logs or external notification subject lines.

## Initial application

1. Show USD250 fee, nonrefundability and required documents before beginning.
2. Applicant creates/verifies provider account. Resolve existing draft/open-case/linkage state.
3. Complete a sectioned application with checklist and Unknown only on approved fields. English first/last names are required for initials. Each party's facts remain independently attributed.
4. Upload in the correct question/category context. Required marriage certificate/CMC, finalized civil divorce decree, applicant photo; spouse photo if available. Petition statement may be typed or PDF/Word. Every reported restraining order requires its own copy, court name, case number and status without Unknown. No baptism certificate requirement.
5. Save private drafts before paying. Expire after180days without applicant activity; warn seven days beforehand in portal/email. System migration does not reset activity. Submitted records never become expirable drafts.
6. Full answer/file review, versioned declaration/signature, then final payment. Admin/secretary waiver handled outside application; historical entry is fee-exempt. Pause payment/submission for exact duplicate-person review holds. No waiver-request UI.
7. Freeze candidate revision, attestation and exact file manifest. Verify actual successful provider payment/waiver; finalize idempotently. Browser return URL is not payment proof. Recover paid-but-interrupted finalization without another charge.
8. Submission enters admin/secretary completeness queue. Accept, or Reject with mandatory correction textarea. Return keeps same case, fee and original signature; preserve corrections/resubmissions without charging/re-signing.
9. First accepted filing may go to assignment agenda even while second filing is incomplete/returned. No other council access to never-submitted drafts.

Use prototype-to-data mapping and accepted application wording in the reference review; do not copy Catholic requirements or rejected proposals. Collect multiple children (gender and lives-with with approved Unknown), prior applications (date/council or diocese/outcome), prior marriages (spouse and ecclesiastical marriage permit) and restraining orders. Spouse parish/Father of Confession, immigration and residence country support Unknown. No spouse lives-with requirement or town-of-birth addition. Add accepted blood-relationship question. Original `AF` review dispositions remain source evidence for exact labels; do not invent replacements from paraphrases here.

Six selectable grounds: Infidelity; Desertion / abandonment; Abuse; Leaving or changing the faith; Addiction; Misrepresentation / concealment prior marriage. Multiple allowed; no Imprisonment. A submitted statement/evidence is an assertion, not a finding. Council can record its finding without overwriting either party.

Applicant corrections while open preserve original/every field revision, actual editor and server time. No reason or re-sign needed. Authorized staff corrections preserve on-behalf subject and actual actor and send no routine change notifications. Applicant sees own answer history; council sees all relevant submitted histories. UI history indicator/modal follows documented Plenix components. Profile updates do not silently rewrite a signed submission; explicit correction is the conservative data-preserving implementation default.

## Council sessions and case hearings

Admin/secretary creates dated council sessions and prepares agenda. `CSYYYYMMDD` is the hidden display reference; friendly label `Council Session YYYY-MM-DD`. One per calendar date. Part1: accepted new cases, president assigns a member, admin/secretary records. Part2: ongoing case hearings presented only by the assigned member. All council can still read all cases. President authorizes reassignment; admin/secretary records, preserves both actors/time and notifies outgoing/incoming members and applicants privately.

Assigned member may request agenda placement for own cases. Closing a session carries time-exhausted unpresented cases to the next already-dated session; if none, leave awaiting manual placement. Deliberate deferral or absent assigned presenter always awaits manual placement. Do not auto-place merely on creating a future date. Planned rescheduling creates the new session, moves attached cases and affected testimony invitations, removes cancelled session row, and retains case-level transfer/audit snapshots. Completed session/hearing history is never deleted through this rule.

Take default council attendance at session start and confirm actual presence per hearing. Applicants attend only their separately scheduled testimony portion, never deliberation. Two applicants may testify in same session at separate times. Invitation includes private date/time/location or remote instructions; applicant Confirm/Reject only, optional rejection explanation; no self-reschedule. Reschedule/cancel notifies affected applicant, requests fresh response on new appointment version. One-day reminder. Rejection does not remove internal hearing. Admin/secretary manages testimony audio; browser recording or upload, whole event, original retained.

Hearing title: `Case Hearing of [first last] vs. [first last] on Council Session [friendly date]`. No separate presentation workflow. Admin/secretary/assigned member records rich-text internal recommendations and separate applicant update; default pending message records date. Single Send action, no presentation draft/finalize workflow. Preserve sent communication; later recommendation revisions are silent and do not rewrite/resend it.

## Reports, intake and question bank

Assigned case manager priest prepares questions using Topic groups → reusable Question categories → Questions. By-group/by-category are alternate views of one selection, not duplicate records. Current authoritative wording is `../CTM-current-question-bank.md` and `../reference-study/interview-current-question-bank.json`; accepted contextual companion is `../CTM-context-sensitive-investigative-questions.md` and adopted prompt JSON. Preserve all59 active references and exact wording. Foundation questions remain selected; administrative identification is separate. Conditional prompts are optional and not universally inserted. No removed standalone For each accusation/EVD block or completed wording review history UI.

Shared bilingual definitions/version publishing belong to admin/secretary. Personal reusable templates belong to manager; submit for shared publication into a separate shared version without converting personal ownership. Retire without erasing history. Never place applicant answers/private facts in reusable templates. Unsent intake snapshots refresh explicitly; sent question wording/order freezes. Select only questions for applicant requests, not all interviewer guidance.

Manager may conduct intake/interview himself or send private applicant request. Applicants separately; no general witness module. Report metadata includes subject, interviewer/actual recorder, method, date, location/duration where known; displayed date is sufficient for report title. Narrative and typed answers are separate from transcript and internal observations. Exact submitted application facts/evidence can be linked to confirmation context without editing source or exposing another applicant's private material.

External priest report is a distinct freeform request explicitly identifying marriage/subject. Request exists before files. Email scoped direct link, expires30days; no CTM/provider account or extra verification. Save/resume allowed while valid. Reissuing disables old link and preserves draft. Submitted response locks link/recipient edits; all authorized council can see submitted original, subject to AI-text review boundary. Alternatively print blank PDF, upload completed paper, local OCR with original accessible; upload automatically records paper method/completion and disables online response. Wrong-upload exception removes wrong payload/derivatives, retaining correction audit, not a universal evidence-delete feature.

Each follow-up is a new report with identifier/date/status, parent-report and case links, shown individually in Reports. Multiple reports per same date allowed, optional user-defined identifier. External priest title `Report by Fr. [name] — [completion date]`. Requests separate from completed newest-first reports. Search within reports. Applicant reads own submitted response only; no council-only internal report text or recordings by inferred access.

All council may view case report drafts/narrative/originals within source scope. Only original council author revises narrative while proceeding open and still authorized; new assignee creates follow-ups rather than rewriting predecessor. Admin/secretary may enter/upload on behalf with actual authorship retained; their default authority does not become permission to rewrite another author's narrative. Closed report/proceeding remains locked after appeal reopening.

## Audio, transcription and translation

Record within Reports UI on desktop/mobile web, optionally for ordinary interviews, with informed-about-recording capture, pause/resume and recoverable chunks. It is one whole-report recording, not per question. Finalize/submit before queueing transcription; no live-transcription prerequisite. Testimony/interview capture/upload has no fixed duration/file cap; provider chunk limits handled server-side. Ordinary audio attachment cap remains100MB.

Retain original recording, original AI transcript, timestamped speaker-labelled segments, full English and Arabic versions (including mixed speech original), original output and every correction. Typed interview answers remain separate; no automatic AI mapping into questions or findings. Approved server/API processing interchangeable through adapters; provider failures leave original audio usable/retryable. Report manager reviews generated report text before wider council visibility; testimony text review/correction by admin/secretary. All applicants denied testimony/interview audio/text. External source narrative remains source-authored; council edits must be visibly separate.

All translations use the exact user master prompt `../CTM-translation-master-prompt.txt`, versioned/editable in settings. Primary/fallback AI priority, with future on-host non-AI engine adapter. Server-only secret references; provider fallback cannot bypass content restrictions. Formal/common Egyptian-context Arabic UI, English/Arabic equivalent labels/questions/help/errors/system notices. Publish reviewed versioned translation bundles; no runtime AI request needed to draw a page. Original case answers remain original language; translations are attributed derivatives.

## Professional Assessments

Separate medical/psychological report requests. Manager (and default authorized admin/secretary operations under latest authority) can request own-subject assessment. Recommended doctors optional; another provider permitted. No doctor portal or clinical automation. Signed scoped release and report are distinct required submission artifacts; staff cannot sign for subject. Without release, restrict report/derived text to pending-authorization intake; council can see missing-release status without contents. Apply scope to retrieval, OCR/search, context links and disclosure events.

Applicant submits own report/release privately, council sees only within signed recipient/purpose scope, source and revisions retained. New clinical material/follow-up gets linked new request/report. No fee/deadline. Closure/cancellation blocks submissions; reopening creates new requests. Only manager routine alerts. Local server OCR/extraction only; never send medical documents/extracted text to external AI, including failover. Institution must supply final signed-release text before live use; schema is not its approval.

## Decisions, decrees and withdrawal

Admin/secretary/assigned member enters type and grounds/reason, affected parties and conditions. Use exact prototype type catalog in `prototype-decision-types.json`; don't infer Catholic legal doctrine or demo-person facts. Display what is voted on first. Full council roster always visible irrespective of attendance. Self vote or admin/secretary entry on behalf, individual votes/tally visible council-only. Keep simple Approve/Deny/Abstain; no quorum gate. President approves directly or admin/secretary records on behalf, with or without votes. Changed type/grounds needs fresh approval and fresh votes if taken; preserve earlier record.

Only admin/secretary manages decree preparation/templates/issuance/release; case manager never does. President Bishop/Metropolitan signs digitally or paper signed scan. Exact signed PDF must be stored before issuing. English, Arabic or one bilingual certificate. ID `DCR-[case]`, then appeal decrees `-A1`, `-A2` by decree-producing appeal proceeding, not each appellant. Signature capture method is recorded; cryptographic signature product is not selected.

Issue atomically closes case/proceeding and queues private notices. Entitled parties get decree-availability notice; other party official decision notice; certificate itself remains hidden until admin/secretary explicitly releases. Released recipient can view/download PDF with ID/language/release date, notification on release. Withdraw mistaken portal access with history. Nullity granted entitles both subject to explicit release; conditional decisions identify parties/conditions and can close before future conditions fulfilled. No replacement-decree workflow or implicit prior-decree voiding. Appeal does not change existing certificate access unless explicit authorized access action.

Petition Denied closes after approved decision, official notice, no decree PDF. Applicant withdraws own petition without reason/approval, fee retained. With one participating filer, closes; with two, only both withdrawals or final decision closes. Admin may withdraw for all. Reconciliation is withdrawal. Notify current assigned member, not other applicant. No participant deletion or historical withdrawal erasure.

## Appeals

Either applicant can draft/submit own appeal: reason/statement, new information/evidence/attachments, declaration and USD250 fee/authorized waiver. Same private180day/7day draft policy. One draft/pending per person/case, independent for each party. Can file while sibling appeal reopened same case; not a second case. A later appeal after decline/withdrawal allowed with fresh fee; pending applicant adds supplements instead. Supplements append immutable extra information, no overwrite or staff-on-behalf supplements.

Submission goes to council agenda queue without reopening or changing decree/access. Original assigned member presents unless president reassigns. Two appeals share one case hearing item with separate Accept/Decline result for each. Admin/secretary/assigned member records result; no invented presidential intake-approval gate. Decline auto official notice with optional explanation to appealing person. Accept creates one new appeal proceeding or joins current same-case appeal proceeding, reacquires open-case claims for parties and notifies both privately. Different open case blocks reopening without deleting appeal. Sibling decline never recloses accepted appeal proceeding.

Accepted case follows regular reports/hearings/decision/decree rules with original proceeding locked. Owner may withdraw pending appeal before result without approval/refund; notify only manager. Pending additions portal alert immediately; email after10quiet minutes.

## Files, search, payments and communications

Private file originals live in persistent VM storage behind authenticated Django access, not PostgreSQL blobs/public CDN. Metadata, transcripts, answers/audit in PostgreSQL. Meilisearch is a derived private index, not source of truth. Context links retain exact versions, owner, uploader and description for report response attachments. No fixed attachment count. PDF/image/Word25MB; video500MB; ordinary audio100MB. Content/type/safety validation is automatic, not a manual council acceptance gate. Successful safe uploads available immediately; current safe version by default, council-only prior version history. Preserve all submitted versions except explicit mistaken report-upload exception.

Presented filename `[case]-[document code]-[YYYYMMDD]-[HHMM].[extension]`, LA upload date/time; for same-minute collision append short discriminator only when needed. UUID object keys prevent physical collisions regardless of filename. Draft filenames stay private until case association. Category/code changes update presented submitted names with history, never signed manifests/original bytes. MC/CMC and CDD retain their required meanings; DEC attachment code is distinct from DCR decree identifier. Approved category edits remain admin/secretary. Ordinary evidence is not automatically transcribed because it is audio/video.

Search PDFs/Word, scanned images/PDF via server OCR, English/Arabic, open/closed cases and reports. Latest versions default, council optional history. Partition/dedupe only as needed, no RAG/AI evidence summary requirement. Reauthorize every hit/snippet/facet/count; never expose raw search API/key to applicants or trust browser filters. Medical and unreleased AI-text scopes apply before returning any content.

Payments stored as obligations/attempts/events/allocations, receipts and duplicate refunds. No card data. USD250 per actual filing party, no fee for simple account link. Nonrefundable after submission except accidental duplicate, admin/secretary authorize. Chargeback/reversal alerts admin/secretary immediately; don't remove submission or silently reopen. Historical entry records exemption, not fake successful transaction.

Native CTM private messaging using existing account authorization; no Zulip or internal council chat. Messages permanent, correction new message. Both-recipient send creates separate private copies. New uploads stored in correct document/request location; message stores reference, link never grants disclosure. Email replies enter correct party history; attachments rejected/returned with portal notice and transient-only payload. Do not accept evidence via email.

Portal message is immediate. Exact choices `Send Immediately` / `Send after council session` apply email delivery. Engineering default: deferred send binds explicit current/selected dated session and dispatches on session close; when no session selected, require selection or immediate send rather than invent a5pm/next-day schedule. This is documented default, not a new business deadline. Manual calls record actual date/time/person/outcome/notes separately from automatic entry actor/time. No dialer/phone recorder.

## Technology and deployment contract

Selected: Django, PostgreSQL, React with pinned Plenix CDN0.58.0, Meilisearch, Docker Engine/Compose; Plenix document pipeline PaddleOCR, OCRmyPDF/Tesseract, Docling and complementary Unstructured. Route by file purpose rather than running all tools redundantly. Reuse existing service only after version/isolation/availability inspection; no assumption any container is already ready.

Implementation defaults to validate/pin before image lock: django-allauth in provider-only mode; Celery+Redis durable jobs with PostgreSQL outbox/reconciliation; Uppy/Tus resumable upload and browser audio capture adapter; PDF.js, PhotoSwipe, Video.js/native audio behind Plenix UI adapters; FFmpeg worker; WeasyPrint bilingual PDF; ClamAV; existing reverse proxy or Caddy; existing backup or Restic. These defaults resolve the design plan without falsely claiming installed/tested compatibility. No Redis-only authoritative queue/ledger; outbox supports redispatch.

Django same-origin backend and React UI, with provider secrets in server environment/secret mounts. Pin compatible supported versions during packaging; don't add Rails/Frappe or Node runtime merely because frontend uses React. One VM, multiple containers, private networks, app HTTPS only externally. No public PostgreSQL/Meilisearch/broker ports. Encrypted server disk/backups, least-privilege service accounts, restore verification and operational secret handling are deployment requirements.

Only documented Plenix components/patterns and `plx-` classes; token-only values, no inline styles/!important/raw colors/numeric font sizes; pinned CDN references, never copied distribution. Required missing component is a real delivery dependency, not permission to invent one. Arabic patch isolated/swappable. Legacy prototype is workflow inventory, not CSS/layout to copy. Exact CDN contract is `../CTM-Plenix-CDN-contract.md`.

Use [the permission matrix](permissions.md), [transactions/acceptance](transactions-and-acceptance.md), [delivery dependencies](delivery-dependencies.md) and field dictionary together. Structural SQL is deliberately not represented as a secured app. Domain-model design review:8/10; remaining points require executable migrations, transaction/RLS tests and validated real-world integrations, not more speculative workflows.
