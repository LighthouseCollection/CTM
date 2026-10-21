# CTM reconciled database tables

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Date: 2026-10-20. Design only: no database, SQL migration, application or deployment was created. Business authority: [confirmed decisions](CTM-confirmed-decisions.md). Read with [permissions](CTM-permissions.md) and [architecture overview](CTM-data-architecture.md). Physical names below are the reconciled relational proposal, not implemented tables.

## 1. Conventions and ownership

`id` means opaque UUID primary key unless a natural/compound key is explicitly stated. Foreign keys are typed, indexed relationships. `?` means nullable; `[]` means related rows, never a comma-separated value. Dates use `date`; instants use `timestamptz`; byte counts and monetary minor units use `bigint`. USD 250.00 is `25000` cents with explicit `USD`. Names/answers use Unicode text. Display identifiers containing DOB never serve as primary keys, object keys or authorization tokens.

Mutable roots have `created_at`, `created_by_account_id?`, `row_version` and a pointer to their current immutable revision where relevant. Permanent revisions/events have actor, server timestamp and predecessor/version references. A historical actor must not be overwritten after account consolidation. `subject_person_id` is distinct from actual staff actor. Case-owned resources carry a checked case relationship; applicant resources also carry an immutable application/participation ownership path.

Only never-submitted draft content and eligible transient processing data can be removed. A submission creates retention references; there is no retained-case purge path. No cascading account/role/category deletion may erase submitted data. Closed substantive records are read-only; operational audit, correspondence delivery, finance events and category/filename metadata can still append under their confirmed scope. Appeals use their own records under the same case, not changes to the original locked submission.

Each row below names principal business columns in addition to its PK/audit conventions. Permissions refer to the matrix rather than broad table CRUD grants.

## 2. Identity, authentication and organization

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `persons` | `canonical_person_id?` self FK; identity state; current identity-review facts/reference | One stable identity root per known person; absorbed roots remain aliases; no cycles; questionnaire assertions are not overwritten by profile changes |
| `person_identity_versions` | person FK; English/Arabic name components; DOB/gender/country-of-birth answer states; source reference; actor/time | Verified or provisional identity facts only; no birth-town field; old versions retained |
| `accounts` | person FK?; scope applicant/council; status; current email FK?; notification locale en/ar; disabled duplicate target? | One primary applicant account per canonical person; preserved disabled duplicates; an unverified registration need not fabricate personal details |
| `account_email_versions` | account FK; email; normalized lookup; pending/verified/superseded; token verification event; effective times | New address inactive until verified; no rewriting prior email/contact evidence; reject conflicting verified ownership instead of automatic merge |
| `account_credentials` | account FK; maintained-auth credential reference/hash; credential version/status | Email/password only where enrolled; no plaintext passwords or questionnaire storage |
| `account_identities` | account FK; provider/issuer; stable subject; verified email claims; linked/unlinked events | Unique provider+subject association; applicant Google/Apple; linking requires proof, not email/name equality |
| `account_verifications` | account/email FK; purpose; token hash; issued/expiry/consumed/revoked instants | Email verification, invitation and recovery scopes; expiring one-use tokens; never in case-email body history |
| `account_sessions` | account FK; portal scope; authentication method; token hash; created/last seen/revoked | No idle-expiry policy; server revocation/status checks across methods; council scope requires password authentication |
| `account_status_events` | account FK; prior/new state; actual staff actor; event time | Suspend/reactivate/deactivate and duplicate disable provenance; no destructive account deletion |
| `auth_events` | account?; action/result; time; limited device/IP; request ID | System-security view only; no passwords/tokens/full questionnaire data |
| `tribunals` | name; diocese FK?; timezone America/Los_Angeles | One operating tribunal; organization data is not a multi-tenant implementation |
| `dioceses` | directory name; locale labels; optional contact/location | Source assertions retain their own text even if directory changes |
| `parishes` | diocese FK?; names; optional location | Directory reference never replaces submitted evidence |
| `clergy_directory` | person FK?; names/title; parish FK?; status | No login/access inferred from a clergy name; questionnaire counseling list remains names only |
| `staff_memberships` | council account/person FK; tribunal FK; appointment/source; effective interval; status | Former memberships and authorship preserved; active membership gates council access |
| `roles`, `permissions`, `role_permissions` | stable codes; allowed operations; effective version | Administrator, Secretary and council membership are explicit capabilities; Presiding gives no unapproved administrative override |
| `role_grant_events` | membership FK; role; grant/revoke; authorizing actor/time | Effective grants + immutable history; only admin/secretary changes council roles; eligibility guards cannot be broadened by a browser payload |
| `ctm_applicants` | person FK; tribunal FK; temporary label?; issuance source | Unique active canonical applicant identity; temporary label is internal/nonunique; prior labels retained as provenance |

The person/identity tables do not automatically prefill new questionnaires. Account email/provider identity and application contact answers are distinct. No self-service registration creates a council membership. Staff-created-on-behalf preparation and first administrator provisioning remain workflow/deployment design, not implied exceptions to draft privacy.

## 3. Case, applicant participation and identity consistency

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `cases` | tribunal FK; marriage FK?; origin new/historical; open/closed; original filed date?; CTM entered time/actor; current identifier FK | One shared case; no per-spouse case duplication; no delete; lifecycle events/proceedings defined in workflow supplement |
| `case_identifiers` | case FK; exact reference text; origin allocated/legacy; local creation date?; timezone?; daily sequence?; issued time | New format YYYYMMDD-##, 01–99; legacy references preserved verbatim and not allocated from entry date; immutable issuance |
| `case_number_counters` | LA date PK; last allocated sequence | Atomic daily allocation; 99 limit; committed values never recycled; historical entry does not increment |
| `case_number_reservations` | unique allocated reference; local date/sequence; filing/idempotency FK; reserved/issued state | Prevent checkout/finalization collisions; a reserved reference is not an open case; exact hold/release timing is a technical protocol to verify |
| `case_parties` | case FK; person FK?; participation state; ctm_applicant FK?; known role/source | Actual participating applicant requires canonical identity; an absent spouse may remain only asserted/unidentified; no compulsory second account/application |
| `applicant_references` | case_party FK; exact issued reference; origin legacy/CTM; frozen initials/DOB/gender component?; issuance actor/time/source | Preserve old applicant ID when available; missing historical details allow unassigned display ID; issued reference never regenerated after corrections |
| `person_open_case_claims` | canonical person PK/FK; case FK; participant FK; acquired time | One open case per person, including historical; checked participant/person/case consistency; lifecycle equivalence requires guarded transaction, not FK alone |
| `person_active_draft_claims` | canonical person PK/FK; application FK; acquired time | At most one unfinished new-case draft; no acquisition while person has an open-case claim |
| `case_assignments` | case FK; active staff membership FK; start/end; assigned actor/time | Partial unique current case assignment; at most one; all council members still read; president authorizes; admin/secretary records; preserve both actors and history |
| `identity_review_holds` | source draft/person; protected candidate identities; matching specification/version; state/reviewer/decision/time | Exact names/DOB/address candidate match; payment/submission blocked until review; owner may save existing draft |
| `identity_consolidation_events` | canonical target; source persons/accounts; approved actor/time; verified provenance | Aliases preserve original keys, applicant IDs and both histories; never automatic fuzzy merging |
| `historical_account_links` | historical case_party/person; verified account; linking staff actor/time; verification evidence reference | Admin/secretary-only link; no case reopening or cross-party access; correction history preserved |

New references must not collide with already used legacy reference text. Duplicate legacy identifiers, if encountered, remain preserved under distinct UUIDs and require verified disambiguation; do not silently renumber, merge or impose new-format validation on them. The uniqueness mechanism must distinguish an allocated namespace from unresolved legacy references rather than assume old data is clean.

Exact-match detection is a review rule, not infallible identification. Unknown/empty values are not positive evidence of matching identity. Store matching snapshots with restricted review access; do not expose candidate emails/cases to applicants. Consolidation resolving to two open cases cannot finalize; do not invent a case-closing override. A conflicting historical association or a concurrently acquired open claim must pause new draft/payment eligibility rather than silently erase a draft or allow a second open case.

## 4. Versioned questionnaire and declaration configuration

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `questionnaires` | purpose; stable code; current published version FK | Petition/response/appeal purpose slots; appeal uses simple signed application in workflow supplement; response onboarding remains unresolved |
| `questionnaire_versions` | questionnaire FK; number; draft/published/retired; digest; prior version; publisher/time | Unique questionnaire+number; published definition immutable |
| `questionnaire_sections` | version FK; stable section code; position; en/ar labels | Version-owned section snapshots |
| `question_definitions` | stable semantic code; type; ownership/sensitivity; answer binding FK | Unique semantic identity; no HTML ID/label identity; incompatible meaning requires a new definition |
| `question_version_definitions` | version/section/question FKs; requiredness; conditions; en/ar text/help; position; council route | Unique version+question; same source drives applicant and council; extra answers fallback prevents missing council fields |
| `question_choice_versions` | question/version FK; stable choice code; en/ar labels; position | Old selected meanings retained; Unknown is distinct from a blank choice |
| `question_answer_bindings` | question FK; typed table/column/collection binding or extension type | One authoritative editable destination per semantic field; no arbitrary table/SQL supplied by administrators |
| `questionnaire_change_events` | version; actor; prior/new config references; time | Admin/secretary changes recorded; published revisions not changed in place |
| `draft_schema_migrations` | application; from/to questionnaire version; answer mapping; affected requirements; actor/service time; notice reference | Preserve entered answers/retired values; no draft-activity reset; migration cannot alter a frozen signed/payment-bound candidate |
| `declarations` | stable purpose/code | Definition identity separate from text |
| `declaration_versions` | declaration FK; number; publication state; previous version; publisher/time | Immutable published policy version |
| `declaration_texts` | version FK; language en/ar; exact text; digest | Unique version+language; exact accepted text referenced by attestation |
| `ground_definitions`, `ground_versions` | stable code; version; detailed/simplified en/ar labels; active interval | Six approved multi-select choices; retired Imprisonment retained only for legacy meaning, not new choice list |
| `document_categories`, `document_category_versions` | stable purpose/UUID; editable code/labels; prior version; actor/time | MC/CMC/CDD/DEC meanings stable; changing code updates current filenames, not source bytes or original manifests |
| `document_requirements` | questionnaire version; category; required/conditional rule; order-instance binding; allowed media | MC/CMC/CDD/applicant photo, statement either/or and per-order copy; spouse photo conditional availability; no baptism category requirement |
| `email_template_versions` | purpose; language; exact template; allowed placeholders; publisher/time | Versioned safe email rendering; system/identity and case content remain differently retained/scoped |

Only approved configuration is mutable through the private admin surface. No template/rule supports arbitrary code execution. Configurability does not permit case purge, cross-applicant access, unverified submission or a second open case. Requiredness can change by publishing a version, not by editing a historical submission's rule set.

## 5. Applications, immutable submissions and corrections

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `applications` | applicant/person; case_party FK?; purpose; owner; origin online/historical/staff preparation; questionnaire version; current revision; first submission?; draft last activity/expiry | Owner is never inferred from uploader; appeal/review lifecycle in workflow supplement; responding-party routing remains unresolved |
| `application_revisions` | application; sequential revision; original schema version; parent revision; actor/time; source applicant/staff/system | Full authoritative revision snapshot or verifiable structural equivalent; unique application+revision; retained after any submission |
| `application_repeat_entries` | application; stable UUID; collection code; created revision | Stable children/orders/priest/prior-application identity; submitted removal is a history event, not destructive deletion |
| `application_person_assertions` | revision; subject self/spouse; English/Arabic name fields; aliases; DOB/gender; birth country/nationality; career; contact/address; immigration; church/awareness | Unique revision+subject; self residing-with only; no spouse residing-with or birth-town column; unknown spouse states allowed |
| `application_children` | revision; repeat-entry FK; first/last names; DOB; gender value/state; resides-with value/state | Gender/residence answer required, Unknown valid; no child account or stored age |
| `application_marriage_assertions` | revision; outside-Coptic flag/denomination/date; church date/priest/name/location/diocese; certificate number/issue date | Diocese Unknown allowed; source assertion never silently upgrades shared marriage facts |
| `application_separation_assertions` | revision; Married/Separated; separation date; initiator self/spouse/both/unknown; civil filed/date/court/location/reference; counseling/prior-application flags | Existing civil date/court/reference required for new petition; finalization separate from retained marital-status choice |
| `application_restraining_orders` | revision; repeat-entry FK; date/expiry; name listed; court; reference; current status | Multiple; actual court/reference/status required with no Unknown; historical-unavailable exception only for historical entry |
| `application_counseling_priests` | revision; repeat-entry FK; priest name | Name only; role/parish/contact/dates/outcome excluded |
| `application_prior_proceedings` | revision; repeat-entry FK; date; council/diocese; outcome; verified prior case FK? | Multiple; external records need no local FK; no copying previous case content into new forms |
| `application_statements` | revision; exact typed text? | Nonblank text OR submitted PDF/DOCX statement link; OCR is not authoritative statement text |
| `application_selected_grounds` | revision; ground version FK | Unique revision+ground; multiple choices; no comma-separated reason or council-finding overwrite |
| `application_extension_answers` | revision; versioned question FK; repeat entry?; answer state; validated typed value | Configurable additional fields only; fixed fields live in typed tables, not duplicate writable answers |
| `application_answer_changes` | application; from/to revision; stable question/binding; repeat-entry?; old/new state/value; actual actor/time | Original and every committed correction; no reason/no re-sign; applicant-owned history with safe actor display |
| `application_submission_candidates` | application; frozen revision/schema; declaration capture; required file manifest; fee obligation; idempotency key; state | Technical finalization bridge; no normal pay-now/submit-later workflow; preserve recovery if externally charged |
| `application_submissions` | application; frozen revision; schema/declaration references; exact manifest/digest; submitter/subject; server receipt time; origin | Immutable; publication boundary for ordinary council readers; distinguish historical transcription from applicant-signed filing |
| `application_attestations` | submission FK; declaration text/version/language; exact signer name; signature file version; acceptance/time | No fabricated historical signature; original signature does not cover later corrected answers |
| `application_migration_archives` | draft migration FK; retired question/version; previous entered answer representation | Do not lose entered answers on new questionnaire publication; deletable only with eligible unsubmitted draft |
| `application_retention_events` | application; submitted/deleted/expired boundary; actor/time; eligible cleanup state | Minimal deletion/expiry metadata; permanent after submission; retention decision serialized with finalization |

Answer states are explicit: `known`, `unknown` where approved, `unanswered`, `not_applicable`, and `historical_unavailable` on authorized historical entry. Do not make `unknown` universally legal: reported order court/reference/status cannot use it. No `declined` shortcut bypasses mandatory fields. Data typing preserves original strings; normalized search is separate.

Every core semantic code maps to exactly one typed answer table/column. A current-answers view combines the committed revision with extension answers. Copies in a frozen submission manifest are intentional evidence; they are not independently editable records. Histories track deleted repeat entries, set membership changes and staff actor separately from owner. Draft autosave is not publication to council.

Type detail: names are separate first/middle/last and optional Arabic components, self DOB is a date, self gender M/F, country fields use stable country codes plus explicit answer state, graduation year is a validated year/text where historical precision is unavailable, and contacts/addresses retain supplied strings as evidence. Spouse living-with is deliberately absent. Fixed known choices include marital status Married/Separated and separation initiator self/spouse/both/unknown. Restraining-order status vocabulary is configurable/versioned without permitting Unknown; no specific legal-status list has been invented. Narrative and field lengths are validation/physical-sizing choices, not permission to truncate evidence.

## 6. Shared marriage context, findings and notes

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `marriages` | provisional registry identity; known source; future registry link? | Separate union per case context; no future marriage process implemented |
| `marriage_parties` | marriage FK; known person FK?; source assertion link; verified identity state | Actual spouse and verified participating applicant are different concepts; absent details not fabricated |
| `case_fact_reviews` | case FK; semantic fact code; current finding-version FK | Independent council finding, not applicant answer |
| `case_fact_review_versions` | finding FK; prior version; value/text; exact source assertion/version references; actual editor/time | Only assigned/admin/secretary while open; immutable versions; applicants never read |
| `case_fact_sources` | finding version; source application revision/question/repeat entry or file-version relationship | Typed links prove provenance; verify same-case relationship |
| `case_notes` | case; original author; current version | Council-only; no applicant publication switch |
| `case_note_versions` | note; prior version; content; actual editor/time | Original author only with current editing permission; closed means no content edits for any role |

Children, ceremonies and address details displayed by council are projections of the attributed application tables, not unsourced `case_family_members` or overwriteable shared profiles. Verified identity data or a council finding may reference an assertion, but never replace the other party's response. Richer historical evidence remains in original documents. No unapproved civil-ceremony questions, counseling metadata or spouse-living-arrangement field is added to satisfy fixture text.

## 7. Private attachments, versions and derivatives

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `files` | logical UUID; security scope; owner application/party? or case; stable category FK; current safe version FK? | A draft file may predate a case; same logical owner persists after association; applicant-owned and council-wide branches exclusive |
| `file_versions` | file FK; version; immutable opaque object key; original upload filename; bytes; detected/declared MIME; checksum; uploader; UTC upload time/LA captured date-time; source version?; technical state | No manual council acceptance; original bytes immutable; latest safe replacement is current; retain all submitted versions |
| `file_name_events` | file version FK; category-code version; old/new presented name; actor/service/time | Current names update on category changes, including historical versions; original manifest/name history remains |
| `upload_sessions` | owning application/party or case; actor; category; expected bytes; transfer chunks/state; expires; resulting version | Server size checks: 25 MB PDF/image/DOCX, 100 MB audio, 500 MB video; no count/aggregate quota; reauthorize finalization |
| `file_technical_events` | version; scan/validation state/result; engine/version; time | Security acceptance only, not authenticity/relevance; rejected bytes never become current or searchable |
| `file_derivatives` | source version; derivative kind; protected output key/digest; engine/version/language; status/time | Local OCR/extraction/preview/technical transcode only; no automatic audio/video transcript; source unchanged |
| `file_search_documents` | version/derivative FK; raw extracted Unicode; normalized search representation; language/index version; case/owner route | Private source-linked English/Arabic search; current version default, council historical option; derived/rebuildable, never source answers |
| `application_file_links` | application/revision or retained manifest FK; file-version FK; category/purpose | Same owner; draft may have no case; submitted link retained |
| `restraining_order_file_links` | exact order revision/entry; file-version FK | Same application revision/owner; each reported order requires own linked copy |
| `submission_file_manifest` | submission FK; exact file-version; owner/category/code/name snapshot; checksum | Original signed evidence never follows a mutable current-version pointer |
| `file_access_events` | case/file/version; actor; action view/download/stream; time/result/request | Immutable case audit; meaningful playback correlation not one event per byte range |
| `draft_cleanup_jobs` | unsubmitted application; retention/deletion token; referenced file checks; state/time | Eligible draft originals/derivatives only; no submitted file removal; prevent submission/delete races |

Current display filename is `[case]-[issued applicant component]-[code]-[upload YYYYMMDD]-[HHMM].[validated extension]` or case-wide `[case]-[code]-[upload YYYYMMDD]-[HHMM].[extension]`. Date/time uses LA; original UTC timestamp retained. Same-minute names are allowed presentation collisions, never storage collisions. Do not use a name as an FK, storage key or file owner.

Before case association, draft files use internal UUIDs/private presentation and never expose the internal temporary applicant label. Final association assigns the case-based presented name without moving source bytes. At submission, retain the application file-version history that still belongs to the submitted record, not merely whatever version happens to be current at later cleanup. A corrected answer clearing an uploaded-document reference does not erase an already-retained version.

Local processing services can read private inputs for work but cannot grant council draft access or send source documents to external OCR/AI/CDN. Signed originals, output provenance and version history are retained; regenerating a cache must not erase original evidence or its audit. Applicant latest-only checks apply to every direct download/preview/range endpoint, including previously issued URLs.

## 8. Filings, fees and provider ledger

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `filing_intents` | subject application or appeal typed link; filing person; purpose; frozen candidate?; idempotency; state | One fee-bearing intent per actual filing; a response is not automatically a second charged petition |
| `fee_schedule_versions` | purpose; USD; amount_minor 25000; effective definition | Snapshot fee at assessment; no new fee-setting permission implied by schema |
| `fee_obligations` | filing FK unique; schedule snapshot; amount/currency; paid/waived/exempt projection | Initial petition/each appeal per filer; historical entry exemption distinct from waiver/payment |
| `fee_waivers` | obligation FK; actual admin/secretary; reason; time; scope | No applicant request table; explicit waiver satisfies only its filing; no fake payment |
| `payment_attempts` | obligation FK; provider; provider session/transaction ID; amount/currency; idempotency; state | No raw card/CVV; unique provider reference; verify successful provider amount/owner/filing before submission |
| `payment_events` | attempt/obligation; provider event ID; event type; provider/received time; amount/currency; verification | Append-only successful, failed, reversal, chargeback history; duplicate event deduplication |
| `payment_allocations` | successful payment attempt; filing/submission; allocated amount | Prevent one charge satisfying multiple filings; preserve initial payment after a duplicate refund |
| `refund_authorizations` | duplicate payment FK; obligation; admin/secretary; reason/amount/time | Accidental duplicates only under approved policy; authorization not provider success |
| `refund_events` | authorization; provider refund ID; state; timestamps | Preserve failure/success/retries; submitted application never deleted |
| `filing_finalization_jobs` | frozen candidate; verified payment/waiver; processing lease/retry; result submission | Reconcile paid technical failure without second charge; no email redirect alone marks paid |

Every submitted filing's financial record is permanent. Financial visibility for a council member requires a published case/filing path; it cannot expose private draft contents through a pre-submission transaction. Admin/secretary waiver or duplicate-review work can use minimum obligation/identity metadata without browsing answers. Provider receipt logs must redact secrets. A waiver bypasses payment only, not required documents, verified email, duplicate hold or open-case rules.

The external payment provider and database cannot share one ACID transaction. Freeze/validate first, establish technical reservations/holds, verify provider event, then commit the internal filing atomically; retain recovery states. Exact reservation timing, day rollover and payment/closure races require implementation verification, not a fabricated business workflow or extra fee policy.

## 9. Email, inbound routing and notifications

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `case_correspondence` | case; direction; canonical subject/body; initiating account/service; subject applicant?; received/requested/sent time; template/language | Permanent council communication record; not portal chat or formal filing |
| `correspondence_recipients` | correspondence; typed applicant participation/staff/contact; actual address snapshot; sender/recipient kind | Preserve actual sent address; no shared applicant visibility/reply-all assumption |
| `outbound_email_deliveries` | correspondence/notification; recipient; provider ID; state | Per-recipient/channel delivery, exact rendered content; provider accepted is not read by human |
| `email_delivery_events` | delivery; provider event ID; event type/time; verified outcome | Idempotent delivered/bounced/failed history |
| `reply_routes` | outbound message; target case/party; opaque token hash; validity/routing references | No subject-only guessing; token does not confer portal login or formal-submission authority |
| `inbound_email_receipts` | provider/message ID; safe headers/body; digest; reply references; sender snapshot; validated routing state; linked case/party? | Unique provider message; store attachment-stripped original/canonical evidence, no hidden permanent MIME attachment intake |
| `inbound_routing_events` | receipt; prior/new case/party mapping; reviewer/time | Ambiguous routing restricted; don't expose unknown inbound messages to all council |
| `email_attachment_returns` | receipt; rejected attachment metadata/digests; return notice/delivery reference; state/time | Return to validated sender with portal notice; payload temporary only, never accepted case file or OCR/search evidence |
| `temporary_email_payloads` | return event FK; restricted temporary key; expiry/cleanup state | Transport/return-only bytes; not permanent submission retention; no council/applicant document browsing |
| `account_notification_preferences` | applicant account FK unique; en/ar; effective history | Applicant notifications use preference, not answer language; no unapproved opt-out of required notices |
| `notifications` | event; recipient account; portal/email channel; payload purpose; source IDs; time; read state? | One per intended recipient/channel; safe payload, no cross-party data |
| `notification_batches` | case+source applicant+recipient+channel; included-event boundary; due_at; state; idempotency | Applicant-update email after ten-minute quiet interval; portal immediate; staff correction excluded |
| `notification_batch_events` | batch FK; source event FK | Unique membership; events arriving after atomic batch close start a new batch |
| `draft_expiry_reminders` | draft/expiry revision; warning due; notice FK; delivery state | Seven days before 180-day deadline; reset/cancel on qualifying activity/submission/deletion |
| `outbox_events` | committed event key; purpose; exact source aggregate/revision IDs; safe payload; time | Transactional handoff; no duplicate notification on retries |
| `background_jobs` | outbox/source FK; type; due time; lease; retry/state | Local scan/OCR/search/name updates/email/cleanup; no external document processing or app-level scheduler created now |

Duplicate hold: admin + secretary, portal and email immediate. Chargeback/reversal: admin + secretary immediate alerts. Account suspend/reactivate: applicant email. Applicant answer/file updates: assigned member + secretary, portal immediate, email ten-minute inactivity digest. Staff answer/file corrections: none. A council-only filename-code change is metadata administration, not applicant activity.

Reply bodies can be appended as correspondence after closure without becoming new substantive evidence or reopening a case. All formal submissions use the portal and correct appeal boundary. Returned email payloads are the explicitly requested exception to ordinary no-attachment outbound emails; they never become an accepted case submission.

## 10. Audit, history, settings and prototype support

| Table | Principal fields / foreign keys | Keys, cardinality and retention |
|---|---|---|
| `audit_events` | actor/subject; operation; exact source key; case?; classification; time/result; request ID | Append-only root; case-safe projection distinct from system/private-draft/security details |
| `audit_event_details` | event FK; restricted metadata; redacted before/after fields | Fine-grained access; full answers already in proper histories, not indiscriminate log copies |
| `historical_entry_events` | case/party; source; entered/finalized event placeholder; actor/time | No fabricated signature or fee; finalization procedure deferred |
| `tribunal_setting_versions` | tribunal; safe system/contact settings; version; editor/time | Display configuration is not permission; naming date timezone fixed by confirmed rule |
| `public_inquiries` | supplied name/email/phone; inquiry text; receipt/triage reference | Prototype contact form only; separate from case evidence; retention/routing not granted applicant-case privileges |
| `recovery_manifests` | DB restore reference; retained file inventory/digests; key-backup reference; verification outcome | Operational backup/migration integrity metadata, no case purge/export permission; destination deferred |

Readable projections: `council_submitted_applications`, `applicant_current_answers`, `applicant_own_answer_history`, `council_case_audit`, `admin_system_audit`, `council_current_documents`, `council_document_history_search` and `council_case_financials`. These are views/contracts, not independent editable data copies. Enforce closed-case applicant restrictions at their base paths and all derivative/result endpoints.

## 11. Confirmed workflow tables and remaining boundaries

The [workflow database supplement](CTM-workflow-database.md) is an integral part of this dictionary. It replaces the earlier deferred-only reservations for initial review, sessions/hearings, assignments, testimony, votes/approval, decrees and appeals with principal fields, relationships, constraints and authority. Reuse existing foundational tables where named; do not create a competing copy of assignments, files, submissions, attestations, financial obligations or messages.

Appeal applications are distinct from case proceedings. Submitted appeal does not reopen a case; council acceptance creates the new appeal proceeding under the same case number and leaves original proceedings read-only. Multiple applicant appeals share one hearing but have separate dispositions and fees. One draft or pending appeal per applicant/case is enforced. Signed appeal submission binds its own declaration and signature. Details and notification rules are in the supplement.

Remaining boundaries: responding-party onboarding and on-behalf application verification; historical-entry finalization; exact conditional/nullity recipient mappings; subsequent appeal decree suffix allocation; open-case conflict handling on appeal acceptance; long testimony audio handling. Provider, deployment and physical SQL choices remain later work.
## 12. Integrity, indexes and transactional gates

| Gate | Database design obligation |
|---|---|
| Ownership | Composite FK/checked relationship prevents file/revision/order/message linked to wrong case/party; applicant A's spouse assertion does not become B's verified profile |
| One open case / one draft | Unique claim per canonical person; deterministic locks on identity, draft and case; creation/association/closure/consolidation use same guarded operations |
| One assigned member | Unique current case assignment; atomic end/start history; current permission rechecked at write/finalize |
| Case numbers | Unique allocated date+sequence and reference; LA date capture; legacy-conflict protection; no COUNT+1 |
| Submitted content | Unique revision numbers; sealed answer rows and manifests; exact schema/declaration/file versions; no cascade deletion |
| Current versions | Pointer may advance only to checked same-file safe version or sealed same-application revision; updates audited; closed proceeding substantive write blocked; narrow appeal/certificate/correspondence exceptions scoped by the workflow supplement |
| Draft removal | No prior retained submission or shared retained version reference; lock against payment finalization and submission; expiry/delete cannot erase charged recovery candidate |
| Configuration | Unique stable field codes and version relationships; typed safe conditions; no in-place published edit; version/locale/digest bound to acceptance |
| Fees | One obligation per filing; unique provider events and idempotency keys; valid amount/currency; payment/waiver distinct; no one payment reused across filings |
| Search | Include only same-permission source rows, correct version scope and published-case eligibility; avoid private draft counts/snippets |
| Audit/notifications | Immutable event IDs; audience-specific projection; batch deadlines persistent; retries cannot duplicate sends or lose source events |

Index all material FK joins and authorization predicates. Prioritize canonical person/account links, claims, owner draft status/expiry, case lifecycle/assignment, revision/source-version paths, file category/current state, financial filing references, correspondence case/time, audit case/actor/time and job due/state. Add private language-aware search indexes to derivative representations, not raw signed source mutation. The actual indexing plan must be checked against query workloads later.

RLS is a second layer. Runtime roles are neither table owners, superusers nor BYPASSRLS; migration/processing roles are distinct. Transaction-local verified actor/portal context must not leak through pooled connections. Column-safe projections remain necessary because RLS alone filters rows, not all sensitive fields. Lifecycle/ownership conditions must remain conjunctive even when multiple role policies exist. Sources: [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [partial indexes](https://www.postgresql.org/docs/current/indexes-partial.html), [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [file uploads](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

## 13. Explicit removals from the old dictionary

No `party_threads`/`party_messages`, `export_jobs`, case `disposition_jobs`/purge retention, general-purpose automatic speech-transcript jobs outside the approved testimony process, required MFA enrollment, editable shared applicant/council answer copies, per-case child profile overwrite table, birth-locality or spouse residing-with question, counseling-role/parish repeater, blanket council draft-reading, manual upload acceptance, attachment sequence-name requirement or superseding applicant-ID generation. A process log or financial reversal is not a basis to delete a submission.

Retain legacy evidence and old meanings without exposing retired requirements in new forms. The earlier detailed draft is archived and is not an implementation specification.



## 14. Returned questionnaire schema refinements

The [questionnaire reconciliation](CTM-questionnaire-decisions-2026-10-20.md) is an integral schema supplement with aliases, case-association events/reviews, staff registration-message events, historical-entry workspaces and finalization, decree-validity events and version-specific testimony-text review. Reuse existing file/finance/correspondence/audit tables. One current valid decree is enforced per case independently of signed file versions and recipient release grants; no mass historical voiding is inferred. AI-text retrieval/search requires reviewed/released exact version, while raw audio follows its existing council-only scope. Ordinary audio limit and unbounded testimony capture are distinct purposes. Exact certificate matching route and voiding trigger await confirmation before executable constraints are designed.

## 15. Portal and interview relational supplement

The [64-response portal/interview register](CTM-portal-interview-decisions.md) supplies principal fields/relationships for information requests and responses, exact document-context links, standardized/derivative template versions/questions, case interviews/answer and observation revisions, recording/capture parts, optional manual question markers, text versions/segments and assigned-member review events. Reuse existing person/case/proceeding/file/AI/correspondence/audit domains; interview data is separate from original application answers and council-session testimony. Unique source/version relationships and closed-proceeding locks are mandatory. AI text review scope differs by purpose; broad council interview visibility never implies unreviewed text access. Requested information/files are automatically received with a New flag; no staff completion gate. No automatic question-answer extraction, priest/witness participant directory or side-by-side application view is approved by these answers.


## Latest reference-review reconciliation

The CTM-reference-review-decisions.md supplement adds versioned interview_question_categories and category/question membership, per-interview selection snapshots and interview_report_revisions assembled from retained answer/evidence versions. Add priest_testimony_requests and priest_testimony_submissions with request sender, explicit marriage/subject party, intended priest/attributed author, scoped token/authentication events and actual timestamps. Reuse file/AI/correspondence/audit infrastructure. Subject, author and requester are separate FKs. Requests do not grant case reading, and generic interview visibility does not publish unreviewed external AI text. Medical wording and external report link/reviewer mechanics are not finalized.


## Investigation hierarchy, source context and evaluation releases

CTM-investigation-model.md is the relational supplement for petition_template_memberships, interview_question_context_links, interview_confirmation_events, interview_response_evidence_links, evaluation_requests, release_form_versions, evaluation_release_attestations, evaluation_reports and evaluation_disclosure_events. Each context/confirmation pins exact application/evidence version and source party. Signed release matches subject, report, purpose and recipient; not a global consent boolean. Reuse signature/file/audit models. View mode does not create duplicate questions/answers, and scoped medical authorization must apply to OCR/search/report contexts as well as files.



## Adopted intake guidance relationships — 2026-10-20

Question definition/version → optional conditional-prompt definition/version (trigger, factual wording, avoid/reuse guidance). Template/topic/category membership reuses these definitions. These are guidance attributes/relationships in the proposed interview model, not new mandatory applicant fields. Sent intake instances preserve exact selected/custom questions and order; unused guidance is not snapshotted as a sent question. An actually asked clarification references its source prompt/version when applicable, preserves its actual wording and links the separately attributed response to that intake/report. Existing answer/evidence-version links support reuse without copying an account or sharing the other applicant's data. The 59 question IDs are unchanged; retired IDs and removed EVD questionnaire blocks stay retired. No migrations were created.


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
