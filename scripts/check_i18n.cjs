#!/usr/bin/env node
// EN/AR dictionary check for static/ctm/*.js (owner: ctm3-i18n-engineer, gate G6).
// Finds each `en: {...}` / `ar: {...}` pair and reports: key missing in one
// language, empty Arabic, Arabic identical to English, placeholder mismatch.
//   node scripts/check_i18n.cjs                 all problems, exit 1 if any
//   node scripts/check_i18n.cjs --base <ref>    only problems not present at <ref>
//   node scripts/check_i18n.cjs --warn          never exit 1
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DIR = 'static/ctm';
const args = process.argv.slice(2);
const baseIdx = args.indexOf('--base');
const BASE = baseIdx >= 0 ? args[baseIdx + 1] : null;
const WARN = args.includes('--warn');

// Read one balanced {...} block starting at `open`, honouring strings and comments.
function block(src, open) {
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    const c = src[i];
    if (c === '"' || c === "'" || c === '`') {
      for (i++; i < src.length && src[i] !== c; i++) if (src[i] === '\\') i++;
      continue;
    }
    if (c === '/' && src[i + 1] === '/') { while (i < src.length && src[i] !== '\n') i++; continue; }
    if (c === '/' && src[i + 1] === '*') { i = src.indexOf('*/', i + 2); if (i < 0) return null; i++; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return src.slice(open, i + 1);
  }
  return null;
}

// Top-level `key: value` pairs of an object literal; value kept only when it is a plain string.
function entries(obj) {
  const out = new Map();
  let depth = 0;
  let expectKey = true;
  for (let i = 1; i < obj.length - 1; i++) {
    const c = obj[i];
    if (c === '"' || c === "'" || c === '`') {
      const start = i;
      for (i++; i < obj.length && obj[i] !== c; i++) if (obj[i] === '\\') i++;
      if (depth === 0 && expectKey) {
        const rest = obj.slice(i + 1).match(/^\s*:/);
        if (rest) { const key = obj.slice(start + 1, i); i += rest[0].length; readValue(key, i); }
      }
      continue;
    }
    if ('{[('.includes(c)) depth++;
    else if ('}])'.includes(c)) depth--;
    else if (c === ',' && depth === 0) expectKey = true;
    else if (depth === 0 && expectKey && /[A-Za-z_$]/.test(c)) {
      const m = obj.slice(i).match(/^([A-Za-z_$][\w$]*)\s*:/);
      if (m) { i += m[0].length - 1; readValue(m[1], i); }
      else expectKey = false;
    }
  }
  return out;

  // `at` is the index of the ':' after the key; only the value is inspected, not consumed.
  function readValue(key, at) {
    expectKey = false;
    const m = obj.slice(at + 1).match(/^\s*(["'`])((?:\\.|(?!\1)[^\\])*)\1\s*(?=[,}])/);
    out.set(key, m ? m[2] : null);
  }
}

const placeholders = (s) => (s.match(/\{[\w.]+\}|%\(?\w*\)?[sd]|\$\{[^}]+\}/g) || []).sort().join(' ');

function problemsFor(file, src) {
  const found = { en: [], ar: [] };
  const re = /\b(en|ar)\s*:\s*\{/g;
  let m;
  while ((m = re.exec(src))) {
    const body = block(src, m.index + m[0].length - 1);
    if (body) found[m[1]].push({ line: src.slice(0, m.index).split('\n').length, map: entries(body) });
  }
  const out = [];
  if (found.en.length !== found.ar.length) {
    out.push(`${file}: ${found.en.length} English dictionaries but ${found.ar.length} Arabic`);
  }
  const n = Math.min(found.en.length, found.ar.length);
  for (let k = 0; k < n; k++) {
    const en = found.en[k].map, ar = found.ar[k].map, where = `${file}:${found.ar[k].line}`;
    for (const key of en.keys()) if (!ar.has(key)) out.push(`${where}: Arabic missing key '${key}'`);
    for (const key of ar.keys()) if (!en.has(key)) out.push(`${where}: English missing key '${key}'`);
    for (const [key, ev] of en) {
      const av = ar.get(key);
      if (typeof ev !== 'string' || typeof av !== 'string') continue;
      if (ev.trim() && !av.trim()) out.push(`${where}: Arabic empty for '${key}'`);
      else if (av === ev && /[a-z]{3,}\s+[a-z]{3,}/i.test(ev)) out.push(`${where}: Arabic same as English for '${key}'`);
      if (placeholders(ev) !== placeholders(av)) out.push(`${where}: placeholders differ for '${key}' (${placeholders(ev) || 'none'} vs ${placeholders(av) || 'none'})`);
    }
  }
  return out;
}

function filesAt(ref) {
  if (!ref) return fs.readdirSync(path.join(ROOT, DIR)).filter((f) => f.endsWith('.js')).map((f) => `${DIR}/${f}`);
  try {
    return execFileSync('git', ['ls-tree', '--name-only', `${ref}:${DIR}`], { cwd: ROOT, encoding: 'utf8' })
      .split('\n').filter((f) => f.endsWith('.js')).map((f) => `${DIR}/${f}`);
  } catch { return []; }
}
const read = (ref, file) => {
  if (!ref) return fs.readFileSync(path.join(ROOT, file), 'utf8');
  try { return execFileSync('git', ['show', `${ref}:${file}`], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 << 20 }); }
  catch { return ''; }
};
// Compare without line numbers so moved code is not "new".
const strip = (p) => p.replace(/:\d+:/, ':');

const current = filesAt(null).flatMap((f) => problemsFor(f, read(null, f)));
let report = current;
if (BASE) {
  const before = new Map();
  for (const p of filesAt(BASE).flatMap((f) => problemsFor(f, read(BASE, f)))) before.set(strip(p), (before.get(strip(p)) || 0) + 1);
  report = current.filter((p) => { const k = strip(p); const left = before.get(k) || 0; if (left) { before.set(k, left - 1); return false; } return true; });
  console.log(`CTM i18n: ${current.length} problem(s) in total, ${report.length} new vs ${BASE}`);
} else {
  console.log(`CTM i18n: ${current.length} problem(s)`);
}
for (const p of report.slice(0, 200)) console.log('  - ' + p);
if (report.length > 200) console.log(`  ... and ${report.length - 200} more`);
process.exit(report.length && !WARN ? 1 : 0);
