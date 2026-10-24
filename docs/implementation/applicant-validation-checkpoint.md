# Backend response to applicant field-mapping checkpoint482af31

**Final isolated PostgreSQL: 599 passed, 1 skipped.** No model drift; migration
rollback/reapply through0039. Protected architecture sources unchanged.

Scope: issue #2/backend; consumes applicant issue #1's pinned mapping and probes.
Does not publish a questionnaire, edit UI/shell modules or approve invented content.

## Completed implementation

- `validate_answers` recursively validates configured `list.item_fields`: rows must
  be objects with distinct stable UUID `id` values, including case-normalized
  duplicate detection. Required text, date, choice, boolean and nested list types
  are checked in each row. Conditions resolve within the same row. Unknown is
  accepted only where the published choices explicitly include that code.
- Publisher validates nested field definitions, local conditions/cycles, supported
  types and choices. Both publisher and final validator accept `textarea` as text;
  objects cannot masquerade as narrative strings. Configured primitive list choices
  are checked. Bounded JSON validation still applies.
- Draft saving remains permissive for incomplete answers. Final submission and
  checkout call the authoritative validator; no sample wording or choices are
  substituted for approved definitions. Existing signed snapshots are untouched.
- New-case identity is bound to eligible current filing answers in migration0039:
  marriage date and sorted spouse birth dates cannot be rebound during insertion.
  The existing initial-filing eligibility guard remains in place. Core isolation
  tests now assert that all seven reviewed tables contain actual records before
  checking anonymous denial, avoiding empty-table success.
- Both MC and CMC are mandatory for new petitions regardless of an incomplete
  questionnaire's configured categories. Confirmed-decisions98 defines MC as church
  and CMC as civil. English labels follow that source. The existing church Arabic
  label moves with MC; CMC retains the existing generic marriage-certificate Arabic
  wording pending approved exact civil wording. No new Arabic text is invented.
- Each restraining-order row's canonical reference is `case_number`; legacy `number`
  is accepted as an alias. If both are present they must agree exactly. Court,
  reference and status must be nonempty text and cannot be Unknown. Original answer
  keys remain frozen; no alias rewrite/backfill. Copy binding remains category RO
  plus attachment.context equal to the row's saved id, with a current clean file.
  Alias support does not relax document scope or medical/file permissions.
- Defensive petition validation returns validation errors for malformed identity,
  grounds and child row shapes instead of relying on truthiness or incidental
  attribute/type exceptions. Published definitions remain responsible for exact
  approved nested choice sets and conditional questions.

## Binding and normalized migration plan

| Current immutable JSON evidence | Approved target / required migration |
| --- | --- |
| AnswerRevision and frozen submission | application_revisions: retain actor, questionnaire version and signed/correction distinction; explicit adapter/backfill mapping required. |
| prior_marriages[].id | application_repeat_entries id; bind to its application/section and retain across revisions; never use row position as identity. |
| prior_marriages[].spouse_name / ecclesiastical_permit | application_prior_records with kind=prior_marriage, revision_id and entry_id; nullable text fields per locked schema, UNIQUE(revision_id,entry_id). |
| configured per-field state | application_prior_records.answer_states / application_answers.answer_state; approved codes required, never derive Unknown from empty JSON. |
| children[] UUID and configured facts | application_children with revision_id/entry_id unique pair, names JSON, nullable date/gender/lives_with and explicit answer_states. |
| restraining_orders[].case_number or legacy number | Canonical court-reference evidence remains attributed to each saved repeat UUID and exact file context; preserve aliases/original JSON during a future typed backfill. |

The normalized roots are not yet implemented. Migration must preserve every source
revision, actual actor and original repeat UUID, quarantine missing/duplicate legacy
IDs, and add same-application/revision foreign keys plus retained-history triggers.
RLS must inherit the existing own-draft/formal-submission/returned-correction rules
through the bound revision; a child-table SELECT grant cannot reveal a hidden
revision. Add dual-read comparisons before any switch; no destructive backfill or
operational migration is part of this checkpoint.

## Unfinished and exact dependencies

- Per-prior-marriage binding is `prior_marriages[]` with stable UUID `id`,
  `spouse_name` text and `ecclesiastical_permit` text. The locked schema's
  application_prior_records explicitly defines ecclesiastical_permit as nullable
  text, not boolean or attachment. Final petition validation rejects malformed row
  identities/shapes and non-text spouse/permit values even before a full definition
  is published. Missing optional values retain absence; configured requiredness,
  allowed choices and Unknown policy still require the approved content definition.
  No permit upload category or global Unknown behavior is introduced.
- Normalized `application_prior_records` and identity/family structures remain
  migrations identified in schema-gap-review.md. JSON/UUID support alone is not
  accepted normalized schema equivalence. No content-driven table was invented.
- Unknown, absent, not provided and not applicable are not silently collapsed or
  globally converted. Currently absence/null/empty can remain in incomplete drafts;
  final requiredness and explicit allowed choices are configured per field. A richer
  normalized answer-state vocabulary requires approved mappings and guarded data
  migration, preserving original snapshots.
- Exact Arabic civil-certificate label and all missing full-form labels/help/
  declarations remain institutional content dependencies. No approved publication
  or bilingual visual acceptance is claimed.
- Existing attachments could have been selected using the old incorrect display
  labels. Operator/institution must review category evidence; do not silently swap
  stored MC/CMC categories or certify historical content based on a new label.

## Acceptance and migration implications

0039 is backend-owned SQL trigger enforcement on the existing Case table; it adds
no domain model, route, role grant or change to the protected151-table specification.
Rollback/reapply is included in PostgreSQL regression tests. Recursive/alias checks
use existing immutable AnswerRevision JSON and do not need a data rewrite. Tightened
final validation may require a legacy incomplete draft to gain stable row IDs or
correct malformed values before checkout; accepted prior signed evidence is retained.

Awaiting governance's serial integration and applicant rerun on that exact successor
SHA, with actual approved repeat definitions. Synthetic fixtures prove validation
behavior only. Live credentials are a separate dependency matrix.
