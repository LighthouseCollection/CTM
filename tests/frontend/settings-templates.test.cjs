// #97 slice 6: My account and CTM Settings are Plenix settings pages (settings-page.md: SettingsLayout + NavList,
// SettingsSection, SettingsRow); users and the system audit are listing pages (CTMShell.Listing); configuration has
// one field per setting (no raw JSON) and saves the stored shape; historical entry follows form-flow.
// Who sees what is unchanged. Synthetic data only.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { harness, find, byName, textOf, settle, nameOf } = require("./harness.cjs");

const PLENIX = Symbol.for("ctm.test.plenix");
const named = (name) => new Proxy(function () {}, { get: (_t, key) => (key === PLENIX ? true : key === "displayName" ? name : named(`${name}.${String(key)}`)) });
const Plenix = new Proxy({}, { get: (_t, key) => named(String(key)) });

const admin = { id: "u-admin", role: "admin", name: "Admin Synthetic", email: "admin@ctm.example.test", notification_language: "en" };
const secretary = { id: "u-sec", role: "secretary", name: "Secretary Synthetic", email: "secretary@ctm.example.test", notification_language: "en" };
const member = { id: "u-mem", role: "member", name: "Member Synthetic" };

const members = [
  { id: "m1", first_name: "Member", last_name: "One", email: "one@ctm.example.test", role: "member", active: true, can_suspend: true, active_case_count: 2, profile_version: 1, status_version: 1 },
  { id: "m2", first_name: "Member", last_name: "Two", email: "two@ctm.example.test", role: "president", active: false, can_reactivate: true, active_case_count: 0, profile_version: 1, status_version: 2 },
];
const settings = [
  { key: "diocese_settings", version: 3, value: { diocese_name: "Synthetic Diocese", system_email: "office@ctm.example.test", case_id_prefix: "CTM", default_session_day: "Tuesday", session_location: "Hall", presiding_bishop: "Bishop Synthetic", tribunal_secretary: "Secretary Synthetic" } },
  { key: "document_templates", version: 2, value: { templates: [{ title: "Summons", category: "letters", body: "Body text", active: true }] } },
  { key: "mobile_settings", version: 1, value: { system_available_mobile: true } },
];
const audit = [{ id: "a1", action: "setting_saved", source: "setting", timestamp: "2026-10-21T12:00:00Z" }];

function server(routes = {}) {
  const writes = [];
  const all = {
    "/api/system/members/": { items: members }, "/api/system/settings/": { items: settings }, "/api/system/audit/": { items: audit },
    "/api/account/sessions/": { items: [{ handle: "s1", current: true }, { handle: "s2", current: false, expires_at: "2026-11-30T12:00:00Z" }] },
    "/api/account/activity/": { items: [] }, ...routes,
  };
  const api = async (url, options) => {
    if (options && options.method && options.method !== "GET") { writes.push({ url, body: JSON.parse(options.body) }); return { version: 9 }; }
    if (!(url in all)) throw Object.assign(new Error(`HTTP 404 ${url}`), { status: 404 });
    return all[url];
  };
  return { api, writes };
}

async function mount(component, props) {
  const h = harness();
  h.React.Fragment = function Fragment(p) { return p.children; };
  const Listing = function Listing() { return null; };
  const window = { React: h.React, Plenix, addEventListener() {}, removeEventListener() {}, CTMShell: { Listing, Workspace: Listing, Table: Listing } };
  const context = { window, console };
  for (const file of ["council.js", "ui-workspaces.js", "historical-entry.js"])
    vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), context);
  const C = typeof component === "string" ? (window.CTMUI[component] || window.CTMHistorical[component]) : component;
  let tree = h.render(C, props);
  for (let i = 0; i < 4; i++) { await settle(); tree = h.render(C, props); }
  return { tree, rerender: async () => { await settle(); return h.render(C, props); } };
}
const listings = (tree) => find(tree, (n) => n.type && n.type.name === "Listing");
const navItems = (tree) => byName(tree, "NavList")[0].props.items.map((item) => item.id);
const sectionTitles = (tree) => byName(tree, "SettingsSection").map((n) => n.props.title);
const plain = (value) => JSON.parse(JSON.stringify(value));
const same = (actual, expected, message) => assert.deepEqual(plain(actual), plain(expected), message);

test("CTM Settings is a SettingsLayout with a NavList, not tabs; admin sees Data & Records, secretary does not", async () => {
  for (const [user, expected] of [[admin, ["members", "configuration", "historical", "audit"]], [secretary, ["members", "configuration", "audit"]]]) {
    const { tree } = await mount("Administration", { api: server().api, user, lang: "en" });
    assert.equal(byName(tree, "SettingsLayout").length, 1);
    assert.equal(byName(tree, "Tabs").length, 0, "no Tabs");
    same(navItems(tree), expected);
  }
});

test("members, presidents and applicants never reach CTM Settings", async () => {
  for (const user of [member, { role: "president" }, { role: "applicant" }]) {
    const { tree } = await mount("Administration", { api: server().api, user, lang: "en" });
    assert.equal(byName(tree, "SettingsLayout").length, 0);
    assert.match(textOf(tree), /You do not have access/);
  }
});

test("Users & Roles is a listing page: row actions in the row menu, active/previous as a command, add for admins only", async () => {
  const { tree } = await mount("Administration", { api: server().api, user: admin, lang: "en", initialSection: "members" });
  const [listing] = listings(tree);
  assert.ok(listing, "CTMShell.Listing");
  same(listing.props.rows.map((r) => r.id), ["m1"]);
  assert.ok(!listing.props.columns.some((c) => c.kind === "actions"), "no button column");
  same(listing.props.rowMenu(members[0]).filter((i) => !i.separator).map((i) => i.label), ["Edit", "Manage access", "Archive"]);
  same(listing.props.rowMenu(members[1]).filter((i) => !i.separator).map((i) => i.label), ["Edit", "Manage access", "Restore"]);
  const actions = listing.props.commandBar.actions;
  same(actions.find((a) => a.id === "view").choices.map((c) => c.label), ["Active Members", "Previous Members"]);
  assert.ok(actions.some((a) => a.id === "add" && a.label === "Add staff user"));
  assert.equal(typeof listing.props.search.text, "function");
  const sec = await mount("Administration", { api: server().api, user: secretary, lang: "en", initialSection: "members" });
  assert.ok(!listings(sec.tree)[0].props.commandBar.actions.some((a) => a.id === "add"), "secretary cannot enroll");
});

test("Tribunal Config has one field per setting, no raw JSON boxes, and saves the stored shape", async () => {
  const { api, writes } = server();
  const mounted = await mount("Administration", { api, user: admin, lang: "en", initialSection: "configuration" });
  const tree = mounted.tree;
  assert.equal(byName(tree, "Textarea").length, 0, "no JSON textareas");
  same(sectionTitles(tree), ["Diocese Settings", "Document Templates", "Decision Outcomes", "Case Workflow Stages", "Canonical Reasons", "Mobile Settings"]);
  const rows = byName(tree, "SettingsRow").map((n) => n.props.label);
  for (const label of ["Diocese name", "System email", "Case ID prefix", "Default session day", "Summons", "System available on mobile"]) assert.ok(rows.includes(label), label);
  assert.ok(byName(tree, "Switch").length >= 2, "booleans are switches");
  // Saving a list posts the value in the stored shape with the loaded version.
  const forms = byName(tree, "Form");
  const templates = forms.find((f) => f.props.label === "Document Templates");
  templates.props.onSubmit({ preventDefault() {} });
  await settle();
  same(writes[0], { url: "/api/system/settings/", body: { key: "document_templates", value: settings[1].value, expected_version: 2, schema_version: 1 } });
  // Diocese settings keep every stored property and the English day value.
  const again = await mounted.rerender();
  byName(again, "Form").find((f) => f.props.label === "Diocese Settings").props.onSubmit({ preventDefault() {} });
  await settle();
  same(writes[1].body, { key: "diocese_settings", value: settings[0].value, expected_version: 3, schema_version: 1 });
});

test("a configuration list item is edited in a dialog with per-property fields and validated before it is applied", async () => {
  const mounted = await mount("Administration", { api: server().api, user: admin, lang: "en", initialSection: "configuration" });
  const stages = byName(mounted.tree, "SettingsSection").find((n) => n.props.title === "Case Workflow Stages");
  const add = find(stages.props.actions, (n) => nameOf(n.type) === "Button" && textOf({ children: n.children }).trim() === "Add item")[0];
  add.props.onClick();
  let tree = await mounted.rerender();
  const dialog = byName(tree, "Dialog")[0];
  assert.ok(dialog, "item dialog");
  same(byName(dialog, "Field").map((n) => n.props.label), ["Name", "Color"]);
  same(byName(dialog, "Switch").map((n) => n.props.label), ["Active"]);
  byName(dialog, "Form")[0].props.onSubmit({ preventDefault() {} });
  tree = await mounted.rerender();
  assert.match(textOf(byName(tree, "Dialog")[0]), /Fill in every required field/);
});

test("Audit & Security: sign-in sessions as a settings section and the audit as a listing page", async () => {
  const { tree } = await mount("Administration", { api: server().api, user: secretary, lang: "en", initialSection: "audit" });
  assert.ok(sectionTitles(tree).includes("Active Sessions"));
  assert.ok(byName(tree, "SettingsRow").some((n) => n.props.label === "Current session"));
  const [listing] = listings(tree);
  assert.equal(listing.props.label, "System audit");
  same(listing.props.rows.map((r) => r.id), ["a1"]);
  assert.ok(find(tree, (n) => n.type && n.type.name === "AuditFilters").length === 1);
});

test("My account is a settings page; notification language is a segmented control; Arabic labels", async () => {
  for (const [lang, title] of [["en", "My Account"], ["ar", "حسابي"]]) {
    const { tree } = await mount("Profile", { api: server().api, user: admin, lang });
    assert.equal(byName(tree, "SettingsLayout").length, 1);
    assert.equal(byName(tree, "Panel").length, 0, "no Panels");
    assert.match(textOf(tree), new RegExp(title));
    assert.equal(byName(tree, "NavList")[0].props.items.length, 5);
    const control = byName(tree, "SegmentedControl")[0];
    same(control.props.options.map((o) => o.value), ["en", "ar"]);
  }
  const source = fs.readFileSync("static/ctm/ui-workspaces.js", "utf8");
  assert.doesNotMatch(source, /ctm-account-(hero|grid)/);
});

test("historical entry follows form-flow: sections, then one FormActions with the primary action last; admin only", async () => {
  const { tree } = await mount("Workspace", { api: server().api, user: admin, lang: "en" });
  const form = byName(tree, "Form").find((f) => f.props.label === "Historical case entry");
  same(byName(form, "FormSection").map((n) => n.props.title), ["Case details", "Party A", "Party B"]);
  const actions = byName(form, "FormActions")[0];
  const last = actions.children.filter(Boolean).at(-1);
  assert.equal(last.props.variant, "primary");
  assert.equal(last.props.type, "submit");
  const denied = await mount("Workspace", { api: server().api, user: secretary, lang: "en" });
  assert.equal(byName(denied.tree, "Form").length, 0);
});
