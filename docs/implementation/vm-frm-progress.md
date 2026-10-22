# VM-FRM backend progress

## Next twenty council revision/historical recovery batches

All20 implemented: typed/optimistic/replay-safe note edits and latest-only edit
capabilities; bounded findings with authorized proceeding citations, compare-save
and exact recovery; typed/optimistic/replay-safe decisions and authoritative list
capabilities; vote keys retaining choice/member/actual recorder under concurrency;
private bounded historical workspace recovery, edited/publication versions and
retained PostgreSQL provenance. Database constraints retain unique note/finding
versions and vote replay identities. Legacy callers can omit the new optional edit
versions; they cannot claim stale-write protection. Report versions remain required.

Full isolated PostgreSQL: **528 passed, 1 skipped**; no model drift; migration
rollback/reapply through0034. Five concurrent resource-write/replay scenarios and
independent runtime-role note/finding/vote/workspace checks pass. Inventory remains
**63 domain models,89 routes,56 forced-RLS tables**: no new domain models, seven
core policy reviews still open. Schema/identity, independent browser, institution
and live provider acceptance remain. Numbered delivery/contracts/compatibility:
[council-revision-continuation.md](council-revision-continuation.md).
Protected build-spec unchanged; no operational migrations, credentials, deployment
or merge.

## Next twenty report authoring/configuration batches

All20 implemented: D19 required edited-version report saves, explicit409 conflicts,
proceeding serialization and exact receipt recovery; bounded narrative/frozen
question/current safe evidence/disclosure checks; authoritative history capabilities;
typed personal/shared templates; valid bilingual questionnaire definitions, choices,
conditions and document requirements; bounded secret-safe settings and optional
compare-and-save; retained PostgreSQL notification provenance/first-read evidence.

Full isolated PostgreSQL: **487 passed, 1 skipped**; no model drift; migration
rollback/reapply through0032. Independent runtime-role report recovery and raw
notification denial checks pass; concurrent narrative/settings saves retain one
winner and report conflicts, and closure prevents later narrative publication.
No domain models/routes/RLS tables added: **63 models,88 routes,56 forced-RLS**.
Seven core policy reviews, semantic schema/identity reconciliation and independent
browser/institution/provider acceptance remain. Exact contracts, compatibility and
numbered20 delivery: [authoring-continuation.md](authoring-continuation.md).
Protected specification/accepted question seed unchanged. No operational migrations,
credential changes, merge or deployment.

## Next twenty communication/delivery/integrity batches

Completed all20: typed/replay-safe messages, own first acknowledgement/private
receipts/pagination; live recipient/current-manager checks; obsolete expiry-warning
suppression; fenced leases/bounded exponential retry/digest quiet serialization;
aware numbering/counter RLS/monotonic provenance; malformed search/hit validation/
safe indexing; extraction checksum/DOCX/idempotency gates; byte-route length checks.

Full isolated PostgreSQL: **433 passed, 1 skipped**; no model drift; migration
rollback/reapply through0031, runtime isolation and concurrent message replay pass.
**56 forced-RLS tables /63 domain models /151 approved target;88 routes**. No new
domain models. Seven core policy reviews and provider/identity/schema/browser
acceptance remain. Contracts and specific limits:
[delivery-continuation.md](delivery-continuation.md).
Protected build-spec unchanged; no operational migrations, credentials, deployment
or merge. Queue fencing does not claim external-provider exactly-once delivery.

## Twenty functional continuation batches

Full isolated PostgreSQL suite: **401 passed, 1 skipped**; no model drift;
rollback/reapply through0029, non-owner isolation and concurrent supplement/link
checks pass. Protected build-spec sources are unchanged.

All20 requested batches are implemented: own supplements/capability/version/replay/
safe evidence; capture metadata/provenance; transcript correction/pagination/private
processing status; explicit151-to-adapter review inventory; pending-link validation/
reuse/serialization/authority/cancellation/RLS; private historical publication/typed
payloads; account administration safeguards; request cancellation/revocation.

Detailed numbered delivery and API contracts:
[twenty-batch-continuation.md](twenty-batch-continuation.md).
Reconciliation inventory associates122 approved concepts with candidate adapters
and marks29 unmapped for review; it claims neither field equivalence nor completion.
No new domain model/table was added to chase the count:63 models/151 approved
target remain.55 forced-RLS tables;8 core policy reviews remain.87 routes.
Live provider, full schema/identity and independent browser acceptance, unlimited
capture and institutional wording remain gates. No operational migrations,
configuration/credentials, deployment or merge.

## D20 media continuation batches

Full isolated PostgreSQL suite: **376 passed, 1 skipped**; no model drift;
migration rollback/reapply through0027, concurrent retry and restricted-role checks pass.

- Council report recording/status list with safe original links and honest null
  capture/duration/update facts; no raw diagnostics serialized.
- Exact transcript read and review routes with current reviewer/exact-version
  release; no applicant audio/generated-content access or inherited review.
- New numbered retry attempts retaining original runs/output and one successor/job
  under repeated/concurrent retries; recording finalize remains bound to attempt1.
- Migration0026 adds attempt identity;0027 adds Recording/ProcessingRun/
  TranscriptRevision/TranscriptReview forced RLS and source/run guards. Runtime
  cannot impersonate the missing output processor.54 protected tables;9 remaining
  domain-table policy reviews;63 models/151 approved target;84 routes.
- Contract/limits: [media-read-and-review.md](media-read-and-review.md). Transcription
  provider, D21 metadata/unlimited capture and independent browser/device acceptance
  remain outstanding. No operational migrations, credentials, deployment or merge.

## Next ten consecutive lifecycle and privacy batches

1. Own draft-delete capability and locked expected-version enforcement.
2. Own withdrawal capability and locked expected-version enforcement, retaining
   existing participation and pending-filing rules.
3. Persist original provider checkout URL/expiry with context/provenance guards
   (migration0024 fields,0025 guards); no invented legacy backfill.
4. Safe own frozen-checkout resume projection: one current pending candidate,
   exact declaration/attestation/files, trusted URL/expiry, no new provider write.
5. D19 council report authorship and original-author-only `can_revise` projection.
6. Strict JSON boolean medical scope in PostgreSQL; exact-owner local extraction
   and no own unsubmitted report narrative leakage through revision queries.
7. Safe current contextual communication links, excluding request/consent sources.
8. CallRecord forced RLS, actor/party provenance, retained history and validation;
   closed-case communication preserved.
9. Recording report/proceeding scope and source/finalization guards, literal notice
   acceptance and cancelled-testimony finalization denial.
10. Exact latest transcript version, matching completed processing output, safe
    original and reviewer checks; retained idempotent review/audit.

Contracts and limitations: [filing-actions-and-resume.md](filing-actions-and-resume.md).
Full isolated PostgreSQL suite: **370 passed, 1 skipped**; no model drift;
migration rollback/reapply through0025 and restricted-role permission checks pass.
50 forced-RLS tables /63 domain models /151 approved target;80 routes.13 domain
table policy reviews remain. D20/D21 recording read/retry/routes and unlimited
streaming capture remain deferred dependencies; no transcription success claimed.
No operational migrations/configuration/credentials, deployment or merge.

## Ten consecutive requested-report batches

Completed consecutively for the user's ten-batch request. Contracts are in
[own-request-contract.md](own-request-contract.md).

1. Closed-case privacy: never-sent requests stay private in API and raw RLS;
   closure cancels drafts separately while retaining sent request history.
2. Own request capabilities and opaque request/proceeding/content identity;
   applicant HTTP completion rejects absent/stale fingerprints.
3. Exact published medical-release definition/version with both declaration
   languages; absent/incomplete definitions fail closed without invented text.
4. Explicit acceptance and exact boolean council recipient scope, bound server-side
   to request/proceeding/assessment purpose; no unsupported scope broadening.
5. Separate safe latest CONSENT original, signature format checks, retained signed
   originals, matching-sign retry and own signed-scope recovery projection.
6. Owner-only request file list with latest originals, consent/report purposes,
   honest scan states and safe links; no other-subject/history disclosure.
7. Locked request uploads with fingerprint checks and staff/external exclusion;
   completed/closed uploads and signed-consent replacement rejected.
8. Response shape/required-question checks and exact contextual latest safe report
   originals; consent cannot masquerade as assessment evidence.
9. Exact response retry returns original receipt, including after later closure;
   changed retries fail. Concurrent submit/sign retries create one retained record;
   closure-winning contention rejects a new response.
10. Migration0023: request/report forced RLS, immutable sent content/provenance,
    restrictive source insert policies and capability-scoped external draft/submit.
    Actor/subject/author isolation is tested with a real non-owner runtime role.

Full isolated PostgreSQL validation: **348 passed, 1 skipped**, including migration
rollback/reapply. **49 forced-RLS tables**, **63 domain models /151 target**, **80
routes**. Fourteen domain-table policy reviews and broader identity/schema/provider
acceptance remain. Applicant/council browser integration is independent evidence.
No operational migrations, credentials, merge or deployment.

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

- F15 now has the assignment-specific adapter and approved membership/role
  structures described below. Broader role/lifecycle/authentication reconciliation
  must not be inferred from that narrow assignment capability.
- F12 now has the closed-case intake and acceptance/reopening adapter described
  below. Applicant/council browser integration remains to be accepted.
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

## Reference configuration PostgreSQL policies

- Migration 0020 adds forced RLS to QuestionnaireVersion, ReportQuestion and
  SettingRevision: **42 protected domain tables**. Active applicants can read
  published questionnaires; council can read shared questions; settings and
  unpublished questionnaire versions remain admin/secretary-only.
- Runtime inserts require admin/secretary authority. Settings require the actual
  context actor, an approved configuration key and recursively credential-free
  JSON (including nested arrays and case-insensitive forbidden key names).
  Published questionnaires require their approved-purpose shape and nonempty
  English/Arabic declarations; this does not invent or publish institutional text.
- All three sources retain their existing immutable-update guards, lack runtime
  update/delete policies, and now reject retained-history deletion even by owner
  SQL outside controlled migration rollback. No reference wording was changed.
- Full isolated PostgreSQL suite: **292 passed, 1 skipped**; no model drift;
  reversal/reapplication verified through 0020. Tests include missing/suspended
  context, applicant/council/admin read separation, setting-author forgery,
  nested credential payload denial and retained reference history.
- Broader role reconciliation, remaining domain-table policy reviews, full151-table reconciliation,
  independent browser reacceptance and institutional/provider gates remain open.

## F15 same-person assignment authorizer and recorder

- Migration 0021 adds the approved `tribunals`, `staff_memberships` and
  `staff_roles` tables, preserving the existing Account implementation and stable
  Microsoft-subject checks. Institution, appointer, grantor, activation, expiration
  and revocation are retained; no historical person/role/appointer is invented or
  backfilled. There are now **63 domain models / 151 approved target tables**.
- Assignment checks are deliberately specific: an existing admin with an explicit
  presidency can authorize and record the same assignment; an existing president
  with explicit administrative assignment authority can do the same. Both actual
  IDs remain in CaseAssignment even when equal. Legacy roles still work. These
  extra role records do not grant system settings, role provisioning, decree
  issuance, or new dual-role approval powers elsewhere.
- `CTM_TRIBUNAL_ID` must explicitly identify the approved current institution.
  Its normalized value enters transaction-local context from server settings,
  never browser roles/headers. Missing/mismatched configuration, inactive/future/
  expired membership, suspended accounts and revoked grants cannot supply extra
  assignment authority. Legacy single-role behavior does not require a new grant.
- Existing-admin-only `GET/POST /api/council/tribunals/` provisions reviewed
  institution metadata `{code,name_en,name_ar?}`. It does not select the current
  institution or change deployment configuration. No actual institution was
  provisioned here.
- Existing-admin-only `GET/POST /api/council/assignment-authorities/` retains grants;
  POST takes `{account_id,tribunal_id,role}` with president/admin/secretary (default
  president), only for an existing active council account. Provisioning is audited
  and idempotent for the current membership/role. `POST .../{role_id}/revoke/`
  retains the grant and actual revoker audit; grants are never reactivated or
  rewritten. This is not general council role-management acceptance.
- Council member rows now include `can_authorize_assignment` and
  `can_record_assignment`. Assignment UI must use those flags instead of treating
  the legacy `president` boolean as assignment authority. The legacy boolean is
  retained for current decision/decree contracts; no inferred approval change.
  Council case data includes chronological `assignment_history` with member,
  president, actor IDs/names/time. Applicant projections omit this internal history.
- All three new tables have forced RLS (**45 protected domain tables**) and guarded
  provenance/retention. Raw runtime writes cannot forge a grantor/appointer, enroll
  an applicant, rebind membership, reactivate a revoked role or assign using missing,
  revoked or cross-tribunal authority. SQL rechecks assignment authority at write.
- Full isolated PostgreSQL suite: **303 passed, 1 skipped**; no model drift;
  inventories regenerated (**78 routes**); reversal/reapplication through 0021.
  Browser integration, real institutional configuration/grants and general role
  lifecycle acceptance remain with governance. No operational migrations,
  credentials, deployment, merge or actual role grants were changed.

## F12 / AS-F12 linked spouse's first filing after closure

- The direct-owner addendum supersedes the earlier closed-match refusal: an
  already-linked canonical person/account with no prior formal petition for this
  case can start the normal petition API with `case_id`. Application adds the
  approved `origin` attribute, using `closed_case_intake` for this route, preserving
  petition purpose/questionnaire/declaration. No DOB-only access or new spouse
  mapping is inferred. Existing first filers must use the appeal route.
- Applicant case detail exposes `can_start_petition` and `can_start_closed_intake`.
  The resulting application exposes `origin`, `requires_new_information` and the
  usual readiness/version/payment flags. Nonempty `new_information` is required
  before checkout/submission; frozen candidate/recovery and one filing fee apply.
- Submission retains the formal answers/manifest/signature and linked spouse but
  keeps `proceeding_id=null`, case closed, no new proceeding/number/open claim and
  no participation activation. Existing shared spouse name/reference/canonical
  identity remain unchanged. Pending filing facts do not update the shared case
  profile or notify the other spouse. Council reviewers/manager receive intake.
- Council `GET /api/applications/?state=council_consideration` includes pending
  appeals and closed first filings. The ordinary completeness queue excludes this
  route. Closed-case agenda/hearing/attendance capabilities accept either type of
  pending council filing; no substantive write to the closed proceeding is enabled.
- Staff detail exposes retained supplements/disposition/eligible hearings and
  `can_record_result`. `POST /api/applications/{id}/closed-case-result/` accepts
  `{hearing_id,result:accept|decline,explanation?}` after a held assigned Part2
  presentation after submission. The legacy appeal result/supplement services
  share this logic without changing the petition's purpose. Existing
  `POST /api/appeals/{id}/additions/` supports owner-only append-only pending facts.
- Acceptance checks formal new information, activates the actual filing spouse,
  rechecks all participating canonical-person claims, and creates or joins one
  open appeal/reconsideration proceeding on the same case. A sibling appeal joins
  that proceeding. Prior proceedings/answers remain locked. A conflict retains
  the pending filing/payment and never closes or overwrites another case.
- Decline or owner withdrawal preserves closure and avoids other-spouse notices.
  Withdrawal after accepted first petition retains the council result and applies
  ordinary active-petition closure rules. A controlled withdrawal/acceptance race
  verifies the waiting acceptance cannot revive a withdrawn pending filing.
- This is an adapter over the existing58-model architecture: legacy
  AppealSupplement/AppealDisposition store shared reconsideration facts/results;
  no claim is made that their legacy names/FKs replace the approved151-table
  appeal structures or that this addendum rewrites protected schema sources.
- Migration0022 retains origin/source/version/single-submission guards and adds
  forced RLS to those two retained tables (**47 protected / 63 domain models**).
  A narrow transaction context permits only council's filing-status result update;
  actual actor/hearing, source ownership, active proceeding and all case claims
  are verified before disposition insertion. Raw writes cannot fabricate a result,
  reset a conclusion, edit submitted intake answers or rebind its old proceeding.
- Full isolated PostgreSQL suite: **317 passed, 1 skipped**; no model drift;
  rollback/reapply through0022; **79 routes**. Tests cover real HTTP/read contracts,
  paid-candidate finalization (mock provider, no real charge), owner/non-owner
  privacy, raw guards, shared reopening, conflict rollback and lock contention.
  F12 browser acceptance and broader schema/identity reconciliation remain open.

## Own released-decree read contract

- Applicant `GET /api/cases/{id}/` now always returns `released_decrees:[]` or
  current own release rows: `{id,reference,language:en|ar|bilingual,released_at,
  signed_file:{id,name,scan_state:'clean',download_url}}`. Stored `both` maps to
  `bilingual` in this own projection. Council decision/release contracts are unchanged.
- Each row requires issuance, the exact authenticated recipient's latest release
  event and current authorized safe access to the exact stored signed PDF. No
  unreleased/revoked/other-recipient history, raw storage keys, unsigned replacements
  or council decision internals are exposed. A current unsafe scan hides the link.
- The case detail response is private/no-store. The lookup follows the released
  signed file's case binding, avoiding applicant joins through council-only
  decision rows. Existing forced RLS is retained, not relaxed for the read projection.
- Full original, Range, HEAD and inline preview bytes are tested before withdrawal;
  every retained URL is denied afterward and the list becomes empty. Independent
  runtime-role tests verify list appearance/disappearance under existing policies.
  No decree issuance/release mutation endpoint was added for applicants.

## F20 / C5 hearing applicant update timing

- `POST /api/hearings/{id}/outcome/` accepts `email_timing:immediate|after_session`
  and `session_id` on the first applicant update, delegated to the existing private
  message validation. A selected session must be planned; invalid first-send
  settings roll back the outcome/message together. Default remains immediate.
- This field controls email timing; portal visibility retains existing private
  message semantics. Deferred jobs wait for the selected session to close and
  retain the existing send-time closure/rebinding checks. No delivery is fabricated.
- Revision timing inputs never resend, reschedule or rewrite the first message.
  Advisory serialization on the hearing prevents concurrent first-save requests
  from creating duplicate applicant messages. Outcome revision history is retained.
- Automatic updates from closed-case hearings without an open proceeding target
  only the current pending filing owners; they do not reveal a private pending
  appeal/first filing to another spouse. Ordinary open-proceeding updates retain
  their established registered-spouse recipients.
- Full isolated PostgreSQL suite: **324 passed, 1 skipped**; includes exact own
  certificate bytes/revocation, restricted-role projection, first-email timing,
  invalid-timing rollback, concurrent revision and pending-spouse notice isolation.
- Current remaining work includes own request/consent response contracts and
  concurrency identity, **16 existing domain-table policy reviews**, broader
  schema/identity/role reconciliation, independent F12/F15/browser integration,
  approved institutional content and live provider acceptance. Draft-only; no
  operational migration, institution/grant setup, credentials, deployment or merge.
