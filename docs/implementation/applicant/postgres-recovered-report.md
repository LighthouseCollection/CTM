# Fresh PostgreSQL acceptance after Docker recovery

Governance confirmed owner-authorized Docker recovery; local inventory verified the old owned container absent. Two new isolated PostgreSQL16 containers were created and removed with ownership verification. [Cleanup evidence](postgres-recovered-cleanup.json). No shared service or CTM server VM was restarted by applicant.

Candidate: backend9b7abce1079370add53ccbfb47a42631e158fff2; integrated frontend83e537d with Plenix0.60.1; captured current applicant modules. The integrated shell already includes linked entry, so no hook patch was applied. This is an explicit local candidate, not a published integration successor.

Fresh HTTP connections physically logged in as current_user=session_user=ctm_app, NOSUPERUSER/NOBYPASSRLS/NOINHERIT, with63 forced-RLS domain tables and zero table-owner memberships. Draft start/save, private draft/history denials and own required-original uploads/downloads completed. The focused run and outer run overlap; their counts are not summed. Controlled scanner policy and synthetic accounts/content/waiver remain fixtures, not live-service acceptance.

## Newly observed blocker

After saving a synthetic Maya Fictional petition, uploading required originals and obtaining an authorized waiver, browser declaration/submission POST returned500. PostgreSQL reports `new row violates row-level security policy for table tribunal_party`; backend tribunal/services/applications.py:445 calls party.save() while updating the generated party name/reference/participating fields. This is the observed failure under the exact login/candidate above; policy cause and required correction belong to backend. No bypass, grant or service change was made here. [Focused evidence](postgres-recovered-focused-result.json) | [Interrupted outer run](postgres-recovered-interrupted.json).

The first fresh attempt stopped earlier because the fee-waiver text matched two panels. The assertion was scoped to Payment status and history; the second attempt progressed to the server failure. [First attempt](postgres-recovered-attempt1.json). Both containers were verified removed. The earlier account-query stall did not recur in these attempts; this does not establish its root cause or permanent resolution.

The new backend hidden-history404 contract is explicitly selected for fresh runs and compares hidden/nonexistent bodies. Legacy default strict403 assertions and historical failed-run evidence remain. Full history-contract checks later in the outer suite were not reached because focused submission failed; no full-suite pass is claimed.

Published JSON omits raw Django DEBUG responses/settings; local raw logs remain ignored. Backend must fix/retest the submission policy path, then applicant can rerun fresh acceptance. Approved bilingual content, normalized schema acceptance, governance integration and live-service acceptance remain separate dependencies. No merge/deploy.

Governance subsequently relayed owner authorization for testing the existing fictional database on CTM VM10.0.0.40. Exact server/candidate handoff is still pending; no server test or deployment was performed here. Preserve existing records and coordinate server migrations/deployments with governance. Local Docker is no longer a prerequisite for that separately authorized testing.
