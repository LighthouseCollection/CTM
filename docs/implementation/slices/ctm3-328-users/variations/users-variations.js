/* Issue #328: four variations of CTM Settings > Users, for the owner's pick. Fictional people only.
 * Documented Plenix 1.6.1 parts only; no inline styles, no local CSS. Open users-variations.html?v=A|B|C|D. */
(function () {
  const R = window.React, P = window.Plenix, h = R.createElement;
  const v = (new URLSearchParams(location.search).get("v") || "A").toUpperCase();
  const roleLabel = { admin: "Administrator", president: "President", secretary: "Secretary", member: "Council member" };
  const people = [
    ["Mark", "Habib", "president", 12, true, true],
    ["Sarah", "Mikhail", "secretary", 8, true, false],
    ["Peter", "Ghaly", "admin", 0, false, false],
    ["Mina", "Farag", "member", 5, true, true],
    ["Mary", "Nassif", "member", 3, true, true],
    ["John", "Wassef", "member", 6, true, true],
    ["Martha", "Iskander", "member", 2, true, false],
    ["George", "Tadros", "member", 4, true, true],
    ["Demiana", "Saad", "member", 0, false, false],
    ["Andrew", "Boulos", "member", 1, true, true],
  ].map(([first, last, role, cases, seated, voting], i) => ({
    id: String(i + 1), first_name: first, last_name: last, name: `${first} ${last}`, role, role_label: roleLabel[role],
    email: `${first}.${last}@example.org`.toLowerCase(), active_case_count: cases, seated, voting: seated && voting, active: true,
  }));

  const casesText = (n) => n === 0 ? "No active cases" : n === 1 ? "1 active case" : `${n} active cases`;
  // One reading of the council seat for every variation: a badge with its icon (owner rule: statuses are badges with an icon).
  const seatBadge = (p) => p.seated
    ? h(P.Badge, { tone: p.voting ? "success" : "active", icon: p.voting ? "gavel" : "person" }, p.voting ? "Voting seat" : "Non-voting seat")
    : h(P.Badge, { tone: "neutral", icon: "person-cancel" }, "No seat");
  const menuItems = (p) => [
    h(P.MenuItem, { key: "e", icon: "pencil" }, "Edit"),
    h(P.MenuItem, { key: "s", icon: "groups" }, "Council seat"),
    h(P.MenuItem, { key: "a", icon: "key" }, "Manage access"),
    h(P.MenuDivider, { key: "d" }),
    h(P.MenuItem, { key: "x", icon: "archive", danger: true }, "Archive"),
  ];
  const moreMenu = (p) => h(P.Menu, { trigger: h(P.Button, { variant: "ghost", iconOnly: true, icon: "more", label: `Actions for ${p.name}` }), placement: "bottom-end" }, ...menuItems(p));

  const bar = (count) => h(P.CommandBar, {
    label: "Users", count: `${count} members`,
    actions: [
      { id: "add", label: "Add staff user", icon: "add", primary: true, onSelect: () => {} },
      { id: "view", label: "Members shown", value: "active", onChange: () => {}, choices: [{ value: "active", label: "Active Members" }, { value: "previous", label: "Previous Members" }] },
    ],
    find: h(P.CommandBarSearch, { value: "", onChange: () => {}, onClear: () => {}, placeholder: "Search members" }),
  });

  // A: one DataGrid table, seats as read-only badges; changes go through the row menu ("Council seat" opens a small dialog).
  function VariantA() {
    const rowMenu = [{ label: "Edit", icon: "pencil", onSelect: () => {} }, { label: "Council seat", icon: "groups", onSelect: () => {} },
      { label: "Manage access", icon: "key", onSelect: () => {} }, { separator: true }, { label: "Archive", icon: "archive", danger: true, onSelect: () => {} }];
    const columns = [
      { title: "Name", field: "person", kind: "avatar-name" },
      { title: "Role", field: "role_label" },
      { title: "Council seat", field: "seat", kind: "center", sortable: false, render: seatBadge, minWidth: "--plx-ref-size-160px" },
      // Status is left out: the view already says Active Members or Previous Members.
      { title: "Active cases", field: "active_case_count", type: "number", kind: "data" },
    ];
    const rows = people.map((p) => ({ ...p, person: { name: p.name } }));
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" }, bar(rows.length),
      h(P.DataGrid, { label: "Active Members", data: rows, index: "id", columns, rowMenu, density: "compact", cells: "text", narrow: "auto", mode: "fill",
        template: { title: "person", subtitle: "role_label", primary: "active_case_count", secondary: "email", tertiary: "seat" },
        strings: { cardCount: { one: "{n} member", other: "{n} members" } } }));
  }

  // B: list + details. The compact list in the settings column; the chosen person in a SidePanel at the shell's end
  // (secondary-pane.md: "a SidePanel for the details of the chosen record ... given to the AppShell's panel").
  const chosen = people[3];
  function VariantB() {
    const items = people.map((p) => ({ id: p.id, name: p.name, description: `${p.role_label} · ${p.email}`, avatar: { name: p.name },
      meta: seatBadge(p), onOpen: () => {} }));
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" }, bar(people.length),
      h(P.ResourceList, { label: "Active Members", noun: "member", items, selected: [chosen.id] }));
  }
  function DetailB() {
    return h(P.SidePanel, { title: chosen.name, open: true, onOpenChange: () => {}, collapseLabel: "Close details",
      footer: h(P.Inline, { gap: "sm" }, h(P.Button, { icon: "pencil" }, "Edit"), h(P.Button, { icon: "key" }, "Manage access"), moreMenu(chosen)) },
      h(P.Stack, { gap: "lg" },
        h(P.Inline, { gap: "md", align: "center" }, h(P.Avatar, { name: chosen.name, size: "lg" }),
          h(P.Text, { variant: "muted" }, chosen.role_label)),
        h(P.PropertyList, { layout: "stacked" },
          h(P.PropertyList.Item, { label: "Email", data: true }, chosen.email),
          h(P.PropertyList.Item, { label: "Active cases", data: true }, String(chosen.active_case_count)),
          h(P.PropertyList.Item, { label: "Status", status: { label: "Active", tone: "success", icon: "check" } })),
        h(P.SettingsSection, { title: "Council seat", headingLevel: 3, description: "Voting needs a seat." },
          h(P.SettingsRow, { label: "Council seat" }, h(P.Switch, { checked: chosen.seated, onChange: () => {}, "aria-label": "Council seat" })),
          h(P.SettingsRow, { label: "Voting" }, h(P.Switch, { checked: chosen.voting, onChange: () => {}, "aria-label": "Voting" })))));
  }

  // C: a compact people list, grouped by council seat; one line per person, seat and cases at the row's end.
  function VariantC() {
    const group = (p) => p.seated ? "Council members" : "Staff without a council seat";
    const ordered = [...people].sort((a, b) => Number(b.seated) - Number(a.seated));
    const items = ordered.map((p) => ({ id: p.id, name: p.name, description: `${p.role_label} · ${p.email}`, avatar: { name: p.name }, group: group(p),
      meta: h(P.Inline, { gap: "sm", align: "center" }, h(P.Text, { variant: "muted" }, casesText(p.active_case_count)), seatBadge(p)),
      actions: moreMenu(p), onOpen: () => {} }));
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" }, bar(people.length),
      h(P.ResourceList, { label: "Active Members", noun: "member", items }));
  }

  // D: people cards in a responsive grid (UserCard), the seat and cases as detail lines.
  function VariantD() {
    const cards = people.map((p) => h(P.UserCard, { key: p.id, name: p.name, secondary: p.email, role: p.role_label, headingLevel: 3,
      details: [{ icon: "groups", label: p.seated ? (p.voting ? "Council seat, voting" : "Council seat, non-voting") : "No council seat" },
        { icon: "briefcase", label: casesText(p.active_case_count) }],
      actions: h(P.Inline, { gap: "sm" }, h(P.Button, { variant: "secondary", icon: "pencil" }, "Edit"), moreMenu(p)) }));
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" }, bar(people.length),
      h(P.ContentGrid, { size: "md", label: "Active Members" }, ...cards));
  }

  const variant = { A: VariantA, B: VariantB, C: VariantC, D: VariantD }[v] || VariantA;
  function Page() {
    const nav = h(P.NavList, { label: "Settings sections", value: "members", onSelect: () => {}, items: [
      { id: "members", label: "Users & Roles", icon: "settings-users" }, { id: "configuration", label: "Tribunal Config", icon: "settings" },
      { id: "historical", label: "Data & Records", icon: "archive" }, { id: "audit", label: "Audit & Security", icon: "lock" }] });
    return h(P.SettingsLayout, { className: "plx-u-flex-1 plx-u-min-h-0", nav },
      h(P.Text, { as: "h1", variant: "title" }, "CTM Settings"),
      h(P.Text, { as: "h2", variant: "heading" }, "Users"),
      h(variant));
  }
  function boot() {
    const root = document.getElementById("root");
    window.ReactDOM.createRoot(root).render(h(P.ThemeProvider, null, h(P.AppShell, { frame: "centered", page: "workspace", panel: v === "B" ? h(DetailB) : undefined },
      h(P.PageContent, null, h(P.Stack, { className: "plx-u-flex-1 plx-u-min-h-0" }, h(Page))))));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
