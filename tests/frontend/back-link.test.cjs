// D-0061 (issue 263): every "Back to ..." item is the quiet Plenix back Link (chevron, start-aligned, mirrored in
// Arabic), never a ghost Button. The case pane keeps the SecondaryPane back row.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const app = fs.readFileSync("static/ctm/app.js", "utf8");
const council = fs.readFileSync("static/ctm/council.js", "utf8");

test("no Back to cases / Back to sessions ghost Button remains", () => {
  assert.doesNotMatch(app, /P\.Button,\s*\{[^}]*variant: "ghost"[^}]*\},\s*t\("back(Cases|Sessions)"\)/);
  assert.doesNotMatch(app, /variant: "ghost", onClick: \(\) => go\(council \? "cases" : "past"\) \}, t\("backCases"\)/);
  assert.doesNotMatch(council, /variant: "ghost", onClick: onBack \}, t\("backSessions"\)/);
});

test("the app builds the back item as P.Link with back, a real route href and a client-side click", () => {
  assert.match(app, /const backLink = \(label, id, selected = null\) =>/);
  assert.match(app, /h\(P\.Link, \{ back: true, href: routes\?\.routeFor\(id, selected\)/);
  assert.match(app, /backLink\(t\("backCases"\), council \? "cases" : "past"\)/);
  assert.match(app, /backLink\(t\("backSessions"\), "sessions"\)/);
});

test("the council session view uses the same P.Link back item", () => {
  assert.match(council, /h\(P\.Link, \{ back: true, href: window\.CTMRoutes\?\.routeFor\("sessions"\)/);
  assert.match(council, /t\("backSessions"\)/);
});

test("back links keep modified clicks (new tab) and use no inline style or raw color", () => {
  assert.match(app, /event\.metaKey \|\| event\.ctrlKey \|\| event\.shiftKey \|\| event\.button/);
  assert.doesNotMatch(app.match(/const backLink[\s\S]{0,500}/)[0], /style:|#[0-9a-f]{3,6}\b/i);
});

const applicant = fs.readFileSync("static/ctm/applicant.js", "utf8");

test("the applicant application editor back item is the same P.Link back, behind the unsaved-changes guard", () => {
  assert.doesNotMatch(applicant, /button\("back", \(\) => navigate\(onBack\), \{ variant: "ghost" \}\)/);
  assert.match(applicant, /h\(P\.Link, \{ back: true, href: window\.CTMRoutes\?\.routeFor\("applications"\)/);
  assert.match(applicant, /navigate\(onBack\)/);
  assert.match(applicant, /event\.metaKey \|\| event\.ctrlKey \|\| event\.shiftKey \|\| event\.button/);
});

test("the case back Link is a start-aligned row above the RecordPage, not in the Header actions slot", () => {
  assert.doesNotMatch(app, /actions: backLink\(/);
  assert.match(app, /if \(page === "case"\)\s*return h\(P\.Stack, null,\s*backLink\(t\("backCases"\), council \? "cases" : "past"\),\s*h\(P\.RecordPage/);
});
