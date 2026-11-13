// Issue 308 (owner approval 2026-11-10): pages load their data in as few rounds as possible. The shell does not
// load what a council page loads itself; each page starts its reads together and asks for nothing twice.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { harness, load, settle } = require("./harness.cjs");

const PLENIX = Symbol.for("ctm.test.plenix");
const named = (name) =>
  new Proxy(function () {}, { get: (_t, key) => (key === PLENIX ? true : key === "displayName" ? name : named(`${name}.${String(key)}`)) });
// Plenix placeholders, with the hooks the shell calls answering like the real ones.
const hooks = { useAppLayout: () => ({ mode: "overlay", toggle() {} }), useToast: () => ({ show() {} }) };
const Plenix = new Proxy({}, { get: (_t, key) => hooks[key] || named(String(key)) });

const secretary = { id: "u-sec", portal: "council", role: "secretary", name: "Synthetic Secretary", ui_language: "en" };

// Loads the real shell (routes, shell layout, council modules, app.js) at a path and records every request.
// reply(url) answers each request; the round a request starts in is counted by settling between rounds.
function bootApp(pathname, reply) {
  const h = harness();
  h.React.Component = class { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  h.React.useLayoutEffect = h.React.useEffect;
  const asked = [];
  let mounted = null;
  const element = () => ({ textContent: "", appendChild() {} });
  const window = {
    React: h.React, Plenix, addEventListener() {}, removeEventListener() {}, dispatchEvent() {},
    location: { pathname, search: "", href: "http://ctm.test" + pathname, origin: "http://ctm.test", assign() {} },
    history: { pushState() {}, replaceState() {} },
    ReactDOM: { createRoot: () => ({ render: (node) => { mounted = node; } }) },
  };
  const document = {
    cookie: "csrftoken=t", documentElement: {}, body: { appendChild() {} }, createElement: element,
    getElementById: (id) => (id === "ctm-config" ? { textContent: JSON.stringify({ providers: [] }) } : element()),
  };
  // Each reply waits until the test releases the round it was asked in, so rounds count real waiting.
  const held = [];
  const fetch = (url, options = {}) => {
    asked.push({ url, method: options.method || "GET" });
    return new Promise((resolve) => held.push(() => resolve({ ok: true, status: 200, json: async () => reply(url) })));
  };
  const context = { window, document, console, fetch, FormData: class FormData {}, URL, URLSearchParams, Intl, localStorage: { getItem: () => null, setItem() {} }, setTimeout, clearTimeout };
  window.window = window;
  window.document = document;
  for (const file of ["routes.js", "shell-layout.js", "council.js", "council-case.js", "council-decree.js", "council-media.js", "app.js"])
    vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), Object.assign(context, { window }), { filename: file });
  // ThemeProvider > DirectionProvider > App
  const App = mounted.children[0].children[0].type;
  const release = () => held.splice(0).forEach((go) => go());
  return { h, App, asked, release };
}

// Renders until no new request starts; returns the requests grouped by the round that started them. A round's
// replies arrive only after every request of that round has started.
async function rounds({ h, App, asked, release }, extra = () => {}) {
  const out = [];
  let seen = 0;
  for (let i = 0; i < 12; i += 1) {
    for (let k = 0; k < 4; k += 1) { extra(h.render(App, {})); await settle(); }
    if (asked.length === seen) break;
    out.push(asked.slice(seen).map((row) => row.url));
    seen = asked.length;
    release();
    await settle();
  }
  return out;
}

const caseRecord = {
  id: "c-1", number: "20261020-01", status: "open", assigned_member: null, assigned_member_id: null, can_assign: true,
  can_place_part2: true, assignment_history: [], can_message: true, parties: [], proceedings: [{ id: "p-c-1", kind: "initial", status: "open", sequence: 1 }],
};
const dashboard = {
  my_cases: 0, review_queue: 2,
  upcoming_sessions: [{ id: "s-1", date: "2099-01-10", state: "planned", starts_at: "2099-01-11T02:00:00Z", location: "Synthetic Hall",
    agenda_count: 3, my_answer: "attend", confirmed: 1, invited: 4 }],
};
function councilReply(url) {
  if (url === "/api/session/") return secretary;
  if (url === "/api/cases/c-1/") return caseRecord;
  if (url === "/api/dashboard/") return dashboard;
  if (url === "/api/notifications/") return { items: [], unread_count: 0, next_offset: null };
  if (url.startsWith("/api/statistics/summary/")) return { year: 2026, years: [2026], threshold: 5, cases_per_member: [], cases_by_ground: [] };
  if (url === "/api/proceedings/p-c-1/decision/") return { items: [] };
  if (url === "/api/council/members/") return { items: [], assignment_authorities: [] };
  return { items: [] };
}

test("council Home: the shell loads no case list; Home asks each source once, in two rounds (issue 308)", async () => {
  const app = bootApp("/", councilReply);
  const steps = await rounds(app);
  const { asked } = app;
  const urls = asked.map((row) => row.url);
  assert.equal(urls.filter((url) => url === "/api/cases/").length, 0, "the full case list is not loaded for Home");
  assert.ok(!urls.some((url) => url.startsWith("/api/sessions/")), "the lead session comes from /api/dashboard/");
  assert.equal(new Set(urls).size, urls.length, "nothing is asked twice");
  assert.equal(steps.length, 2, `session, then everything Home shows: ${JSON.stringify(steps)}`);
});

test("council case page: the case record is read once and members once; three rounds (issue 308)", async () => {
  const app = bootApp("/cases/c-1", councilReply);
  const steps = await rounds(app);
  const { asked } = app;
  const urls = asked.map((row) => row.url);
  assert.equal(urls.filter((url) => url === "/api/cases/c-1/").length, 1, "one case record");
  assert.equal(urls.filter((url) => url === "/api/council/members/").length, 1, "the assign control reuses the summary's members");
  assert.equal(steps.length, 3, `session; case, requests, audit, members; decision: ${JSON.stringify(steps)}`);
  assert.deepEqual([...steps[1]].sort(), ["/api/cases/c-1/", "/api/cases/c-1/audit/", "/api/cases/c-1/requests/", "/api/council/members/"]);
  assert.deepEqual(steps[2], ["/api/proceedings/p-c-1/decision/"]);
});

test("Home lead session reads the dashboard card: time, place, agenda size and answers (issue 308)", async () => {
  const h = harness();
  h.React.Component = class { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  const C = load(h, { CTMShell: { Table() { return null; } } });
  const asked = [];
  const api = async (url) => { asked.push(url); return councilReply(url); };
  const props = { api, lang: "en", user: secretary, onCase() {}, onSession() {}, onNavigate() {} };
  h.render(C.CouncilHome, props); await settle(); h.render(C.CouncilHome, props); await settle();
  const { textOf, find } = require("./harness.cjs");
  const tree = h.render(C.CouncilHome, props);
  const root = find(tree, (n) => n.props && typeof n.props.onClickCapture === "function")[0];
  const lead = root.children.filter(Boolean)[1];
  const text = textOf(lead);
  assert.match(text, /Synthetic Hall/);
  assert.match(text, /Attending/);
  assert.match(text, /1 of 4/);
  assert.ok(!asked.some((url) => url.startsWith("/api/sessions/")));
});

test("Home's two statistics charts share one summary request (issue 308)", async () => {
  const h = harness();
  h.React.Component = class { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  const C = load(h, { CTMShell: { Table() { return null; } } });
  const asked = [];
  const api = async (url) => { asked.push(url); return councilReply(url); };
  const props = { api, lang: "en", user: secretary, onCase() {}, onSession() {}, onNavigate() {} };
  const { byName } = require("./harness.cjs");
  const tree = h.render(C.CouncilHome, props);
  const grid = byName(tree, "WidgetGrid").find((node) => node.props.items.some((item) => item.id === "grounds"));
  // Both charts on their own, as the grid draws them: their reads start together.
  h.unmount();
  asked.length = 0;
  function Both() { return grid.props.items.map((item) => grid.props.renderItem(item)); }
  h.render(Both, {});
  await settle();
  assert.deepEqual(asked.filter((url) => url.startsWith("/api/statistics/summary/")), ["/api/statistics/summary/"]);
});
