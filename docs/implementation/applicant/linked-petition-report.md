# Applicant stream: linked first-petition completion checkpoint

Completed within applicant frontend ownership. Shared/backend sources, protected specification and migrations are untouched. PR5 remains draft. No merge or deployment.

## Completed

- Added first-petition entry to applicant-owned applicant-appeals.js. It requires literal server can_start_petition, submits kind=petition with the exact case ID, and accepts only a valid same-case petition response. Concurrent starts are blocked, access failures lock retry, and late acknowledgements do not navigate after leaving. Existing appeal and reopened-sibling behavior remains available.
- Replaced the second submitted-filing database fixture with actual start/save/upload/separate authorized waiver/browser declaration and submission. Own draft/history privacy is checked in both directions; the first withdrawal retains the second filing, and the last withdrawal closes the case.
- Verified a linked never-filer can start a first petition from a closed case, save new information, supply required originals, obtain an explicit separate waiver and submit through the browser. Submission keeps the case closed and adds no proceeding. Account/party verification, historical closed case and content are explicit fixtures; this is not identity onboarding, decree issuance or institutional publication acceptance.
- Proposed minimal current-integration shell hook in linked-petition-integration.patch. It also gives petition/appeal/decrees/requests distinct case-qualified React keys. Adding the entry exposed existing duplicate selection keys that left three stale certificate panels; the full strict certificate-revocation regression now passes without weakening its locator.
- Kept the older standalone shell proposal in sync. Governance must choose the appropriate patch for its exact candidate; do not apply both to one shell.

## Verification and provenance

- 94 frontend tests pass. Two new controller tests failed before implementation and pass afterward.
- Six pinned Plenix browser fixture groups pass, including EN/AR390px, no inline styles/overflow, exact routing, capability absence and late acknowledgements.
- Nine standalone proposed-shell fixture groups pass.
- Unmodified integrated104e4fd:75 actual Django API/browser groups pass after strengthening the second filing. [Base evidence](linked-petition-base-api-result.json).
- Review candidate based on104e4fd plus only applicant-appeals.js and linked-petition-integration.patch:76 actual API/browser groups pass, no page errors. [Candidate evidence](linked-petition-api-result.json). JSON records exact module/patch SHA256 captured before the test run. This is a local review assembly, not a published integration commit.

Reproduce with `uv run --group browser python scripts/browser_applicant_linked_petition.py`. The script archives the pinned commit, overlays the named applicant module and applies only the minimal shared-hook proposal in an ignored temporary directory. The existing runner checks cwd and imported model origin to prevent mixed source acceptance. SQLite/synthetic sessions, controlled scan policy and fixture waivers do not establish PostgreSQL/runtime-role, real payments/providers or approved wording.

Independent review found no further concrete findings after correcting clean-checkout directory creation and hashing the exact copied candidate bytes. An initial isolated migration attempt failed before browser execution with a Django Options/get_models setup error; a fresh archive rerun completed. No product workaround was made. Review-candidate patch line-ending application failure was corrected in the patch artifact before successful verification.

## Unfinished / blocked by named dependencies

The original applicant stream cannot honestly be marked fully accepted while these remain:

| Item | Exact dependency / owner |
| --- | --- |
| Full approved form | Institutional content + backend configuration owners: reviewed versioned EN/AR fields/help/choices/conditions/declaration. Source seed is only six unpublished unlabeled fields. The90-target/five-repeat/24-AF mapping is complete as source reconciliation; no sample wording is approved. |
| Final repeat validation | Backend issue2: five actual list/item_fields validation gaps. Textarea is a separate frontend/publication vocabulary mismatch because publisher rejects it. |
| Semantic data and evidence | Backend/schema owner: JSON versus normalized schema/answer-state equivalence, exact RO number aliases and per-prior-marriage permit binding. |
| Certificate meanings | Backend/content owners: MC church / CMC civil in confirmed decisions versus generic MC / CMC church in adapter labels. Both required certificates retained in mapping. |
| Institution release/signatures | Institutional owners: reviewed declaration/release/decree content, actual signature and issuance acceptance. |

[Full field mapping and exact blockers](field-mapping/README.md) | [Download mapping JSON](field-mapping/result.json)

## Awaiting acceptance

Governance must integrate the minimal hook/module while preserving its council expected_version and UI fixes, then record and test the exact successor SHA. Independent QA15 owns council report rechecks; these applicant tests do not close that work order. Full approved-content/repeat PostgreSQL journey, live auth/payment/email/scan/storage and institutional EN/AR/mobile acceptance remain separate. No credentials or institutional decisions were invented to bypass these dependencies.
