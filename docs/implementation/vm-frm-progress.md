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
