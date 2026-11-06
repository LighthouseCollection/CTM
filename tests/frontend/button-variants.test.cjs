// D-0036 (#115): CTM uses Plenix Button variants by role and never restyles buttons.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const dir = path.join(__dirname, "..", "..", "static", "ctm");
const files = fs.readdirSync(dir).filter((f) => f.endsWith(".js"));
const sources = files.map((f) => ({ f, src: fs.readFileSync(path.join(dir, f), "utf8") }));

// Each P.Button(...) call's props object, up to its first closing brace.
function buttons(src) {
  const out = [];
  const re = /h\(P\.Button,\s*\{([^}]*)\}/g;
  let m;
  while ((m = re.exec(src))) out.push({ props: m[1], at: m.index });
  return out;
}

test("filled danger buttons only confirm inside a dialog footer", () => {
  for (const { f, src } of sources) {
    for (const b of buttons(src)) {
      if (!/variant:\s*"danger"/.test(b.props)) continue;
      const before = src.slice(Math.max(0, b.at - 1500), b.at);
      const footer = before.lastIndexOf("footer:");
      const dialog = Math.max(before.lastIndexOf("P.Dialog"), before.lastIndexOf("P.ConfirmDialog"));
      assert.ok(footer > -1 && dialog > -1 && dialog < footer, `${f}: variant "danger" Button outside a dialog footer`);
    }
  }
});

test("no tertiary buttons and no button restyling", () => {
  for (const { f, src } of sources) {
    for (const b of buttons(src)) {
      assert.ok(!/variant:\s*"tertiary"/.test(b.props), `${f}: tertiary Button is not used in CTM`);
      assert.ok(!/className:\s*"[^"]*plx-button/.test(b.props), `${f}: Button restyled through plx-button class`);
      assert.ok(!/\bstyle\s*:/.test(b.props), `${f}: Button with inline style`);
    }
  }
});
