# Applicant fields and repeat-section mapping

Pinned integration candidate: `104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc`.
This is a requirement-to-source reconciliation, not publication of a new questionnaire.

[Download JSON](result.json) | [Field CSV](fields.csv) | [Validator observations](validation-probes.json)

## Completed

- Enumerated90 semantic field targets, five repeat-section families, ten contextual file/attestation requirements and all24 AF dispositions. Counts are audit rows, not a question count, completeness percentage or proof of schema equivalence.
- Each field has source path/line, target contract table, candidate seed binding, validation/Unknown policy and exact dependency. Six flat seed bindings are semantic candidates, not confirmed one-to-one mappings of all approved questions.
- Preserved accepted additions and narrow overrides: child gender/lives-with and Unknown; spouse parish/confessor/immigration/residence; marriage diocese; blood relationship only; priest-name-only counseling; prior-marriage spouse/permit and known spouse history; repeated prior applications; per-order actual court/reference/status/copy.
- Excluded rejected expansions, spouse lives-with, town of birth, baptism certificate, additional civil/finality questions, and interview-only AF08/09/12/13/14. AF02/03/16/17 are narrative guidance rather than duplicate compulsory questions. AF11 is read with the later existing-date/CDD clarification.
- The59 accepted English interview questions remain a separate question library. They are not59 applicant fields. No invented Arabic or sample declaration has been published.
- Generator uses the pinned schema table set and source hashes, reads actual seed AST and verifies its six codes. Reproduce with `uv run python scripts/build_applicant_field_mapping.py` and `uv run python scripts/probe_applicant_field_validation.py`.

## Unfinished

`tribunal/management/commands/seed_reference.py:26-54` creates an unpublished petition definition with only `first_name`, `last_name`, `birth_date`, `gender`, `marriage_date`, `grounds`. None of these six has label_en/label_ar; the current frontend correctly refuses such an incomplete definition. The seed is not evidence of actual deployed database configuration. The other84 mapped semantic targets and all five repeat families are absent from that reference definition. Some flat fields combine semantic concepts and need exact approved bindings, not mechanical code generation.

For every row, the CSV explicitly reports missing seed labels and binding status. Obtain versioned English/Arabic labels, help, choices, requiredness and conditional branches from the institutional content/configuration owner. Exact approved display wording cannot be inferred from semantic identifiers or this mapping. Original prototype-to-data labels and AF decisions are evidence; neither the old prototype nor English interview bank independently grants institutional publication approval.

The generic applicant editor supports text, textarea, date, choices, boolean, multiselect and one-level item_fields records with UUIDs for new rows. It does not establish that the five approved sections have been configured. Child-only checks do not cover every repeater. Structured address fields require approved flat binding or explicitly designed grouping; arbitrary nested repeat sections are currently rejected. Answer-state semantics (Unknown/not provided/not applicable), sanctioned dates and choices, conditional Other text, date order, and per-row contextual evidence need explicit configuration/validation contracts. Do not set Unknown globally.

Normalized schema targets come from the locked build contract. Current storage candidate is AnswerRevision.answers JSON. This is not proof that JSON names implement normalized person/marriage/separation/repeat/answer tables. Older prototype map table names such as application_statements and application_prior_proceedings do not exist in the current contract; this mapping uses application_answers and application_prior_records instead and preserves source provenance. Backend owns required model/migration and policy changes.

## Blocked: exact dependencies

| ID | Dependency / owner | Evidence / required outcome |
| --- | --- | --- |
| F01 | Institutional content and backend configuration owners | Reviewed bound EN/AR application labels/help/choices/declarations, complete definitions and publication receipt. All90 target rows identify absent seed labels; these are not90 necessarily distinct questions. |
| F02 | Backend issue2 validator owner | Nested item_fields validation and row-object/UUID uniqueness checks. Five reachable list-definition gaps plus one unsupported textarea-definition vocabulary mismatch observed; see validation-probes.json. Fix server-side before accepting full repeat journeys. |
| F03 | Backend issue2 schema/identity owner | Map JSON fields and stable repeat IDs to approved semantic structures and explicit answer states; identify actual migration requirements. No frontend-owned migration is proposed. |
| F04 | Backend/document-contract plus content owners | Confirm per-prior-marriage permit binding; each reported RO already requires its own context and copy, but field code is number in current backend versus semantic case_number. Publish exact aliases rather than guess. |
| F06 | Backend category and institutional content owners | Confirmed decisions98 defines MC church/CMC civil; backend DOCUMENT_LABELS189-190 defines MC generic marriage/CMC church. Both required categories are retained; resolve meanings before approved form/visual acceptance. |
| F05 | Institutional wording owners | Approved signed declaration/professional release and equivalent Arabic text; synthetic acceptance content is not authorization. |

## Validation observations

At pinned candidate, actual `validate_answers` accepts malformed nested required/date/choice values, non-object repeat rows and duplicate row IDs (five list/item_fields expectations). It also accepts a non-string textarea value, but `configuration.py:205-220` rejects textarea definitions at publication: that sixth observation is an unsupported-definition/defense-in-depth vocabulary mismatch, not the same reachable final-validation exposure. The frontend supports textarea while the publisher does not. Top-level required/date/boolean checks reject invalid values, and a valid nested Unknown sample is accepted. These are direct actual-function probes without a database or HTTP; they are not a demonstrated authorization bypass. Submission additionally calls `validate_petition` (child gender/lives_with truthiness, identity/grounds/future dates) and `required_documents` (RO metadata/copy checks). Those compensating checks must not be omitted from severity interpretation. Saved drafts retain arbitrary JSON by design; incomplete drafts are allowed. The gap is authoritative final nested/type validation, not the mere ability to save an incomplete draft.

## Awaiting acceptance

Fresh applicant journey against the unmodified integrated104e4fd archive passed all74 actual Django API/browser groups;92 frontend tests pass. [Integrated API evidence](integrated-api-result.json). The runner did not overlay applicant modules or apply the standalone shell patch. PostgreSQL runtime-role/full approved repeat journey, bilingual field-by-field review and final visual acceptance remain open. A passing synthetic journey can establish plumbing only; missing approved content remains blocked.

Initial attempt launched the archive from the applicant directory and mixed Python module origins; its apparent missing URL attribute was a harness failure. Tracker corrections were posted immediately. The runner now requires archive cwd and verifies the imported models originate there. The original false product-defect report is not retained as an open defect. Integrated testing also updates selectors for the current navigation semantics and duplicate sidebar/content Back controls without changing product sources.

Independent review resolved the missing civil-certificate/MC mapping and the textarea exposure distinction; no further concrete findings. Reproduce exact integrated run in PowerShell: set CTM_APPLICANT_INTEGRATED=true and CTM_APPLICANT_BACKEND_REF=104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc, then run `uv run --group browser python scripts/browser_applicant_api.py`. This mode archives that commit without overlaying product code or applying standalone patches.
