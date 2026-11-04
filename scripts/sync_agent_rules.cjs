#!/usr/bin/env node
// Keeps agent instructions identical for every coding agent on CTM.
// CLAUDE.md is the single source; AGENTS.md (read by Codex and other agents) is generated.
//   node scripts/sync_agent_rules.cjs          write AGENTS.md
//   node scripts/sync_agent_rules.cjs --check  exit 1 if AGENTS.md is out of date (CI)
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const src = path.join(root, 'CLAUDE.md');
const dst = path.join(root, 'AGENTS.md');
const header =
  '<!-- GENERATED from CLAUDE.md by scripts/sync_agent_rules.cjs. Do not edit; edit CLAUDE.md and re-run. -->\n\n';

const body = fs.readFileSync(src, 'utf8').replace(/\r\n/g, '\n')
  .replace(/^# CTM — instructions for Claude Code/m, '# CTM — instructions for coding agents (Claude, Codex, others)');
const expected = header + body;

if (process.argv.includes('--check')) {
  const actual = fs.existsSync(dst) ? fs.readFileSync(dst, 'utf8').replace(/\r\n/g, '\n') : '';
  if (actual !== expected) {
    console.log('Agent rules: AGENTS.md is out of date. Run: node scripts/sync_agent_rules.cjs');
    process.exit(1);
  }
  console.log('Agent rules: OK (AGENTS.md matches CLAUDE.md)');
} else {
  fs.writeFileSync(dst, expected);
  console.log('Agent rules: wrote AGENTS.md from CLAUDE.md');
}
