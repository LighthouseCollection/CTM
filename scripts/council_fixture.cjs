/* Synthetic council contract fixture for browser checks on machines without
   Python. Serves the real shell assets (pinned Plenix CDN, council.js, app.js)
   with an in-memory stub of the existing endpoints. It is NOT a real-API,
   provider-login or database test and contains no real case data.

   Usage: node scripts/council_fixture.cjs [port] [role]
   role: secretary (default) | member | president */
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const port = Number(process.argv[2] || 18850);
let role = process.argv[3] || "secretary";

const people = {
  secretary: { id: "u-sec", name: "Synthetic Secretary", role: "secretary" },
  member: { id: "u-mem", name: "Fr. Synthetic Member", role: "member" },
  president: { id: "u-pre", name: "Synthetic President", role: "president" },
};
const state = {
  applications: [
    {
      id: "a-1", kind: "petition", status: "submitted", case_id: "c-1", case_number: "20261020-01",
      version: 2, answers: { first_name_en: "Test", last_name_en: "Applicant", grounds: ["desertion"] },
      fee: { amount_minor: 25000, currency: "usd", status: "paid" },
    },
    {
      id: "a-2", kind: "petition", status: "submitted", case_id: "c-2", case_number: "20261020-02",
      version: 1, answers: {}, fee: { amount_minor: 25000, currency: "usd", status: "waived" },
    },
    { id: "a-3", kind: "petition", status: "accepted", case_id: "c-3", case_number: "20261019-01", version: 1, answers: {}, fee: null },
  ],
  cases: [
    { id: "c-1", number: "20261020-01", status: "open", assigned_member: null },
    { id: "c-2", number: "20261020-02", status: "open", assigned_member: null },
    { id: "c-3", number: "20261019-01", status: "open", assigned_member: null },
    { id: "c-4", number: "20261001-01", status: "open", assigned_member: "Fr. Synthetic Member" },
  ],
  sessions: [{ id: "s-1", date: "2026-11-05", reference: "CS20261105", state: "planned" }],
  agenda: [],
  attendance: [],
  posts: [],
  requests: [],
  decisions: [],
  questions: [
    { id: "q1", code: "OPEN-01", version: 1, category: "Foundational questions", wording_en: "Please state your full name and your spouse’s full name.", wording_ar: "", foundational: true, guidance: {} },
    { id: "q2", code: "DM-01", version: 1, category: "Decision to marry", wording_en: "Synthetic question one?", wording_ar: "", foundational: false, guidance: {} },
    { id: "q3", code: "DM-02", version: 1, category: "Decision to marry", wording_en: "Synthetic question two?", wording_ar: "", foundational: false, guidance: {} },
  ],
};
const parties = (c) => [
  { id: "pa-" + c.id, name: "Synthetic Applicant", is_self: false, can_receive: true, reference: null },
  { id: "pb-" + c.id, name: "Synthetic Spouse", is_self: false, can_receive: true, reference: null },
];
const members = () => Object.values(people).map(({ id, name, role }) => ({ id, name, role }));
const json = (res, status, body) => {
  res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(JSON.stringify(body));
};
const admin = () => ["secretary", "admin"].includes(role);

function api(req, res, url, body) {
  const p = url.pathname;
  const me = people[role];
  let m;
  if (p === "/__role/") { role = body.role; return json(res, 200, { role }); }
  if (p === "/__posts/") return json(res, 200, state.posts);
  if (req.method === "POST") state.posts.push({ path: p, body });
  if (p === "/api/session/")
    return json(res, 200, { ...me, portal: "council", ui_language: "en", notification_language: "en", csrf_token: "x" });
  if (p === "/api/account/settings/") return json(res, 200, { ui_language: body.ui_language || "en", notification_language: "en", email: "synthetic@example.test" });
  if (p === "/api/notifications/") return json(res, 200, { items: [], next_offset: null, unread_count: 0 });
  if (p === "/api/applications/") return json(res, 200, { items: state.applications });
  if ((m = p.match(/^\/api\/applications\/([^/]+)\/review\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const app = state.applications.find((a) => a.id === m[1]);
    if (!app || app.status !== "submitted") return json(res, 422, { error: "validation", messages: ["No petition is awaiting completeness review."] });
    if (body.result === "reject" && !String(body.instructions || "").trim())
      return json(res, 422, { error: "validation", messages: ["Reject requires correction instructions."] });
    app.status = body.result === "accept" ? "accepted" : "returned";
    return json(res, 201, { id: "r-" + app.id });
  }
  if (p === "/api/cases/") return json(res, 200, { items: state.cases });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/$/))) {
    const c = state.cases.find((x) => x.id === m[1]);
    return json(res, 200, { ...c, can_message: true, parties: parties(c), proceedings: [{ id: "p-" + c.id, kind: "initial", status: "open", sequence: 1 }] });
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/files\/$/))) return json(res, 200, { items: [], next_offset: null });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/assignment\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const c = state.cases.find((x) => x.id === m[1]);
    const mem = members().find((x) => x.id === body.member_id);
    if (!members().some((x) => x.id === body.president_id && x.role === "president")) return json(res, 404, { error: "resource_or_input_invalid" });
    c.assigned_member = mem.name;
    return json(res, 201, { id: "as-" + c.id });
  }
  if (p === "/api/council/members/") return json(res, 200, { items: members() });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/reports\/$/))) return json(res, 200, { items: [] });
  if (p === "/api/report-questions/") return json(res, 200, { items: state.questions });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/requests\/$/))) {
    const c = state.cases.find((x) => x.id === m[1]);
    if (req.method === "POST") {
      if (!admin() && c.assigned_member !== people[role].name)
        return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
      if (!body.title || !body.party_id) return json(res, 404, { error: "resource_or_input_invalid" });
      const codes = new Set(["OPEN-01", ...(body.questions || [])]);
      const r = {
        id: "rq-" + (state.requests.length + 1), case: c.id, title: body.title, kind: body.kind, state: "draft", instructions: body.instructions,
        questions: state.questions.filter((q) => codes.has(q.code)).map((q) => ({ code: q.code, version: q.version, en: q.wording_en, ar: q.wording_ar })),
      };
      state.requests.unshift(r);
      return json(res, 201, { id: r.id });
    }
    return json(res, 200, { items: state.requests.filter((r) => r.case === c.id) });
  }
  if ((m = p.match(/^\/api\/requests\/([^/]+)\/send\/$/))) {
    const r = state.requests.find((x) => x.id === m[1]);
    r.state = "sent";
    return json(res, 200, { id: r.id, token: null });
  }
  if ((m = p.match(/^\/api\/proceedings\/([^/]+)\/decision\/$/))) {
    if (req.method !== "POST") return json(res, 405, { error: "method_not_allowed" });
    if (!String(body.grounds || "").trim())
      return json(res, 422, { error: "validation", messages: ["Record the decision type and grounds/reason."] });
    const d = { id: "dv-" + (state.decisions.length + 1), ...body };
    state.decisions.push(d);
    return json(res, 201, { id: d.id });
  }
  if ((m = p.match(/^\/api\/decisions\/([^/]+)\/vote\/$/))) {
    if (body.member_id && !admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    if (state.decisions[state.decisions.length - 1].id !== m[1])
      return json(res, 422, { error: "validation", messages: ["This decision has been revised; use the latest version."] });
    return json(res, 201, { id: "vote-" + Date.now() });
  }
  if ((m = p.match(/^\/api\/decisions\/([^/]+)\/approve\/$/))) {
    if (role !== "president" && !admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    if (role !== "president" && !members().some((x) => x.id === body.president_id && x.role === "president"))
      return json(res, 404, { error: "resource_or_input_invalid" });
    return json(res, 201, { id: "appr-" + m[1] });
  }
  if (p === "/api/sessions/") {
    if (req.method === "POST") {
      if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
      if (state.sessions.some((s) => s.date === body.date)) return json(res, 409, { error: "conflict", detail: "The operation conflicts with another saved record." });
      const s = { id: "s-" + body.date, date: body.date, reference: "CS" + body.date.replace(/-/g, ""), state: "planned" };
      state.sessions.unshift(s);
      return json(res, 201, { id: s.id });
    }
    return json(res, 200, { items: [...state.sessions].sort((a, b) => b.date.localeCompare(a.date)) });
  }
  if ((m = p.match(/^\/api\/sessions\/([^/]+)\/agenda\/$/))) {
    const s = state.sessions.find((x) => x.id === m[1]);
    if (req.method === "POST") {
      const c = state.cases.find((x) => x.id === body.case_id);
      if (body.part === 1 && !admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
      if (body.part === 2 && !admin() && c.assigned_member !== people[role].name)
        return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
      const item = { id: "i-" + s.id + c.id, session: s.id, case_id: c.id, case_number: c.number, part: body.part, state: "scheduled", position: state.agenda.length + 1 };
      state.agenda.push(item);
      return json(res, 201, { id: item.id });
    }
    return json(res, 200, {
      session: { id: s.id, date: s.date, state: s.state, can_record_attendance: admin() && s.state === "planned" },
      items: state.agenda.filter((x) => x.session === s.id),
    });
  }
  if ((m = p.match(/^\/api\/sessions\/([^/]+)\/attendance\/$/))) {
    if (req.method === "POST") {
      const mem = members().find((x) => x.id === body.member_id);
      state.attendance = state.attendance.filter((r) => r.member_id !== body.member_id);
      state.attendance.push({ id: "at-" + mem.id, member_id: mem.id, member_name: mem.name, member_active: true, present: body.present, actor_id: me.id, timestamp: new Date().toISOString() });
      return json(res, 201, { id: "at-" + mem.id });
    }
    return json(res, 200, { items: state.attendance });
  }
  if ((m = p.match(/^\/api\/sessions\/([^/]+)\/close\/$/))) {
    const s = state.sessions.find((x) => x.id === m[1]);
    s.state = "closed";
    state.agenda.filter((x) => x.session === s.id && x.state === "scheduled").forEach((x) => (x.state = "unpresented"));
    return json(res, 200, { id: s.id });
  }
  if ((m = p.match(/^\/api\/agenda\/([^/]+)\/hear\/$/))) {
    const item = state.agenda.find((x) => x.id === m[1]);
    const c = state.cases.find((x) => x.id === item.case_id);
    if (c.assigned_member !== people[role].name) return json(res, 403, { error: "forbidden", detail: "Only the assigned member presents the hearing." });
    const row = state.attendance.find((r) => r.member_id === people[role].id);
    if (!row) return json(res, 422, { error: "validation", messages: ["Record the assigned presenter's attendance before the hearing."] });
    if (!row.present) { item.state = "presenter_absent"; return json(res, 200, { state: "presenter_absent", awaiting_manual_placement: true }); }
    item.state = "heard";
    return json(res, 201, { id: "h-" + item.id });
  }
  return json(res, 404, { error: "resource_or_input_invalid" });
}

http
  .createServer((req, res) => {
    const url = new URL(req.url, `http://127.0.0.1:${port}`);
    if (url.pathname.startsWith("/static/")) {
      const file = path.join(root, url.pathname);
      if (!file.startsWith(path.join(root, "static"))) return json(res, 404, {});
      return fs.readFile(file, (err, data) => {
        if (err) return json(res, 404, {});
        res.writeHead(200, { "Content-Type": "text/javascript; charset=utf-8" });
        res.end(data);
      });
    }
    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/__")) {
      let raw = "";
      req.on("data", (c) => (raw += c));
      req.on("end", () => {
        let body = {};
        try { body = raw ? JSON.parse(raw) : {}; } catch { return json(res, 400, {}); }
        api(req, res, url, body);
      });
      return;
    }
    const shell = fs
      .readFileSync(path.join(root, "tribunal/templates/tribunal/shell.html"), "utf8")
      .replace("{% load static %}", "")
      .replace(/\{% static '([^']+)' %\}/g, "/static/$1")
      .replace('{{ boot|json_script:"ctm-config" }}', '<script id="ctm-config" type="application/json">{"providers":[]}</script>');
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
    res.end(shell);
  })
  .listen(port, "127.0.0.1", () => console.log(`council fixture on http://127.0.0.1:${port} as ${role}`));
