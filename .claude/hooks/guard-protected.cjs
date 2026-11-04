#!/usr/bin/env node
// PreToolUse guard: blocks edits to the approved contract and question bank.
// Exit code 2 blocks the tool call and shows stderr to Claude.
const fs = require('fs');

let input = '';
try { input = fs.readFileSync(0, 'utf8'); } catch { process.exit(0); }
let data;
try { data = JSON.parse(input); } catch { process.exit(0); }

const ti = data.tool_input || {};
const path = String(ti.file_path || ti.notebook_path || '').replace(/\\/g, '/');
if (!path) process.exit(0);

const rules = [
  [/\/docs\/architecture\/build-spec\//, 'docs/architecture/build-spec/ is the protected approved contract. Raise the conflict on GitHub instead of editing it.'],
  [/\/tribunal\/reference\/question-bank\.json$/, 'The accepted question bank wording is protected. Do not rewrite it.'],
];
// Owner decision 2026-11-04: agents may write .env and key files (deployment).
// Only the approved contract and the accepted question bank stay protected.

for (const [re, msg] of rules) {
  if (re.test(path)) {
    process.stderr.write(`BLOCKED by CTM guard: ${msg}\nPath: ${path}\n`);
    process.exit(2);
  }
}
process.exit(0);
