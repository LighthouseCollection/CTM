// Issue 144: Plenix 0.91.0 marks these utility classes as going away (PDS#723, PDS#737). CTM stays off them.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const GOING_AWAY = ["plx-u-absolute", "plx-u-top-0", "plx-u-left-0", "plx-u-right-0", "plx-u-justify-center",
  "plx-u-text-center", "plx-u-bg-transparent", "plx-u-w-36px", "plx-u-w-72px", "plx-u-w-100px"];

function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? files(full) : /\.(js|html)$/.test(entry.name) ? [full] : [];
  });
}

test("no CTM page uses a Plenix utility class that is going away", () => {
  const sources = [...files("static/ctm"), ...files("tribunal/templates")];
  for (const file of sources) {
    const text = fs.readFileSync(file, "utf8");
    for (const name of GOING_AWAY) assert.ok(!new RegExp(`${name}(?![\w-])`).test(text), `${file} uses ${name}`);
  }
});

// #144 hotfix: a Plenix Image frame takes the file's natural size. A srcSet density (the first fix) failed on
// screens above 1x: the browser chose src as the 1x candidate and drew the logo at 1104 px over the page.
// Each logo is therefore a file whose own svg width/height is the size it is drawn at, and no srcSet.
test("each logo is a file sized to where it is drawn, never a srcSet density", () => {
  const sized = { "tribunal-logo-36.svg": ["36", "34"], "tribunal-logo-72.svg": ["72", "68"], "diocese-seal-100.svg": ["100", "100"] };
  for (const [name, [w, ht]] of Object.entries(sized))
    assert.match(fs.readFileSync(`static/ctm/${name}`, "utf8"), new RegExp(`<svg[^>]* width="${w}" height="${ht}"`), name);
  const app = fs.readFileSync("static/ctm/app.js", "utf8"), report = fs.readFileSync("static/ctm/external-report.js", "utf8");
  for (const text of [app, report]) {
    assert.doesNotMatch(text, /srcSet|drawnAt/);
    assert.doesNotMatch(text, /tribunal-logo-cropped\.svg|diocese-seal\.png/, "unsized files would draw at their natural size");
    assert.match(text, /src: "\/static\/ctm\/tribunal-logo-36\.svg"/);
  }
  assert.match(app, /src: "\/static\/ctm\/tribunal-logo-72\.svg"/);
  assert.match(app, /src: "\/static\/ctm\/diocese-seal-100\.svg"/);
});
