#!/usr/bin/env node
// Stop hook (PDS 1.0 measurement-receipt pattern): an agent may not finish while
// UI files changed after the last passing `node scripts/ui_check.cjs`.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

let input = {};
try { input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch { /* no input */ }
if (input.stop_hook_active) process.exit(0); // already blocked once this turn: never loop

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
let changed = [];
try {
  changed = execFileSync('git', ['status', '--porcelain', '--', 'static/ctm', 'tribunal/templates'], { cwd: root, encoding: 'utf8' })
    .split('\n').filter(Boolean).map((l) => l.slice(3).trim()).filter((f) => !f.includes(' -> '));
} catch { process.exit(0); }
if (!changed.length) process.exit(0);

const mtime = (f) => { try { return fs.statSync(path.join(root, f)).mtimeMs; } catch { return 0; } };
const newest = Math.max(...changed.map(mtime));
const receipt = mtime('.tmp/ui-check-receipt.json');
if (receipt >= newest) process.exit(0);

process.stderr.write(
  `UI files changed after the last passing UI check (${changed.slice(0, 5).join(', ')}${changed.length > 5 ? ', ...' : ''}).\n` +
  'Run `node scripts/ui_check.cjs` and fix any failure before reporting this as done.\n'
);
process.exit(2);
