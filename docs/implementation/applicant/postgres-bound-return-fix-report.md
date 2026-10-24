# Returned-correction submission fix: applicant retest

**The original failing journey passes** on exact combined integration b3de51e203c814f1260ba5046e1d35e67d486657, which includes backend48b80c40fe3e2c4c96a3afa40f0bae69b4addfb4 and migrations0040/0041. The isolated archive uses the combined build's actual frontend and backend without applicant asset overlays or hook patches. This is a local PostgreSQL16 browser/API run, not a public-server Microsoft sign-in run. [Focused result](postgres-bound-return-fix-focused-result.json).

All seven focused groups passed: own draft start/save; private draft/history and foreign-write denial; required original uploads/downloads; initial formal submission and exact receipt replay; returned correction save preserving original revision/manifest/attestation/actor; corrected resubmission retaining waiver and original signature; own notification acknowledgement with duplicate/foreign isolation. Optional spouse_birth_date remains absent, preserving the failure trigger. No second attestation was sent and two formal submission records were verified.

SQL current_user=session_user=ctm_app, NOSUPERUSER/NOBYPASSRLS/NOINHERIT,63forced-RLS domain tables, zero owner memberships. Synthetic accounts/authentication, content, authorized waiver and controlled scan policy remain fixtures. No RLS bypass or runtime-role relaxation was added. The owned container was verified removed. [Cleanup](postgres-bound-return-fix-cleanup.json).

## Separate broader-suite result

The outer suite continued beyond the focused journey and completed own-history browser checks, including hidden/nonexistent-history404 body equality. It later stopped at browser_applicant_api.py:226: foreign/council private draft detail expected403 but returned404. [Interrupted outer run](postgres-bound-return-fix-interrupted.json). This is a separate status-oracle reconciliation; no private payload leak is established by this result. The focused pass does not make the full outer suite pass, and overlapping group counts are not added. Historical failed submissions and strict403 runs remain unchanged.

## Handoff and remaining acceptance

Applicant's requested returned-correction retest is complete for the exact combined build under physical restricted SQL login. Governance owns deployed image/migration verification and designated fictional Microsoft test identity; independent QA owns combined-build acceptance. The shared server is governance-reported deployed at this commit but was not authenticated or mutated by this run. No operational migration, shared-server deployment or main merge occurred here.

Remaining: reconcile broader private-resource status expectations with backend's documented RLS contract, then broader acceptance; genuine shared-server applicant journey; approved full EN/AR content and Arabic civil wording; normalized schema reconciliation and live-service acceptance.
