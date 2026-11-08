// Issue 230 (D-0054): one searchable, multi-select case picker for both agenda parts; opening it never shows the
// page's earlier error.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, byName, find, textOf, settle } = require("./harness.cjs");

function Table() { return null; }
function boot() {
  const h = harness();
  h.React.Component = class { constructor(p) { this.props = p; } };
  h.React.Component.prototype.isReactComponent = {};
  return [h, load(h, { CTMShell: { Table } })];
}
const plain = (v) => JSON.parse(JSON.stringify(v));
const items = [
  { id: "c1", number: "20261021-07", party_names: ["Mark Example", "Mary Example"], filed_at: "2026-10-01", grounds: ["abuse"], status: "open", assigned_member: "Fr. A", recommendation_preview: "Grant the petition after a further hearing" },
  { id: "c2", number: "20261021-08", party_names: ["Peter Sample", "Sarah Sample"], filed_at: null, grounds: [], status: "open", assigned_member: null, recommendation_preview: null },
];

test("opening the picker clears the page's previous error (the #224 refusal left in the dialog)", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  assert.match(council, /onClick: \(\) => \{ setFailure\(null\); setDialog\(\{ kind: "place", part: 1 \}\); \}/);
  assert.match(council, /onClick: \(\) => \{ setFailure\(null\); setDialog\(\{ kind: "place", part: 2 \}\); \}/);
  const dialog = council.slice(council.indexOf('dialog?.kind === "place"'), council.indexOf('dialog?.kind === "place"') + 400);
  assert.match(dialog, /h\(CasePicker, \{/);
  assert.doesNotMatch(dialog, /failure \? h\(P\.Notice/);
});

test("rows: number, parties, filed, grounds, status, member, short recommendation; search by number or name", () => {
  const [, C] = boot();
  const t = C.translator("en");
  const rows = C.pickerRows(items, "", t, "en");
  assert.deepEqual(plain(rows.map((r) => [r.number, r.grounds, r.member, r.recommendation])),
    [["20261021-07", "Abuse", "Fr. A", "Grant the petition after a further hearing"], ["20261021-08", "—", "Not yet assigned", "Not Recorded"]]);
  assert.match(rows[0].parties, /Mark Example.*vs\..*Mary Example/);
  assert.deepEqual(plain(C.pickerRows(items, "sarah", t, "en").map((r) => r.id)), ["c2"]);
  assert.deepEqual(plain(C.pickerRows(items, "-07", t, "en").map((r) => r.id)), ["c1"]);
});

test("the button counts the choice in EN and AR", () => {
  const [, C] = boot();
  assert.equal(C.pluralWord("en", "addCasesCount", 1), "Add 1 case");
  assert.equal(C.pluralWord("en", "addCasesCount", 3), "Add 3 cases");
  assert.equal(C.pluralWord("ar", "addCasesCount", 2), "إضافة قضيتين");
  assert.equal(C.pluralWord("ar", "addCasesCount", 3), "إضافة ٣ قضايا");
});

test("the picker: a selectable grid, adds the chosen cases in one batch, and shows an empty state when none", async () => {
  const [h, C] = boot();
  const calls = [];
  let added = null;
  const api = async (url, options) => { calls.push([url, options?.body || null]); return url.includes("eligible-cases") ? { items } : { items: [] }; };
  const props = { api, lang: "en", sessionId: "s1", part: 2, onClose() {}, onAdded: (n) => { added = n; } };
  h.render(C.CasePicker, props); await settle();
  let tree = h.render(C.CasePicker, props);
  assert.equal(calls[0][0], "/api/sessions/s1/eligible-cases/?part=2");
  const table = find(tree, (n) => n.type === Table)[0];
  assert.equal(table.props.grid.selectable, true);
  assert.deepEqual(plain(table.props.columns.map((c) => c.field)), ["number", "parties", "filed", "grounds", "member", "recommendation"]);
  const dialog = byName(tree, "Dialog")[0];
  assert.equal(dialog.props.size, "xl");
  assert.equal(table.props.narrow, "table");
  const primary = () => byName(h.render(C.CasePicker, props), "Dialog")[0].props.footer.children.find((b) => b.props.variant === "primary");
  assert.equal(primary().props.disabled, true);
  table.props.grid.onSelectionChange(["c1", "c2"]);
  assert.match(textOf({ children: primary().children }), /Add 2 cases/);
  await primary().props.onClick(); await settle();
  assert.deepEqual(calls.at(-1), ["/api/sessions/s1/agenda/batch/", JSON.stringify({ part: 2, case_ids: ["c1", "c2"] })]);
  assert.equal(added, 2);
  // part 1 has no member column; no eligible cases is an EmptyState, not an error
  const [h2, C2] = boot();
  const props2 = { api: async () => ({ items: [] }), lang: "en", sessionId: "s1", part: 1, onClose() {}, onAdded() {} };
  h2.render(C2.CasePicker, props2); await settle();
  tree = h2.render(C2.CasePicker, props2);
  assert.equal(byName(tree, "EmptyState")[0].props.title, "No accepted cases are waiting to be assigned.");
  assert.equal(byName(tree, "Notice").length, 0);
});
