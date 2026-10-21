# Applicant questionnaire and council record reconciliation

Date: 2026-10-20. Scope: data architecture and requirements only; no prototype UI changes. Current detailed table/permission contracts: `CTM-database-tables.md` and `CTM-permissions.md`. Sources: current `ctm-public/public-petition.html`, dynamic child/clergy controls in `ctm-admin/app.js`, and current council parties, marriage, separation, requisition, summary, document and intake pages. The embedded older reconciliation audit is historical evidence, not a current gap count.

## Agreed architecture

Admin and secretary may edit questionnaire questions and required fields. Both portals use one versioned field-definition catalog and the same applicant-owned answers. A council display is a projection of those answers, not a second form requiring transcription. Council findings remain a separate private record. Both applicants' assertions remain independently attributed, including contradictory answers.

Each published questionnaire version includes English/Arabic labels, semantic field codes, types, choices, conditional rules, requiredness, document rules and council display routing. Submitted applications permanently reference their exact version. An edit to a published version creates a new version; it never rewrites old submissions, labels, choices or signatures. Retiring a question hides it from future versions without deleting old answers. Corrections to a submitted application remain on its original version and preserve field history.

Allow configuration of ordinary question content and requiredness. This is not permission to change person identity keys, applicant ownership, privacy, retention, fee rules or the one-open-case constraint. Changes to existing field meaning or type require a new compatible definition/migration, not reinterpretation of historical values. Questionnaire routing must ensure new questions are visible in council review even if the existing case-page layout has no dedicated slot: a version-driven additional-answers section is the fallback, subject to normal permissions.

## Current field-to-council reconciliation

“Present” means a corresponding current display exists; it does not establish a working backend. “Add to council” and “extend applicant” are later implementation requirements, not work performed on the UI. New fields not already approved are explicitly marked proposed.

| Applicant field / semantic source | Current council destination | Reconciliation requirement |
|---|---|---|
| Account email/password/verification/provider identities | Account administration, not case answers | Keep credentials, tokens and password confirmation out of the council questionnaire; verification is an account prerequisite |
| Applicant first/middle/last names | Parties: combined full name | Store separate components; show combined name plus details/history without losing middle names |
| English-spelled first/last names for ID | No distinct English/Arabic identity slots | Confirmed requirement; bind initials to English components; assigned ID never recomputed after correction |
| Other names known by | Parties: Other Names Known By | Present; preserve structured aliases and submitted value |
| DOB and gender | Parties: DOB/age and gender/name badges | Present; DOB is canonical, age derived; render explicit labels instead of inferring data from icons |
| Place of birth | Parties: Place of Birth | Confirmed country only for both parties; label Country of Birth consistently; no city/town field |
| Nationality | Parties: Nationality | Present; one shared semantic field and equivalent bilingual choices |
| Education, graduation year, occupation | Parties: Career | Present; no second administrative entry |
| Street/city/region/postal/country | Parties: combined Address; Separation: living arrangements | Preserve component answers; reuse the same source revision in both views |
| Immigration status and residing with | Parties; Separation for residence | Applicant fields present; keep applicant assertions separate from council findings |
| Applicant contact email/mobile | Parties: Contact | Present; contact assertion is distinct from current verified account email |
| Denomination, bishop, diocese, parish, confessor | Parties: Church Membership | Present for applicant; retain original submitted names even if directories change |
| Other party aware of application | Parties: respondent awareness | Present; label as reported by the submitter, not verified notification or consent |
| Spouse first/middle/last names, aliases, DOB, gender | Parties: Respondent | Present in combined display; allow confirmed Unknown for missing spouse facts; do not create a fictitious verified account/person |
| Spouse birthplace/nationality | Parties: Respondent personal details | Country of birth only, as confirmed for applicant; Unknown allowed for spouse |
| Spouse address | Parties and Separation | Confirmed addition: spouse country of residence with Unknown allowed; direct address mapping, never default from filer |
| Spouse email/mobile/education/graduation/occupation | Parties | Present; all unavailable spouse details accept Unknown |
| Spouse denomination/diocese/bishop | Parties | Present; preserve source party attribution |
| Spouse parish and Father of Confession | Parties: Respondent > Church Membership | Confirmed additions; explicit Unknown allowed; same applicant-owned answers feed council fields directly |
| Spouse immigration status | Parties: Respondent > Contact | Confirmed addition; Unknown allowed; direct applicant-owned source mapping |
| Spouse currently resides with | Parties/Separation sample displays | Excluded by user: no spouse residing-with question or separate unsourced council field; own-applicant and child questions remain |
| Children: first/last names and DOB | Parties: Children; Summary: names/age | Present; dynamic repeater must preserve stable child-entry UUIDs, not array-position identities |
| Children: gender and resides with | Parties: Children | Confirmed additions to public repeater; require an answer but accept Unknown for either field; age remains derived |
| Married outside Coptic church, outside denomination/date | Marriage: Church Marriage | Present; retain conditional answer states |
| Church marriage date, priest, church name/address | Marriage | Present; derive duration with explicit date basis |
| Marriage certificate number/issue date | Marriage: Marriage Certificate | Present; reference immutable source file version separately |
| Marriage diocese | Marriage council page only | Confirmed questionnaire addition; Unknown allowed; direct ceremony-diocese mapping, no default from current parish/diocese |
| Current marital status/separation date | Separation | Present; display as assertions and do not conflate with civil finality |
| Separation initiated by | Separation council page only | Confirmed addition: Applicant, Spouse, Both, Unknown; relative to author, no inference from who filed |
| Reason/grounds | Summary, Separation, filters | Confirmed structured selection plus required statement; simplified list excludes Imprisonment and adds Misrepresentation / concealment prior marriage; council findings remain distinct |
| Civil divorce filed/date/court/address/reference | Separation: Civil Divorce | Verified existing fields: Date of Civil Divorce, Name of Court and Civil Case Number confirmed required, plus finalized CDD upload; court address requiredness unchanged |
| Civil divorce status | Separation council page only | No added applicant status/date question approved; existing divorce date/court/reference and CDD source feed display; council finding is separate |
| Restraining order filed/date/expiry/name listed | Separation: Restraining Order | Present; retain conditional states and sensitive naming/protection data |
| Restraining order court/reference/status | Separation council page only | Confirmed conditional required fields when an order exists; no Unknown option; applicant assertion distinct from council verification |
| Restraining order copy | Separation/Documents | Confirmed multiple orders, each with separate details and required copy; bind each exact file version to its order before submission |
| Reconciliation attempted | Separation: Reconciliation | Present |
| Repeating priest names | Separation has only the counseling flag; Intake can interview clergy | Confirmed names only; remove prototype role field; same submitted list feeds council review |
| Clergy role/parish/contact/dates/outcome | Prototype has role; other fields were proposed | Excluded from applicant reconciliation repeater: priest name only |
| Prior application yes/no, when, where, outcome | Separation: Prior Application | Confirmed repeating previous applications: date, council/diocese and outcome per entry; may refer to external/pre-CTM records |
| Typed petition statement or PDF/DOCX statement | Requisition: separate requests for each party | Use exact submitted typed text and/or file links; either meets requirement; council-written investigation report is distinct |
| Petition statement on Summary | Summary currently displays overview/milestones, not original narrative | Add link/preview to own-party submitted requisition rather than create another editable summary copy |
| MC church certificate | Marriage/Documents | Mandatory before submission; category MC, not filename guessing |
| CMC civil certificate | Documents | Mandatory before submission; category CMC despite older optional prototype control |
| CDD finalized civil divorce decree | Separation/Documents | Mandatory before submission; distinct from council-issued DEC |
| Applicant photograph | Generic document area; no dedicated clearly categorized view | Mandatory; explicit photo category; not government-issued photo ID |
| Spouse photograph supplied by filer | Generic document area | Upload if available; cannot block submission when unavailable; owned by supplying applicant |
| Other evidence/audio/video/PDF/image/Word | Evidence and Documents | Use one private storage/version subsystem with category-specific links; apply confirmed size and access policies |
| Baptism certificates | Public instructions and sample document fixtures | Excluded: remove production requirements/categories; do not reproduce fixture requirements |
| Accepted declaration language/text version | No complete dedicated council attestation display | Add protected attestation display linked to original submission/version |
| Signer first/middle/last names, drawn signature and date | No complete dedicated council applicant signature display | Add applicant attestation record, not the bishop decree signature; preserve exact original bytes/text/digest |
| Questionnaire version and submission timestamp | Not consistently displayed | Council must be able to identify exact question version, submitting person and server submission time |
| Changed answer/history | No implemented common per-field change model | Confirmed icon/modal for changed field; original/new values, actual editor/time; applicant sees only own history while open |
| Additional configurable questions | No fixed layout slot today | Render from the submission's versioned catalog in the appropriate council section or additional-answers fallback; never discard unrecognized fields |

## Council fields that must not become applicant questions

Case number generation, assignments and assignment history, intake interview time/method/interviewer/duration/notes, hearing scheduling/attendance, investigation recommendations, council findings and notes, votes, decree preparation/approval and internal audit are council/system data. Do not add them to the public questionnaire merely because they appear in the council UI. Age, durations and case counts are calculated, not questions.

An applicant's correction and an administrator/secretary correction target that applicant's answer revision. A council finding does not. Applicant-originated committed changes send the agreed immediate council-portal notices and ten-minute email digest to assigned member/secretary. Staff-originated corrections are recorded silently. Council findings/notes remain council-only.

## Questionnaire configuration database contract

- `questionnaires`: stable questionnaire identity and purpose (petition/response/appeal as approved by later workflows).
- `questionnaire_versions`: version UUID/number, state draft/published/retired, prior version, publisher and server timestamps, exact definition digest.
- `question_definitions`: immutable field identity, semantic code, value type, ownership/sensitivity classification and structured-field storage binding.
- `question_version_definitions`: version-specific question text/localizations, help, requiredness, choices, display/branching rules, ordering and council section routing. Separate stable semantic identity from changing presentation.
- `question_choice_versions`: stable choice codes with versioned English/Arabic labels; old selections retain their original meanings.
- `questionnaire_change_events`: editor, timestamp, affected definitions and prior/new revision references; no history-destroying published edits.
- `question_answer_bindings`: one authoritative destination per core field; configurable extension answers use validated typed storage. No independently editable applicant and council copies.
- `application_submissions`: pin original questionnaire version, declaration version/language, answer revision and required file-version manifest. Later configuration changes never retroactively add missing-required errors to old submissions.

Only council administrator/secretary can edit/publish configuration. Validate unique semantic codes, valid field mappings and choices, bilingual text, resolvable conditional references and safe expressions; no arbitrary SQL/script execution in question rules. Prevent incompatible core-type changes without explicit migration. Apply applicant privacy, no-deletion and no-second-open-case rules outside configurable requiredness.

Confirmed: unfinished drafts update to the new published version with entered answers preserved by stable field/repeat identities. Inform the applicant of newly required questions; preserve migration provenance and do not reset inactivity expiry for administrative migration. Existing submitted versions remain unchanged. Treat this as rare configuration maintenance; reject incompatible publication rather than erase or silently reinterpret an answer. Detailed council/decree processing workflows remain deferred. No form screen or database migration has been implemented.
