// CTM#324 (owner, 2026-11-10): every council and applicant page ends with the Plenix footer
// (page-structures-footer.md: AppShell footer slot holding a StatusBar, status-region.md), so the last card
// and the side nav's last item do not sit on the window's bottom edge. No CTM CSS.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "..", "..", "static", "ctm", "app.js"), "utf8");

test("the council and applicant AppShell passes a Plenix StatusBar as its footer", () => {
  const shell = src.slice(src.indexOf("P.AppShell,\n"));
  const props = shell.slice(0, shell.indexOf("h(CaseNavigationState"));
  assert.match(props, /footer:\s*h\(P\.StatusBar,/, "AppShell footer is a P.StatusBar");
});

test("the footer names the portal through t() with existing EN/AR keys", () => {
  const m = src.match(/footer:\s*h\(P\.StatusBar,\s*\{([^}]*)\}/);
  assert.ok(m, "StatusBar props found");
  assert.match(m[1], /t\(council \? "council" : "applicant"\)/);
});

test("no CTM styling on the footer", () => {
  const m = src.match(/footer:\s*h\(P\.StatusBar,\s*\{([^}]*)\}/);
  assert.ok(m && !/style|className/.test(m[1]), "no style or className on the StatusBar");
});

test("the content column is bounded by what the page renders, not by a hand-kept page list", () => {
  // A min-h-0 Stack shrinks below its content, so plain scrolling pages lose PageContent's padding-block-end
  // (Plenix's space above the footer). Any page that renders a bounded part (Listing, Workspace, SettingsLayout,
  // CasesTable: all carry plx-u-min-h-0) keeps the bounded column so its panes scroll alone (G5a on PR #327).
  assert.doesNotMatch(src, /masterDetail/, "no second page list");
  assert.match(src, /h\(P\.PageContent, null, h\(PageColumn, \{ pageKey: page \}/);
  assert.match(src, /page: \[[^\]]*"cases"[^\]]*\]\.includes\(page\) \? "master-detail" : "workspace"/, "AppShell page mode stays as on main");
});

function load(name) {
  const m = src.match(new RegExp(`function ${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n  \\}\\n`));
  assert.ok(m, `${name} found`);
  return new Function(`${m[0]}; return ${name};`)();
}

test("holdsBoundedPart is true for any page whose column contains a bounded part (myCases, administration, settings…)", () => {
  const holdsBoundedPart = load("holdsBoundedPart");
  const column = (selectors) => ({ querySelector: (s) => (selectors.includes(s) ? {} : null) });
  const startIn = (col) => ({ parentElement: col });
  assert.equal(holdsBoundedPart(startIn(column([".plx-u-min-h-0"]))), true, "a Listing/Workspace/settings page");
  assert.equal(holdsBoundedPart(startIn(column([]))), false, "a plain scrolling page such as Home");
  assert.equal(holdsBoundedPart(null), false);
  assert.equal(holdsBoundedPart({ parentElement: null }), false);
});

test("PageColumn re-checks as the page loads and keeps the bounded class only when needed", () => {
  assert.match(src, /new MutationObserver\(sync\)/);
  assert.match(src, /className: bounded \? "plx-u-flex-1 plx-u-min-h-0" : "plx-u-flex-1"/);
});
