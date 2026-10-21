# Prototype to data mapping

Date: 2026-10-20. Read alongside `CTM-data-architecture.md`. Source paths are relative to the workspace. This is a requirements mapping, not an implementation or UI redesign. Current schema and authorization contracts are in `CTM-database-tables.md` and `CTM-permissions.md`; proposed or deferred extensions below are not confirmed new fields. Every top-level page is covered in the page register below; exact extracted page text and static controls are preserved in the inventory.

## Questionnaire dictionary and direct council feed

Every applicant entry below belongs to its own application revision and immutable submission. Council sees it directly with submitting party, source version, and receipt time. Another applicant cannot see it. Names entered about a spouse remain the submitting applicant's assertions, not verified changes to the spouse's person/account. HTML control IDs are not stable business field names.

| Section / field codes | Data type / repeat structure | Authoritative destination | Council use / reconciliation |
|---|---|---|---|
| `account.email`, password, confirmation | Verified email; credential input | `accounts` and maintained auth component | Password confirmation never stored; credentials never in questionnaire snapshots |
| `self.first_name`, `middle_name`, `last_name`, `other_names` | Text; other names may repeat | `application_person_assertions` with immutable revisions | Parties view; keep submitted name separate from current profile |
| `self.dob`, `gender`, `birth_country`, `nationality` | Date; M/F as currently requested; country/text | Same | Parties; confirmed Country of Birth only, no town/locality addition |
| `self.education`, `graduation_year`, `occupation` | Text/catalog; four-digit year or unknown | Same | Parties; no inferred upbringing or population divorce rate |
| `self.address.street`, city, region, postal, country | Structured international address | Same | Parties and separation view; snapshot not live-profile pointer |
| `self.immigration_status`, `residing_with` | Catalog + other/unknown | Same | Sensitive profile assertions; minimize role-visible fields where approved |
| `self.email`, `mobile` | Contact values | Same | Submitted contact distinct from verified account login/safe notification address |
| `self.denomination`, `bishop`, `diocese`, `parish`, `confessor` | Directory FK where verified + submitted text | Same | Parties/church section; directory changes do not rewrite snapshots |
| `spouse.aware_of_application` | Yes/no/unknown with source | Same, subject spouse | A's report is not proof of B notification, account consent, or service |
| `spouse.first_name`, middle, last, aliases, DOB, gender, birth country, nationality | Same types as self | Same, subject spouse | Council comparison; staff verifies identity before linking stable person |
| `spouse.address.street`, city, region, postal; confirmed country of residence | Address; unknown allowed | Same | Add confirmed spouse country of residence; Unknown allowed; do not guess from A |
| `spouse.email`, mobile, education, graduation_year, occupation | Same as self; conditional availability | Same | Not a B credential or verified contact |
| `spouse.denomination`, diocese, bishop; confirmed parish/confessor/immigration_status | Text/catalog + explicit Unknown | Same | Confirmed added spouse fields map directly to council; spouse residing_with excluded |
| `children[].first_name`, last_name, DOB | Repeating names/date | `application_children` | Dynamic `DF.addChild` has these three fields |
| Confirmed `children[].gender`, `residing_with` | Required answer per child; explicit Unknown accepted for each | `application_children` | User clarified YES: collect alongside name and DOB; council receives the same applicant-owned assertions |
| `marriage.outside_coptic`, outside denomination/date | Conditional yes/no + text/date | `application_marriage_assertions` | Marriage facts reviewed into ceremony records, preserving testimony |
| `marriage.church_date`, officiating_priest, church_name, location | Date/text/directory | Same | Marriage view; marriage duration derived using stated date basis |
| `marriage.certificate_number`, certificate_issued_date | Text/date | Same | Not a substitute for document version and review |
| Confirmed `marriage.diocese` | Text/directory with explicit Unknown | `application_marriage_assertions` | Directly feeds council ceremony Diocese; no inferred current-diocese value |
| Civil ceremony date/location beyond current questions | Deferred; no new question approved | Source document or later workflow design | Not an added core-table applicant field; retain source evidence without inferring facts |
| `separation.marital_status`, date | Catalog/date | `application_separation_assertions` | Preserve distinction between still married, separated and civil divorce finality |
| Confirmed `separation.initiated_by` | Applicant/spouse/both/Unknown, relative to application author | Same | Add questionnaire question; direct source for council Initiated By |
| `civil_divorce.filed`, divorce_date, court, court_location, case_number | Conditional fields; dates/text | Same | Do not conflate filing date with finalization date; label explicitly |
| Civil divorce finality display | Existing Date of Civil Divorce + required CDD; no extra date/status questions approved | `application_separation_assertions`, submitted file manifest and separate council finding | Do not infer council-verified finality from an upload; existing date/court/reference required |
| `restraining_order.filed`, date, expiration_date, name_listed | Conditional repeating orders | `application_restraining_orders` | Sensitive, record named/protected/restrained roles explicitly once known |
| Confirmed `restraining_order.court`, case_number, status; court_location separately proposed | Conditional required actual values; no Unknown for confirmed fields | Same | Direct council field mapping; verification remains council work |
| `counseling.attempted`, `clergy[].name` | Yes/no + repeating contacts | `application_separation_assertions` and `application_counseling_priests` | Confirmed priest name only; prototype role input excluded |
| Excluded clergy role/parish/dates/outcome/contact | Not collected in applicant repeater | No applicant question fields | Priest name only; council interviews/reports remain separate |
| `prior_application.applied`, when, where, outcome | Conditional external proceeding | `application_prior_proceedings` | Confirmed repeatable prior applications; date, council/diocese and outcome per entry |
| `summary.narrative`, petition statement document | Nonblank text OR accepted PDF/DOCX file-version link; either satisfies requirement | `application_statements`; private file-version links | Requisition per party and read-only council source; council recommendation is separate |
| Confirmed selected grounds | Multiple approved ground-version links plus typed/uploaded statement | `application_selected_grounds` | All source selections feed council; findings remain separate |
| `documents.applicant_photo`, spouse_photo, church_certificate, civil_certificate, civil_divorce_decree | Category + immutable file versions | `files`, `file_versions`, `application_file_links` and immutable manifests | Named document categories replace generic filename-only lists; photo is not photo ID |
| Conditional restraining orders, counseling/grounds evidence; baptism certificates excluded | Versioned requirement rules | `document_requirements` and file links | Baptism certificates are confirmed not needed; other categories remain subject to their approved requirements |
| `consent.accepted`, declaration language/version | Boolean acceptance + immutable text version/digest | `application_attestations`, `declaration_versions`, `declaration_texts` | Council needs attestation record even though no dedicated current council consent page exists |
| `signature.first`, middle, last, drawn signature, date | Signed name/date + file-version bytes | `application_attestations` | Bind to final submission digest and server received time; no reusable public signature |

Proposed additions are requirements for review, not modified prototype fields. If a fact is unavailable about the spouse, use an explicit unknown answer; do not make applicants fabricate it. Requiredness and branching are frozen by questionnaire version, including “Other” free-text details and validation of date order. Technical upload safety is checked server-side, not inferred from the prototype's green selected-file badge; there is no manual council acceptance gate.

## Council operational data that must stay internal

Intake, investigation, hearings, sessions, votes and decree rows below describe prototype evidence and reserved workflow boundaries. They do not approve detailed tables, status transitions or writer roles; see the deferred group in `CTM-database-tables.md`.

| Source module | Captured/generated data | Destination |
|---|---|---|
| Summary | Case creation/filing dates, stage, responsible member, derived marriage duration, hearing dates, milestones | `cases`, assignment/stage events and read projections; no second independent summary record |
| Intake | Interviewed person, interviewer, in-person/phone/virtual method, date/time, location, duration, rich notes, upload, OCR action | Deferred intake interview/version boundary with typed private file links; no workflow approval |
| Requisition | Separate A/B written petitions and attachments | `application_statements`, `application_submissions` and file manifests; council investigation report is a deferred separate boundary |
| Evidence/documents | Name, media type, size, created/received date, user, category, preview and download; script fixtures include MP3 | Private file/version/link tables; evidence review and custody events; audio supported alongside requested video |
| Notes | Title, body, author, date/time and revision | `case_notes`, `case_note_versions`; council only |
| Hearings | Session selection, type, case stage, attendance, testimony/notes, recommendation/outcome, historical hearings | Deferred hearings/roster/attendance boundary; no cross-applicant testimony access |
| Sessions | Date/time/location, presiding/secretary, upcoming/in-progress/completed, assignment agenda, hearing order, roll call, session summary/minutes | Council sessions/agenda/rosters/attendance/minutes; distinguish authentication sessions |
| Votes | Member, approve/deny/abstain, tally, recorder | Deferred decision/vote boundary; no inferred majority/quorum rule or approval authority |
| Decision | Category/outcome, rationale, A/B permission, conditions, deferral/withdrawal/reconciliation | Versioned outcomes, decisions, dispositions, conditions; a final decision closes the case; detailed procedural effects deferred |
| Decree | Preamble, findings, canonical basis, statement, conditions, bishop signature, issued PDF, notification | Versioned decree sections/templates, approvals and issuances; issued content frozen |
| Communications | Inbound/outbound email history, recipient, subject/body, call party/date/duration/notes, acknowledgments | `case_correspondence`, `correspondence_recipients` and routed reply history; no private portal chat |
| Timeline/audit | Business milestones vs actor, role, action, target, time and change | Timeline projection vs private append-only audit; no internal audit dump to applicants |
| Members/accounts | Titles, names, phone/email, appointment/member-since, role/status, assigned/closed counts, departure reason, portrait, passwords/sessions | Persons, directory, staff memberships, auth component and private profile files; counts derived |
| Admin | Role matrix, diocesan settings, grounds, stages, outcomes, templates, exports, purge, security and mobile preferences | Versioned policy/settings and explicit grants; exports and case purge excluded; mobile toggles never access control |
| Reports/search/archive | Filters, counts, workload, aggregate outcomes, closed dates, document text, advanced cross-module search | Authorized queries/views/jobs; archive not deletion; no invented sample statistics |

## Future marriage module inventory

The Holy Crowning portal is not ignored; it is explicitly deferred. `public-crown-cert-impediment.html` includes Arabic-name components, parents' names, marital/engagement/widow history, prior marriage types, remarriage permit council/date/reference, spiritual attendance/communion/confession, church meetings, confessor/parish, certificate coverage period, parishioner declaration/signature, photo and government ID. Several portions are marked completed by priest and need separate future authorship permissions.

`public-crown-consanguinity.html` includes relationship-by-blood-or-marriage, relationship description, declaration acceptance, name/date/signature. `public-crown-guidelines.html` includes versioned guideline acknowledgments and aggregate completion; these are not boolean attributes on the CTM case. `public-crown-dashboard.html` includes ordered steps for certificate, consanguinity, engagement and guidelines. Engagement has a dashboard placeholder but no actual standalone form file in this prototype. The future Crown login is source evidence only; CTM applicant Google/Apple/password sign-in is separately confirmed in the decision register.

Future entities: marriage-preparation applications and parties, priest attestations, no-impediment certificates and coverage, prior-union assertions, consanguinity declarations, engagement events/documents, guideline versions and per-person acknowledgments. Share stable person/directory links; exchange only approved per-person CTM permission disposition, never tribunal evidence.

## Full page register

The generated register following this section assigns every top-level HTML page to its business boundary. Static controls include buttons and filters, not just persisted fields. The separate raw inventory intentionally retains prototype text, including outdated statements, for traceability.


| Source | Static controls | Boundary / storage responsibility |
|---|---:|---|
| `ctm-public/public-about.html` | 0 | Public content and council role descriptions; versioned content, not authoritative staff appointments |
| `ctm-public/public-admin-signin.html` | 3 | Staff authentication and recovery; accounts/auth_events |
| `ctm-public/public-apply.html` | 0 | Eligibility, document requirements and fee mention; versioned intake policy |
| `ctm-public/public-contact.html` | 6 | Public inquiries; not case/evidence intake |
| `ctm-public/public-crown-cert-impediment.html` | 64 | Future marriage preparation; deferred separate context |
| `ctm-public/public-crown-consanguinity.html` | 8 | Future marriage preparation; deferred separate context |
| `ctm-public/public-crown-dashboard.html` | 0 | Future marriage preparation; deferred separate context |
| `ctm-public/public-crown-guidelines.html` | 101 | Future marriage preparation; deferred separate context |
| `ctm-public/public-crown-login.html` | 3 | Future marriage preparation; deferred separate context |
| `ctm-public/public-ctm-home.html` | 0 | Service navigation; no applicant data model |
| `ctm-public/public-determinations.html` | 0 | Public outcome explanations; versioned approved content/catalog |
| `ctm-public/public-dissolution-home.html` | 0 | Public tribunal entry and grounds copy; policy catalog |
| `ctm-public/public-faq.html` | 17 | Versioned eligibility/required-document/process content |
| `ctm-public/public-matrimony.html` | 0 | Future marriage information boundary |
| `ctm-public/public-petition.html` | 127 | Applications, structured assertions, repeats, uploads, declarations and signatures |
| `ctm-public/public-process.html` | 0 | Versioned public process instructions |
| `ctm-public/public-reconciliation-audit.html` | 0 | Historical field audit; not current truth or production public content |
| `ctm-public/public-signin.html` | 3 | Applicant authentication and recovery |
| `ctm-admin/admin-archived.html` | 2 | Closed case queries/archive attributes and retention |
| `ctm-admin/admin-case-audit.html` | 3 | Private audit events and actor/target provenance |
| `ctm-admin/admin-case-communications.html` | 15 | Case correspondence, party recipients, email/call history |
| `ctm-admin/admin-case-decree-view.html` | 0 | Immutable issued decree, approvals and private PDF |
| `ctm-admin/admin-case-decree.html` | 57 | Votes, decisions, per-party dispositions, decree templates/issuance and notices |
| `ctm-admin/admin-case-documents.html` | 1 | Categorized private file versions and source ownership |
| `ctm-admin/admin-case-evidence.html` | 1 | Evidence records, files, audio and chain of custody |
| `ctm-admin/admin-case-hearings-2.html` | 11 | Alternative unassigned hearing state; same hearings model |
| `ctm-admin/admin-case-hearings.html` | 10 | Hearings, attendance, session link and outcome history |
| `ctm-admin/admin-case-intake.html` | 19 | Interviews, interviewer/subject, notes, attachments/OCR |
| `ctm-admin/admin-case-marriage.html` | 3 | Marriage assertions, ceremonies and certificates |
| `ctm-admin/admin-case-notes.html` | 2 | Internal versioned notes; never shared-party feed |
| `ctm-admin/admin-case-parties.html` | 1 | People, private per-party assertions, contacts/church affiliation, children |
| `ctm-admin/admin-case-requisition.html` | 4 | Per-party petitions/narratives and source files |
| `ctm-admin/admin-case-separation.html` | 3 | Separation/civil proceedings/orders/counseling/prior cases |
| `ctm-admin/admin-case-summary.html` | 0 | Authorized case overview projection, milestones/assignment |
| `ctm-admin/admin-case-timeline.html` | 3 | Private business-event timeline projection |
| `ctm-admin/admin-cases.html` | 8 | Case creation/list, filtered queries and open-case invariants |
| `ctm-admin/admin-index.html` | 9 | Derived dashboard/session/case workload and analytics |
| `ctm-admin/admin-management.html` | 67 | Staff/permissions, policy/template versions and audit/security; export and purge excluded |
| `ctm-admin/admin-member.html` | 0 | Membership history and derived case responsibility workload |
| `ctm-admin/admin-reports.html` | 6 | Authorized aggregate queries; export excluded by user |
| `ctm-admin/admin-search.html` | 13 | Scoped cross-case search with no unauthorized snippets/counts |
| `ctm-admin/admin-session-summary.html` | 23 | Historical agenda, attendance, recommendations and approved minutes |
| `ctm-admin/admin-sessions-historical.html` | 2 | Session history queries |
| `ctm-admin/admin-sessions-upcoming.html` | 10 | Agenda, assignments, hearings and start-session attendance |
| `ctm-admin/admin-sessions.html` | 16 | Session calendar/history, independent session identifier |
| `ctm-admin/admin-support.html` | 0 | Placeholder support content; no business subsystem established |
| `ctm-admin/admin-user-account.html` | 19 | Staff profile, authentication sessions, preferences and activity |
| `ctm-admin/consolidation-preview.html` | 1 | UI experiment only; no production business entities |
| `ctm-admin/design-preview.html` | 6 | UI experiment only; no production business entities |
