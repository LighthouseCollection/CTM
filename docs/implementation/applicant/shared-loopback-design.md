# Guarded applicant shared-loopback acceptance design

Governance approved this design for the owner-authorized CTM test VM. It targets immutable source `/opt/ctm/releases/dccbd63`, image `ctm-application:dccbd63` and a clone named from the full run ID, for example `ctm_accept_applicant_20261022t010203z_a1b2c3d4`. It never changes the shared `ctm` database, public listener, roles, provider configuration, workers or deployed container.

## Approach

The acceptance operator creates a PostgreSQL clone and protected artifact directory during a serial governance window. A pure guard module runs before Django setup. It validates the exact release-directory suffix, deterministic source-tree SHA-256, deployed candidate/tagged-image identity, `127.0.0.1:0` binding, clone database names and physical `ctm_owner`/`ctm_app` connection identities. Media and output paths must resolve under `/srv/ctm/acceptance/<unique-run>` with mode `0700`.

The existing complete applicant API/browser runner gains `--shared-loopback`. It uses the immutable release as application source, owner credentials only for clone migrations and fixture creation, and a separate physical `ctm_app` connection for every HTTP request. Fixtures receive unique run-tagged accounts and questionnaire versions. All screenshots and JSON evidence go to the protected artifact directory; the release tree is hashed again after the run to prove it was unchanged.

The harness removes provider, SMTP and payment credentials from its process before Django imports. Django's test email backend, eager local task mode and controlled scan policy remain explicit synthetic boundaries. Browser navigation is loopback-only. There is no public session route or provider-link fixture.

## Failure and evidence rules

Any guard mismatch aborts before migrations or fixture writes. Results record only source/image hashes, clone name, restricted-role facts, test groups, page errors and artifact state; database URLs, passwords, cookies and environment values are never serialized. The clone and artifacts are retained for governance and QA review, with no automatic cleanup.

Success requires the full suite to finish, no page errors, physical `current_user=session_user=ctm_app`, all domain tables forced RLS and zero owner memberships. The result remains synthetic authentication/content/scan/waiver evidence and does not establish Google/Apple, live payment/email/antivirus or institutional-content acceptance.

