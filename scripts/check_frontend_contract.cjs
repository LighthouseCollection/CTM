#!/usr/bin/env node
// Fast deterministic gate for CTM frontend rules. Run: node scripts/check_frontend_contract.cjs
// 1. One Plenix CDN version everywhere (the version pinned in ctm/settings.py).
// 2. No raw colors, numeric font sizes, !important or inline style props in council/applicant JS.
// 3. Data font: known data fields marked as data, names not (scripts/check_data_font.cjs, #325).
// Exit 1 on violations. Use --warn to report without failing.
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const warnOnly = process.argv.includes('--warn');
// --base <ref>: only check files changed since <ref> (used by CI and the pre-commit hook).
const baseIdx = process.argv.indexOf('--base');
let changedSet = null;
if (baseIdx > -1) {
  const { execSync } = require('child_process');
  const base = process.argv[baseIdx + 1];
  const out = (cmd) => execSync(cmd, { cwd: root }).toString().split(/\r?\n/).filter(Boolean);
  changedSet = new Set([...out(`git diff --name-only ${base}`), ...out('git ls-files --others --exclude-standard')]);
}
const inScope = (f) => !changedSet || changedSet.has(path.relative(root, f).replace(/\\/g, '/'));
const problems = [];

function walk(dir, exts, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['node_modules', '.git', '.venv', '.tmp', 'staticfiles'].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, exts, out);
    else if (exts.includes(path.extname(e.name))) out.push(p);
  }
  return out;
}
const rel = (p) => path.relative(root, p).replace(/\\/g, '/');

// 1. CDN pin consistency
const settings = fs.readFileSync(path.join(root, 'ctm', 'settings.py'), 'utf8');
const pinMatch = settings.match(/design-system\.lighthouseway\.org\/cdn\/(\d+\.\d+\.\d+)/);
const pin = pinMatch && pinMatch[1];
if (!pin) problems.push('ctm/settings.py: could not find the pinned Plenix CDN version');

const cdnFiles = walk(root, ['.py', '.js', '.cjs', '.html'])
  .filter((f) => !rel(f).startsWith('docs/') && inScope(f));
for (const f of cdnFiles) {
  const text = fs.readFileSync(f, 'utf8');
  for (const m of text.matchAll(/design-system\.lighthouseway\.org\/cdn\/(\d+\.\d+\.\d+)/g)) {
    if (pin && m[1] !== pin) problems.push(`${rel(f)}: Plenix CDN ${m[1]} differs from pinned ${pin}`);
  }
}

// 2. Styling rules in application JS/HTML (the RTL bridge is the documented exception)
const uiFiles = walk(path.join(root, 'static', 'ctm'), ['.js', '.html', '.css'])
  .concat(walk(path.join(root, 'tribunal', 'templates'), ['.html']))
  .filter(inScope);
const checks = [
  [/#[0-9a-fA-F]{3,8}\b(?=["'`;\s)])/g, 'raw hex color (use --plx-sys-*/--plx-comp-* tokens)'],
  [/\brgba?\(\s*\d/g, 'raw rgb() color (use Plenix tokens)'],
  [/!important/g, '!important is not allowed'],
  [/fontSize\s*:\s*['"]?\d/g, 'numeric font size (use Plenix typography)'],
  [/\bstyle\s*=\s*\{\s*\{/g, 'inline style object (use plx- classes / documented components)'],
  [/\sstyle\s*=\s*["']/g, 'inline style attribute'],
];
for (const f of uiFiles) {
  const r = rel(f);
  if (/rtl|arabic-styling/i.test(r)) continue;
  // Server-rendered print/PDF templates (WeasyPrint) cannot load the Plenix CDN.
  if (/_print\.html$|_pdf\.html$|\/pdf\//.test(r)) continue;
  const lines = fs.readFileSync(f, 'utf8').split(/\r?\n/);
  lines.forEach((line, i) => {
    if (/ctm-contract-allow/.test(line)) return; // explicit, reviewed exception
    for (const [re, msg] of checks) {
      re.lastIndex = 0;
      if (re.test(line)) problems.push(`${r}:${i + 1}: ${msg}`);
    }
  });
}

// 3. The data font rule (#325, owner 2026-11-10): known data fields carry the Plenix data marking, names never do.
const { findDataFontProblems } = require('./check_data_font.cjs');
for (const f of uiFiles.filter((f) => f.endsWith('.js') && path.dirname(f) === path.join(root, 'static', 'ctm'))) {
  problems.push(...findDataFontProblems(fs.readFileSync(f, 'utf8'), rel(f)));
}

if (problems.length) {
  console.log(`CTM frontend contract: ${problems.length} problem(s)`);
  for (const p of problems) console.log(`  - ${p}`);
  process.exit(warnOnly ? 0 : 1);
}
console.log(`CTM frontend contract: OK (Plenix CDN ${pin})`);
