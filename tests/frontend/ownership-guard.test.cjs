// #67: database-owned paths are approved by facts a PR author cannot choose.
const test = require('node:test');
const assert = require('node:assert');
const { decide, DB_LABEL } = require('../../scripts/db_owner_guard.cjs');

const base = { files: ['tribunal/services/council.py'], isFork: false, labelled: false, labellerCanWrite: false };

test('a PR that touches no database-owned path passes without a label', () => {
  assert.strictEqual(decide(base).ok, true);
});

test('a branch name never approves database paths (the #67 bypass)', () => {
  const r = decide({ ...base, files: ['tribunal/migrations/0099_x.py'], branch: 'backend-sneaky' });
  assert.strictEqual(r.ok, false);
  assert.match(r.reason, new RegExp(DB_LABEL));
});

test('migrations, tribunal/db and deploy/postgres all count, including the old name of a rename', () => {
  for (const f of ['tribunal/migrations/0099_x.sql', 'tribunal/db/rls.sql', 'deploy/postgres/init.sql']) {
    assert.strictEqual(decide({ ...base, files: [f] }).ok, false, f);
  }
  assert.strictEqual(decide({ ...base, files: ['docs/x.md'], previousFiles: ['tribunal/db/rls.sql'] }).ok, false);
});

test('a same-repository PR labelled by a writer may change database paths', () => {
  const r = decide({ ...base, files: ['tribunal/migrations/0099_x.py'], labelled: true, labellerCanWrite: true });
  assert.strictEqual(r.ok, true);
});

test('the label only counts when someone with write access applied it', () => {
  const r = decide({ ...base, files: ['tribunal/migrations/0099_x.py'], labelled: true, labellerCanWrite: false });
  assert.strictEqual(r.ok, false);
});

test('a fork PR can never change database paths, even with the label', () => {
  const r = decide({ ...base, files: ['tribunal/migrations/0099_x.py'], isFork: true, labelled: true, labellerCanWrite: true });
  assert.strictEqual(r.ok, false);
  assert.match(r.reason, /fork/);
});

test('check_ownership.cjs ignores an author-chosen branch name (GITHUB_HEAD_REF)', () => {
  const { execFileSync, spawnSync } = require('node:child_process');
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ctm-own-'));
  fs.mkdirSync(path.join(dir, 'scripts'));
  for (const f of ['check_ownership.cjs', 'db_owner_guard.cjs']) {
    fs.copyFileSync(path.join(__dirname, '..', '..', 'scripts', f), path.join(dir, 'scripts', f));
  }
  const git = (...a) => execFileSync('git', a, { cwd: dir, stdio: 'ignore' });
  git('init', '-q'); git('-c', 'user.email=t@example.test', '-c', 'user.name=t', 'commit', '-q', '--allow-empty', '-m', 'base');
  git('checkout', '-q', '--detach');
  fs.mkdirSync(path.join(dir, 'tribunal', 'migrations'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'tribunal', 'migrations', '0099_x.py'), '# x\n');
  const env = { ...process.env, GITHUB_HEAD_REF: 'backend-sneaky', GITHUB_EVENT_NAME: 'push', CTM_ROLE: '' };
  const r = spawnSync(process.execPath, ['scripts/check_ownership.cjs', '--base', 'HEAD'], { cwd: dir, env, encoding: 'utf8' });
  assert.strictEqual(r.status, 1, r.stdout + r.stderr);
  assert.match(r.stdout, /database-owned path/);
  const ok = spawnSync(process.execPath, ['scripts/check_ownership.cjs', '--base', 'HEAD', '--role', 'database'], { cwd: dir, env, encoding: 'utf8' });
  assert.strictEqual(ok.status, 0, ok.stdout + ok.stderr);
});
