# 0001 Server list queries: one POST endpoint per list, page/size/sort/q/filters
2026-11-10 · Status: proposed

Context:
- Owner performance rule 5 (#311, #312) requires every list to load one page from the server, with search and sort on the server.
- Today the list endpoints (`GET /api/cases/`, `/api/applications/`, `/api/sessions/`, `/api/system/members/`, `/api/system/accounts/`, `/api/system/audit/`, `/api/cases/<id>/audit/`) return the first 100 or 250 rows. Screens sort, filter and search those rows in the browser, so every row after the cap is silently missing.
- `build-spec/permissions.md`: permissions apply to derivatives, search, counts and links. `transactions-and-acceptance.md` SEC01 names counts and search snippets; SEC02 excludes drafts.
- CTM already sends search phrases in a POST body so names never reach URLs or access logs (`runSearch` in `static/ctm/council.js`, `POST /api/search/`).
- Plenix `DataGrid` (pinned 1.6.1) asks `fetchRows({ page, size, sort, filters, search })` and expects `{ rows, total }`.

Decision:
- Add one read endpoint, `POST /api/lists/<name>/`, in a new module `tribunal/list_api.py`. The list rules live in a registry in a new module `tribunal/lists.py`. `tribunal/api.py` does not grow.
- Body: `{ page, size, sort: [{ field, dir }], q, filters: {…}, facets }`. Response: `{ items, page, size, total, has_more }`.
- Each list declares, per role, the sort keys, filter keys and search fields it accepts. Anything else is refused with 422. Nothing is ignored silently.
- `total` is a SQL `COUNT` of the same authorized and filtered queryset that produces the page. Lists whose visibility is decided in Python (audit) return `total: null` and `has_more` from a look-ahead row.
- The existing GET list endpoints stay unchanged for callers that still use them. They are removed in a later slice once nothing calls them.

Consequences:
- Easier: one contract and one adapter for every grid; permission rules for counts and search live in one place and are tested once per list.
- Harder: reads through POST are not HTTP-cacheable. The in-memory cache of #308 must key on path and body.
- Offset pages can drift when rows are added between pages. The frontend adapter drops rows whose id it has already shown.
- Migration: index-only migration (`0078_list_indexes`). Rollback: revert the frontend first, then the route. The GET endpoints keep working throughout.

Alternatives considered:
- Query parameters on the existing GET endpoints: cacheable and smaller, but search text (names) would land in URLs and access logs. That breaks the rule `runSearch` already follows. Rejected.
- Keyset (cursor) pagination: stable under inserts, but Plenix "pages" mode jumps to page N and shows a total. Lists hold thousands of rows, not millions. Rejected for now. A cursor can be added later as a body option.
- A query library or new dependency (django-filter, GraphQL): new dependency and a second permission layer. Rejected.

Decision log: none (technical choice; the owner rule is recorded under #311).
