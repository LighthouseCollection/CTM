// pds#1122, pds#1139 (Plenix 1.4.0): a long read-only value is cut to 3 lines and its corner icon opens the whole text in a Dialog
// titled with the field's label. PropertyList.Item { lines: 3 } does it for a tile (overflow "dialog" is its default with lines); Text { lines, overflow: "dialog", overflowLabel }
// does it outside a list. Every long-text field named here passes lines; the long values of the case profile and the case card fields pass it when they are long.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = (name) => fs.readFileSync("static/ctm/" + name, "utf8");

test("long-text tiles pass lines: 3 (notes, grounds, conditions, appeal explanation, observations, answers)", () => {
  const decree = read("council-decree.js"), caseSrc = read("council-case.js"), media = read("council-media.js"), applicant = read("applicant.js");
  for (const [src, label] of [[decree, "grounds"], [decree, "conditions"], [decree, "appealExplanation"], [caseSrc, "grounds"], [caseSrc, "conditions"], [media, "observations"]])
    assert.match(src, new RegExp('P\\.PropertyList\\.Item, \\{ label: t\\("' + label + '"\\), lines: 3, span: "full" \\}'), label);
  assert.match(decree, /label: base\.fieldLabel\(row, code, lang\) \|\| code, lines: 3 \}/, "the petition answers in the decree page");
  assert.match(caseSrc, /label: base\.fieldLabel\(row, code, lang\) \|\| code, lines: 3 \}/, "the petition answers on the case page");
  assert.match(applicant, /label: fieldLabel, lines: 3 \}/, "the applicant's read-only answers");
});

test("the case profile and the case card fields clamp their long values", () => {
  const src = read("council-case.js");
  assert.match(src, /span: longValue\(value\) \? "full" : undefined, lines: longValue\(value\) \? 3 : undefined/, "spouse profile sections");
  assert.match(src, /span: longValue\(values\[key\]\) \? "full" : undefined, lines: longValue\(values\[key\]\) \? 3 : undefined/, "CaseReadFields");
});

test("long text outside a list is a Text with lines, overflow dialog and its label", () => {
  assert.match(read("council-media.js"), /P\.Text, \{ as: "p", dir: "auto", lines: 3, overflow: "dialog", overflowLabel: t\("observations"\) \}/);
  assert.match(read("council-media.js"), /label: label\(code\), lines: 3 \}/, "the conflict answers");
  assert.match(read("council-media.js"), /lines: 3, overflow: "dialog", overflowLabel: label \}, typeof answer/, "the answer panels");
  assert.match(read("app.js"), /text\(shown\.observations, \{ lines: 3, overflow: "dialog", overflowLabel: t\("observations"\) \}\)/);
});

test("the previous recommendation in the agenda grids opens its whole text in a Dialog", () => {
  assert.match(read("council.js"), /P\.Text, \{ as: "span", truncate: true, overflow: "dialog", overflowLabel: t\("previousRecommendation"\)/);
});
