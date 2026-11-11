// The data font rule (owner, 2026-11-10, #325): case numbers, IDs, dates, times, amounts and counts use
// Plenix's data font (Reddit Mono) through the documented markings; names and words never do.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findDataFontProblems } = require("../../scripts/check_data_font.cjs");

const dir = path.join(__dirname, "..", "..", "static", "ctm");

test("every CTM screen marks its known data fields as data and no name as data", () => {
  const problems = fs.readdirSync(dir).filter((f) => f.endsWith(".js"))
    .flatMap((f) => findDataFontProblems(fs.readFileSync(path.join(dir, f), "utf8"), f));
  assert.deepEqual(problems, []);
});

test("no screen or document still names the retired DM Mono font", () => {
  const root = path.join(__dirname, "..", "..");
  const files = [...fs.readdirSync(dir).map((f) => path.join(dir, f)).filter((f) => /\.(js|html|css)$/.test(f)), path.join(root, "DESIGN.md")];
  for (const f of files) assert.doesNotMatch(fs.readFileSync(f, "utf8"), /DM\s?Mono/i, f);
});

test("a PropertyList date without data: true is flagged; with it, it passes", () => {
  const bad = 'h(P.PropertyList.Item, { label: t("submittedAt") }, base.formatWhen(row.submitted_at, lang))';
  const good = 'h(P.PropertyList.Item, { label: t("submittedAt"), data: true }, base.formatWhen(row.submitted_at, lang))';
  assert.equal(findDataFontProblems(bad).length, 1);
  assert.deepEqual(findDataFontProblems(good), []);
});

test("a version or count in plain Text is flagged; variant data passes", () => {
  assert.equal(findDataFontProblems('h(P.Text, null, String(row.version))').length, 1);
  assert.deepEqual(findDataFontProblems('h(P.Text, { variant: "data" }, String(row.version))'), []);
});

test("a time isolated with bdi must sit inside a data Text", () => {
  assert.equal(findDataFontProblems('h(P.Text,null,t("sentAt"),": ",h("bdi",{dir:"ltr"},row.sent_at))').length, 1);
  assert.deepEqual(findDataFontProblems('h(P.Text,null,t("sentAt"),": ",h(P.Text,{variant:"data"},h("bdi",{dir:"ltr"},row.sent_at)))'), []);
});

test("a grid date, time, count or case number column needs kind data, a data type or a per-value pill", () => {
  assert.equal(findDataFontProblems('{ title: t("submitted"), field: "submitted", minWidth: "11rem" }').length, 1);
  assert.equal(findDataFontProblems('{ title: t("caseNumber"), field: "case_number", kind: "name" }').length, 1);
  assert.deepEqual(findDataFontProblems('{ title: t("caseNumber"), field: "case_number", kind: ["name", "data"] }'), []);
  assert.deepEqual(findDataFontProblems('{ title: t("count"), field: "hearing_case_count", type: "number" }'), []);
  assert.deepEqual(findDataFontProblems('{ title: t("submitted"), field: "submitted", pill: (value, row) => ({ data: Boolean(row.submitted_at) }) }'), []);
});

test("a person's name never takes the data font", () => {
  assert.equal(findDataFontProblems('{ title: t("applicant"), field: "applicant_name", kind: "data" }').length, 1);
  assert.equal(findDataFontProblems('h(P.Text, { variant: "data" }, row.actor)').length, 1);
  assert.deepEqual(findDataFontProblems('h(P.Text, { variant: "strong" }, row.actor)'), []);
});

test("a list row meta that is a date is flagged", () => {
  assert.equal(findDataFontProblems('items: rows.map((row) => ({ meta: formatWhen(row.timestamp, lang) }))').length, 1);
  assert.deepEqual(findDataFontProblems('items: rows.map((row) => ({ meta: h(P.Text, { variant: "data" }, formatWhen(row.timestamp, lang)) }))'), []);
});

test("a tile count needs data: true", () => {
  assert.equal(findDataFontProblems('{ icon: "folder", label: t("cases"), value: String(count) }').length, 1);
  assert.deepEqual(findDataFontProblems('{ icon: "folder", label: t("cases"), value: String(count), data: true }'), []);
});
