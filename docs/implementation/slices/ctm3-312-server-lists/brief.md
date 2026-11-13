# ctm3-312 — lists load one page at a time from the server (brief)

Issue: LighthouseCollection/CTM#312, part of #311 (owner performance standard, rule 5, chat 2026-11-10).
Brief derived from the issue by ctm3-solution-architect because no brief existed; ctm3-product-lead may amend it.

**What:** every list (cases, applications, sessions, users, audit, messages) asks the server for one page
(25 to 50 rows) and sends search, sort and filters to the server. Plenix `DataGrid` supports
`fetchRows({ page, size, sort, filters, search })` with `mode: "fill"` or `"pages"`.

**Why:** lists download every row and sort in the browser, so they slow down as the data grows. Today the
server also cuts most lists at 100 or 250 rows without saying so.

| ID | Done when |
|---|---|
| AC-1 | `design.md`, `contract/*.json` and ADR 0001 describe one list query contract (request, response, errors) |
| AC-2 | Council case lists (all, mine, archived, Home My cases) load pages from the server with server search, sort and filters |
| AC-3 | The New applications queues (awaiting review, for council) load pages from the server |
| AC-4 | Session lists (current, upcoming, archived) load pages from the server; "today" is the Los Angeles civil date on the server |
| AC-5 | Users and roles (council members, accounts) load pages from the server with search, role and active filters |
| AC-6 | System audit and case audit load pages from the server with action, source, date and text filters |
| AC-7 | Messages and notifications keep their existing server pages of 50 (already compliant), proven by a test |
| AC-8 | Counts never leak: `total` counts only rows the actor may read; search and sort run only on fields the actor may read; unknown keys are refused |
| AC-9 | No screen downloads a whole list to find one row: lookups use the `ids` or `case` filters |
| AC-10 | Before/after server time and response size for the largest list (cases, 2,000 fictional cases) are recorded in `evidence.md` |

Spec acceptance IDs covered: SEC01, SEC02, SEC03, UI01.
