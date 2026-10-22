// Minimal render harness for council components: real module code, a tiny hook runtime and named
// placeholders for Plenix components. No browser and no React package. Not a test file itself.
const fs = require("node:fs");
const vm = require("node:vm");

function harness() {
  let states = [];
  let index = 0;
  let effects = [];
  const React = {
    useState(init) {
      const i = index++;
      if (!(i in states)) states[i] = typeof init === "function" ? init() : init;
      return [states[i], (v) => { states[i] = typeof v === "function" ? v(states[i]) : v; }];
    },
    useEffect(fn) { effects.push(fn); },
    createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }),
  };
  return {
    React,
    render(component, props) {
      index = 0;
      effects = [];
      const tree = component(props);
      effects.forEach((f) => f());
      return tree;
    },
    unmount() { states = []; }, // what in-app navigation does to the page's component state
  };
}

// Any Plenix component is a named placeholder; nested names (PropertyList.Item) work too.
const named = (name) => new Proxy(function () {}, { get: (_t, key) => (key === "displayName" ? name : named(`${name}.${String(key)}`)) });
const Plenix = new Proxy({}, { get: (_t, key) => named(String(key)) });
const nameOf = (type) => (type && type.displayName) || "";

function load(h) {
  const window = { React: h.React, Plenix, addEventListener() {}, removeEventListener() {} };
  const context = { window, console };
  for (const file of ["council.js", "council-case.js", "council-decree.js", "council-media.js"])
    vm.runInNewContext(fs.readFileSync(`static/ctm/${file}`, "utf8"), context);
  return window.CTMCouncil;
}

// Walks children and element-valued props (Tabs items[].content, SplitView first/second, ...).
function find(tree, predicate, out = []) {
  if (!tree || typeof tree !== "object") return out;
  if (Array.isArray(tree)) {
    for (const item of tree) find(item, predicate, out);
    return out;
  }
  if ("type" in tree && "props" in tree) {
    if (predicate(tree)) out.push(tree);
    for (const child of tree.children || []) find(child, predicate, out);
    for (const value of Object.values(tree.props)) if (value && typeof value === "object") find(value, predicate, out);
    return out;
  }
  for (const value of Object.values(tree)) if (value && typeof value === "object") find(value, predicate, out);
  return out;
}
const textOf = (node) =>
  node === null || node === undefined || node === false ? "" : typeof node !== "object" ? String(node) : (node.children || []).map(textOf).join(" ");
const byName = (tree, name) => find(tree, (n) => nameOf(n.type) === name);
const textareas = (tree) => byName(tree, "Textarea");
const notices = (tree) => byName(tree, "Notice").map(textOf);
const buttons = (tree, label) => find(tree, (n) => nameOf(n.type) === "Button" && textOf(n).trim() === label);
const dialogs = (tree) => byName(tree, "ConfirmDialog");
const type = (area, value) => area.props.onChange({ target: { value } });
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

module.exports = { harness, load, find, textOf, byName, textareas, notices, buttons, dialogs, type, settle, nameOf };
