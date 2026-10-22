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

test("session layout assets use a current cache version", () => {
  assert.match(shell, /ctm\/shell-layout\.js\x27 %\}\?v=[a-z0-9-]+/);
  assert.match(shell, /ctm\/council\.js\x27 %\}\?v=[a-z0-9-]+/);
});
test("council modules load in order before app.js with the pinned Plenix CDN", () => {
  const order = ["cdn/0.65.0/plenix.js", "ctm/council.js", "ctm/council-case.js", "ctm/council-decree.js", "ctm/council-media.js", "ctm/app.js"].map((s) => shell.indexOf(s));
  for (const index of order) assert.ok(index > 0);
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  assert.doesNotMatch(shell, /cdn\/(?!0\.65\.0)\d+\.\d+\.\d+/);
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

test("report templates are an inline category-to-question workspace", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /label: t\("reportTemplates"\)/);
  assert.match(councilCase, /title: t\("questionCategories"\)/);
  assert.match(councilCase, /title: t\("questionSelection"\)/);
  assert.match(councilCase, /value: "both", label: t\("bothSpouses"\)/);
  assert.match(councilCase, /const partyIds = form\.party === "both"/);
  assert.match(councilCase, /party_ids: partyIds/);
  assert.doesNotMatch(councilCase.slice(councilCase.indexOf("function RequestsPanel"), councilCase.indexOf("function ReportsWorkspace")), /h\(P\.Dialog/);
});

test("report template questions hide internal question-bank codes", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /key: q\.code, label: wording\(q, lang\)/);
});

test("report template wording follows the selected request language", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /if \(lang === "ar"\) return ar \|\| en/);
  assert.match(councilCase, /lang === "en-ar" && ar \? `\$\{en\}\r?\n\$\{ar\}` : en/);
  assert.match(councilCase, /lang === "en-ar" && ar \? `\$\{en\} \/ \$\{ar\}` : en/);
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
  assert.match(app, /\["home", "sessions", "sessionsUpcoming", "sessionsArchived", "search", "myCases", "cases", "archived", "statistics"\]/);
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
  assert.match(app, /const caseSearchIcon = \(\) =>\s*h\(P\.Icon, \{ name: "folder_eye"/);
  assert.match(app, /id === "search"\s*\? caseSearchIcon\(\)/);
  assert.match(app, /const appealsReturnIcon = \(\) =>/);
  assert.match(app, /id === "appeals"\s*\? appealsReturnIcon\(\)/);
  assert.match(app, /const casesNavigationItems = \[\s*\{ id: "search", icon: navigationIcon\("search"\), label: t\("search"\) \}/);
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
  assert.match(council, /className: "ctm-session-header-action"/);
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(css, /\.ctm-session-header-action\s*\{[^}]*inline-size: fit-content/);
  assert.match(council, /icon: "folder-add", label: t\("addAssignmentCase"\)/);
  assert.match(council, /className: "ctm-calendar-add-icon"/);
  assert.match(council, /name: "calendar"/);
  assert.match(council, /name: "add", size: "2xs"/);
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
  assert.match(council, /h\(P\.Button, \{ className: "ctm-session-header-action", size: "sm", icon: action\.icon/);
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
  assert.match(council, /collapsible: true,[\s\S]*defaultExpanded: true/);
  assert.match(council, /strings: \{ collapse: t\("collapse"\), expand: t\("expand"\) \}/);
  assert.match(agendaTable, /previousRecommendation/);
  assert.doesNotMatch(agendaTable, /field: "record"/);
  assert.match(agendaTable, /title: t\("actions"\), field: "open_action"/);
  assert.match(council, /empty: t\(`part\$\{n\}Empty`\), isStatic: true/);
  assert.match(shellLayout, /className, isStatic = true/);
  const assignmentColumns = agendaTable.slice(agendaTable.indexOf("const columns = first"), agendaTable.indexOf("        : ["));
  assert.ok(assignmentColumns.lastIndexOf("field: \"open_action\"") > assignmentColumns.lastIndexOf("field: \"assigned_member_name\""), "Cases to assign ends with Open");
  const scheduledColumns = agendaTable.slice(agendaTable.indexOf("        : ["), agendaTable.indexOf("      return h(P.Panel"));
  assert.ok(scheduledColumns.lastIndexOf("field: \"open_action\"") > scheduledColumns.lastIndexOf("field: \"previous_recommendation\""), "Scheduled hearings ends with Open");
  assert.match(shellLayout, /headerMenu: !isStatic/);
  assert.match(shellLayout, /resizable: !isStatic/);
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
  assert.match(councilCase, /icon: spousePhoto\(P, h, party\)/);
  assert.match(councilCase, /function spouseHeaderTitle/);
  assert.match(councilCase, /title: spouseHeaderTitle\(P, h, t, party\)/);
  assert.match(councilCase, /collapsible: true,\s*defaultExpanded: false/);
  assert.doesNotMatch(councilCase, /spouseIdentity\(P, h, t, party\)/);
  assert.match(councilCase, /collapsible: true/);
  assert.match(councilCase, /profile\?\.contact/);
  assert.match(councilCase, /function spouseProfileSection\(P, h, t, title, icon, values, twoColumns = false\)/);
  assert.match(councilCase, /t\("contact"\), "message", \[\s*[\s\S]*?\], true\)/);
  const councilCss = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(councilCss, /plx-data-grid__type-icon/);
  assert.match(councilCss, /ctm-spouse-profile-section--two-columns/);
  assert.match(councilCss, /grid-column: 1 \/ -1/);
  assert.match(councilCss, /inline-size: 68px/);
  assert.match(councilCase, /t\("personalDetails"\), "person", \[/);
  assert.doesNotMatch(councilCase, /t\("personalDetails"\), "user", \[/);
  assert.match(councilCase, /P\.SectionHeading, \{ level: 2 \}/);
  assert.match(councilCase, /P\.Divider, \{ className: "ctm-spouse-profile-section__divider" \}/);
  assert.doesNotMatch(councilCase, /ctm-spouse-profile-columns/);
  const personal = councilCase.indexOf('t("personalDetails")');
  const contact = councilCase.indexOf('t("contact")');
  const career = councilCase.indexOf('t("career")');
  const church = councilCase.indexOf('t("churchAffiliation")');
  assert.ok(personal < contact && contact < career && career < church, "spouse profile sections stay in the requested vertical order");
  assert.match(councilCase, /manage && record\.status === "open" && record\.parties\.length < 2/);
});

test("marriage card saves council-owned edits through the shared card finding layer", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(councilCase, /function councilCardValues\(record, scope, submitted\)/);
  assert.match(councilCase, /fact_code: "case_card\.marriage"/);
  assert.match(councilCase, /\/findings\//);
  assert.match(councilCase, /ctm-case-edit-grid/);
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
  assert.match(councilCase, /CaseReadFields, \{ P, h, fields: summaryReadFields, values: summaryReadValues, className: "ctm-case-summary-fields" \}/);
  assert.match(councilCase, /ctm-case-edit-grid ctm-case-read-grid/);
  const councilCss = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(councilCss, /\.ctm-case-read-grid input\[readonly\]/);
  assert.match(councilCase, /reasonForDivorce: "Reason for Divorce"/);
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

test("case navigation groups notes and communications outside Case Overview", () => {
  const councilCase = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(app, /notes: "Notes"/);
  assert.match(app, /communications: "Email"/);
  assert.match(app, /caseCollaboration: "Email & Notes"/);
  assert.match(app, /items: ["case", "timeline", "parties", "marriage", "separation"]/);
  assert.match(app, /id === "separation"\s*\? h\("span", \{ className: "ctm-separation-nav-icon"/);
  assert.match(app, /h\(P\.Icon, \{ name: "person" \}\), h\(P\.Icon, \{ name: "close" \}\)/);
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
  assert.match(app, /className: "ctm-decree-nav-icon"/);
  assert.match(app, /className: "ctm-decision-nav-icon"/);
  assert.match(app, /M12 3v17M5 7h14/);
  assert.match(app, /groups: collaborationGroups/);
  assert.match(app, /page === "notes" && council && councilModule\?\.CaseNotesWorkspace/);
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
  assert.match(source, /function editSession\(row\)/);
  assert.match(source, /rows, selected, onSelect: select, empty: t\(emptyKey\), isStatic: true/);
  assert.match(source, /empty: t\(emptyKey\), isStatic: true/);
  assert.match(source, /method: editing \? "PATCH" : "POST"/);
  assert.match(source, /const \[formOpen, setFormOpen\] = R\.useState\(false\)/);
  assert.match(source, /onClick: startCreate/);
  assert.match(source, /mode === "upcoming" && canManage\(user\) && formOpen/);
  assert.match(source, /title: t\("sessionTime"\), field: "starts_at", minWidth: "8rem", pill: false, render: \(row\) => formatTime\(row\.starts_at, lang\)/);
  assert.doesNotMatch(source.slice(source.indexOf("columns: ["), source.indexOf("]),\n      }),")), /presiding_member_name/);
  assert.doesNotMatch(source.slice(source.indexOf("columns: ["), source.indexOf("]),\n      }),")), /locationNotRecorded/);
});


test("new session form defaults the Bellflower location and uses a responsive two-column grid", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const css = fs.readFileSync("static/ctm/ctm.css", "utf8");
  assert.match(council, /R\.useState\("St\. George Coptic Orthodox Church, Bellflower, California"\)/);
  assert.match(council, /className: "ctm-session-form-grid"/);
  assert.match(css, /\.ctm-session-form-grid[\s\S]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /\.ctm-session-form \.plx-form-actions[\s\S]*background: transparent/);
  assert.match(css, /#ctm-root \.plx-panel \.plx-form-actions[\s\S]*background: transparent/);
});


test("tribunal session lists do not show date filters", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SessionList"), council.indexOf("function AgendaItemCard"));
  assert.doesNotMatch(source, /SessionFilters/);
  assert.match(source, /const rows = buckets\[mode\] \|\| \[\]/);
});


test("upcoming sessions expose create edit and save actions in a Plenix toolbar", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const source = council.slice(council.indexOf("function SessionList"), council.indexOf("function AgendaItemCard"));
  assert.match(source, /h\(P\.Toolbar, \{ label: t\("tribunalSession"\) \}/);
  assert.match(source, /icon: "add"/);
  assert.match(source, /icon: "pencil"/);
  assert.match(source, /icon: "save"/);
  assert.match(source, /form: "ctm-session-form"/);
  assert.match(source, /t\("saveSession"\)/);
  assert.doesNotMatch(source, /SessionFilters/);
});
