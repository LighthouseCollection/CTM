// Dispatcher rules (template v2.4 §6.2, D-0040). Pure: state in, actions out.
"use strict";

const LANE_PRIORITY = { release: "release", build: "build", design: "design", architecture: "design", plan: "design", spec: "spec", locale: "verify", docs: "verify" };
const BUILD_LANES = new Set(["build"]);
const GATES_ASSIGNED = "gates:assigned";

function globToRe(glob) {
  let re = "";
  for (let i = 0; i < glob.length; i += 1) {
    const c = glob[i];
    if (c === "*" && glob[i + 1] === "*") { re += ".*"; i += 1; }
    else if (c === "*") re += "[^/]*";
    else re += /[A-Za-z0-9_/-]/.test(c) ? c : `\\${c}`;
  }
  return new RegExp(`^${re}$`);
}
const matches = (files, globs) => (globs || []).some((g) => { const re = globToRe(g); return files.some((f) => re.test(f)); });

function rank(role, settings) {
  const p = role.kind === "task" ? role.priority : LANE_PRIORITY[role.lane] || "evergreen";
  const i = (settings.priority || []).indexOf(p);
  return i < 0 ? 99 : i;
}
const minutes = (now, iso) => (iso ? (now - Date.parse(iso)) / 60000 : Infinity);
// Gate and task roles run as short tasks on top of `slots` (D-0025).
const isGate = (r) => r.kind === "task" || r.gate === true;

/**
 * state: { now, settings, roles, registryOk, registryProblems, freeGb,
 *          issues: [{number, labels, title}]          open issues
 *          prs: [{number, labels, draft, files}]      open PRs
 *          sessions: { [roleId]: {pid, alive, started, item, lastActivity, stalls, long, queueLong} }
 *          memo: { lastRefill } }
 * returns [{type: label|start|stop|nudge|queue|hold|refill|process_issue, ...}]
 */
function decide(state) {
  const { now, settings, roles } = state;
  const actions = [];
  const memo = state.memo || {};
  // The poller skips a process issue whose title is already open on GitHub.
  const processIssue = (title, body) => actions.push({ type: "process_issue", title, body });

  if (!state.registryOk) {
    processIssue("Dispatcher: role registry check fails", `\`node scripts/check_registry.cjs\` fails, so the dispatcher starts nothing:\n\n${(state.registryProblems || []).join("\n")}`);
    return actions;
  }
  const active = roles.filter((r) => !r.parked);
  const labelOf = new Map(roles.map((r) => [r.label, r]));
  const sessions = state.sessions || {};

  // A PR ready for review gets the label of every applicable gate role, once.
  const prs = (state.prs || []).map((p) => ({ ...p, labels: [...p.labels] }));
  for (const pr of prs) {
    if (pr.draft || pr.labels.includes(GATES_ASSIGNED)) continue;
    const add = active
      .filter((r) => r.kind === "task" && r.wakes_on.includes("pr_ready_for_review") && (r.always || matches(pr.files || [], r.applies_to_paths)))
      .map((r) => r.label)
      .filter((l) => !pr.labels.includes(l));
    actions.push({ type: "label", item: pr.number, add: [...add, GATES_ASSIGNED], reason: "PR ready for review: gate roles assigned" });
    pr.labels.push(...add, GATES_ASSIGNED);
  }

  // Work per role: lane roles take Ready issues; task roles take open PRs with their label.
  const work = new Map(active.map((r) => [r.id, []]));
  for (const i of state.issues || []) {
    if (!i.labels.includes(settings.ready_label)) continue;
    const owners = i.labels.map((l) => labelOf.get(l)).filter(Boolean);
    if (!owners.length) {
      processIssue(`Dispatcher: Ready issue #${i.number} matches no role`, `#${i.number} has \`${settings.ready_label}\` but no registered \`agent:\` label. Relabel it, or start role discovery (template §5.9).`);
    }
    for (const r of owners) if (!r.parked && r.kind === "lane") work.get(r.id).push(i.number);
  }
  for (const pr of prs) {
    if (pr.draft) continue;
    for (const l of pr.labels) {
      const r = labelOf.get(l);
      if (r && !r.parked && r.kind === "task") work.get(r.id).push(pr.number);
    }
  }

  // Running sessions: idle, stalled, over the short-task cap.
  const running = new Set();
  for (const r of active) {
    const s = sessions[r.id];
    if (!s || !s.alive) continue;
    const idle = minutes(now, s.lastActivity || s.started);
    const has = work.get(r.id).length > 0;
    if (!has && idle >= settings.idle_exit_min) {
      actions.push({ type: "stop", role: r.id, reason: `idle ${Math.round(idle)} min with no work` });
      continue;
    }
    if (has && idle >= settings.stall_min) {
      if ((s.stalls || 0) >= 1) {
        actions.push({ type: "stop", role: r.id, item: s.item, requeue: r.kind === "lane", reason: `stalled twice (${Math.round(idle)} min)` });
        continue;
      }
      actions.push({ type: "nudge", role: r.id, item: s.item, reason: `no activity for ${Math.round(idle)} min` });
    }
    if (isGate(r) && !s.long && minutes(now, s.started) >= settings.short_task_cap_min) {
      actions.push({ type: "stop", role: r.id, item: s.item, queueLong: true, reason: `short task over short_task_cap_min (${settings.short_task_cap_min} min)` });
      continue;
    }
    running.add(r.id);
  }

  // Refill: Ready buffer below ready_min, or a plan review when everything is empty.
  const refill = settings.refill_role;
  if (refill && work.has(refill) && !running.has(refill) && !work.get(refill).length && minutes(now, memo.lastRefill) >= settings.stall_min) {
    const buildReady = active.filter((r) => BUILD_LANES.has(r.lane)).reduce((n, r) => n + work.get(r.id).length, 0);
    const anyReady = [...work.values()].some((w) => w.length);
    const backlog = (state.issues || []).filter((i) => !i.labels.includes(settings.ready_label) && !i.labels.includes(settings.in_progress_label)).length;
    if (buildReady < settings.ready_min && backlog > 0) {
      work.get(refill).push(null);
      actions.push({ type: "refill", reason: `build lanes have ${buildReady} Ready item(s), below ready_min` });
    } else if (!anyReady && backlog === 0) {
      work.get(refill).push(null);
      actions.push({ type: "refill", reason: "Backlog and Ready are empty: plan review" });
    }
  }

  // Start by priority; long work only within slots; nothing below the memory floor.
  const candidates = active.filter((r) => work.get(r.id).length && !running.has(r.id)).sort((a, b) => rank(a, settings) - rank(b, settings));
  if (state.freeGb < settings.start_new_below_free_gb) {
    if (candidates.length) actions.push({ type: "hold", reason: `free memory ${state.freeGb.toFixed(1)} GB is below start_new_below_free_gb` });
    return actions;
  }
  const isLong = (r) => !isGate(r) || Boolean(sessions[r.id] && (sessions[r.id].long || sessions[r.id].queueLong));
  let longRunning = active.filter((r) => running.has(r.id) && isLong(r)).length;
  let shortRunning = active.filter((r) => running.has(r.id) && !isLong(r)).length;
  for (const r of candidates) {
    const long = isLong(r);
    if (long && longRunning >= settings.slots) { actions.push({ type: "queue", role: r.id, reason: "no long-work slot free" }); continue; }
    if (!long && settings.short_tasks_max !== "unlimited" && shortRunning >= settings.short_tasks_max) { actions.push({ type: "queue", role: r.id, reason: "short_tasks_max reached" }); continue; }
    if (long) longRunning += 1; else shortRunning += 1;
    const item = work.get(r.id)[0];
    actions.push({ type: "start", role: r.id, item, long, reason: item === null ? "refill" : "work waiting" });
  }
  return actions;
}

module.exports = { decide, globToRe, GATES_ASSIGNED };
