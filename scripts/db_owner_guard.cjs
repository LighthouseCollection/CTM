#!/usr/bin/env node
// Database-owned paths guard (#67). Runs from .github/workflows/db-owner-guard.yml
// on pull_request_target, so the code is main's copy and the PR cannot change it.
// The PR's code is never checked out: changed files come from the GitHub API.
//
// A PR may change tribunal/migrations/, tribunal/db/ or deploy/postgres/ only if
//   1. its branch lives in this repository (pushing one already needs write access;
//      fork PRs never change database paths), and
//   2. it carries the label below, applied by someone with write access.
// Branch names, --role flags and anything else the author chooses do not count.
const { execFileSync } = require('child_process');

const DB_LABEL = 'agent:ctm3-database-engineer';
const DB_OWNED = [/^tribunal\/migrations\//, /^tribunal\/db\//, /^deploy\/postgres\//];
const WRITE = new Set(['admin', 'maintain', 'write']);

function decide({ files, previousFiles = [], isFork, labelled, labellerCanWrite }) {
  const touched = [...files, ...previousFiles].filter((f) => DB_OWNED.some((re) => re.test(f)));
  if (touched.length === 0) return { ok: true, reason: 'no database-owned path changed' };
  const list = [...new Set(touched)].join(', ');
  if (isFork) return { ok: false, reason: `database-owned paths changed from a fork: ${list}` };
  if (!labelled) return { ok: false, reason: `database-owned paths changed (${list}); needs the '${DB_LABEL}' label` };
  if (!labellerCanWrite) return { ok: false, reason: `'${DB_LABEL}' was applied by someone without write access` };
  return { ok: true, reason: `database-owned paths approved by '${DB_LABEL}': ${list}` };
}

function gh(path) {
  return JSON.parse(execFileSync('gh', ['api', '--paginate', '--slurp', path], { encoding: 'utf8', maxBuffer: 64 << 20 })).flat();
}

function main() {
  const repo = process.env.REPO;
  const pr = process.env.PR_NUMBER;
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo || '') || !/^\d+$/.test(pr || '')) throw new Error('REPO and PR_NUMBER are required');
  const [info] = gh(`repos/${repo}/pulls/${pr}`);
  // Dispatched runs report on the dispatched commit, so it must be this PR's head.
  const expect = process.env.EXPECT_HEAD_SHA;
  if (expect && info.head.sha !== expect) {
    console.log(`::error:: PR #${pr} head is ${info.head.sha}, not the dispatched commit ${expect}`);
    process.exit(1);
  }
  const changes = gh(`repos/${repo}/pulls/${pr}/files?per_page=100`);
  const labelled = info.labels.some((l) => l.name === DB_LABEL);
  let labellerCanWrite = false;
  if (labelled) {
    const events = gh(`repos/${repo}/issues/${pr}/events?per_page=100`)
      .filter((e) => e.event === 'labeled' && e.label && e.label.name === DB_LABEL);
    const last = events[events.length - 1];
    if (last && last.actor) {
      const [perm] = gh(`repos/${repo}/collaborators/${encodeURIComponent(last.actor.login)}/permission`);
      labellerCanWrite = WRITE.has(perm.permission);
    }
  }
  const result = decide({
    files: changes.map((c) => c.filename),
    previousFiles: changes.map((c) => c.previous_filename).filter(Boolean),
    isFork: !info.head.repo || info.head.repo.full_name !== repo,
    labelled,
    labellerCanWrite,
  });
  console.log(`${result.ok ? 'OK' : '::error::'} ${result.reason}`);
  process.exit(result.ok ? 0 : 1);
}

module.exports = { decide, DB_LABEL, DB_OWNED };
if (require.main === module) main();
