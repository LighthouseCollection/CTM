#!/usr/bin/env node
// Fast UI check for agents: Plenix styling on changed files, EN/AR keys and the
// frontend contract tests. On success it writes .tmp/ui-check-receipt.json, which
// the Stop hook (.claude/hooks/require-fresh-check.cjs) reads before an agent may
// say a UI change is done.
//   node scripts/ui_check.cjs [--base <ref>]   (default base: HEAD)
'use strict';
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const base = args.includes('--base') ? args[args.indexOf('--base') + 1] : 'HEAD';
const testFiles = fs.readdirSync(path.join(ROOT, 'tests/frontend')).filter((f) => f.endsWith('.test.cjs')).map((f) => `tests/frontend/${f}`);

const steps = [
  ['Plenix styling', ['scripts/check_frontend_contract.cjs', '--base', base]],
  ['EN/AR keys', ['scripts/check_i18n.cjs', '--base', base]],
  ['Frontend tests', ['--test', ...testFiles]],
];
const results = [];
for (const [name, argv] of steps) {
  const r = spawnSync(process.execPath, argv, { cwd: ROOT, encoding: 'utf8' });
  const ok = r.status === 0;
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) console.log((r.stdout + r.stderr).split('\n').slice(-25).join('\n'));
}
if (results.every((r) => r.ok)) {
  fs.mkdirSync(path.join(ROOT, '.tmp'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, '.tmp/ui-check-receipt.json'), JSON.stringify({ at: new Date().toISOString(), base, results }, null, 2));
  console.log('UI check OK (receipt .tmp/ui-check-receipt.json)');
  process.exit(0);
}
process.exit(1);
