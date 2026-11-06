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

test("the logos get their drawn width from Image srcSet density, not a size class", () => {
  for (const file of ["static/ctm/app.js", "static/ctm/external-report.js"]) {
    const text = fs.readFileSync(file, "utf8");
    assert.match(text, /const drawnAt = \(src, naturalWidth, width\) =>/);
    assert.doesNotMatch(text, /tribunal-logo-cropped\.svg"[^}]*fit: "contain"/);
  }
  const drawnAt = (src, naturalWidth, width) => `${src} ${+(naturalWidth / width).toFixed(4)}x`;
  assert.equal(drawnAt("/l.svg", 1104, 36), "/l.svg 30.6667x");
  assert.equal(drawnAt("/s.png", 456, 100), "/s.png 4.56x");
  // The SVG needs a natural size for the density to apply.
  assert.match(fs.readFileSync("static/ctm/tribunal-logo-cropped.svg", "utf8"), /<svg[^>]* width="1104" height="1050"/);
});
