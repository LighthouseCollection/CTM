/* CTMServerList: the browser side of POST /api/lists/<name>/ (issue 312, task T5, issue 370).
 *
 * query(api, list, body, signal) -> Promise<{items, page, size, total, has_more, facets?}>
 *   body is {page, size, sort, q, filters, facets}; total is null for lists the server filters row by row (audit).
 *   A failed request rejects with the error `api` gave, which carries .status; the body of a non-JSON failure (the
 *   CSRF 403 page) is never read.
 * byIds(api, list, ids) -> Promise<Map<id, row>>
 *   Looks rows up by id in chunks of 100; ids the person may not read are not in the map.
 *
 * `api` is the page's api function (static/ctm/app.js): api(url, options) -> parsed JSON.
 */
(() => {
  "use strict";
  const CHUNK = 100;
  const NAME = /^[a-z][a-z-]*$/;

  const fail = (message, status) => Object.assign(new Error(message), { status, data: null });

  async function query(api, list, body, signal) {
    if (typeof list !== "string" || !NAME.test(list)) throw fail("unknown_list", 0);
    const data = await api(`/api/lists/${list}/`, { method: "POST", body: JSON.stringify(body || {}), ...(signal ? { signal } : {}) });
    if (!data || typeof data !== "object" || !Array.isArray(data.items)) throw fail("invalid_list_response", 200);
    return {
      items: data.items, page: data.page, size: data.size,
      total: data.total ?? null, has_more: data.has_more === true,
      ...(data.facets ? { facets: data.facets } : {}),
    };
  }

  async function byIds(api, list, ids) {
    const unique = [...new Set(ids || [])];
    const chunks = [];
    for (let i = 0; i < unique.length; i += CHUNK) chunks.push(unique.slice(i, i + CHUNK));
    const found = new Map();
    const pages = await Promise.all(chunks.map((chunk) => query(api, list, { page: 1, size: CHUNK, filters: { ids: chunk } })));
    for (const page of pages) for (const row of page.items) found.set(row.id, row);
    return found;
  }

  window.CTMServerList = Object.freeze({ query, byIds });
})();
