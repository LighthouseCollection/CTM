#!/usr/bin/env node
// PreToolUse guard: blocks edits to protected sources and secrets.
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
  [/(^|\/)\.env(\.|$)(?!example)/, 'Never write secrets files. Use deploy/.env.example for documented keys only.'],
  [/\.(pem|key|p12|pfx)$/, 'Never write private keys or certificates.'],
];

for (const [re, msg] of rules) {
  if (re.test(path)) {
    process.stderr.write(`BLOCKED by CTM guard: ${msg}\nPath: ${path}\n`);
    process.exit(2);
  }
}
process.exit(0);
