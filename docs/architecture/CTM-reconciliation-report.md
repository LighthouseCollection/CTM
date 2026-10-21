# CTM database reconciliation report

Date: 2026-10-20. Scope: reconcile detailed relational documentation and permissions to confirmed user decisions. No build, migration, database creation, UI change, infrastructure operation, payment/email provisioning or case/decree workflow design.

## 1. Deliverables and authority

- [Confirmed decisions](CTM-confirmed-decisions.md): business-policy authority, updated to point to completed documentation reconciliation.
- [Architecture overview](CTM-data-architecture.md): clean current hierarchy, source-of-truth rules, invariants and deferred boundaries; replaces the accumulated working draft.
- [Detailed tables](CTM-database-tables.md): typed entities, principal columns/FKs, revision/retention semantics, unique claims and transaction guards.
- [Permission matrix](CTM-permissions.md): applicant/member/assigned/admin/secretary/service access with explicit ownership and lifecycle conditions.
- [Applicant/council reconciliation](questionnaire-council-reconciliation.md) and [prototype mapping](prototype-to-data-map.md): aligned to canonical names and approved additions/exclusions.

The original working document is preserved verbatim in `archive/CTM-data-architecture-pre-reconciliation-2026-10-20.md`, SHA-256 `59bd8e122cceee5e4415febbf73dae0bf21fa602d2cf25a55036b2f87894325f`. It is not an active implementation specification. Raw prototype inventory/JSON/source manifest remain source evidence, not overridden production policy.

## 2. Decision-to-schema-and-permission traceability

| Confirmed decision group | Reconciled tables / contracts | Permission or integrity effect |
|---|---|---|
| One council, all authorized council read submitted cases | `tribunals`, `staff_memberships`, case-scoped read views | No tenant fabrication; no automatic broad write authority |
| One stable person and applicant account across cases | `persons`, `accounts`, `account_identities`, canonical aliases | Email/provider is not case ownership; no copying old answers |
| Social applicant, password-only council, no idle timeout | Portal-scoped `account_sessions`, credentials/identities/status events | Current active membership/revocation still required |
| Email verification before starting; verified email change | `account_email_versions`, `account_verifications` | New email pending until verified; history not rewritten |
| One open case and one active new-case draft | `person_open_case_claims`, `person_active_draft_claims` | Unique canonical-person claims plus guarded locks; open case blocks draft creation |
| Shared case/absent spouse | `case_parties`, attributed spouse assertions, marriage context | No fictional second account or participation; no reciprocal applicant reads |
| New and historical numbering | Identifiers, counters and technical reservations | LA creation date, 01–99; legacy references retained; no number recycling |
| Permanent applicant IDs | `applicant_references`, original issuance provenance | No ID regeneration on corrected name/DOB/gender |
| Private drafts and expiry/deletion | `applications`, retention events, cleanup and reminder jobs | Owner-only; 180-day inactivity expiry/seven-day email; no submitted deletion |
| Versioned bilingual questionnaire/declaration | Definition/version/localization/binding tables; attestations | Admin/secretary config; exact accepted versions preserved |
| Existing drafts migrate | `draft_schema_migrations`, migrated/retired answer storage | Preserve answers; notify new required fields; no inactivity reset or signed-candidate mutation |
| One source for applicant/council | Typed answer tables and extension answer binding | No duplicate editable answer table per portal |
| Reconciled spouse/country/marriage fields | Person/marriage assertions | Unknown where approved; birth-country only; no spouse residing-with |
| Children/priest/prior applications | Children; priest-name list; prior-proceeding entries | Stable repeating IDs; child gender/residence Unknown; priest names only |
| Multiple reported orders | Order entry/revision plus typed file links | Court/reference/status actual values; own required copy per order |
| Six grounds and statement either/or | Selected ground-version links; typed statement/file manifest | Multiple selections, exact labels; PDF/DOCX or nonblank text; no Imprisonment for new versions |
| Original submission and all corrections | Revisions, submissions, attestations, answer changes | Owner corrections/admin-secretary on behalf while open; no reason/no re-sign |
| Conflicting answers vs findings | `case_fact_reviews`, versions and exact source links | No overwrite of either party; findings council-only |
| Restricted findings/notes writers | Finding/note revision tables | Assigned/admin/secretary; note author-only; closed content locked |
| Files/history/limits | File roots/versions, technical states, typed links/manifests | Automatic technical acceptance, no staff approval; latest applicant-only vs council full history |
| Filename code edits affect existing names | Stable categories/code versions and `file_name_events` | Rename presentation, preserve bytes, source manifest and old names |
| Local English/Arabic extraction/search | Derivatives/search documents, worker jobs | No external document processing, no automatic speech transcription; latest search default/history option |
| USD 250 filing/appeal and historical exemption | Intents, fee obligations, schedule snapshots | Per actual filer; fee-waived/exempt distinct from payment; no fabricated receipts |
| Final-step payment/recovery | Frozen submission candidates, provider events, allocations, finalization jobs | Verify amount/identity; no duplicate charge; no normal pay-now/submit-later flow |
| Waiver/refund/reversal | Waivers, refund authorization/events, payment events | Admin/secretary actions; all council read published case finance; immediate reversal alerts; no deletion |
| Historical entries and account links | Origin/source flags, historical links/events | Admin entry missing-data exception; verified admin/secretary linking; preserved original IDs/history |
| Exact duplicate hold/consolidation | Review holds, consolidation events, canonical alias references | Minimal private identity review; pause fee/submission; disable duplicate login without erasure |
| Council account/applicant suspension powers | Membership/role/status events | Admin/secretary only; revoke sessions; preserve old actors and submitted records |
| Manual/outbound emails and incoming replies | Correspondence, recipients, delivery events, inbound receipt/routes | Assigned/admin/secretary manual sends; body preservation, verified routing, no chat |
| No accepted email attachments | Return events and temporary payload boundary | Return with portal notice; no hidden MIME evidence archive/OCR/search ingestion |
| Immediate vs grouped vs silent notices | Outbox, per-recipient notifications/batches/events | Applicant update ten-minute email quiet window; staff corrections never enter it |
| Audit access and file-access history | Audit root/details, case/system projections, access events | All council case audit, admin/secretary system audit; applicants own answer history only |
| Closure/decree/appeals | Locked originals, internal appeal relationship reservation and explicit decree access interface | No automatic reopen; no public appeal number; no blanket decree recipient assumption |
| Never delete submitted cases, no export | Retention references/privileges; absence of export/purge tables | Account/catalog updates cannot cascade; operational backups are not user-facing exports |

## 3. Superseded proposals removed or corrected

| Old proposal/problem | Reconciled result |
|---|---|
| One case-only editable record for spouse facts | Separate applicant assertions; independent council findings and source links |
| Council/admin blanket access to unfinished drafts | Denied; narrowly scoped identity/fee metadata only for confirmed administration |
| Unrestricted `add_notes` role grant | Current assigned/admin/secretary only; author-only revisions and closed lock |
| Presiding role implicitly has every permission | General reads only unless holding a separately confirmed role/assignment; workflow powers deferred |
| Applicant history exposes old attachment bytes through original snapshots | Original manifest retained for council; applicant bytes latest-only and closed decree-only |
| Imprisonment/baptism requirement/counseling role/spouse living-with/birth town | Retired/excluded as confirmed; legacy source remains evidence |
| Automatic civil-status/date/civil-ceremony question expansion | No unapproved questions added; current fields and original CDD evidence preserved |
| Attachment sequence filename and regenerated identity-based names | Upload YYYYMMDD-HHMM; assigned applicant ID frozen; category-code rename exception recorded |
| `party_threads` / `party_messages` | Removed; email correspondence and reply capture only |
| `export_jobs`, case purge/disposition | Removed; permanent submitted retention, eligible draft cleanup only |
| Mandatory MFA or session idle expiry | Removed from confirmed authentication requirement; revocation remains |
| Automatic speech transcripts | Removed; playable audio/video only |
| Email attachment preserved in raw MIME case evidence | Attachment-stripped body/header provenance plus transient rejection-return payload |
| Financial reversal treated as deletion/withdrawal | Append-only financial fact and admin/secretary alert; application preserved |
| Full prototype case/decree state machine treated as approved schema | Explicit relationship reservations, no new workflows/authority inferred |

## 4. Design edge cases resolved without adding business policy

1. **Single source versus snapshots:** typed core fields and extension bindings have one editable authority. Immutable manifests/revisions are intentional evidence, not separate live copies.
2. **Filename renaming versus immutable submission:** current download names may change while original manifest name/code, checksum and bytes remain fixed. Source links use UUIDs.
3. **Closed records versus operational activity:** view/download audit, correspondence receipt, financial delivery/reversal and authorized naming metadata append without permitting content edits.
4. **Applicant vs actual actor:** staff corrections preserve applicant ownership but always name the staff editor/uploader. Identity consolidation never rewrites previous authors.
5. **Submitted history versus cleanup:** draft expiry/deletion checks retained graph references and in-flight payment/submission. Once a retained version is referenced, a cleared UI field cannot erase it.
6. **Technical upload safety versus approval:** the only acceptance state is technical validation. OCR failure is processing status, not council rejection of an upload.
7. **Unlimited count versus safe storage:** no count/total quota is invented; per-file limits, streaming, rate/concurrency protections and capacity monitoring remain technical controls.
8. **Duplicate identity versus perfect identification:** exact matches trigger review, not automatic merge; false negatives cannot be solved merely by unique email. Canonical confirmed identity carries claims.
9. **Appeal scope versus closure:** appeal is internally distinct under the same case; no new case number/open claim merely from submission; review effects remain deferred.
10. **Cross-system payment atomicity:** provider charge and PostgreSQL commit require frozen intent/idempotency/recovery, not an impossible shared database transaction.
11. **Role read versus write:** table reads are not blanket CRUD; history/system details, source versions, current assignment and ownership all remain explicit.
12. **Historical missing information:** unknown/unavailable values are represented without fabricated names/dates/IDs. Legacy duplicate identifier text requires disambiguation, not automatic renumbering.

## 5. Validation performed

Document checks cover:

- All 16 confirmed-decision sections have traced table/permission coverage.
- Current table names referenced by active field maps are defined or explicitly reserved/deferred.
- All 49 top-level prototype pages remain mapped; raw source inventories are not overwritten with new requirements.
- Source SHA-256 manifest comparison confirms the original 49 HTML pages and shared `app.js` have not changed.
- Local Markdown deliverable links resolve.
- Excluded exports/purge/chat/speech/MFA/idle-timeout policies are not present as active grants or required production tables.
- Notification, latest-file/history, finance and close-state guards have consistent current definitions.
- No SQL migration, runnable application source, test database or deployment artifact was introduced; new/updated deliverables are Markdown documentation only, plus the preserved Markdown archive.

These are documentation checks. They do **not** establish that PostgreSQL constraints/RLS, authentication, OCR language quality, webhook validation, file security, concurrent numbering, identity-merge races or restore recovery actually work. Those remain future implementation tests.

## 6. Deferred, not accidentally approved

- Responding-party onboarding/linking and historical-entry finalization remain unresolved. Confirmed initial intake, assignments, sessions/hearings, voting/approval, withdrawals and appeals are now reconciled in CTM-workflow-database.md.
- Exact conditional/nullity recipient mapping and institution-authored template wording remain. Confirmed decree numbering, language, approval/signature/issuance, release, access withdrawal and clerical replacement are reconciled; no generic redacted-copy assumption.
- Provider account setup, Linux distribution, VM sizing, backup destination/schedules/recovery targets and email vendor.
- Exact framework/auth implementation, physical DDL/RLS/functions, OCR/search packages and performance validation.
- Institutional declaration wording/translations; preserving exact versions is settled, substantive legal/canonical content is not invented.

Documentation scope is complete. No further user-policy question is required to finish this reconciliation. Do not build from deferred entity reservations or reopen settled questions to fill implementation details.

## 7. Confirmed-workflow reconciliation update

Added CTM-workflow-database.md as the integral workflow table/constraint supplement. Updated confirmed decisions, architecture overview, table dictionary and permission specification. Appeals lifecycle approved by user, including private signed drafts/payment, applicant-only supplements, separate sibling appeals/results, same-case reopening into a new section, original read-only history and regular decree rules. Updated testimony AI exception, recipient/version certificate release, and post-closure correspondence. This remains documentary reconciliation, not executed enforcement tests or database migrations.


## 8. Returned questionnaire reconciliation

All 39 response IDs are represented once in CTM-questionnaire-decisions-2026-10-20.md. Original response values/clarifications are retained in questionnaire/returned-answers-2026-10-20.json and pass worksheet import validation. Updated active workflow, confirmed register, table dictionary, permissions and overview. User clarifications override radio selections and prior assumptions. Exact certificate route and decree voiding trigger remain explicit follow-ups; no provider/component has been selected and no executable schema/application has been built.


## 9. Portal and investigation interview response update

All 30 portal and 34 interview question IDs are represented in CTM-portal-interview-decisions.md. Clarifications supersede worksheet examples: one current portal view; correct-location files; released decree is PDF; investigation distinct from testimony; no priest/witness participants; guided questionnaire rather than mandatory side-by-side display; optional markers; all-council draft visibility with reviewed-AI-text restriction; no AI extraction into interview answers. Standardized bilingual interview template wording is a draft for review. Confirmed register, workflow, permission and table supplements link these rules. Unclear responses P13/P30/C34 are not treated as approvals. No application or executable schema changes.
