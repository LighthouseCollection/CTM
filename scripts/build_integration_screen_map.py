"""Publish an evidence-qualified screen inventory, not a completion percentage."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/implementation/integration'
OUT.mkdir(parents=True, exist_ok=True)
ROWS = []

def screen(portal, name, module, implemented, missing, working, access, source, gap=''):
    ROWS.append(dict(portal=portal, screen=name, source_module=module,
        implemented=implemented, remaining=missing, access=access, data_source=source,
        workflow='Defined; exceptions in linked gap review', schema='Planned; full semantic reconciliation open',
        database='Partial adapter implemented', coded='Missing' if module=='None' else 'Partial',
        working=working, UI='Not accepted; no redesign performed',
        testing_QA='Partial; evidence scope below', gap_ids=gap))

screen('Shared','Sign-in','app.js + allauth','Universal entry, provider routing; genuine Microsoft local review setup retained',
 'Live Google/Apple and production Microsoft acceptance; full identity/role reconciliation','Microsoft previously verified; integrated root HTTP200',
 'Public login; preauthorized council identity','Account/identity provider')
screen('Applicant','Home/current work','app.js','Current filing or open case prioritized','Full approved dashboard/action completeness',
 'Actual API browser suite within synthetic scope','Own account','Own applications/cases')
screen('Applicant','Application questionnaire','applicant.js','Versioned editing, conditional fields, explicit saving, draft checklist/requirements',
 'Full approved bilingual form content and exact prototype field mapping','Actual API browser suite','Own application','QuestionnaireVersion/AnswerRevision','PA28')
screen('Applicant','Application documents','applicant-files.js','Contextual originals, replacements, safe-file states and interrupted-upload guard',
 'Live ClamAV/storage and large resumable uploads','Actual API browser suite; scan policy controlled','Own attachments','Attachment/FileVersion/scan events','PA25')
screen('Applicant','Review/declaration/submission','applicant-filing.js','Review, declaration binding, version/fee gating and formal submission',
 'Institutional declaration approval and live payment callbacks','Actual API browser suite; fixture waiver/provider','Own filing','Submission/CheckoutIntent/FeeObligation')
screen('Applicant','Returned corrections','applicant.js + filing','Original submission retained; private saved corrections and resubmission',
 'Full field-history presentation acceptance','Privacy regression + actual API browser suite','Own answers; council formal snapshots only','CompletenessReview/AnswerRevision/Submission')
screen('Applicant','Payment history/checkout recovery','applicant-payments.js + recovery','Own events/receipts, original checkout binding, expiry and safe resume',
 'Real Stripe receipts/refunds/reversals and delivery acceptance','Actual API suite; controlled provider output','Own obligations/attempts','FeeObligation/PaymentEvent/CheckoutIntent')
screen('Applicant','Draft deletion/withdrawal','applicant-lifecycle.js','Capability/version checks, explicit confirmation and recovery',
 'Combined institutional workflow acceptance','Actual API browser suite','Own permitted filing only','Application/party withdrawal state')
screen('Applicant','Communications','applicant-messages.js','Private send/history/read receipt, pagination, idempotency and recovery',
 'Actual SMTP/inbound reply/attachment-return integration','Actual API browser suite; no live email','Own spouse-specific channel','Message/MessageRecipient/Outbox','PA21')
screen('Applicant','Testimony appointments','applicant-appointments.js','Private invitations, confirm/reject and optional rejection explanation',
 'Live invitation/reminder delivery and devices','Actual API coverage; no live email','Own appointments','TestimonyAppointment/versions/responses')
screen('Applicant','Requests/intake responses','applicant-requests.js + responses','Own bound questions, scoped evidence, response receipts/replay',
 'Full approved templates and actual mail delivery','Actual API browser suite','Own sent requests','ReportRequest/ReportRevision')
screen('Applicant','Professional release/assessment response','applicant-assessments.js','Explicit bound declaration/scope, separate consent file and assessment response',
 'Institution-approved signed release wording and live scan acceptance','Actual API synthetic declaration only','Own request/subject scope','MedicalRelease/ReportRequest/files')
screen('Applicant','Appeal filing/additions','applicant-appeals.js + supplements','Draft/start, paid-or-waived submission, own history/additions/replay',
 'Full real later-petition and council disposition journey','Actual API/browser; some sibling states fixtures','Own appeal; other spouse private','Application/AppealSupplement/Disposition')
screen('Applicant','Past cases/released certificates','applicant-decrees.js + app.js','Closed-case list and current recipient release reader',
 'Actual signed institutional certificates and full access/revocation acceptance','Partial API scope; no institutional certificate approval','Own cases and explicitly released certificate','Case/Decree/DecreeRelease')
screen('Shared','Notifications','app.js','Own notification list and read-state controls','Live delivery/template/language completeness',
 'API coded; combined manual acceptance partial','Own notifications','Notification/Outbox')
screen('Council','Home dashboard','council.js CouncilHome','Upcoming dates, review/unread/consideration counts and own cases',
 'Outstanding requests, fuller session context/prior summary, workload/recent submissions and visual acceptance',
 'Read-only actual API smoke','All council; role-scoped actions','Dashboard/cases/notifications','PA10')
screen('Council','Cases','council.js CasesTable','Sortable/pageable returned-array table and case opening',
 'Spouse/factual columns, operational tabs, advanced filters and server pagination','Read-only actual API smoke','All council submitted cases','GET cases capped100','PA07 PA08')
screen('Council','Archived','council.js CasesTable','Closed case list and read navigation','Richer outcome/closure columns and complete pagination',
 'Read-only actual API smoke','All council','Closed Case list','PA07 PA08')
screen('Council','Completeness review','council.js ReviewWorkspace','Submitted queue, formal answers/files, return instructions and accept',
 'Full combined reviewer/applicant visual acceptance','Backend tests; read smoke not write acceptance','Authorized reviewer; submitted filings only','Submission/CompletenessReview')
screen('Council','Tribunal Sessions/agenda','council.js SessionList/Workspace','Assignment/hearing phases, attendance, reschedule, testimony and carryover',
 'Session metadata, richer historical filters, complete summary/minutes decisions','Read smoke + backend tests; full UI journey pending',
 'Council read; authorized session writers','CouncilSession/Agenda/Attendance/Hearing','PA16 PA17 PA18')
screen('Council','Case Summary','council-case.js CaseSummary','Status, assignee, spouses, proceeding, requests and decision links',
 'Filing/grounds/marriage/children/last hearing/key-date factual summary','Read-only actual API smoke','Council','Case detail/requests/decision','PA05')
screen('Council','Timeline','council-case.js CaseTimeline','Audit milestones and assignment history','Marriage/family chronology, factual dates and filters',
 'Read-only actual API smoke','Council','Audit/assignment history','PA06')
screen('Council','Spouses','council-case.js CaseParties','Names, reference, registration and authorized add-spouse form',
 'Rich sourced personal facts, children and accepted shared-fact discrepancy projection','Read-only actual API smoke','Council; admin/secretary onboarding per current contract','Case parties; profile assertions not projected','PA03 PA04')
screen('Council','Marriage','None','Navigation label only, disabled','Full shared-fact view, discrepancy flags and contextual documents',
 'Not implemented','Council view; source-specific correction policy','Marriage/application assertions; projection missing','PA01 PA25')
screen('Council','Separation','None','Navigation label only, disabled','Full separation/civil divorce/repeated orders/prior-records and discrepancy view',
 'Not implemented','Council view; source-specific correction policy','Separation/repeat assertions; projection missing','PA02 PA25')
screen('Council','Petition/notes/findings','council-case.js PetitionWorkspace','Formal questionnaires and internal notes/history; findings read',
 'Approved fact-code finding creation and full contextual evidence',
 'Read smoke + backend notes/findings tests','Council read; permitted case writers','Application/Submission/CaseNote/Finding','PA25')
screen('Council','Reports/intake/templates','council-case.js + council-media.js','Template/category selection, questions, requests, report reader and author revision UI',
 'Reaccept revision UI against latest expected_version contract; full report metadata and external priest workflow',
 'Read smoke; PostgreSQL revision tests; QA01 separate','Council read; original authorized author writes','ReportRequest/Report/ReportRevision','PA19')
screen('Council','Recording/transcripts','council-media.js','Whole-report recorder/local recovery and original playback; status placeholder',
 'D20 status/review/retry UI wiring, real worker, server streaming, device/long-audio acceptance',
 'Fixture-tested UI; live transcription unavailable','Council only; scoped reviewer','Recording/ProcessingRun/Transcript')
screen('Council','Hearings','council-case.js + council.js','Agenda appearances, presenter/attendance/outcome and applicant update',
 'Combined real full session/decision journey and metadata','Read smoke; backend tests','Assigned presenter and authorized writers','Agenda/Hearing/Outcome','PA16')
screen('Council','Evidence/Documents','council-media.js','Split read/view, image/audio/video and browser-native PDF fallback',
 'CDN embedded PDF repair; live safe-file range/playback/OCR acceptance; missing factual-page contexts',
 'Read-only API smoke; renderer interactions need further acceptance','Council authorized sources','Attachment/FileVersion/context','PA25')
screen('Council','Professional Assessments','council-case.js AssessmentsWorkspace','Separate requests/scope-gated read','Approved signed release text, recommendations workflow and real acceptance',
 'Read smoke; backend scope tests','Council with release scope; authorized writers','MedicalRelease/ReportRequest')
screen('Council','Decision & Voting','council-case.js DecisionWorkspace','Catalog/grounds/named entitlements, roster/votes/approval/history',
 'Full combined decision approval journey and approved Arabic labels','Read smoke; backend/unit tests','Council reads; server-authorized votes/approval','DecisionRevision/Vote/PresidentialApproval')
screen('Council','Decree','council-decree.js','Signed PDF upload/signature record/issue/release/withdraw access',
 'Approved type-specific templates and certificate authoring/generation','Read smoke; backend lifecycle tests','Admin/secretary management; President signature','Decree/signature/release/decision','PA23 PA24')
screen('Council','Appeals/later petitions','council-decree.js AppealsWorkspace','Queue/detail, hearing eligibility and per-filing accept/decline',
 'Combined actual two-spouse reopening/decree cycle acceptance','Read smoke + backend tests','Authorized assigned case writer','Application/Disposition/Proceeding')
screen('Council','Communications/calls','app.js + council-case.js CallLog','Private recipient messages and manual call log','Inbound/live email, full subject/contact/duration mapping',
 'Read-only API smoke; backend delivery tests','Assigned case writer; approved closed-case communication policy','Message/Recipient/CallRecord','PA20 PA21')
screen('Council','Case Audit','council-case.js CaseAudit','Case event list/search','Structured filters, full pagination and target context',
 'Read-only API smoke','All council','AuditEvent','PA22')
screen('Council','Q Search','council.js SearchWorkspace','Document query and history toggle','Unified case/person/session results and advanced filters; live index acceptance',
 'Screen renders; live query not accepted','Council; source reauthorization','Meilisearch + DocumentText','PA09')
screen('Council','Statistics and Reports','council.js StatisticsWorkspace','Open/closed/unassigned/workload/session counts','Complete server metrics/periods/charts; max100 limitation',
 'Read-only API smoke','Council','Cases/sessions list','PA11')
screen('Council','Member profile/history','None','Roster only','Member details/current/past assignment workspace',
 'Not implemented','Council','Staff memberships/assignment history','PA12')
screen('Shared','My Profile','app.js','Name/portal display','Editable profile/contact/photo relationship and own activity',
 'Stub','Own profile','Account + unfinalized portrait mapping','PA15')
screen('Shared','Account Settings','app.js','Interface/notification language','Consolidated account fields, provider email/security/session workflow',
 'Partial','Own account','Account settings API','PA15')
screen('System','CTM Settings/account management','None','Selected enrollment/configuration APIs exist','Consolidated admin/settings screens, roles/lifecycle/photo/secrets inventory',
 'No complete screen','Existing admin enrollment; settings-specific authorization','Settings/staff/identity integrations','PA13 PA14')
screen('System','System Audit/security history','None','System audit API exists','Complete system audit/login/session management UI',
 'No complete screen','Admin/secretary','Audit/account/session sources','PA14')
screen('System','Historical case entry','None','Staging/publish API exists','Authorized historical entry form, missing-data workflow, retained identifiers',
 'API tested; screen missing','System-level authorized staff','HistoricalWorkspace','PA26')
screen('External','Priest report capability page','None','Backend capability endpoints exist','External page/delivery and actual acceptance',
 'No complete user-facing workflow','Only scoped unexpired recipient link','ReportRequest token scope')

meta = dict(branch='governance/integration-20261021',
    backend='37d6ed7afb000b8959843e42607d56e156f6a851',
    applicant='2ae4541651e89589ca1bb554c1d3e1a67443c760',
    council='65fa3893758ab298beee8aa921a544a8cd489ebc',
    assembly='backend merge, applicant merge, council merge; reverse council standalone shell patch, apply applicant then council-after-applicant shell patches',
    evidence={'frontend_unit':'180 passed','postgres':'490 passed,2 skipped; no model drift',
              'actual_api_browser':'66 groups passed; isolated SQLite, synthetic sessions, controlled scan/provider policy',
              'seed_fixture':'3 SQLite tests passed after correcting legacy fixture manifest identity key'},
    preview='http://localhost:18844/',
    limitations='No production deployment, no full151 schema completion, no live payment/email/scan/OCR/transcription or general visual approval.')
(OUT/'screen-map.json').write_text(json.dumps({'metadata':meta,'screens':ROWS},indent=2,ensure_ascii=False),encoding='utf-8')
with (OUT/'screen-map.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(ROWS[0]));writer.writeheader();writer.writerows(ROWS)
text=['# Integrated CTM screen and feature map','',
 'This is a pinned integration snapshot, not a completion percentage. Each screen separates implemented behavior from remaining work. Working is scoped to the stated tests; UI is not accepted merely because it renders.','',
 '## Build and evidence','',*['- '+key+': `'+str(value)+'`' for key,value in meta.items() if key!='evidence'],'',
 *['- '+key+': '+value for key,value in meta['evidence'].items()],'',
 'The preview uses a COPY of the existing isolated local review database/media with provider-only Microsoft login retained. Original data/checkout remain intact. It is loopback-only and uses test settings, so it must never be exposed publicly. No prototype redesign was performed.','',
 '## Screen map','', '| Portal | Screen | Implemented / connected | Remaining | Working evidence |','|---|---|---|---|---|']
for row in ROWS:text.append('| '+' | '.join(row[k] for k in ['portal','screen','implemented','remaining','working'])+' |')
text+=['','## Seven stages by screen','', '| Screen | Workflow | Schema | Database | Coded | Working | UI | Testing/QA |','|---|---|---|---|---|---|---|---|']
for row in ROWS:text.append('| '+' | '.join(row[k] for k in ['screen','workflow','schema','database','coded','working','UI','testing_QA'])+' |')
text+=['','## Interpretation','',
 '- Most rows remain partial at feature level even if their unit tests pass. No unsupported 100-percent-complete claim is made.',
 '- Detailed per-row access, data source and module information is in screen-map.json and CSV.',
 '- Read-only council smoke results/screenshots are in evidence/. Screen rendering is weaker evidence than full write/lifecycle acceptance.',
 '- The earlier prototype audit remains the reference for missing factual pages and schema questions (issue14 / PR13).',
 '- Owner shared-fact rule: show marriage/separation shared facts once from first formal filing, flag discrepancies and retain originals. The source-correction rule is still awaiting a decision; these missing views were not invented during integration.',
 '- Main is unchanged. Integration branch commits merge workstreams only here; public release remains separate.','']
(OUT/'README.md').write_text('\n'.join(text),encoding='utf-8')
print('Screen inventory:',len(ROWS))
