# Applicant continuation: backend validation and row-local conditions

Pinned backend: ff8571720ae1940034832bfbb69ddf9503f94c0e. Review candidate preserves integrated104e4fd shared UI/report-version fixes, overlays the captured applicant editor/linked-petition modules and applies only the named minimal shell proposal. This is not a merged/published integration successor.

## Completed and independently checked

- 17 direct actual-validator cases pass against ff85717. Rejection cases supply otherwise-valid row UUIDs and assert the failing field path, so an ID failure cannot mask broken required/date/choice checks. The old pinned104e4fd validator matches only6 of the17 outcomes. These are direct-function observations, not HTTP/publication acceptance. [Comparison JSON](field-mapping/backend-validation-comparison.json).
- 30 backend tests in tests/test_recursive_answers.py pass independently in the disposable ff85717 SQLite archive. They cover recursive/textarea publication and validation, document aliases/certificate meanings and prior-marriage technical bindings. The backend's599 PostgreSQL result remains separately reported evidence, not a test count independently rerun here.
- 76 applicant actual-Django/SQLite API/browser groups pass against the explicit ff85717/104e4fd candidate. [Candidate JSON](backend-validation-api-result.json) records backend/frontend refs and exact overlaid editor/module/patch hashes. One initial invocation exited without a captured result; the successful rerun is the acceptance evidence.
- 96 frontend tests pass. Two new condition tests failed before implementation. applicant.js now permits configured conditions local to one repeat row, renders child fields using that row's answers, and rejects cycles at top level or within a repeat definition. One repeat-record level remains supported; nested repeat records are still rejected rather than flattened or guessed. Cross-row/outer references do not become valid local references.
- Nine pinned Plenix browser fixture groups pass, including independent row0/row1 condition visibility and exact hidden-value restoration, all five repeat families, interruption preservation and Arabic390px without runtime styles/overflow. A generic fixture-only conditional detail is not an added approved application question. [Browser JSON](row-condition-browser-result.json).

Nine proposed-shell fixture groups also pass. Independent code review found no concrete findings; it inspected the row-local scope, cycle rejection, hidden-value preservation and pinned candidate provenance.

The repeat-browser JSON source_commit identifies the base HEAD at execution; module_sha256 identifies the tested working-tree editor bytes included in this checkpoint.

## Blocker reconciliation

[Download resolution JSON](field-mapping/backend-resolution.json).

| Earlier blocker | Current status | Still required |
| --- | --- | --- |
| F02 recursive final validation | Five earlier repeat gaps now covered by passing exact probes; textarea vocabulary aligned | Approved per-field choices/requiredness/Unknown, full runtime acceptance |
| F04 document aliases/prior marriage binding | RO canonical case_number plus exact legacy number alias; prior_marriages UUID/spouse_name/nullable-text ecclesiastical_permit clarified and tested | Institutional field/representation acceptance and guarded normalized backfill; no permit-upload requirement invented |
| F06 MC/CMC meanings | MC church and CMC civil English meanings align with confirmed decisions; both mandatory | Exact approved Arabic civil wording remains pending; generic existing Arabic is not institutional sign-off |
| F01/F05 approved bilingual publication | Still blocked on institution/configuration owners | Reviewed versioned EN/AR labels/help/choices/branches/declarations/releases, not sample text |
| F03 normalized schema | Still unfinished with backend/institution owners | Approved semantic/answer-state equivalence and guarded migrations; JSON preservation alone is not equivalence |
| PostgreSQL/integration | Still awaiting recovery and exact-candidate acceptance | Prior owned container cleanup, older403/404 contract/stall investigation, governance successor integration and runtime/live/visual tests |

The historical mapping/probe snapshots retain their original refs and findings. This successor reconciliation updates status without silently replacing baseline evidence or claiming all earlier findings persist at ff85717.

## Boundaries and next step

No shared product source, backend service, migration, protected specification or institutional text was edited. Shared loading/navigation remains a governance patch. The already-stuck owned PostgreSQL container was not replaced with another container, and no shared Docker engine or existing service was restarted. The previous stall's cause remains unverified and is not asserted as a failure reproduced at ff85717.

Governance can integrate this applicant checkpoint with the new backend while preserving existing council/UI fixes, then rerun exact successor checks after operator recovery. Full approved form publication remains blocked by missing reviewed content; this checkpoint does not invent it.
