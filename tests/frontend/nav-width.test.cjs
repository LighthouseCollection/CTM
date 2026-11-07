// D-0047, D-0048 (#193): navigation panes fit their labels; every nav icon is a Plenix icon so items line up.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const app = fs.readFileSync(path.join(__dirname, "..", "..", "static", "ctm", "app.js"), "utf8");

test("case navigation pane uses the Plenix md pane width (D-0048) and stays collapsible", () => {
  const at = app.indexOf("P.SecondaryPane");
  const pane = app.slice(at, at + 400);
  assert.match(pane, /width: "md"/);
  assert.match(pane, /collapsible: true/);
});

test("navigation icons are Plenix icons, never hand-drawn SVG", () => {
  assert.doesNotMatch(app, /h\("svg"/);
});

test("the way back to sessions is short", () => {
  assert.doesNotMatch(app, /Back to (Current|Upcoming|Archived) Tribunal Sessions/);
});
