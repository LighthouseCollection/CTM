const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const shell = fs.readFileSync("tribunal/templates/tribunal/shell.html", "utf8");
const app = fs.readFileSync("static/ctm/app.js", "utf8");
const shellLayout = fs.readFileSync("static/ctm/shell-layout.js", "utf8");

test("council modules load in order before app.js with the pinned Plenix CDN", () => {
  const order = ["cdn/0.61.0/plenix.js", "ctm/council.js", "ctm/council-case.js", "ctm/council-decree.js", "ctm/council-media.js", "ctm/app.js"].map((s) => shell.indexOf(s));
  for (const index of order) assert.ok(index > 0);
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  assert.doesNotMatch(shell, /cdn\/(?!0\.61\.0)\d+\.\d+\.\d+/);
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
  assert.match(app, /\["home", "sessions", "sessionsUpcoming", "sessionsArchived", "myCases", "cases", "search", "archived", "statistics"\]/);
  assert.match(app, /sessions: "Tribunal Sessions - Current"/);
  assert.match(app, /sessionsUpcoming: "Tribunal Sessions - Upcoming"/);
  assert.match(app, /sessionsArchived: "Tribunal Sessions - Archived"/);
  assert.match(app, /mode: page === "sessions" \? "current" : page === "sessionsUpcoming" \? "upcoming" : "archived"/);
  assert.match(app, /heading: t\("tribunalSessions"\)/);
  assert.match(app, /items: sessionNavigationItems/);
  assert.match(app, /heading: t\("cases"\)/);
  for (const key of ["myCases", "allCases", "archivedCases"])
    assert.match(app, new RegExp(`t\\("${key}"\\)`), key);
  assert.match(app, /statistics: "Reports only"/);
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
  assert.match(shell, /ctm\/ctm\.css/);
  assert.match(council, /value: "draft", label: t\("sessionStatusDraft"\), icon: "document"/);
  assert.match(council, /value: "adjourned", label: t\("sessionStatusAdjourned"\), icon: "stop"/);
  assert.match(council, /session\.state === "draft" && session\.can_activate/);
  assert.match(council, /\/activate\//);
  assert.match(council, /P\.DataPill, \{ gender: normalizedGender, fill: true \}/);
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
  assert.match(council, /sessionStatusDraft/);
  assert.match(council, /sessionStatusInSession/);
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
  assert.match(agendaTable, /title: "", field: "open_action"/);
  const assignmentColumns = agendaTable.slice(agendaTable.indexOf("const columns = first"), agendaTable.indexOf("        : ["));
  assert.ok(assignmentColumns.lastIndexOf("field: \"open_action\"") > assignmentColumns.lastIndexOf("field: \"assigned_member_name\""), "Cases to assign ends with Open");
  const scheduledColumns = agendaTable.slice(agendaTable.indexOf("        : ["), agendaTable.indexOf("      return h(P.Panel"));
  assert.ok(scheduledColumns.lastIndexOf("field: \"open_action\"") > scheduledColumns.lastIndexOf("field: \"previous_recommendation\""), "Scheduled hearings ends with Open");
  assert.match(shellLayout, /headerMenu: false/);
  assert.match(shellLayout, /resizable: false/);
  assert.match(shellLayout, /return h\(P\.DataTable/);
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
  assert.match(councilCase, /collapsible: true/);
  assert.match(councilCase, /profile\?\.contact/);
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
