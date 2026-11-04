#!/usr/bin/env node
// Lints migrations added or changed on this branch versus a base ref.
// Run: node scripts/check_migration_diff.cjs [base-ref]   (default origin/main)
// Catches problems that previously reached main: irreversible RunSQL, demo data
// shipped as schema migrations, weakened history guards, unsafe SECURITY DEFINER,
// and duplicate migration numbers.
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const base = process.argv[2] || 'origin/main';
const migDir = 'tribunal/migrations';

let changed = [];
try {
  changed = execSync(`git diff --name-only --diff-filter=AM ${base}...HEAD -- ${migDir}`, { cwd: root })
    .toString().split(/\r?\n/).filter((f) => /\.(py|sql)$/.test(f) && !/__init__/.test(f));
} catch (e) {
  console.error(`Could not diff against ${base}: ${e.message}`);
  process.exit(1);
}

const problems = [];
const warnings = [];
for (const f of changed) {
  // Ignore Python (#) and SQL (--) comment lines so a mention is not a finding.
  const text = fs.readFileSync(path.join(root, f), 'utf8')
    .split(/\r?\n/).filter((l) => !/^\s*(#|--)/.test(l)).join('\n');
  const name = path.basename(f);
  if (/demo|fictitious|fixture|sample/i.test(name)) {
    problems.push(`${f}: looks like demo/seed data. Use a gated management command (seed_demo), not a schema migration.`);
  }
  if (f.endsWith('.py')) {
    const runSqlCount = (text.match(/RunSQL\s*\(/g) || []).length;
    // Reverse given as keyword (reverse_sql=...) or as the second positional argument.
    const reverseCount = (text.match(/reverse_sql\s*=/g) || []).length
      + (text.match(/RunSQL\s*\(\s*[A-Za-z_][\w.]*\s*,\s*(?!reverse_sql|state_operations|hints|elidable)[A-Za-z_][\w.]*\s*[,)]/g) || []).length;
    if (runSqlCount > reverseCount) problems.push(`${f}: ${runSqlCount} RunSQL but ${reverseCount} reverse_sql - every RunSQL must be reversible.`);
    const runPyCount = (text.match(/RunPython\s*\(/g) || []).length;
    const runPyRev = (text.match(/RunPython\s*\([^)]*,\s*(reverse_code\s*=\s*)?[A-Za-z_.]+/g) || []).length;
    if (runPyCount > runPyRev) problems.push(`${f}: RunPython without reverse_code.`);
  }
  if (/SECURITY\s+DEFINER/i.test(text) && !/SET\s+search_path/i.test(text)) {
    problems.push(`${f}: SECURITY DEFINER without a pinned search_path.`);
  }
  if (/\bBYPASSRLS\b/i.test(text) && !/NOBYPASSRLS/i.test(text)) {
    problems.push(`${f}: grants BYPASSRLS - not allowed for runtime roles.`);
  }
  // Reverse SQL legitimately disables RLS and drops triggers, so these are review warnings.
  if (/NO\s+FORCE\s+ROW\s+LEVEL\s+SECURITY|DISABLE\s+ROW\s+LEVEL\s+SECURITY/i.test(text)) {
    warnings.push(`${f}: disables/unforces RLS (expected only in reverse_sql) - confirm.`);
  }
  if (/DROP\s+TRIGGER/i.test(text) || /RETURN\s+OLD\s*;/i.test(text)) {
    warnings.push(`${f}: drops a trigger or returns OLD - confirm history guards are not weakened.`);
  }
}

// Duplicate leading numbers among ALL migrations is fine only if a merge migration exists;
// flag new files that reuse an existing number.
const all = fs.readdirSync(path.join(root, migDir)).filter((n) => /^\d{4}_.*\.py$/.test(n));
const byNum = {};
for (const n of all) (byNum[n.slice(0, 4)] ||= []).push(n);
for (const f of changed.filter((x) => x.endsWith('.py'))) {
  const n = path.basename(f).slice(0, 4);
  if ((byNum[n] || []).length < 2) continue;
  const merged = all.some((m) => /_merge/.test(m) && m.slice(0, 4) >= n);
  const msg = `${f}: migration number ${n} is shared by ${byNum[n].join(', ')}`;
  if (merged) warnings.push(`${msg} (a later merge migration exists).`);
  else problems.push(`${msg} - renumber or add a merge migration.`);
}

if (warnings.length) {
  console.log(`Migration lint: ${warnings.length} review warning(s)`);
  for (const w of warnings) console.log(`  ~ ${w}`);
}
if (problems.length) {
  console.log(`Migration lint: ${problems.length} problem(s) in ${changed.length} changed file(s)`);
  for (const p of problems) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`Migration lint: OK (${changed.length} changed migration file(s) vs ${base})`);
