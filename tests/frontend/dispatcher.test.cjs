// Dispatcher rules (template v2.4 §6.2, D-0039): scripts/dispatcher/decide.cjs.
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { load } = require("../../scripts/lib/registry.cjs");
const { decide, globToRe } = require("../../scripts/dispatcher/decide.cjs");

const reg = load();
const NOW = Date.parse("2026-11-06T12:00:00Z");
const ago = (min) => new Date(NOW - min * 60000).toISOString();
const S = reg.settings;
const base = (over = {}) => ({
  now: NOW, settings: S, roles: reg.roles, registryOk: true, freeGb: 8,
  issues: [], prs: [], sessions: {}, memo: { lastRefill: ago(1) }, ...over,
});
const of = (actions, type) => actions.filter((a) => a.type === type);
const ready = (n, role) => ({ number: n, title: `t${n}`, labels: [`agent:${role}`, S.ready_label] });

test("glob matching for applies_to_paths", () => {
  assert.ok(globToRe("static/ctm/**").test("static/ctm/app.js"));
  assert.ok(globToRe(".github/workflows/**").test(".github/workflows/quality.yml"));
  assert.ok(!globToRe("ctm/settings*.py").test("ctm/urls.py"));
});

test("a Ready item starts its lane agent", () => {
  const a = decide(base({ issues: [ready(10, "ctm3-backend-engineer")] }));
  assert.deepStrictEqual(of(a, "start").map((x) => [x.role, x.item]), [["ctm3-backend-engineer", 10]]);
});

test("a running agent is not started twice", () => {
  const a = decide(base({ issues: [ready(10, "ctm3-backend-engineer")], sessions: { "ctm3-backend-engineer": { alive: true, started: ago(2), lastActivity: ago(1), item: 10 } } }));
  assert.strictEqual(of(a, "start").length, 0);
});

test("parked roles never start", () => {
  const a = decide(base({ issues: [ready(11, "ctm3-media-pipeline-engineer")] }));
  assert.strictEqual(of(a, "start").length, 0);
});

test("long work is capped at slots, highest priority first; gate roles run on top", () => {
  const lanes = ["ctm3-product-lead", "ctm3-design-director", "ctm3-backend-engineer", "ctm3-frontend-engineer", "ctm3-database-engineer", "ctm3-solution-architect"];
  const issues = lanes.map((r, i) => ready(20 + i, r)).concat([ready(30, "ctm3-release-engineer")]);
  const a = decide(base({ issues }));
  const long = of(a, "start").filter((x) => x.long);
  assert.strictEqual(long.length, S.slots);
  assert.ok(of(a, "start").some((x) => x.role === "ctm3-release-engineer" && !x.long), "release is a gate role");
  assert.ok(long.slice(0, 3).every((x) => ["ctm3-backend-engineer", "ctm3-frontend-engineer", "ctm3-database-engineer"].includes(x.role)), "build before design and spec");
  assert.strictEqual(of(a, "queue").length, lanes.length - S.slots);
});

test("a PR ready for review gets its applicable gate roles once", () => {
  const pr = { number: 5, draft: false, labels: [], files: ["static/ctm/app.js"] };
  const a = decide(base({ prs: [pr] }));
  const add = of(a, "label")[0].add;
  for (const l of ["agent:ctm3-code-reviewer", "agent:ctm3-qa-engineer", "agent:ctm3-design-critic", "agent:ctm3-a11y-rtl-auditor", "gates:assigned"]) assert.ok(add.includes(l), l);
  assert.ok(!add.includes("agent:ctm3-security-reviewer"));
  assert.strictEqual(of(decide(base({ prs: [{ ...pr, labels: ["gates:assigned"] }] })), "label").length, 0);
  assert.strictEqual(of(decide(base({ prs: [{ ...pr, draft: true }] })), "label").length, 0);
});

test("idle sessions with no work stop after idle_exit_min", () => {
  const a = decide(base({ sessions: { "ctm3-backend-engineer": { alive: true, started: ago(60), lastActivity: ago(S.idle_exit_min + 1) } } }));
  assert.deepStrictEqual(of(a, "stop").map((x) => x.role), ["ctm3-backend-engineer"]);
});

test("a stall is nudged once, then stopped and returned to Ready", () => {
  const issues = [ready(40, "ctm3-backend-engineer")];
  const s = { alive: true, started: ago(60), lastActivity: ago(S.stall_min + 1), item: 40 };
  assert.strictEqual(of(decide(base({ issues, sessions: { "ctm3-backend-engineer": s } })), "nudge").length, 1);
  const again = of(decide(base({ issues, sessions: { "ctm3-backend-engineer": { ...s, stalls: 1 } } })), "stop");
  assert.deepStrictEqual(again.map((x) => [x.role, x.requeue]), [["ctm3-backend-engineer", true]]);
});

test("a short task over short_task_cap_min stops and comes back as long work", () => {
  const prs = [{ number: 6, draft: false, labels: ["gates:assigned", "agent:ctm3-code-reviewer"], files: [] }];
  const a = decide(base({ prs, sessions: { "ctm3-code-reviewer": { alive: true, started: ago(S.short_task_cap_min + 1), lastActivity: ago(1), item: 6 } } }));
  assert.ok(of(a, "stop").some((x) => x.role === "ctm3-code-reviewer" && x.queueLong));
  const b = decide(base({ prs, sessions: { "ctm3-code-reviewer": { queueLong: true, alive: false } } }));
  assert.ok(of(b, "start").some((x) => x.role === "ctm3-code-reviewer" && x.long));
});

test("nothing starts below the memory floor", () => {
  const a = decide(base({ freeGb: S.start_new_below_free_gb - 0.5, issues: [ready(10, "ctm3-backend-engineer")] }));
  assert.strictEqual(of(a, "start").length, 0);
  assert.strictEqual(of(a, "hold").length, 1);
});

test("the Ready buffer below ready_min wakes the refill role, at most once per stall_min", () => {
  const backlog = [{ number: 50, title: "epic", labels: [] }];
  const a = decide(base({ issues: backlog, memo: {} }));
  assert.ok(of(a, "start").some((x) => x.role === S.refill_role && x.item === null));
  assert.strictEqual(of(decide(base({ issues: backlog, memo: { lastRefill: ago(1) } })), "refill").length, 0);
});

test("a Ready issue with no role and a failing registry open process issues", () => {
  const a = decide(base({ issues: [{ number: 60, title: "x", labels: [S.ready_label] }] }));
  assert.ok(of(a, "process_issue").some((x) => /#60 matches no role/.test(x.title)));
  const b = decide(base({ registryOk: false, issues: [ready(10, "ctm3-backend-engineer")] }));
  assert.deepStrictEqual(b.map((x) => x.type), ["process_issue"]);
});
