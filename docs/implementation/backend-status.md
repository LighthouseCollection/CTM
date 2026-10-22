# Backend stream status: issue #2

Owner: VM-FRM backend/security; branch work/vm-frm-backend; draft PR #7.
No merge, deployment, operational migration or credential change is authorized.

## Completed (implementation; acceptance separate)

Validation: **566 PostgreSQL passed,1 skipped**; no model drift; migration rollback/
reapply through0038. Protected151-table specification and accepted questions unchanged.

- Seven remaining core-table policy reviews implemented in0037, with63/63 current
  domain tables forced RLS; queue provenance in0036.
- Explicit existing-role app/worker grants and bounded private-draft retention in0038;
  actual named-role tests cover filing, authentication/provider bootstrap, delivery,
  retention, paid recovery and denial of unauthorized identities/provider facts.
- Approved-schema reconciliation expanded to all151 tables and their column/type/
  relationship evidence. Confirmed gaps and migration families are recorded in
  schema-gap-review.md; no accepted equivalence claim for the63-model adapter.
- Live-service dependencies separated in live-service-dependencies.md.
- All streams received the requested continuation/ownership/acceptance instructions
  on issues #1/#2/#3/#15/#4. Council is restricted to its requested first task.

## Unfinished

Full approved-schema implementation is not complete. Required identity/version,
account/institution history, typed family facts, source/citation and association
migrations are identified in the schema gap review. The field inventory deliberately
retains unaccepted candidate mappings; it is not a semantic sign-off. This delivery
completes the requested reconciliation/documentation, not those future migrations.

## Blocked (exact dependencies)

- Live-service acceptance: operator-managed provider/SMTP/Stripe/search/scan bindings
  and authorized test identities/mailboxes; see the separate dependency matrix.
  Operational availability is unverified, not asserted missing based on this sandbox.
- Accepted application fact/repeat mapping: applicant issue #1 supplies approved
  question, validation and Arabic mappings before normalized fact backfill design.
- Canonical institutional/membership/content records and identity correction rules:
  institution/governance acceptance before populating new retained fact structures.

## Awaiting acceptance

- Governance reviews and serially integrates this PR's exact delivered SHA.
- Independent non-owner/integration/browser acceptance against that successor SHA;
  QA issue #15 preserves existing findings and follows council's unsaved-text fix.
- Institution accepts schema equivalence, operational readiness and live-service
  evidence. Passing isolated backend tests does not close these gates.

## Publication ledger

The code, tests and reports in this delivery are published together in draft PR #7.
The issue #2 delivery comment records the exact commit and verification counts.
Earlier progress sections retain their historical numbers; they are not current
integration or live-service acceptance. No work is represented as pushed until the
branch update is confirmed. Remaining working-tree changes, if any, must be named
in the GitHub delivery comment.
