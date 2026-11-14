// #353 G2: the council photo design (Settings > Users & Roles control, and where the photo shows) is written down,
// uses only Plenix components read at the pinned version, and has a full state list and EN/AR text placement.
// The builder works from this file; these checks keep it complete. Design only: no app code is checked here.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const DOC = "docs/implementation/slices/core-353-council-photos/design.md";
const read = () => fs.readFileSync(DOC, "utf8");

// Plenix components (and their published spec pages) read for this design at the pinned CDN version.
const PLENIX = {
  AvatarUpload: "avatar-upload.md", Avatar: "avatar.md", Field: "field.md", FileInput: "file-input.md",
  ConfirmDialog: "confirmation-dialog.md", Dialog: "confirmation-dialog.md", Notice: "notice.md", Toast: "toast.md",
  Spinner: "spinner.md", UserCard: "user-card.md", MetricCard: "metric-card.md", ActionMenu: "action-menu.md",
  SettingsSection: "settings-page.md", Button: "button.md", EntityHeader: "record-page.md",
};

test("#353 G2: the design file exists and links the issue, G1 and the open Users pick", () => {
  assert.ok(fs.existsSync(DOC), `${DOC} exists`);
  const doc = read();
  assert.match(doc, /#353/);
  assert.match(doc, /G1/);
  assert.match(doc, /#328/);
  assert.match(doc, /#331/);
});

test("#353 G2: every Plenix component the design names is one read at the pinned version, with its spec page", () => {
  const doc = read();
  const table = doc.slice(doc.indexOf("## Plenix components"), doc.indexOf("\n## ", doc.indexOf("## Plenix components") + 5));
  assert.ok(table.length > 50, "a Plenix components section");
  for (const [name, page] of Object.entries(PLENIX)) {
    if (table.includes(`\`${name}\``)) assert.ok(table.includes(page), `${name} cites ${page}`);
  }
  // every component in backticks in the components table is a known one
  const named = [...table.matchAll(/^\| `([A-Z][A-Za-z]+)`/gm)].map((m) => m[1]);
  assert.ok(named.length >= 8, "the table lists the components");
  for (const n of named) assert.ok(PLENIX[n], `${n} is a Plenix component read for this design`);
});

test("#353 G2: the control is Plenix AvatarUpload with the G1 rules: no crop, JPEG/PNG, 2 MB", () => {
  const doc = read();
  assert.match(doc, /AvatarUpload/);
  assert.match(doc, /crop=\{false\}/);
  assert.match(doc, /accept="image\/png,image\/jpeg"/);
  assert.match(doc, /maxSize=\{2097152\}/);
  // never fake success: the picture changes only after the server confirms
  assert.match(doc, /only after the server/i);
});

test("#353 G2: the control fits each Settings > Users variation (A, B, C, D) and today's screen", () => {
  const doc = read();
  for (const v of ["A", "B", "C", "D"]) assert.match(doc, new RegExp(`\\| ${v} `), `variation ${v} placement`);
  assert.match(doc, /[Tt]oday/);
});

test("#353 G2: the state list covers every state the control and the display can reach", () => {
  const doc = read();
  const states = ["No photo", "Has photo", "Uploading", "Saved", "Too large", "Not JPEG or PNG", "Remove: confirm", "Removing",
    "Removed", "Network or server error", "Forbidden", "Not seated", "Conflict", "Read-only", "Photo fails to load"];
  for (const s of states) assert.ok(doc.includes(`| ${s} `), `state row "${s}"`);
});

test("#353 G2: every new string has an English text, a key and an Arabic placement, and no Arabic is invented", () => {
  const doc = read();
  const section = doc.slice(doc.indexOf("## Words"), doc.indexOf("\n## ", doc.indexOf("## Words") + 5));
  const rows = [...section.matchAll(/^\| `(photo[A-Za-z]+)` \| ([^|]+) \| ([^|]+) \|/gm)];
  assert.ok(rows.length >= 10, "at least ten keyed strings");
  for (const [, key, en, place] of rows) {
    assert.ok(en.trim().length > 2, `${key} has English`);
    assert.ok(place.trim().length > 2, `${key} has a placement`);
  }
  assert.match(section, /arabic-proposals\.md/);
  assert.match(section, /RTL/);
  assert.doesNotMatch(section, /[؀-ۿ]/, "Arabic words come from the i18n engineer (D-0012), not from this design");
});

test("#353 G2: applicants never see a council photo, and the photo is decorative beside a visible name", () => {
  const doc = read();
  assert.match(doc, /[Aa]pplicants? never/);
  assert.match(doc, /decorative/);
});

test("#353 G2: no styling outside Plenix in the design (no inline styles, raw colors or numeric sizes)", () => {
  const doc = read();
  assert.doesNotMatch(doc, /style=|#[0-9a-fA-F]{6}\b|!important|\b\d+px\b/);
});

// Design Critic review on PR #357 (G5b FAIL, round 1): the four fixes stay fixed.
const section = (doc, head) => {
  const i = doc.indexOf(head);
  assert.ok(i >= 0, `section ${head}`);
  const j = doc.indexOf("\n## ", i + 5);
  return doc.slice(i, j < 0 ? undefined : j);
};

test("#353 G2: the Presiding fact stays a documented EntityHeader fact; the photo there waits for a logged Plenix request", () => {
  const doc = read();
  const comps = section(doc, "## Plenix components");
  assert.match(comps, /\| `EntityHeader` \| record-page\.md \|/, "EntityHeader is in the components table with its page");
  const row = doc.split("\n").find((l) => l.startsWith("| Presiding fact"));
  assert.ok(row, "a Presiding fact row in the display table");
  assert.doesNotMatch(row, /Avatar/, "no Avatar inside an EntityHeader fact (facts are { icon, label, value, action })");
  assert.match(row, /\{ icon, label, value, action \}/);
  assert.match(row, /PLX-028/);
  const reqs = fs.readFileSync("docs/implementation/plenix-requests.md", "utf8");
  const req = reqs.split("\n").find((l) => l.startsWith("| PLX-028 |"));
  assert.ok(req, "PLX-028 is logged in plenix-requests.md");
  assert.match(req, /EntityHeader/);
  assert.match(req, /record-page/);
  assert.match(req, /#353/);
});

test("#353 G2: the failure notice button is the existing retry key, whose English is \"Try again\"", () => {
  const words = section(read(), "## Words");
  assert.doesNotMatch(words, /"Retry"/);
  assert.match(words, /`retry` \("Try again"\)/);
  // the notice text does not repeat its own button
  for (const key of ["photoSaveFailed", "photoRemoveFailed"]) {
    const row = words.split("\n").find((l) => l.startsWith(`| \`${key}\``));
    assert.ok(row, key);
    assert.doesNotMatch(row.split("|")[2], /try again/i, `${key} English leaves "Try again" to the button`);
  }
});

test("#353 G2: Conflict shows whose change won and keeps the person's chosen file for one more try (DESIGN.md \u00a73)", () => {
  const doc = read();
  const row = doc.split("\n").find((l) => l.startsWith("| Conflict "));
  assert.ok(row);
  assert.match(row, /\{actor\}|whose change won/);
  assert.match(row, /kept|keeps/);
  assert.match(row, /photoUseMine/);
  const words = section(doc, "## Words");
  assert.match(words, /^\| `photoUseMine` \|/m);
  assert.match(words, /^\| `photoConflict` \| [^|]*\{actor\}/m);
});

test("#353 G2: today's Users list draws no avatar, so the list shows a photo only in a layout that already draws one", () => {
  const doc = read();
  const today = doc.split("\n").find((l) => l.startsWith("| Today "));
  assert.ok(today);
  assert.match(today, /no avatar/i);
  const list = doc.split("\n").find((l) => l.startsWith("| Settings > Users list"));
  assert.ok(list);
  assert.match(list, /only in a layout that already draws/i);
  assert.doesNotMatch(doc, /Each surface keeps its current avatar size/);
});
