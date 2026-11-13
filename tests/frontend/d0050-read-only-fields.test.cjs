// D-0050 (issue 268): a card heading always has its icon; in a record or detail view a label and value is a
// read-only field (PropertyList item), and a status is a Badge, never hand-built "Label: value" text.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const src = (f) => fs.readFileSync(`static/ctm/${f}`, "utf8");

test("the question categories Panel has an icon", () => {
  assert.match(src("council-case.js"), /h\(P\.Panel, \{ icon: "[a-z-]+", title: t\("questionCategories"\) \}/);
});

test("the report view shows the subject as a PropertyList item", () => {
  const app = src("app.js");
  assert.doesNotMatch(app, /text\(`\$\{t\("subject"\)\}: /);
  assert.match(app, /PropertyList\.Item, \{ label: t\("subject"\)/);
});

test("the case header shows its status as a Badge in meta, not as description text", () => {
  const app = src("app.js");
  assert.doesNotMatch(app, /description: `\$\{t\("status"\)\}: /);
  assert.match(app, /RecordPage\.Header, \{ title: data\.number,\s*meta: h\(P\.Badge/);
});

test("the application fee is a PropertyList item with its status, not 'Fee: ' text", () => {
  for (const f of ["applicant-filing.js", "applicant-payments.js"]) {
    const s = src(f);
    assert.doesNotMatch(s, /`\$\{t\("fee"\)\}: `/, f);
    assert.match(s, /PropertyList\.Item,\s*\{\s*label:\s*t\("fee"\)/, f);
  }
});

test("the invitation version, start and end are PropertyList items", () => {
  const s = src("applicant-appointments.js");
  assert.doesNotMatch(s, /`\$\{t\("(version|start|end)"\)\}: /);
  for (const k of ["version", "start", "end"]) assert.match(s, new RegExp(`PropertyList\\.Item,\\s*\\{\\s*label:\\s*t\\("${k}"\\)`));
});
