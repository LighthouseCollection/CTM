# Next five applicant tasks

Implemented against the approved architecture without editing backend, protected
specification, shared shell source, migrations or institutional wording. The shared
integration remains a proposed patch. These five items are partial until the stated
backend/institution dependencies are resolved; PR #5 stays draft.

| Task | Concrete progress | Remaining |
| --- | --- | --- |
| Request responses / professional release | Bound intake response editor prepared with review, exact question keys, version payload, navigation/unload protection and uncertain-result lock. Previously sent closed requests remain readable. | Own capability/concurrency contract; approved release definition, signed scope and request-scoped originals. No professional consent fabricated. |
| Supplements / decrees | Actual owner supplement POST preserves submitted answers and rejects staff authorship. Actual explicit decree release and withdrawal control retained full/range/preview/HEAD URLs for an exact stored synthetic PDF; delivery is no-store. | Own supplement history/capability and own active decree release list. Real signing/issuance are separate. |
| Checkout recovery | Actual own payment history blocks fresh checkout/signature for unresolved/unknown attempts. Prepared resume displays original snapshot and opens only the matching existing safe URL, without POST. | Original immutable candidate/declaration/attestation and authorized resume projection. Missing data keeps payment blocked. |
| Deletion / withdrawal | Distinct explicit confirmations, server capability gates, version payloads, single-attempt lock and parent competing-write protection, including delayed acknowledgement. | Own action capabilities/version enforcement and joint-case closure acceptance. Returned filings never use draft deletion. |
| Bilingual forms | Technical audit command with exact JSON pointers and downloadable reference inventory. Technical readiness never claims institutional approval. | Approved full bound wording/translations and nested backend validation. The reference seed has 59 English questions and no Arabic wording. |

## Blocking privacy finding

Backend f0e21b4 changes unsent staff requests from draft to closed during actual
case closure. The applicant endpoint excludes only draft, exposing the unsent
instructions/questions. The diagnostic reproduces this and the default real-API
suite now fails its closure gate. The frontend rejects a missing sent timestamp,
but that cannot repair API disclosure. Reported to backend owner in GitHub #2.

Previously sent closed requests must remain visible; never-sent drafts must remain
private. An explicit `CTM_APPLICANT_REQUEST_CLOSURE_AUDIT=0` run is baseline-only,
not full acceptance. Preserve the failing regression until a backend fix is verified.

## Validation

59 unit tests, 9 new batch browser groups, 9 shell groups, 19 base editor groups
and 4 request-reader groups pass. The real-API run passes 34 preceding groups,
then fails the new closure privacy gate. Fixtures use isolated SQLite, synthetic
accounts and a synthetic PDF; they do not establish real provider, signed-release,
institutional language, PostgreSQL or deployment readiness.

Run a candidate wording audit without publishing or modifying it:

```sh
node scripts/audit_applicant_forms.cjs application-projection.json readiness.json
```

The output omits answers and retains `institutional_approval:not_verified` even
when the technical definition is complete.

- [Download batch JSON](next-five-result.json)
- [Download closure privacy evidence](request-closure-privacy-result.json)
- [Download reference wording inventory](bilingual-source-inventory.json)

Local typing during read-only capability refresh is now preserved. A deliberately delayed projection read proves saves/filing stay blocked until it settles; server can_edit and action locks still govern editing/writes.
