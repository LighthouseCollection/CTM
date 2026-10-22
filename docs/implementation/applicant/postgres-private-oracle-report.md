# Private-resource denial reconciliation and renewed Docker stall

Candidate `a2844f73fc9a28906cef51b63149f0a40c95e68c` was exercised with physical `current_user=session_user=ctm_app`, `NOSUPERUSER`, `NOBYPASSRLS`, `NOINHERIT`, 63 forced-RLS domain tables and zero owner memberships.

The prior broader-suite failure was reproduced before changing assertions. Foreign draft detail expected `403` but received `404`. Source tracing shows detail, history, files and payments all resolve through the same RLS-filtered application lookup. The acceptance contract was narrowed to require each foreign response to match the same endpoint for a nonexistent application exactly: status `404` and equal JSON body. All four endpoint comparisons passed. A later foreign original range assertion then failed with the same stale `403` expectation; its foreign response and a nonexistent file response both passed exact `404`/body equality after the minimal assertion change. Explicit denials for visible unsafe, superseded or unreleased resources remain unchanged.

Independent review found that the foreign-file assertion also needed to preserve the default SQLite `403` contract, and identified two later foreign application-detail checks requiring the same PostgreSQL concealment branch. Both findings were fixed. A fresh default SQLite run against backend `48b80c4` passes all 75 API/browser groups with no page errors, confirming those explicit-denial expectations remain intact outside the restricted-RLS mode.

The first run completed 11 outer groups before the foreign-file assertion; its container was removed. [Interrupted evidence](postgres-private-oracle-interrupted.json) and [cleanup evidence](postgres-private-oracle-cleanup.json) remain separate from the successor attempt.

The successor attempt moved beyond both corrected privacy checks, then the local Docker failure recurred. An unblocked `ctm_app` account lookup remained active for more than 51 seconds despite the role's 15-second `statement_timeout`; `pg_blocking_pids` was empty and no wait event was reported. The runner was interrupted to prevent a longer hang. Ownership was verified before targeted cleanup, but Docker returned `tried to kill container, but did not receive an exit event`. [Sanitized stall evidence](postgres-private-oracle-stall.json).

No full-suite pass is claimed. No permission, policy or production behavior changed. No further local Docker acceptance may start while this owned container exists. Governance must recover it. The authorized shared test server remains the preferred acceptance environment once a genuine fictional sign-in identity or governance-owned private harness is available. Historical failures and the separate seven-group returned-correction pass remain intact.

