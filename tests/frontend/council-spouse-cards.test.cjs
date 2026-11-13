// #240 (D-0057): each spouse is one collapsible Plenix Panel. The header holds the photo (Avatar) in the icon spot,
// the name and an Applicant / Respondent badge, and nothing else; Change photo is a small ghost icon button with a
// tooltip, Edit stays in the header actions; CTM ID and the portal account live in the body. The whole header
// toggles through Plenix's own toggleOn="header", not a CTM click handler. Synthetic data only.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { harness, load, find, byName, textOf, settle, nameOf } = require("./harness.cjs");

const source = fs.readFileSync("static/ctm/council-case.js", "utf8");
const secretary = { id: "u-mgr", role: "member", name: "Synthetic Manager" }; // the assigned member may edit
const member = { id: "u-mem", role: "member", name: "Synthetic Member" };

const record = {
  id: "c1", number: "20261020-04", status: "open", assigned_member_id: "u-mgr", assigned_member: "Synthetic Manager",
  assignment_history: [{ id: "a1", member_id: "u-mgr", member: "Synthetic Manager" }],
  parties: [
    { id: "p1", slot: "A", name: "Applicant Synthetic", reference: "20261020-04-AS19800101F", gender: "F", can_receive: true, profile: { personal: { nationality: "Synthetic" } } },
    { id: "p2", slot: "B", name: "Respondent Synthetic", reference: "20261020-04-RS19790101M", gender: "M", can_receive: false },
  ],
  proceedings: [{ id: "pr1", status: "open", sequence: 1 }],
  marriage: {}, separation: {}, summary: {},
};
const routes = {
  "/api/cases/c1/": record, "/api/cases/c1/audit/": { items: [] }, "/api/cases/c1/requests/": { items: [] },
  "/api/cases/c1/reports/": { items: [] }, "/api/cases/c1/calls/": { items: [] }, "/api/proceedings/pr1/notes/": { items: [] },
  "/api/proceedings/pr1/decision/": { items: [] }, "/api/council/members/": { items: [] }, "/api/cases/": { items: [] },
  "/api/applications/": { items: [] }, "/api/sessions/": { items: [] }, "/api/report-questions/": { items: [] },
};
const api = async (url) => {
  const route = routes[url.split("?")[0]];
  if (route === undefined) throw Object.assign(new Error(`HTTP 404 ${url}`), { status: 404 });
  return route;
};

async function mount(lang, user) {
  const h = harness();
  h.React.Component = class Component { constructor(props) { this.props = props; } };
  h.React.Component.prototype.isReactComponent = {};
  const C = load(h, { document: { documentElement: { lang } }, CTMShell: { Workspace: function Workspace() { return null; }, Table: function Table() { return null; } }, CTMUI: { filterAudit: (rows) => rows, AuditFilters: function AuditFilters() { return null; } } });
  const props = { api, lang, user, caseId: "c1" };
  let tree = h.render(C.CaseParties, props);
  for (let i = 0; i < 4; i++) { await settle(); tree = h.render(C.CaseParties, props); }
  return tree;
}

const WORDS = {
  en: { applicant: "Applicant", respondent: "Respondent", changePhoto: "Change photo", ctmId: "CTM ID#", portal: "Portal account", collapse: "Collapse" },
  ar: { applicant: "مقدم الطلب", respondent: "الطرف الآخر", changePhoto: "تغيير الصورة", ctmId: "معرّف CTM#", portal: "حساب البوابة", collapse: "طي" },
};

for (const lang of ["en", "ar"]) {
  test(`${lang}: one collapsible Panel per spouse, whole header toggles through Plenix, no CTM click workaround`, async () => {
    const tree = await mount(lang, secretary);
    const panels = byName(tree, "Panel");
    assert.equal(panels.length, 2);
    for (const panel of panels) {
      assert.equal(panel.props.collapsible, true);
      assert.equal(panel.props.toggleOn, "header");
      assert.equal(panel.props.onClick, undefined, "no click handler on the Panel");
      assert.equal(panel.props.className, undefined);
    }
  });

  test(`${lang}: title is the name and a role badge only; the photo is the Avatar in the icon spot`, async () => {
    const tree = await mount(lang, secretary);
    const w = WORDS[lang];
    const [first, second] = byName(tree, "Panel");
    for (const [panel, name, role] of [[first, "Applicant Synthetic", w.applicant], [second, "Respondent Synthetic", w.respondent]]) {
      const title = textOf(panel.props.title).replace(/\s+/g, " ").trim();
      assert.equal(title, `${name} ${role}`, "name and role, nothing else");
      const badges = byName(panel.props.title, "Badge");
      assert.equal(badges.length, 1);
      assert.equal(badges[0].props.tone, "neutral");
      assert.equal(textOf({ children: badges[0].children }).trim(), role);
      const avatars = byName(panel.props.icon, "Avatar");
      assert.equal(avatars.length, 1);
      assert.equal(avatars[0].props.size, "sm");
      assert.equal(avatars[0].props.name, name);
      assert.equal(byName(panel.props.icon, "AvatarUpload").length, 0, "no upload control in the icon spot");
      assert.ok(panel.props.strings.collapse.includes(name) && !panel.props.strings.collapse.includes("{"), "collapse label names the spouse");
      assert.ok(panel.props.strings.expand.includes(name) && !panel.props.strings.expand.includes("{"), "expand label names the spouse");
    }
  });

  test(`${lang}: Change photo is a small ghost icon-only button with a tooltip, before Edit, opening a dialog`, async () => {
    const tree = await mount(lang, secretary);
    const w = WORDS[lang];
    const [panel] = byName(tree, "Panel");
    const buttons = byName(panel.props.actions, "Button");
    assert.equal(buttons.length, 2);
    const [photo, edit] = buttons;
    assert.equal(photo.props.variant, "ghost");
    assert.equal(photo.props.size, "sm");
    assert.equal(photo.props.icon, "photo_camera");
    assert.equal(photo.props["aria-label"], w.changePhoto);
    assert.equal(textOf({ children: photo.children }).trim(), "", "icon only");
    const tips = byName(panel.props.actions, "Tooltip");
    assert.equal(tips.length, 1);
    assert.equal(tips[0].props.content, w.changePhoto);
    assert.equal(edit.props.size, "sm");
    assert.equal(byName(panel.props.body ?? panel.children, "AvatarUpload").length, 0, "not inside the card body or edit form");
  });

  test(`${lang}: CTM ID (plain body text) and the portal account badge are in Personal details, not the title`, async () => {
    const tree = await mount(lang, secretary);
    const w = WORDS[lang];
    const [panel] = byName(tree, "Panel");
    assert.ok(!textOf(panel.props.title).includes("20261020-04-AS19800101F"));
    const items = byName({ children: panel.children }, "PropertyList.Item");
    const id = items.find((item) => item.props.label === w.ctmId);
    assert.ok(id, "CTM ID item");
    assert.equal(id.props.data, undefined, "plain body text, not monospace");
    assert.match(textOf({ children: id.children }), /20261020-04-AS19800101F/);
    const portal = items.find((item) => item.props.label === w.portal);
    assert.ok(portal, "portal account item");
    assert.equal(byName({ children: portal.children }, "Badge").length, 1);
  });
}

test("a user who may not edit the case sees no Change photo and no Edit", async () => {
  const tree = await mount("en", member);
  for (const panel of byName(tree, "Panel")) assert.equal(byName(panel.props.actions ?? null, "Button").length, 0);
});

test("source: the helper and the click workaround are gone", () => {
  const parties = source.slice(source.indexOf("function CaseParties"));
  assert.ok(!source.includes("spouseHeaderTitle"));
  assert.ok(!source.includes("data-ctm-no-toggle"));
  assert.ok(!/plx-panel__header/.test(parties));
  assert.ok(!/ctm-spouse-profile-edit/.test(source));
});
