# VM-FRM backend progress

Issue: https://github.com/LighthouseCollection/CTM/issues/2

## First slice: applicant filing contract

Own application list, create and detail responses now include the bound
`questionnaire` (`id`, `version`, `published`, `definition`, `declaration_en`,
`declaration_ar`), `duplicate_hold`, latest `return_instructions`, and boolean
`can_edit`, `can_checkout`, `can_submit`, `can_resubmit`.
These fields are supplied only to the application owner; existing submitted
council projections are preserved. Drafts remain inaccessible to council.

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

Existing upload route remains `POST /api/uploads/`. The proposed application
file listing and council projections in issue #2 remain subsequent slices.

## Validation and remaining work

- 21 filing contract regressions pass on SQLite in an isolated container.
- Full PostgreSQL suite, including existing non-owner RLS tests: in progress.
- No schema changes; preserve existing models and protected 151-table contract.
- Full schema reconciliation, outstanding policies/grants, council projections,
  file listing contract and live payment/email acceptance remain incomplete.
- No payment/email credentials were configured or provider success claimed.
- Git CLI credentials are unavailable. The independent shallow application
  checkout was reconstructed from connector source and verified against main
  `da99591136f2136c0adfcfe7f443ca3384e8b948`; binary historical reference
  documents are omitted locally. Publication uses the GitHub connector with
  current main as parent. Prototype history is separate.
- No operational migration, credential change, deployment or merge performed.
