// Issue 199 (D-0048): the case summary keeps each child's first name, last name and date of birth.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, byName, find, textOf } = require("./harness.cjs");

const [h, C] = (() => { const x = harness(); x.React.Component = class { constructor(p) { this.props = p; } }; x.React.Component.prototype.isReactComponent = {}; return [x, load(x, { document: { documentElement: { lang: "en" } } })]; })();
const plain = (v) => JSON.parse(JSON.stringify(v));
const t = C.caseTranslator("en"), ar = C.caseTranslator("ar");

test("a child saved as a name only is split so the council can complete it", () => {
  assert.deepEqual(plain(C.childForm({ name: "Mary Anne Hayes" })), { first_name: "Mary Anne", last_name: "Hayes", date_of_birth: "" });
  assert.deepEqual(plain(C.childForm("Peter")), { first_name: "Peter", last_name: "", date_of_birth: "" });
  assert.deepEqual(plain(C.childForm({ name: "x", first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" })), { first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" });
});

test("each child needs first name, last name and a date of birth that is not in the future", () => {
  const ok = { first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" };
  assert.equal(C.childProblem(ok, "2026-11-07"), null);
  assert.equal(C.childProblem({ ...ok, first_name: " " }, "2026-11-07").key, "childFirstRequired");
  assert.equal(C.childProblem({ ...ok, last_name: "" }, "2026-11-07").key, "childLastRequired");
  assert.equal(C.childProblem({ ...ok, date_of_birth: "" }, "2026-11-07").key, "childBirthRequired");
  assert.equal(C.childProblem({ ...ok, date_of_birth: "2026-11-08" }, "2026-11-07").key, "childBirthFuture");
  // Well before the marriage only warns.
  assert.equal(C.childWarning({ date_of_birth: "2009-01-01" }, "2010-06-01"), "childBirthBeforeMarriage");
  assert.equal(C.childWarning({ date_of_birth: "2009-07-01" }, "2010-06-01"), null);
  for (const key of ["childFirstRequired", "childLastRequired", "childBirthRequired", "childBirthFuture", "childBirthBeforeMarriage", "addChild", "noChildrenShort", "dateOfBirth", "edit", "save", "remove", "childrenIncomplete"])
    assert.notEqual(ar(key), t(key), key);
});

test("age counts whole years on civil dates", () => {
  assert.equal(C.ageOn("2015-03-04", "2026-03-03"), 10);
  assert.equal(C.ageOn("2015-03-04", "2026-03-04"), 11);
});

test("the summary form sends all three fields per child and no hard-coded English is left", () => {
  const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
  assert.match(source, /children: summaryForm\.children\.map\(\(child\) => \(\{ first_name: child\.first_name, last_name: child\.last_name, date_of_birth: child\.date_of_birth \}\)\)/);
  assert.doesNotMatch(source, /One child per line/);
  assert.doesNotMatch(source, /onClick: startSummaryEdit \}, "Edit"\)/);
  assert.doesNotMatch(source, /disabled: summaryPending \}, "Save"\)/);
  assert.doesNotMatch(source, /P\.Textarea, \{ rows: 4, value: summaryForm\.children/);
});

test("the child editor: No children with Add child; rows with Edit and Remove; Remove drops the row", () => {
  let list = [];
  const draw = (children) => h.render(C.ChildrenEditor, { lang: "en", children, onChange: (next) => { list = next; }, disabled: false, marriageDate: "2010-06-01" });
  let tree = draw([]);
  assert.equal(byName(tree, "EmptyState")[0].props.title, "No children");
  assert.match(textOf(byName(tree, "EmptyState")[0].props.action), /Add child/);
  tree = draw([{ first_name: "Mary", last_name: "Hayes", date_of_birth: "2015-03-04" }, { first_name: "John", last_name: "Hayes", date_of_birth: "2017-05-06" }]);
  const buttons = byName(tree, "Button").map((b) => textOf({ children: b.children }).trim());
  assert.deepEqual(buttons.filter((b) => b === "Edit").length, 2);
  assert.deepEqual(buttons.filter((b) => b === "Remove").length, 2);
  byName(tree, "Button").find((b) => textOf({ children: b.children }).trim() === "Remove").props.onClick();
  assert.deepEqual(plain(list), [{ first_name: "John", last_name: "Hayes", date_of_birth: "2017-05-06" }]);
  assert.match(textOf(tree), /Mary Hayes/);
});

// D-0050 (#217 G2, G5): the Separation cards and the editable case cards have EN and AR words, no English literals.
test("separation cards and editable case cards are EN/AR", () => {
  const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
  const start = source.indexOf("  function CaseSeparation(");
  const sep = source.slice(start, source.indexOf("\n  }\n", start));
  assert.ok(sep.includes("t(\"separationDetails\")"), "the real CaseSeparation body");
  assert.doesNotMatch(sep.replace(/\/\/.*$/gm, ""), /"[A-Z][a-z]+[ ?]/, "no English labels or titles");
  const panel = source.slice(source.indexOf("  function CouncilEditablePanel("), source.indexOf("  function CouncilEditablePanel(") + 3000);
  assert.doesNotMatch(panel, /\}, "Edit"\)|\}, "Save"\)/);
  for (const key of ["separationDetails", "civilDivorce", "restrainingOrder", "reconciliation", "maritalStatus", "initiatedBy", "courtName", "courtLocation", "civilCaseNumber", "civilDivorceStatus", "orderFiled", "orderNameListed", "orderCaseNumber", "orderStatus", "reconciliationAttempted", "permitPreviouslyApplied", "permitWhen", "permitWhere", "decisionOutcome"])
    assert.notEqual(ar(key), t(key), key);
});
