#!/usr/bin/env node
// Role registry checks (project-plan template v2.4 §9, checks 13 and 15).
//   13: every ctm3-* role has a registry entry, a definition, a work-item label
//       and at least one trigger; parked roles still need entry + definition.
//   15: no instruction document quotes a registry setting's value; documents
//       name the setting (`slots`) instead.
// Usage: node scripts/check_registry.cjs [--labels]   (--labels also checks the
// agent: labels exist on GitHub, using gh.)
"use strict";
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { ROOT, load } = require("./lib/registry.cjs");

const problems = [];
const rel = (p) => path.relative(ROOT, p).split(path.sep).join("/");

// Triggers the dispatcher understands (scripts/dispatcher, D-0039).
const TRIGGERS = new Set([
  "ready_item", "issue_opened", "comment_mention", "ready_below_min", "release_done",
  "heartbeat", "type_ui_issue", "api_change", "stall_alert", "daily", "weekly",
  "pr_touches_text", "public_api_changed", "pr_integrate_ready", "release_batch_ready",
  "pr_ready_for_review", "bug_ready", "fix_round_3",
]);
const SETTINGS = {
  slots: "number", reserved_gate_slots: "number", short_task_cap_min: "number",
  start_new_below_free_gb: "number", idle_exit_min: "number", stall_min: "number",
  heartbeat_min: "number", ready_min: "number", ready_label: "string",
  in_progress_label: "string", refill_role: "string", memory_limit_default: "string",
};
const MEMORY = /^\d+(\.\d+)?[MG]$/;
const SOURCE = /^(charter|[\w.-]+\/[\w.-]+@[0-9a-f]{7,40}:.+)$/;

let reg;
try { reg = load(); } catch (e) { console.error(`check_registry: ${e.message}`); process.exit(1); }
const settings = reg.settings || {};
const roles = Array.isArray(reg.roles) ? reg.roles : [];

// ---- check 13: registry ----
for (const [k, t] of Object.entries(SETTINGS)) {
  if (typeof settings[k] !== t) problems.push(`settings.${k}: missing or not a ${t}`);
}
if (!(settings.short_tasks_max === "unlimited" || typeof settings.short_tasks_max === "number")) {
  problems.push("settings.short_tasks_max: must be a number or 'unlimited'");
}
const priorities = Array.isArray(settings.priority) ? settings.priority : [];
if (!priorities.length) problems.push("settings.priority: missing list");

const ids = new Set();
for (const r of roles) {
  const where = `role ${r.id || "(no id)"}`;
  if (!r.id) { problems.push(`${where}: no id`); continue; }
  if (ids.has(r.id)) problems.push(`${where}: duplicate id`);
  ids.add(r.id);
  if (!["lane", "task"].includes(r.kind)) problems.push(`${where}: kind must be lane or task`);
  if (r.kind === "lane" && !r.lane) problems.push(`${where}: a lane role needs lane`);
  if (r.kind === "task" && !priorities.includes(r.priority)) problems.push(`${where}: priority must be one of settings.priority`);
  if (r.label !== `agent:${r.id}`) problems.push(`${where}: label must be agent:${r.id}`);
  if (typeof r.parked !== "boolean") problems.push(`${where}: parked must be true or false`);
  if (!SOURCE.test(String(r.source || ""))) problems.push(`${where}: source must be charter or <owner/repo>@<commit>:<path>`);
  if (!MEMORY.test(String(r.memory_limit || ""))) problems.push(`${where}: memory_limit like 1.5G`);
  if (!Number.isInteger(r.instances) || r.instances < 1) problems.push(`${where}: instances must be >= 1`);
  const wakes = Array.isArray(r.wakes_on) ? r.wakes_on : [];
  if (!wakes.length) problems.push(`${where}: needs at least one wakes_on trigger`);
  for (const w of wakes) if (!TRIGGERS.has(w)) problems.push(`${where}: unknown trigger ${w}`);
  for (const s of Array.isArray(r.skills) ? r.skills : [null]) {
    if (!s || !fs.existsSync(path.join(ROOT, ".claude", "skills", String(s), "SKILL.md"))) {
      problems.push(`${where}: skills must be a list of .claude/skills/<name> (bad: ${s})`);
    }
  }
  const def = path.join(ROOT, String(r.definition || ""));
  if (!r.definition || !fs.existsSync(def)) { problems.push(`${where}: definition ${r.definition} not found`); continue; }
  if (path.basename(def, ".md") !== r.id) problems.push(`${where}: definition file name must be ${r.id}.md`);
  const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(fs.readFileSync(def, "utf8"));
  const model = fm && /^model:\s*(\S+)/m.exec(fm[1]);
  if (!model || model[1] !== String(r.model)) problems.push(`${where}: model ${r.model} differs from ${r.definition} (${model ? model[1] : "none"})`);
}
for (const f of fs.readdirSync(path.join(ROOT, ".claude", "agents"))) {
  const id = path.basename(f, ".md");
  if (f.startsWith("ctm3-") && f.endsWith(".md") && !ids.has(id)) {
    problems.push(`.claude/agents/${f}: role has no entry in agents.config.yaml (it cannot be started)`);
  }
}
if (settings.refill_role && !ids.has(settings.refill_role)) problems.push(`settings.refill_role ${settings.refill_role} is not a role`);

if (process.argv.includes("--labels")) {
  const have = new Set(JSON.parse(execFileSync("gh", ["label", "list", "--limit", "500", "--json", "name"], { encoding: "utf8" })).map((l) => l.name));
  for (const l of [settings.ready_label, settings.in_progress_label, ...roles.map((r) => r.label)]) {
    if (!have.has(l)) problems.push(`GitHub label ${l} does not exist`);
  }
}

// ---- check 15: settings in prose ----
function walk(dir, out) {
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith(".md")) out.push(p);
  }
  return out;
}
const docs = [
  "CLAUDE.md", "AGENTS.md", "README.md", "docs/implementation/sdlc.md", "docs/MASTER_PLAN.md",
].map((f) => path.join(ROOT, f)).filter((f) => fs.existsSync(f));
for (const d of [".rulesync", ".claude/agents", ".claude/skills"]) walk(path.join(ROOT, d), docs);

const names = Object.keys(settings).filter((k) => typeof settings[k] === "number");
const nameNear = new RegExp(`\b(${names.join("|")})\b[^.;\n]{0,25}?\b\d+`);
const phrases = [
  /\b\d+\s+(long[- ]work\s+)?(slots|sessions|agents)\b/i,
  /\b\d+\s+long[- ]work\b/i,
  /\babout\s+\d+\s+min(ute)?s?\b/i,
  /\b(capped at|at most|up to)\s+\d+\s+(minutes|sessions|agents|slots)\b/i,
  /\b(capped at|at most|up to)\s+\d+\s*$/i, // the noun wrapped to the next line
  /\(now \d+\)/i,
];
for (const f of docs) {
  fs.readFileSync(f, "utf8").split(/\r?\n/).forEach((line, i) => {
    if (line.includes("registry-value-ok")) return;
    // Drop ids and section numbers so "D-0039" or "§4.4" never look like values.
    const s = line.replace(/\b[A-Z]{1,3}-\d+\b/g, "").replace(/#\d+/g, "").replace(/§[\d.]+/g, "")
      .replace(/\bG\d[a-e]?\b/g, "").replace(/\bcheck(s)? \d+( and \d+)?/gi, "");
    if (nameNear.test(s) || phrases.some((p) => p.test(s))) {
      problems.push(`${rel(f)}:${i + 1}: quotes a registry value; name the setting instead (check 15): ${line.trim().slice(0, 100)}`);
    }
  });
}

if (problems.length) {
  console.error(`CTM role registry: ${problems.length} problem(s)`);
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log(`CTM role registry: OK (${roles.length} roles, ${roles.filter((r) => r.parked).length} parked, ${docs.length} documents checked)`);
