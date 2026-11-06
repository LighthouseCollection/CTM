// #97 slice 4 (D-0034): the shell, sign-in and the app.js views on the Plenix 0.86.0 page templates.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const app = fs.readFileSync("static/ctm/app.js", "utf8");
const shell = fs.readFileSync("tribunal/templates/tribunal/shell.html", "utf8");
const between = (start, end) => app.slice(app.indexOf(start), app.indexOf(end, app.indexOf(start)));
const signIn = between("if (user === null) {", "const council = user.portal");

test("sign-in is the Auth page with SsoButtons for the configured providers only (sign-in.md, single-sign-on.md)", () => {
  // #144: the Auth card is centered in a growing Stack below the diocese header (no overlay utilities), so
  // the page never scrolls; Auth page mode would add a full window height under the header.
  assert.match(signIn, /h\(P\.Stack, \{ grow: true, justify: "center", align: "center", inset: "lg" \}, h\(P\.Auth, \{/);
  assert.match(signIn, /title: t\("signIn"\)/);
  assert.match(signIn, /h\(P\.SsoButtons, \{/);
  assert.match(signIn, /providers: config\.providers\.map\(\(name\) => \(\{ id: name, label: t\(name\) \}\)\)/);
  // The provider handoff is unchanged: a POST to the allauth provider login.
  assert.match(signIn, /onProvider: \(provider\) => postForm\(`\/accounts\/\$\{provider\.id\}\/login\/`\)/);
  // The button words stay the existing EN/AR "Continue with …" keys.
  assert.match(signIn, /strings: \{ label: t\("signIn"\), provider: "\{name\}" \}/);
  assert.match(app, /microsoft: "Continue with Microsoft"/);
  assert.match(app, /microsoft: "المتابعة باستخدام Microsoft"/);
});

test("sign-in keeps the honest unavailable message and never offers passwords", () => {
  assert.match(signIn, /config\.providers\.length\s*\?\s*h\(P\.SsoButtons/);
  assert.match(signIn, /: h\(P\.Notice, \{ tone: "warning" \}, t\("noProviders"\)\)/);
  assert.match(app, /"Sign-in is temporarily unavailable\. Please contact the tribunal\."/);
  assert.match(app, /noProviders: "تسجيل الدخول غير متاح مؤقتًا\. يرجى التواصل مع المجلس\."/);
  // SignInForm always draws a password field (0.86.0), so CTM uses Auth + SsoButtons alone (PLX request).
  assert.doesNotMatch(app, /P\.SignInForm|P\.SignUpForm|P\.PasswordResetForm|type: "password"/);
  assert.doesNotMatch(signIn, /organization: true/);
  // One h1 on the page: the diocese header; the card title is the h2 "Sign in".
  assert.match(signIn, /headingLevel: 2/);
  assert.match(signIn, /Coptic Orthodox Church - Diocese of Los Angeles/);
  assert.doesNotMatch(signIn, /h\(P\.Panel/);
});

test("the navigation pane keeps its menus and adds the settings footer (side-navigation.md footer)", () => {
  const nav = between("const nav = h(", "const accountIdentity");
  assert.match(nav, /footer: h\(P\.NavList, \{\s*label: t\("settings"\),\s*value: page,\s*onSelect: \(id\) => go\(id\),\s*items: \[\{ id: "settings", icon: h\(P\.Icon, \{ name: "settings", "aria-hidden": true \}\), label: t\("settings"\) \}\]/);
  // The four menus and their order are unchanged.
  const order = ["items: primaryNavigationItems.slice(0, 1)", "items: sessionNavigationItems", "items: casesNavigationItems", "items: council ? primaryNavigationItems.slice(1) : primaryNavigationItems"].map((s) => nav.indexOf(s));
  for (const index of order) assert.ok(index > 0);
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  assert.match(app, /: \["home", "applications", "appointments", "past"\]/);
});

test("notifications are a ResourceList with their open and read actions (resource-list.md)", () => {
  const inbox = between("function NotificationInbox", "function ReportDetail");
  assert.match(inbox, /h\(P\.ResourceList, \{/);
  assert.match(inbox, /label: t\("notifications"\)/);
  assert.match(inbox, /emptyState: h\(P\.EmptyState, \{ title: t\("noNotifications"\) \}\)/);
  assert.match(inbox, /t\("openCase"\)/);
  assert.match(inbox, /t\("markRead"\)/);
  assert.match(inbox, /onClick: more \}, t\("more"\)/);
  assert.doesNotMatch(inbox, /h\(\s*P\.Panel/);
});

test("applicant home, applications and past cases are ResourceLists (resource-list.md)", () => {
  assert.match(app, /const caseItem = \(row\) => \(\{/);
  assert.match(app, /const applicationItem = \(row\) => \(\{/);
  assert.match(app, /const caseList = \(rows\) =>\s*h\(P\.ResourceList, \{/);
  assert.match(app, /const applicationList = \(rows\) =>\s*h\(P\.ResourceList, \{/);
  // The applicant's open actions keep their words.
  assert.match(app, /lang === "ar" \? "فتح الطلب" : "Open application"/);
  assert.match(app, /openCase\(row\.id, \{ page: "home", labelKey: "backHome" \}\)/);
  const home = between('if (page === "home" && !council) {', 'if (council && councilModule?.CasesTable');
  assert.match(home, /applicationList\(\[filing\]\)/);
  assert.match(home, /caseList\(\[currentCase\]\)/);
  assert.match(home, /h\(P\.EmptyState, \{ title: t\("noCurrent"\) \}\)/);
  assert.doesNotMatch(app, /h\(\s*P\.Panel,\s*\{ icon: "doc-text", key: row\.id, title: t\(row\.kind\)/);
});

test("the applicant case is a RecordPage with its header, body panels unchanged (record-page.md)", () => {
  const record = between('if (page === "case")\n', 'if (councilModule?.StatisticsWorkspace');
  assert.match(record, /h\(P\.RecordPage, \{/);
  assert.match(record, /h\(P\.RecordPage\.Header, \{ title: data\.number/);
  assert.match(record, /t\("backCases"\)/);
  for (const part of ["StartPetition", "StartAppeal", "ReleasedDecrees", "Requests"]) assert.match(record, new RegExp(part));
  assert.match(record, /title: t\("parties"\)/);
  assert.match(record, /title: t\("timeline"\)/);
});

// #97 slice 8: every CTM script carries a cache stamp (slices 1–8 changed them all), so a browser never mixes
// a fresh module with a stale cached one.
test("shell.html gives every static/ctm script a cache stamp, bumped after slices 1–8", () => {
  const scripts = [...shell.matchAll(/static '(ctm\/[a-z-]+\.js)' %\}(\?v=[^"]*)?"/g)];
  assert.ok(scripts.length >= 25, "every module is listed");
  // Bumped for #116 and #144 (2026-11-06): the live site kept serving the old stamp after the reminders UI.
  for (const [, file, stamp] of scripts) assert.equal(stamp, "?v=ctm-20261106b", file);
});

// CTM#113 (owner: "it feels smaller than the cdn tab"): CTM renders at the CDN default density (density.md:
// "standard when unset"); only DataGrid keeps its own compact rows (its default, owner 2026-10-22).
test("CTM#113: no app-wide compact density; tables keep their own compact rows", () => {
  for (const file of ["tribunal/templates/tribunal/shell.html", "static/ctm/external-report.html"])
    assert.doesNotMatch(fs.readFileSync(file, "utf8"), /data-plx-density/, file);
  assert.match(fs.readFileSync("static/ctm/shell-layout.js", "utf8"), /density: "compact", cells: "pill"/);
});

// #108 (Plenix 0.88.0, pds#274): every CTM shell turns on the CDN's screen-size check, with EN and AR words.
test("every AppShell turns on minSize with EN and AR strings", () => {
  const fs = require("node:fs");
  for (const file of ["static/ctm/app.js", "static/ctm/external-report.js"]) {
    const src = fs.readFileSync(file, "utf8");
    const shells = src.match(/h\(\s*P\.AppShell,[^]*?strings:/g) || [];
    assert.ok(shells.length > 0, file);
    for (const s of shells) assert.match(s, /minSize: true/, file);
    assert.equal((src.match(/minSizeTitle:/g) || []).length, 2, file + " EN+AR title");
    assert.equal((src.match(/minSizeText: .*\{width\} × \{height\}/g) || []).length, 2, file + " EN+AR text");
  }
});
