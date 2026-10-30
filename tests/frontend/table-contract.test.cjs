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
  assert.equal(result.props.typeIcons,false);
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

test("case numbers are id cells so Arabic pages read them 01-20261020 (Plenix 0.76.0)",()=>{
  const grid=mount({label:"Cases",rows:[{id:"one",case_number:"20261020-01",code:"Q-1"}],columns:[{field:"case_number",kind:"name"},{field:"code"}]});
  assert.deepEqual(grid.props.columns[0].kind,["data","id"]);
  assert.equal(grid.props.columns[1].kind,"data");
});
