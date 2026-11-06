#!/usr/bin/env node
// CTM dispatcher, mode P (template v2.4 §6, D-0039). Task Scheduler runs it every
// heartbeat_min from the dispatcher worktree; design: docs/implementation/slices/dispatcher/brief.md.
//   node scripts/dispatcher/poll.cjs                one poll: decide and act
//   node scripts/dispatcher/poll.cjs --dry-run      print the plan, change nothing
//   node scripts/dispatcher/poll.cjs --launch-test  G0: every non-parked role can be launched
// GitHub access is the host's gh login (a user token, never GITHUB_TOKEN; L-18).
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawn, spawnSync } = require("child_process");
const { ROOT, load } = require("../lib/registry.cjs");
const { decide } = require("./decide.cjs");

const REPO = process.env.CTM_REPO || "LighthouseCollection/CTM";
const STATE = process.env.CTM_DISPATCH_STATE || path.join(process.env.LOCALAPPDATA || os.homedir(), "ctm-dispatcher");
const CLAUDE = process.env.CTM_CLAUDE || "claude";
const HEARTBEAT_TITLE = "Dispatcher heartbeat";
const SIGN = "\n\n— ctm3-dispatcher (ctm3-delivery-lead)";
const DRY = process.argv.includes("--dry-run");
const LAUNCH_TEST = process.argv.includes("--launch-test");

const dir = (...p) => { const d = path.join(STATE, ...p); fs.mkdirSync(d, { recursive: true }); return d; };
const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return d; } };
const writeJson = (f, v) => fs.writeFileSync(f, JSON.stringify(v, null, 2));
const gh = (args) => execFileSync("gh", args, { encoding: "utf8", cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] });
const ghJson = (args) => JSON.parse(gh(args) || "null");
const log = (m) => {
  const line = `${new Date().toISOString()} ${m}`;
  console.log(line);
  if (!DRY) fs.appendFileSync(path.join(dir("logs"), "dispatcher.log"), line + "\n");
};

function alive(pid) { try { process.kill(pid, 0); return true; } catch (e) { return e.code === "EPERM"; } }

function hookSettings() {
  const script = path.join(ROOT, "scripts", "dispatcher", "activity-hook.cjs").split(path.sep).join("/");
  const hooks = [{ type: "command", command: `node "${script}"`, timeout: 10 }];
  const f = path.join(dir(), "hook-settings.json");
  writeJson(f, { hooks: { SessionStart: [{ hooks }], PostToolUse: [{ matcher: "*", hooks }], Stop: [{ hooks }] } });
  return f;
}

function launchArgs(role, settings, item, reason) {
  const prompt = [
    `You are ${role.id}, started by the CTM dispatcher (D-0039). Reason: ${reason}.`,
    item
      ? `Work item: https://github.com/${REPO}/issues/${item}.`
      : "No work item: refill the Ready queue from docs/MASTER_PLAN.md (template v2.4 §4.4), or run a plan review if Backlog is empty.",
    "Read CLAUDE.md and your definition first. Work only in your own git worktree (git worktree add ../ctm3-wt/<role>-<item> -b ctm3/<topic> origin/main); never switch branches in a shared checkout.",
    role.kind === "lane"
      ? `When you start an item, replace \`${settings.ready_label}\` with \`${settings.in_progress_label}\`. Work your lane's Ready items one at a time; when none are left, post "lane empty" on your last item and exit.`
      : `Fill your gate row on the PR (PASS / FAIL / N/A with a reason), then remove your \`${role.label}\` label and exit.`,
    "Desktop checks only, never mobile. Sign GitHub comments with your role. Do not wait for the owner. Keep cost low: no polling loops.",
  ].join("\n");
  const args = ["-p", prompt, "--agent", role.id, "--settings", hookSettings(), "--permission-mode", "bypassPermissions", "--output-format", "text"];
  if (role.model && role.model !== "inherit") args.push("--model", role.model);
  return args;
}

function memLimitMb(v) {
  const m = /^(\d+(?:\.\d+)?)([MG])$/.exec(String(v || ""));
  return m ? Math.round(Number(m[1]) * (m[2] === "G" ? 1024 : 1)) : 1536;
}

function start(role, settings, a) {
  const out = fs.openSync(path.join(dir("logs"), `${role.id}-${Date.now()}.log`), "a");
  const env = { ...process.env, CTM_ROLE: role.id, CTM_DISPATCH_STATE: STATE, NODE_OPTIONS: `--max-old-space-size=${memLimitMb(role.memory_limit)}` };
  const child = spawn(CLAUDE, launchArgs(role, settings, a.item, a.reason), { cwd: ROOT, env, detached: true, windowsHide: true, stdio: ["ignore", out, out] });
  child.unref();
  const now = new Date().toISOString();
  writeJson(path.join(dir("sessions"), `${role.id}.json`), { pid: child.pid, started: now, item: a.item, long: a.long, stalls: 0 });
  writeJson(path.join(dir("activity"), `${role.id}.json`), { ts: now, event: "launched" });
  return child.pid;
}

function stop(roleId) {
  const f = path.join(dir("sessions"), `${roleId}.json`);
  const s = readJson(f, null);
  if (s && s.pid && alive(s.pid)) {
    if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(s.pid), "/T", "/F"], { stdio: "ignore" });
    else { try { process.kill(s.pid); } catch { /* already gone */ } }
  }
  try { fs.unlinkSync(f); } catch { /* none */ }
  return s;
}

function gather(reg, memo) {
  const sessions = {};
  for (const r of reg.roles) {
    const f = path.join(dir("sessions"), `${r.id}.json`);
    const s = readJson(f, null);
    if (!s) continue;
    const act = readJson(path.join(dir("activity"), `${r.id}.json`), {});
    sessions[r.id] = { ...s, alive: Boolean(s.pid && alive(s.pid)), lastActivity: act.ts };
    // A finished session leaves its file behind; keep only the queueLong marker.
    if (!sessions[r.id].alive && !DRY) {
      if (!(s.queueLong && !s.pid)) { try { fs.unlinkSync(f); } catch { /* none */ } }
    }
  }
  const check = spawnSync(process.execPath, [path.join(ROOT, "scripts", "check_registry.cjs")], { encoding: "utf8" });
  const prs = ghJson(["pr", "list", "--repo", REPO, "--state", "open", "--limit", "100", "--json", "number,labels,isDraft,files"])
    .map((p) => ({ number: p.number, draft: p.isDraft, labels: p.labels.map((l) => l.name), files: (p.files || []).map((x) => x.path) }));
  const issues = ghJson(["issue", "list", "--repo", REPO, "--state", "open", "--limit", "500", "--json", "number,title,labels"])
    .map((i) => ({ number: i.number, title: i.title, labels: i.labels.map((l) => l.name) }));
  return {
    now: Date.now(), settings: reg.settings, roles: reg.roles, registryOk: check.status === 0,
    registryProblems: (check.stderr || "").split("\n").filter(Boolean), freeGb: os.freemem() / 1024 ** 3,
    issues, prs, sessions, memo,
  };
}

function heartbeat(state, actions, memo) {
  const day = Date.now() - 864e5;
  const running = Object.values(state.sessions).filter((x) => x.alive).length;
  const stalled = actions.filter((a) => a.type === "nudge" || (a.type === "stop" && a.requeue)).length;
  const lanes = {};
  for (const r of state.roles.filter((x) => x.kind === "lane" && !x.parked)) {
    lanes[r.lane] = (lanes[r.lane] || 0) + state.issues.filter((i) => i.labels.includes(r.label) && i.labels.includes(state.settings.ready_label)).length;
  }
  const body = [
    "Updated by the CTM dispatcher (mode P, D-0039) on every poll. The daily watchdog (`dispatcher-watchdog.yml`) opens a `process` issue when this is older than 2 × `heartbeat_min`.",
    "",
    `**Last poll:** ${new Date().toISOString()} on ${os.hostname()}`,
    `**Health:** sessions running ${running}, stalled ${stalled}; Ready per lane: ${Object.entries(lanes).map(([k, v]) => `${k} ${v}`).join(", ")}; roles launched in 24 h: ${(memo.launches || []).filter((t) => t > day).length}; nudges in 24 h: ${(memo.nudges || []).filter((t) => t > day).length} (target 0); free memory ${state.freeGb.toFixed(1)} GB.`,
    "",
    "**This poll:**",
    ...(actions.length ? actions.map((a) => `- ${a.type}${a.role ? ` ${a.role}` : ""}${a.item ? ` #${a.item}` : ""}: ${a.reason || a.title || ""}`) : ["- nothing to do"]),
    SIGN.trim(),
  ].join("\n");
  let num = memo.heartbeatIssue;
  if (!num) {
    const found = ghJson(["issue", "list", "--repo", REPO, "--state", "open", "--search", `"${HEARTBEAT_TITLE}" in:title`, "--json", "number,title"]).find((i) => i.title === HEARTBEAT_TITLE);
    num = found ? found.number : Number(/(\d+)\s*$/.exec(gh(["issue", "create", "--repo", REPO, "--title", HEARTBEAT_TITLE, "--body", body]).trim())[1]);
    try { gh(["issue", "pin", String(num), "--repo", REPO]); } catch { /* pin limit reached */ }
    memo.heartbeatIssue = num;
  }
  gh(["issue", "edit", String(num), "--repo", REPO, "--body", body]);
}

function act(state, actions, memo) {
  const roles = new Map(state.roles.map((r) => [r.id, r]));
  const S = state.settings;
  for (const a of actions) {
    try {
      if (a.type === "label") {
        gh(["issue", "edit", String(a.item), "--repo", REPO, "--add-label", a.add.join(",")]);
      } else if (a.type === "start") {
        const pid = start(roles.get(a.role), S, a);
        (memo.launches = memo.launches || []).push(Date.now());
        log(`started ${a.role} pid ${pid} item ${a.item}`);
      } else if (a.type === "stop") {
        stop(a.role);
        if (a.requeue && a.item) {
          gh(["issue", "edit", String(a.item), "--repo", REPO, "--remove-label", S.in_progress_label, "--add-label", S.ready_label]);
          gh(["issue", "comment", String(a.item), "--repo", REPO, "--body", `${a.role} stalled twice (${a.reason}); the session was stopped and this item is back in Ready. ctm3-delivery-lead: add the cause to docs/lessons.md.${SIGN}`]);
        }
        if (a.queueLong) writeJson(path.join(dir("sessions"), `${a.role}.json`), { queueLong: true });
        log(`stopped ${a.role}: ${a.reason}`);
      } else if (a.type === "nudge") {
        if (a.item) gh(["issue", "comment", String(a.item), "--repo", REPO, "--body", `${a.role}: ${a.reason} while this is assigned. Continue, or post a ruling and move on.${SIGN}`]);
        const f = path.join(dir("sessions"), `${a.role}.json`);
        const s = readJson(f, {});
        s.stalls = (s.stalls || 0) + 1;
        writeJson(f, s);
        (memo.nudges = memo.nudges || []).push(Date.now());
      } else if (a.type === "process_issue") {
        const exists = ghJson(["issue", "list", "--repo", REPO, "--state", "open", "--search", `"${a.title}" in:title`, "--json", "title"]).some((i) => i.title === a.title);
        if (!exists) gh(["issue", "create", "--repo", REPO, "--title", a.title, "--body", a.body + SIGN, "--label", "process", "--label", "sev:S1"]);
      } else if (a.type === "refill") {
        memo.lastRefill = new Date().toISOString();
      } else {
        log(`${a.type} ${a.role || ""}: ${a.reason}`);
      }
    } catch (e) {
      log(`FAILED ${a.type} ${a.role || a.item || ""}: ${String(e.stderr || e.message).trim()}`);
    }
  }
}

function launchTest(reg) {
  const v = spawnSync(CLAUDE, ["--version"], { encoding: "utf8" });
  let bad = v.status === 0 ? 0 : 1;
  console.log(`claude: ${v.status === 0 ? v.stdout.trim() : "NOT FOUND (set CTM_CLAUDE)"}`);
  for (const r of reg.roles) {
    const def = fs.existsSync(path.join(ROOT, r.definition));
    if (!def) bad += 1;
    if (r.parked) { console.log(`- ${r.id}: parked; entry and definition ${def ? "ok" : "MISSING"}`); continue; }
    const args = launchArgs(r, reg.settings, 1, "launch test");
    console.log(`- ${r.id}: ${def ? "ok" : "definition MISSING"} -> claude --agent ${r.id}${args.includes("--model") ? ` --model ${r.model}` : ""}`);
  }
  console.log(bad ? `launch test: ${bad} problem(s)` : "launch test: OK");
  process.exitCode = bad ? 1 : 0;
}

function main() {
  // Only the dispatcher's own worktree (install.sh) follows origin/main; never move a dev checkout.
  if (!DRY && !LAUNCH_TEST && /[\\/]ctm3-wt[\\/]dispatcher$/.test(ROOT)) {
    spawnSync("git", ["-C", ROOT, "fetch", "-q", "origin", "main"], { stdio: "ignore" });
    spawnSync("git", ["-C", ROOT, "checkout", "-q", "--detach", "origin/main"], { stdio: "ignore" });
  }
  const reg = load();
  if (LAUNCH_TEST) return launchTest(reg);
  const memoFile = path.join(dir(), "memo.json");
  const memo = readJson(memoFile, {});
  const day = Date.now() - 864e5;
  memo.launches = (memo.launches || []).filter((t) => t > day);
  memo.nudges = (memo.nudges || []).filter((t) => t > day);
  const state = gather(reg, memo);
  const actions = decide(state);
  if (DRY) {
    for (const a of actions) console.log(JSON.stringify(a));
    console.log(`dry run: ${actions.length} action(s), free memory ${state.freeGb.toFixed(1)} GB`);
    return;
  }
  act(state, actions, memo);
  try { heartbeat(state, actions, memo); } catch (e) { log(`FAILED heartbeat: ${String(e.stderr || e.message).trim()}`); }
  writeJson(memoFile, memo);
}

main();
