// Template v2.4 check 16 (G-6): GitHub starts no workflow for a PR, merge, push
// or label made with GITHUB_TOKEN (lesson L-18), so such a step must end in an
// explicit `gh workflow run` / repository_dispatch, or be allow-listed with a reason.
const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { scan, check, loadAllow } = require('../../scripts/check_handoffs.cjs');

const wf = (steps, jobEnv = '') => `name: t
on: push
jobs:
  j:
    runs-on: ubuntu-latest
${jobEnv}    steps:
${steps}`;

const one = (text) => check({ 'w.yml': text }, []);

test('a merge with GITHUB_TOKEN and no dispatch fails', () => {
  const r = one(wf(`      - name: Merge
        env:
          GH_TOKEN: \${{ github.token }}
        run: gh pr merge "$url" --squash --auto
`));
  assert.strictEqual(r.length, 1);
  assert.match(r[0], /w\.yml.*Merge.*merge/);
});

test('the same merge passes when the step ends by dispatching the next workflow', () => {
  const r = one(wf(`      - name: Merge
        env:
          GH_TOKEN: \${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr merge "$url" --squash
          gh workflow run deploy.yml --ref main
`));
  assert.deepStrictEqual(r, []);
});

test('a dispatch before the hand-off does not count: it must come after', () => {
  const r = one(wf(`      - name: Open
        env:
          GH_TOKEN: \${{ github.token }}
        run: |
          gh workflow run quality.yml --ref x
          gh pr create --base main --head x --title t --body b
`));
  assert.strictEqual(r.length, 1);
});

test('the job-level token counts, and a bot-token fallback to GITHUB_TOKEN still counts', () => {
  const r = one(wf(`      - name: Label
        run: gh issue edit 5 --add-label sev:S1
`, `    env:
      GH_TOKEN: \${{ secrets.CTM_BOT_TOKEN || secrets.GITHUB_TOKEN }}
`));
  assert.strictEqual(r.length, 1);
  assert.match(r[0], /label/);
});

test('an app token is fine, including an inline GH_TOKEN override', () => {
  assert.deepStrictEqual(one(wf(`      - name: App
        env:
          GH_TOKEN: \${{ steps.app.outputs.token }}
        run: gh pr merge 1 --squash
`)), []);
  assert.deepStrictEqual(one(wf(`      - name: Inline
        env:
          GH_TOKEN: \${{ github.token }}
        run: GH_TOKEN="$APP_TOKEN" gh pr create --title t --body b
`)), []);
});

test('git push and tags use the checkout token (GITHUB_TOKEN by default)', () => {
  const r = one(wf(`      - uses: actions/checkout@v4
      - name: Tag
        run: |
          git tag v1
          git push origin v1
`));
  assert.strictEqual(r.length, 1);
  assert.match(r[0], /push/);
  assert.deepStrictEqual(one(wf(`      - uses: actions/checkout@v4
        with:
          token: \${{ steps.app.outputs.token }}
      - name: Tag
        run: git push origin v1
`)), []);
});

test('issue creation with labels across a line continuation is a label hand-off', () => {
  const r = one(wf(`      - name: Report
        env:
          GH_TOKEN: \${{ github.token }}
        run: |
          gh issue create --title "x" \\
            --label type:bug --body b
`));
  assert.strictEqual(r.length, 1);
});

test('comments, plain issues, label creation and comment-only steps are not hand-offs', () => {
  assert.deepStrictEqual(one(wf(`      - name: Talk
        env:
          GH_TOKEN: \${{ github.token }}
        run: |
          # gh pr merge is mentioned here only
          gh issue comment 5 --body hi
          gh issue create --title t --body b
          gh label create sev:S1 --force
`)), []);
});

test('github-script calls count too', () => {
  const r = one(wf(`      - name: Script
        uses: actions/github-script@v7
        with:
          script: await github.rest.pulls.merge({ owner, repo, pull_number: 1 })
`));
  assert.strictEqual(r.length, 1);
});

test('an allow-list entry needs a reason, and an entry that matches nothing is reported', () => {
  const text = wf(`      - name: Report
        env:
          GH_TOKEN: \${{ github.token }}
        run: gh issue create --title t --body b --label type:bug
`);
  assert.deepStrictEqual(check({ 'w.yml': text }, [{ workflow: 'w.yml', job: 'j', step: 'Report', reason: 'report only' }]), []);
  assert.strictEqual(check({ 'w.yml': text }, [{ workflow: 'w.yml', job: 'j', step: 'Report', reason: '' }]).length, 1);
  const stale = check({ 'w.yml': text }, [
    { workflow: 'w.yml', job: 'j', step: 'Report', reason: 'report only' },
    { workflow: 'w.yml', job: 'j', step: 'Gone', reason: 'old' },
  ]);
  assert.strictEqual(stale.length, 1);
  assert.match(stale[0], /matches no hand-off/);
});

test('scan names unnamed steps by position', () => {
  const found = scan(wf(`      - env:
          GH_TOKEN: \${{ github.token }}
        run: gh pr merge 1
`));
  assert.strictEqual(found[0].step, 'step 1');
});

test("CTM's own workflows pass check 16", () => {
  const root = path.join(__dirname, '..', '..');
  const fs = require('node:fs');
  const dir = path.join(root, '.github', 'workflows');
  const files = {};
  for (const f of fs.readdirSync(dir).filter((f) => /\.ya?ml$/.test(f))) files[f] = fs.readFileSync(path.join(dir, f), 'utf8');
  assert.deepStrictEqual(check(files, loadAllow(root)), []);
});
