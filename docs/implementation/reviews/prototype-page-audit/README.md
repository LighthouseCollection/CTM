# CTM prototype coverage audit: workflow, schema, database and UI

## Conclusion

The prototype was not fully reconciled at field/action level. Important factual pages and administration/search/reporting details remain missing or reduced. A page name in the navigation and a coded component are not evidence of full capability coverage. This audit does not authorize copying prototype design, changing approved schema or restoring rejected features.

## Coverage and fixed snapshots

33 HTML pages recursively; 29 business/placeholder and4 design/reference pages. Source inspection plus selected inline/shared functional scripts. No rendered visual or runtime acceptance.

- Prototype: `D:\Documents\Projects\Projects_Applications\LACopts Church Tribunal\ClericalTribunalManagement_v2\ctm-admin`.
- Backend: `d724ba56b8bd5cf501d55fbbca416470108f963a`.
- Council: `e70bb9d439ede8649b7a0fab2fcc43d718624f27`.
- Applicant: `44f311ef8538de1283b006b9a96ec31db61cb794`.
- Approved schema: `ctm-build-contract-2026-10-21-v1`,151 tables. Operational adapter:63 model classes, not a direct one-to-one table implementation.

These are separate branch snapshots, not an integrated or deployed build. Work after these commits may resolve findings. Prototype samples are fictional source evidence, not authoritative institutional text.

## Every HTML page

| Prototype | Current destination | Coverage | Findings |
|---|---|---|---|
| `admin-archived.html` | CasesTable closed view | Partial | PA07, PA08 |
| `admin-case-audit.html` | CaseAudit | Partial | PA22 |
| `admin-case-communications.html` | Communications / call log | Partial | PA20, PA21 |
| `admin-case-decree-view.html` | Issued Decree + Decision history | Partial | PA24 |
| `admin-case-decree.html` | Decision & Voting / Decree / Communications | Partial | PA23 |
| `admin-case-documents.html` | Documents media viewer | Mapped / partial | PA25 |
| `admin-case-evidence.html` | Evidence media viewer | Mapped / partial | PA25 |
| `admin-case-hearings-2.html` | Same hearing workflow, alternate empty-state fixture | Mapped alternate | PA16 |
| `admin-case-hearings.html` | CaseHearings / SessionWorkspace | Mapped / partial | PA16, PA17 |
| `admin-case-intake.html` | Reports / requests / interviews | Mapped / partial | PA19 |
| `admin-case-marriage.html` | Marriage disabled | Missing | PA01, PA25, PA28 |
| `admin-case-notes.html` | Petition internal notes / revision history | Mapped; not a missing entity |  |
| `admin-case-parties.html` | Spouses / CaseParties | Partial | PA03, PA04 |
| `admin-case-requisition.html` | Petition: individual formal submissions | Renamed / partial | PA21, PA25 |
| `admin-case-separation.html` | Separation disabled | Missing | PA02, PA25, PA28 |
| `admin-case-summary.html` | CaseSummary | Partial | PA04, PA05 |
| `admin-case-timeline.html` | CaseTimeline | Partial | PA06 |
| `admin-cases.html` | CasesTable / review / historical entry | Partial | PA07, PA08, PA26 |
| `admin-index.html` | CouncilHome | Partial | PA10, PA11 |
| `admin-management.html` | Partial system administration APIs | Mostly missing UI | PA13, PA14 |
| `admin-member.html` | No member detail workspace found | Missing | PA12 |
| `admin-reports.html` | StatisticsWorkspace (distinct from case Reports) | Partial | PA11 |
| `admin-search.html` | SearchWorkspace | Partial | PA09 |
| `admin-session-summary.html` | Closed session records, no full minutes workflow | Partial | PA17 |
| `admin-sessions-historical.html` | Closed sessions list/workspace | Partial | PA18 |
| `admin-sessions-upcoming.html` | SessionWorkspace | Mapped / partial | PA16, PA17 |
| `admin-sessions.html` | SessionList / SessionWorkspace | Mapped / partial | PA16, PA18 |
| `admin-support.html` | No support equivalent; prototype under-development placeholder | Unconfirmed candidate |  |
| `admin-user-account.html` | Profile / language preferences | Partial | PA15 |
| `consolidation-preview.html` | Design/reference experiment; not current product UI | Excluded reference |  |
| `design-preview.html` | Design/reference experiment; not current product UI | Excluded reference |  |
| `patternfly-spike/index.html` | Design/reference experiment; not current product UI | Excluded reference |  |
| `patternfly-spike/token-match-matrix.html` | Design/reference experiment; not current product UI | Excluded reference |  |

## Findings with evidence

### PA01 — P1 — Marriage overview is missing

**Classification:** Implementation gap

**Prototype source/element:** admin-case-marriage.html:67-162: outside-Coptic ceremony, dates, priest, church/location/diocese, certificate number/issue date and contextual documents.

**Current source evidence:** Council app.js:1246-1255 disables Marriage; council implementation notes explicitly say no projection. Case detail lacks these facts.

**Schema equivalent:** marriages + application_marriage_assertions + application_answers/additional_facts + file_context_links. Current Case.marriage_date is not the full record. Certificate issue date needs an explicit question/field mapping.

**Next action:** Build source-attributed council marriage projection/view and exact contextual document links. Separate spouse assertions from findings; do not invent a table per page.

### PA02 — P1 — Separation overview is missing

**Classification:** Implementation gap

**Prototype source/element:** admin-case-separation.html:92-279: separation/initiator; civil court/date/number/status; restraining orders; reconciliation; previous permit applications; documents.

**Current source evidence:** Separation is disabled in council shell; backend case_detail lacks this projection.

**Schema equivalent:** application_separation_assertions, application_restraining_orders, application_prior_records and answers. Current adapter uses AnswerRevision.answers JSON.

**Next action:** Build read projection and page. Render multiple orders/prior records and approved Unknown states. Do not restore rejected spouse lives-with requirements.

### PA03 — P1 — Spouses page loses detailed profiles

**Classification:** Implementation gap

**Prototype source/element:** admin-case-parties.html:101-180: DOB, aliases, birth country, nationality, contact, immigration, education/graduation, occupation, church/parish/Father of Confession.

**Current source evidence:** council-case.js:2234 CaseParties shows name, CTM reference, registration badge and add-spouse form. api.py:469 case_detail provides only minimal party details.

**Schema equivalent:** person_identity_versions + application_person_assertions + answers/additional_facts. Current Person/Account/Party do not provide the complete council profile.

**Next action:** Map each approved field to exact question code and retained answer source, then render attributed spouse profiles. Unconfirmed prototype-only fields need review; do not merge conflicting spouse accounts of a fact.

### PA04 — P1 — Children missing from council overview

**Classification:** Implementation gap

**Prototype source/element:** admin-case-parties.html:191-215 and summary:251-255: repeated child names, DOB/age, gender and lives-with.

**Current source evidence:** CaseParties, CaseSummary and case_detail have no child projection.

**Schema equivalent:** application_children + stable repeat-entry identities; generic answers lists are only an adapter. Age is derived, not a stored timeless fact.

**Next action:** Connect repeated children into Spouses/Summary with approved Unknown and per-source attribution.

### PA05 — P1 — Summary lacks factual overview

**Classification:** Implementation gap

**Prototype source/element:** admin-case-summary.html:208-348: filing date, grounds, duration, last hearing, children, key dates.

**Current source evidence:** council-case.js:2649 CaseSummary shows operational state, assignee, spouses, proceeding, request counts and decision links, not the full factual summary.

**Schema equivalent:** Submissions, grounds, marriage assertions, children, hearings and lifecycle events already planned.

**Next action:** Restore factual summary with authoritative dates and source links. Distinguish creation from filing and define duration endpoints.

### PA06 — P2 — Timeline omits marriage/family chronology

**Classification:** Implementation gap

**Prototype source/element:** admin-case-timeline.html:79-81,115-120: Case/Marriage filters, church marriage, births, separation, divorce and counseling.

**Current source evidence:** CaseTimeline derives audit milestones and assignment history, not a full family chronology.

**Schema equivalent:** Assertion/repeat records plus lifecycle events. Event occurrence date is different from audit recorded_at.

**Next action:** Add source-linked factual timeline and filters. Do not silently restore timeline export/rasterization.

### PA07 — P1 — Cases/Archived lose queues and important columns

**Classification:** Implementation gap

**Prototype source/element:** admin-cases.html:118-159: My/Unassigned/Active/Closed/Incomplete/All tabs, spouses, last activity, filing date, grounds and outcome; admin-archived.html:81-87.

**Current source evidence:** council.js:2300 CasesTable shows case number, manager and open/closed status only. api.py:445 lacks richer row projection.

**Schema equivalent:** Case lifecycle, application completeness, assignments, party identity, grounds, submissions, decisions/decrees are distinct concepts.

**Next action:** Restore server-backed queues/columns/filters; incomplete means formal returned/incomplete filing, never private unfinished drafts. No case delete or arbitrary close action.

### PA08 — P1 — Pagination cannot reach all records

**Classification:** Implementation gap

**Prototype source/element:** Cases, Archived and historical-session browsing imply complete record access.

**Current source evidence:** api.py:445 cases and :594 sessions return only first100; DataTable pagination operates on that array.

**Schema equivalent:** No new business table: needs authorized query, count and stable cursor/filter contract.

**Next action:** Implement server pagination and complete counts, test >100 cases/sessions and stable ordering.

### PA09 — P1 — Advanced search is document-only and lacks filters

**Classification:** Implementation gap

**Prototype source/element:** admin-search.html:88-116: cases/people/documents/sessions, case ID/name/status/grounds/manager/document type/date range.

**Current source evidence:** council.js:2092 SearchWorkspace offers query/history only; backend search service queries ctm_documents, api accepts q/history/case_id.

**Schema equivalent:** search_documents supports source_kind/source_id/version/security scope; additional entity indexing/query projections missing.

**Next action:** Restore unified authorized entity search and filters. Keep text in POST bodies, medical exclusions and source authorization on every result/snippet.

### PA10 — P2 — Dashboard misses defined content

**Classification:** Implementation gap

**Prototype source/element:** admin-index.html:484-570,802-855; earlier approved dashboard plan also requires Outstanding Requests.

**Current source evidence:** CouncilHome:2207 has session dates, unread/review/consideration counts and own-case cards; no outstanding requests, previous summary, roster workload or recent submissions.

**Schema equivalent:** Requests, assignments, sessions and submissions exist conceptually; aggregate projections missing.

**Next action:** Complete functional dashboard in Plenix and conduct actual visual review. Do not copy prototype CSS or hardcoded metrics.

### PA11 — P2 — Statistics is only basic operational counts

**Classification:** Implementation gap

**Prototype source/element:** admin-reports.html:77-103; admin-index.html:579-790: period, case volume/status/grounds/outcomes/workload/durations and demographic breakdowns.

**Current source evidence:** council.js:2368 StatisticsWorkspace computes limited open/closed/unassigned/member/session counts over max100 rows.

**Schema equivalent:** Most source facts already planned. No obligatory analytics table; period/denominator definitions required.

**Next action:** Implement full server aggregates and period filters. Outcome proportions can be valid with defined cohort; do not call tribunal demographics population divorce rates or imply causation.

### PA12 — P2 — Council member detail/history page absent

**Classification:** Implementation gap

**Prototype source/element:** admin-member.html:132-184: member ID/contact, active assigned cases and past cases.

**Current source evidence:** No member-detail workspace; roster API is not equivalent to member historical workload view.

**Schema equivalent:** staff_memberships/roles, accounts, case_assignments. Past workload cannot be reconstructed from current assigned_member alone.

**Next action:** Provide member profile/current/past cases with retained assignment history and bounded queries.

### PA13 — P1 — System management UI mostly absent

**Classification:** Implementation gap

**Prototype source/element:** admin-management.html:191-250,317-470: staff lifecycle, tribunal settings, grounds/stages/outcomes, template library/editor.

**Current source evidence:** Generic settings API allows six keys; enrollment/authority routes exist but no equivalent comprehensive system administration workspace.

**Schema equivalent:** Staff tables, ground_definitions, decision_types, document_categories, questionnaire/declaration/template/setting/integration versions.

**Next action:** Build system-level management, not case-member authority. Existing-admin-only council creation and later fixed permission rules supersede generic role toggles.

### PA14 — P2 — Previous members/login sessions/security views incomplete

**Classification:** Implementation gap

**Prototype source/element:** admin-management.html:239-250,280-301,529-599: departed members, login result/IP/device, session revocation and audit filters.

**Current source evidence:** Active-account flag, partial membership dates and generic audit are not full lifecycle/login/session interfaces.

**Schema equivalent:** staff memberships/roles, account_events, app_sessions/identities; provider login events require explicit integration.

**Next action:** Define CTM vs provider-session/log sources and safe retention, expose authorized history/revocation. No local password system.

### PA15 — P2 — My Account profile is a stub

**Classification:** Implementation gap

**Prototype source/element:** admin-user-account.html:113-157,197-276: photo/title/name/phone/contact, role/appointment info, cases/activity.

**Current source evidence:** app.js:1521 Profile displays name and portal; Account Settings provides languages only. No full phone/photo profile adapter.

**Schema equivalent:** Identity/profile facts, staff memberships/roles and contextual photo ownership need exact mapping.

**Next action:** Complete approved profile/contact and role/activity views; keep provider identity/email-change rules. Do not restore password/timeouts/SMS widgets.

### PA16 — P1 — Session timing/location/presiding metadata lacks explicit storage

**Classification:** Schema clarification + implementation gap

**Prototype source/element:** admin-sessions-upcoming.html:125-130; admin-session-summary.html:83-86: time, presiding member, location and actual duration.

**Current source evidence:** CouncilSession stores date/state/closed_at; session API has date/reference/state/capabilities only.

**Schema equivalent:** Baseline council_sessions also lacks scheduled time/location/presiding snapshot. Testimony appointment location/time is not session metadata.

**Next action:** Define session start/timezone/location and presiding reference/snapshot; clarify actual start/end. Append approved schema mapping/change rather than fabricate values.

### PA17 — P2 — Session summary/minutes not complete

**Classification:** Schema clarification + implementation gap

**Prototype source/element:** admin-session-summary.html:91-150: totals, cases/outcomes/recommendations, attendance, minutes, recorder/approval and print.

**Current source evidence:** Closed agenda/hearing records exist; no dedicated equivalent minutes version/approval entity or full summary generator found.

**Schema equivalent:** Agenda/attendance/hearing outcomes support summary. No session_minutes entity in151 baseline.

**Next action:** Compose retained-record summary. Editable minutes/approval require workflow/schema decision; prototype TBD is not approval. Printing is distinct from rejected exports.

### PA18 — P2 — Historical session filters incomplete

**Classification:** Implementation gap

**Prototype source/element:** admin-sessions-historical.html:189-214 and admin-sessions.html:345-369: date/year, member, ground, outcome and totals.

**Current source evidence:** Split session list/closed workspace exist; no complete filtered/paged aggregate API.

**Schema equivalent:** Sessions, agenda, assignments, hearings and decisions supply sources.

**Next action:** Add complete historical filters/counts and friendly date-based names; do not restore old sequence IDs.

### PA19 — P2 — Interview event metadata only partly retained

**Classification:** Schema clarification + implementation gap

**Prototype source/element:** admin-case-intake.html:211-260: subject, actual interviewer, method, datetime/location/duration.

**Current source evidence:** Report has completion_date/method/author; structured actual location/duration/datetime not found. Recording duration is different.

**Schema equivalent:** reports baseline has completion_date/method, recordings duration. Explicit mapping needed for remaining approved interview facts.

**Next action:** Reconcile interviewer vs recorder and event metadata. Owner later chose date sufficient for report naming, not necessarily deletion of event details.

### PA20 — P2 — Call logging has narrower metadata/contact scope

**Classification:** Implementation gap

**Prototype source/element:** admin-case-communications.html:359-386: spouse/clergy contact, inbound/outbound, date, duration and notes.

**Current source evidence:** CallRecord requires Party and has occurred_at/outcome/notes; no explicit direction/duration or clergy contact.

**Schema equivalent:** call_details has contacted_person/call_at/outcome/notes; communications.direction could hold direction if adapter mapped.

**Next action:** Document call-to-communication mapping and clarify clergy contact scope. No new dialing/automatic phone recording claim.

### PA21 — P1 — Communication subject/external recipients/inbound reply coverage incomplete

**Classification:** Implementation gap

**Prototype source/element:** admin-case-communications.html:315-345: subject, spouse/clergy recipient and message history.

**Current source evidence:** Existing Message/Recipient and call UI do not establish full subject/thread/external-clergy/inbound integration.

**Schema equivalent:** communications.subject/channel/direction; recipients.external_email; reply_routes/inbound_receipts/attachment_returns planned.

**Next action:** Map actual subject/thread/delivery contract; distinguish priest request invites from ordinary correspondence. Private spouse channels and contextual document links remain required.

### PA22 — P2 — Case audit structured filters reduced

**Classification:** Implementation gap

**Prototype source/element:** admin-case-audit.html:96-101: action/user selectors and timestamp/action/user/target/description.

**Current source evidence:** CaseAudit offers free-text filtering; equivalent action/user/date structured controls absent.

**Schema equivalent:** audit_events source references and safe details already planned.

**Next action:** Add useful authorized filters/pagination and safe actor/target context, preserving council vs system audit scope.

### PA23 — P1 — Decree template authoring/generation missing

**Classification:** Implementation gap

**Prototype source/element:** admin-case-decree.html:378-416 and admin-management.html:408-470: preamble/findings/canonical basis/statement/conditions editor, signature and templates.

**Current source evidence:** Council decree UI uploads signed PDF, records signature, issues and releases; notes explicitly state generation unavailable.

**Schema equivalent:** decree_template_versions/certificates/issuance/entitlements/releases planned; current smaller model adapter not fully equivalent.

**Next action:** Complete approved versioned type-specific EN/AR/bilingual certificate authoring/generation. Institutional wording remains blocked; no sample doctrine treated as approved.

### PA24 — P2 — Issued decree structured read needs reconciliation

**Classification:** Implementation gap

**Prototype source/element:** admin-case-decree-view.html:233-405: metadata, tally/member votes, narrative sections, signature and PDF.

**Current source evidence:** Votes/decision/decree details exist across separate destinations; structured narrative preview/generation absent.

**Schema equivalent:** Decision/votes/approval and exact signed PDF/template provenance, not duplicate free-editable certificate facts.

**Next action:** Map existing destinations before duplicating; provide source-linked read view while exact signed certificate remains authoritative.

### PA25 — P1 — Contextual documents not connected to missing factual pages

**Classification:** Implementation gap

**Prototype source/element:** Marriage:144-162, Separation:261-279, Requisition:108-126 plus Evidence/Documents split views.

**Current source evidence:** Global viewers and file contexts exist; no Marriage/Separation view to host their exact category/context files.

**Schema equivalent:** files + file_context_links + repeat/question context + exact versions/manifests; current Attachment.context is a string adapter.

**Next action:** Map stable contexts and render latest permitted versions in correct locations. Multiple links must not require copying originals.

### PA26 — P1 — Historical case entry lacks full council UI

**Classification:** Implementation gap

**Prototype source/element:** admin-cases.html:88 Create a Case; owner later approved special historical entry with missing facts/no fee.

**Current source evidence:** Backend historical_stage/publish and workspace exist; no complete historical-entry workspace in council module inventory.

**Schema equivalent:** historical_entry_workspaces, preserved original identifiers and unavailable facts.

**Next action:** Add authorized system-level entry, open/closed selection and original IDs without bypassing ordinary applicant requirements.

### PA27 — P1 — Full schema equivalence not demonstrated

**Classification:** Schema reconciliation gap

**Prototype source/element:** Detailed pages versus151-table approved contract; not a one-page/one-table exercise.

**Current source evidence:** Pinned backend has63 model classes/aggregate adapters; JSON stores several normalized concepts. Counts alone prove neither data loss nor equivalence.

**Schema equivalent:** Need per-column mapping to model/JSON path, type, validation, repeat ID, history, RLS, provenance and query/index semantics.

**Next action:** Create explicit equivalence register; migrations only for unsupported semantics after review. Do not replace approved schema to match adapter.

### PA28 — P1 — Application-to-council field coverage not proven

**Classification:** Verification gap

**Prototype source/element:** All spouse/marriage/separation/repeat labels; build-spec requires accepted AF wording and repeat details.

**Current source evidence:** Generic renderer/report question bank is not proof published petition definition includes every approved field. Report questions are not application intake.

**Schema equivalent:** Questionnaire code -> assertion/answer JSON path -> formal revision -> council projection, with exact EN/AR/Unknown requirements.

**Next action:** Register each prototype field and later disposition; identify omitted codes vs stored-but-unshown values. Do not silently add unapproved prototype-only questions.

### PA29 — P2 — Page completion needs seven-stage evidence

**Classification:** Governance gap

**Prototype source/element:** All business pages and later Reports/Appeals/Assessments workflows.

**Current source evidence:** Named screen/fixture-tested component was conflated with full working and visual acceptance. Separate branches are not localhost integration.

**Schema equivalent:** Delivery governance, no new business entity.

**Next action:** Track Workflow/Schema/Database/Coded/Working/UI/QA per capability, with source/runtime/visual evidence separately.

### PA30 — P2 — Dynamic controls must remain requirements evidence

**Classification:** Coverage rule

**Prototype source/element:** admin-cases.html:118-159 inline tabs/actions and shared prototype app.js; design previews separate.

**Current source evidence:** Static headings alone miss operational tabs, fields and state-dependent actions.

**Schema equivalent:** Map destinations/actions/roles, not literal old navigation or CSS.

**Next action:** Keep functional coverage while excluding purge/export/password/old-stage shortcuts; prototype scripts are not normative permission logic.

## Schema: preserve semantics rather than matching table names

| Prototype concept | Approved data home | Current mapping / gap |
|---|---|---|
| Spouse profiles | identity versions + application_person_assertions + answers | Person/Account/Party + AnswerRevision JSON; rich council projection absent |
| Marriage/ceremonies/certificate | marriages + application_marriage_assertions | Case date + JSON; certificate issue date field/code mapping unresolved |
| Separation/civil divorce | application_separation_assertions | JSON adapter; factual council page absent |
| Children/orders/prior marriages/applications | application repeat entries + typed repeat tables | JSON lists need stable entry IDs, validation, provenance and version mapping |
| Petition/requisition | applications/revisions/submissions/grounds/manifests | Renamed Petition; do not duplicate merely to match old page name |
| Intake/report | requests, sent snapshots, reports, answers, revisions and source links | Aggregated into ReportRequest/Report/ReportRevision |
| Session/hearing attendance | session_attendance + hearing_attendance | Combined Attendance model may be equivalent if scope constraints/history preserved |
| Session time/location/presiding | No complete explicit baseline mapping | Actual schema clarification, not merely a missing page |
| Minutes/version/approval | No baseline session_minutes entity | Uncovered workflow/schema decision; compose summary separately |
| Decree | template versions/certificates/issuance/entitlements/releases | Smaller adapter; authoring/generation missing |
| Communications | communications/recipients/call_details/inbound/reply/delivery tables | Message/Recipient/CallRecord/Outbox narrower adapter |
| Administration | memberships/roles/account events/sessions/settings/integrations | APIs and generic settings are not complete management UI |

A field register must record prototype label, later owner disposition, application code, exact DB column/JSON path, required/Unknown rules, repeat identity, formal source revision, read/write authority, retained history, index/search path, actual council destination and acceptance tests. Generic JSON presence alone is not proof of equivalence; absent normalized table name alone is not proof of lost data. Do not create one table per HTML page.

## Prototype items deliberately superseded

- No permanent purge/delete of submitted cases. Draft deletion and narrowly scoped wrong-file handling remain separate.
- No bulk case export PDF/CSV/Excel. Approved decree/priest-request printing is a separate workflow.
- No local password/reset screens, forced inactivity timeout controls or SMS assumptions; later identity-provider decisions control.
- Only existing admin adds council accounts. Generic role switches must not broaden fixed case permissions.
- No Imprisonment ground; use the approved six grounds.
- No mandatory sequential spouse testimony, vote-before-type wizard, all-votes-required approval or draft/finalize message stages.
- Reconciliation is withdrawal; no required reason or separate approval invented.
- Use agreed new-case/session/decree identifiers, preserving historic IDs only for historical records.
- No other-spouse submissions, internal findings/recordings or unreleased certificates exposed to applicants.
- Do not restore rejected spouse lives-with requirement/current-address expansion.
- Do not copy desktop-only blockers, legacy custom CSS, PatternFly spike/token rules or hardcoded statistics.
- Sample theological/legal decree text is not approved institutional wording.
- Support is a prototype placeholder, not evidence of an approved support-ticket subsystem.
- Old case action menu Close/Reject/Delete is not current permission authority. Closure follows decision/withdrawal rules.

## Seven completion stages

| Work area | Workflow | Schema | Database | Coded | Working | UI | Testing / QA |
|---|---|---|---|---|---|---|
| Marriage/Separation/Spouses/children | Mostly agreed; reconcile fields | Mostly mapped; specific gaps open | Partial JSON adapter | Missing/partial views | Not established here | Not accepted here | Source audit only |
| Queues/search/dashboard/statistics/member history | Prototype + agreed plan | Existing concepts | Query/aggregate gaps | Partial | Not established end-to-end | Not accepted here | Needs actual API and visual review |
| Session metadata/minutes | Details require decision | Explicit additions/mapping needed | Metadata missing | Session workspace partial | Not established | Not accepted | New checks after approval |
| Administration/profile | Later role/provider rules control | Mostly planned | Partial | Mostly missing UI | Not established | Not accepted | Role/provider tests needed |
| Decree authoring | Defined; text approval blocked | Approved entities mapped | Partial adapter | Upload/issue/release exists; generation absent | Full journey not accepted | Not accepted | Signed PDF/content/release checks needed |

No new product code or database mutation was performed. Existing worker test results do not establish prototype completeness or visual acceptance.

## Suggested correction order (not new worker assignments)

1. Complete factual coverage: Marriage, Separation, Spouses/children, contextual documents and Summary.
2. Publish exact field/schema/JSON mapping and source-attributed API projections, including private returned answers and conflicting spouse assertions.
3. Restore full queues/filtering/pagination, advanced search and member history.
4. Reconcile session metadata/summary; approve any editable minutes workflow separately.
5. Complete management/account UI and decree authoring without reintroducing rejected prototype features.
6. Finish meaningful server dashboard/statistics and visually review EN/AR/mobile against Plenix.
7. Run combined actual-backend acceptance; update all seven stages before calling a capability fully complete.

## Evidence and limits

- `audit-results.json`:33 page records,30 findings and prototype SHA-256 inventory.
- `prototype-inventory.json`: visible text/input identifiers with line numbers for every HTML page.
- `prototype-extracted.txt`: readable extraction; includes fictional prototype samples.
- Source inspection includes selected inline scripts/shared app.js for dynamic controls. Not every handler was executed.
- No browser screenshot/click-through audit or production DB query. No live provider/OCR/transcription claim.
- Adjacent public applicant pages outside requested ctm-admin tree were not independently audited. Full application-field coverage is a follow-on dependency.
- Current source anchors refer to pinned branch files, not the localhost build.

- `field-mapping-review.csv`: 48 detailed prototype field mappings with explicit unresolved application-code/JSON-path qualifiers. This is a reconciliation worksheet, not a completed equivalence claim.
