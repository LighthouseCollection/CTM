// #370 (T5 of #312): the browser side of POST /api/lists/<name>/. The fixtures are the contract examples in
// docs/implementation/slices/ctm3-312-server-lists/contract/*.json, so the adapter is tested against the same
// shapes the backend asserts (L-04).
//
// Plenix pin check required by T5 (done against the pinned 1.8.0 source, the pin in ctm/settings.py, not 1.6.1):
//   DataGrid `fetchRows({page,size,sort,filters,search,signal})` — sort is [{field, dir}], filters is
//   [{field, type:"like", value}] (platform/components/DataGrid/engine/useRemoteRows.ts); this matches design section 8.
//   The grid's own `strings` already hold `loading` ("Loading records"), `failed` and `retry`
//   (platform/i18n/en.js, DataGrid chrome.tsx moreRow/emptyRow), so no CTM keys (listLoadingMore, listRetry,
//   listLoadFailed) are needed in this task.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const CONTRACT = "docs/implementation/slices/ctm3-312-server-lists/contract/";
const fixture = (name) => JSON.parse(fs.readFileSync(CONTRACT + name, "utf8"));

function load() {
  const window = {};
  vm.runInNewContext(fs.readFileSync("static/ctm/server-list.js", "utf8"), { window, Object, Promise, Map, Set, Array, JSON, Error, Math, Number });
  return window.CTMServerList;
}

// Same error shape as fetchApi in static/ctm/app.js: a failed response rejects with .status and .data (null when not JSON).
const failing = (status) => async () => { const e = new Error("request_failed"); e.status = status; e.data = null; throw e; };

test("server-list: query posts the body and passes signal", async () => {
  const { request, response } = fixture("post-list-cases.json");
  const calls = [];
  const api = async (url, options) => { calls.push({ url, options }); return response.body; };
  const controller = new AbortController();
  const result = await load().query(api, "cases", request.body, controller.signal);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, request.path);
  assert.equal(calls[0].options.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].options.body), request.body);
  assert.equal(calls[0].options.signal, controller.signal);
  assert.deepEqual(Array.from(result.items), Array.from(response.body.items));
  assert.equal(result.total, response.body.total);
  assert.equal(result.has_more, response.body.has_more);
  assert.equal(result.page, 1);
  assert.equal(result.size, 50);
});

test("server-list: facets come through and a null total is kept", async () => {
  const { response } = fixture("post-list-audit.json");
  const result = await load().query(async () => response.body, "audit", { page: 1, size: 50 });
  assert.equal(result.total, null);
  assert.deepEqual(Array.from(result.facets.action), ["decree_released", "session_closed"]);
});

test("server-list: non-JSON error rejects with status", async () => {
  // contract errors: 403 text/html from Django's CSRF middleware; fetchApi gives it .status 403 and data null.
  const error = fixture("post-list-cases.json").errors.find((e) => e.content_type === "text/html");
  assert.equal(error.status, 403);
  await assert.rejects(load().query(failing(403), "cases", { page: 1, size: 50 }), (e) => e.status === 403 && !e.data);
});

test("server-list: a reply that is not a list rejects instead of showing a blank grid", async () => {
  await assert.rejects(load().query(async () => "<html>", "cases", { page: 1, size: 50 }), (e) => e instanceof Error && e.status === 200);
  await assert.rejects(load().query(async () => ({ page: 1 }), "cases", { page: 1, size: 50 }), (e) => e.status === 200);
});

test("server-list: an unknown list name is refused before any request", async () => {
  let called = false;
  await assert.rejects(load().query(async () => { called = true; }, "../x", { page: 1, size: 50 }));
  assert.equal(called, false);
});

test("server-list: byIds chunks 250 ids into 3 requests of at most 100", async () => {
  const ids = Array.from({ length: 250 }, (_, i) => "id-" + i);
  const calls = [];
  const api = async (url, options) => {
    const body = JSON.parse(options.body);
    calls.push(body);
    return { items: body.filters.ids.map((id) => ({ id })), page: 1, size: 100, total: body.filters.ids.length, has_more: false };
  };
  const found = await load().byIds(api, "sessions", ids);
  assert.equal(calls.length, 3);
  assert.deepEqual(calls.map((c) => c.filters.ids.length), [100, 100, 50]);
  assert.ok(calls.every((c) => c.size === 100 && c.page === 1));
  assert.ok(found instanceof Map);
  assert.equal(found.size, 250);
  assert.equal(found.get("id-249").id, "id-249");
});

test("server-list: byIds leaves out ids the server does not return and makes no request for none", async () => {
  const { response } = fixture("post-list-sessions.json");
  const id = response.body.items[0].id;
  const api = async () => ({ items: [response.body.items[0]], page: 1, size: 100, total: 1, has_more: false });
  const found = await load().byIds(api, "sessions", [id, "not-readable", id]);
  assert.deepEqual(Array.from(found.keys()), [id]);
  let called = false;
  const empty = await load().byIds(async () => { called = true; }, "sessions", []);
  assert.equal(empty.size, 0);
  assert.equal(called, false);
});
