// D-0049 (issue 170): New applications has two views, "Awaiting review" (default) and "For council", the view in
// the address as ?view=council. For council lists /api/applications/?state=council_consideration through
// considerationQueue(); Home's For council tile opens it.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { harness, load, find, byName, settle } = require("./harness.cjs");

function Listing() { return null; }
function Table() { return null; }
function Workspace() { return null; }
function boot(search) {
  const h = harness();
  h.React.Component = class { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  const C = load(h, { CTMShell: { Listing, Table, Workspace }, location: { pathname: "/applications/new", search }, history: { pushState() {} } });
  return [h, C];
}
const secretary = { id: "sec", portal: "council", role: "secretary" };
const same = (actual, expected) => assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected);

test("the view comes from the address; anything but view=council is Awaiting review", () => {
  const [, C] = boot("");
  assert.equal(C.applicationView(""), "review");
  assert.equal(C.applicationView("?view=council"), "council");
  assert.equal(C.applicationView("?a=1&view=council"), "council");
  assert.equal(C.applicationView("?view=councils"), "review");
  assert.equal(C.applicationViewSearch("council"), "?view=council");
  assert.equal(C.applicationViewSearch("review"), "");
});

async function render(search) {
  const [h, C] = boot(search);
  const asked = [];
  const api = async (url) => {
    asked.push(url);
    return url.includes("council_consideration")
      ? { items: [
          { id: "a1", case_id: "c1", case_number: "20261021-07", kind: "appeal", status: "submitted" },
          { id: "a2", case_id: "c2", case_number: "20261021-08", kind: "petition", origin: "closed_case_intake", status: "submitted" },
          { id: "a3", case_id: "c3", case_number: "20261021-09", kind: "petition", status: "submitted" },
        ] }
      : { items: [{ id: "a4", case_id: "c4", case_number: "20261021-10", kind: "petition", status: "submitted" }] };
  };
  const props = { api, lang: "en", user: secretary, onOpen() {} };
  h.render(C.NewApplicationsTable, props);
  await settle();
  return [h.render(C.NewApplicationsTable, props), asked];
}

test("New applications shows Tabs Awaiting review / For council; Awaiting review is the default", async () => {
  const [tree, asked] = await render("");
  const tabs = byName(tree, "Tabs")[0];
  same(tabs.props.items.map((item) => [item.value, item.label]), [["review", "Awaiting review"], ["council", "For council"]]);
  assert.equal(tabs.props.value, "review");
  assert.ok(asked.includes("/api/applications/?state=awaiting_review"));
  const list = find(tree, (n) => n.type === Listing)[0];
  same(list.props.rows.map((row) => row.case_number), ["20261021-10"]);
  assert.equal(list.props.empty, "No applications are awaiting completeness review.");
});

test("?view=council lists the council consideration queue: appeals and closed-case later petitions only", async () => {
  const [tree, asked] = await render("?view=council");
  assert.equal(byName(tree, "Tabs")[0].props.value, "council");
  assert.ok(asked.includes("/api/applications/?state=council_consideration"));
  const list = find(tree, (n) => n.type === Listing)[0];
  same(list.props.rows.map((row) => row.case_number), ["20261021-07", "20261021-08"]);
  assert.equal(list.props.empty, "No applications are waiting for the council.");
  assert.equal(list.props.rows[0].status, "Awaiting council consideration");
});

test("Home's For council tile opens the council view; the AR view labels exist", () => {
  const [, C] = boot("");
  const tiles = C.homeTiles({ dashboard: { my_cases: 0, review_queue: 0 }, unread: 0, consideration: 2 }, secretary, C.translator("en"), String);
  assert.equal(tiles.find((tile) => tile.id === "consideration").href, "/applications/new?view=council");
  const ar = C.translator("ar");
  assert.equal(ar("viewAwaitingReview"), "في انتظار المراجعة");
  assert.equal(ar("viewForCouncil"), "أمام المجلس");
  assert.notEqual(ar("councilQueueEmpty"), C.translator("en")("councilQueueEmpty"));
});

test("Back or Forward within the same page reloads it (the ?view changes, page and selection do not)", () => {
  const app = require("node:fs").readFileSync("static/ctm/app.js", "utf8");
  const restore = app.slice(app.indexOf("const restore = () => {"), app.indexOf('window.addEventListener("popstate", restore)'));
  assert.match(restore, /setData\(null\);[\s\S]*reload\(\(n\) => n \+ 1\);/);
});
