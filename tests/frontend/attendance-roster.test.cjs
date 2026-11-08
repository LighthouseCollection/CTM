// Issue 229 (D-0053): the attendance roster's rules: order, summary counts, "Mark the rest present" skips Absent,
// read-only hides the button, the control never folds.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { harness, load, byName, find, textOf, settle } = require("./harness.cjs");

function boot() {
  const h = harness();
  h.React.Component = class { constructor(p) { this.props = p; } };
  h.React.Component.prototype.isReactComponent = {};
  return [h, load(h)];
}
const plain = (v) => JSON.parse(JSON.stringify(v));
const rows = [
  { id: "m2", name: "Fr. Zed", role: "member", seat: "voting", present: false },
  { id: "m1", name: "Fr. Abe", role: "member", seat: "voting", present: null },
  { id: "p", name: "H.G. Presiding", role: "president", seat: "voting", present: true },
  { id: "s", name: "Sec Retary", role: "secretary", seat: "non_voting", present: null },
  { id: "f", name: "Fr. Former", role: "member", present: true, former: true },
];

test("order: presiding, secretary, members by name, former members last", () => {
  const [, C] = boot();
  assert.deepEqual(plain(C.rosterOrder(rows, "en").map((r) => r.id)), ["p", "s", "m1", "m2", "f"]);
});

test("summary counts active seat holders only; unrecorded are the ones with no record", () => {
  const [, C] = boot();
  assert.deepEqual(plain(C.rosterSummary(rows)), { present: 1, total: 4, unrecorded: 2 });
  assert.deepEqual(plain(C.rosterSummary(rows, { m1: true })), { present: 2, total: 4, unrecorded: 1 });
});

test("Mark the rest present sets only members with no record and never overwrites Absent", async () => {
  const [h, C] = boot();
  const posted = [];
  const props = { lang: "en", rows, readOnly: false, onRecord: async (id, present) => { posted.push([id, present]); } };
  let tree = h.render(C.AttendanceRoster, props);
  const button = byName(tree, "Button")[0];
  assert.match(textOf({ children: button.children }), /Mark the rest present/);
  assert.match(textOf(tree), /1 of 4 present · 2 not recorded/);
  await button.props.onClick();
  await settle();
  assert.deepEqual(posted, [["s", true], ["m1", true]]);
  assert.ok(!posted.some(([id]) => id === "m2"), "Absent kept");
  tree = h.render(C.AttendanceRoster, props);
  assert.match(textOf(tree), /3 of 4 present/);
});

test("Mark all present when nobody is recorded; a failed save is put back and names the member", async () => {
  const [h, C] = boot();
  const fresh = rows.filter((r) => !r.former).map((r) => ({ ...r, present: null }));
  const props = { lang: "en", rows: fresh, readOnly: false, onRecord: async (id) => { if (id === "s") throw new Error("no"); } };
  let tree = h.render(C.AttendanceRoster, props);
  const button = byName(tree, "Button")[0];
  assert.match(textOf({ children: button.children }), /Mark all present/);
  await button.props.onClick();
  await settle();
  tree = h.render(C.AttendanceRoster, props);
  assert.match(textOf(byName(tree, "Notice")[0]), /Sec Retary/);
  assert.match(textOf(tree), /3 of 4 present · 1 not recorded/);
});

test("rows are compact UserCards with a SegmentedControl that never folds; read-only hides the button", () => {
  const [h, C] = boot();
  let tree = h.render(C.AttendanceRoster, { lang: "en", rows, readOnly: true, onRecord: async () => {} });
  assert.equal(byName(tree, "Button").length, 0);
  assert.ok(byName(tree, "ReadOnly")[0]);
  const cards = byName(tree, "UserCard");
  assert.equal(cards.length, 5);
  assert.ok(cards.every((card) => card.props.variant === "compact"));
  assert.equal(cards[0].props.secondary, "Presiding · Voting");
  assert.equal(cards[1].props.secondary, "Secretary · Non-voting");
  assert.ok(cards.every((card) => card.props.actions.props.fold === "never"));
  assert.equal(byName(tree, "Table").length + byName(tree, "DataGrid").length, 0);
  const ar = C.translator("ar"), en = C.translator("en");
  for (const key of ["rosterPresentOf", "rosterNotRecorded", "markAllPresent", "markRestPresent", "rosterSaveFailed", "seatVoting", "seatNonVoting"]) assert.notEqual(ar(key), en(key), key);
});

test("the server roster (title, voting, photo, present) becomes roster rows; former members' records stay at the end", () => {
  const [h, C] = boot();
  const rows = C.rosterRowsFrom({
    roster: [
      { member_id: "p", member_name: "H.G. Presiding", member_role: "president", member_active: true, title: "presiding", voting: true, photo_url: null, present: null },
      { member_id: "s", member_name: "Sec Retary", member_role: "secretary", member_active: true, title: "secretary", voting: false, photo_url: "/p.jpg", present: true },
    ],
    items: [{ member_id: "s", member_name: "Sec Retary", member_role: "secretary", present: true }, { member_id: "x", member_name: "Fr. Former", member_role: "member", present: false }],
  });
  assert.deepEqual(plain(rows), [
    { id: "p", name: "H.G. Presiding", role: "presiding", seat: "voting", present: null, former: false },
    { id: "s", name: "Sec Retary", role: "secretary", seat: "non_voting", photo_url: "/p.jpg", present: true, former: false },
    { id: "x", name: "Fr. Former", role: "member", present: false, former: true },
  ]);
  assert.equal(C.rosterRowsFrom({ items: [] }), null, "an older server without roster keeps the old path");
  const tree = h.render(C.AttendanceRoster, { lang: "en", rows, readOnly: false, onRecord: async () => {} });
  assert.equal(byName(tree, "UserCard")[0].props.secondary, "Presiding · Voting");
});
