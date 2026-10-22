// Minimal render harness for council components: real module code, a tiny hook runtime and named
// placeholders for Plenix components. No browser and no React package. Not a test file itself.
// Nested function components are rendered too, each with its own hook state (keyed by tree position and
// key), and effects honour dependency lists and cleanups like React.
const fs = require("node:fs");
const vm = require("node:vm");

const PLENIX = Symbol.for("ctm.test.plenix");

function harness() {
  let fibers = new Map(); // instance path -> { states, deps, cleanups }
  let current = null;
  let index = 0;
  let effectIndex = 0;
  let pending = [];
  let seen = new Set();
  const React = {
    useState(init) {
      const fiber = current;
      const i = index++;
      if (!(i in fiber.states)) fiber.states[i] = typeof init === "function" ? init() : init;
      return [fiber.states[i], (v) => { fiber.states[i] = typeof v === "function" ? v(fiber.states[i]) : v; }];
    },
    useEffect(fn, deps) {
      const fiber = current;
      const i = effectIndex++;
      const previous = fiber.deps[i];
      const changed = !deps || !previous || deps.length !== previous.length || deps.some((d, k) => !Object.is(d, previous[k]));
      if (changed) {
        fiber.deps[i] = deps;
        pending.push(() => {
          if (typeof fiber.cleanups[i] === "function") fiber.cleanups[i]();
          fiber.cleanups[i] = fn();
        });
      }
    },
    useRef(initial) {
      const [ref] = React.useState(() => ({ current: initial }));
      return ref;
    },
    useMemo(compute, deps) {
      const [memo] = React.useState(() => ({ deps: undefined, value: undefined }));
      if (!memo.deps || !deps || deps.length !== memo.deps.length || deps.some((d, k) => !Object.is(d, memo.deps[k]))) {
        memo.deps = deps;
        memo.value = compute();
      }
      return memo.value;
    },
    useCallback: (fn, deps) => React.useMemo(() => fn, deps),
    useReducer(reducer, initial, init) {
      const [value, set] = React.useState(() => (init ? init(initial) : initial));
      return [value, (action) => set((old) => reducer(old, action))];
    },
    createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }),
  };
  const isComponent = (type) =>
    typeof type === "function" && !type[PLENIX] && !(type.prototype && type.prototype.isReactComponent);
  function call(type, props, path) {
    if (!fibers.has(path)) fibers.set(path, { states: [], deps: [], cleanups: [] });
    seen.add(path);
    const saved = [current, index, effectIndex];
    current = fibers.get(path);
    index = 0;
    effectIndex = 0;
    try {
      return type(props);
    } finally {
      [current, index, effectIndex] = saved;
    }
  }
  function renderValue(value, path) {
    if (!value || typeof value !== "object") return value;
    if (Array.isArray(value)) return value.map((v, i) => renderValue(v, `${path}.${i}`));
    if ("type" in value && "props" in value) return renderNode(value, path);
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = typeof v === "function" ? v : renderValue(v, `${path}/${k}`);
    return out;
  }
  function renderNode(node, path) {
    if (isComponent(node.type)) {
      const id = `${path}:${node.type.name || "C"}${node.props.key != null ? `#${node.props.key}` : ""}`;
      const output = call(node.type, { ...node.props, children: node.children }, id);
      return { type: node.type, props: node.props, children: [renderValue(output, id)] };
    }
    const props = {};
    for (const [k, v] of Object.entries(node.props)) props[k] = typeof v === "function" ? v : renderValue(v, `${path}/${k}`);
    return { type: node.type, props, children: (node.children || []).map((c, i) => renderValue(c, `${path}.${i}`)) };
  }
  function dispose(paths) {
    for (const p of paths) {
      const fiber = fibers.get(p);
      if (fiber) fiber.cleanups.forEach((c) => typeof c === "function" && c());
      fibers.delete(p);
    }
  }
  return {
    React,
    // Renders the component tree; returns the top component's own output (nested components stay as nodes).
    render(component, props) {
      pending = [];
      seen = new Set();
      const output = call(component, props, "root");
      const tree = renderValue(output, "root");
      dispose([...fibers.keys()].filter((p) => !seen.has(p)));
      pending.forEach((f) => f());
      return tree;
    },
    // What in-app navigation does to the page's component state.
    unmount() {
      dispose([...fibers.keys()]);
    },
  };
}

// Any Plenix component is a named placeholder; nested names (PropertyList.Item) work too.
const named = (name) =>
  new Proxy(function () {}, { get: (_t, key) => (key === PLENIX ? true : key === "displayName" ? name : named(`${name}.${String(key)}`)) });
const Plenix = new Proxy({}, { get: (_t, key) => named(String(key)) });
const nameOf = (type) => (type && type[PLENIX] && type.displayName) || "";

function load(h, extra = {}) {
  const window = { React: h.React, Plenix, addEventListener() {}, removeEventListener() {}, ...extra };
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
// Visible text: children plus the text-bearing props Plenix renders (titles, labels, messages).
const TEXT_PROPS = ["title", "label", "message", "description"];
const textOf = (node) => {
  if (node === null || node === undefined || node === false) return "";
  if (typeof node !== "object") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join(" ");
  const own = "props" in node ? TEXT_PROPS.map((k) => (typeof node.props[k] === "string" ? node.props[k] : "")).join(" ") : "";
  return `${own} ${(node.children || []).map(textOf).join(" ")}`;
};
const byName = (tree, name) => find(tree, (n) => nameOf(n.type) === name);
const textareas = (tree) => byName(tree, "Textarea");
const notices = (tree) => byName(tree, "Notice").map(textOf);
const buttons = (tree, label) => find(tree, (n) => nameOf(n.type) === "Button" && textOf({ children: n.children }).trim() === label);
const dialogs = (tree) => byName(tree, "ConfirmDialog");
const type = (area, value) => area.props.onChange({ target: { value } });
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

module.exports = { harness, load, find, textOf, byName, textareas, notices, buttons, dialogs, type, settle, nameOf };
