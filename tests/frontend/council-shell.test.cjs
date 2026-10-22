const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const shell = fs.readFileSync("tribunal/templates/tribunal/shell.html", "utf8");
const app = fs.readFileSync("static/ctm/app.js", "utf8");

test("council modules load in order before app.js with the pinned Plenix CDN", () => {
  const order = ["cdn/0.60.1/plenix.js", "ctm/council.js", "ctm/council-case.js", "ctm/council-decree.js", "ctm/council-media.js", "ctm/app.js"].map((s) => shell.indexOf(s));
  for (const index of order) assert.ok(index > 0);
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  assert.doesNotMatch(shell, /cdn\/(?!0\.60\.1)\d+\.\d+\.\d+/);
});

test("council navigation exposes current, upcoming, and archived tribunal sessions", () => {
  assert.match(app, /\["home", "sessions", "sessionsUpcoming", "sessionsArchived", "cases", "search", "archived", "statistics"\]/);
  assert.match(app, /sessions: "Tribunal Sessions - Current"/);
  assert.match(app, /sessionsUpcoming: "Tribunal Sessions - Upcoming"/);
  assert.match(app, /sessionsArchived: "Tribunal Sessions - Archived"/);
  assert.match(app, /mode: page === "sessions" \? "current" : page === "sessionsUpcoming" \? "upcoming" : "archived"/);
  assert.match(app, /heading: t\("tribunalSessions"\)/);
  assert.match(app, /items: sessionNavigationItems/);
});

test("session lifecycle changes refresh their parent destination list", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /function SessionWorkspace\(\{[^}]*onChanged/);
  assert.match(council, /"sessionClosed",\s*onChanged/);
  assert.match(council, /onChanged: retry/);
});

test("the current session uses the default EntityHeader with real session facts and actions", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /mode === "current"/);
  assert.match(council, /h\(P\.EntityHeader/);
  assert.doesNotMatch(council, /h\(P\.RecordPage\.Header/);
  assert.match(council, /media: \{ icon: "calendar"/);
  assert.match(council, /facts: sessionFacts/);
  assert.match(council, /actions: sessionHeaderActions/);
  for (const key of ["addAssignmentCase", "addHearingCase", "attendance"])
    assert.match(council, new RegExp(`t\\("${key}"\\)`), key);
  assert.match(council, /t\("casesToAssign"\)/);
  assert.match(council, /t\("scheduledCasesForHearing"\)/);
  assert.match(council, /h\(P\.SplitView/);
});

test("council pages are enabled only when their module is loaded", () => {
  for (const name of ["CaseParties", "CaseTimeline", "PetitionWorkspace", "AssessmentsWorkspace", "CaseHearings", "DecisionWorkspace", "DecreeWorkspace", "AppealsWorkspace", "CaseAudit"])
    assert.match(app, new RegExp(`councilModule\\?\\.${name}`), name);
  assert.match(app, /councilModule\?\.SearchWorkspace \? \[\] : \["search"\]/);
  assert.match(app, /councilModule\?\.StatisticsWorkspace \? \[\] : \["statistics"\]/);
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
