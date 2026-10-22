# External-priest / interview original privacy correction

## Reproduction and resulting behavior

Council C05 reproduced on shared test candidatedccbd63: a council writer's
external_priest paper upload was assigned to the subject applicant with own
visibility. Once scan was clean, that applicant could GET the PDF. Backend reproduced
HTTP200 under restrictedctm_app before the fix. This is synthetic reproduction;
no real-data exposure is established by the report.

New external_priest and interview request uploads always use ownerNULL and council
visibility, regardless of supplied visibility. The request must still be sent,
case/proceeding open and uploader an authorized council writer. Intake ownership,
medical/psychological scoped consent, category limits, file scan/size gates and
existing request/version/recording controls remain unchanged. This does not add
paper completion, external capability upload or new applicant file access.

Application authorization explicitly rejects applicant access to these request kinds,
including a legacy incorrectly owned row and require_safe=False reads.0042 additionally
replaces four existing SQL policy helpers, retaining signatures and ACLs:
- ctm_attachment_visible and ctm_file_row_readable exclude noncouncil readers when
  the bound report request is external_priest/interview, regardless of stored owner
  or visibility. This covers Attachment/FileVersion and derived scan/text visibility.
- ctm_attachment_writable and ctm_request_source_writable accept these sources only
  with no owner, no application binding, council visibility and the real open sent
  request/case/proceeding/writer proof. Direct SQL cannot reproduce the wrong scope.

Legacy attachment provenance and bytes are not rewritten. Already misclassified rows
become unreadable to applicants via GET/HEAD/range and direct restricted SQL, while
council can read their originals. A legacy incorrectly scoped attachment cannot be
reused as a new correctly scoped upload context; retain it and create a new council
attachment rather than silently changing its historical ownership/visibility.
No signed filing, medical disclosure, report or token lifecycle is rewritten.

External-report responses now always carry no-referrer, including unavailable-link,
unsupported-method and missing-route responses, through the outer private middleware.
Normal same-origin CSRF behavior on other routes is unchanged.

## Verification and integration

Twenty-one focused PostgreSQL tests cover both kinds, PDF/whole recording upload,
subject GET/HEAD/range denial with absent-ID equality, authorized council positive
control, legacy wrong-owner rows and derived scan/text denial, eight direct SQL
scope forgeries, service denial without RLS concealment, ordinary intake positive
control and failed external-link headers. The existing strict JSON-boolean medical-consent rule is preserved in both upgrade
and reverse, with an explicit raw restricted-role migration regression. Full
PostgreSQL739 passed,1 skipped;
rollback/reapply through0042. Synthetic clean scans are explicitly test stand-ins,
not live antivirus/provider acceptance.99routes/63models/63forced tables unchanged.

0042_council_request_file_privacy follows already-applied0041. Governance alone
serially applies it with a recoverable snapshot and integrates the exact backend
SHA. Never reuse/rename applied0040_account_administration or0041_bound_returned_filing.
The separate UI PR22 competing0040_session_workspace_metadata must be reconciled
as an unapplied unique successor by governance/backend (proposed0043 after0042),
not deployed as a parallel leaf. Backend did not edit that branch or operate the server.
Downgrading0042 restores the vulnerable prior SQL behavior; rollback is not a safe
privacy acceptance outcome. Retain appropriate access restrictions during recovery.

Council reruns the reported clean-scan subject-denial scenario on the exact integrated
successor; QA independently verifies negative access and records its SHA. C05 boot
HTML/Bearer transport, distinguishable capability states, capability recording,
print/paper completion, additional projection and invitation delivery remain separate
unfinished work. Document-category runtime labels remain deferred by this incident.
No merge/deploy or operational migration by the backend stream.
