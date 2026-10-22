# Full UI workstream reconciliation

[Download JSON](ui-full-reconciliation.json) | [Prototype control evidence](ui-prototype-controls.json)

All 45 mapped destinations are reconciled below. This completes the screen-register review, not the product implementation or full UI acceptance. Each row retains the original seven-stage scope from the historical map and adds current source/evidence and exact dependency identifiers. Missing API/content contracts are not marked completed; existing APIs do not excuse unfinished UI.

Runtime prototype coverage:42 in-scope HTML pages,855 controls inventoried,47 safe visible tabs/dialogs/disclosures exercised,7 conditional/repeat interactions. The entire DOM includes hidden controls; revealed controls are separately recorded. Submit/send/delete/export/payment/provider actions were excluded; Crown/future screens and design experiments were excluded. No prototype password/idle-timeout/purge controls were imported as requirements.

## Screen register

| ID | Screen | UI controls reviewed | Remaining / dependency IDs |
|---|---|---|---|
| UI-01 | Sign-in | Provider entry/routing and unavailable provider states; no CTM password UI. | Live identity/provider acceptance remains. **AUTH** |
| UI-02 | Home/current work | Current filing/case priority and navigation. | Applicant dashboard/action acceptance remains with issue1. **APPLICANT** |
| UI-03 | Application questionnaire | Section navigation, conditional questions, repeat rows and validation. | Latest repeat-condition renderer must be integrated; approved field coverage is not published. **APPLICANT, FORM** |
| UI-04 | Application documents | Contextual file slots, upload state and original/version access. | Large upload/device/storage acceptance remains. **FILES** |
| UI-05 | Review/declaration/submission | Review/declaration, paid-or-waived submission and recovery states. | Approved declaration and live payment acceptance remain. **FORM, PAYMENT** |
| UI-06 | Returned corrections | Returned correction editing, history presentation and resubmission. | Exact latest applicant modules and full field-history visual acceptance remain. **APPLICANT, FORM** |
| UI-07 | Payment history/checkout recovery | Payment list, expiry/recovery and retry states. | Actual receipts/refunds/callback and delivery acceptance remain. **PAYMENT** |
| UI-08 | Draft deletion/withdrawal | Draft removal/withdrawal confirmation and error states. | Combined institutional acceptance remains; no submitted-case purge. **APPLICANT** |
| UI-09 | Communications | Own private thread, composer, read receipts and load-more. | Inbound delivery and attachment-return acceptance remain. **COMM** |
| UI-10 | Testimony appointments | Appointment invitations, confirm/reject and explanation. | Real invitation delivery/device acceptance remains. **DELIVERY** |
| UI-11 | Requests/intake responses | Own requests and responses with bound question/file context. | Approved templates and live response delivery remain. **FORM, DELIVERY** |
| UI-12 | Professional release/assessment response | Own scoped release and assessment upload states. | Institutional signed release wording and real scan acceptance remain. **RELEASE, FILES** |
| UI-13 | Appeal filing/additions | Appeal filing/additions and saved/submitted states. | Latest validation modules and full two-spouse journey acceptance remain. **APPLICANT, PAYMENT** |
| UI-14 | Past cases/released certificates | Own past cases and explicitly released certificates. | Institutional signed PDFs and revocation/access acceptance remain. **CERT, FILES** |
| UI-15 | Notifications | Own notifications, read state, paging and target navigation. | Latest applicant inbox integration and actual delivery/template acceptance remain. **APPLICANT, DELIVERY** |
| UI-16 | Home dashboard | Upcoming session, attention and assigned-work sections. | Outstanding request/prior summary/latest submission sections require dashboard projections; assigned-case identity needs stable IDs. **DASHBOARD, PAGING** |
| UI-17 | Cases | Table/detail, search, assignee/status columns and keyboard entry. | Filtered-out actionable preview fixed. Operational queues and spouse/factual columns require projections; full list inaccessible past server cap. **PAGING, FACTS** |
| UI-18 | Archived | Closed table/detail, search and assignee/status columns. | Full closure/outcome columns and all-record navigation require server fields/continuation. **PAGING, FACTS** |
| UI-19 | Completeness review | Completeness reader, accept/return dialog and mandatory explanation. | Full combined reviewer/applicant lifecycle/visual acceptance remains with council/applicant QA. **COUNCIL** |
| UI-20 | Tribunal Sessions/agenda | Table/detail, upcoming/past/date filters, create/reschedule/close, attendance and two agenda tables. | Attendance/table/filter regressions fixed; timing/location/presiding/minutes projections and all action-journey acceptance remain. **SESSION, PAGING, COUNCIL** |
| UI-21 | Case Summary | Case/assignee, spouse/proceeding and pending request/decision links. | Shared factual overview/children/key dates cannot be reconstructed from private drafts or guessed question codes. **FACTS** |
| UI-22 | Timeline | Business milestones and assignment history. | Marriage/family chronology and filters depend on factual projection; audit is not a substitute. **FACTS** |
| UI-23 | Spouses | Spouse identity/reference/registration and authorized second-party entry. | Rich personal details, children, portrait and discrepancy projection missing from authorized case response. **FACTS, ACCOUNT** |
| UI-24 | Marriage | Missing structured shared marriage view and contextual documents; navigation remains disabled. | Implement when first-formal-source facts/provenance/discrepancy contract is supplied; do not fabricate fields. **FACTS** |
| UI-25 | Separation | Missing shared separation/divorce/repeated-orders view and contextual documents; navigation remains disabled. | Implement with authorized factual/document projection and source correction rule. **FACTS** |
| UI-26 | Petition/notes/findings | Attributed petitions, notes/history and findings read. | Approved fact-code creation and complete contextual evidence mapping remain. **FACTS, FORM, COUNCIL** |
| UI-27 | Reports/intake/templates | Report/request tabs, question/template filters, revisions/history and selected reader. | Council S10/C-02 fixes require serial integration and QA15; external priest metadata/delivery remain. **COUNCIL, EXTERNAL** |
| UI-28 | Recording/transcripts | Recorder, original playback, recovery, transcript/version/retry surfaces. | Council issue3 owns active D20 status/view/correction/retry implementation against existing APIs; worker unavailable is not a UI blocker. **D20** |
| UI-29 | Hearings | Selected hearing/session details and existing outcome/testimony dialogs. | All dialog/lifecycle acceptance and richer session metadata remain. **SESSION, COUNCIL** |
| UI-30 | Evidence/Documents | Safe-file list/version/load-more, selection and media/browser PDF fallback. | Context links depend on factual pages; embedded PDF remains CDN defect; live range/scan/OCR acceptance remains. **FACTS, FILES, CDN** |
| UI-31 | Professional Assessments | Separate requests/reports, restricted status, release-aware reads and composer. | Signed release wording, recommendation workflow and actual disclosure acceptance remain. **RELEASE, COUNCIL** |
| UI-32 | Decision & Voting | Decision form, full roster/tally, approval and earlier versions. | Full real approval journey and approved Arabic type labels remain; preserve existing version fixes. **COUNCIL, FORM** |
| UI-33 | Decree | Signed PDF upload/attestation, issuance/closure, explicit release/withdrawal and structured read. | Type-specific approved template authoring/generation service and institutional certificate acceptance remain. **CERT, COUNCIL** |
| UI-34 | Appeals/later petitions | Appeal/later-filing selection, statements/additions, fee/result and hearing links. | Complete actual two-spouse reopened/decree cycle acceptance remains. **COUNCIL, APPLICANT** |
| UI-35 | Communications/calls | Selected message, composer and manual calls. | Subject/contact/external recipient/inbound/duration fields are not in current mutation/read contract. **COMM** |
| UI-36 | Case Audit | Search, actor/action/source/date filters, reset and selected target context. | Structured filters restored; all-record pagination and richer target projection still need backend continuation. **PAGING** |
| UI-37 | Search | POST phrase, history option, keyboard result selection and accurate initial/loading/empty/error states. | Unified case/person/session results and advanced facets are absent from document search contract. **SEARCH** |
| UI-38 | Statistics and Reports | Operational counts/workload and explicit cap limitation. | Period/metric/outcome aggregate APIs and approved denominators required for full reporting; no fabricated charts. **METRICS, PAGING** |
| UI-39 | Member profile/history | Active council directory and selected role/capabilities now implemented. | Member contact/photo/appointment/departure and current/past assignment history require authorized projection. **MEMBER, ACCOUNT** |
| UI-40 | My Profile | Actual signed-in name/email/role/portal/languages and settings link now implemented. | Profile/contact/photo editing and own activity require account contract. No hardcoded portraits/people. **ACCOUNT** |
| UI-41 | Account Settings | Own interface/notification preferences and authenticated identity navigation. | Provider email verification/link/security/session management lack endpoints. Superseded CTM password/SMS/idle controls excluded. **ACCOUNT** |
| UI-42 | CTM Settings/account management | Admin/secretary directory/configuration reads, admin-only enrollment and explicit save errors now implemented. | Role/status lifecycle, previous members, settings-specific validated editing and provider-secret inventory remain dependencies. **MEMBER, CONFIG, ACCOUNT** |
| UI-43 | System Audit/security history | Role-gated system audit table/detail, action/source/date filters and reset now implemented. | No actor/session/login/security payload is returned; full audit paging and session revocation need contracts. **ACCOUNT, PAGING** |
| UI-44 | Historical case entry | Admin-owned stage/resume/version-conflict/publish form with original references and unknown-data preservation now implemented. | Richer factual/file historical capture and discoverable owned-workspace listing require API projection; no invented account associations. **HISTORICAL** |
| UI-45 | Priest report capability page | External priest response page is absent; no fake signed-in substitute created. | Public shell route/token-delivery contract needed alongside existing bearer-protected external JSON endpoint; preserve 30-day scope/reissue/lock rules. **EXTERNAL** |

## Status and acceptance boundaries

- Completed and pushed before this pass:554dcf6 and earlier PR19 checkpoints (navigation, split workspaces, header/logo, attendance/agenda, responsive case navigation, Search states).
- Implemented in this pass: API-backed account identity/admin directory/configuration reads/enrollment/system audit; structured case audit filters/target context; session status/date filters; filtered-out preview correction; versioned historical stage/resume/publish; own unsaved input guards. Test evidence and final commit are recorded on issue4/new successor PR after validation.
- Unfinished/blocked items remain per-row above. Dependency contracts and owners are listed in ui-dependencies.md; owning-stream work is not duplicated or claimed as delivered by UI.
- Awaiting acceptance: serial integration of this successor (PR19 was already merged by governance) preserving newer council/applicant/backend changes, exact successor SHA PostgreSQL/API acceptance, institutional content approval and full EN/AR/device/action review. Synthetic and isolated SQLite results are distinct evidence.
- No main merge, deployment, operational migration, provider credentials or design-system pin changes.

## Validation of this expanded UI pass

- 236 frontend tests passed, including stable account-ID assignment matching, role gates, Los Angeles date bounds, session filtering, enrollment validation, retained historical metadata and malformed saved-payload rejection.
- 14 focused Django shell/account tests passed on isolated SQLite.
- Actual Django/SQLite browser acceptance (no API interception): admin account identity, enrollment and roster refresh, configuration reads, filtered system audit, historical stage/save, stale-version409 without losing typed changes, explicit discard/reload, resumed update, confirmed publish, retained identifiers, immutable readable published view and Open case. Member/applicant system access returns403. Test database/media are unique disposable paths; no live data touched.
- Synthetic browser acceptance:10 role/language combinations for profile/admin gating, enrollment validation and payload, long configuration text and unsaved navigation; English/Arabic phone/desktop case views and session sizes; independent main/case navigation; all14 split destinations; Search lifecycle/Enter selection; case/session/audit filters and duplicate-date protection; attendance/agenda actions and cancellation of assignment/reschedule/close dialogs; native header identity/avatar/fallback.
- Prototype runtime inventory:42 pages,855 controls,47 safe open/tab/disclosure triggers,7 conditional/repeat triggers. This does not mean855 controls were executed or that all hidden combinations were exhausted. Read source evidence and rejected-control exclusions alongside runtime results.
- Code review found one historical metadata loss case; fixed with a failing-then-passing regression. No other concrete review findings were reported. The test harness's local WSGI backlog was enlarged for the shell's parallel static requests; no product/server capacity or database setting was changed.
- Representative Arabic phone administration/configuration and English published-history screenshots were visually inspected. Long retained names are shown as readable properties after publication, rather than clipped disabled inputs. Selection prompts now distinguish an existing list with nothing selected from an actually empty list.

All results are scoped to this UI branch based on0b10a61. Current governance backend/applicant/council changes are included in that base; further successors remain separately owned. UI-24/25 factual views, richer account/history/configuration/contracts, external priest shell, metrics and listed CDN/content dependencies remain incomplete; this report does not mark the full product/UI assignment complete.

Current successor verification: case row highlight persists after focus leaves the table; session uses CDN default RecordPage.Header in EN/AR at390/768/1253. Browser error reported on18844 was undefined CTMShell.Table in an older already-loaded0.58 shell; current template loads shell-layout.js before council.js. No live reload/deployment was performed.
