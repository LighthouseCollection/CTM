const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
function mount(props) {
  const window = { React: { createElement: (type, props, ...children) => ({type, props, children}) }, Plenix: { Table: "Table", DataGrid: "DataGrid", DataPill: "DataPill" } };
  vm.runInNewContext(fs.readFileSync("static/ctm/shell-layout.js", "utf8"), {window});
  return window.CTMShell.Table(props);
}
test("reference tables use native compact pill tables and retain zero values", () => {
  const rows=[{id:"one",total:0}];
  const result=mount({label:"Totals",rows,columns:[{title:"Total",field:"total",type:"number"}]});
  assert.equal(result.type,"Table");
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
test("custom cells are not double wrapped and column widths belong to the CDN", () => {
  const render=()=>"action";
  const result=mount({label:"Actions",rows:[],columns:[{field:"action",render,minWidth:"12rem"}]});
  assert.equal(result.props.columns[0].render({}).type,"DataPill");
  assert.equal(result.props.columns[0].render({}).props.size,"md");
  assert.equal(result.props.columns[0].pill,false);
  assert.equal(result.props.columns[0].minWidth,undefined);
});
