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

test("scrolling pages keep PageContent's bottom padding: min-h-0 only on master-detail pages", () => {
  // A min-h-0 Stack shrinks below its content, so the content overflows it and PageContent's padding-block-end
  // (Plenix's space above the footer) is lost. Split list/detail pages still need it so their panes scroll alone.
  assert.match(src, /h\(P\.PageContent, null, h\(P\.Stack, \{ className: masterDetail \? "plx-u-flex-1 plx-u-min-h-0" : "plx-u-flex-1" \}/);
  assert.match(src, /page: masterDetail \? "master-detail" : "workspace"/);
});
