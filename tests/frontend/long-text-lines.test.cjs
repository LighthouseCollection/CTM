// pds#1139 (Plenix 1.4.0, pds#1122): a long read-only value clamps to 3 lines and shows the corner icon that opens the whole text.
// Every long-text field passes `lines: 3` on its PropertyList.Item; the long-value helper decides for free-form values.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = (file) => fs.readFileSync(`static/ctm/${file}`, "utf8");

test("case read fields pass lines when the value is long", () => {
  const src = read("council-case.js");
  assert.equal([...src.matchAll(/span: longValue\((\w+(?:\[key\])?)\) \? "full" : undefined, lines: longValue\(\1\) \? 3 : undefined/g)].length, 2);
});

for (const [file, label] of [
  ["council-case.js", "grounds"], ["council-case.js", "conditions"],
  ["council-decree.js", "grounds"], ["council-decree.js", "conditions"], ["council-decree.js", "appealExplanation"],
  ["council-media.js", "observations"],
]) {
  test(`${file}: ${label} is a full-row tile clamped to 3 lines`, () => {
    assert.match(read(file), new RegExp(`label: t\\("${label}"\\), span: "full", lines: 3 \\}`));
  });
}

test("answers from the application forms clamp to 3 lines", () => {
  assert.match(read("council.js"), /label: label \|\| code, lines: 3 \}, answerText/);
  assert.match(read("council-decree.js"), /lang\) \|\| code, lines: 3 \}, base\.answerText/);
});
