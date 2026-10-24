Current validation: **863 PostgreSQL passed, 1 skipped**; no model drift; migration rollback/reapply through0049. Nineteen new paper-source/permission/recovery regressions included; SQLite paper/receipt endpoint contract separately passed. Integration/UI/independent acceptance remains pending.

# Council completion from an external priest paper original

Backend issue #2 / council C05;0049_external_paper_completion after0048.
No frontend/shared shell or approved question/content source is edited.

POST `/api/requests/{id}/paper-completion/` accepts `file_id`,
`completion_date` (received date, canonical YYYY-MM-DD, no later than the project
America/Los_Angeles date), and mandatory existing `expected_version` request hash.
Only an existing case writer may record the response. This is council recording
of a priest's paper, not applicant intake or a council-authored priest narrative.

The request must be sent external_priest with an open case/proceeding. The file
must be the current PDF version of categoryREPORT, already bound to the exact
request/case/proceeding, application-null, owner-null, council-visible and with
its latest scan clean. Existing upload API supports that source using request_id
and categoryREPORT; pending/rejected scans cannot complete. No scan/OCR result is
invented. Council UI must orchestrate upload→technical readiness→completion as one
user workflow; this API does not claim automatic background completion after upload.

The report stores methodpaper, actual council recorder as author, caller-supplied
received date, revision actor and only the original file ID in answers.files.
The priest identity/title remains the original request's recorded content. No
transcription, signature validation or anonymous authorship is fabricated. File
version/bytes/hash remain retained and council-readable; applicants remain denied.
Request completion disables the old online write capability. Unexpired issued
bearers may confirm the existing minimal receipt, including paper completion, but
cannot read paper/report content or mutate it.

One proceeding lock serializes paper/online submissions, other request writers and
closure. Identical actor/file/date/version retry returns the original report ID,
including after closure, without duplicate revision/audit/notice. A different
source/date or recorder cannot replace a completed response. General narrative
revision is denied and can_revise=false for paper reports; follow-up is a separate
linked request. Existing saved online draft is retained, not silently discarded.

0049 adds a private non-app-executable source-proof helper and narrowly extends
report-root/revision policies to this writer-bound file/date/request operation.
Direct SQL cannot forge actor/date, substitute an unbound source, skip context,
change answers or add a second paper revision. Existing ordinary reports, strict
medical consent and0042 file privacy rules remain. The status projection gains
minimal receipt support for actual paper reports. No domain model/table or role
grant expansion; one additive council endpoint. Existing runtime grants for the
replaced entrypoints are preserved. No new grant step beyond existing plans.

Verification uses physicalctm_app and synthetic local source bytes/scan events;
not live antivirus, OCR, signature or paper-content acceptance. Covers successful
completion/replay/download/recorded actor/one notification, old-link denial and
minimal receipt, applicant and bearer denial, scan/current-version/request/category/
date/version/writer failures, raw source forgeries, immutable response, private
helper permission denial and exact receipt recovery after closure. A separate
PostgreSQL/SQLite endpoint lifecycle verifies the adapter contract.

Governance owns serial integration/migration and gives council/QA an exact combined
SHA.0049 reverse restores0023 report-root,0042 request-source and0047 receipt
functions, then removes the private helper; it does not delete new retained paper
records. Rollback requires coordinated matching code/write controls and is not
acceptance of the new paper lifecycle. Preserve applied history; coordinate
unapplied UI metadata to unique later0050. No operational migration/merge/deploy
by backend. UI adoption, printable blank request, explicit wrong-upload correction
exception, recordings and actual email invitation remain unfinished. This delivery
completes the paper-recording API, not all C05 acceptance or local OCR integration.
