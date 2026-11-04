#!/usr/bin/env node
// Moves every Plenix CDN reference in CTM to one version.
//   node scripts/bump_plenix.cjs 0.86.0      set an explicit version
//   node scripts/bump_plenix.cjs latest      read cdn/latest.json
//   node scripts/bump_plenix.cjs --current   print the pinned version
//   node scripts/bump_plenix.cjs --verify    check every referenced CDN file exists at the pin
// Exit codes: 0 changed or already current (prints "current=<v>" / "updated=<old>-><new>"), 1 error.
const fs = require('fs');
const path = require('path');
const https = require('https');

const root = path.resolve(__dirname, '..');
const CDN = 'https://design-system.lighthouseway.org/cdn';
const PIN_RE = /design-system\.lighthouseway\.org\/cdn\/(\d+\.\d+\.\d+)\//g;
const SKIP_DIRS = new Set(['.git', 'node_modules', '.venv', '.tmp', 'staticfiles', 'docs']);
const SELF = path.resolve(__filename);
const EXTS = new Set(['.py', '.js', '.cjs', '.html', '.json']);

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (EXTS.has(path.extname(e.name)) && path.resolve(p) !== SELF) out.push(p);
  }
  return out;
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode !== 200) { res.resume(); return reject(new Error(`${url} -> HTTP ${res.statusCode}`)); }
      let body = '';
      res.on('data', (c) => (body += c));
      res.on('end', () => { try { resolve(JSON.parse(body)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}


function statusOf(url) {
  return new Promise((resolve) => {
    const req = https.request(url, { method: 'HEAD' }, (res) => { res.resume(); resolve(res.statusCode); });
    req.on('error', () => resolve(0));
    req.setTimeout(15000, () => { req.destroy(); resolve(0); });
    req.end();
  });
}

// Every CDN file CTM references at the pinned version must exist (catches removed files,
// e.g. icons-all.css was dropped from Plenix, which string-based tests cannot see).
async function verify(version) {
  const urls = new Set();
  const re = new RegExp('design-system\\.lighthouseway\\.org/cdn/' + version.replace(/\./g, '\\.') + '/([A-Za-z0-9_./-]+)', 'g');
  for (const f of walk(root)) {
    if (/[\\/]tests?[\\/]/.test(f)) continue;
    for (const m of fs.readFileSync(f, 'utf8').matchAll(re)) urls.add(m[1].replace(/[.,]+$/, ''));
  }
  const missing = [];
  for (const u of [...urls].sort()) {
    if (u.endsWith('/')) continue;
    const code = await statusOf(`${CDN}/${version}/${u}`);
    if (code !== 200) missing.push(`${u} -> HTTP ${code}`);
  }
  if (missing.length) {
    console.log(`verify=FAIL version=${version} missing=${missing.length}`);
    for (const m of missing) console.log(`  - ${m}`);
    process.exit(1);
  }
  console.log(`verify=OK version=${version} files=${urls.size}`);
}

function currentPin() {
  const s = fs.readFileSync(path.join(root, 'ctm', 'settings.py'), 'utf8');
  const m = s.match(/PLENIX_BASE\s*=\s*"https:\/\/design-system\.lighthouseway\.org\/cdn\/(\d+\.\d+\.\d+)\/"/);
  if (!m) throw new Error('PLENIX_BASE not found in ctm/settings.py');
  return m[1];
}

async function main() {
  const arg = process.argv[2];
  if (!arg) throw new Error('usage: bump_plenix.cjs <version|latest|--current>');
  const old = currentPin();
  if (arg === '--current') { console.log(old); return; }
  if (arg === '--verify') { await verify(old); return; }

  let target = arg;
  if (arg === 'latest') {
    const latest = await getJson(`${CDN}/latest.json`);
    const pin = latest.pins && latest.pins.ctm; // a "ctm" pin in latest.json holds CTM on a version
    target = pin || latest.latest;
  }
  if (!/^\d+\.\d+\.\d+$/.test(target)) throw new Error(`not a version: ${target}`);
  // The version must really exist on the CDN before anything is changed.
  await getJson(`${CDN}/${target}/docs/index.json`);

  if (target === old) { console.log(`current=${old}`); return; }

  const esc = target.replace(/\./g, '\\.');
  const oldEsc = old.replace(/\./g, '\\.');
  let files = 0;
  for (const f of walk(root)) {
    const text = fs.readFileSync(f, 'utf8');
    const next = text
      .replace(PIN_RE, `design-system.lighthouseway.org/cdn/${target}/`)
      // short form used in tests, e.g. a quoted cdn/<version>/plenix.js
      .replace(/(["'`])cdn\/\d+\.\d+\.\d+\//g, `$1cdn/${target}/`)
      // regex forms in tests: cdn\/0\.68\.0 and (?!0\.68\.0)
      .replace(/cdn\\\/\d+\\\.\d+\\\.\d+/g, `cdn\\/${esc}`)
      .replace(new RegExp(oldEsc.replace(/\\/g, '\\\\'), 'g'), esc);
    if (next !== text) { fs.writeFileSync(f, next); files++; }
  }
  console.log(`updated=${old}->${target} files=${files}`);
}

main().catch((e) => { console.error(`bump_plenix: ${e.message}`); process.exit(1); });
