// Role registry loader and check (template v2.4 §5.1, §9 checks 13 and 15; D-0040).
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { execFileSync } = require("node:child_process");
const path = require("node:path");
const { parse, load } = require("../../scripts/lib/registry.cjs");

test("parses the registry subset: maps, lists of maps, inline lists, scalars, comments", () => {
  const r = parse("settings:\n  slots: 4   # c\n  label: status:ready\n  on: [a, b]\nroles:\n  - id: x\n    parked: false\n    skills: []\n  - id: y\n");
  assert.deepStrictEqual(r, { settings: { slots: 4, label: "status:ready", on: ["a", "b"] }, roles: [{ id: "x", parked: false, skills: [] }, { id: "y" }] });
});

test("rejects duplicate keys", () => {
  assert.throws(() => parse("a: 1\na: 2\n"), /duplicate key a/);
});

test("every ctm3 role definition has a registry entry with a label and a trigger", () => {
  const fs = require("node:fs");
  const reg = load();
  const ids = new Set(reg.roles.map((r) => r.id));
  for (const f of fs.readdirSync(path.join(__dirname, "..", "..", ".claude", "agents"))) {
    if (f.startsWith("ctm3-")) assert.ok(ids.has(f.replace(/\.md$/, "")), f);
  }
  for (const r of reg.roles) {
    assert.strictEqual(r.label, `agent:${r.id}`);
    assert.ok(r.wakes_on.length > 0, r.id);
  }
  assert.strictEqual(reg.roles.find((r) => r.id === "ctm3-media-pipeline-engineer").parked, true);
});

test("check_registry.cjs passes on the repository", () => {
  const out = execFileSync(process.execPath, [path.join(__dirname, "..", "..", "scripts", "check_registry.cjs")], { encoding: "utf8" });
  assert.match(out, /CTM role registry: OK/);
});
