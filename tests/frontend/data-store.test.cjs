// Issue 308, step 2 (owner approval 2026-11-10): the tab's memory store for server reads (static/ctm/data.js).
// Kept reads come back at once, a page's first reads are drawn from memory and refreshed quietly, saves and
// sign-out clear everything, and only allow-listed reads are ever kept or loaded ahead.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("static/ctm/data.js", "utf8");
const tick = () => new Promise((resolve) => setImmediate(resolve));

// Loads data.js with a fake clock, a fake tab and a fake server. server.reply(url) answers; held replies wait for
// release() so a test can see what is on its way.
function load({ hold = false } = {}) {
  let clock = 1_000_000;
  class FakeDate extends Date {
    static now() { return clock; }
  }
  const idle = [];
  const listeners = {};
  const document = { visibilityState: "visible", addEventListener: (name, fn) => { listeners[name] = fn; } };
  const timers = [];
  const window = { requestIdleCallback: (fn) => idle.push(fn) };
  const navigator = { connection: { saveData: false } };
  const asked = [];
  const held = [];
  const server = { replies: {}, status: {} };
  const raw = (url, options = {}) => {
    asked.push({ url, method: options.method || "GET" });
    const answer = () => {
      const status = server.status[url];
      if (status) {
        const error = new Error("request_failed");
        error.status = status;
        return Promise.reject(error);
      }
      return Promise.resolve(JSON.parse(JSON.stringify(server.replies[url] ?? { url })));
    };
    if (!hold) return answer();
    return new Promise((resolve, reject) => held.push(() => answer().then(resolve, reject)));
  };
  vm.runInNewContext(source, { window, document, navigator, Date: FakeDate, Promise, JSON, Map, Set, Object, String, setTimeout: (fn) => timers.push(fn) }, { filename: "data.js" });
  const store = window.CTMData;
  return {
    store, raw, asked, server, document, navigator,
    api: store.wrap(raw),
    gets: () => asked.filter((a) => a.method === "GET").map((a) => a.url),
    advance: (ms) => { clock += ms; },
    release: () => held.splice(0).forEach((go) => go()),
    held: () => held.length,
    input: (name = "keydown") => listeners[name]?.(),
    timers: () => timers.splice(0).forEach((fn) => fn()),
    runIdle: () => idle.splice(0).forEach((fn) => fn()),
    show: (state) => { document.visibilityState = state; listeners.visibilitychange?.(); },
  };
}

test("only allow-listed reads are kept; the never-kept list always goes to the server", () => {
  const { store } = load();
  for (const url of ["/api/cases/", "/api/cases/?mine=1", "/api/cases/c-1/", "/api/cases/c-1/requests/", "/api/cases/c-1/parties/",
    "/api/applications/", "/api/dashboard/", "/api/dashboard/members/", "/api/statistics/summary/", "/api/sessions/",
    "/api/sessions/s-1/agenda/", "/api/sessions/s-1/attendance/", "/api/sessions/s-1/answers/", "/api/council/members/"])
    assert.equal(store.keepable(url), true, url);
  for (const url of ["/api/session/", "/api/files/", "/api/files/f-1/status/", "/api/cases/c-1/files/?history=1",
    "/api/cases/c-1/audit/", "/api/cases/c-1/timeline/", "/api/cases/c-1/messages/", "/api/notifications/",
    "/api/proceedings/p-1/decision/", "/api/proceedings/p-1/findings/", "/api/decisions/d-1/vote/", "/api/decrees/d-1/release/",
    "/api/applications/a-1/", "/api/applications/a-1/payments/", "/api/reports/r-1/revisions/", "/api/transcripts/t-1/",
    "/api/cases/c-1/reports/", "/api/sessions/s-1/attendance/?hearing_id=h-1", "/api/search/?q=x"])
    assert.equal(store.keepable(url), false, url);
});

test("nothing is kept before the account is known", async () => {
  const { api, gets } = load();
  await api("/api/dashboard/");
  await api("/api/dashboard/");
  assert.deepEqual(gets(), ["/api/dashboard/", "/api/dashboard/"]);
});

test("a repeat read within 10 s comes from memory, as a copy the page cannot change", async () => {
  const { store, api, gets, advance, server } = load();
  store.setAccount("u-1");
  server.replies["/api/cases/"] = { items: [{ id: "c-1" }] };
  const first = await api("/api/cases/");
  first.items.push({ id: "changed-by-page" });
  advance(9_000);
  const second = await api("/api/cases/");
  assert.deepEqual(second, { items: [{ id: "c-1" }] });
  assert.deepEqual(gets(), ["/api/cases/"]);
  advance(2_000); // 11 s: outside a page's first reads it asks the server again
  await api("/api/cases/");
  assert.deepEqual(gets(), ["/api/cases/", "/api/cases/"]);
});

test("two reads of the same address at the same time share one request", async () => {
  const h = load({ hold: true });
  h.store.setAccount("u-1");
  const a = h.api("/api/statistics/summary/");
  const b = h.api("/api/statistics/summary/");
  assert.equal(h.held(), 1);
  h.release();
  assert.deepEqual(await a, await b);
  assert.deepEqual(h.gets(), ["/api/statistics/summary/"]);
});

test("reads off the allow-list, and reads with options, always go to the server", async () => {
  const { store, api, gets } = load();
  store.setAccount("u-1");
  await api("/api/cases/c-1/audit/");
  await api("/api/cases/c-1/audit/");
  await api("/api/session/");
  await api("/api/session/");
  assert.deepEqual(gets(), ["/api/cases/c-1/audit/", "/api/cases/c-1/audit/", "/api/session/", "/api/session/"]);
});

test("any save clears everything kept, and a read that started before it never fills the store", async () => {
  const h = load({ hold: true });
  h.store.setAccount("u-1");
  const before = h.api("/api/cases/c-1/");
  h.release();
  await before;
  assert.equal(h.store.size(), 1);
  const early = h.api("/api/council/members/"); // on its way while the save happens
  const save = h.api("/api/cases/c-1/assignment/", { method: "POST", body: "{}" });
  assert.equal(h.store.size(), 0);
  h.release();
  await Promise.all([early, save]);
  assert.equal(h.store.size(), 0, "the read that started before the save is not kept");
  const after = h.api("/api/cases/c-1/");
  h.release();
  await after;
  assert.deepEqual(h.gets(), ["/api/cases/c-1/", "/api/council/members/", "/api/cases/c-1/"]);
  for (const method of ["PUT", "PATCH", "DELETE"]) {
    await (async () => { const r = h.api("/api/cases/c-1/", {}); h.release(); await r; })();
    assert.equal(h.store.size(), 1);
    const s = h.api("/api/cases/c-1/", { method });
    h.release();
    await s;
    assert.equal(h.store.size(), 0, method);
  }
});

test("a list query (POST /api/lists/<name>/) is a read: it leaves kept entries intact and is never kept itself (#370)", async () => {
  const h = load();
  h.store.setAccount("u-1");
  h.server.replies["/api/lists/cases/"] = { rows: [1] };
  await h.api("/api/cases/c-1/");
  assert.equal(h.store.size(), 1);
  const first = await h.api("/api/lists/cases/", { method: "POST", body: "{}" });
  assert.deepEqual(first, { rows: [1] });
  assert.equal(h.store.size(), 1, "the kept entry survives the list query");
  h.server.replies["/api/lists/cases/"] = { rows: [2] };
  const second = await h.api("/api/lists/cases/", { method: "POST", body: "{}" });
  assert.deepEqual(second, { rows: [2] }, "a second query asks the server again");
  assert.equal(h.store.size(), 1);
  await h.api("/api/cases/c-1/"); // still answered from memory
  assert.deepEqual(h.asked.filter((a) => a.url === "/api/cases/c-1/").length, 1);
  // Any other POST is still a save.
  await h.api("/api/cases/c-1/assignment/", { method: "POST", body: "{}" });
  assert.equal(h.store.size(), 0);
});

test("a 401 or a different account clears everything", async () => {
  const { store, api, server } = load();
  store.setAccount("u-1");
  await api("/api/dashboard/");
  await api("/api/sessions/");
  assert.equal(store.size(), 2);
  store.setAccount("u-1");
  assert.equal(store.size(), 2, "the same account keeps its data");
  store.setAccount("u-2");
  assert.equal(store.size(), 0);
  await api("/api/dashboard/");
  server.status["/api/notifications/"] = 401;
  await assert.rejects(api("/api/notifications/"), (error) => error.status === 401);
  assert.equal(store.size(), 0);
  await api("/api/dashboard/");
  store.setAccount(null);
  assert.equal(store.size(), 0);
});

test("a page's first reads are drawn from memory at once and refreshed quietly; the page redraws only on a change", async () => {
  const h = load();
  h.store.setAccount("u-1");
  h.server.replies["/api/sessions/"] = { items: [1] };
  await h.api("/api/sessions/");
  h.advance(60_000);
  let changes = 0;
  const reader = h.store.reader(() => { changes += 1; });
  reader.open();
  const shown = await reader.run(() => h.api("/api/sessions/"));
  assert.deepEqual(shown, { items: [1] }, "drawn from memory at once");
  await tick();
  assert.deepEqual(h.gets(), ["/api/sessions/", "/api/sessions/"], "and asked again in the background");
  assert.equal(changes, 0, "the same answer does not redraw");
  h.advance(60_000);
  h.server.replies["/api/sessions/"] = { items: [1, 2] };
  await reader.run(() => h.api("/api/sessions/"));
  await tick();
  assert.equal(changes, 1, "a changed answer redraws the page");
  assert.deepEqual(await reader.run(() => h.api("/api/sessions/")), { items: [1, 2] });
  reader.close();
});

test("a later read of an older copy (not a page's first read) waits for the server; older than 5 minutes is gone", async () => {
  const h = load();
  h.store.setAccount("u-1");
  await h.api("/api/council/members/");
  h.advance(30_000);
  await h.api("/api/council/members/");
  assert.equal(h.gets().length, 2);
  h.advance(5 * 60_000 + 1);
  const reader = h.store.reader(() => {});
  reader.open();
  await reader.run(() => h.api("/api/council/members/"));
  assert.equal(h.gets().length, 3, "an expired copy is never drawn");
});

test("a refused quiet refresh forgets the copy and makes the page ask again", async () => {
  const h = load();
  h.store.setAccount("u-1");
  await h.api("/api/cases/c-1/");
  h.advance(20_000);
  let changes = 0;
  const reader = h.store.reader(() => { changes += 1; });
  reader.open();
  h.server.status["/api/cases/c-1/"] = 403; // access was withdrawn since the copy was kept
  await reader.run(() => h.api("/api/cases/c-1/"));
  await tick();
  await tick();
  assert.equal(changes, 1);
  assert.equal(h.store.size(), 0);
  await assert.rejects(reader.run(() => h.api("/api/cases/c-1/")), (error) => error.status === 403);
});

test("loading ahead: allow-listed only, at most 2 at a time, never while the user waits, never hidden or on data saver", async () => {
  const h = load({ hold: true });
  h.store.setAccount("u-1");
  const user = h.api("/api/dashboard/");
  h.store.prefetch(["/api/cases/", "/api/sessions/s-1/agenda/", "/api/council/members/", "/api/cases/c-1/audit/", "/api/files/", null]);
  h.advance(3000);
  h.runIdle();
  assert.deepEqual(h.gets(), ["/api/dashboard/"], "nothing loads ahead while a user read is on its way");
  h.release();
  await user;
  await tick();
  assert.deepEqual(h.gets(), ["/api/dashboard/", "/api/cases/", "/api/sessions/s-1/agenda/"], "two at a time");
  // A user read of an address already loading ahead joins it instead of asking twice.
  const joined = h.api("/api/cases/");
  h.release();
  await joined;
  await tick();
  h.release();
  await tick();
  assert.deepEqual(h.gets(), ["/api/dashboard/", "/api/cases/", "/api/sessions/s-1/agenda/", "/api/council/members/"]);
  assert.ok(!h.gets().some((url) => url.includes("audit") || url.includes("files")));
  // Already kept: not loaded again.
  h.store.prefetch(["/api/cases/"]);
  h.advance(3000);
  h.runIdle();
  await tick();
  assert.equal(h.gets().length, 4);
  // Hidden tab: waits until the tab shows again.
  h.advance(11_000);
  h.show("hidden");
  h.store.prefetch(["/api/sessions/"]);
  h.advance(3000);
  h.runIdle();
  await tick();
  assert.equal(h.gets().length, 4);
  h.show("visible");
  await tick();
  assert.equal(h.gets().at(-1), "/api/sessions/");
  h.release();
  await tick();
  // A connection that asks to save data loads nothing ahead.
  h.navigator.connection.saveData = true;
  h.store.prefetch(["/api/applications/"]);
  h.advance(3000);
  h.runIdle();
  await tick();
  assert.ok(!h.gets().includes("/api/applications/"));
});

test("loading ahead waits for 2 seconds without input and starts again after the next input", async () => {
  const h = load();
  h.store.setAccount("u-1");
  h.input();
  h.store.prefetch(["/api/sessions/s-1/agenda/"]);
  h.advance(1000);
  h.runIdle();
  await tick();
  assert.deepEqual(h.gets(), [], "input 1 second ago: nothing yet");
  h.advance(1500);
  h.timers();
  h.runIdle();
  await tick();
  assert.deepEqual(h.gets(), ["/api/sessions/s-1/agenda/"]);
  // Input after the job was queued but before it ran: the job waits again.
  h.store.prefetch(["/api/council/members/"]);
  h.advance(3000);
  h.runIdle();
  h.input("pointerdown");
  await tick();
  h.input("scroll");
  h.store.prefetch(["/api/sessions/"]);
  h.runIdle();
  await tick();
  assert.equal(h.gets().includes("/api/sessions/"), false);
  h.advance(2500);
  h.timers();
  h.runIdle();
  await tick();
  assert.ok(h.gets().includes("/api/sessions/"));
});

test("no loading ahead on a 2G or slower connection", async () => {
  for (const type of ["slow-2g", "2g"]) {
    const h = load();
    h.store.setAccount("u-1");
    h.navigator.connection.effectiveType = type;
    h.store.prefetch(["/api/sessions/"]);
    h.advance(3000);
    h.runIdle();
    h.timers();
    await tick();
    assert.deepEqual(h.gets(), [], type);
  }
  const ok = load();
  ok.store.setAccount("u-1");
  ok.navigator.connection.effectiveType = "4g";
  ok.store.prefetch(["/api/sessions/"]);
  ok.advance(3000);
  ok.runIdle();
  await tick();
  assert.deepEqual(ok.gets(), ["/api/sessions/"]);
});

test("a sign-in or sign-out in another tab empties the store before the next read", async () => {
  const h = load();
  let cookie = "token-a";
  h.store.watch(() => cookie);
  h.store.setAccount("u-1");
  h.server.replies["/api/cases/"] = { items: ["a"] };
  await h.api("/api/cases/");
  assert.equal(h.store.size(), 1);
  cookie = "token-b"; // another tab signed in as someone else
  h.server.replies["/api/cases/"] = { items: ["b"] };
  const seen = await h.api("/api/cases/");
  assert.deepEqual(seen, { items: ["b"] }, "drawn from the server, not from the other account's copy");
  assert.deepEqual(h.gets(), ["/api/cases/", "/api/cases/"]);
  // The same holds for a page's first reads (no quiet refresh of the old copy) and for loading ahead.
  cookie = "token-c";
  await h.store.reader(() => {}).run(() => h.api("/api/cases/"));
  assert.equal(h.gets().length, 3);
  cookie = "token-d";
  h.store.prefetch(["/api/sessions/"]);
  assert.equal(h.store.size(), 0);
});

test("back on the tab after a while, the open pages' first reads are asked again", async () => {
  const h = load();
  h.store.setAccount("u-1");
  h.server.replies["/api/dashboard/"] = { n: 1 };
  let changes = 0;
  const reader = h.store.reader(() => { changes += 1; });
  reader.open();
  await reader.run(() => h.api("/api/dashboard/"));
  h.show("hidden");
  h.advance(30_000);
  h.server.replies["/api/dashboard/"] = { n: 2 };
  h.show("visible");
  await tick();
  await tick();
  assert.equal(h.gets().length, 2);
  assert.equal(changes, 1);
  reader.reset();
  h.show("hidden");
  h.advance(30_000);
  h.show("visible");
  await tick();
  assert.equal(h.gets().length, 2, "a page drawn without kept data is not refreshed");
});

test("memory only: no browser storage, and api() keeps cache: no-store", () => {
  assert.doesNotMatch(source, /localStorage|sessionStorage|indexedDB|caches\.|serviceWorker|document\.cookie/);
  const app = fs.readFileSync("static/ctm/app.js", "utf8");
  assert.match(app, /cache: "no-store"/);
  assert.match(app, /const api = window\.CTMData \? window\.CTMData\.wrap\(fetchApi\) : fetchApi;/);
  assert.match(app, /window\.CTMData\?\.setAccount\(value\?\.id\)/);
  assert.match(app, /window\.CTMData\?\.setAccount\(null\)/);
});

test("the shell loads data.js before the modules that use it", () => {
  const shell = fs.readFileSync("tribunal/templates/tribunal/shell.html", "utf8");
  const at = (file) => shell.indexOf(`'ctm/${file}'`);
  assert.ok(at("data.js") > -1);
  for (const file of ["council.js", "ui-workspaces.js", "app.js"]) assert.ok(at("data.js") < at(file), file);
});

test("a council page loader is tracked, refreshed quietly, and never redrawn under unsaved edits", () => {
  const council = fs.readFileSync("static/ctm/council.js", "utf8");
  const start = council.indexOf("function useLoad(");
  const body = council.slice(start, council.indexOf("function plural(", start));
  assert.match(body, /window\.CTMData\.reader\(/);
  assert.match(body, /if \(unsavedDrafts\.size\) return;/);
  assert.match(body, /reader\.current \? reader\.current\.run\(loader\) : loader\(\)/);
  assert.match(body, /if \(!quiet\) setState/);
});
