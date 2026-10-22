# Restricted PostgreSQL private draft read contract

## Current integration evidence

Governance reports combined candidate
b3de51e203c814f1260ba5046e1d35e67d486657 includes backend48b80c4, with0040/0041
applied to the shared test server. Backend has not independently performed that
server operation. Backend48b80c4 hosted PostgreSQL checks both passed.

Applicant evidence89072dd independently reran the exact combined code under physical
current_user=session_user=ctm_app, NOSUPERUSER/NOBYPASSRLS/NOINHERIT,63 forced tables
and zero owner memberships. All seven focused browser/API groups passed, including
the original optional-spouse-DOB-absent returned correction resubmission, receipt
replay, original revision/manifest/attestation/actor preservation, retained waiver,
no second signature, two formal submissions and notification isolation.

This is isolated synthetic authentication/content/scan-policy/waiver evidence, not
genuine public Microsoft sign-in or independent QA acceptance. The earlier failing
reports remain valid historical evidence. Shared-server operations and release
acceptance belong to governance; independent combined-build verification belongs
to QA. Main merge and production acceptance are not claimed.

## The broader runner's next stop

Applicant89072dd reports a subsequent broader assertion expected403 for another
person's private draft detail and received404. Under the restricted PostgreSQL role,
RLS hides the unsubmitted Application before application_for can inspect ownership.
The API therefore returns the same404 resource_or_input_invalid JSON as an absent
UUID. No row or existence data is disclosed. A database owner/SQLite run can instead
reach the service-level PermissionDenied403; it is not the restricted-role oracle.

For GET /api/applications/<uuid>/ and its history/, files/ and payments/ children:
- Owner of the prepared draft receives200.
- Unrelated applicant, member, president, admin and secretary receive404 for both
  private and absent IDs, with identical response bodies and private,no-store headers.
- The draft is absent from each unrelated account's application list.

Tests in tests/test_private_draft_contract.py exercise these four routes under actual
ctm_app SQL session authorization. They do not simulate a physical login handshake.
No application code, policy, grant or migration changes accompany this checkpoint.
Authentication-required401, CSRF403, explicit capability403 and validation422 have
separate meanings; this private-resource rule does not redefine all denied requests.

Applicant owns adjustment of its overly strict broader draft-read oracle, retaining
the failed result and then running later scenarios on the exact accepted candidate.
Backend does not edit its runner or relax privacy to satisfy an owner-role expectation.
Independent QA should preserve its findings and record its exact combined-build SHA.

## Baseline assessment

The attached B01 README is an immutable historical snapshot at35e02f7. Its seven
remaining core policies and worker-grant gaps are now implemented in backend's
published0036–0038 work, and the submission blocker is fixed by0041. Its490-test
integration count is not the current candidate's count. Governance separately
reports236 frontend/674 PostgreSQL passed,2 skipped forb3de51e; those figures are
attributed evidence, not this backend test run or a summed count.151-table semantic
parity, approved content, live providers, broader profile/factual workflows and
independent acceptance remain incomplete. No percentage of overall completion is
inferred from model/table/test totals. B01 itself is not overwritten.
