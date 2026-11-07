// D-0045 (#170): every CTM page fills the window; the Plenix 1366px centered frame is not used.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const dir = path.join(__dirname, "..", "..", "static", "ctm");

test("AppShell uses the full-window frame", () => {
  for (const f of fs.readdirSync(dir).filter((n) => n.endsWith(".js"))) {
    const src = fs.readFileSync(path.join(dir, f), "utf8");
    assert.ok(!/frame:\s*"centered"/.test(src), `${f}: AppShell frame "centered" (use "full", D-0045)`);
  }
});
