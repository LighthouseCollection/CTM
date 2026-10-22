# Five applicant repeat families: technical verification

All eight browser scenario groups pass against applicant.js from4611b4c with the real pinned Plenix0.58.0 CDN. [Download JSON](repeat-sections-result.json). The fixture captures and serves the exact module bytes whose SHA256 is recorded in the result, along with the source commit. No production code or shared/backend sources changed in this checkpoint.

| Family | Technical fixture fields |
| --- | --- |
| Children | first_name, last_name, birth_date, gender, lives_with |
| Restraining orders | court, number, status |
| Prior applications | record_date, council_or_diocese, outcome |
| Prior marriages | spouse_name, ecclesiastical_permit |
| Counseling priests | priest_name |

These are explicit synthetic bindings and bilingual fixture labels, not an approved versioned form or a proposal to publish these codes. In particular, prior-marriage permit text is only a test value: this does not prove an uploaded permit link. RO number/case_number alias reconciliation and exact approved choices/Unknown policy remain backend/content dependencies.

Verified in the browser for every family: edit an original row, add a row, assert each new saved field value, retain original UUID/opaque source metadata and untouched row/fields, review in Arabic, remove the middle row, save, deep-compare surviving rows and recheck every reloaded visible field. Unknown root values remain exact, including false/null/zero. Failed save does not mutate saved fixture state; dirty local edits survive Arabic390px language switching, with no runtime inline styles or horizontal overflow and no automatic retry. Missing nested Arabic wording blocks editing instead of inventing a translation or mutating saved values. No object-to-string coercion appears in review.

Independent review identified a preservation-assertion gap (new rows/survivors originally checked mainly by IDs). Explicit field-value and full survivor comparisons now close that gap; all eight groups passed afterward, and recheck found no further concrete findings.

Reproduce: `uv run --group browser python scripts/browser_applicant_repeat_sections.py`. Screenshots and temporary logs stay under ignored .tmp/applicant-repeat-sections. This suite uses a synthetic API and cannot establish backend final validation, required document acceptance, institutional wording or PostgreSQL/RLS behavior. Existing actual-Django76-group candidate evidence remains in linked-petition-api-result.json; it was not relabelled as this fixture run.

## Status and remaining dependencies

Completed: five-family applicant UI preservation and interruption verification. Pushed status is recorded in issue1 at this checkpoint. Unfinished: approved full bound form publication. Blocked: institutional EN/AR fields/help/choices/conditions/declarations, backend authoritative repeat validation and textarea vocabulary alignment, schema/answer-state/evidence bindings and MC/CMC category reconciliation. Exact owner requests have been posted to backend issue2 and institutional-content issue12; implementation cannot substitute fixture wording for approval. Awaiting acceptance: governance minimal-hook integration, full approved-content PostgreSQL journey, live services and institutional visual review. No merge or deployment.
