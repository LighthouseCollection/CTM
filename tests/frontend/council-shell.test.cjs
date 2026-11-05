const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const shell = fs.readFileSync("tribunal/templates/tribunal/shell.html", "utf8");
const app = fs.readFileSync("static/ctm/app.js", "utf8");
const shellLayout = fs.readFileSync("static/ctm/shell-layout.js", "utf8");

test("static table headers retain their full label on hover", () => {
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.doesNotMatch(css, /\.plx-table__title > \.plx-table__type-icon/);
  assert.doesNotMatch(css, /--plx-comp-data-grid-context-hover-reserve/);
  assert.match(shellLayout, /typeIcons: false/);
});

test("shared person pills prefer recorded gender over the generic person treatment", () => {
  assert.match(shellLayout, /raw === "F" \|\| raw === "female" \? "female"/);
});

test("session layout assets use a current cache version", () => {
  assert.match(shell, /ctm\/shell-layout\.js\x27 %\}\?v=[a-z0-9-]+/);
  assert.match(shell, /ctm\/council\.js\x27 %\}\?v=[a-z0-9-]+/);
});
test("council modules load in order before app.js with the pinned Plenix CDN", () => {
  const order = ["cdn/0.86.0/plenix.js", "ctm/council.js", "ctm/council-case.js", "ctm/council-decree.js", "ctm/council-media.js", "ctm/app.js"].map((s) => shell.indexOf(s));
  for (const index of order) assert.ok(index > 0);
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  assert.doesNotMatch(shell, /cdn\/(?!0\.86\.0)\d+\.\d+\.\d+/);
});

test("shell draws Material navigation symbols through Icon, without the retired icons-all.css (Plenix 0.74.0)", () => {
  assert.doesNotMatch(shell, /icons-all\.css/);
  assert.match(shell, /cdn\/0\.86\.0\/plenix\.js"><\/script>\s*<script defer src="https:\/\/design-system\.lighthouseway\.org\/cdn\/0\.86\.0\/plenix-icons-plenix\.js"><\/script>\s*<script defer src="https:\/\/design-system\.lighthouseway\.org\/cdn\/0\.86\.0\/plenix-engines\.js">/);
  assert.match(app, /name: "document_search"/);
  assert.match(app, /name: "person_cancel"/);
});

test("navigation icons use the live CDN material filename convention", () => {
  assert.match(app, /sessionsGroup: "calendar_month"/);
  assert.match(app, /sessionsArchived: "calendar_lock"/);
  assert.match(app, /name: "folder_shared"/);
  assert.match(app, /name: "document_search"/);
  assert.match(app, /name: "person_cancel"/);
  assert.doesNotMatch(app, /calendar-month|calendar-lock|folder-shared|document-search|person-cancel/);
});

test("case workspaces use the CDN contained tab variant", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const councilMedia = fs.readFileSync("static/ctm/council-media.js", "utf8");
  assert.match(app, /h\(P\.Tabs, \{[\s\S]*variant: "contained", label: t\("communications"\)/);
  assert.match(councilCase, /variant: "contained", label: t\("reports"\)/);
  assert.match(councilCase, /h\(P\.Tabs, \{[\s\S]*variant: "contained", label: t\("callLog"\)/);
  assert.match(councilMedia, /h\(P\.Tabs, \{\s*variant: "contained",\s*label: report\.title/);
});

test("all tabbed workspaces place their content inside contained tabs", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const communications = app.slice(app.indexOf("function CommunicationsWorkspace"), app.indexOf("function CaseNavigationState"));
  const calls = councilCase.slice(councilCase.indexOf("function CallLog"), councilCase.indexOf("// ---------- Professional Assessments ----------"));
  const reports = councilCase.slice(councilCase.indexOf("function ReportsWorkspace"), councilCase.indexOf("// ---------- Decision & Voting ----------"));
  for (const source of [communications, calls, reports])
    assert.match(source, /items: \[[\s\S]*content:/);
});

test("reports separate interview work from completed reports and template composition", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /interviewReports: "Reports for Interview"/);
  assert.match(councilCase, /value: "interviews", label: t\("interviewReports"\), content: interviewReports/);
  assert.match(councilCase, /mode: "interviews"/);
  assert.match(councilCase, /interviewOnly \? row\.kind === "interview" : row\.kind !== "interview"/);
  // A new interview opens its interview tab; an external priest request (C-05) stays in Report Maker for its link.
  assert.match(councilCase, /onCreated: \(id, note\) => \{ if \(note !== "externalDraftSaved"\) setTab\("interviews"\); \}/);
});

test("report maker replaces the former report templates workspace label", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /reportTemplates: "Report Maker"/);
});

test("report templates are an inline category-to-question workspace", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /label: t\("reportTemplates"\)/);
  assert.match(councilCase, /title: t\("questionCategories"\)/);
  assert.match(councilCase, /title: t\("questionSelection"\)/);
  assert.match(councilCase, /function ReportPartySelector/);
  assert.match(councilCase, /ctm-report-party-cards/);
  assert.match(councilCase, /next\.length === eligible\.length && eligible\.length > 1 \? "both"/);
  assert.match(councilCase, /const partyIds = form\.party === "both"/);
  assert.match(councilCase, /party_ids: partyIds/);
  assert.doesNotMatch(councilCase.slice(councilCase.indexOf("function RequestsPanel"), councilCase.indexOf("function ReportsWorkspace")), /h\(P\.Dialog/);
});


test("report template intake uses selectable spouse cards and keeps applicant delivery disabled", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(councilCase, /h\(P\.Avatar, \{ src: party\.photo_url/);
  assert.match(councilCase, /kind: "interview"/);
  assert.match(councilCase, /\{ value: "intake", label: t\("methodApplicant"\), disabled: true \}/);
  assert.doesNotMatch(councilCase.slice(councilCase.indexOf("function RequestComposer"), councilCase.indexOf("const interviewDraftKey")), /description: t\("interviewHelp"\)/);
  assert.match(css, /\.ctm-report-party-cards \{/);
  assert.match(css, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
});

test("council case module has no stale template exports", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.doesNotMatch(councilCase, /templateSelection/);
});

test("report maker omits applicant instructions and reusable question-template controls", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const reportMaker = councilCase.slice(councilCase.indexOf("function RequestComposer"), councilCase.indexOf("const interviewDraftKey"));
  assert.doesNotMatch(reportMaker, /TemplateTools/);
  assert.doesNotMatch(reportMaker, /t\("instructions"\)/);
  assert.doesNotMatch(councilCase, /function TemplateTools/);
});

test("interview report reading panes omit the frozen-question notice", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const readingPane = councilCase.slice(councilCase.indexOf("function RequestDetail"), councilCase.indexOf("function RequestsPanel"));
  assert.doesNotMatch(readingPane, /frozenNotice/);
});

test("report template questions hide internal question-bank codes", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /key: q\.code, label: wording\(q, form\.language\)/);
});

test("report template draft action is named as a report", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /saveReport: "Save as a Report"/);
  assert.match(councilCase, /t\("saveReport"\)/);
});

test("Arabic report questions use an RTL reading surface", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(councilCase, /dir: form\.language === "ar" \? "rtl" : undefined/);
  // Plenix 0.75.0 follows the wrapper's dir attribute itself (plenix-platform #413); CTM keeps no RTL patch.
  assert.equal((councilCase.match(/lang: form\.language === "ar" \? "ar" : undefined/g) || []).length, 2);
  assert.match(councilCase, /ctm-report-question-language--rtl/);
  assert.doesNotMatch(css, /\.ctm-report-question-language--rtl/);
  assert.doesNotMatch(css, /direction: rtl/);
});

test("Decision & Voting uses stacked decision and council-vote containers", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const decisionWorkspace = councilCase.slice(councilCase.indexOf("function DecisionWorkspace"), councilCase.indexOf("// ---------- Case audit"));
  assert.match(councilCase, /function CouncilVoteRecord\(/);
  assert.match(decisionWorkspace, /ctm-decision-voting-workspace/);
  assert.doesNotMatch(decisionWorkspace, /noDecision/);
  assert.doesNotMatch(decisionWorkspace, /title: t\(revising \? "reviseDecision" : "recordDecision"\)/);
  assert.doesNotMatch(decisionWorkspace, /window\.CTMShell\.Workspace/);
  assert.match(councilCase, /h\(P\.Table, \{ label: t\("voteRecord"\)/);
  assert.match(councilCase, /recordVotesContinue/);
  assert.match(councilCase, /VOTE_BADGES\[choice\]\.icon/);
});

test("decision version form omits the deferral helper text", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const decisionForm = councilCase.slice(councilCase.indexOf("function DecisionForm"), councilCase.indexOf("function CouncilVoteRecord"));
  assert.doesNotMatch(decisionForm, /deferralNotice/);
});

test("report template wording follows the selected request language", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /if \(lang === "ar"\) return ar \|\| en/);
  assert.match(councilCase, /lang === "en-ar" && ar \? `\$\{en\}\r?\n\$\{ar\}` : en/);
  assert.match(councilCase, /lang === "en-ar" && ar \? `\$\{en\} \/ \$\{ar\}` : en/);
  assert.match(councilCase, /label: groupTitle\(group, form\.language\)/);
  assert.match(councilCase, /key: q\.code, label: wording\(q, form\.language\)/);
});

test("account menu receives localized AppHeader labels and density choices", () => {
  for (const key of ["menu", "myAccount", "settings", "appSettings", "app", "density", "compact", "standard", "comfortable", "signOut"])
    assert.match(app, new RegExp(`${key}:`), key);
  assert.match(app, /menu: "Account menu"/);
  assert.match(app, /menu: "قائمة الحساب"/);
  assert.match(app, /trigger: "Account and settings for \{name\}"/);
  assert.match(app, /density: true/);
  assert.match(app, /strings: accountStrings/);
});

test("council navigation groups sessions and cases into their requested destinations", () => {
  assert.match(app, /\["home", "sessions", "sessionsUpcoming", "sessionsArchived", "myCases", "newApplications", "cases", "archived", "statistics"\]/);
  assert.match(app, /sessions: "Tribunal Sessions - Current"/);
  assert.match(app, /sessionsUpcoming: "Tribunal Sessions - Upcoming"/);
  assert.match(app, /sessionsArchived: "Tribunal Sessions - Archived"/);
  assert.match(app, /mode: page === "sessions" \? "current" : page === "sessionsUpcoming" \? "upcoming" : "archived"/);
  assert.match(app, /heading: t\("tribunalSessions"\)/);
  assert.match(app, /items: sessionNavigationItems/);
  assert.match(app, /heading: t\("cases"\)/);
  for (const key of ["myCases", "allCases", "archivedCases"])
    assert.match(app, new RegExp(`t\\("${key}"\\)`), key);
  assert.match(app, /statistics: "Reports"/);
  assert.match(app, /allCases: "All Active Cases"/);
  assert.match(app, /cases: page === "myCases" \? data\.items\.filter\(\(row\) => row\.assigned_member_id === user\.id\) : data\.items/);
  assert.match(app, /\["home", "myCases", "cases", "archived", "past"\]\.includes\(page\)/);
  assert.match(app, /view: page === "myCases" \? "mine" : page === "archived" \? "archived" : "active"/);
  assert.match(app, /id === "search"\s*\? h\(P\.Icon, \{ name: "document_search"/);
  assert.match(app, /sessions: "today"/);
  assert.match(app, /sessionsGroup: "calendar_month"/);
  assert.match(app, /cases: "work"/);
  assert.match(app, /sessionsArchived: "calendar_lock"/);
  assert.match(app, /\{ id: "sessions", icon: navigationIcon\("sessions"\), label: t\("sessionCurrent"\) \}/);
  assert.match(app, /heading: t\("tribunalSessions"\),\s*icon: navigationIcon\("sessionsGroup"\)/);
  assert.match(app, /councilModule\?\.canManage\?\.\(user\)/);
  assert.match(app, /const appealsReturnIcon = \(\) =>/);
  assert.match(app, /id === "appeals"\s*\? appealsReturnIcon\(\)/);
  assert.doesNotMatch(app, /const casesNavigationItems = \[\s*\{ id: "search"/);
});

test("home session cards open Tribunal Sessions Current", () => {
  const home = app.slice(app.indexOf('if (page === "home" && council && councilModule?.CouncilHome)'), app.indexOf('if (page === "medical"', app.indexOf('if (page === "home" && council && councilModule?.CouncilHome)')));
  assert.match(home, /onSession: \(\) => go\("sessions"\)/);
  assert.doesNotMatch(home, /onSession: \(id\) => go\("session", id\)/);
});

test("session lifecycle changes refresh their parent destination list", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /function SessionWorkspace\(\{[^}]*onChanged/);
  assert.match(council, /"hearingAdjournedNotice",\s*onChanged/);
  assert.match(council, /onChanged: retry/);
});

test("the current session keeps labeled actions and its status control inside the CDN header anatomy", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /mode === "current"/);
  assert.match(council, /plx-entity-header\$\{current/);
  assert.match(council, /className: "plx-entity-header__aside"/);
  assert.match(council, /P\.Stack, \{ gap: "xs", align: "end" \},/);
  assert.match(council, /P\.Inline,\s*\{ key: action\.label, justify: "end" \}/);
  assert.match(council, /icon: "folder-add", label: t\("addAssignmentCase"\)/);
  assert.match(council, /icon: "event_available", label: t\("addHearingCase"\)/);
  assert.match(council, /className: "ctm-session-agenda-grid"/);
  assert.match(shell, /ctm\/ctm\.css/);
  assert.match(council, /value: "draft", label: t\("sessionStatusPlanned"\), icon: "document"/);
  assert.match(council, /value: "adjourned", label: t\("sessionStatusAdjourned"\), icon: "stop"/);
  assert.match(council, /session\.state === "planned" && manage/);
  assert.match(council, /\/plan\//);
  assert.match(council, /session\.state === "draft" && session\.can_activate/);
  assert.match(council, /\/activate\//);
  assert.match(council, /P\.DataPill, \{ size: "md", gender: normalizedGender \}/);
  assert.match(council, /name: "calendar", size: "lg"/);
  assert.match(council, /sessionHeaderActions\.map/);
  assert.match(council, /h\(P\.Button, \{ size: "sm", icon: action\.icon/);
  for (const key of ["addAssignmentCase", "addHearingCase", "attendance"])
    assert.match(council, new RegExp(`t\\("${key}"\\)`), key);
  assert.match(council, /t\("casesToAssign"\)/);
  assert.match(council, /t\("scheduledCasesForHearing"\)/);
  const sessionFacts = council.slice(council.indexOf("const sessionFacts"), council.indexOf("const sessionHeaderActions"));
  assert.doesNotMatch(sessionFacts, /location/);
  assert.match(council, /P\.SegmentedControl,/);
  assert.match(council, /h\(P\.Inline, \{ justify: "end" \},\s*h\(P\.SegmentedControl,/);
  assert.match(council, /sessionStatusPlanned/);
  assert.match(council, /sessionStatusInProgress/);
  assert.match(council, /sessionStatusAdjourned/);
  assert.match(council, /adjournedSessionMessage/);
  assert.match(council, /kind: "attendance"/);
  assert.match(council, /dialog\?\.kind === "attendance"/);
  assert.match(council, /onClick: \(\) => onCase\(row\.case_id\)/);
  assert.doesNotMatch(council, /dialog\?\.kind === "agenda"/);
  const agendaTable = council.slice(council.indexOf("const agendaTable"), council.indexOf("return h(", council.indexOf("const agendaTable")));
  assert.doesNotMatch(agendaTable, /P\.SplitView/);
  const sessionWorkspace = council.slice(council.indexOf("function SessionWorkspace"), council.indexOf("function searchProblem"));
  assert.match(sessionWorkspace, /const \[agendaTab, setAgendaTab\] = R\.useState\("scheduled"\)/);
  assert.match(sessionWorkspace, /h\(P\.Tabs, \{ variant: "contained", label: t\("agenda"\), value: agendaTab, onChange: setAgendaTab,/);
  assert.match(sessionWorkspace, /\{ value: "scheduled", label: t\("scheduledCasesForHearing"\), content: agendaTable\(2\) \}/);
  assert.match(sessionWorkspace, /\{ value: "assign", label: t\("casesToAssign"\), content: agendaTable\(1\) \}/);
  assert.doesNotMatch(agendaTable, /P\.Panel/);
  assert.match(agendaTable, /previousRecommendation/);
  assert.match(agendaTable, /h\(PreviousRecommendationCell, \{ value: row\.previous_recommendation, lang \}\)/);
  assert.match(council, /function PreviousRecommendationCell\(\{ value, lang \}\)/);
  assert.match(council, /t\("readRecommendation"\)/);
  assert.match(council, /open: open, size: "lg", title: t\("previousRecommendation"\)/);
  assert.doesNotMatch(agendaTable, /field: "record"/);
  assert.match(agendaTable, /title: t\("actions"\), field: "open_action"/);
  assert.match(council, /empty: t\(`part\$\{n\}Empty`\), isStatic: true/);
  assert.match(shellLayout, /className, isStatic = true/);
  const assignmentColumns = agendaTable.slice(agendaTable.indexOf("const columns = first"), agendaTable.indexOf("        : ["));
  assert.ok(assignmentColumns.lastIndexOf("field: \"open_action\"") > assignmentColumns.lastIndexOf("field: \"assigned_member_name\""), "Cases to assign ends with Open");
  const scheduledColumns = agendaTable.slice(agendaTable.indexOf("        : ["), agendaTable.indexOf("      return h(P.Panel"));
  assert.ok(scheduledColumns.lastIndexOf("field: \"open_action\"") > scheduledColumns.lastIndexOf("field: \"previous_recommendation\""), "Scheduled hearings ends with Open");
  assert.match(shellLayout, /headerMenu: true/);
  assert.match(shellLayout, /resizable: column.resizable !== false/);
  assert.match(shellLayout, /h\(P\.DataGrid/);
});

test("council pages are enabled only when their module is loaded", () => {
  for (const name of ["CaseParties", "CaseTimeline", "PetitionWorkspace", "AssessmentsWorkspace", "CaseHearings", "DecisionWorkspace", "DecreeWorkspace", "AppealsWorkspace", "CaseAudit"])
    assert.match(app, new RegExp(`councilModule\\?\\.${name}`), name);
  assert.match(app, /councilModule\?\.SearchWorkspace \? \[\] : \["search"\]/);
  assert.match(app, /councilModule\?\.StatisticsWorkspace \? \[\] : \["statistics"\]/);
});

test("spouse cards use the submitted council profile projection and remain collapsible", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /ctmId: "CTM ID#"/);
  assert.match(councilCase, /function spouseProfileSection/);
  assert.match(councilCase, /t\("personalDetails"\)/);
  assert.match(councilCase, /t\("churchAffiliation"\)/);
  assert.match(councilCase, /party\.photo_url/);
  assert.match(councilCase, /icon: h\(SpousePhotoUpload, \{ api, P, h, t, user, record, party, onSaved: retry \}\)/);
  assert.match(councilCase, /function spouseHeaderTitle/);
  assert.match(councilCase, /title: spouseHeaderTitle\(P, h, t, party\)/);
  assert.match(councilCase, /collapsible: true,\s*expanded: Boolean\(expandedParties\[party\.id\]\)/);
  assert.doesNotMatch(councilCase, /spouseIdentity\(P, h, t, party\)/);
  assert.match(councilCase, /collapsible: true/);
  assert.match(councilCase, /profile\?\.contact/);
  assert.match(councilCase, /function spouseProfileSection\(P, h, t, title, icon, values, twoColumns = false\)/);
  assert.match(councilCase, /function SpouseContactSection\(\{ api, P, h, t, user, record, party, onSaved \}\)/);
  assert.match(councilCase, /h\(SpouseContactSection, \{ api, P, h, t, user, record, party, onSaved: retry \}\)/);
  assert.match(councilCase, /twoColumns\s*\? caseColumns\(P, h, fields\.map/);
  assert.match(councilCase, /size: "2xl",\s*label: party\.name/);
  assert.match(councilCase, /t\("personalDetails"\), "person", \[/);
  assert.doesNotMatch(councilCase, /t\("personalDetails"\), "user", \[/);
  assert.match(councilCase, /P\.SectionHeading, \{ level: 2 \}/);
  assert.match(councilCase, /h\(P\.Divider\)/);
  assert.doesNotMatch(councilCase, /ctm-spouse-profile-columns/);
  const spouseCards = councilCase.slice(councilCase.indexOf("function CaseParties"));
  const personal = spouseCards.indexOf('t("personalDetails")');
  const contact = spouseCards.indexOf("h(SpouseContactSection");
  const career = spouseCards.indexOf('t("career")');
  const church = spouseCards.indexOf('t("churchAffiliation")');
  assert.ok(personal < contact && contact < career && career < church, "spouse profile sections stay in the requested vertical order");
  assert.match(councilCase, /manage && record\.status === "open" && record\.parties\.length < 2/);
});

test("marriage card saves council-owned edits through the shared card finding layer", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /function councilCardValues\(record, scope, submitted\)/);
  assert.match(councilCase, /fact_code: "case_card\.marriage"/);
  assert.match(councilCase, /\/findings\//);
  assert.match(councilCase, /caseColumns\(P, h, fields\.map/);
});

test("case back navigation retains the workspace that opened the case", () => {
  assert.match(app, /const \[caseOrigin, setCaseOrigin\] = R\.useState\(null\)/);
  assert.match(app, /const openCase = \(id, origin\) =>/);
  assert.match(app, /const returnToCaseOrigin = \(\) =>/);
  assert.match(app, /onClick: returnToCaseOrigin/);
  assert.match(app, /page: "search", labelKey: "backSearchResults"/);
  assert.match(app, /onOpen: \(id\) => openCase\(id, \{ page, labelKey:/);
  assert.match(app, /page: "session", selection, labelKey: "backTribunalSession"/);
});

test("case summary shows case details and recorded key-date milestones", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const api = fs.readFileSync("tribunal/api.py", "utf8");
  assert.match(councilCase, /caseSummary: "Case Summary"/);
  assert.match(councilCase, /CaseReadFields, \{ P, h, fields: summaryReadFields, values: summaryReadValues, lang, columns: 2 \}/);
  assert.match(councilCase, /reasonForDivorce: "Reason Seeking Divorce"/);
  assert.doesNotMatch(councilCase, /h\(P\.DataPill, \{ gender, fill: true \}, party\.name\)/);
  assert.match(councilCase, /h\(P\.Timeline, \{ label: t\("keyDates"\), items: summaryTimeline \}\)/);
  assert.match(councilCase, /status: record\.status === "open" \? t\("active"\) : bt\("closed"\)/);
  assert.match(councilCase, /actions: canEditSummary && !summaryEditing/);
  assert.match(councilCase, /fact_code: "case_card\.summary"/);
  assert.match(councilCase, /title: t\("churchMarriage"\), actions: canWrite && !editing/);
  assert.match(councilCase, /title, icon, actions: canWrite && !editing/);
  assert.match(councilCase, /\["applicant", t\("applicant"\)\], \["respondent", t\("respondent"\)\]/);
  assert.match(api, /def _summary_child\(value\):/);
  assert.match(councilCase, /latestAudit\("case_heard"\)/);
  assert.match(councilCase, /latestAudit\("case_assigned"\)/);
  assert.match(councilCase, /latestAudit\("application_submitted"\)/);
  assert.match(api, /def _case_summary\(case, application\):/);
  assert.match(api, /summary=_case_summary\(case, marriage_application\)/);
  assert.match(api, /def _applicant_submission_source\(application\):/);
  assert.match(api, /"kind": "applicant_submission"/);
  assert.match(api, /"kind": "council_record", "record_type": "hearing"/);
  assert.doesNotMatch(api, /case\.created_at\.isoformat\(\)/);
  assert.match(councilCase, /if \(summary\.filing_date\) summaryTimeline\.push\(\{/);
  assert.match(councilCase, /const applicationDates = \[/);
  assert.match(councilCase, /record\.marriage\?\.church_marriage_date/);
  assert.match(councilCase, /record\.separation\?\.separation_date/);
  assert.match(councilCase, /record\.separation\?\.civil_divorce\?\.date/);
  assert.match(councilCase, /record\.separation\?\.restraining_orders/);
  assert.match(councilCase, /function isSubmittedDate\(value\)/);
  assert.match(councilCase, /timeZone: "UTC"/);
  assert.match(api, /gender=p\.person\.gender if p\.person_id else None/);
});

test("Case Audit is the final Case Review navigation item", () => {
  assert.match(app, /"documents",\s*\n\s*"medical",\s*\n\s*"audit",/);
  assert.doesNotMatch(app, /\[\{ id: "audit", label: t\("audit"\), icon: navigationIcon\("audit"\) \}\]/);
});

test("My Account does not link to CTM Settings", () => {
  const workspaces = fs.readFileSync("static/ctm/ui-workspaces.js", "utf8");
  assert.doesNotMatch(workspaces, /onSettings/);
  assert.doesNotMatch(workspaces, /preferences: "Account Settings"/);
  assert.match(app, /page === "settings" && window\.CTMUI\?\.canAdminister\(user\)/);
});
test("CTM Settings users directory supports active, previous, and account-management actions", () => {
  const workspaces = fs.readFileSync("static/ctm/ui-workspaces.js", "utf8");
  assert.match(workspaces, /function MemberDirectory/);
  assert.match(workspaces, /label: "Active Members"/);
  assert.match(workspaces, /label: "Previous Members"/);
  assert.match(workspaces, /Add staff user/);
  assert.match(workspaces, /\/api\/system\/members\//);
  assert.match(workspaces, /\/api\/system\/accounts\/\$\{encodeURIComponent\(archiveTarget\.id\)\}\/status\//);
  assert.match(workspaces, /Manage access/);
});
test("Tribunal Config provides saved administration sections including mobile settings", () => {
  const workspaces = fs.readFileSync("static/ctm/ui-workspaces.js", "utf8");
  for (const title of ["Diocese Settings", "Document Templates", "Decision Outcomes", "Case Workflow Stages", "Canonical Reasons", "Mobile Settings"])
    assert.match(workspaces, new RegExp(title));
  assert.match(workspaces, /api\("\/api\/system\/settings\//);
});
test("Audit and Security includes active session revocation controls", () => {
  const workspaces = fs.readFileSync("static/ctm/ui-workspaces.js", "utf8");
  assert.match(workspaces, /function SecuritySessions/);
  assert.match(workspaces, /Revoke all other sessions/);
  assert.match(workspaces, /\/api\/account\/sessions\//);
});
test("CTM Settings opens the complete administration workspace for administrators", () => {
  assert.match(app, /if \(page === "settings" && window\.CTMUI\?\.canAdminister\(user\)\)\s*return h\(window\.CTMUI\.Administration/);
});

test("case navigation groups notes and communications outside Case Overview", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(app, /notes: "Notes"/);
  assert.match(app, /communications: "Email"/);
  assert.match(app, /caseCollaboration: "Email & Notes"/);
  assert.match(app, /items: ["case", "timeline", "parties", "marriage", "separation"]/);
  assert.match(app, /id === "separation"\s*\? h\(P\.Icon, \{ name: "person_cancel"/);
  assert.match(app, /page === "separation" && council && councilModule\?\.CaseSeparation/);
  assert.match(app, /items: \["communications", "calls", "notes"\]/);
  assert.match(councilCase, /function CaseSeparation\(\{ api, lang, user, caseId \}\)/);
  assert.match(councilCase, /"Separation Details"/);
  assert.match(councilCase, /"Civil Divorce"/);
  assert.match(councilCase, /"Restraining Order"/);
  assert.match(councilCase, /scope: "restraining_order", title: "Restraining Order", icon: "link"/);
  assert.match(councilCase, /"Reconciliation"/);
  assert.match(app, /const collaborationGroups = \[/);
  assert.match(app, /items: ["notes", "communications"]/);
  assert.match(app, /id === "decision"\s*\? h\(P\.Icon, \{ name: "gavel"/);
  assert.match(app, /name: "gavel"/);
  assert.match(app, /id === "marriage"\s*\? h\(P\.Icon, \{ name: "church"/);
  assert.match(app, /id === "decree"\s*\? h\(P\.Icon, \{ name: "approval"/);
  assert.match(app, /id === "hearings"\s*\? h\(P\.Icon, \{ name: "balance"/);
  assert.match(app, /groups: collaborationGroups/);
  assert.match(app, /page === "notes" && council && councilModule\?\.CaseNotesWorkspace/);
  assert.match(app, /onGoDecision: \(\) => go\(\"decision\"\)/);
  assert.match(fs.readFileSync("static/ctm/council-decree.js", "utf8"), /decreeProtocolMessage/);
  assert.match(app, /page === "marriage" && council && councilModule\?\.CaseMarriage/);
});

test("api() keeps CSRF on every request and lets FormData set its own type", () => {
  const start = app.indexOf("async function api(");
  const body = app.slice(start, app.indexOf("function MessageComposer", start));
  assert.match(body, /"X-CSRFToken": csrf\(\)/);
  assert.match(body, /options\.body instanceof FormData/);
  assert.match(body, /credentials: "same-origin"/);
  assert.match(body, /error\.status = response\.status/);
});

test("assessment reports are excluded from the ordinary report reader", () => {
  assert.match(app, /!\["medical", "psychological"\]\.includes\(row\.kind\) && !row\.restricted/);
});

test("petition view shows the submitted petition without a redundant navigation notice", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.doesNotMatch(councilCase, /petitionReadOnly/);
  assert.doesNotMatch(councilCase, /codesNotice/);
});


test("active-session transfers require a reason and use the retained override endpoint", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /transferCaseTitle/);
  assert.match(council, /transferReason/);
  assert.match(council, /\/transfer\//);
  assert.match(council, /row\.can_transfer/);
  assert.match(council, /candidate\.date > session\.date/);
  assert.doesNotMatch(council, /row\.can_transfer && transferSessions\.length \? h\(P\.Button/);
});


test("agenda tables reserve enough space for complete header labels", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(council, /yearsMarried"\), field: "married_years", minWidth: "7\.5rem"/);
  assert.match(council, /applicant"\), field: "applicant", kind: "name", minWidth: "10\.5rem"/);
  assert.match(council, /respondent"\), field: "respondent", minWidth: "10\.5rem"/);
  assert.match(council, /assignedTo"\), field: "assigned_member_name", minWidth: "12rem"/);
  assert.doesNotMatch(css, /ctm-session-agenda-grid[\s\S]*min-block-size/);
  assert.match(council, /className: "ctm-session-agenda-grid"[\s\S]*isStatic: true/);
  assert.match(council, /h\(P\.DataPill, \{ size: "md", gender: normalizedGender \}, value\)/);
  assert.match(council, /h\(P\.DataPill, \{ size: "md", person: true \}, value\)/);
  assert.doesNotMatch(council, /DataPill, \{ gender: normalizedGender, fill: true \}/);
});


test("new council sessions preselect Metropolitan Serapion as presiding", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /row\.name === "H\.E\. Metropolitan Serapion"/);
  assert.match(council, /if \(!presiding && defaultPresiding\?\.id\) setPresiding\(defaultPresiding\.id\)/);
});


test("upcoming sessions use a full table and load the selected session into the form", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SessionList"), council.indexOf("function AgendaItemCard"));
  assert.doesNotMatch(source, /P\.SplitView/);
  assert.match(source, /const \[selected, select\] = R\.useState\(""\)/);
  assert.match(source, /function editSession\(row\)/);
  assert.match(source, /rows: tableRows, selected, onSelect: select, empty: t\(emptyKey\), isStatic: true/);
  assert.match(source, /empty: t\(emptyKey\), isStatic: true/);
  assert.match(source, /method: editing \? "PATCH" : "POST"/);
  assert.match(source, /const \[formOpen, setFormOpen\] = R\.useState\(false\)/);
  assert.match(source, /onClick: startCreate/);
  assert.match(source, /mode === "upcoming" && canManage\(user\) && formOpen/);
  assert.match(source, /title: t\("sessionTime"\), field: "session_time", minWidth: "8rem"/);
  assert.match(source, /h\(P\.Badge, \{ tone: sessionStatusTone\(row\.state\) \}/);
  assert.doesNotMatch(source.slice(source.indexOf("columns: ["), source.indexOf("]),\n      }),")), /presiding_member_name/);
  assert.doesNotMatch(source.slice(source.indexOf("columns: ["), source.indexOf("]),\n      }),")), /locationNotRecorded/);
});


test("new session form defaults the Bellflower location and uses a responsive two-column grid", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(council, /R\.useState\("St\. George Coptic Orthodox Church, Bellflower, California"\)/);
  assert.match(council, /h\(P\.Columns, \{ count: 2, collapseBelow: "wide" \}/);
});


test("tribunal session lists do not show date filters", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SessionList"), council.indexOf("function AgendaItemCard"));
  assert.doesNotMatch(source, /SessionFilters/);
  assert.match(source, /const rows = buckets\[mode\] \|\| \[\]/);
});


test("upcoming session actions live in each row instead of the toolbar", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SessionList"), council.indexOf("function AgendaItemCard"));
  const toolbar = source.slice(source.indexOf('h(P.Toolbar'), source.indexOf('mode === "upcoming" && canManage(user) && formOpen'));
  assert.match(toolbar, /icon: "add"/);
  assert.doesNotMatch(toolbar, /icon: "pencil"/);
  assert.match(source, /field: "session_actions"/);
  assert.match(source, /onClick: \(\) => editSession\(row\)/);
  assert.match(source, /onClick: \(\) => setDeleteTarget\(row\)/);
  assert.match(source, /icon: "trash", variant: "danger-secondary", disabled: pending \|\| row\.state !== "draft"/);
  assert.match(source, /method: "DELETE"/);
  assert.match(source, /P\.ConfirmDialog/);
  assert.match(source, /form: "ctm-session-form"/);
  assert.match(source, /t\("saveSession"\)/);
});

test("delete controls use the shared danger-secondary treatment", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const lifecycle = fs.readFileSync("static/ctm/applicant-lifecycle.js", "utf8");
  assert.match(council, /icon: "trash", variant: "danger-secondary", onClick: \(\) => setDeleteTarget\(row\).*t\("deleteCase"\)/);
  assert.match(lifecycle, /variant:action==="delete"\?"danger-secondary":undefined/);
  assert.match(lifecycle, /variant:selected==="delete"\?"danger-secondary":undefined/);
});

test("case list workspaces are table-only and open cases from their action column", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function CasesTable"), council.indexOf("// Operational counts"));
  assert.doesNotMatch(source, /P\.SplitView/);
  assert.doesNotMatch(source, /P\.ReadingPane/);
  assert.match(source, /h\(P\.Inline, \{ gap: "md", align: "end", wrap: true \},[\s\S]*P\.Input, \{ type: "search", width: "lg"[\s\S]*showClosedCases/);
  assert.match(source, /title: t\("actions"\), field: "open_action"/);
  assert.match(source, /onClick: \(\) => onOpen\(row\.id\)/);
});

test("document search omits redundant helper and field-label copy", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SearchWorkspace"), council.indexOf("// Council Home"));
  assert.doesNotMatch(source, /searchLabel/);
  assert.doesNotMatch(source, /description: t\("searchHelp"\)/);
});

test("session agenda person pills preserve normalized gender styling", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("const personPill"), council.indexOf("const agendaTable"));
  assert.match(source, /gender === "M" \|\| gender === "male"/);
  assert.match(source, /gender === "F" \|\| gender === "female"/);
});

test("archived agenda rows retain gender metadata and use approved case statuses", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const rows = council.slice(council.indexOf("function agendaDisplayStatus"), council.indexOf("function sessionDateProblem"));
  assert.match(rows, /applicant_gender === "M" \|\| row\.applicant_gender === "male"/);
  assert.match(rows, /respondent_gender === "F" \|\| row\.respondent_gender === "female"/);
  assert.match(rows, /row\?\.state === "heard"\) return "closed"/);
  assert.match(rows, /row\?\.part === 1 && !row\?\.assigned_member_id\) return "toBeAssigned"/);
  assert.match(rows, /return "inProgress"/);
  const archive = council.slice(council.indexOf("mode === \"archived\" && selectedSession"), council.indexOf("function AgendaItemCard"));
  assert.match(archive, /field: "applicant", type: "person"/);
  assert.match(archive, /field: "respondent", type: "person"/);
});

test("case hearings use full-width current and past tabs with an in-progress hearing header", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /function CaseHearings\(\{ api, lang, user, caseId, onSession, onDecision \}\)/);
  assert.match(councilCase, /variant: "contained", label: t\("hearingsTitle"\)/);
  assert.match(councilCase, /currentHearing: "Current Hearing: \{date\}"/);
  assert.match(councilCase, /pastHearings: "Past hearings"/);
  assert.match(councilCase, /data-plx-media-hue": "green"/);
  assert.match(councilCase, /rescheduleHearing: "Reschedule this hearing"/);
  assert.match(councilCase, /councilAttendance: "Council attendance"/);
  assert.match(councilCase, /outcome: "Outcome"/);
  assert.match(councilCase, /decisionMade: "Decision Made — Go to Decision tab"/);
  assert.match(councilCase, /recommendationOnly: "Recommendation \(no final decision yet\)"/);
  assert.doesNotMatch(councilCase.slice(councilCase.indexOf("function CaseHearings"), councilCase.indexOf("// ---------- Petition")), /CTMShell\.Workspace/);
});

test("case hearing header is rendered above its tabs and Hearings uses the balance icon", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const app = fs.readFileSync("static/ctm/app.js", "utf8");
  const hearing = councilCase.slice(councilCase.indexOf("function CaseHearings"), councilCase.indexOf("function HearingAttendance"));
  assert.match(hearing, /const currentHeader = current \? h\("header", \{ className: "plx-entity-header" \}/);
  assert.match(hearing, /return h\(P\.Stack, \{ gap: "lg" \}, currentHeader, h\(P\.Tabs/);
  assert.match(app, /id === "hearings"\s*\? h\(P\.Icon, \{ name: "balance"/);
});

test("council can edit a spouse contact through a versioned case finding", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(councilCase, /function SpouseContactSection\(/);
  assert.match(councilCase, /fact_code: `case_card\.contact_\$\{party\.id\}`/);
  assert.match(councilCase, /h\(SpouseContactSection, \{ api, P, h, t, user, record, party, onSaved: retry \}\)/);
  assert.match(councilCase, /P\.SectionHeading, \{ level: 2 \}/);
});

test("case navigation uses the requested Material folder icons", () => {
  assert.match(app, /id: "myCases", icon: h\(P\.Icon, \{ name: "folder_shared", "aria-hidden": true \}\), label: t\("myCases"\)/);
  assert.match(app, /id: "cases", icon: h\(P\.Icon, \{ name: "folder", "aria-hidden": true \}\), label: t\("allCases"\)/);
});

test("Cases includes a New Applications table that opens the standard case view", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /function NewApplicationsTable\(\{ api, lang, user, onOpen \}\)/);
  assert.match(council, /api\(REVIEW_URL\)/);
  assert.match(council, /title: t\("caseNumber"\), field: "case_number"/);
  assert.match(council, /onOpen\(row\.case_id, row\.id\)/);
  assert.match(app, /id: "newApplications"[\s\S]*label: t\("newApplications"\)/);
  assert.match(app, /page === "newApplications"/);
  assert.match(app, /reviewApplicationId: caseOrigin\?\.applicationId/);
});

test("opening a new application adds accept and decline controls to the standard case view", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /function ApplicationReviewActions\(\{ api, lang, applicationId, onDone \}\)/);
  assert.match(councilCase, /variant: "danger"/);
  assert.match(councilCase, /h\(P\.Button, \{ variant: "primary", disabled: pending, onClick: \(\) => setMode\("accept"\) \}, t\("acceptApplication"\)\)/);
  assert.match(councilCase, /api\(`\/api\/applications\/\$\{encodeURIComponent\(applicationId\)\}\/review\/`/);
  assert.match(councilCase, /result,\s*instructions: result === "reject" \? reason\.trim\(\) : ""/);
  assert.match(councilCase, /h\(ApplicationReviewActions, \{ api, lang, applicationId: reviewApplicationId/);
});

test("upcoming session editing offers Cancel that clears selection and closes the form", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SessionList"), council.indexOf("function AgendaItemCard"));
  assert.match(source, /function cancelSessionForm\(\)[\s\S]*select\(""\)[\s\S]*setFormOpen\(false\)/);
  assert.match(source, /icon: "close", onClick: cancelSessionForm, disabled: pending[\s\S]*t\("cancel"\)/);
});

test("home attention empty state uses a calm reassurance", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /nothingNeedsAttention: "You’re all caught up for now\."/);
});

test("neutral table pill treatment does not override CDN gender categories", () => {
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(css, /\.plx-data-grid \.plx-data-pill:not\(\[data-plx-category\]\),\s*\.plx-data-grid \.plx-data-pill\[data-plx-category="grey"\]/);
  assert.doesNotMatch(css, /\.plx-data-grid \.plx-data-pill\s*\{\s*background-color/);
});

test("council spouse cards offer authorized profile-photo uploads", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /function SpousePhotoUpload\(/);
  assert.match(councilCase, /form\.append\("category", "CASE_PHOTO"\)/);
  assert.match(councilCase, /form\.append\("context", party\.id\)/);
  assert.match(councilCase, /form\.append\("case_id", record\.id\)/);
  assert.match(councilCase, /h\(SpousePhotoUpload, \{ api, P, h, t, user, record, party, onSaved: retry \}\)/);
});

test("council-facing copy never uses presidential terminology", () => {
  for (const file of ["static/ctm/council-case.js", "static/ctm/council-decree.js"])
    assert.doesNotMatch(fs.readFileSync(file, "utf8"), /presidential/i, file);
});


test("scheduled hearing numbers are sequential within the hearing tab", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /hearing_number: first \? null : index \+ 1/);
  assert.match(council, /field: "hearing_number"/);
});


test("session forms show the centrally configured president as read-only", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /h\(P\.Select, \{ value: presiding, disabled: true,/);
  assert.doesNotMatch(council, /presiding_member_id: presiding/);
});

// ctm3-48 (#48, D-0022): rows whose Plenix default is the intended look. The JS no longer uses the class; the
// rules themselves go when the last #48 PR deletes ctm.css (touching it earlier fails the contract check on its
// old raw colors), so that PR replaces the CSS half of this test with "ctm.css does not exist".
const removedStyling = [
  ["#1", "ctm-session-header-action"], ["#4", "ctm-spouse-profile-section__heading"], ["#5", "ctm-spouse-profile-section__edit"],
  ["#6", "ctm-spouse-profile-section__divider"], ["#7", "ctm-decision-nav-icon"], ["#7", "ctm-decree-nav-icon"],
  ["#11", "ctm-case-summary-person-pill"], ["#17", "ctm-calendar-add-icon"], ["#24", "ctm-application-review"],
  ["#25", "ctm-demo-evidence-gallery"], ["#26", "ctm-demo-document-list"],
];
test("ctm3-48: delete-only rows no longer use a CTM styling class", () => {
  const js = fs.readdirSync("static/ctm").filter((f) => f.endsWith(".js")).map((f) => fs.readFileSync(`static/ctm/${f}`, "utf8")).join("\n");
  for (const [row, name] of removedStyling) assert.ok(!new RegExp(String.raw`\b${name}\b`).test(js), `${row} class ${name}`);
  assert.doesNotMatch(js, /["` ]ctm-spouse-profile-section["` ]/, "#4 accent section class");
  assert.doesNotMatch(js, /ctm-spouse-profile-sections/, "unused section wrapper class");
});

test("ctm3-48: council root gets direction from DirectionProvider; calendar action uses one Plenix icon", () => {
  assert.match(app, /h\(P\.ThemeProvider, null, h\(P\.DirectionProvider, \{ follow: true \}, h\(App\)\)\)/);
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /\{ icon: "event_available", label: t\("addHearingCase"\)/);
});

// ctm3-48 part 2 (#48): Case Overview cards and the session form use Plenix layout parts instead of ctm.css grids.
test("ctm3-48 part 2: case cards and session form use no CTM layout class", () => {
  const js = ["council.js", "council-case.js"].map((f) => fs.readFileSync(`static/ctm/${f}`, "utf8")).join("\n");
  for (const name of ["ctm-spouse-header", "ctm-petition-header", "ctm-spouse-profile-section--two-columns", "ctm-spouse-photo",
    "ctm-case-summary-fields", "ctm-case-edit-grid", "ctm-case-read-grid", "ctm-session-form-grid"])
    assert.ok(!js.includes(name), name);
});

test("ctm3-48 part 2: grids are Plenix Columns that collapse to one column on narrow windows", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(councilCase, /function caseColumns\(P, h, items, count, collapseBelow\)/);
  assert.match(councilCase, /h\(P\.Columns, \{ count, collapseBelow \}/);
  assert.match(councilCase, /, 3, "wide"\)/, "#13 edit forms: three columns");
  assert.match(councilCase, /, 2, "medium"\)/, "#8 spouse profile: two columns");
  assert.match(council, /h\(P\.Columns, \{ count: 2, collapseBelow: "wide" \}/, "#16 session form");
});

test("ctm3-48 part 2: read mode is a PropertyList, never a read-only input", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const read = councilCase.slice(councilCase.indexOf("function CaseReadFields("), councilCase.indexOf("function CaseMarriage("));
  assert.match(read, /P\.PropertyList, \{ layout: "stacked"/);
  assert.doesNotMatch(read, /readOnly: true|P\.Input/);
  assert.match(read, /timeZone: "UTC"/, "date-only values never shift a day");
});

test("ctm3-48 part 2: spouse photo change is Plenix AvatarUpload with EN and AR words", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const upload = councilCase.slice(councilCase.indexOf("function SpousePhotoUpload("), councilCase.indexOf("function spouseHeaderTitle("));
  assert.match(upload, /h\(P\.AvatarUpload, \{/);
  assert.match(upload, /size: "2xl"/);
  assert.match(upload, /crop: false/);
  assert.match(upload, /removable: false/);
  assert.match(upload, /strings: \{ change: t\("changePhoto"\), add: t\("addPhoto"\), notImage: t\("photoNotImage"\), tooLarge: t\("photoTooLarge"\), picture: t\("photoOf"\) \}/);
  assert.doesNotMatch(upload, /h\("input"|h\("label"/);
  assert.match(councilCase, /size: "2xl"/);
});

// ctm3-48 part 3 (#48): vote and attendance tables (interim until PLX-009), past hearings, timeline, hearing header.
test("ctm3-48 part 3: no CTM class left for votes, attendance, hearings or timeline", () => {
  const js = ["app.js", "council.js", "council-case.js"].map((f) => fs.readFileSync(`static/ctm/${f}`, "utf8")).join("\n");
  for (const name of ["ctm-council-vote", "ctm-vote-total", "ctm-hearing-attendance", "ctm-past-hearings-table", "ctm-case-timeline", "ctm-hearing-header"])
    assert.ok(!js.includes(name), name);
  assert.doesNotMatch(js, /type: "radio"/, "no native radio grids");
});

test("ctm3-48 part 3: council vote is a Plenix Table with tone buttons and icon badges for totals", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const vote = councilCase.slice(councilCase.indexOf("function CouncilVoteRecord("), councilCase.indexOf("async function submitVote()"));
  assert.match(vote, /h\(P\.Table, \{ label: t\("voteRecord"\)/);
  assert.match(vote, /h\(P\.ButtonGroup, \{ label:/);
  assert.match(vote, /tone: VOTE_TONES\[choice\]/);
  assert.match(vote, /pressed: choices\[row\.member\.id\] === choice/);
  assert.match(councilCase, /const VOTE_TONES = \{ approve: "success", deny: "danger", abstain: "neutral" \}/);
  assert.match(vote, /h\(P\.Badge, \{ key: choice, tone: VOTE_BADGES\[choice\]\.tone, icon: VOTE_BADGES\[choice\]\.icon \}/);
});

test("ctm3-48 part 3: attendance is a SegmentedControl per member in a Plenix Table (three places)", () => {
  for (const file of ["app.js", "council.js", "council-case.js"]) {
    const src = fs.readFileSync(`static/ctm/${file}`, "utf8");
    assert.match(src, /h\(P\.SegmentedControl, \{/, file);
    assert.match(src, /options: \[\{ value: "present"/, file);
  }
});

test("ctm3-48 part 3: timeline is Plenix Timeline grouped by year; past hearings a Plenix Table", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const timeline = councilCase.slice(councilCase.indexOf("function CaseTimeline("));
  assert.match(timeline, /h\(P\.SectionHeading, \{ level: 2 \}, group\.year\)/);
  assert.match(timeline, /h\(P\.Timeline, \{ label:/);
  assert.match(timeline, /dateTime: event\.timestamp/);
  assert.match(councilCase, /h\(P\.Table, \{ label: t\("pastHearings"\)/);
});
