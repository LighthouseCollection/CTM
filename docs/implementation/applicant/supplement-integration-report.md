# Ten supplement integration batches completed locally

## Current supplement integration (2026-10-21)

Backend a0bd138 now supplies own supplement history/capability, version checks and
idempotent recovery. The applicant workspace consumes actual hash-only manifests,
freezes the displayed version and one key, recovers matching own receipts, and offers
explicit exact retry after refresh. It supports appeal and closed-case first-filing
reconsideration; the latter is verified with controller/contract browser fixtures.

Current checks: 78 frontend tests, 61 real API/browser scenario groups, nine
supplement interruption/EN–AR groups and nine shell groups pass. The real runner
uses isolated SQLite, synthetic sessions/content and scanner test policy. Controlled
provider output remains a fixture. No PostgreSQL/live-provider/antivirus/institutional
wording/signature/issuance acceptance is claimed. [Report](supplement-integration-report.md)
and [Download JSON](supplement-integration-result.json).

| Batch | Work | Result / coverage |
| --- | --- | --- |
| 1 | Own history | Actual private own capability/history with hashed manifests; no invented actor/file metadata. real API. |
| 2 | Bound submission | Displayed version and one frozen idempotency key; stale/malformed requests denied. unit and real API. |
| 3 | Safe evidence | Latest own ordinary originals only; superseded/pending/cross-application evidence and unsafe bytes denied. real API and fixtures. |
| 4 | Review preservation | Escaped local text and frozen evidence names retained; links require current clean authorization. real API and interruption fixtures. |
| 5 | Lost acknowledgement | One real committed append recovered by matching own key/text/files after explicit refresh. real API. |
| 6 | Exact retry | Original payload/key/version reused; exact server replay returns same receipt without extra alerts, changed replay rejects. real API and explicit-retry browser fixture. |
| 7 | Closed-case first filing | Same supplement panel enabled for closed_case_intake, with neutral filing wording. controller and synthetic contract browser; not full real intake journey. |
| 8 | EN/AR | Actual receipt history and recovery fit Arabic390px without runtime styles/overflow. real API and browser fixture. |
| 9 | Privacy/interruption | Linked spouse/staff denial, parent dirty/unload/navigation guards, denied-refresh private-view clearing and post-withdrawal recovery. real API and fixtures. |
| 10 | Evidence/integration | Independent review findings reproduced/fixed; reports, JSON, queue and contract updated. source review and checks. |

Implementation: `static/ctm/applicant-supplements.js` and the reconsideration hook in
`applicant.js`. Source contracts: backend `docs/implementation/twenty-batch-continuation.md`
and `tribunal/services/filing_actions.py` / `decisions.py` at the SHA above. Shared
`app.js`, shell template, backend services/migrations and protected specifications
are untouched. The existing proposed shell patch loads the module; PR #5 stays draft.

Red/green regressions cover actual hash-only receipts, frozen version/key and exact
recovery/retry, preserving unavailable evidence during refresh, keeping frozen evidence
names with current-only links, and local-selection copy without an unconfirmed receipt
claim. Independent review identified the last two issues; both were reproduced and fixed.

[Detailed real API evidence](supplement-api-result.json) · [Remaining work](remaining-work.md).
Earlier source reconciliation at d724ba5 remains a valid historical snapshot;
its AS09 missing frontend contract is superseded by this local integration.

During final verification, one runner invocation ended before output and one rerun
hit SQLite write contention between a language-preference POST and synthetic fixture
setup. The harness now awaits the real preference response before that fixture writer;
the final complete run passes all 61 groups. This does not establish PostgreSQL race
acceptance, and no backend lock/authorization rule was relaxed.
