// #353 G3: the council photo architecture (storage, API contract, permissions) is written down and consistent with the
// G2 design: one owners block, an ADR, real JSON request/response examples, and a refusal code for every G2 error word.
// Architecture only: these checks keep the contract complete; the builder's pytest proves the code against it.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const DIR = "docs/implementation/slices/core-353-council-photos";
const DOC = `${DIR}/design.md`;
const CONTRACT = `${DIR}/contract`;
const ADR = "docs/adr/0002-council-photos.md";
const read = (file) => fs.readFileSync(file, "utf8");
const section = (doc, heading) => {
  const start = doc.indexOf(heading);
  assert.ok(start > -1, `section "${heading}"`);
  const next = doc.indexOf("\n## ", start + heading.length);
  return doc.slice(start, next === -1 ? undefined : next);
};
const contracts = () =>
  fs.readdirSync(CONTRACT).filter((f) => f.endsWith(".json")).map((f) => ({ name: f, ...JSON.parse(read(path.join(CONTRACT, f))) }));
const URL_RE = /^\/api\/council\/photos\/[0-9a-f-]{36}\/([1-9][0-9]*)\/$/;
const MAX = 2097152; // G1: 2 MB; G2: AvatarUpload maxSize

test("#353 G3: the design file has the G3 architecture with every part a builder needs", () => {
  const doc = read(DOC);
  const g3 = doc.slice(doc.indexOf("# G3 architecture"));
  assert.ok(doc.includes("# G3 architecture"), "a G3 architecture part");
  for (const heading of ["## G3.1 Approaches", "## G3.2 Data", "## G3.3 Service commands", "## G3.4 Authorization",
    "## G3.5 API contract", "## G3.6 Failure paths", "## G3.7 Owners", "## G3.8 Tasks", "## G3.9 Risks"]) {
    assert.ok(g3.includes(heading), heading);
  }
  assert.match(g3, /docs\/adr\/0002-council-photos\.md/);
});

test("#353 G3: the owners block keeps every lane to its own files (CLAUDE.md ownership rule)", () => {
  const doc = read(DOC);
  const m = doc.match(/```owners\s*\n([\s\S]*?)```/);
  assert.ok(m, "an owners block (scripts/check_ownership.cjs reads it)");
  const owners = {};
  for (const line of m[1].split(/\r?\n/)) {
    const mm = line.match(/^\s*([\w-]+)\s*:\s*(.+)$/);
    if (mm) owners[mm[1]] = mm[2].split(",").map((s) => s.trim());
  }
  for (const role of ["architect", "design", "database", "backend", "frontend", "i18n"]) assert.ok(owners[role], `role ${role}`);
  const dbOwned = (f) => /^tribunal\/(migrations|db)\//.test(f);
  for (const [role, files] of Object.entries(owners)) {
    if (role !== "database") for (const f of files) assert.ok(!dbOwned(f), `${role} must not own ${f}`);
  }
  assert.ok(owners.database.some((f) => /^tribunal\/migrations\/0080_council_photos\.(py|sql)$/.test(f)), "the migration");
  for (const f of owners.frontend) {
    assert.ok(!/^tribunal\/(services\/|policy\.py|migrations\/|db\/)/.test(f), `frontend must not own ${f}`);
  }
  for (const f of owners.backend) assert.ok(!f.startsWith("static/"), `backend must not own UI file ${f}`);
  // one owner per file
  const seen = new Map();
  for (const [role, files] of Object.entries(owners)) for (const f of files) {
    assert.ok(!seen.has(f), `${f} owned by both ${seen.get(f)} and ${role}`);
    seen.set(f, role);
  }
  assert.ok(owners.architect.includes(ADR), "the architect owns the ADR");
});

test("#353 G3: the ADR is written in the docs/adr format", () => {
  assert.ok(fs.existsSync(ADR), `${ADR} exists`);
  const adr = read(ADR);
  assert.match(adr, /^# 0002 /);
  assert.match(adr, /Status: (proposed|accepted)/);
  for (const part of ["Context:", "Decision:", "Consequences:", "Alternatives considered:", "Decision log:"]) {
    assert.ok(adr.includes(part), part);
  }
  assert.match(adr, /#353/);
});

test("#353 G3: every contract file is a real request and response pair", () => {
  const all = contracts();
  const names = all.map((c) => c.name).sort();
  for (const want of ["post-photo.json", "post-photo-conflict.json", "post-photo-refusals.json", "delete-photo.json",
    "get-photo.json", "get-photo-applicant.json", "get-seats.json"]) {
    assert.ok(names.includes(want), `contract/${want}`);
  }
  for (const c of all) {
    const pairs = c.cases || [c];
    for (const p of pairs) {
      assert.ok(p.request && p.request.method && p.request.path, `${c.name}: request method and path`);
      assert.ok(p.response && Number.isInteger(p.response.status), `${c.name}: response status`);
      assert.match(p.request.path, /^\/api\//, `${c.name}: an API path`);
      if (p.request.method !== "GET" && p.request.method !== "HEAD") {
        assert.ok(p.request.headers && p.request.headers["X-CSRFToken"], `${c.name}: a CSRF-protected write`);
      }
    }
  }
});

test("#353 G3: photo URLs are versioned, staff-only API paths and match photo_version", () => {
  const walk = (value, visit) => {
    if (Array.isArray(value)) value.forEach((v) => walk(v, visit));
    else if (value && typeof value === "object") { visit(value); Object.values(value).forEach((v) => walk(v, visit)); }
  };
  let count = 0;
  for (const c of contracts()) for (const p of c.cases || [c]) walk(p.response.body, (o) => {
    if (!("photo_url" in o)) return;
    if (o.photo_url === null) { assert.ok(o.photo_version === undefined || Number.isInteger(o.photo_version), c.name); return; }
    const m = o.photo_url.match(URL_RE);
    assert.ok(m, `${c.name}: ${o.photo_url} is /api/council/photos/<account>/<version>/`);
    if ("photo_version" in o) assert.equal(Number(m[1]), o.photo_version, `${c.name}: URL version is photo_version`);
    count += 1;
  });
  assert.ok(count >= 4, "examples carry photo URLs");
});

test("#353 G3: an applicant gets no council photo and no URL (AC-353-3)", () => {
  const applicant = contracts().filter((c) => (c.cases || [c]).some((p) => p.actor === "applicant"));
  assert.ok(applicant.length >= 1, "a contract shows the applicant case");
  for (const c of applicant) for (const p of c.cases || [c]) if (p.actor === "applicant") {
    assert.equal(p.response.status, 403, `${c.name}: applicant refused`);
    assert.doesNotMatch(JSON.stringify(p.response), /\/api\/council\/photos\/[0-9a-f]/, `${c.name}: no URL to an applicant`);
  }
  const g3 = read(DOC).slice(read(DOC).indexOf("# G3 architecture"));
  assert.match(g3, /AC-353-3/);
});

test("#353 G3: every refusal code maps to a G2 error word, and the size limit matches G2", () => {
  const doc = read(DOC);
  const words = new Set([...section(doc, "## Words").matchAll(/^\| `(photo[A-Za-z]+)` \|/gm)].map((m) => m[1]));
  const map = section(doc, "## G3.6 Failure paths");
  const rows = [...map.matchAll(/^\| (\d{3}) \| `([a-z_]+)` \| `(photo[A-Za-z]+)` \|/gm)];
  assert.ok(rows.length >= 6, "a status | code | word table");
  const codes = new Map(rows.map(([, status, code, word]) => [code, { status: Number(status), word }]));
  for (const [code, { word }] of codes) assert.ok(words.has(word), `${code} maps to G2 word ${word}`);
  for (const code of ["photo_too_large", "photo_wrong_content", "not_seated", "forbidden", "photo_conflict"]) {
    assert.ok(codes.has(code), `refusal code ${code}`);
  }
  for (const c of contracts()) for (const p of c.cases || [c]) {
    // writes only: the control maps these to its words; a display surface falls back on any failed load (G2)
    const write = p.request.method === "POST" || p.request.method === "DELETE";
    if (write && p.response.status >= 400 && p.response.body && p.response.body.error && p.actor !== "applicant") {
      const known = codes.get(p.response.body.error);
      assert.ok(known, `${c.name}: ${p.response.body.error} is in the failure table`);
      assert.equal(known.status, p.response.status, `${c.name}: ${p.response.body.error} status`);
    }
  }
  const conflict = JSON.parse(read(`${CONTRACT}/post-photo-conflict.json`));
  const body = conflict.response.body;
  assert.ok("photo_url" in body && Number.isInteger(body.photo_version) && body.changed_by && body.changed_by.name,
    "a conflict answer carries the current photo_url, its version and who changed it (G2)");
  assert.match(doc, new RegExp(`max_bytes[^\\n]*${MAX}`), "the server limit is the G2 maxSize");
  assert.match(doc, /maxSize=\{2097152\}/);
});
