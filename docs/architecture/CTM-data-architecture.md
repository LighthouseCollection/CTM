# CTM data hierarchy and database architecture

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Reconciled 2026-10-20 against all confirmed decisions. Documentation only: no application code, UI, database, migration, VM, payment/email account or infrastructure change has been built or provisioned. Confirmed case, appeal and decree workflows and returned questionnaire refinements are part of the linked supplements.

## Document authority

1. [Confirmed business decisions](CTM-confirmed-decisions.md) states the agreed requirements.
2. [Reconciled database tables](CTM-database-tables.md) translates them into typed relationships, immutable history and integrity gates.
3. [Reconciled permissions](CTM-permissions.md) defines ownership, role, assignment and lifecycle access.
4. [Questionnaire/council reconciliation](questionnaire-council-reconciliation.md) maps current applicant questions to council fields and separates proposed/deferred items.
5. [Reconciliation report](CTM-reconciliation-report.md) records changes, traceability and documentation verification.

The earlier 196 KB working architecture with accumulated proposals/overrides is preserved in [the archive](archive/CTM-data-architecture-pre-reconciliation-2026-10-20.md). It is historical context, not a current schema or permissions specification. The prototype inventory is also evidence rather than approved production policy.

## 1. Product and deployment boundary

One server application serves one council/tribunal through two portals and one authoritative PostgreSQL database. Applicant privacy is enforced within the shared database, not by duplicating public/private records. All authorized council members read submitted cases; writing is restricted by the explicit permission matrix. Plenix CDN will supply presentation assets later; it receives no case documents or OCR text.

Initial hosting: dedicated Linux CTM VM on the user's server, one disk with separate application, database and private-file directories. No Supabase/Neon. Linux distribution, VM size, backup destination/schedule and provider accounts are deferred. Standard PostgreSQL and a replaceable private-storage interface preserve portability to another VM, Azure or AWS. Backups must preserve DB, files, keys and number allocations together; no backup target was selected.

## 2. Data hierarchy

- Stable person and canonical identity links: independent of email, case number and historical applicant labels.
- Account and sign-in identities: one primary applicant account across cases, linked Google/Apple/password methods; council sessions password-only.
- Organization and staff: one tribunal, directories, active/historical memberships and explicit administrative permissions.
- Marriage context: the union under review, separate from current account/contact facts and future marriage-preparation workflows.
- Shared case: original/new case number, one current assigned member, open/closed lifecycle and multiple attributed participants. An absent spouse does not require an account or second application.
- Applicant application: versioned questionnaire, self/spouse assertions, repeating children/priests/prior applications/orders, grounds, petition statement and private uploads.
- Submission and corrections: exact signed original schema/declaration/file manifest, immutable answer changes and current committed view.
- Council record: independent attributed findings and author-owned internal notes, never replacements for applicant assertions.
- Files and derivatives: logical document, immutable byte versions, editable presented-name history, private local extraction/OCR/search data and access events.
- Filing finance: per-filer obligation, payment/waiver/exemption, provider/refund/reversal events and idempotent finalization recovery.
- Communication and jobs: sent emails, safely routed replies, rejected-attachment return metadata, per-recipient notices, digest batches and outbox.
- Audit: case-safe history readable by all council; system/security audit readable only by admin/secretary.
- Deferred workflow records: appeal, intake/investigation, sessions/hearings, decisions/decrees and stage-specific effects. Only relationships and confirmed invariants are reserved now.

## 3. Source-of-truth rules

The same stable field definition and authoritative applicant answer revision feeds applicant and council views. Fixed business fields have typed storage; extension questions use validated typed answers. Never maintain independently editable applicant and council copies.

A source applicant's spouse statement is not the other applicant's account/profile. Conflicting statements remain separately attributed. Council findings link exact source revisions/files and remain private; they do not overwrite either statement. New cases start blank even though the applicant account persists.

Submission freezes the original questionnaire version, declaration language/text and signature, answer revision and exact file-version manifest. Current corrections form later immutable revisions, with no reason or new signature required. Published configuration creates new versions and updates unfinished drafts without erasing answers. It does not rewrite submitted content.

Logical file ownership and opaque immutable storage keys are independent of current filename. Admin/secretary category-code changes update current filenames and retain all former names; original bytes/checksums/submission manifests remain unchanged.

## 4. Critical identity and consistency rules

- Never two open cases per canonical applicant, including open historical cases; no administrative override.
- An open case also blocks starting another new-case draft; otherwise only one unfinished new-case draft per person.
- Only one current assigned member per case; all authorized council members still read the case.
- New case numbers use creation date in America/Los_Angeles and daily 01–99. Historical numbers/IDs remain unchanged. Allocate under transaction/idempotency protection.
- Assigned CTM references remain unchanged after name/DOB/gender corrections. English first/last initials are required for newly generated IDs.
- Exact names/DOB/address matching triggers admin/secretary review; hold payment/submission while owner can save existing draft. Similarity is not automatic proof or a merge.
- Verified consolidation preserves original records/actors and disables the duplicate login. Identity reconciliation may not create a second open case or destroy either submission history.

Claims/unique indexes plus guarded transactions must work together: a partial index cannot by itself enforce a condition on another table's lifecycle. See the table dictionary for cross-case/party FKs, current-version pointers and finalization gates.

## 5. Lifecycle, privacy and retention

Verified account/email precede application initiation. Applicant drafts are private; only minimum identity/fee metadata is exposed for explicitly authorized administration. Technical workers do not make a draft council-visible.

Applicants may delete never-submitted drafts. Drafts expire after 180 inactive days, with an email warning seven days beforehand. Submission/payment-recovery locking prevents cleanup races. Once submitted, all submitted case data and histories are retained permanently; no case purge or user-facing export exists.

While open, applicants can see/correct their own answers and view their own answer history/latest attachments. They cannot read the other party's data or their own older attachment versions. Authorized council members can read source histories. Staff corrections and uploads have actual staff attribution and preserve the subject owner.

Once closed, applicants can access only the specifically authorized decree. Original findings/notes and substantive material are locked for all staff. Operational events can append without changing substantive contents. Appeal petitions/evidence are separate case-linked submissions, not edits to the locked original. An appeal uses the original case number, enters council review, and does not itself reopen a case.

## 6. Files, processing and search

Required petition uploads: MC, CMC, CDD, applicant photo; a petition statement PDF/DOCX if not typed; and a copy per reported restraining order. Spouse photo only if available. Baptism certificates excluded. Historical entry has the approved missing-data/fee exception.

Limits: PDF/image/DOCX 25 MB; ordinary audio 100 MB; video 500 MB. Testimony capture/upload has the later no-fixed-cap exception. No fixed attachment-count cap or approved total-byte quota. Uploads are automatically current after technical security validation; no manual council acceptance gate. Preserve all submitted versions and log authorized views/downloads.

Filename example: `20261020-01-JS19850314M-CDD-20261022-1430.pdf`; case-wide `20261020-01-DEC-20261022-1430.pdf`. Dates/times use LA; display-name collisions cannot overwrite files. No sequential attachment filename component remains.

PDF/DOCX extraction, scanned-PDF/image OCR and English/Arabic search run entirely locally. Source bytes/text remain unchanged. Search covers submitted open and closed cases, latest versions by default with a council option for older versions. Testimony audio now has approved AI-API transcription/translation; source-language and full English/Arabic versions are council-only. PDF/image OCR and document text extraction remain local-only; no general video transcription is approved. Permissions also cover OCR snippets, counts, previews, copied URLs and stream requests.

## 7. Finance and communications

Every petition filer pays USD 250; two filing spouses each pay; a responding-only participant does not. Each appeal costs USD 250. Inform users before starting; final verified payment or authorized waiver completes a frozen filing. Handle technical provider/DB failure without a second charge or ordinary paid-but-unsubmitted workflow.

Admin/secretary record externally arranged waivers and accidental-duplicate refunds. All council members read case financial business records. Submitted fees are non-refundable except duplicates. Provider chargebacks/reversals append to the ledger, alert admin/secretary immediately and never erase the filing. Stripe is preferred but not finally onboarded.

Assigned member/admin/secretary manually send case emails with actual sender/time. Sent content and delivery history remain. Replies are automatically preserved and safely routed to case/applicant; ambiguous messages stay restricted. Email is not formal submission. Attachments received by email are returned with portal instructions and do not enter case evidence/OCR/search. Permanent rejection metadata is separate from restricted temporary return payload.

Applicant-originated committed answer/file changes: assigned member + secretary, portal immediate, email after ten minutes without further changes. Staff corrections: no notifications. Duplicate holds and chargeback/reversal alerts: admin + secretary immediate. Account suspension/reactivation: applicant email. All histories remain regardless of notification suppression.

## 8. Confirmed workflow architecture and remaining boundaries

The [workflow database supplement](CTM-workflow-database.md) and [case/session decisions](CTM-case-session-workflow.md) define approved review, assignment, sessions, testimony, voting/presidential approval, decree issuance/release, withdrawal, correspondence and appeals. They are part of this architecture, not deferred placeholders. Existing generic case tables gain proceeding relationships; appeal applications, reopened proceedings and decrees remain distinct.

An appeal uses the regular application submission/payment/attestation process with its own simple statement/new-information/evidence form. Submission queues it without reopening. Acceptance reopens the same case into a new appeal section, preserving original proceedings read-only; separate applicant appeals share a hearing with separate results. Decree issuance closes the case; signed certificate exposure requires explicit version-specific release. Post-closure messaging and controlled certificate administration are permitted exceptions, not general edit access.

Still unresolved: responding-party onboarding, historical finalization, exact conditional decree entitlements and a small number of edge cases listed in the supplement. Deployment/provider and physical SQL/RLS choices remain later work. No application, migrations or deployment have been built.
## 9. Verification and readiness

This pass checks documentary traceability, table/permission consistency, stale requirement removal and unchanged prototype sources. It does not test real RLS, authentication, payment webhooks, concurrency, storage, OCR accuracy or deployment security. Those require implementation and an actual test database later.

Workflow policies are reconciled with the supplementary table/permission design. Production readiness still requires resolution of the named boundaries and a verified physical schema/RLS/concurrency design; documentary review is not security certification.

## 10. Returned decision questionnaire

[All 39 questionnaire responses](CTM-questionnaire-decisions-2026-10-20.md) are reconciled, with clarifications overriding earlier proposals. They supplement the workflow tables, permissions and confirmed register. Open-source testimony recording and PDF scanning are requirements, not selected components. No fixed testimony recording cap; generated transcripts need staff review before other council access. Remaining focused clarifications concern the certificate-based matching minimum, decree voiding timing and case-manager terminology; detailed certificate handover and applicant-portal design remain deferred.



## 11. Confirmed portal/interview scope

[Reconciled portal/interview decisions](CTM-portal-interview-decisions.md) are part of this architecture. Separate guided investigation interviews from council testimony; preserve source, versions, authorship and review boundaries. Applicant portal is projections/actions over authoritative application/case/appeal/correspondence records with one current-workflow view, not a duplicate database or a new ban on independent same-case appeals. Contextual document links are required. Draft standardized English/Arabic interview wording is available for review only; no application UI/database has been built. P13 is settled as automatic receipt/New flag with no staff completion step. P30 and C34 need explanation, not silent assumption.


## Latest reference-review reconciliation

Accepted reference-study responses are reconciled in CTM-reference-review-decisions.md. Current interview template is category-based; CTM-interview-category-bank.md and its planner show selection and report structure. Requested priest reports have explicit subject identity and a scoped free-form write/record link, with retained transcription/translation history. No new Catholic procedure, ground, priest membership or AI-generated questionnaire answer is inferred. Application source remains unchanged; detailed implementation comes later.


## Investigation hierarchy, source context and evaluation releases

Working grouped title: Case Investigation and Factual Discovery. CTM-investigation-model.md describes reusable question families across petition templates, alternate council views, exact submitted-answer confirmation/evidence integrated into the questionnaire and report, plus conditional medical/psychiatric records and signed release disclosure. The updated planner is a planning artifact; category/question research prompts provide optional future research, not new published questions or CTM implementation.



## Current medical / psychological workflow authority — 2026-10-20

The user delegated completion of this section using prior CTM choices. [Medical and psychological report workflow](CTM-medical-psychological-report-workflow.md) is authoritative for requests, optional council-recommended doctors, alternative providers, signed release capture, private applicant uploads, council access within authorization, local OCR/search, case-manager-only routine notifications, revisions/follow-ups, reassignment and closure. It specifies architecture only; no production implementation exists.

This supersedes earlier conflicting admin/secretary on-behalf case-operation permissions for this section. Those roles support system-level/cross-program administration; they do not gain operational write access to assigned-case evaluation requests by role alone. Case-manager responsibility does not remove council case-read access or the signed report-disclosure scope. The exact institution-approved release text remains a document-content dependency. No external doctor portal, automatic clinical judgment or external medical-document AI processing is introduced.


## Confirmed template management and closed reports — 2026-10-20

[Template-management workflow](CTM-template-management-workflow.md) is the current authority for system-level shared-library publishing by admin/secretary; case-manager personal reusable templates; submission of personal templates for shared publication while keeping the personal original; retirement without loss of history; preserved unsent drafts with explicit refresh; and immutable sent-question snapshots.

Reports cannot be edited after case closure, including clerical corrections. Earlier report-author editing permissions apply only while the relevant case/proceeding is open. Reopening preserves the prior closed reports; new material follows the authorized appeal proceeding. These are documentation decisions, not implemented database permissions.


## Settings and translation authority — 2026-10-20

[Settings and translation architecture](CTM-settings-translation-architecture.md) records inspected prototype system/account settings and the newly requested translation configuration: exact editable/versioned Coptic Orthodox master prompt, primary/fallback AI slots, protected server-side API keys, and a future non-AI on-host engine mode. All translation outputs retain source/version provenance. Local OCR and medical-content restrictions override any provider fallback; prompt OCR instructions do not authorize external document uploads. Account settings cannot change system integrations. Shared question translations are reviewed/versioned before publishing. This specifies architecture only; no live integration or translated question bank was built.


Arabic interface localization is confirmed for both portals. See the Arabic user interface section in [Settings and translation architecture](CTM-settings-translation-architecture.md). Versioned reviewed UI resources use the same translation service/master prompt, support RTL and separate account UI-language preference, and never change authorization or automatically translate original case answers.


## Temporary Arabic styling patch — 2026-10-20

See [Arabic styling bridge](CTM-arabic-styling-bridge.md). The separate Arabic-scoped CSS is now linked in 49 prototype pages and can be replaced independently when the Plenix Arabic CDN exists. No locale controller or translated resources have been installed. All Arabic UI text follows familiar Egyptian wording/formal-common context as specified by the user; no blanket formal-only default.


## Required package capability: council Microsoft sign-in — 2026-10-20

User confirmed inclusion of Microsoft sign-in in the delivery package. [Council Microsoft sign-in](CTM-microsoft-council-sign-in.md) supersedes the earlier council email/password-only restriction by adding organizational Microsoft authentication. Admin preauthorizes the CTM member and role; a Microsoft/lacopts email alone never grants access. Provider configuration belongs to admin system settings, identity links use validated tenant/object identity, and applicant/external-priest authentication remains separate. This is specified, not deployed; actual tenant/app registration, credentials and callback configuration are required before a live connection.


## Consolidated technology register — 2026-10-20

[Technology, open-source tools and deployment plan](CTM-technology-and-open-source-stack.md) is the current consolidated reference for Django/Rails/Frappe comparison, performance considerations, the Plenix-aligned processing/search stack, browser recorder/viewers, private storage responsibilities, container/service reuse and unresolved technical choices. It distinguishes agreed requirements, reuse baseline, candidates and external services. No application framework or pinned tool version is selected by documenting this register. No installation or performance benchmark has been run.


## Hosting clarification — 2026-10-20

Latest user decision: final hosting will be either Azure or a private server at a designated location with VPN access. The choice and network-access details will be discussed later. Do not treat an Azure migration in one week, public internet availability, or a specific VPN product as a committed deployment requirement. The immediate objective is a fully working functional demonstration for approximately 10 users. Use one dedicated Linux CTM VM containing multiple containers managed as one deployment package, with private persistent storage and a tested backup/restore plan. Keep hosting-specific endpoints, secrets, storage paths and provider callbacks configurable so the same application package can be deployed to either destination. Framework selection, VM sizing, distribution and exact software versions remain pending; this hosting clarification does not finalize them.


## Selected Django + Plenix React CDN — 2026-10-20

The user selected Django with Plenix CDN and identified Plenix as React-based. [Django–Plenix integration](CTM-Django-Plenix-integration.md) defines the compatible browser/server roles, same-origin deployment recommendation, protected endpoints and CDN integration verification. Earlier framework comparisons remain decision history; Django versus Rails/Frappe is no longer an open choice. Exact dependency versions, provider configuration and hosting remain deployment details. No actual application was built by recording this selection.


## Pinned Plenix CDN contract — 2026-10-20

[Plenix 0.58.0 contract](CTM-Plenix-CDN-contract.md) is authoritative: load theme-boot, fonts, plenix CSS, matching React/ReactDOM vendor scripts and plenix.js in the user's specified order, using window.Plenix (or the documented ESM alternative with React 18 peer). Use documented Plenix components/patterns, plx- classes and --plx-sys-*/--plx-comp-* tokens only; no inline styles, raw colors, numeric font sizes or !important. Ask for missing components/values. No CDN assets are copied. The old prototype Arabic bridge is not yet compliant production styling; its necessary behavior must be reconciled against documented tokens before use.


## Initial VM deployment address — confirmed 2026-10-20

The user will initially install CTM on their own VM and access it at **https://ctm.lighthouseway.org**. Both applicant and council portals belong to this application origin; exact portal route paths are implementation details. Django sessions, CSRF origin checks, reverse-proxy/HTTPS settings and approved identity-provider callback registrations must use this canonical address. Payment/email callbacks use the same configured public application base URL where applicable. Do not invent a VM IP, DNS record, reverse proxy product or active provider connection from the supplied hostname.

Application availability at this address does not make case data public. Authentication, admin-only council enrollment, applicant isolation and private file/search access remain required. Database, search, processing services and storage management endpoints stay private. Whether network access will also be restricted by VPN must follow the final access decision; browser reachability and external provider webhook reachability must be configured explicitly rather than assumed.

This selects the initial own-VM deployment, while a later Azure/private-server move remains a separate future discussion. No DNS, certificate, VM, deployment or network setting was changed or verified by documenting the URL. All host-specific settings remain configurable for portability.


## Locked council navigation and layout map — 2026-10-20

[Council navigation and layout](CTM-council-navigation-and-layout.md) records the user's locked hierarchy, Communications directly after Case Overview, Appeals beneath Decision, no case list in navigation, and the persistent sidebar avatar/name trigger with a hidden account/system menu subject to documented Plenix support. It distinguishes agreed case-report split view from proposed evidence/document/communication/assessment layouts and optional search/appeal previews. No unverified custom Plenix shell or component has been built.


## In-app communications and call workflow — 2026-10-20

User explicitly requests in-app messaging, email and calling under Communications. [Communications workflow](CTM-communications-workflow.md) supersedes older email-only/no-chat statements and distinguishes reliable device-dial initiation logging from integrated telephony answered/duration/recording events. Asterisk is an optional open-source candidate only; normal tel links cannot record the other party's telephone audio. Search and Appeals split-view previews are now confirmed in the navigation/layout map. No phone system or UI was installed.


## Council Home review — 2026-10-21

[Council Home dashboard](CTM-council-home-dashboard.md) records approved assigned-work/attention/session/request sections and a source-based review of the existing prototype dashboard, including recommended retention of session/submission content and relocation of large analytics to Statistics and Reports. Exact layouts remain subject to the pinned Plenix contract; no production dashboard was built.


## Approved applicant application flow — 2026-10-21

[Applicant application process](CTM-applicant-application-workflow.md) records the user-approved sequence: fee/document information, provider account, eligibility/resume, section-based form and contextual uploads, private saved draft, review/declaration, final payment and submission, confirmation, completeness review/return and council processing. It preserves existing identity/payment/privacy/history rules and uses the strict Plenix contract. This approval concerns the application process; earlier proposed applicant shell navigation and split views are not automatically locked. No production application was built.
