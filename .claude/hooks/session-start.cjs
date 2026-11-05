#!/usr/bin/env node
// SessionStart hook: load the lessons file and a short decision index into the
// agent's context, so past mistakes and owner decisions are never re-learned.
'use strict';
const fs = require('fs');
const path = require('path');

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const read = (f) => { try { return fs.readFileSync(path.join(root, f), 'utf8'); } catch { return ''; } };

const lessons = read('docs/lessons.md');
const decisions = read('decisions.yaml');
const index = [];
const re = /- id: (D-\d{4})[\s\S]*?decision: (.*)[\s\S]*?status: (\w+)/g;
let m;
while ((m = re.exec(decisions))) if (m[3] === 'active') index.push(`${m[1]}: ${m[2].trim().slice(0, 140)}`);

const out = [
  'CTM session context (from .claude/hooks/session-start.cjs).',
  'Rules: CLAUDE.md "Rules for every role". Never wait for the owner; check decisions.yaml before asking anything.',
  '',
  `Active decisions (${index.length}) - full entries in decisions.yaml:`,
  ...index.map((l) => '- ' + l),
  '',
  lessons.trim(),
].join('\n');
process.stdout.write(out + '\n');
