# VM-FRM: backend/security/integration

Implement shared backend contracts in LighthouseCollection/CTM on branch
work/vm-frm-backend, in your own clone. Read governance.md and all approved
build-spec contracts before changes. Inspect existing58-model implementation;
do not replace it or rewrite the approved151-table contract to match it.

Prioritize APIs needed for the applicant-to-decree demo, business constraints,
permissions, remaining database policies/grants and realistic payment integration.
Own all new migrations and backend changes; coordinate endpoint contracts with
both UI streams through their issues. Verify PostgreSQL migrations and non-owner
access tests. Missing credentials are blockers to report, not reasons to fake
payment/email success. Microsoft login is verified locally; preserve its tenant
and preauthorized subject checks. No local passwords.

OCR/audio are deferred. Do not change credentials, deploy, run operational
migrations or merge independently. Push an early draft PR, record checks and
blockers, and keep progressing on independent work.
