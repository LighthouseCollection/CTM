// D-0063 (CTM#289, owner; Plenix D-0093): CTM opens in the 1366px centered frame, with the header's expand toggle.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const dir = path.join(__dirname, "..", "..", "static", "ctm");

test("AppShell uses the 1366px centered frame", () => {
  let shells = 0;
  for (const f of fs.readdirSync(dir).filter((n) => n.endsWith(".js"))) {
    const src = fs.readFileSync(path.join(dir, f), "utf8");
    assert.ok(!/frame:\s*"full"/.test(src), `${f}: AppShell frame "full" (use "centered", D-0063)`);
    shells += (src.match(/frame:\s*"centered"/g) || []).length;
  }
  assert.ok(shells >= 2, "both shells (sign-in and council) pass frame \"centered\"");
});
