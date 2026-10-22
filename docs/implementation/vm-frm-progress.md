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
