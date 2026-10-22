# VM-FRM backend progress

Issue: https://github.com/LighthouseCollection/CTM/issues/2

## First slice: applicant filing contract

Own application list, create and detail responses now include the bound
`questionnaire` (`id`, `version`, `published`, `definition`, `declaration_en`,
`declaration_ar`), `duplicate_hold`, latest `return_instructions`, and boolean
`can_edit`, `can_checkout`, `can_submit`, `can_resubmit`.
Filing action fields are supplied only to the application owner. Submitted
council projections now also include the completeness review contract described
below. Drafts remain inaccessible to council.

Filing flags check saved answers, current safe required documents, verified
owner, duplicate hold, lifecycle, fee and published bilingual declaration for
first filings. They describe readiness before attestation/provider availability;
mutations revalidate and remain authoritative. `can_edit` is independent of
payment readiness. Returned petitions retain their original signature/fee,
enable resubmission and never enable checkout. Closed original proceedings
remain read-only, including after an appeal reopens the case.

`POST /api/applications/{id}/checkout/` and `/submit/` require
`expected_version` as a non-negative JSON integer. A stale version returns 422
before creating a candidate or submission. Service comparison occurs after the
application row lock; successful submission key replays return the original
submission. Existing internal/provider service callers may omit this argument.

First checkout/submission refuses an unpublished or incomplete bilingual bound
declaration; no latest-version substitution occurs. Returned filings reuse the
original attestation without requiring another signature.

Existing upload route is `POST /api/files/`. The earlier `/api/uploads/` progress
note was incorrect; the route has not changed.

## Validation and remaining work

- 22 filing contract regressions pass on SQLite in an isolated container.
- Full isolated PostgreSQL suite: 209 passed, 1 skipped. Includes all application
  migrations, raw non-owner RLS tests, returned filing projection under a
  non-owner role, and checkout waiting for a concurrent answer save.
- Skipped check is `test_deployment_init.py`'s disposable GitHub-service-only
  deployment initialization check; no operational initialization was run.
- `makemigrations --check --dry-run`: no changes detected. Structural build-spec
  validation passes (151 tables, 59 accepted questions preserved). These checks
  do not establish full model/contract reconciliation or production readiness.
- No schema changes; preserve existing models and protected 151-table contract.
- Full schema reconciliation, outstanding policies/grants and live payment/email
  acceptance remain incomplete.
- No payment/email credentials were configured or provider success claimed.
- Git CLI credentials are unavailable. The independent shallow application
  checkout was reconstructed from connector source and verified against main
  `da99591136f2136c0adfcfe7f443ca3384e8b948`; binary historical reference
  documents are omitted locally. Publication uses the GitHub connector with
  current main as parent. Prototype history is separate.
- No operational migration, credential change, deployment or merge performed.

## Continuing slices: documents, council reads and decision privacy

- `GET /api/applications/{id}/files/` is owner-only and returns current ordinary
  originals with scan state, clean-only authorized download URLs, `can_upload`
  and bilingual requirement labels. Requirements share submission validation:
  filing kind, configured categories, typed-statement alternative and each saved
  restraining-order identifier. Unknown scan results fail closed. No history or
  storage keys are exposed. Replacements must match context and visibility.
- Upload uses the existing `POST /api/files/`. Owner uploads lock application;
  staff corrections lock case without granting managers application-answer writes.
- Council application projections include applicant name, submission time/version,
  bound questionnaire, immutable submission manifest, review history and
  `can_review`. `?state=awaiting_review` is council-only. Closed proceedings cannot
  receive completeness decisions.
- Session agenda adds presenter/party/hearing/testimony data and capabilities,
  including attendance-gated `can_present`. Case detail adds assignment/placement
  capabilities. Active roster identifies presidents; no fictitious seeded president.
- `GET /api/hearings/{id}/` includes retained outcome revisions. Part 1 assignment
  items become `assigned` at session close and are not carried forward; they
  cannot be presented as Part 2 hearings.
- Decision GET retains all versions, effective latest votes plus vote history,
  approval/history, and current-version action flags. Request listing adds subject,
  language, timestamps, parent and author. In-person interview send no longer
  notifies the applicant, and applicants cannot complete an interview request.
- Taxonomy projection uses `topic_groups` arrays because approved categories may
  belong to several groups. Category/group Arabic labels are null until reviewed
  content exists; English/Arabic question wording is never synthesized. Sending
  a question without wording for the selected language is refused.
- Migration `0013_decision_privacy` adds forced RLS to six more tables: decisions,
  votes, approvals, signature attestations, decrees and releases. Non-owner tests
  cover self/on-behalf boundaries, stale decision rejection, exact signed PDF,
  issuance and recipient-specific release/revocation. Total protected tables: 29;
  this is not complete domain/schema reconciliation. No production grants added.
- External priest capability page/email delivery (D10), reviewed Arabic question
  translations (part of D9), finance/auth/worker grants and remaining schema mapping
  remain open. Continued checks and integration results belong on PR #7 / issue #2.
- Continuing-slice validation: full isolated PostgreSQL suite **234 passed,
  1 skipped**, including reversal/reapplication through migration 0013 and raw
  decision/decree non-owner tests. `makemigrations --check --dry-run` finds no
  model drift. All migrations ran only in disposable test databases.

## Payment lifecycle, finance privacy and readiness gate

- Checkout and payment events retain the provider PaymentIntent identifier in
  migration 0014. Signed unpaid checkout completion remains `processing`; only
  verified paid events can satisfy a fee. Signed expiry/failure is retained and
  never downgrades a paid/finalized candidate. An unresolved or stale checkout
  prevents a second payment/manual submission or a waiver over an in-flight fee.
- Verified dispute/refund facts preserve applications/submissions and notify
  admin/secretary. A refund observation is not a refund request/authorization.
  `charge.refunded` amounts are cumulative provider observations, not additive
  refund allocations. No refund API operation or live Stripe call was performed.
- Late payment after an earlier checkout expired remains recoverable even if a
  new pending attempt prevents finalization. Recovery commits its `needs_review`
  state/alerts before surfacing validation failure; no paid fact is lost and no
  automatic extra charge is attempted.
- `GET /api/applications/{id}/payments/` provides owner/authorized finance history,
  with verified-payment evidence separate from waiver/exemption. Admin/secretary
  have `GET /api/payments/reconciliation/` and authenticated POST
  `/api/payments/{intent_id}/retry/`; retry revalidates the paid candidate and
  never contacts Stripe to charge again. No private answers appear in the queue.
- Migration 0015 adds forced RLS on obligations, checkouts, payment events and
  completeness reviews. Signed callbacks/recovery use narrow transaction-local
  provider context, never interactive browser identity. Snapshot/source identity,
  paid/finalized state, fee amount and waiver attribution cannot be reset.
  Admin/secretary can waive an eligible obligation without draft-answer access.
- `check_backend_readiness` is a read-only CLI gate. It reports role privileges,
  ownership access, installed tables, forced RLS, grants and public helper ACLs.
  `--report-only` collects blockers without a failing exit status. It never grants
  privileges or claims that configured credentials prove provider acceptance.
- Latest full isolated PostgreSQL suite: **255 passed, 1 skipped**. Migration
  reversal/reapplication now reaches 0015; 33 domain tables have forced RLS.
  Django reports no missing model migrations. Inventory still reports 58 models
  against the approved151-table contract, with explicit routes regenerated.
- Provider event references follow [Stripe's event types](https://docs.stripe.com/api/events/types)
  and [Checkout Sessions](https://docs.stripe.com/api/checkout/sessions). Real test-mode
  credentials/callback acceptance, duplicate-refund authorization/allocation,
  receipts/email delivery, remaining identity/report/worker policies and complete
  schema reconciliation remain open. No credential/operational change occurred.

## Planned sessions and testimony

- Migration 0016 adds `agenda_transfer_events` and `testimony_appointment_versions`
  using the approved table names, plus original message-session snapshots and an
  explicit outbox discard timestamp. Existing 58 models are preserved (60 total).
- `POST /api/sessions/{id}/reschedule/` takes `{date,reason,appointments:{id:
  {starts_at,ends_at,instructions?}}}`. Every active testimony needs explicit new
  timezone-aware non-overlapping times. It creates a new session and all agenda
  entries, retains source/attendance snapshots, moves appointments with new
  invitation versions, preserves responses and removes source agenda/session.
- Held hearings/completed history, occupied dates and unresolved closed-case agenda
  entries reject the operation atomically. **Repeat-reschedule limitation:** a
  retained transfer's destination FK prevents deleting that destination later.
  This case is explicitly refused pending governance reconciliation of the
  approved restrictive relationship; history is not deleted or rewritten.
- Deferred messages retain body/sender/recipients and original session snapshot;
  only the operational session binding moves under an exact audited transaction
  context. The pending email still waits for the new selected session to close.
- `GET /api/appointments/` exposes only the signed-in applicant's invitation,
  version, response and `can_respond`, without internal agenda/attendance access.
  Existing response POST rejects stale versions and closed/cancelled invitations.
  `POST /api/appointments/{id}/cancel/` requires an authorized writer and exact
  `expected_version`, retains a new cancelled snapshot and privately notifies owner.
- One-day reminder jobs are version-bound. Superseded jobs are explicitly
  `discarded_at`, never `delivered_at`; no email success is fabricated. Worker-only
  predicate functions recheck current invitation and selected-session closure.
- Forced RLS now covers 37 domain tables, including appointments, responses and
  immutable transfer/invitation history. DB triggers reject overlap, subject/version
  takeover and message-body/history rewrites. Full isolated PostgreSQL suite:
  **265 passed, 1 skipped**, including rollback/reapplication through 0016 and a
  complete reschedule/own-response path under a non-owner role. No model drift.
- GitHub PostgreSQL CI passed on finance head `6e690b5`; scheduling CI follows push.

## Newly prioritized owner decision

Governance's [2026-10-21 owner clarification](https://github.com/LighthouseCollection/CTM/blob/main/docs/implementation/reviews/owner-clarifications-2026-10-21.md)
and issue #9 supersede earlier returned-correction visibility assumptions. F08 /
AS-F08 requires last-formal-only council reads/bytes/history/search and no early
correction alerts while returned. The applicant stream reproduced the current
gap against finance head. This is the next backend priority; no claim of having
closed F08 is made by the earlier test counts.

## F08 / AS-F08 returned-correction privacy

- Council application detail/version and answer history now use formal submissions
  while returned. The applicant retains the current private edit state. Returned
  edit windows are derived from immutable completeness-review/submission history;
  unsubmitted intermediate corrections remain private after a later resubmission.
- Council file lists/history, ordinary download, HEAD, Range, inline preview and
  source-authorized search reject pending correction originals. Default lists
  retain the latest formal manifest rather than switching to the private replacement.
  Pending corrections are not sent to the search index. Prior formal bytes remain
  available, subject to their current technical safety gate.
- Migration 0017 applies the same restriction to non-owner PostgreSQL reads of
  answers, attachment roots, file versions/technical events/derivatives, audit
  sources and retained correction notifications. Existing source ACLs and medical/
  exact decree-release rules still apply. No historical content is rewritten.
- Returned saves/uploads no longer queue manager alerts. Retained pre-fix jobs
  are rechecked before delivery; private jobs are discarded without delivered_at.
  Resubmission retains original signature, fee and case and exposes only the
  actual formal revision/manifest. No new recipient-routing policy is inferred.
- Full isolated PostgreSQL suite: **270 passed, 1 skipped**, including F08 HTTP
  surfaces, multiple edits/returns, cached search, legacy outbox suppression,
  raw non-owner queries, and migration rollback/reapplication through 0017.
  Applicant-stream browser reacceptance is still required; these backend checks
  do not claim the independently reported browser acceptance has passed.

## Council D12–D18 read contracts and retained library

- D12: decision history includes `decree` (or null), reference/language/issuance,
  signer identity, signed-file ID and chronological release/withdrawal events.
  This stays council-only and works after closure and reload.
- D13: council `GET /api/files/{id}/status/` reports latest scan state and
  `can_download`. It preserves draft/returned/medical source authorization and
  supplies no file bytes or storage keys. A non-clean result never enables download.
- D15: staff appeal detail/list includes supplements with manifests and actors,
  disposition with hearing/reopened-proceeding IDs, eligible hearing IDs/dates,
  and `can_record_result`. It removes the need to scan the latest 24 agendas.
- D16: assessment request metadata adds `release_status` (none/signed/out_of_scope)
  and `release_scope` containing only the council boolean. A narrow PostgreSQL
  helper lets council read this consent status without access to out-of-scope
  release rows, private consent text, signatures or report content.
- D17: note revisions include original author ID/name, timestamp and current
  author/write-eligibility `can_edit`. Existing findings route now supports GET
  with retained fact revisions, values, source references and actual actors.
- D18: template list includes owner, retained version and question code/version
  references. Admin/secretary `POST /api/templates/{id}/publish/` creates a shared
  copy of the retained personal version; it never transfers the source owner.
  `POST /api/templates/{id}/retire/` is personal-owner-only or administrative for
  shared templates, audited and irreversible. Publishing/retiring serialize on
  the source; retained template versions are never deleted or rewritten.
- Migration 0018 adds forced RLS/provenance guards for the two library tables;
  **39 domain tables** now have forced RLS. Runtime-role tests cover private
  template isolation, denied shared creation/ownership takeover/history rewrite,
  consent metadata without content access, and migration reversal/reapplication.
- F32 owner-decision regression checks verify shared closure releases all claims
  for that case and preserves unrelated cases. A conflicting open claim blocks
  appeal acceptance atomically, retaining the pending appeal and original closure.
- Full isolated PostgreSQL suite: **280 passed, 1 skipped**; no model drift;
  inventories: **60 domain models / 151 approved contract tables, 75 routes**.
  GitHub PostgreSQL CI passed on privacy head `859e42b`; this slice follows push.

## Remaining owner-decision reconciliation

- F15 same-person president+admin assignment needs effective multiple-role
  representation; current Account.role is singular. Do not fabricate a second
  person or infer presidential authority for every administrator. Approved
  staff_memberships/staff_roles reconciliation remains required.
- F12 linked never-filing spouse filing against a closed case still needs the
  closed-case intake and council acceptance/reopening transaction. Current code
  refuses the closed match; it must not be presented as implemented.
- F30 secretary joint-withdrawal authority and manual priest bearer-link delivery
  remain unapproved; neither permission is inferred. D14 approved bilingual decree
  templates/rendering and the medical release declaration remain institutional
  content dependencies. Public/provider/end-to-end acceptance remains incomplete.

## Governance withdrawal regression and council security follow-ups

- F08 follow-up: staff detail/list now tests current revision visibility rather
  than only `status == returned`. After a returned private edit followed by
  withdrawal/closure, privileged connections still fall back to the last formal
  revision; runtime connections do the same when RLS hides the current revision.
  The applicant retains their own saved work. Formal answers are never replaced
  with empty answers just because the private current row is invisible.
- `POST /api/search/` now accepts JSON `{q, history?:boolean, case_id?:uuid}`;
  GET is refused (405). Existing authentication/CSRF protections apply. Search
  phrases therefore need not be put in URLs by clients; council must switch its
  caller to POST. Invalid non-boolean history values are refused.
- Search results and index writes exclude medical/psychological request files,
  plus all medical-visibility files, regardless of council disclosure consent.
  Cached hits are rejected before derivative/snippet retrieval and result counts.
  Dedicated authorized assessment access remains separate. Existing external
  indexes may retain previously indexed text and need an operational review/purge;
  this implementation does not claim to have removed external indexed content.
- Ordinary follow-up requests cannot use medical/psychological reports as parent.
  Assessment follow-ups remain allowed. Migration 0019 also enforces this for raw
  database writes, same-case parent binding, retained request scope/identity and
  retained Report.request identity. Existing historical rows are not rewritten;
  lifecycle updates remain possible without rebinding their source.
- Full isolated PostgreSQL suite: **290 passed, 1 skipped**, including detail/list
  withdrawal under a non-owner role, both assessment kinds and visibility paths,
  consent-bearing cached hits/index suppression, POST-only request contract,
  raw parent/rebinding denials and migration rollback/reapply through 0019.
  Prior council head `e2f714a` passed both GitHub PostgreSQL checks.
