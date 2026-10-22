# Backend stream status: issue #2

Owner: VM-FRM backend/security; branch work/vm-frm-backend; draft PR #7.
No merge, deployment, operational migration or credential change is authorized.

## Completed (implementation; acceptance separate)

Validation: **647 PostgreSQL passed, 1 skipped**; no model drift; migration rollback/
reapply through0039. Protected151-table specification and accepted questions unchanged.

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

## Applicant checkpoint continuation

The latest backend-owned slice implements recursive repeat validation, stable row
identities, textarea publisher/runtime agreement, RO case-number aliases and MC/CMC
category reconciliation, plus new-case identity snapshot binding in0039. Details,
compatibility and remaining content dependencies:
[applicant-validation-checkpoint.md](applicant-validation-checkpoint.md).

## Runtime identity and UI pagination continuation

Bounded actual SQL session-identity HTTP regressions, hidden/absent404 contract,
and authorized continuation for cases and case/system audit are implemented.
[Runtime investigation, pagination and limitations](runtime-pagination-continuation.md).
The applicant's external account-query stall was not reproduced by these tests and
remains unresolved; no shared engine/container operation was performed.

## Typed settings continuation

All six setting families now expose bounded value schemas and validation, HTTP
writes require expected_version, and safe incompatible legacy values are flagged
while unsafe legacy values are redacted. This is typed version storage; provider/
consumer activation and approved bilingual content remain separate unfinished work.
[Wire contract, compatibility and acceptance](typed-settings-contract.md).

## Unfinished

UI's other requested backend contracts remain unfinished: approved own-profile/
contact/portrait mutations, verified email/provider/session administration, member
contact/appointment/history projections, formal-source factual discrepancy views,
and consumer integration of stored settings. Pagination and per-family settings
edit schemas are addressed in these continuations;
those separate contracts are not claimed complete or all blocked by credentials.

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
  question and Arabic mappings before normalized fact backfill design. The reported
  recursive validator and textarea gaps are addressed in the checkpoint continuation;
  exact per-prior-marriage requiredness/answer states and approved Arabic civil-certificate
  wording still require content/configuration owners.
- Canonical institutional/membership/content records and identity correction rules:
  institution/governance acceptance before populating new retained fact structures.

## Awaiting acceptance

- Governance reviews and serially integrates this PR's exact delivered SHA.
- UI binds list continuation; applicant independently reruns the actual physical-login
  browser journey and preserves its previous403/404 and stall findings.
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
