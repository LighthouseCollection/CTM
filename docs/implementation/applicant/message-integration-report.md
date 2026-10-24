# Ten applicant private message batches completed locally

## Current private message integration (2026-10-21)

Applicant-only messaging now integrates backend db6dfa3: exact own thread binding,
50-row private history continuation, reviewed sending with stable replay keys,
receipt recovery and explicit own portal-copy read acknowledgements. Portal read
evidence is displayed separately from email delivery. Shared shell changes remain
a governance integration patch; no council/shared source is edited directly.

Current checks: 83 frontend tests, 66 real API/browser groups, eight message
interruption/EN–AR fixture groups and nine shell groups pass. These use isolated
SQLite/synthetic sessions and scanner test policy; controlled provider output is
still a fixture. Earlier per-feature counts below retain their recorded snapshots.
PostgreSQL, live email/payment/provider/antivirus and institutional content/issuance
acceptance remain separate. [Report](message-integration-report.md) and
[Download JSON](message-integration-result.json).

| Batch | Work | Result / coverage |
| --- | --- | --- |
| 1 | Own thread | Exact case and one self-party binding, explicit send capability, private routing. unit and real API. |
| 2 | Paginated history | Bounded50-row pages and explicit continuation; no repeated/private malformed projections. unit, fixtures and real API. |
| 3 | Reviewed send | Escaped message review; own portal/immediate recipient only. fixtures and real API. |
| 4 | Frozen replay identity | One stable key freezes text, recipient, channel, timing/session and empty attachment list. unit and real API. |
| 5 | Lost acknowledgement | A real committed send with lost HTTP acknowledgement recovers from later own history page. real API. |
| 6 | Exact retry | Explicit unchanged retry; exact backend replay creates no extra message/alert/job; changed reuse rejects. unit, fixtures and real API. |
| 7 | Read receipts | Explicit own-copy acknowledgement, original timestamp retained; sender/other party denied. unit, fixtures and real API. |
| 8 | Interruption guards | Dirty/unload/navigation protection; pending discard blocks during delayed send; denied refresh retains local intent. browser fixtures and actual shell. |
| 9 | EN/AR privacy | Arabic390px, escaped content/no styles/overflow; all seeded private IDs excluded from spouse-visible pages. fixtures and real API. |
| 10 | Integration evidence | Applicant-only shared shell proposal, independent review and consolidated result/queue. source and checks. |

Implementation is in `static/ctm/applicant-messages.js`. Unit coverage lives in
`tests/frontend/applicant-messages.test.cjs`; interruption fixtures in
`scripts/browser_applicant_messages.py`; actual API acceptance in
`scripts/applicant_message_acceptance.py` under the isolated archive runner.
New controller tests failed before implementation and pass now. Browser fixtures
cover failed read refresh/retry, dropped/committed send acknowledgements, frozen
payload reuse, delayed write/discard guards, malformed/denied refresh and RTL.

Independent review found no concrete module defect. It requested stronger privacy
evidence: every seeded own-private message ID is checked against every spouse-visible
page, including continuation. The actual test now performs that check. Initial harness
runs were corrected to await async history rendering and use the existing “Back to
cases” navigation control; no server behavior or assertion was weakened.

The shared shell proposal loads/routes only applicant messaging; shared `app.js` and
shell template stay untouched. Governance must reconcile this patch with the council
branch serially. PR #5 remains draft. [Detailed real API evidence](message-api-result.json)
and [remaining work](remaining-work.md).
