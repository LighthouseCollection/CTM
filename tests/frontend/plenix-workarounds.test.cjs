// #264: CTM uses the Plenix 1.8.0 components instead of hand-built plx- markup.
// (1) AppHeader draws the brand from `brand={{ logo, organization, application }}`;
// (2) PagePanes is the pane row, not a raw <div className="plx-page-panes">.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = (file) => fs.readFileSync(file, "utf8");

test("AppHeader brand is the documented object, not hand-built plx-app-header markup", () => {
  for (const file of ["static/ctm/app.js", "static/ctm/external-report.js"]) {
    const text = read(file);
    assert.doesNotMatch(text, /plx-app-header__/, `${file} hand-builds plx-app-header markup`);
    assert.match(text, /brand:\s*\{\s*logo:\s*\{[^}]*src:\s*"\/static\/ctm\/tribunal-logo-36\.svg"/, `${file} brand logo`);
    assert.match(text, /organization:\s*"DIOCESE OF LOS ANGELES"/, `${file} organization`);
    assert.match(text, /application:\s*"CLERICAL TRIBUNAL MANAGEMENT"/, `${file} application`);
  }
});

test("the case pane row is P.PagePanes, not a raw plx-page-panes div", () => {
  const text = read("static/ctm/app.js");
  assert.doesNotMatch(text, /plx-page-panes/);
  assert.match(text, /h\(P\.PagePanes,\s*null,\s*caseNav/);
});

test("no hand-written plx- class other than plx-u-* utilities in the pages touched by #264", () => {
  for (const file of ["static/ctm/app.js", "static/ctm/external-report.js"]) {
    const bad = [...read(file).matchAll(/["'`]((?:[^"'`]*\s)?plx-(?!u-)[\w-]+[^"'`]*)["'`]/g)].map((m) => m[1]);
    assert.deepEqual(bad, [], `${file} uses plx- component classes: ${bad.join(", ")}`);
  }
});
