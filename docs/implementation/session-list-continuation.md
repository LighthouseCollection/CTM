# Tribunal Sessions list continuation

GET /api/sessions/ retains the existing items and their id/date/reference/state and
server capabilities. All active council roles may read; applicants still receive403
and anonymous callers401 without rows or continuation/count metadata. POST creation,
agenda/attendance/hearing/reschedule/close services are unchanged.

The response adds offset, limit and next_offset. Default limit100 preserves the
previous first-page size; maximum250, positive integer, offset nonnegative. Query
validation uses the shared bounded pagination parser; duplicates/invalid bounds
return422. next_offset is null at the end. Follow continuation while preserving
filters; do not assume the first100 rows are the full session directory.

Optional filters, all applied before pagination:
- state: exactly planned or closed; one nonempty value.
- date_from and date_to: one exact YYYY-MM-DD calendar date each, inclusive.
- A reversed range, empty/duplicate filter, invalid date/state returns422.

Ordering is descending session date then UUID. Existing unique-per-date behavior
remains. Offset pages can shift when sessions are created or rescheduled; refresh
from offset0 after lifecycle actions. Capability flags still derive from real state
and actor. No state transition, date default, content or count is invented.

This supports the UI's current/upcoming/archive query binding without defining a
new lifecycle approval or timezone rule. UI/product owns lifecycle naming/acceptance
and should pass its selected calendar bounds. The approved council_sessions schema
currently defines date/reference/state/creator/closed_at, not time, location,
presiding member or minutes. Those requested fields require a separate approved
contract/schema decision and are not implied by this pagination implementation.
Do not substitute testimony appointment timing/location for whole-session fields.

Sixteen actualctm_app SQL-session tests cover recovery of105 rows, four council
roles, inclusive state/date filtering before continuation, capability preservation,
invalid/duplicate inputs, cache headers and denied applicant/anonymous access.
Full PostgreSQL706 passed,1 skipped. No new model, route, grant, policy or migration;
current adapter remains63domain models/97routes/63forced tables through0041.

Governance reviews/serially integrates exact pushed SHA; UI binds continuation and
filters, and QA independently records the combined successor SHA. This backend
stream performs no shared-server operation, merge or deployment.
