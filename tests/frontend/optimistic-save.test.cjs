// Issue 313 (performance rule 6): the shared optimistic-save helper (static/ctm/optimistic.js).
// Safe edits show the new value at once and are put back, with a message, if the server refuses.
// Votes, decisions, decrees, payments and anything legal stay confirm-first: shown only after the server agrees.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function load() {
  const window = {};
  vm.runInNewContext(fs.readFileSync("static/ctm/optimistic.js", "utf8"), { window, Promise, RegExp, Object, Error });
  return window.CTMOptimistic;
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
const ATTENDANCE = "/api/sessions/s-1/attendance/";

// A save the test settles by hand, so it can look at the screen while the server has not answered.
function held() {
  let settle;
  const promise = new Promise((resolve, reject) => (settle = { resolve, reject }));
  return { promise, ...settle };
}

test("a safe edit is shown before the server answers and stays when the server accepts", async () => {
  const O = load();
  const log = [];
  const server = held();
  const done = O.run({ path: ATTENDANCE, save: () => (log.push("save"), server.promise), apply: () => log.push("apply"), revert: () => log.push("revert") });
  await tick();
  assert.deepEqual(log, ["apply", "save"], "shown first, then sent");
  server.resolve({ id: 1 });
  const outcome = await done;
  assert.deepEqual(log, ["apply", "save"], "nothing is undone");
  assert.equal(outcome.ok, true);
  assert.deepEqual(outcome.result, { id: 1 });
  assert.equal(outcome.shownEarly, true);
});

test("a refused save puts the old value back and reports the failure without throwing", async () => {
  const O = load();
  const log = [];
  const error = Object.assign(new Error("request_failed"), { status: 403 });
  const outcome = await O.run({ path: ATTENDANCE, save: () => Promise.reject(error), apply: () => log.push("apply"), revert: () => log.push("revert") });
  assert.deepEqual(log, ["apply", "revert"]);
  assert.equal(outcome.ok, false);
  assert.equal(outcome.error, error);
  assert.equal(outcome.shownEarly, true);
});

test("a save that throws before returning a promise is also undone", async () => {
  const O = load();
  const log = [];
  const outcome = await O.run({ path: ATTENDANCE, save: () => { throw new Error("offline"); }, apply: () => log.push("apply"), revert: () => log.push("revert") });
  assert.deepEqual(log, ["apply", "revert"]);
  assert.equal(outcome.ok, false);
});

test("votes, decisions, decrees, payments and legal steps are confirm-first: nothing is shown until the server agrees", async () => {
  const O = load();
  const paths = [
    "/api/decisions/d-1/vote/",
    "/api/decisions/d-1/",
    "/api/decrees/x-1/issue/",
    "/api/decrees/x-1/sign/",
    "/api/cases/c-1/decrees/",
    "/api/payments/p-1/",
    "/api/cases/c-1/payments/",
    "/api/applications/a-1/submit/",
    "/api/applications/a-1/withdraw/",
    "/api/requests/r-1/send/",
    "/api/hearings/h-1/outcome/",
    "/api/proceedings/p-1/findings/",
  ];
  for (const path of paths) {
    assert.equal(O.mode(path), "confirm", path);
    const log = [];
    const server = held();
    const done = O.run({ path, save: () => server.promise, apply: () => log.push("apply"), revert: () => log.push("revert") });
    await tick();
    assert.deepEqual(log, [], `${path}: nothing shown while the server has not answered`);
    server.resolve({});
    const outcome = await done;
    assert.deepEqual(log, ["apply"], `${path}: shown after the server agreed`);
    assert.equal(outcome.shownEarly, false);
  }
});

test("a refused confirm-first save shows nothing and has nothing to undo", async () => {
  const O = load();
  const log = [];
  const outcome = await O.run({ path: "/api/decisions/d-1/vote/", save: () => Promise.reject(new Error("no")), apply: () => log.push("apply"), revert: () => log.push("revert") });
  assert.deepEqual(log, []);
  assert.equal(outcome.ok, false);
  assert.equal(outcome.shownEarly, false);
});

test("deny by default: a path that is not on the safe list, or has no path, is confirm-first", () => {
  const O = load();
  for (const path of ["/api/cases/c-1/assignment/", "/api/files/", "/api/something-new/", "", undefined, null, 42]) assert.equal(O.mode(path), "confirm", String(path));
  for (const path of [ATTENDANCE, "/api/sessions/abc%2D1/attendance/"]) assert.equal(O.mode(path), "optimistic", path);
});

test("the confirm-first list wins over the safe list", () => {
  const O = load();
  assert.equal(O.mode("/api/decisions/d-1/attendance/"), "confirm");
  assert.equal(O.mode("/api/payments/sessions/s-1/attendance/"), "confirm");
  assert.equal(O.mode("/api/sessions/s-1/attendance/?x=/vote/"), "confirm");
});
