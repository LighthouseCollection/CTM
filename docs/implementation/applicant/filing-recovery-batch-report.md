# Next ten applicant batches: filing actions and checkout recovery

## Current filing/recovery verification (2026-10-21)

The next ten batches integrate backend `d724ba56b8bd5cf501d55fbbca416470108f963a`
(including filing contracts introduced in acafe29). Own draft deletion and withdrawal
now use the server capabilities and current answer version. Original checkout recovery
uses the retained candidate, attestation, exact declaration and future provider expiry.
Local expiry removes resume only; it never reconciles a payment or enables a new charge.

Current checks: 68 frontend tests, 54 real API/browser scenario groups, 11 response/
recovery/lifecycle fixture groups and nine shell groups pass. The earlier 66/42 results
below are historical snapshots. All backend data is isolated/synthetic; one controlled
provider-create output verifies retained adapter behavior without network or a charge.
The second joint filing and pending appeal state are explicit fixtures. PostgreSQL,
live provider callbacks/antivirus, institutional wording and document issuance remain
outside this acceptance. [Report](filing-recovery-batch-report.md) and
[Download JSON](filing-recovery-batch-result.json).

| Batch | Work | Evidence |
| --- | --- | --- |
| 1 | Draft deletion | Explicit current capability and confirmation; draft revisions/file records are removed and retained original URLs deny access. |
| 2 | Action concurrency/privacy | Missing/malformed/stale versions and foreign owner fail; stale browser confirmation locks until refresh. |
| 3 | Returned withdrawal | Returned filing cannot use draft deletion; own withdrawal retains fee/history. |
| 4 | Joint case safety | Synthetic second participant remains active after first withdrawal; last withdrawal closes case; no spouse notice. |
| 5 | Pending appeal withdrawal | Synthetic pending appeal stays owner-only before disposition; fee/revision and closed case retained. |
| 6 | Original checkout recovery | Real adapter with controlled provider output retains exact candidate/version/signer/declarations; GET is private/no-store. |
| 7 | URL and expiry | Exact HTTPS provider host, raw controls rejected, explicit future expiry; timer and click recheck. |
| 8 | Payment state changes | Processing/paid/reconciliation/elapsed expiry/changed revisions hide resume and block fresh charge. |
| 9 | Interruption and EN/AR | Lost deletion acknowledgement recovers once; mobile RTL and expiry while mounted verified. |
| 10 | Review and evidence | Read-only independent review, consolidated report/JSON and remaining dependency reconciliation. |

Production changes are limited to `static/ctm/applicant-recovery.js` and
`applicant-lifecycle.js`. Tests exercise actual adapter contracts in
`scripts/browser_applicant_api.py` and `scripts/applicant_filing_acceptance.py`;
interruption/clock regressions are in `scripts/browser_applicant_next_batch.py`.
New unit regressions cover expiry/raw URLs and literal action confirmation.

Red/green evidence: missing/elapsed expiry and truthy confirmation initially failed
unit checks. Mounted expiry and expiry beyond the browser timer maximum initially
failed browser checks, then passed after fixes. Independent review found no production
correctness/privacy issue and identified a screenshot caret artifact risk; the test
now uses the established `caret="initial"` setting.

[Remaining work](remaining-work.md). The previous ten-batch report retains its
recorded version and results; this report supersedes its lifecycle/resume dependencies.

[Detailed API predicates](filing-recovery-api-result.json). Physical storage cleanup was not independently verified.
