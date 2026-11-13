// #264: CTM uses the Plenix 1.8.0 components instead of hand-built plx- markup.
// (1) AppHeader keeps the hand-built brand: the 1.8.0 `brand` object clips the application line (PLX-028);
// (2) PagePanes is the pane row, not a raw <div className="plx-page-panes">.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = (file) => fs.readFileSync(file, "utf8");

test("AppHeader brand stays the hand-built workaround until PLX-028 is fixed", () => {
  // Plenix 1.8.0 clips the `brand.application` line ("CLERICAL TRIBUNAL MANAGEM...") although there is room, EN and AR.
  for (const file of ["static/ctm/app.js", "static/ctm/external-report.js"]) {
    const text = read(file);
    assert.doesNotMatch(text, /brand:\s*\{/, `${file} uses the brand object (clipped, PLX-028)`);
    assert.match(text, /plx-app-header__app/, `${file} brand application line`);
    assert.match(text, /DIOCESE OF LOS ANGELES/, `${file} organization`);
    assert.match(text, /CLERICAL TRIBUNAL MANAGEMENT/, `${file} application`);
  }
});

test("the case pane row is P.PagePanes, not a raw plx-page-panes div", () => {
  const text = read("static/ctm/app.js");
  assert.doesNotMatch(text, /plx-page-panes/);
  assert.match(text, /h\(P\.PagePanes,\s*null,\s*caseNav/);
});

test("no hand-written plx- class other than plx-u-* utilities and the PLX-028 header brand", () => {
  for (const file of ["static/ctm/app.js", "static/ctm/external-report.js"]) {
    const bad = [...read(file).matchAll(/["'`]((?:[^"'`]*\s)?plx-(?!u-|app-header__)[\w-]+[^"'`]*)["'`]/g)].map((m) => m[1]);
    assert.deepEqual(bad, [], `${file} uses plx- component classes: ${bad.join(", ")}`);
  }
});
