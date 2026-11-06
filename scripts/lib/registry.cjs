// Reads agents.config.yaml (the role registry, template v2.4 §5.1).
// The file uses a plain YAML subset - nested maps, lists of maps, [inline, lists],
// scalars and # comments - so CI and the dispatcher need no package install.
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const REGISTRY = path.join(ROOT, "agents.config.yaml");

function scalar(raw) {
  const v = raw.trim();
  if (v === "") return null;
  if (v.startsWith("[") && v.endsWith("]")) {
    const inner = v.slice(1, -1).trim();
    return inner ? inner.split(",").map((s) => scalar(s)) : [];
  }
  if (/^(['"]).*\1$/.test(v)) return v.slice(1, -1);
  if (v === "true") return true;
  if (v === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(v)) return Number(v);
  return v;
}

function lines(text) {
  return text.split(/\r?\n/).map((l, i) => {
    const s = l.replace(/(^|\s)#.*$/, "").replace(/\s+$/, "");
    return { n: i + 1, indent: s.length - s.trimStart().length, text: s.trim() };
  }).filter((l) => l.text);
}

function parseBlock(ls, i, indent) {
  // Returns [value, nextIndex]; a block is either a list (- items) or a map.
  if (ls[i].text.startsWith("- ")) {
    const list = [];
    while (i < ls.length && ls[i].indent === indent && ls[i].text.startsWith("- ")) {
      const first = ls[i].text.slice(2);
      const itemIndent = indent + 2;
      const synthetic = [{ n: ls[i].n, indent: itemIndent, text: first }];
      let j = i + 1;
      while (j < ls.length && ls[j].indent >= itemIndent) synthetic.push(ls[j++]);
      list.push(first.includes(":") ? parseBlock(synthetic, 0, itemIndent)[0] : scalar(first));
      i = j;
    }
    return [list, i];
  }
  const map = {};
  while (i < ls.length && ls[i].indent === indent) {
    const m = /^([A-Za-z0-9_\-]+):\s*(.*)$/.exec(ls[i].text);
    if (!m) throw new Error(`agents.config.yaml line ${ls[i].n}: expected "key: value"`);
    if (m[1] in map) throw new Error(`agents.config.yaml line ${ls[i].n}: duplicate key ${m[1]}`);
    if (m[2] === "" && i + 1 < ls.length && ls[i + 1].indent > indent) {
      const [v, next] = parseBlock(ls, i + 1, ls[i + 1].indent);
      map[m[1]] = v;
      i = next;
    } else {
      map[m[1]] = scalar(m[2]);
      i += 1;
    }
  }
  if (i < ls.length && ls[i].indent > indent) {
    throw new Error(`agents.config.yaml line ${ls[i].n}: unexpected indentation`);
  }
  return [map, i];
}

function parse(text) {
  const ls = lines(text);
  if (!ls.length) return {};
  const [v, i] = parseBlock(ls, 0, ls[0].indent);
  if (i !== ls.length) throw new Error(`agents.config.yaml line ${ls[i].n}: could not parse`);
  return v;
}

function load(file = REGISTRY) {
  return parse(fs.readFileSync(file, "utf8"));
}

module.exports = { ROOT, REGISTRY, parse, load };
