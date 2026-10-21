# CTM reconciled permissions

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Date: 2026-10-20. Documentation design only; these policies have not been installed or tested against a database. Authority: [confirmed decisions](CTM-confirmed-decisions.md). Resource/table definitions: [database dictionary](CTM-database-tables.md). Confirmed workflow authority is defined in section 11 and CTM-workflow-database.md; those provisions supplement the foundational matrices.

## 1. Principals and mandatory gates

- **Applicant owner:** verified, nonsuspended primary account resolved to the canonical person, accessing that person's own application/participation. Google, Apple and password are allowed. A shared case number or being named in another person's answers never grants access.
- **Council member:** active council account and membership, using a council password-authenticated session. Applicant social sign-in does not grant council access. All active authorized council members read submitted cases.
- **Assigned member:** council member who currently holds the case's sole assignment. This is a case-scoped relationship, not a permanent role or exclusive read entitlement.
- **Administrator / Secretary:** active council application roles with the specifically confirmed administrative powers. Hosting/database operator access is not an application role.
- **Services:** narrowly scoped verified job/ingestion actors. They perform technical processing, delivery or cleanup on a committed authorized event. They do not become applicants, impersonate staff, read arbitrary data through the UI or invent business decisions.

Multiple roles combine only within hard ownership/lifecycle restrictions. No grant bypasses one-open-case, draft privacy, permanent retention, author-only note editing or closed substantive locks. A former assignment gives no continuing write authority. A person with both staff and applicant identities must use the proper portal/session context; applicant data responses cannot acquire staff visibility from an ambient role flag.

Neither applicants nor council have automatic inactivity timeouts. Every request still checks current suspension/deactivation/revocation and portal authentication scope. A role edit must affect current authorization, not wait for an old browser token to expire. No mandatory/optional MFA feature is introduced by this design.

## 2. Permission notation

**Own** = same verified canonical person plus checked application/participation ownership. **Read** = authorized read, not update/delete. **Open** = case remains open when the write commits. **Author** = original note author plus current write-eligible role/assignment. **Minimum** = restricted metadata for the named administrative purpose, never general draft answers. **Deferred** = not authorized by this design pending the later workflow; not a blank permission to scaffold from the prototype.

The Member column represents an unassigned council member with no administrative role. The Assigned column adds current case assignment. Administrator and Secretary remain constrained by explicit author/lifecycle gates.

## 3. Applications, drafts and submitted records

| Operation / resource | Applicant owner | Member | Assigned | Administrator | Secretary | Additional gate |
|---|---|---|---|---|---|---|
| Start new-case draft | Own | No | No | No through applicant identity | No through applicant identity | Verified email; no open case; no active new-case draft; staff-on-behalf workflow deferred |
| Read unfinished applicant draft/answers/history | Own | No | No | No | No | Minimum duplicate/waiver metadata exceptions below do not grant answers |
| Save own unfinished draft/upload | Own | No | No | No | No | Existing draft; allowed technical checks; duplicate hold permits saving, not submission |
| Delete own never-submitted draft | Own | No | No | No by role | No by role | Serialize against checkout/submission; retained submissions never deletable |
| Expire eligible draft at 180 days | No direct action | No | No | No manual purge | No manual purge | Scoped cleanup service only; seven-day warning; no submitted/charged-recovery erasure |
| Formal online submission | Own subject to finalization | No | No | Deferred on behalf | Deferred on behalf | Required fields/files, grounds/statement, verified identity/email, claims, no review hold, successful fee/authorized waiver |
| Read own submitted answers while open | Own | Read both parties | Read both parties | Read both parties | Read both parties | Submission committed; current answer projection, not another party's assertions |
| Read original attestation while open | Own original submission | Read | Read | Read | Read | Exact accepted text/signature/schema versions; no later correction falsely re-signed |
| Read own answer history while open | Own | Read | Read | Read | Read | Actor/time and old/new values; safe actor attribution in applicant view |
| Correct applicant answer while open | Own | No | No merely assigned | Yes, on behalf | Yes, on behalf | Actual editor distinct from subject; preserve every version; no reason/no re-sign |
| Read other applicant's answers/history | No | Read | Read | Read | Read | Council only after submission; no application-to-application copying |
| Read applicant application/answers/history after closure | No | Read | Read | Read | Read | Applicant decree-only exception below; council history remains permanent |
| Edit original closed application | No | No | No | No | No | Appeal is separate; administrative role cannot override content lock |
| Delete any submitted application/version | No | No | No | No | No | Permanent retention; account/category changes cannot cascade delete |
| Admin-enter historical case/spouse data | No | No | No by assignment | Yes | Not inferred | Missing-data/fee exemption; actual historical lifecycle; finalization sequence deferred |
| Link verified historical participation/account | No self-association | No | No | Yes | Yes | Verified identity; original IDs/history retained; claims checked; no access expansion |

For response/appeal drafts, data ownership/privacy is the same, but routing, eligible preparation states and review procedures await workflow design. Do not extrapolate the new-case draft ban into denial of participation in the existing shared case; equally, do not create another-case draft as a workaround.

## 4. Findings, notes and case assignment

| Operation | Applicant | Member | Assigned | Administrator | Secretary | Additional gate |
|---|---|---|---|---|---|---|
| Read submitted case overview, both source assertions | Own approved projection only | Read | Read | Read | Read | No private unfinished drafts or unrelated system details |
| Read council findings and finding history | No | Read | Read | Read | Read | Open or closed cases; private projections only |
| Record/revise findings | No | No | Yes, Open | Yes, Open | Yes, Open | Sources pinned to exact revisions; findings never replace applicant answers |
| Read internal notes/history | No | Read | Read | Read | Read | Council only, including closed records |
| Add internal note | No | No | Yes, Open | Yes, Open | Yes, Open | Actual original author/time stored |
| Revise note | No | No merely former author | Author, Open | Author, Open | Author, Open | Even admin/secretary cannot edit another author's note |
| Revise findings/notes after closure | No | No | No | No | No | New substantive material through separate appeal records, not the locked original |
| Delete submitted findings/notes/history | No | No | No | No | No | Permanent case retention |
| View current/prior assignment | Own approved status only | Read | Read | Read | Read | One current assigned member; no invented applicant internal roster access |
| Assign/reassign, decide/close/reopen, approve appeals | No inferred grant | Deferred | Deferred | Deferred | Deferred | Later case workflow; preservation/one-open-case guards still mandatory |

The prototype's Presiding label does not automatically grant unconfirmed override privileges. Presiding users receive general member reads; administrative/writing powers require a confirmed role/assignment. Vote/decree approval authority is not set here.

## 5. Attachments, names, derivatives and search

| Operation | Applicant owner | Member | Assigned | Administrator | Secretary | Additional gate |
|---|---|---|---|---|---|---|
| Upload draft attachments | Own | No | No | No applicant-draft access | No applicant-draft access | Verified account; active private draft; per-file limits; technical checks |
| New/corrected own upload on open submitted case | Own | No | No | On behalf as below | On behalf as below | Portal only; preserve versions; latest completed safe version becomes current |
| Council-side case upload | No | No | Yes, Open | Yes, Open | Yes, Open | Case-wide or checked subject ownership; actual uploader logged |
| Correct applicant attachment on their behalf | No other person's file | No | Yes, Open | Yes, Open | Yes, Open | Owner unchanged; actual staff uploader/time; notification-free |
| View/download latest own attachment while open | Own | Read | Read | Read | Read | Technical safe state; no earlier version through copied URL |
| View/download earlier submitted versions | No | Read | Read | Read | Read | Council-only history; no unsent draft versions exposed before submission |
| View/download other applicant's submitted file | No | Read | Read | Read | Read | Case/ownership authorization; view/download audit |
| Upload ordinary original-case material after closure | No | No | No | No | No | Appeal-owned intake is separate; no automatic reopen |
| Read/download closed original-case evidence | No | Read | Read | Read | Read | Authorized decree is applicant exception |
| Read/download closed-case decree | Explicit recipient grant only | Read issued record | Read issued record | Read issued record | Read issued record | Stored signed version plus explicit admin/secretary release and party entitlement required; no blanket shared-case grant |
| Delete submitted original or file version | No | No | No | No | No | Retention across corrections and category changes |
| Manage attachment categories/codes | No | No | No | Yes | Yes | Current filenames updated; old names/manifests retained; stable semantic purpose |
| Search submitted PDFs/DOCX/OCR and metadata | No council-wide search | Read | Read | Read | Read | Open and closed cases; default latest, explicit include-older; no private-draft hit/count/snippet |
| Read another party's derivative/OCR text | No | Same as source | Same as source | Same as source | Same as source | Derivative is never less restricted than source |

Same-minute presented names may coincide; files do not share keys or permissions. A filename change is metadata maintenance permitted on closed records; it does not alter signed PDF contents, locked answers or source checksums. A worker completing safe extraction/name updates after closure cannot add substantive council evidence or bypass the applicant closure restriction.

Approved local processing is service access, not council draft-read permission. No external OCR/text service, automatic audio/video transcript, manual council upload-acceptance queue, attachment-count cap or user-facing export is authorized.

## 6. Account, configuration and financial administration

| Operation | Applicant | Member | Assigned | Administrator | Secretary | Additional gate |
|---|---|---|---|---|---|---|
| Register/link applicant Google/Apple/password | Own verified account | No action as council | No action as council | No automatic impersonation | No automatic impersonation | Proof of provider/account control; one primary account; scope-separated council sign-in |
| Change account email | Own after verification | Own account as permitted auth operation | Same | Same | Same | Pending until new address verified; no rewriting historical questionnaire contact |
| Create/deactivate/reactivate council accounts | No | No | No | Yes | Yes | Preserve membership/actor history; revoke deactivated sessions |
| Change council roles | No | No | No | Yes | Yes | Effective history and immediate authorization; no client-chosen role |
| Suspend/reactivate applicant account | No | No | No | Yes | Yes | Preserve records; all provider sessions revoked; applicant emailed on status transition |
| Review exact-match hold | Own hold-status notice only | No | No | Minimum identity comparison | Minimum identity comparison | Candidate names/DOB/address only as needed; never general draft answers |
| Confirm duplicates/choose primary/disable duplicate | No self-merge | No | No | Yes | Yes | Verified decision; original actor/IDs/submissions retained; no two open cases |
| Edit/publish questionnaire/declaration | No | No | No | Yes | Yes | Immutable published versions, safe rules, bilingual text, migrated drafts and preserved signed submissions |
| View case payment/refund/waiver business records | No other person's financial data | Read | Read | Read | Read | Published case/filing scope; no raw credentials or unrelated private draft data |
| Pay own final filing | Own | No | No | No payment impersonation | No payment impersonation | Completed frozen filing, USD 250, verification/eligibility checks |
| Record fee waiver | No request feature | No | No | Yes | Yes | Obligation-specific record; authorizer/reason/time; no fake charge |
| Authorize duplicate-payment refund | No | No | No | Yes | Yes | Accidental duplicate only; preserve correct filing allocation/provider history |
| Change fee amount or refund submitted fee for other reasons | No | No | No | Not granted | Not granted | No unapproved broad fee-setting/refund permission inferred |

An applicant may see the fee due/payment result needed for their own checkout. This is not approval of a separate financial dashboard or post-closure receipt-access exception to decree-only case access. Staff see business financial history for a published case; system-wide security/payment-admin audit visibility is separately restricted.

Historical administrative entry is confirmed for Administrator. Secretary historical linking is confirmed, but creating historical cases was not separately granted; do not silently expand that action from generic administration capability. The workflow discussion may settle further staff-entry authority.

## 7. Email and notifications

| Operation | Applicant | Member | Assigned | Administrator | Secretary | Additional gate |
|---|---|---|---|---|---|---|
| Send manual case email through CTM | No council send interface | No | Yes | Yes | Yes | Actual sender/time/content retained; recipient/lifecycle specifics deferred |
| Read case communication history | No shared council thread | Read | Read | Read | Read | Case-linked published record, sanitized content; private/unrouted intake restricted |
| Submit application/evidence/correction by email | No | No | No | No | No | Portal only; reply body is communication, not formal submission |
| Email-attachment intake into case file | No | No | No | No | No | Return rejected payload with notice; no evidence/OCR/search import |
| Process valid inbound reply / return attachments | Send reply outside CTM | No raw-ingestion privilege | No raw-ingestion privilege | Restricted review only where approved | Restricted review only where approved | Scoped ingestion service; validated mapping; ambiguous message held |
| Trigger automatic stage updates | No direct role grant | Deferred | Deferred | Deferred | Deferred | Future committed stage events/templates/recipient rules |

Notification routing is fixed by source:

- Applicant-originated committed corrections/new or corrected files: current assigned member + secretary, portal immediate; per-applicant/case email batch after ten minutes without further qualifying changes. If no assigned member, secretary only.
- Staff-originated answer/file corrections: no applicant/council notifications and no reset of applicant batch deadlines. Histories/audit still visible as permitted.
- Exact-match duplicate hold: admin + secretary, portal/email immediate.
- Chargeback/reversal: admin + secretary, immediate alerts, no filing deletion.
- Applicant suspension/reactivation: applicant email, selected English/Arabic language.
- Draft expiry: applicant email seven days before the current 180-day deadline.

Read-state/delivery retries are recipient-scoped. Deduplicate recipients with multiple roles; record provider acceptance/delivery honestly without claiming human reading. No case content/DOB reference appears in external alert summaries. Rejected email attachments are explicitly returned, with only transient payload handling; the permanent record contains the return/rejection metadata and approved body, not a hidden accepted attachment archive.

## 8. Case audit versus system audit

| Resource | Applicant | All council including assigned | Administrator / Secretary |
|---|---|---|
| Own answer history while open | Own only | Read each submitted applicant's history | Read |
| Individual case audit, including actor/time and attachment access | No | Read | Read |
| System-wide account/security/role/audit administration events | No | No without separate role | Read |
| Raw authentication secrets, verification/reset tokens | No | No | No UI read grant |
| Alter/delete submitted audit history | No | No | No |

A case audit projection may show that an authorized financial action occurred without exposing unrelated security events, private draft bodies or raw secrets. Case financial business records themselves remain readable to all council as confirmed. Account disabling and identity consolidation append provenance rather than rewrite old event authors.

## 9. Service and database-role boundaries

| Service purpose | Allowed scope | Explicit denial |
|---|---|---|
| Portal runtime | Verified transaction-local actor/portal plus allowed resource operations | Superuser/table-owner/BYPASSRLS, caller-supplied identity/role, direct unrestricted CRUD |
| Local scan/OCR/extraction | Assigned safe-processing input/output references, including private draft inputs; result/audit state | External document egress, council draft publication, source overwrite; testimony AI processing is a separate approved service boundary |
| Email ingestion/return | Verified receipt, routing evidence, safe body, rejected transient payload/return job | Formal submission, answer correction, new case/appeal creation, evidence ingestion |
| Notification dispatcher | Committed outbox/batch and active authorized recipients | Inventing recipients from shared case membership, duplicate sends, leaking source content |
| Draft cleanup | Never-submitted eligible draft graph checked against retention and in-flight payment/finalization | Case deletion, retained version deletion, account/category cascade purge |
| Payment handler | Verified signed/provider event, correct obligation, immutable event/idempotency | Trusting browser redirect, storing card/CVV, deleting case after reversal |
| Filename maintenance | Current category code + stable source/version metadata; append name history | Changing owner, immutable bytes, assigned applicant ID or original manifest |
| Backup/migration operator | Controlled operational copy/recovery under deployment procedures | User-facing case export role or implicit application council access |

RLS uses read/write checks and non-bypass roles; views and column-level output contracts are still required. Scoped privileged routines need fixed safe search paths and tightly limited invocation. Never allow a permissive policy for “same case” to accidentally OR away a restrictive “own party” or “case open” gate. Composite FKs validate relationship identity; they do not replace lifecycle locking.

## 10. Gates shared by every write and retrieval

1. Resolve verified portal session and active canonical identity/membership; never treat email/filename/reference as authorization.
2. Check exact role/assignment/owner action, lifecycle and resource relationship, including the subject application/file version.
3. For writes, lock/version-check the relevant root and revalidate eligibility at commit, not only when opening a form/upload.
4. For submissions, freeze the candidate and exact schema/declaration/file references; enforce all fee/hold/identity/claims rules; publish only after verified success or authorized waiver.
5. Append source revision/event, actor/time, retention edges and outbox as one internal transaction. Do not counterfeit cross-system ACID with a payment/email provider.
6. For retrieval, enforce version/closure/source authorization on bytes, OCR, snippets, nested relationships, counts, history and copied links. A previous URL is not a permanent grant.

## 11. Confirmed workflow authority

The [workflow database supplement](CTM-workflow-database.md) is part of this permission specification and overrides earlier workflow placeholders. Closed proceedings remain immutable; narrowly authorized correspondence, testimony processing/corrections, signed certificate preparation/correction/release, pending appeal supplements and reopening of a new proceeding do not grant ordinary closed-record edits.

| Operation | Authorized actor |
|---|---|
| Initial completeness Accept/Reject; rejection instructions required | Admin/secretary |
| Choose initial assignment or authorize reassignment | President |
| Record assignment/reassignment | Admin/secretary, preserving president and entering actor separately |
| Create/reschedule/close sessions; prepare agenda; record council attendance | Admin/secretary |
| Request upcoming agenda placement | Current assigned member for own cases |
| Present case hearing/appeal | Current assigned member only; absence defers to manual placement |
| Record/revise next steps and recommendations; internal/public message fields | Admin/secretary/current assigned member; preserve revisions; corrections notification-free |
| Schedule testimony | Admin/secretary/current assigned member |
| Confirm/Reject own testimony invitation | Invited applicant; explanation optional; no rescheduling |
| Manage testimony recording; correct transcript/translation | Admin/secretary; preserve source AI output and every revision |
| Read testimony audio/transcripts/translations | Council only, never applicants |
| Enter type and grounds/reason | Admin/secretary/current assigned member |
| Vote Approve/Deny/Abstain | Council member directly, or admin/secretary on behalf; attendance does not filter list |
| Read individual votes and tally | All authorized council, never applicants |
| Final presidential approval | President directly or admin/secretary records on behalf; exact approving version retained |
| Prepare decree; templates; clerical replacement; issue/release/withdraw certificate access | Admin/secretary; required stored president-signed certificate before issuance |
| Sign decree or corrected replacement | President Bishop/Metropolitan; digital or physical signed scan |
| View/download released certificate | Exact entitled applicant and exact released current version; history council-only |
| Withdraw own petition | Applicant, no approval/reason; admin may withdraw for all parties |
| Create/sign/pay/submit appeal | Either linked applicant, own submission only |
| Supplement pending appeal | Owner applicant only; no staff on-behalf supplements |
| Withdraw pending appeal before result | Owner applicant; no approval/refund |
| Record council Accept/Decline for each appeal | Admin/secretary/current assigned member; actual actor/time |
| Send case messages after closure | Admin/secretary/current assigned member; private recipients, retained history |

An applicant may access their own appeal draft/submission/supplements and case communication/invitations after source-case closure under these explicit scopes. Earlier decree-only closed-case descriptions refer to original substantive proceedings; they must not block these confirmed portal functions. Read-only original evidence is not reopened by an accepted appeal: new material belongs to the new proceeding.

This is documentation, not proof of working enforcement. Implementation must test applicant isolation, private drafts, assignment changes, closed proceeding locks, provider retries, release/revocation, sibling appeals, open-case claims and session revocation.


## 12. Returned questionnaire refinements

[All reconciled answers](CTM-questionnaire-decisions-2026-10-20.md) supplement the matrices above. Admin/secretary may correct/cancel pending party associations and correct wrong case associations while retaining history. Registration-request emails must be staff-initiated by admin/secretary/case manager; no newly inferred case-manager role or party-creation grant. Admin may stage historical entries and finalize open/closed classification; admin/secretary may correct historical transcription with original/revision history. Admin/secretary versions bilingual system-message templates and sees failed email delivery/retry information.

Council access to testimony source audio does not automatically disclose unreviewed AI text. Admin/secretary reviews generated transcript/translation versions before release to other council members; all applicants remain denied. Corrections to speaker attribution retain original AI output and revision provenance. Signed nullity decree may entitle both parties, but each still requires explicit certificate release. Conditional decree explicitly identifies parties/conditions and may close before future remarriage conditions are fulfilled. One current valid decree is separate from access to retained signed history; voiding trigger is still pending clarification.

Applicant appeal submission is not blocked merely because the other applicant appeal has reopened the same case. Both remain independent under one-draft/pending-per-applicant/case rules. Never bypass a different-open-case conflict on linking or acceptance. No fixed testimony recording/upload cap is imposed; ordinary audio attachment limits remain scoped separately. These are design permissions, not installed enforcement.

## 13. Portal and investigation interview permissions

[Portal/interview response supplement](CTM-portal-interview-decisions.md) governs this scope. Applicant can initiate/reply to case correspondence, respond to own information requests with evidence only where uploads are authorized, see own fees and download own receipt, mark own notifications read, and access private appointment/appeal/certificate projections. No staff Request completed action: incoming information/files are automatically received and flagged New. No profile-to-signed-case automatic rewrite is approved. Portal-only document lists cannot bypass exact question/request context or version ownership.

Only current assigned member conducts/authors investigation interviews. Admin/secretary may record/upload on behalf but retain actual interviewer and entering actor. Original interviewer alone revises completed narrative while case/proceeding open and currently authorized; new assigned member adds follow-ups. All active authorized council can read interview drafts/narrative and audio, but generated text requires assigned-member review before disclosure to other council. Testimony generated-text review remains admin/secretary: distinct processing purposes, not one blanket reviewer role. Interview participants are case applicants, separately; no priest/witness feature. No applicant access to any interview material. Interview auto-transcription extends authorized API processing to this purpose; no AI-generated template answers. Closed proceeding locks remain.


## Latest reference-review reconciliation

Reference-review update: assigned member selects interview categories and assembles report from stored answers under existing author/current-assignment checks. Authorized case sender may request priest testimony; intended priest receives only report-scoped minimal subject context and write/record submission capability, not case/council/applicant portal access. The separate requested priest report is now an explicit exception to earlier no-priest-feature descriptions; general priest/witness interviews/directory remain absent. Authenticated priest submission and AI review require dedicated scope checks. Council-only content stays private; exact external-link lifecycle and text reviewer are pending.


## Investigation hierarchy, source context and evaluation releases

Medical/psychiatric test/evaluation data now has a conditional signed release/disclosure requirement on applicant and council sides. Own subject only for applicant; never other-party medical access. Staff cannot sign as the subject. Signed authorization purpose/recipient/version scope must be enforced for disclosure, file retrieval, snippets and report inclusion. Exact legal text/signatory/revocation/sequence remains for institutional confirmation. Investigation source contexts are council-visible under source permission, not new cross-applicant disclosure. By-template and by-family views share existing author/assignment/source permissions. No medical-document external AI processing is authorized.



## Current medical / psychological workflow authority — 2026-10-20

The user delegated completion of this section using prior CTM choices. [Medical and psychological report workflow](CTM-medical-psychological-report-workflow.md) is authoritative for requests, optional council-recommended doctors, alternative providers, signed release capture, private applicant uploads, council access within authorization, local OCR/search, case-manager-only routine notifications, revisions/follow-ups, reassignment and closure. It specifies architecture only; no production implementation exists.

This supersedes earlier conflicting admin/secretary on-behalf case-operation permissions for this section. Those roles support system-level/cross-program administration; they do not gain operational write access to assigned-case evaluation requests by role alone. Case-manager responsibility does not remove council case-read access or the signed report-disclosure scope. The exact institution-approved release text remains a document-content dependency. No external doctor portal, automatic clinical judgment or external medical-document AI processing is introduced.


## Confirmed template management and closed reports — 2026-10-20

[Template-management workflow](CTM-template-management-workflow.md) is the current authority for system-level shared-library publishing by admin/secretary; case-manager personal reusable templates; submission of personal templates for shared publication while keeping the personal original; retirement without loss of history; preserved unsent drafts with explicit refresh; and immutable sent-question snapshots.

Reports cannot be edited after case closure, including clerical corrections. Earlier report-author editing permissions apply only while the relevant case/proceeding is open. Reopening preserves the prior closed reports; new material follows the authorized appeal proceeding. These are documentation decisions, not implemented database permissions.


## Settings and translation authority — 2026-10-20

[Settings and translation architecture](CTM-settings-translation-architecture.md) records inspected prototype system/account settings and the newly requested translation configuration: exact editable/versioned Coptic Orthodox master prompt, primary/fallback AI slots, protected server-side API keys, and a future non-AI on-host engine mode. All translation outputs retain source/version provenance. Local OCR and medical-content restrictions override any provider fallback; prompt OCR instructions do not authorize external document uploads. Account settings cannot change system integrations. Shared question translations are reviewed/versioned before publishing. This specifies architecture only; no live integration or translated question bank was built.


Arabic interface localization is confirmed for both portals. See the Arabic user interface section in [Settings and translation architecture](CTM-settings-translation-architecture.md). Versioned reviewed UI resources use the same translation service/master prompt, support RTL and separate account UI-language preference, and never change authorization or automatically translate original case answers.


## Required package capability: council Microsoft sign-in — 2026-10-20

User confirmed inclusion of Microsoft sign-in in the delivery package. [Council Microsoft sign-in](CTM-microsoft-council-sign-in.md) supersedes the earlier council email/password-only restriction by adding organizational Microsoft authentication. Admin preauthorizes the CTM member and role; a Microsoft/lacopts email alone never grants access. Provider configuration belongs to admin system settings, identity links use validated tenant/object identity, and applicant/external-priest authentication remains separate. This is specified, not deployed; actual tenant/app registration, credentials and callback configuration are required before a live connection.


## In-app communications and call workflow — 2026-10-20

User explicitly requests in-app messaging, email and calling under Communications. [Communications workflow](CTM-communications-workflow.md) supersedes older email-only/no-chat statements and distinguishes reliable device-dial initiation logging from integrated telephony answered/duration/recording events. Asterisk is an optional open-source candidate only; normal tel links cannot record the other party's telephone audio. Search and Appeals split-view previews are now confirmed in the navigation/layout map. No phone system or UI was installed.


## Confirmed native messaging policy — 2026-10-20

[Communications workflow](CTM-communications-workflow.md) now records permanent sent messages, corrections by new message, existing/new document links backed by normal case storage, no council-only chat, existing-account/case access without separate messaging accounts, immediate portal availability, and immediate or 17:00 America/Los_Angeles email-summary delivery. This does not change other workflow-specific notification schedules. No live messaging service was built.
