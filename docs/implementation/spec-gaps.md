# Spec gaps register

Gaps between the approved build-spec (151 planned tables, acceptance IDs,
F01-F36 review findings) and the implementation, as rows instead of prose.
Counts are computed at a named commit, never copied from older documents.
Detailed table mapping stays in `docs/implementation/schema-reconciliation/`.

| Id | Spec reference | Current state (commit) | Owner stream | Status | Notes |
|---|---|---|---|---|---|
| GAP-001 | `build-spec/schema.json` (151 tables) | PR20 reconciliation at `db82099`: 3 implemented, 110 partial, 37 missing, 1 decision needed | backend/database | Open | Recompute with `schema-reconciliation/reconcile.py` before relying on these numbers |
| GAP-002 | `CTM-Independent-Acceptance-Review.md` (kept in git history) F01-F36 | 9 P0 findings (F01, F06, F11, F13, F14, F24, F26, F28, F29) not yet tracked as test IDs | all | Open | Map each to a test or slice |
