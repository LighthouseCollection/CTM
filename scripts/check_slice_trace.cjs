#!/usr/bin/env node
// Traceability check for one slice: every acceptance ID named in brief.md must
// appear in design.md (tests section) and, once it exists, in evidence.md.
// Run: node scripts/check_slice_trace.cjs <slice-id> [--require-evidence]
const fs = require('fs');
const path = require('path');

const slice = process.argv[2];
if (!slice) { console.error('usage: check_slice_trace.cjs <slice-id> [--require-evidence]'); process.exit(2); }
const needEvidence = process.argv.includes('--require-evidence');
const dir = path.resolve(__dirname, '..', 'docs', 'implementation', 'slices', slice);
const read = (n) => { const p = path.join(dir, n); return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null; };

const brief = read('brief.md');
if (!brief) { console.error(`missing ${slice}/brief.md`); process.exit(1); }
const design = read('design.md');
const evidence = read('evidence.md');

// Spec acceptance IDs (SEC01, DEC02, UI01 ...), review findings (F01-F36) and slice IDs (AC-1, RF-1).
const idRe = /\b(?:[A-Z]{2,4}\d{2}|F\d{2}|AC-\d+|RF-\d+)\b/g;
const ids = [...new Set(brief.match(idRe) || [])].sort();
const problems = [];
if (!ids.length) problems.push('brief.md names no acceptance IDs');
for (const id of ids) {
  if (design !== null && !design.includes(id)) problems.push(`${id}: in brief.md but not in design.md`);
  if (design === null) { problems.push('design.md missing'); break; }
}
if (evidence !== null || needEvidence) {
  if (evidence === null) problems.push('evidence.md missing');
  else for (const id of ids) {
    const row = evidence.split(/\r?\n/).find((l) => l.includes(id) && l.trim().startsWith('|'));
    if (!row) problems.push(`${id}: no row in evidence.md`);
    else if (!/\b(PASS|FAIL|UNVERIFIED|CI-PENDING|NOT TESTED)\b/.test(row)) problems.push(`${id}: evidence row has no result`);
  }
}

if (problems.length) {
  console.log(`Slice trace ${slice}: ${problems.length} problem(s) for ${ids.length} ID(s)`);
  for (const p of problems) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`Slice trace ${slice}: OK (${ids.join(', ')})`);
