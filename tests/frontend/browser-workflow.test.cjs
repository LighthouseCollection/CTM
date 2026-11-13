// Issue #51 / lesson L-08: browser scripts that gate a claim run in CI on every PR.
// This pins the shape of .github/workflows/browser.yml so it cannot quietly lose a script,
// start cancelling its own runs (L-12), or gain a way to push from untrusted code.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const file = path.join(__dirname, '..', '..', '.github', 'workflows', 'browser.yml');
const text = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';

test('the browser workflow exists', () => {
  assert.ok(text, '.github/workflows/browser.yml is missing');
});

test('runs on every pull request, not pull_request_target', () => {
  assert.match(text, /^on:\s*\n\s+pull_request:/m);
  assert.doesNotMatch(text, /pull_request_target/);
});

test('never cancels a run in progress (L-12)', () => {
  assert.doesNotMatch(text, /cancel-in-progress:\s*true/);
});

test('uses a disposable PostgreSQL service and fictional data only', () => {
  assert.match(text, /image:\s*postgres:16/);
  assert.match(text, /CTM_TEST_DATABASE_URL/);
  assert.doesNotMatch(text, /secrets\.(?!GITHUB_TOKEN)/);
});

test('runs the shell footer, CDN smoke and key dates scripts', () => {
  for (const s of ['browser_shell_footer.py', 'browser_cdn_smoke.py', 'browser_key_dates.py']) {
    assert.ok(text.includes(`scripts/${s}`), `${s} is not run`);
  }
});

test('a listed script that is not on this branch is reported as skipped, not silently dropped', () => {
  assert.match(text, /Skipped/);
  assert.match(text, /-f \"\$script\"/);
});

test('uploads the screenshots as an artifact and to ci-screenshots', () => {
  assert.match(text, /actions\/upload-artifact@[0-9a-f]{40}/);
  assert.match(text, /ci-screenshots/);
});

test('the screenshot upload reaches the hidden .tmp folder and fails loudly when it finds nothing', () => {
  const step = (text.match(/uses: actions\/upload-artifact@[\s\S]*?(?=\n  [a-z][\w-]*:|\n      - |$)/) || [''])[0];
  assert.ok(step, 'upload-artifact step missing');
  assert.match(step, /include-hidden-files:\s*true/, '.tmp is hidden; upload-artifact skips it by default');
  assert.match(step, /if-no-files-found:\s*error/, 'a run with no screenshots must not look green');
});

test('the job that runs browser code is read-only; only the publish job may write', () => {
  const jobs = text.split(/^jobs:\s*$/m)[1] || '';
  const blocks = jobs.split(/^  (?=[a-z][\w-]*:\s*$)/m).filter(Boolean);
  assert.ok(blocks.length >= 2, 'expected a browser job and a separate publish job');
  const writers = blocks.filter((b) => /contents:\s*write/.test(b));
  assert.strictEqual(writers.length, 1);
  assert.doesNotMatch(writers[0], /playwright|uv run/, 'the writing job must not run browser code');
});

test('does not publish from fork pull requests', () => {
  assert.match(text, /head\.repo\.full_name\s*==\s*github\.repository/);
});

test('every action is pinned to a full commit SHA', () => {
  const uses = [...text.matchAll(/uses:\s*(\S+)/g)].map((m) => m[1]);
  assert.ok(uses.length > 0);
  for (const u of uses) assert.match(u, /@[0-9a-f]{40}$/, `${u} is not SHA-pinned`);
});

test('desktop only: no mobile or tablet viewport is requested', () => {
  assert.doesNotMatch(text, /mobile|tablet/i);
});
