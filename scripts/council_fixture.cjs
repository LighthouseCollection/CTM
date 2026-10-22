/* Synthetic council contract fixture for browser checks on machines without
   Python. Serves the real shell assets (pinned Plenix CDN, council modules,
   app.js) with an in-memory stub of the council endpoints. It is NOT a
   real-API, provider-login or database test and contains no real case data.

   Usage: node scripts/council_fixture.cjs [port] [role] [--contract=main|pr7]
   role: secretary (default) | member | president
   --contract=pr7 adds the council projections proposed in backend PR #7
   (review projection, agenda capabilities, hearing read, decision read,
   question taxonomy, request metadata, interview boundary). */
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const args = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const pr7 = process.argv.includes("--contract=pr7");
// --decree-read adds a decree object to decision rows (requested dependency D12).
const decreeRead = process.argv.includes("--decree-read");
const port = Number(args[0] || 18850);
let role = args[1] || "secretary";

const people = {
  secretary: { id: "u-sec", name: "Synthetic Secretary", role: "secretary" },
  member: { id: "u-mem", name: "Fr. Synthetic Member", role: "member" },
  president: { id: "u-pre", name: "Synthetic President", role: "president" },
};
const nameOf = (id) => Object.values(people).find((p) => p.id === id)?.name || null;
const now = () => new Date().toISOString();
const state = {
  applications: [
    {
      id: "a-1", kind: "petition", status: "submitted", case_id: "c-1", case_number: "20261020-01", version: 2,
      answers: { first_name_en: "Test", last_name_en: "Applicant", grounds: ["desertion"] },
      fee: { amount_minor: 25000, currency: "usd", status: "paid" },
    },
    {
      id: "a-2", kind: "petition", status: "submitted", case_id: "c-2", case_number: "20261020-02", version: 1,
      answers: {}, fee: { amount_minor: 25000, currency: "usd", status: "waived" },
    },
    { id: "a-3", kind: "petition", status: "accepted", case_id: "c-3", case_number: "20261019-01", version: 1, answers: {}, fee: null },
    {
      id: "a-5", kind: "appeal", status: "submitted", case_id: "c-5", case_number: "20260901-01", version: 1,
      answers: { statement: "Synthetic appeal statement.", new_information: "Synthetic new information." },
      fee: { amount_minor: 25000, currency: "usd", status: "paid" },
    },
  ],
  reviews: [],
  cases: [
    { id: "c-1", number: "20261020-01", status: "open", assigned: null },
    { id: "c-2", number: "20261020-02", status: "open", assigned: null },
    { id: "c-3", number: "20261019-01", status: "open", assigned: null },
    { id: "c-4", number: "20261001-01", status: "open", assigned: "u-mem" },
    { id: "c-5", number: "20260901-01", status: "closed", assigned: "u-mem" },
  ],
  sessions: [
    { id: "s-1", date: "2026-11-05", reference: "CS20261105", state: "planned" },
    { id: "s-0", date: "2026-10-08", reference: "CS20261008", state: "closed" },
  ],
  agenda: [{ id: "i-s-0c-5", session: "s-0", case_id: "c-5", part: 2, state: "heard", position: 1 }],
  attendance: [],
  hearings: [{ id: "h-appeal", agenda: "i-s-0c-5", case_id: "c-5", state: "held", presenter_id: "u-mem" }],
  outcomes: [],
  testimony: [],
  posts: [],
  requests: [],
  decisions: [],
  votes: [],
  approvals: [],
  files: [],
  attestations: [],
  decrees: [],
  questions: [
    { id: "q1", code: "OPEN-01", version: 1, category: "Foundational questions", wording_en: "Please state your full name and your spouse’s full name.", wording_ar: "", foundational: true, guidance: {} },
    { id: "q2", code: "DM-01", version: 1, category: "Decision to marry", wording_en: "Synthetic question one?", wording_ar: "", foundational: false, guidance: {} },
    { id: "q3", code: "DM-02", version: 1, category: "Decision to marry", wording_en: "Synthetic question two?", wording_ar: "", foundational: false, guidance: {} },
  ],
};
const taxonomy = {
  "OPEN-01": { category_id: "QC01", category_ar: null, topic_groups: [{ id: "TG01", title: "Foundation", title_ar: null }] },
  "DM-01": { category_id: "QC05", category_ar: null, topic_groups: [{ id: "TG02", title: "Common guided interview", title_ar: null }, { id: "TG03", title: "Annulment-related factual inquiry", title_ar: null }] },
  "DM-02": { category_id: "QC05", category_ar: null, topic_groups: [{ id: "TG02", title: "Common guided interview", title_ar: null }] },
};
const parties = (c) => [
  { id: "pa-" + c.id, name: "Synthetic Applicant", is_self: false, can_receive: true, reference: null },
  { id: "pb-" + c.id, name: "Synthetic Spouse", is_self: false, can_receive: true, reference: null },
];
const members = () =>
  Object.values(people).map(({ id, name, role }) => (pr7 ? { id, name, role, president: role === "president", active: true } : { id, name, role }));
const json = (res, status, body) => {
  res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(JSON.stringify(body));
};
const admin = () => ["secretary", "admin"].includes(role);
const me = () => people[role];
const caseRow = (c) => ({ id: c.id, number: c.number, status: c.status, assigned_member: nameOf(c.assigned) });

function applicationRow(a) {
  const base = { ...a };
  if (!pr7) return base;
  return {
    ...base,
    applicant_name: "Synthetic Applicant",
    submitted_at: "2026-10-20T18:04:00Z",
    submitted_version: a.version,
    questionnaire: { id: "qn-1", version: 1, published: true, definition: { fields: [
      { code: "first_name_en", label_en: "First name (English)", label_ar: "" },
      { code: "last_name_en", label_en: "Last name (English)", label_ar: "" },
      { code: "grounds", label_en: "Grounds", label_ar: "" },
    ] } },
    manifest: [
      { file_id: "f-mc-" + a.id, category: "MC", name: `${a.case_number}-MC-20261020-1804.pdf`, scan_state: "clean" },
      { file_id: "f-cdd-" + a.id, category: "CDD", name: `${a.case_number}-CDD-20261020-1805.pdf`, scan_state: "pending" },
    ],
    reviews: state.reviews.filter((r) => r.app === a.id),
    can_review: admin() && a.status === "submitted",
    ...(a.kind === "appeal" ? appealExtras(a) : {}),
  };
}

function appealExtras(a) {
  const c = state.cases.find((x) => x.id === a.case_id);
  const eligible = state.hearings.filter((hh) => hh.case_id === a.case_id && hh.state === "held" && hh.presenter_id === c.assigned)
    .map((hh) => ({ id: hh.id, session_date: state.sessions.find((x) => x.id === state.agenda.find((i) => i.id === hh.agenda)?.session)?.date || "2026-10-08" }));
  return {
    supplements: [{ id: "sup-1", text: "Synthetic supplement.", manifest: [], actor: "Synthetic Applicant", actor_id: "applicant-x", timestamp: "2026-10-12T17:00:00Z" }],
    disposition: a.disposition || null,
    eligible_hearings: eligible,
    can_record_result: Boolean(a.status === "submitted" && !a.disposition && eligible.length && (admin() || c.assigned === me().id)),
  };
}

function agendaRow(item, s) {
  const c = state.cases.find((x) => x.id === item.case_id);
  const row = { id: item.id, case_id: c.id, case_number: c.number, part: item.part, state: item.state, position: item.position };
  if (!pr7) return row;
  const hearing = state.hearings.find((h) => h.agenda === item.id);
  const presence = state.attendance.find((r) => r.member_id === me().id);
  return {
    ...row,
    hearing_id: hearing ? hearing.id : null,
    assigned_member_id: c.assigned,
    assigned_member_name: nameOf(c.assigned),
    party_names: parties(c).map((p) => p.name),
    can_present: Boolean(c.assigned === me().id && item.part === 2 && item.state === "scheduled" && s.state === "planned" && presence && presence.present),
    can_record_outcome: Boolean(hearing && (admin() || c.assigned === me().id) && c.status === "open"),
    testimony: state.testimony.filter((t) => t.agenda === item.id),
  };
}

function decisionRow(d) {
  const effective = {};
  for (const v of state.votes.filter((v) => v.decision === d.id)) effective[v.member_id] = v;
  const approvals = state.approvals.filter((a) => a.decision === d.id);
  const current = state.decisions.filter((x) => x.proceeding === d.proceeding).every((x) => x.number <= d.number);
  return {
    ...d, votes: Object.values(effective), vote_history: state.votes.filter((v) => v.decision === d.id),
    approval: approvals[approvals.length - 1] || null, approval_history: approvals, current,
    can_vote: current, can_approve: current && (role === "president" || admin()),
    ...(decreeRead || pr7 ? { decree: state.decrees.find((x) => x.decision === d.id) || null } : {}),
  };
}

function api(req, res, url, body) {
  const p = url.pathname;
  let m;
  if (p === "/__role/") { role = body.role; return json(res, 200, { role }); }
  if (p === "/__posts/") return json(res, 200, state.posts);
  if (req.method === "POST") state.posts.push({ path: p, body });
  if (p === "/api/session/")
    return json(res, 200, { ...me(), portal: "council", ui_language: "en", notification_language: "en", csrf_token: "x" });
  if (p === "/api/account/settings/") return json(res, 200, { ui_language: body.ui_language || "en", notification_language: "en", email: "synthetic@example.test" });
  if (p === "/api/notifications/") return json(res, 200, { items: [], next_offset: null, unread_count: 0 });
  if (p === "/api/applications/") {
    let rows = state.applications;
    if (pr7 && url.searchParams.get("state") === "awaiting_review") rows = rows.filter((a) => a.kind === "petition" && a.status === "submitted");
    return json(res, 200, { items: rows.map(applicationRow) });
  }
  if ((m = p.match(/^\/api\/applications\/([^/]+)\/review\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const app = state.applications.find((a) => a.id === m[1]);
    if (!app || app.status !== "submitted") return json(res, 422, { error: "validation", messages: ["No petition is awaiting completeness review."] });
    if (body.result === "reject" && !String(body.instructions || "").trim())
      return json(res, 422, { error: "validation", messages: ["Reject requires correction instructions."] });
    app.status = body.result === "accept" ? "accepted" : "returned";
    state.reviews.push({ app: app.id, result: body.result, instructions: body.instructions, actor: me().name, timestamp: now() });
    return json(res, 201, { id: "r-" + app.id });
  }
  if (p === "/api/cases/") return json(res, 200, { items: state.cases.map(caseRow) });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/$/))) {
    const c = state.cases.find((x) => x.id === m[1]);
    const extra = pr7
      ? { assigned_member_id: c.assigned, can_place_part2: admin() || c.assigned === me().id, can_assign: admin() && c.status === "open" }
      : {};
    return json(res, 200, { ...caseRow(c), ...extra, can_message: true, parties: parties(c), proceedings: [{ id: "p-" + c.id, kind: "initial", status: c.status, sequence: 1 }] });
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/files\/$/))) {
    // Simulates the asynchronous safety check finishing before the next listing.
    for (const f of state.files.filter((f) => f.case === m[1])) {
      if (f.scan_state === "pending" && f.checked) f.scan_state = "clean";
      f.checked = true;
    }
    const rows = state.files.filter((f) => f.case === m[1] && f.scan_state === "clean" && !state.decrees.some((d) => d.signed_file_id === f.id));
    return json(res, 200, {
      items: rows.map((f) => ({ id: f.id, name: f.name, category: f.category, version: 1, mime_type: "application/pdf", download_url: `/api/files/${f.id}/` })),
      next_offset: null,
    });
  }
  if (p === "/api/files/") {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
    const f = { id: "f-" + (state.files.length + 1), case: body.case_id, category: body.category, name: `${body.case_number}-${body.category}-20261021-1800.pdf`, scan_state: state.files.length ? "clean" : "pending" };
    state.files.push(f);
    return json(res, 201, { id: f.id, name: f.name, scan_state: f.scan_state, sha256: "synthetic" });
  }
  if ((m = p.match(/^\/api\/files\/([^/]+)\/signature\/$/))) {
    if (role !== "president" && !admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    if (!body.evidence || body.evidence.confirmed_signed !== true || !["digital", "signed_scan"].includes(body.method))
      return json(res, 422, { error: "validation", messages: ["Record digital signature or uploaded signed scan evidence."] });
    state.attestations.push({ file: m[1], signer: body.signer_id, method: body.method });
    return json(res, 201, { id: "att-" + m[1] });
  }
  if ((m = p.match(/^\/api\/decisions\/([^/]+)\/decree\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const d = state.decisions.find((x) => x.id === m[1]);
    if (!state.approvals.some((a) => a.decision === d.id && a.president_id === body.signer_id))
      return json(res, 422, { error: "validation", messages: ["Matching presidential approval is required."] });
    if (!state.attestations.some((a) => a.file === body.file_id && a.signer === body.signer_id))
      return json(res, 422, { error: "validation", messages: ["Record the president signature evidence/method for this exact stored PDF before issuance."] });
    const c = state.cases.find((x) => "p-" + x.id === d.proceeding);
    const decree = { id: "dcr-" + c.id, decision: d.id, reference: "DCR-" + c.number, language: body.language, issued_at: now(), signer: nameOf(body.signer_id), signed_file_id: body.file_id, releases: [] };
    state.decrees.push(decree);
    c.status = "closed";
    return json(res, 201, { id: decree.id });
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/audit\/$/))) {
    if (!state.audit) state.audit = [
      { id: "ev-1", action: "application_submitted", timestamp: "2026-10-20T18:04:00Z", source: "Application", source_id: "a", actor: "applicant-x" },
      { id: "ev-2", action: "completeness_accept", timestamp: "2026-10-20T19:00:00Z", source: "CompletenessReview", source_id: "r", actor: "u-sec" },
      { id: "ev-3", action: "case_assigned", timestamp: "2026-10-21T17:00:00Z", source: "CaseAssignment", source_id: "x", actor: "u-sec" },
      { id: "ev-4", action: "session_closed", timestamp: "2026-10-21T20:00:00Z", source: "CouncilSession", source_id: "s", actor: null },
    ];
    return json(res, 200, { items: state.audit });
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/calls\/$/))) {
    if (!state.calls) state.calls = [];
    if (req.method === "POST") {
      const c = state.cases.find((x) => x.id === m[1]);
      if (!admin() && c.assigned !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
      if (!String(body.outcome || "").trim() || !/(Z|[+-]\d{2}:\d{2})$/.test(body.occurred_at || ""))
        return json(res, 422, { error: "validation", messages: ["Call outcome and actual timestamp with timezone are required."] });
      const call = { id: "call-" + (state.calls.length + 1), case: m[1], party_id: body.party_id, occurred_at: body.occurred_at, recorded_at: now(), outcome: body.outcome, notes: body.notes };
      state.calls.unshift(call);
      return json(res, 201, { id: call.id });
    }
    return json(res, 200, { items: state.calls.filter((x) => x.case === m[1]) });
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/messages\/$/))) return json(res, 200, { items: [] });
  if ((m = p.match(/^\/api\/proceedings\/([^/]+)\/notes\/$/))) {
    if (!state.notes) state.notes = [];
    if (req.method === "POST") {
      const c = state.cases.find((x) => "p-" + x.id === m[1]);
      if (!admin() && c.assigned !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
      if (!String(body.text || "").trim()) return json(res, 422, { error: "validation", messages: ["Note cannot be empty."] });
      if (body.note_id) {
        const prior = state.notes.filter((n) => n.note_id === body.note_id);
        if (!prior.length || prior[0].author_id !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the original author can edit a note." });
        state.notes.push({ ...prior[0], id: "nr-" + body.note_id + "-" + (prior.length + 1), version: prior.length + 1, text: body.text, timestamp: now() });
        return json(res, 201, { id: body.note_id });
      }
      const id = "n-" + (state.notes.length + 1);
      state.notes.push({ id: "nr-" + id, note_id: id, version: 1, text: body.text, proceeding: m[1], author_id: me().id, author: me().name, timestamp: now() });
      return json(res, 201, { id });
    }
    return json(res, 200, {
      items: state.notes
        .filter((n) => n.proceeding === m[1])
        .map((n) => (pr7 ? { ...n, can_edit: n.author_id === me().id } : { id: n.id, note_id: n.note_id, version: n.version, text: n.text })),
    });
  }
  if ((m = p.match(/^\/api\/proceedings\/([^/]+)\/findings\/$/))) {
    if (!pr7) return json(res, 405, { error: "method_not_allowed" });
    return json(res, 200, {
      items: m[1] === "p-c-4" ? [{ id: "fr-1", fact_code: "marriage_date_confirmed", version: 1, value: "Confirmed against certificate", sources: [], actor_id: "u-mem", actor: "Fr. Synthetic Member", timestamp: "2026-10-21T18:00:00Z" }] : [],
    });
  }
  if ((m = p.match(/^\/api\/files\/([^/]+)\/status\/$/))) {
    if (!pr7) return json(res, 404, { error: "resource_or_input_invalid" });
    const f = state.files.find((x) => x.id === m[1]);
    if (f && f.scan_state === "pending") { if (f.checked) f.scan_state = "clean"; f.checked = true; }
    return json(res, 200, { id: m[1], scan_state: f ? f.scan_state : "pending", can_download: f?.scan_state === "clean" });
  }
  if (p === "/api/templates/") {
    if (!state.templates) state.templates = [{ id: "tpl-1", title: "Common guided interview", shared: true, retired: false, owner_id: null, version: 1, questions: [{ code: "DM-01", version: 1 }, { code: "DM-02", version: 1 }] }];
    if (req.method === "POST") {
      const tpl = { id: "tpl-" + (state.templates.length + 1), title: body.title, shared: false, retired: false, owner_id: me().id, version: 1, questions: (body.questions || []).map((code) => ({ code, version: 1 })) };
      state.templates.push(tpl);
      return json(res, 201, { id: tpl.id });
    }
    const view = (tpl) => pr7
      ? { ...tpl, can_publish: admin() && !tpl.shared && !tpl.retired, can_retire: !tpl.retired && (tpl.shared ? admin() : tpl.owner_id === me().id) }
      : { id: tpl.id, title: tpl.title, shared: tpl.shared, retired: tpl.retired };
    return json(res, 200, { items: state.templates.filter((tpl) => tpl.shared || tpl.owner_id === me().id).map(view) });
  }
  if ((m = p.match(/^\/api\/templates\/([^/]+)\/(publish|retire)\/$/))) {
    const tpl = state.templates.find((x) => x.id === m[1]);
    if (m[2] === "retire") tpl.retired = true;
    else state.templates.push({ ...tpl, id: tpl.id + "-shared", shared: true, owner_id: null });
    return json(res, m[2] === "publish" ? 201 : 200, { id: tpl.id });
  }
  if (p === "/api/dashboard/")
    return json(res, 200, {
      my_cases: state.cases.filter((c) => c.status === "open" && c.assigned === me().id).length,
      review_queue: admin() ? state.applications.filter((a) => a.kind === "petition" && a.status === "submitted").length : null,
      upcoming_sessions: state.sessions.filter((s) => s.state === "planned").map((s) => ({ id: s.id, date: s.date })),
    });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/parties\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    return json(res, 201, { id: "pending-" + Date.now() });
  }
  if (p === "/api/search/") {
    // PR #7: POST JSON only (GET 405); main: GET query only.
    if (pr7 && req.method !== "POST") return json(res, 405, { error: "method_not_allowed" });
    if (!pr7 && req.method !== "GET") return json(res, 405, { error: "method_not_allowed" });
    const q = (pr7 ? body.q : url.searchParams.get("q")) || "";
    if (q.trim().length < 2) return json(res, 422, { error: "validation", messages: ["Use a search phrase of2–200characters."] });
    if (q === "unconfigured") return json(res, 422, { error: "validation", messages: ["Search engine is not configured."] });
    return json(res, 200, {
      items: [{ file_id: "f-search-1", case_id: "c-4", name: "20261001-01-PET-20261001-0930.pdf", snippet: `Synthetic excerpt containing ${q}.` }],
      returned_count: 1,
    });
  }
  if ((m = p.match(/^\/api\/appeals\/([^/]+)\/result\/$/))) {
    const app = state.applications.find((a) => a.id === m[1]);
    const c = state.cases.find((x) => x.id === app.case_id);
    if (!admin() && c.assigned !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
    if (app.status !== "submitted" || !["accept", "decline"].includes(body.result))
      return json(res, 422, { error: "validation", messages: ["No pending appeal or invalid result."] });
    if (!state.hearings.some((h) => h.id === body.hearing_id && h.case_id === c.id)) return json(res, 404, { error: "resource_or_input_invalid" });
    app.status = body.result === "accept" ? "accepted" : "declined";
    app.disposition = { id: "disp-" + app.id, result: body.result, explanation: body.explanation, actor: me().name, actor_id: me().id, timestamp: now(), hearing_id: body.hearing_id, reopened_proceeding_id: null };
    if (body.result === "accept") c.status = "open";
    return json(res, 201, { id: "disp-" + app.id });
  }
  if ((m = p.match(/^\/api\/decrees\/([^/]+)\/release\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const decree = state.decrees.find((x) => x.id === m[1]);
    const d = state.decisions.find((x) => x.id === decree.decision);
    if ((d.entitlements || {})[body.party_id] !== "certificate") return json(res, 403, { error: "forbidden", detail: "Party is entitled to notice only." });
    decree.releases.push({ party_id: body.party_id, action: body.action, actor: me().name, timestamp: now() });
    return json(res, 201, { id: "rel-" + decree.releases.length });
  }
  // Council projection of a medical report without a council-scope release.
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/reports\/$/))) return json(res, 200, { items: m[1] === "c-4" ? [{ id: "rep-med-1", restricted: true }] : [] });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/assignment\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const c = state.cases.find((x) => x.id === m[1]);
    if (!members().some((x) => x.id === body.president_id && x.role === "president")) return json(res, 404, { error: "resource_or_input_invalid" });
    c.assigned = body.member_id;
    return json(res, 201, { id: "as-" + c.id });
  }
  if (p === "/api/council/members/") return json(res, 200, { items: members() });
  if (p === "/api/report-questions/")
    return json(res, 200, { items: state.questions.map((q) => (pr7 ? { ...q, ...taxonomy[q.code] } : q)) });
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/requests\/$/))) {
    const c = state.cases.find((x) => x.id === m[1]);
    if (req.method === "POST") {
      if (!admin() && c.assigned !== me().id)
        return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
      if (!body.title || !body.party_id) return json(res, 404, { error: "resource_or_input_invalid" });
      const codes = ["intake", "interview"].includes(body.kind) ? new Set(["OPEN-01", ...(body.questions || [])]) : new Set();
      const r = {
        id: "rq-" + (state.requests.length + 1), case: c.id, title: body.title, kind: body.kind, state: "draft", instructions: body.instructions,
        questions: state.questions.filter((q) => codes.has(q.code)).map((q) => ({ code: q.code, version: q.version, en: q.wording_en, ar: q.wording_ar })),
        subject_party_id: body.party_id, subject_name: parties(c).find((x) => x.id === body.party_id)?.name, language: body.language,
        created_at: now(), sent_at: null, parent_report_id: body.parent_id, author: me().name,
      };
      state.requests.unshift(r);
      return json(res, 201, { id: r.id });
    }
    const rows = state.requests.filter((r) => r.case === c.id).map((r) => {
      if (pr7) return ["medical", "psychological"].includes(r.kind) ? { ...r, release_status: "none", release_scope: null } : r;
      const { subject_party_id, subject_name, language, created_at, sent_at, parent_report_id, author, ...old } = r;
      return old;
    });
    return json(res, 200, { items: rows });
  }
  if ((m = p.match(/^\/api\/requests\/([^/]+)\/send\/$/))) {
    const r = state.requests.find((x) => x.id === m[1]);
    r.state = "sent";
    r.sent_at = now();
    return json(res, 200, { id: r.id, token: null });
  }
  if ((m = p.match(/^\/api\/requests\/([^/]+)\/complete\/$/))) {
    const r = state.requests.find((x) => x.id === m[1]);
    if (r.state !== "sent") return json(res, 422, { error: "validation", messages: ["Request is not awaiting this response."] });
    r.state = "completed";
    return json(res, 201, { id: "rep-" + r.id });
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
      if (body.part === 2 && !admin() && c.assigned !== me().id)
        return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
      const item = { id: "i-" + s.id + c.id, session: s.id, case_id: c.id, part: body.part, state: "scheduled", position: state.agenda.length + 1 };
      state.agenda.push(item);
      return json(res, 201, { id: item.id });
    }
    const session = { id: s.id, date: s.date, state: s.state, can_record_attendance: admin() && s.state === "planned" };
    if (pr7) Object.assign(session, { can_manage: admin() && s.state === "planned", can_close: admin() && s.state === "planned", can_reschedule: admin() && s.state === "planned" });
    return json(res, 200, { session, items: state.agenda.filter((x) => x.session === s.id).map((x) => agendaRow(x, s)) });
  }
  if ((m = p.match(/^\/api\/sessions\/([^/]+)\/attendance\/$/))) {
    if (req.method === "POST") {
      const mem = members().find((x) => x.id === body.member_id);
      state.attendance = state.attendance.filter((r) => r.member_id !== body.member_id);
      state.attendance.push({ id: "at-" + mem.id, member_id: mem.id, member_name: mem.name, member_active: true, present: body.present, actor_id: me().id, timestamp: now() });
      return json(res, 201, { id: "at-" + mem.id });
    }
    return json(res, 200, { items: state.attendance });
  }
  if ((m = p.match(/^\/api\/sessions\/([^/]+)\/close\/$/))) {
    const s = state.sessions.find((x) => x.id === m[1]);
    s.state = "closed";
    for (const x of state.agenda.filter((x) => x.session === s.id && x.state === "scheduled")) {
      const c = state.cases.find((y) => y.id === x.case_id);
      x.state = pr7 && x.part === 1 && c.assigned ? "assigned" : "unpresented";
    }
    return json(res, 200, { id: s.id });
  }
  if ((m = p.match(/^\/api\/sessions\/([^/]+)\/reschedule\/$/))) {
    if (!admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const s = state.sessions.find((x) => x.id === m[1]);
    if (!String(body.reason || "").trim()) return json(res, 422, { error: "validation", messages: ["Record the reason for rescheduling."] });
    if (state.sessions.some((x) => x.date === body.date)) return json(res, 422, { error: "validation", messages: ["Another council session already uses this date."] });
    const active = state.testimony.filter((t) => t.session === s.id && t.state !== "cancelled");
    for (const t of active) {
      const slot = (body.appointments || {})[t.id];
      if (!slot || !/[+-]\d{2}:\d{2}$/.test(slot.starts_at) || !/[+-]\d{2}:\d{2}$/.test(slot.ends_at))
        return json(res, 422, { error: "validation", messages: ["Provide explicit new times for every active testimony appointment."] });
    }
    const target = { id: "s-" + body.date, date: body.date, reference: "CS" + body.date.replace(/-/g, ""), state: "planned" };
    state.sessions.push(target);
    for (const item of state.agenda.filter((x) => x.session === s.id)) { item.session = target.id; item.id = "i-" + target.id + item.case_id; }
    for (const t of active) Object.assign(t, { session: target.id, agenda: "i-" + target.id + state.agenda.find((x) => x.session === target.id)?.case_id, starts_at: body.appointments[t.id].starts_at, ends_at: body.appointments[t.id].ends_at, version: t.version + 1, response: null });
    state.sessions = state.sessions.filter((x) => x.id !== s.id);
    return json(res, 201, { id: target.id, date: target.date, reference: target.reference });
  }
  if ((m = p.match(/^\/api\/appointments\/([^/]+)\/cancel\/$/))) {
    const t = state.testimony.find((x) => x.id === m[1]);
    if (body.expected_version !== t.version) return json(res, 422, { error: "validation", messages: ["Reload the latest testimony invitation before cancelling."] });
    t.state = "cancelled";
    return json(res, 200, { id: t.id, version: t.version, state: t.state });
  }
  if ((m = p.match(/^\/api\/agenda\/([^/]+)\/hear\/$/))) {
    const item = state.agenda.find((x) => x.id === m[1]);
    const c = state.cases.find((x) => x.id === item.case_id);
    if (c.assigned !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the assigned member presents the hearing." });
    const row = state.attendance.find((r) => r.member_id === me().id);
    if (!row) return json(res, 422, { error: "validation", messages: ["Record the assigned presenter's attendance before the hearing."] });
    if (!row.present) { item.state = "presenter_absent"; return json(res, 200, { state: "presenter_absent", awaiting_manual_placement: true }); }
    item.state = "heard";
    const hearing = { id: "h-" + item.id, agenda: item.id, case_id: c.id, state: "held", presenter_id: me().id };
    state.hearings.push(hearing);
    return json(res, 201, { id: hearing.id });
  }
  if ((m = p.match(/^\/api\/agenda\/([^/]+)\/testimony\/$/))) {
    const item = state.agenda.find((x) => x.id === m[1]);
    const c = state.cases.find((x) => x.id === item.case_id);
    if (!admin() && c.assigned !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
    const s = state.sessions.find((x) => x.id === item.session);
    if (!body.starts_at.startsWith(s.date) || body.starts_at >= body.ends_at)
      return json(res, 422, { error: "validation", messages: ["Use non-overlapping testimony times on the session date."] });
    if (state.testimony.some((t) => t.session === s.id && t.starts_at < body.ends_at && t.ends_at > body.starts_at))
      return json(res, 422, { error: "validation", messages: ["Another applicant's testimony overlaps this appointment."] });
    const party = parties(c).find((x) => x.id === body.party_id);
    const appt = { id: "t-" + (state.testimony.length + 1), agenda: item.id, session: s.id, party_id: party.id, party_name: party.name,
      starts_at: /[+-]\d{2}:\d{2}$/.test(body.starts_at) ? body.starts_at : body.starts_at + ":00-08:00", ends_at: /[+-]\d{2}:\d{2}$/.test(body.ends_at) ? body.ends_at : body.ends_at + ":00-08:00", instructions: body.instructions, version: 1, state: "scheduled", response: null };
    state.testimony.push(appt);
    return json(res, 201, { id: appt.id });
  }
  if ((m = p.match(/^\/api\/hearings\/([^/]+)\/$/))) {
    if (!pr7) return json(res, 404, { error: "resource_or_input_invalid" });
    const hearing = state.hearings.find((x) => x.id === m[1]);
    const c = state.cases.find((x) => x.id === hearing.case_id);
    return json(res, 200, { ...hearing, can_record_outcome: admin() || c.assigned === me().id, outcomes: state.outcomes.filter((o) => o.hearing === hearing.id) });
  }
  if ((m = p.match(/^\/api\/hearings\/([^/]+)\/outcome\/$/))) {
    const hearing = state.hearings.find((x) => x.id === m[1]);
    const c = state.cases.find((x) => x.id === hearing.case_id);
    if (!admin() && c.assigned !== me().id) return json(res, 403, { error: "forbidden", detail: "Only the assigned case manager can perform this action." });
    const o = { id: "o-" + (state.outcomes.length + 1), hearing: hearing.id, internal_text: body.internal_text, recommendations: body.recommendations, actor: me().name, actor_id: me().id, timestamp: now() };
    state.outcomes.push(o);
    return json(res, 201, { id: o.id });
  }
  if ((m = p.match(/^\/api\/proceedings\/([^/]+)\/decision\/$/))) {
    if (req.method !== "POST") {
      if (!pr7) return json(res, 405, { error: "method_not_allowed" });
      return json(res, 200, { items: state.decisions.filter((d) => d.proceeding === m[1]).sort((a, b) => b.number - a.number).map(decisionRow) });
    }
    if (!String(body.grounds || "").trim())
      return json(res, 422, { error: "validation", messages: ["Record the decision type and grounds/reason."] });
    const number = state.decisions.filter((d) => d.proceeding === m[1]).length + 1;
    const d = { id: "dv-" + m[1] + "-" + number, proceeding: m[1], number, ...body, actor: me().name, timestamp: now() };
    state.decisions.push(d);
    return json(res, 201, { id: d.id });
  }
  if ((m = p.match(/^\/api\/decisions\/([^/]+)\/vote\/$/))) {
    if (body.member_id && !admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const d = state.decisions.find((x) => x.id === m[1]);
    if (!decisionRow(d).current) return json(res, 422, { error: "validation", messages: ["This decision has been revised; use the latest version."] });
    state.votes.push({ decision: d.id, member_id: body.member_id || me().id, choice: body.choice, actor_id: me().id, actor: me().name, timestamp: now() });
    return json(res, 201, { id: "vote-" + state.votes.length });
  }
  if ((m = p.match(/^\/api\/decisions\/([^/]+)\/approve\/$/))) {
    if (role !== "president" && !admin()) return json(res, 403, { error: "forbidden", detail: "Administrator or secretary required." });
    const presidentId = role === "president" ? me().id : body.president_id;
    if (!members().some((x) => x.id === presidentId && x.role === "president")) return json(res, 404, { error: "resource_or_input_invalid" });
    state.approvals.push({ decision: m[1], president_id: presidentId, president: nameOf(presidentId), actor: me().name, actor_id: me().id, timestamp: now() });
    return json(res, 201, { id: "appr-" + m[1] });
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
        if ((req.headers["content-type"] || "").startsWith("multipart/form-data")) {
          // Loose multipart read of the text fields only; file bytes are ignored.
          for (const field of ["case_id", "category", "visibility"]) {
            const hit = raw.match(new RegExp(`name="${field}"\\r\\n\\r\\n([^\\r]*)`));
            if (hit) body[field] = hit[1];
          }
          body.case_number = state.cases.find((x) => x.id === body.case_id)?.number || "case";
        } else {
          try { body = raw ? JSON.parse(raw) : {}; } catch { return json(res, 400, {}); }
        }
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
  .listen(port, "127.0.0.1", () => console.log(`council fixture on http://127.0.0.1:${port} as ${role} (${pr7 ? "pr7" : "main"} contract)`));
