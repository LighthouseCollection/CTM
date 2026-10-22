Current validation: **833 PostgreSQL passed, 1 skipped**, migration rollback/reapply through0047 and no model drift. Nineteen new physical-role status/receipt checks plus one cross-adapter endpoint lifecycle; SQLite lifecycle separately passed. Council UI/integration acceptance remains required.

C05 capability status/receipt: new read-only Bearer-only status endpoint exposes only lifecycle/expiry and an unexpired original report ID/time receipt.0047 adds app-only digest-bound projection; no existing mutation/row-visibility change. See external-status-receipt.md. UI metadata unique successor proposal0048after0047.

Governance scoped withdrawal acceptance:73357864789e22bb504002b089f2934e11f86e37 withf0e97fa/0046 verifies firstwithdraw keeps case/otherfiling open, finalwithdraw closes case, fee/history/notification isolation and linkedsubmit201. Focused7pass/outer66partial; later message-pagination fixture stops broader run, so no full applicant/QA acceptance inferred.

Current validation: **813 PostgreSQL passed, 1 skipped**, migration rollback/reapply through0046;16 new physical-role browser-entry regressions and Chromium fragment-transport smoke passed. No model/route/migration/grant changes in this continuation.

External priest browser entry now negotiates explicit HTML navigation to the existing council static page while preserving Bearer JSON. No asset copy/migration; combined council assets and exact-successor browser acceptance are required. See external-browser-entry.md.

# Backend stream status: issue #2

Owner: VM-FRM backend/security; branch work/vm-frm-backend; draft PR #7.
No merge, deployment, operational migration or credential change is authorized.

## Completed (implementation; acceptance separate)

Prior historical validation:764 PostgreSQL passed/1skip through0044; current delivery validation is recorded above. Protected151-table specification and accepted questions unchanged.

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

## Account administration and returned filing continuation

Account directory/detail/status/history APIs, compare-and-save status changes,
target session revocation, source-bound configured bilingual status notices and
stable assigned_member_id are implemented.0040 adds the audit index and restricted
notice proofs;0041 corrects bound returned-petition resubmission with optional or
corrected DOB. Current adapter:63 domain models,99 routes,63 forced-RLS tables.
[Contract and remaining work](account-administration-contract.md).

## Integrated fix and private draft contract checkpoint

Governance reports48b80c4 integrated/deployed for testing asb3de51e with0040/0041.
Applicant89072dd reports all seven focused physical-login PostgreSQL groups pass,
including the exact returned correction failure. Backend48b80c4 hosted checks pass.
A subsequent broader strict403 expectation receives the intended private-resource404;
four app SQL-session regressions now cover detail/history/files/payments, all council
roles and unrelated applicants, identical hidden/absent bodies, list isolation and
private cache headers. No policy/API/migration change is needed for that oracle.
[Evidence, contract and B01 evaluation](private-draft-read-contract.md).

## Own session administration continuation

Active accounts can list valid own sessions with opaque handles and explicitly
revoke one, including the current session. Owner filtering precedes pagination;
foreign/absent sessions share404; current-session revocation logs out the next
request. Deletion and actual-actor audit are atomic. No migration or grant change.
[Wire contract, evidence and adapter limits](own-session-administration.md).
Microsoft callbackc06b869 is also pushed (679-test checkpoint); hosted checks pass.
Governance reports it preserved in deployeddccbd63; genuine callback confirmation
remains separate. Independent QAc54333d reports13/13 and32/32 backendfix checks on
b3de51e only, not the latest deployed head.

## Tribunal Sessions list continuation

GET /api/sessions/ now supports bounded offset/limit/next_offset, optional planned/
closed state and inclusive date_from/date_to filters before pagination. Existing
fields/capabilities and default100 are preserved; rows beyond the former cap are
reachable. Council-only authority remains. No lifecycle semantics or unsupported
session timing/location/presiding/minutes fields are invented.
[Contract and remaining field decisions](session-list-continuation.md).

## Council appointment and assignment history continuation

Admin/secretary can page actual memberships and assignment-role history for an
existing council account, including inactive accounts. Real appointment/grant
actors and recorded intervals are retained; revocation actor/time are returned
only from actual audit evidence. Current scope/grant flags do not widen authority.
No historical appointment or baseline role grant is invented.
[Projection, provenance and limits](member-history-projection.md).

## Council request original privacy correction

Reproduced council C05 subject-applicant HTTP200 after clean scan for an external
priest upload. New external_priest/interview uploads are council-visible with no
owner; service and0042 read/write policy guards also protect retained legacy wrong
scope and derived scan/text rows. Original evidence is not rewritten. External-link
responses consistently use no-referrer. Twenty-one targeted regressions and full suite
pass; independent exact-successor negative-access acceptance remains required.
[Root cause, migration coordination and limits](council-request-file-privacy.md).

## Applicant request author projection correction

Reproduced valid admin-authored requests returning generic404 because author
Account RLS correctly hid the administrator.0043 exposes only author display names
bound to authorized request IDs; the endpoint keeps its author field without
Account dereferences or broader Account SELECT. Admin remains hidden, member author
remains genuine, and outsider/private/external/interview/worker access stays denied.
[Source-scoped lookup, grants and successor acceptance](request-author-projection.md).

## Filing document-label settings consumer

Owner filing-file requirement labels now consume valid latest document_categories
bilingual configuration through a narrow app-only projection; invalid legacy values
fall back to existing labels. Requiredness, codes, contextual originals, scans and
submission/recovery validation remain unchanged; settings rows stay hidden.
[Runtime semantics, grants and content acceptance](document-label-consumer.md).

## Recent backend corrections

- 0045: first linked petition without optional spouse DOB. Governance verified submit201/same-case/own-answer/private-history on ace31522; full applicant acceptance remains separate.
- 0046: joint withdrawal decision respects hidden participants; final authorized closure clears all case claims and unfinished requests. Applicant successor2a7d0eb rerun stopped earlier at a synthetic closure reason; the approved decree_issued fixture contract was supplied without weakening policies. Withdrawal successor acceptance remains pending.
- Council link metadata and browser entry are implemented; no priest recording, paper or delivery completion is claimed.

## Unfinished

UI's other requested backend contracts remain unfinished: approved own-profile/
contact/portrait mutations, verified email/provider administration, broader normalized/admin session history, member
contact/portrait editing and broader institutional history, formal-source factual discrepancy views,
and consumer integration of stored settings beyond account status notices and filing document labels. Council C05 external
recording/paper-completion/invitation contracts remain unfinished. Capability status/receipt is implemented; council UI binding and independent acceptance remain pending. Browser-entry routing and council link metadata are implemented; combined UI acceptance remains pending. Pagination and per-family settings
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

- Governance reported serial integration of48b80c4 asb3de51e; subsequent backend test/documentation checkpoints still require review.
- UI binds list continuation; applicant focused physical-login rerun passed onb3de51e.
  Its broader private-draft404 oracle was reconciled in0828515; the full PG run
  remains incomplete after an isolated account-query/Docker stall, with prior findings preserved.
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
