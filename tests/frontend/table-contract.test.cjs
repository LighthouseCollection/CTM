const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
function mount(props) {
  const window = { React: { createElement: (type, props, ...children) => ({type, props, children}) }, Plenix: { Table: "Table", DataGrid: "DataGrid", DataPill: "DataPill" } };
  vm.runInNewContext(fs.readFileSync("static/ctm/shell-layout.js", "utf8"), {window});
  return window.CTMShell.Table(props);
}
test("all tables use resizable native grids and retain zero values", () => {
  const rows=[{id:"one",total:0}];
  const result=mount({label:"Totals",rows,columns:[{title:"Total",field:"total",type:"number"}]});
  assert.equal(result.type,"DataGrid");
  assert.equal(result.props.columns[0].resizable,true);
  assert.equal(result.props.headerMenu,true);
  assert.equal(result.props.wrapHeaders,false);
  assert.equal(result.props.density,"compact");
  assert.equal(result.props.cells,"pill");
  assert.equal(result.props.data,rows);
});
test("workspaces retain native keyboard row opening and selection", () => {
  let opened;
  const result=mount({label:"Cases",rows:[{id:"one"}],columns:[{field:"name"}],selected:"one",onSelect:id=>opened=id});
  assert.equal(result.type,"DataGrid");
  result.props.onRowClick({id:"two"});
  assert.equal(opened,"two");
  assert.deepEqual(Array.from(result.props.selected),["one"]);
  assert.equal(result.props.density,"compact");
  // 0.86.0 defaults (#97 slice 1): type icons on and the open row marked.
  assert.equal(result.props.typeIcons,true);
  assert.equal(result.props.openKey,"one");
});
test("rich custom cells retain sizing and are not wrapped", () => {
  const render=()=>({type:"Button"});
  const result=mount({label:"Actions",rows:[{id:"one"}],columns:[{field:"action",render,minWidth:"12rem"}]});
  assert.equal(result.props.columns[0].render({}).type,"Button");
  assert.equal(result.props.columns[0].pill,false);
  assert.equal(result.props.columns[0].minWidth,"12rem");
});

test("action columns stay bounded without disabling their resize handles", () => {
  const result=mount({label:"Actions",rows:[],columns:[{field:"open_action",minWidth:"7rem",render:()=>({type:"Button"})}]});
  const column=result.props.columns[0];
  assert.equal(column.resizable,true);
  assert.equal(column.sortable,false);
  assert.equal("headerSort" in column,false);
  assert.equal(column.maxWidth,"--plx-ref-size-240px");
  assert.equal(column.minWidth,"7rem");
  assert.equal(column.render({}).type,"Button");
});

test("native person cells retain recorded gender and safe missing names", () => {
 const result=mount({label:"People",rows:[{id:"1",applicant:"Emma",applicant_gender:"F"},{id:"2",applicant:{gender:"M",name:""}},{id:"3",applicant:"Alex"}],columns:[{field:"applicant",type:"person"}]});
 const field=result.props.columns[0].field;
 assert.equal(result.props.data[0][field].gender,"female");
 assert.equal(result.props.data[1][field].name,"—");
 assert.equal(result.props.data[2][field].gender,undefined);
});

 test("068 projects scalar and gender cells through native pills without mutating source records",()=>{
  const rows=[{id:"one",applicant:"Emma",applicant_gender:"F",total:0}];
  const grid=mount({label:"People",rows,columns:[{field:"applicant",type:"person"},{field:"total",type:"number",render:r=>r.total}]});
  // Plenix 0.74.0 always uses uniform pill widths and ignores the option; CTM no longer sends it.
  assert.equal("uniformPillWidths" in grid.props,false);
  assert.equal(grid.props.columns[0].render,undefined);
  assert.equal(grid.props.data[0][grid.props.columns[0].field].gender,"female");
  assert.equal(grid.props.columns[1].render,undefined);
  assert.equal(grid.props.data[0][grid.props.columns[1].field],0);
  assert.equal(rows[0].applicant,"Emma");
});

test("formatted scalar cells retain domain ordering",()=>{
 const rows=[{id:"early",starts_at:"2026-10-22T09:00:00Z"},{id:"late",starts_at:"2026-10-22T14:00:00Z"}];
 const result=mount({label:"Times",rows,columns:[{field:"starts_at",type:"date",render:r=>r.id==="early"?"9:00 AM":"2:00 PM"}]});
 const c=result.props.columns[0];
 assert.equal(typeof c.sorter,"function");
 assert.ok(c.sorter("9:00 AM","2:00 PM",rows[0],rows[1],c.field,"asc")<0);
});

// #97 slice 8: in Arabic, Plenix's undocumented kind "id" laid case numbers out right to left (09-NEW-DEMO,
// 04-20261020). Case numbers and codes are documented "data" values, which read left to right.
test("case numbers and codes are LTR data cells, never kind id (Arabic DEMO-NEW-09, 20261020-04)",()=>{
  const grid=mount({label:"Cases",rows:[{id:"one",case_number:"20261020-04",number:"DEMO-NEW-09",code:"Q-1",ref:"X"}],
    columns:[{field:"case_number",kind:"name"},{field:"number",kind:["data","id"]},{field:"code"},{field:"ref",kind:["name","id"]}]});
  assert.equal(grid.props.columns[0].kind,"data");
  assert.equal(grid.props.columns[1].kind,"data");
  assert.equal(grid.props.columns[2].kind,"data");
  assert.deepEqual([...grid.props.columns[3].kind],["name"]); // plain copy: the array comes from the vm sandbox realm
  for (const file of fs.readdirSync("static/ctm").filter((name)=>name.endsWith(".js")))
    assert.doesNotMatch(fs.readFileSync(`static/ctm/${file}`,"utf8"),/kind: "id"|"id"]/,file);
});

// #97 slice 1: the collection foundation on the 0.86.0 DataGrid defaults and page templates.
const { harness, find, nameOf } = require("./harness.cjs");
function shell(extra = {}) {
  const h = harness();
  const Plenix = new Proxy({}, { get: (_t, key) => { const f = function () {}; f[Symbol.for("ctm.test.plenix")] = true; f.displayName = String(key); return f; } });
  const window = { React: h.React, Plenix, ...extra };
  vm.runInNewContext(fs.readFileSync("static/ctm/shell-layout.js", "utf8"), { window, document: { documentElement: { lang: "en" } } });
  return { h, S: window.CTMShell };
}
test("tables use the 0.86.0 narrow row cards by default and keep the fixed table as an opt-in", () => {
  const rows=[{id:"one",name:"A"}];
  assert.equal(mount({label:"Cases",rows,columns:[{field:"name"}]}).props.narrow,"auto");
  assert.equal(mount({label:"Cases",rows,columns:[{field:"name"}],narrow:"table"}).props.narrow,"table");
  assert.equal(mount({label:"Cases",rows,columns:[{field:"name"}],typeIcons:false}).props.typeIcons,false);
});
test("grids that still have a button column keep the fixed table so their buttons are not cut off", () => {
  const rows=[{id:"one",name:"A"}], button=()=>({type:"Button"});
  for (const field of ["open_action","actions","session_actions","row_action"])
    assert.equal(mount({label:"Cases",rows,columns:[{field:"name"},{field,render:button}]}).props.narrow,"table",field);
  assert.equal(mount({label:"Cases",rows,columns:[{field:"name"},{field:"x",kind:"actions",render:button}]}).props.narrow,"table");
  assert.equal(mount({label:"Cases",rows,columns:[{field:"name"},{field:"open_action",render:button}],narrow:"auto"}).props.narrow,"auto");
  assert.equal(mount({label:"Cases",rows,columns:[{field:"name"},{field:"transaction"}]}).props.narrow,"auto");
});
test("row menus are optional and existing button columns keep working beside them", () => {
  const rows=[{id:"one",name:"A"}], cols=[{field:"name"},{field:"open_action",render:()=>({type:"Button"})}];
  const plain=mount({label:"Cases",rows,columns:cols});
  assert.equal(plain.props.rowMenu,undefined);
  assert.equal(plain.props.rowMenuButton,false);
  let opened;
  const menu=[{label:"Open",icon:"open",onSelect:r=>opened=r.id}];
  const grid=mount({label:"Cases",rows,columns:cols,rowMenu:menu});
  assert.equal(grid.props.rowMenu,menu);
  assert.equal(grid.props.rowMenuButton,true);
  grid.props.rowMenu[0].onSelect(grid.props.data[0]);
  assert.equal(opened,"one");
  assert.equal(grid.props.columns[1].render({}).type,"Button");
});
test("row card slots, card count and extra documented grid props pass through", () => {
  const cardCount={one:"{n} case",other:"{n} cases"};
  const grid=mount({label:"Cases",rows:[],columns:[{field:"name"}],template:{title:"name"},layout:"B",keyColumns:["name"],cardCount,grid:{mode:"pages",pageSize:25}});
  assert.equal(grid.props.template.title,"name");
  assert.equal(grid.props.layout,"B");
  assert.deepEqual([...grid.props.keyColumns],["name"]);
  assert.equal(grid.props.strings.cardCount,cardCount);
  assert.equal(grid.props.mode,"pages");
  assert.equal(grid.props.pageSize,25);
  assert.equal("template" in mount({label:"Cases",rows:[],columns:[]}).props,false);
});
// D-0064 (issue 272): a loading table is a busy region named after the grid; no Skeleton rows (the spinner follows after a second).
test("loading tables are a busy region named after the grid, without skeletons", () => {
  const { h, S } = shell({ setTimeout, clearTimeout });
  const tree = h.render(S.Table, { label: "Cases", rows: [], columns: [], loading: true });
  assert.equal(find(tree, n => nameOf(n.type) === "DataGrid").length, 0);
  assert.equal(find(tree, n => nameOf(n.type) === "Skeleton").length, 0);
  assert.equal(find(tree, n => n.props && n.props["aria-busy"] === "true")[0].props["aria-label"], "Cases");
});
test("workspaces draw the SplitWorkspace body: toolbar, SplitView of the grid and a reading pane", () => {
  const { h, S } = shell();
  const rows=[{id:"one",title:"Case one"}];
  const empty = h.render(S.Workspace, { label: "Cases", rows, columns: [{field:"title"}], children: r => "detail " + r.id, actions: "act", commandBar: { actions: [{ id: "new", label: "New" }] } });
  const bar = find(empty, n => nameOf(n.type) === "CommandBar")[0];
  assert.equal(bar.props.label, "Cases");
  assert.equal(bar.props.actions[0].id, "new");
  const split = find(empty, n => nameOf(n.type) === "SplitView")[0];
  assert.equal(split.props.first.props.rowMenu, undefined);
  const pane = split.props.second;
  assert.equal(nameOf(pane.type), "ReadingPane");
  assert.equal(pane.props.actions, null, "no actions while nothing is open");
  assert.equal(nameOf(pane.props.empty.type), "EmptyState");
  const chosen = h.render(S.Workspace, { label: "Cases", rows, selected: "one", columns: [{field:"title"}], children: r => "detail " + r.id, actions: "act" });
  const open = find(chosen, n => nameOf(n.type) === "ReadingPane")[0];
  assert.equal(open.props.label, "Case one");
  assert.equal(open.props.actions, "act");
  assert.deepEqual(open.children, ["detail one"]);
});
test("a plain toolbar node still sits above the workspace", () => {
  const { h, S } = shell();
  const tree = h.render(S.Workspace, { label: "Notes", rows: [], columns: [], toolbar: { type: "Toolbar", props: {}, children: [] } });
  assert.equal(find(tree, n => n.type === "Toolbar").length, 1);
  assert.equal(find(tree, n => nameOf(n.type) === "CommandBar").length, 0);
});
test("listings draw the full-room ListingPage body and open the domain record", () => {
  const { h, S } = shell();
  let opened;
  const rows=[{id:"one",name:"A"}];
  const tree = h.render(S.Listing, { label: "Cases", rows, columns: [{field:"name"}], onOpen: r => opened = r, rowMenu: [{label:"Open"}] });
  const grid = find(tree, n => nameOf(n.type) === "DataGrid")[0];
  assert.equal(grid.props.mode, "fill");
  assert.equal(grid.props.rowMenuButton, true);
  grid.props.onRowClick({ id: "one" });
  assert.equal(opened, rows[0]);
});
test("search puts a CommandBarSearch on one collection state with the grid", () => {
  const view = { searchProps: { value: "", onChange() {}, onClear() {} }, filterProps: { fields: [] }, tableProps: { filter: () => true, onViewChange() {} } };
  let fields, options;
  const { h, S } = shell();
  // The hook is the CDN's; the test records what CTMShell asks of it.
  const Plenix = new Proxy({}, { get: (_t, key) => { if (key === "useCollectionView") return (f, o) => { fields = f; options = o; return view; };
    const f = function () {}; f[Symbol.for("ctm.test.plenix")] = true; f.displayName = String(key); return f; } });
  const window = { React: h.React, Plenix };
  vm.runInNewContext(fs.readFileSync("static/ctm/shell-layout.js", "utf8"), { window, document: { documentElement: { lang: "ar" } } });
  const text = r => r.name;
  const tree = h.render(window.CTMShell.Listing, { label: "القضايا", rows: [{id:"one",name:"A"}], columns: [{title:"Name",field:"name"}], search: { text, placeholder: "ابحث", filters: true } });
  assert.equal(options.text, text);
  assert.equal(fields[0].label, "Name");
  const search = find(tree, n => nameOf(n.type) === "CommandBarSearch")[0];
  assert.equal(search.props.placeholder, "ابحث");
  assert.equal(find(tree, n => nameOf(n.type) === "FilterPanel").length, 1);
  const grid = find(tree, n => nameOf(n.type) === "DataGrid")[0];
  assert.equal(grid.props.filter, view.tableProps.filter);
  assert.equal(grid.props.onViewChange, view.tableProps.onViewChange);
});
test("searched grids keep the same data array and row copies while the records are unchanged (PLX-013)", () => {
  // The grid's data is also the hook's options.data; read it there (the harness copies element props).
  let data;
  const view = { searchProps: {}, filterProps: {}, tableProps: { filter: () => true } };
  const h = harness();
  const Plenix = new Proxy({}, { get: (_t, key) => { if (key === "useCollectionView") return (_f, o) => { data = o.data; return view; };
    const f = function () {}; f[Symbol.for("ctm.test.plenix")] = true; f.displayName = String(key); return f; } });
  const window = { React: h.React, Plenix };
  vm.runInNewContext(fs.readFileSync("static/ctm/shell-layout.js", "utf8"), { window, document: { documentElement: { lang: "en" } } });
  const rows = [{ id: "one", applicant: "Emma", applicant_gender: "F" }];
  const draw = () => { h.render(window.CTMShell.Listing, { label: "Cases", rows: rows.slice(), columns: [{ field: "applicant", type: "person" }], search: { text: r => r.applicant } }); return data; };
  const first = draw(), second = draw();
  assert.equal(second, first);
  rows[0] = { ...rows[0], applicant: "Emma B" };
  const third = draw();
  assert.notEqual(third, first);
  assert.equal(third[0].__ctm_display_0.name, "Emma B");
});

// #97 slice 8: parallel slices once appended the same PLX number twice; every request id is unique.
test("plenix-requests.md has one row per PLX id", () => {
  const ids = [...fs.readFileSync("docs/implementation/plenix-requests.md", "utf8").matchAll(/^\| (PLX-\d+) \|/gm)].map((m) => m[1]);
  assert.ok(ids.length >= 23);
  assert.deepEqual(ids.filter((id, i) => ids.indexOf(id) !== i), []);
});

// #111: in the fixed table (a grid with row buttons) a button column without a width was drawn at its 240px
// cap, so the session agenda overflowed at 1280px and its overlay scrollbar sat on the rows. A button column
// now takes the width its caller asks for (width, else minWidth).
test("button columns are as wide as the caller asks, not their 240px cap (#111)", () => {
  const sized = mount({ label: "Agenda", rows: [], columns: [{ field: "open_action", minWidth: "9rem", render: () => ({ type: "Button" }) }] });
  assert.equal(sized.props.columns[0].width, "9rem");
  const explicit = mount({ label: "Agenda", rows: [], columns: [{ field: "open_action", width: "10rem", minWidth: "9rem", render: () => ({ type: "Button" }) }] });
  assert.equal(explicit.props.columns[0].width, "10rem");
  const plain = mount({ label: "Cases", rows: [], columns: [{ field: "name", minWidth: "9rem" }] });
  assert.equal("width" in plain.props.columns[0], false, "text columns keep Plenix's content sizing");
});

// #118 / #114: short values are content-sized so the spare room is not given to the first column.
test("session list and agenda columns are fitted to their content (#118, #114, #111)", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const list = council.slice(council.indexOf('const manage = mode === "upcoming" && canManage(user);'), council.indexOf("const listProps = {"));
  // Status keeps no width: it is the last content-sized column, so it (capped at 240px) and the row menu take the spare room.
  for (const field of ["date", "session_time", "adjourned_time", "assigned_case_count", "hearing_case_count"])
    assert.match(list, new RegExp(`field: "${field}",[^\n]*width: "`), field);
  assert.doesNotMatch(list, /minWidth/);
  const agenda = council.slice(council.indexOf("const title = first ? t(\"casesToAssign\")"), council.indexOf("ctm-session-agenda-grid"));
  assert.equal((agenda.match(/title: t\("actions"\), field: "open_action", minWidth: "9rem"/g) || []).length, 2);
  // Every hearings-agenda column except "#" has a width, so Plenix's fixed table does not stretch one past the room (PLX-025).
  const hearings = agenda.slice(agenda.indexOf('title: "#"'));
  for (const field of ["applicant", "respondent", "assigned_member_name", "previous_recommendation"])
    assert.match(hearings, new RegExp(`field: "${field}",[^\\n]*width: "`), field);
  // #110: Plenix 1.1.0+ (D-0108, #966) draws a column with no `width` or `minWidth` as wide as its content (at least
  // 32px), so "#" sets neither and fits its one or two digits.
  const ordinal = hearings.slice(0, hearings.indexOf("\n"));
  assert.match(ordinal, /title: "#", field: "hearing_number", kind: \["name", "data"\] \}/, "#110: content-sized ordinal");
  assert.doesNotMatch(ordinal, /width|minWidth/i, "#110: no width on the # column");
});
