#!/usr/bin/env node
// Template v2.4 check 16 (gap G-6, lesson L-18): a pull request, merge, push or
// label made with GITHUB_TOKEN starts no other workflow. Every workflow step that
// does one of these with GITHUB_TOKEN (or github.token, also as a `||` fallback)
// must end in an explicit `gh workflow run` / repository_dispatch, or be listed in
// .github/handoffs-allow.json with a reason (reports nobody has to react to).
//
// Reads workflow files line by line (no YAML library in this repo): jobs at two
// spaces, steps as `- ` items under `steps:`. Scripts a step calls are not read.
const fs = require('fs');
const path = require('path');

const KINDS = [
  ['pull request', /\bgh pr create\b|\bpulls\.create\b|\bcreatePullRequest\b/],
  ['merge', /\bgh pr merge\b|\bgh api\b.*\/(merges|pulls\/[^/\s]+\/merge)\b|\bpulls\.merge\b|\bmergePullRequest\b/],
  ['push', /\bgit push\b|\bgit\.createRef\b|\bgh api\b.*git\/refs\b/],
  ['label', /--add-label\b|\bgh (issue|pr) create\b.*--label\b|\bgh api\b(?=.*\/labels\b)(?=.*(-X|--method)\s*POST)|\baddLabels\b/],
];
const DISPATCH = /\bgh workflow run\b|\/dispatches\b|\bcreateDispatchEvent\b|\bcreateWorkflowDispatch\b/;
const GITHUB_TOKEN = /secrets\.GITHUB_TOKEN|github\.token/;
// `GH_TOKEN="$APP_TOKEN" gh ...` on one line uses another token for that command.
const INLINE_OTHER_TOKEN = /\bGH_TOKEN=(?!["']?\$\{\{\s*(secrets\.GITHUB_TOKEN|github\.token))/;
const ALLOW_FILE = '.github/handoffs-allow.json';

const indent = (l) => l.length - l.trimStart().length;
const tokenIn = (lines, key) => {
  for (const l of lines) {
    const m = l.match(new RegExp(`^\\s*(?:-\\s+)?${key}:\\s*(.+)$`));
    if (m) return m[1].trim();
  }
  return null;
};

function blocks(lines, start, end, childIndent) {
  const out = [];
  for (let i = start; i < end; i++) {
    if (lines[i].trim() && indent(lines[i]) === childIndent && /^\s*-\s/.test(lines[i])) out.push(i);
  }
  return out.map((s, k) => lines.slice(s, k + 1 < out.length ? out[k + 1] : end));
}

// Join `\` line continuations and drop comment lines; keep the line order.
function commands(stepLines) {
  const out = [];
  let cur = '';
  for (const raw of stepLines) {
    const l = raw.trimEnd();
    if (/^\s*#/.test(l)) continue;
    if (/^\s*(-\s+)?name:/.test(l)) continue;
    cur += (cur ? ' ' : '') + l.trim().replace(/\\$/, '');
    if (!/\\$/.test(l)) { out.push(cur); cur = ''; }
  }
  if (cur) out.push(cur);
  return out;
}

function scan(text) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const top = (re) => lines.findIndex((l) => re.test(l));
  const wfEnvAt = top(/^env:\s*$/);
  const wfEnv = wfEnvAt < 0 ? [] : lines.slice(wfEnvAt + 1, lines.findIndex((l, i) => i > wfEnvAt && l.trim() && indent(l) === 0));
  const jobsAt = top(/^jobs:\s*$/);
  if (jobsAt < 0) return [];
  let jobsEnd = lines.findIndex((l, i) => i > jobsAt && l.trim() && indent(l) === 0 && !/^\s*#/.test(l));
  if (jobsEnd < 0) jobsEnd = lines.length;
  const jobStarts = [];
  for (let i = jobsAt + 1; i < jobsEnd; i++) {
    const m = lines[i].match(/^ {2}([A-Za-z0-9_-]+):\s*$/);
    if (m) jobStarts.push([i, m[1]]);
  }
  const found = [];
  jobStarts.forEach(([s, job], k) => {
    const e = k + 1 < jobStarts.length ? jobStarts[k + 1][0] : jobsEnd;
    const stepsAt = lines.findIndex((l, i) => i > s && i < e && /^\s+steps:\s*$/.test(l));
    if (stepsAt < 0) return;
    const firstItem = lines.findIndex((l, i) => i > stepsAt && i < e && /^\s*-\s/.test(l));
    if (firstItem < 0) return;
    const jobEnvToken = tokenIn(lines.slice(s, stepsAt), '(?:GH_TOKEN|GITHUB_TOKEN)') || tokenIn(wfEnv, '(?:GH_TOKEN|GITHUB_TOKEN)');
    const steps = blocks(lines, firstItem, e, indent(lines[firstItem]));
    const checkout = steps.find((b) => /uses:\s*actions\/checkout@/.test(b.join('\n')));
    const pushToken = (checkout && tokenIn(checkout, 'token')) || '${{ github.token }}';
    steps.forEach((step, n) => {
      const d = indent(step[0]);
      const own = step.filter((l, i) => i === 0 || indent(l) === d + 2);
      const nameLine = own.map((l) => l.match(/^\s*(?:-\s+)?name:\s*(.+)$/)).find(Boolean);
      const name = nameLine ? nameLine[1].trim().replace(/^(['"])(.*)\1$/, '$2') : `step ${n + 1}`;
      const script = /uses:\s*actions\/github-script@/.test(step.join('\n'));
      const ghToken = tokenIn(step, '(?:GH_TOKEN|GITHUB_TOKEN)') || jobEnvToken
        || (script ? tokenIn(step, 'github-token') || '${{ github.token }}' : null);
      const cmds = commands(step);
      const kinds = new Set();
      let last = -1;
      cmds.forEach((c, i) => {
        for (const [kind, re] of KINDS) {
          if (!re.test(c)) continue;
          const token = kind === 'push' && /\bgit push\b/.test(c) ? pushToken : (INLINE_OTHER_TOKEN.test(c) ? null : ghToken);
          if (token && GITHUB_TOKEN.test(token)) { kinds.add(kind); last = i; }
        }
      });
      if (!kinds.size) return;
      const dispatched = cmds.slice(last + 1).some((c) => DISPATCH.test(c));
      found.push({ job, step: name, kinds: [...kinds], dispatched });
    });
  });
  return found;
}

function check(files, allow) {
  const problems = [];
  const used = new Set();
  for (const [workflow, text] of Object.entries(files)) {
    for (const f of scan(text)) {
      if (f.dispatched) continue;
      const i = allow.findIndex((a) => a.workflow === workflow && a.job === f.job && a.step === f.step);
      const where = `${workflow} job '${f.job}' step '${f.step}'`;
      if (i < 0) {
        problems.push(`${where}: ${f.kinds.join(', ')} with GITHUB_TOKEN starts no workflow; end the step with \`gh workflow run\` (or repository_dispatch), use an app token, or allow-list it with a reason in ${ALLOW_FILE}`);
        continue;
      }
      used.add(i);
      if (!String(allow[i].reason || '').trim()) problems.push(`${where}: allow-list entry needs a reason`);
    }
  }
  allow.forEach((a, i) => {
    if (!used.has(i)) problems.push(`${ALLOW_FILE}: entry ${a.workflow} job '${a.job}' step '${a.step}' matches no hand-off; remove it`);
  });
  return problems;
}

function loadAllow(root) {
  const file = path.join(root, ALLOW_FILE);
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')).allow : [];
}

function main() {
  const root = process.cwd();
  const dir = path.join(root, '.github', 'workflows');
  const files = {};
  for (const f of fs.readdirSync(dir).filter((f) => /\.ya?ml$/.test(f)).sort()) files[f] = fs.readFileSync(path.join(dir, f), 'utf8');
  const problems = check(files, loadAllow(root));
  for (const p of problems) console.log(`::error::${p}`);
  if (!problems.length) console.log(`OK: no GITHUB_TOKEN hand-off without a dispatch (${Object.keys(files).length} workflows)`);
  process.exit(problems.length ? 1 : 0);
}

module.exports = { scan, check, loadAllow, KINDS };
if (require.main === module) main();
