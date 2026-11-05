#!/usr/bin/env node
// Checks that the files changed on this branch belong to the stream that changed them.
// Run: node scripts/check_ownership.cjs [--slice <slice-id>] [--role <owner>] [--base <ref>]
//
// Two sources of truth, strictest wins:
// 1. Global protected paths: only the database owner may touch migrations / RLS / grants.
// 2. Optional slice ownership block in docs/implementation/slices/<id>/design.md:
//      ```owners
//      backend: tribunal/services/decrees.py, tribunal/decree_api.py, tests/test_decree_*.py
//      council-frontend: static/ctm/council-decree.js, tests/frontend/council-decree*.test.cjs
//      database: tribunal/migrations/*
//      ```
//    With --role, every changed file must match that role's globs.
//    Without --role, every changed file must match SOME role's globs.
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const arg = (name, dflt) => {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : dflt;
};
const base = arg('--base', 'origin/main');
const slice = arg('--slice');
const role = arg('--role');

// Committed changes on the branch + uncommitted edits + untracked files.
const lines = (cmd) => execSync(cmd, { cwd: root }).toString().split(/\r?\n/).filter(Boolean);
const changed = [...new Set([
  ...lines(`git diff --name-only ${base}...HEAD`),
  ...lines('git diff --name-only HEAD'),
  ...lines('git ls-files --others --exclude-standard'),
])];

const globToRe = (g) => new RegExp('^' + g.trim()
  .replace(/[.+^${}()|[\]\\]/g, '\\$&')
  .replace(/\*\*/g, '\u0000').replace(/\*/g, '[^/]*').replace(/\u0000/g, '.*') + '$');

const problems = [];

// 1. Database-owned paths. Only the 'database' role (or a branch whose name says so) may change them.
const dbOwned = [/^tribunal\/migrations\//, /^tribunal\/db\//, /^deploy\/postgres\//];
// CI checks out a detached merge commit ('HEAD'); the PR branch name is in GITHUB_HEAD_REF.
const localBranch = execSync('git rev-parse --abbrev-ref HEAD', { cwd: root }).toString().trim();
const branch = localBranch === 'HEAD' && process.env.GITHUB_HEAD_REF ? process.env.GITHUB_HEAD_REF : localBranch;
const isDbStream = role === 'database' || /vm-frm|backend|database|schema/.test(branch);
for (const f of changed) {
  if (dbOwned.some((re) => re.test(f)) && !isDbStream) {
    problems.push(`${f}: database-owned path changed on '${branch}'${role ? ` by role '${role}'` : ''}. Only the database/backend stream writes migrations, RLS and grants.`);
  }
}

// 2. Slice ownership block.
if (slice) {
  const designPath = path.join(root, 'docs', 'implementation', 'slices', slice, 'design.md');
  if (!fs.existsSync(designPath)) {
    problems.push(`slice '${slice}': ${path.relative(root, designPath)} not found`);
  } else {
    const m = fs.readFileSync(designPath, 'utf8').match(/```owners\s*\n([\s\S]*?)```/);
    if (!m) {
      problems.push(`slice '${slice}': design.md has no \`\`\`owners block`);
    } else {
      const owners = {};
      for (const line of m[1].split(/\r?\n/)) {
        const mm = line.match(/^\s*([\w-]+)\s*:\s*(.+)$/);
        if (mm) owners[mm[1]] = mm[2].split(',').map(globToRe);
      }
      const docsOk = (f) => f.startsWith(`docs/implementation/slices/${slice}/`);
      for (const f of changed) {
        if (docsOk(f)) continue;
        if (role) {
          if (!owners[role]) { problems.push(`role '${role}' is not in the owners block`); break; }
          if (!owners[role].some((re) => re.test(f))) problems.push(`${f}: not owned by '${role}' in ${slice}/design.md`);
        } else {
          const who = Object.keys(owners).filter((r) => owners[r].some((re) => re.test(f)));
          if (who.length === 0) problems.push(`${f}: not listed in any owner's globs in ${slice}/design.md`);
          if (who.length > 1) problems.push(`${f}: owned by several roles (${who.join(', ')}) - give shared files one owner`);
        }
      }
    }
  }
}

if (problems.length) {
  console.log(`Ownership: ${problems.length} problem(s) in ${changed.length} changed file(s)`);
  for (const p of [...new Set(problems)]) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`Ownership: OK (${changed.length} changed file(s) vs ${base}${slice ? `, slice ${slice}` : ''}${role ? `, role ${role}` : ''})`);
