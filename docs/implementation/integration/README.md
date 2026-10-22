# Integrated CTM screen and feature map

This is a pinned integration snapshot, not a completion percentage. Each screen separates implemented behavior from remaining work. Working is scoped to the stated tests; UI is not accepted merely because it renders.

## Build and evidence

- branch: `governance/integration-20261021`
- backend: `37d6ed7afb000b8959843e42607d56e156f6a851`
- applicant: `2ae4541651e89589ca1bb554c1d3e1a67443c760`
- council: `65fa3893758ab298beee8aa921a544a8cd489ebc`
- assembly: `backend merge, applicant merge, council merge; reverse council standalone shell patch, apply applicant then council-after-applicant shell patches`
- preview: `http://localhost:18844/`
- limitations: `No production deployment, no full151 schema completion, no live payment/email/scan/OCR/transcription or general visual approval.`

- frontend_unit: 180 passed
- postgres: 490 passed,2 skipped; no model drift
- actual_api_browser: 66 groups passed; isolated SQLite, synthetic sessions, controlled scan/provider policy
- seed_fixture: 3 SQLite tests passed after correcting legacy fixture manifest identity key

The preview uses a COPY of the existing isolated local review database/media with provider-only Microsoft login retained. Original data/checkout remain intact. It is loopback-only and uses test settings, so it must never be exposed publicly. No prototype redesign was performed.

## Screen map

| Portal | Screen | Implemented / connected | Remaining | Working evidence |
|---|---|---|---|---|
| Shared | Sign-in | Universal entry, provider routing; genuine Microsoft local review setup retained | Live Google/Apple and production Microsoft acceptance; full identity/role reconciliation | Microsoft previously verified; integrated root HTTP200 |
| Applicant | Home/current work | Current filing or open case prioritized | Full approved dashboard/action completeness | Actual API browser suite within synthetic scope |
| Applicant | Application questionnaire | Versioned editing, conditional fields, explicit saving, draft checklist/requirements | Full approved bilingual form content and exact prototype field mapping | Actual API browser suite |
| Applicant | Application documents | Contextual originals, replacements, safe-file states and interrupted-upload guard | Live ClamAV/storage and large resumable uploads | Actual API browser suite; scan policy controlled |
| Applicant | Review/declaration/submission | Review, declaration binding, version/fee gating and formal submission | Institutional declaration approval and live payment callbacks | Actual API browser suite; fixture waiver/provider |
| Applicant | Returned corrections | Original submission retained; private saved corrections and resubmission | Full field-history presentation acceptance | Privacy regression + actual API browser suite |
| Applicant | Payment history/checkout recovery | Own events/receipts, original checkout binding, expiry and safe resume | Real Stripe receipts/refunds/reversals and delivery acceptance | Actual API suite; controlled provider output |
| Applicant | Draft deletion/withdrawal | Capability/version checks, explicit confirmation and recovery | Combined institutional workflow acceptance | Actual API browser suite |
| Applicant | Communications | Private send/history/read receipt, pagination, idempotency and recovery | Actual SMTP/inbound reply/attachment-return integration | Actual API browser suite; no live email |
| Applicant | Testimony appointments | Private invitations, confirm/reject and optional rejection explanation | Live invitation/reminder delivery and devices | Actual API coverage; no live email |
| Applicant | Requests/intake responses | Own bound questions, scoped evidence, response receipts/replay | Full approved templates and actual mail delivery | Actual API browser suite |
| Applicant | Professional release/assessment response | Explicit bound declaration/scope, separate consent file and assessment response | Institution-approved signed release wording and live scan acceptance | Actual API synthetic declaration only |
| Applicant | Appeal filing/additions | Draft/start, paid-or-waived submission, own history/additions/replay | Full real later-petition and council disposition journey | Actual API/browser; some sibling states fixtures |
| Applicant | Past cases/released certificates | Closed-case list and current recipient release reader | Actual signed institutional certificates and full access/revocation acceptance | Partial API scope; no institutional certificate approval |
| Shared | Notifications | Own notification list and read-state controls | Live delivery/template/language completeness | API coded; combined manual acceptance partial |
| Council | Home dashboard | Upcoming dates, review/unread/consideration counts and own cases | Outstanding requests, fuller session context/prior summary, workload/recent submissions and visual acceptance | Read-only actual API smoke |
| Council | Cases | Sortable/pageable returned-array table and case opening | Spouse/factual columns, operational tabs, advanced filters and server pagination | Read-only actual API smoke |
| Council | Archived | Closed case list and read navigation | Richer outcome/closure columns and complete pagination | Read-only actual API smoke |
| Council | Completeness review | Submitted queue, formal answers/files, return instructions and accept | Full combined reviewer/applicant visual acceptance | Backend tests; read smoke not write acceptance |
| Council | Tribunal Sessions/agenda | Assignment/hearing phases, attendance, reschedule, testimony and carryover | Session metadata, richer historical filters, complete summary/minutes decisions | Read smoke + backend tests; full UI journey pending |
| Council | Case Summary | Status, assignee, spouses, proceeding, requests and decision links | Filing/grounds/marriage/children/last hearing/key-date factual summary | Read-only actual API smoke |
| Council | Timeline | Audit milestones and assignment history | Marriage/family chronology, factual dates and filters | Read-only actual API smoke |
| Council | Spouses | Names, reference, registration and authorized add-spouse form | Rich sourced personal facts, children and accepted shared-fact discrepancy projection | Read-only actual API smoke |
| Council | Marriage | Navigation label only, disabled | Full shared-fact view, discrepancy flags and contextual documents | Not implemented |
| Council | Separation | Navigation label only, disabled | Full separation/civil divorce/repeated orders/prior-records and discrepancy view | Not implemented |
| Council | Petition/notes/findings | Formal questionnaires and internal notes/history; findings read | Approved fact-code finding creation and full contextual evidence | Read smoke + backend notes/findings tests |
| Council | Reports/intake/templates | Template/category selection, questions, requests, report reader and author revision UI | Full report metadata and external priest workflow; broader author/reassignment UI acceptance | Read smoke + shipped JS payload against PostgreSQL HTTP write/replay/conflict; QA01 separate |
| Council | Recording/transcripts | Whole-report recorder/local recovery and original playback; status placeholder | D20 status/review/retry UI wiring, real worker, server streaming, device/long-audio acceptance | Fixture-tested UI; live transcription unavailable |
| Council | Hearings | Agenda appearances, presenter/attendance/outcome and applicant update | Combined real full session/decision journey and metadata | Read smoke; backend tests |
| Council | Evidence/Documents | Split read/view, image/audio/video and browser-native PDF fallback | CDN embedded PDF repair; live safe-file range/playback/OCR acceptance; missing factual-page contexts | Read-only API smoke; renderer interactions need further acceptance |
| Council | Professional Assessments | Separate requests/scope-gated read | Approved signed release text, recommendations workflow and real acceptance | Read smoke; backend scope tests |
| Council | Decision & Voting | Catalog/grounds/named entitlements, roster/votes/approval/history | Full combined decision approval journey and approved Arabic labels | Read smoke; backend/unit tests |
| Council | Decree | Signed PDF upload/signature record/issue/release/withdraw access | Approved type-specific templates and certificate authoring/generation | Read smoke; backend lifecycle tests |
| Council | Appeals/later petitions | Queue/detail, hearing eligibility and per-filing accept/decline | Combined actual two-spouse reopening/decree cycle acceptance | Read smoke + backend tests |
| Council | Communications/calls | Private recipient messages and manual call log | Inbound/live email, full subject/contact/duration mapping | Read-only API smoke; backend delivery tests |
| Council | Case Audit | Case event list/search | Structured filters, full pagination and target context | Read-only API smoke |
| Council | Q Search | Document query and history toggle | Unified case/person/session results and advanced filters; live index acceptance | Screen renders; live query not accepted |
| Council | Statistics and Reports | Open/closed/unassigned/workload/session counts | Complete server metrics/periods/charts; max100 limitation | Read-only API smoke |
| Council | Member profile/history | Roster only | Member details/current/past assignment workspace | Not implemented |
| Shared | My Profile | Name/portal display | Editable profile/contact/photo relationship and own activity | Stub |
| Shared | Account Settings | Interface/notification language | Consolidated account fields, provider email/security/session workflow | Partial |
| System | CTM Settings/account management | Selected enrollment/configuration APIs exist | Consolidated admin/settings screens, roles/lifecycle/photo/secrets inventory | No complete screen |
| System | System Audit/security history | System audit API exists | Complete system audit/login/session management UI | No complete screen |
| System | Historical case entry | Staging/publish API exists | Authorized historical entry form, missing-data workflow, retained identifiers | API tested; screen missing |
| External | Priest report capability page | Backend capability endpoints exist | External page/delivery and actual acceptance | No complete user-facing workflow |

## Seven stages by screen

| Screen | Workflow | Schema | Database | Coded | Working | UI | Testing/QA |
|---|---|---|---|---|---|---|---|
| Sign-in | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Microsoft previously verified; integrated root HTTP200 | Not accepted; no redesign performed | Partial; evidence scope below |
| Home/current work | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite within synthetic scope | Not accepted; no redesign performed | Partial; evidence scope below |
| Application questionnaire | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite | Not accepted; no redesign performed | Partial; evidence scope below |
| Application documents | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite; scan policy controlled | Not accepted; no redesign performed | Partial; evidence scope below |
| Review/declaration/submission | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite; fixture waiver/provider | Not accepted; no redesign performed | Partial; evidence scope below |
| Returned corrections | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Privacy regression + actual API browser suite | Not accepted; no redesign performed | Partial; evidence scope below |
| Payment history/checkout recovery | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API suite; controlled provider output | Not accepted; no redesign performed | Partial; evidence scope below |
| Draft deletion/withdrawal | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite | Not accepted; no redesign performed | Partial; evidence scope below |
| Communications | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite; no live email | Not accepted; no redesign performed | Partial; evidence scope below |
| Testimony appointments | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API coverage; no live email | Not accepted; no redesign performed | Partial; evidence scope below |
| Requests/intake responses | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API browser suite | Not accepted; no redesign performed | Partial; evidence scope below |
| Professional release/assessment response | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API synthetic declaration only | Not accepted; no redesign performed | Partial; evidence scope below |
| Appeal filing/additions | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Actual API/browser; some sibling states fixtures | Not accepted; no redesign performed | Partial; evidence scope below |
| Past cases/released certificates | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Partial API scope; no institutional certificate approval | Not accepted; no redesign performed | Partial; evidence scope below |
| Notifications | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | API coded; combined manual acceptance partial | Not accepted; no redesign performed | Partial; evidence scope below |
| Home dashboard | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only actual API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Cases | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only actual API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Archived | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only actual API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Completeness review | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Backend tests; read smoke not write acceptance | Not accepted; no redesign performed | Partial; evidence scope below |
| Tribunal Sessions/agenda | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke + backend tests; full UI journey pending | Not accepted; no redesign performed | Partial; evidence scope below |
| Case Summary | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only actual API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Timeline | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only actual API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Spouses | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only actual API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Marriage | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | Not implemented | Not accepted; no redesign performed | Partial; evidence scope below |
| Separation | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | Not implemented | Not accepted; no redesign performed | Partial; evidence scope below |
| Petition/notes/findings | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke + backend notes/findings tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Reports/intake/templates | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke + shipped JS payload against PostgreSQL HTTP write/replay/conflict; QA01 separate | Not accepted; no redesign performed | Partial; evidence scope below |
| Recording/transcripts | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Fixture-tested UI; live transcription unavailable | Not accepted; no redesign performed | Partial; evidence scope below |
| Hearings | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke; backend tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Evidence/Documents | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only API smoke; renderer interactions need further acceptance | Not accepted; no redesign performed | Partial; evidence scope below |
| Professional Assessments | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke; backend scope tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Decision & Voting | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke; backend/unit tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Decree | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke; backend lifecycle tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Appeals/later petitions | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read smoke + backend tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Communications/calls | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only API smoke; backend delivery tests | Not accepted; no redesign performed | Partial; evidence scope below |
| Case Audit | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Q Search | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Screen renders; live query not accepted | Not accepted; no redesign performed | Partial; evidence scope below |
| Statistics and Reports | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Read-only API smoke | Not accepted; no redesign performed | Partial; evidence scope below |
| Member profile/history | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | Not implemented | Not accepted; no redesign performed | Partial; evidence scope below |
| My Profile | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Stub | Not accepted; no redesign performed | Partial; evidence scope below |
| Account Settings | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Partial | Partial | Not accepted; no redesign performed | Partial; evidence scope below |
| CTM Settings/account management | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | No complete screen | Not accepted; no redesign performed | Partial; evidence scope below |
| System Audit/security history | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | No complete screen | Not accepted; no redesign performed | Partial; evidence scope below |
| Historical case entry | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | API tested; screen missing | Not accepted; no redesign performed | Partial; evidence scope below |
| Priest report capability page | Defined; exceptions in linked gap review | Planned; full semantic reconciliation open | Partial adapter implemented | Missing | No complete user-facing workflow | Not accepted; no redesign performed | Partial; evidence scope below |

## Interpretation

- Most rows remain partial at feature level even if their unit tests pass. No unsupported 100-percent-complete claim is made.
- Detailed per-row access, data source and module information is in screen-map.json and CSV.
- Read-only council smoke results/screenshots are in evidence/. Screen rendering is weaker evidence than full write/lifecycle acceptance.
- The earlier prototype audit remains the reference for missing factual pages and schema questions (issue14 / PR13).
- Owner shared-fact rule: show marriage/separation shared facts once from first formal filing, flag discrepancies and retain originals. The source-correction rule is still awaiting a decision; these missing views were not invented during integration.
- Main is unchanged. Integration branch commits merge workstreams only here; public release remains separate.
