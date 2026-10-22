# Ten applicant batches completed locally

## Current verification: ten batches (2026-10-21)

Backend `480a246118cce8c4ac338c32c71c79cde74816d2` supplies the own request
fingerprint, capabilities, scoped originals, published declaration and retained
consent/response receipts. Intake and assessment workspaces now use these actual
contracts. The previously reported closure disclosure is resolved and independently
verified: never-sent drafts remain private; previously sent closed requests remain
readable, and exact submitted responses recover their original receipts after closure.
The default closure gate remains enabled.

Final local checks: 66 frontend tests, 42 real API/browser scenario groups, five
assessment interruption groups, nine next-batch groups, nine shell groups and four
request-reader groups pass. The real API runner uses isolated SQLite, synthetic
accounts/content, temporary backend archives and a scanner test policy. It does not
establish PostgreSQL, live provider/payment/antivirus, institutional wording approval,
signature issuance or operational delivery acceptance. See the consolidated ten-batch report and JSON evidence.

| Batch | Completed work | Evidence |
| --- | --- | --- |
| 1 | Closure privacy | Never-sent drafts excluded after actual closure; sent closed rows retained. |
| 2 | Own request identity | Opaque fingerprint, proceeding and explicit capabilities validated. |
| 3 | Intake responses | Bound answers reviewed and submitted without internal observations. |
| 4 | Receipt recovery | Exact replay reuses receipt, including after closure; changed replay rejected. |
| 5 | Published declaration | Exact supplied bilingual version displayed and explicitly accepted. |
| 6 | Scoped originals | Request-bound uploads, clean-only exact links and distinct report evidence. |
| 7 | Consent binding | Signature original, declaration and council/request/proceeding scope retained. |
| 8 | Assessment response | Signed-scope-gated report submission and immutable original receipt. |
| 9 | Interruption/privacy | Dirty evidence survives refresh; upload blocks pending discard; denied reads clear private links. |
| 10 | Integration/evidence | Proposed shared shell patch, consolidated report and sanitized JSON. |

The implementation lives in `static/ctm/applicant-assessments.js`,
`applicant-responses.js` and `applicant-requests.js`. Regression evidence is in
`tests/frontend/applicant-assessments.test.cjs` and the matching browser scripts.
Independent review found two interruption issues; failing browser regressions
reproduced both, fixes passed, and review found no further concrete findings.
Shared `app.js`, shell template and protected build specifications were not edited;
governance receives only the shell integration patch. PR #5 stays draft.

[Download JSON](ten-batch-result.json) · [Remaining work](remaining-work.md)
