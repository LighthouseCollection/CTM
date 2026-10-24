const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const sourcePath = "static/ctm/routes.js";
const source = fs.existsSync(sourcePath) ? fs.readFileSync(sourcePath, "utf8") : "";
const window = {};
vm.runInNewContext(source, { window });
const plain = (value) => JSON.parse(JSON.stringify(value));

test("CTM routes serialize and restore session, case, and case-section locations", () => {
  const routes = window.CTMRoutes;
  assert.ok(routes, "client routing helper must be available");

  assert.deepEqual(plain(routes.parse("/sessions/upcoming")), {
    page: "sessionsUpcoming", selection: null, pathname: "/sessions/upcoming",
  });
  assert.deepEqual(plain(routes.parse("/sessions/session-42")), {
    page: "session", selection: "session-42", pathname: "/sessions/session-42",
  });
  assert.deepEqual(plain(routes.parse("/cases/case 42/evidence")), {
    page: "evidence", selection: "case 42", pathname: "/cases/case%2042/evidence",
  });
  assert.equal(routes.routeFor("session", "session-42"), "/sessions/session-42");
  assert.equal(routes.routeFor("evidence", "case 42"), "/cases/case%2042/evidence");
  assert.deepEqual(plain(routes.parse("/settings/audit")), {
    page: "settings", selection: "audit", pathname: "/settings/audit",
  });
  assert.equal(routes.routeFor("settings", "audit"), "/settings/audit");
});

test("CTM routes reject malformed and unknown paths without throwing", () => {
  const routes = window.CTMRoutes;
  assert.equal(routes.parse("/cases/%E0%A4%A"), null);
  assert.equal(routes.parse("/unknown/workspace"), null);
});

test("the CTM shell restores the browser route and listens to Back and Forward", () => {
  const app = fs.readFileSync("static/ctm/app.js", "utf8");
  const urls = fs.readFileSync("ctm/urls.py", "utf8");
  const shell = fs.readFileSync("tribunal/templates/tribunal/shell.html", "utf8");

  assert.match(shell, /ctm\/routes\.js/);
  assert.match(app, /window\.CTMRoutes/);
  assert.match(app, /window\.addEventListener\("popstate"/);
  assert.match(app, /history\.pushState/);
  assert.match(urls, /re_path\(r"\^\(\?P<client_path>/);
});

test("Tribunal Session data uses native pills and its state uses a semantic badge", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const sessionList = council.slice(council.indexOf("function SessionList"), council.indexOf("function SessionAttendance"));

  assert.doesNotMatch(sessionList, /field: "starts_at"[^\n]*pill: false/);
  assert.doesNotMatch(sessionList, /field: "adjourned_at"[^\n]*pill: false/);
  assert.doesNotMatch(sessionList, /field: "assigned_case_count"[^\n]*pill: false/);
  assert.doesNotMatch(sessionList, /field: "hearing_case_count"[^\n]*pill: false/);
  assert.match(sessionList, /h\(P\.Badge, \{ tone: sessionStatusTone\(row\.state\) \}/);
  assert.match(sessionList, /field: "session_actions"[^\n]*pill: false/);
});

