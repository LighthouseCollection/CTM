# Implementation status - 2026-10-21



## Outcome



A real Django backend now exists in the new private `LighthouseCollection/CTM` repository. It persists records, applies explicit permissions and performs tested workflow transitions. This is a partial implementation of the approved contract. It is not yet the functional ten-user browser demo or a production deployment.



The alpha prototype remains in its separate repository. No operational CTM database was reset, migrated or populated during this implementation session.



## Implemented backend paths



| Area | Present behavior | Remaining work |

|---|---|---|

| Accounts | Provider-only custom accounts; unusable CTM passwords; preauthorized tenant/object identity for council; verified applicant identities; suspension session revocation | Real Microsoft/Google/Apple callback tests, full account linking/email change, duplicate consolidation and administrative security alerts |

| Applications | Private drafts, versioned answers, questionnaire/declaration snapshots, required fields/documents, fee gating, exact three-date marriage matching, original case return/resubmission, one-open-case claims | Full151-table mapping and every application/prototype field; duplicate identity review UI and exact-match hold detection |

| Payments | Stripe checkout adapter, signature-verified callbacks, immutable payment events, frozen candidate, idempotent recoverable submission and callback race handling | Real Stripe test credentials, refund/chargeback/reversal and reconciliation workflows, receipts |

| Cases | Los Angeles daily numbers, party references, assignment history, open claims, historical entry workspaces and verified pending-party links | Full identity/alias merge, complete lifecycle and cross-program record reconciliation |

| Council sessions | Agenda parts, hearings, outcomes, next dated-session carryover, testimony invitations/responses, overlap checks, manual deferrals | Attendance UI, session rescheduling/cancellation, complete hearing briefing and session acceptance tests |

| Reports | Exact question seed, foundational question inclusion, versioned templates and sent snapshots, assigned-author report history, follow-up links, external 30-day bearer capability, applicant own-response projection | Browser report editor, printable PDF and paper-response replacement, external invitation delivery/recorded response, all report search/indexing |

| Professional Assessments | Separate medical/psychological request type, exact-request signed disclosure scope, original file authorization, local-only extraction gate | Approved bilingual release content, complete request/doctor/release UI and processing acceptance |

| Files | Private originals, category/MIME limits, contextual owners/versions, technical scan gate, latest-only applicant access, council history, audited download | Resumable/whole-recording capture, background scan recovery, external-upload path, complete viewer acceptance, automatic category rename history and all acquisition adapters |

| Audio | Whole-report recording association, notice confirmation, finalize-once processing queue | Recorder UI/mobile recovery, actual transcription/translation engine, reviewed transcript editor and all configured engine failure tests |

| Documents/search | Local native DOCX/PDF extraction, Tesseract/OCRmyPDF English/Arabic paths, source-authorized Meilisearch adapter | Real worker pipeline, PaddleOCR/Docling adapters, legacy Word handling, operational index setup, report/global search coverage and representative OCR tests |

| Decision/decree | Exact decision version, vote/approval provenance, shared revision locks, signed-file attestation, issue/close, explicit entitled recipient release and withdrawal | Approved templates/PDF generation, actual signature product and UI; no removed replacement-decree workflow added |

| Appeals | Separate filing fee, append-only additions, withdrawal, per-appeal result, shared reopening proceeding and preserved original history | Full review/agenda UI and end-to-end multi-party appeal exercises |

| Communications | Private per-party message copies, contextual document links, session-close delivery trigger and manual call records | SMTP/inbound-email integration, bilingual actual message bodies, rejection of inbound attachments, browser conversations |

| Background work | Durable outbox, retry leases, quiet-period digest batching, current-manager routing, retention warnings and cleanup | Crash/retry load tests and all operational alerts; isolated real-broker/default-worker smoke test passed |

| Database protection | PostgreSQL constraints/transaction locks, immutable update/delete guards (with explicit private-draft cleanup exceptions), case/party deletion protection, closed-proceeding insert guards on key histories; forced RLS on 23 private-source and council tables with transaction-local actor/capability context | Remaining table RLS, complete grant and ownership split, worker maintenance contexts, remaining lifecycle guards and all 151-table security requirements |

| Interface | Pinned Plenix shell, universal sign-in, account menu, initial case/session/application projections, private communications and persisted language settings | Filing/report/evidence/decision editors, split views, full localization/accessibility acceptance and provider browser login |



## Verified in the VM



- SSH key access to `admin@10.0.0.40` works.

- Existing PostgreSQL, Redis, Meilisearch, ClamAV and Engram infrastructure containers were running and healthy when inspected.

- Validation uses `/opt/ctm-validation`, the separate `ctm_validation` role/database and pytest's temporary `test_ctm_validation` database. The role is not superuser and cannot bypass RLS; CREATEDB is for disposable pytest databases only.

- PostgreSQL migrations and regression tests executed in a Linux container. See `validation-results.json` for the final run count.

- The application Docker image built successfully, including static collection.

- An isolated Redis/worker probe consumed the configured default queue and recorded a durable retry; its temporary containers were removed. A private validation-only Gunicorn container returned HTTP health status `ok` against the isolated database. It uses test settings and has no public proxy route. It is not the production service and does not enable real identity/payment providers.

- Reference seeding preserved 59 English questions and left institutional declarations unpublished.



## Blockers skipped during autonomous work



1. Pinned Plenix 0.58.0 component documentation repeatedly timed out from both AdminPC and VM. No prototype UI was copied or undocumented component invented. The root currently returns an honest backend-status JSON response.

2. Microsoft/Google/Apple, Stripe, SMTP/inbound email and transcription/translation credentials were not supplied/configured. Adapters retain work or report unavailable; no credentials were invented and no real charges/emails were attempted.

3. Approved bilingual declaration/release/decree content remains a configuration dependency. Research/reference drafts were not silently published as institutional text.

4. The151-table physical contract is not fully represented by the initial Django models. The inventory is an implementation map, not permission to reduce the contract. Full model/migration reconciliation is a production gate.

5. Public readiness requires remaining RLS and production grants, full backup restoration, complete Arabic/Plenix UI, provider integration tests and the ten-user end-to-end exercise.

6. Windows Python 3.12.11 intermittently crashed in migration state rendering; reruns passed. Linux/PostgreSQL validation is the primary evidence; the Windows runtime issue remains an environment limitation.



## Deployment cautions



Do not run `docker compose up` for the application against the operational database yet. Use `check_readiness` and resolve its blockers first. Initial database scripts apply only to fresh volumes; changing an init script does not fix existing roles. The dedicated Engram role changes in this repository were not applied to the existing VM Engram service.



`CTM_TRUST_PROXY_SSL=true` is appropriate only with origin ingress restricted to the trusted HTTPS reverse proxy. The default is false. The SMTP outbox uses at-least-once retries and stable Message-ID headers; it does not promise exactly-once email delivery after a process crash.



File writes happen after database commit to a private atomic destination. A disk write failure can leave source metadata awaiting recovery; a complete repair/reconciliation worker is still required. Files are never exposed by a public MEDIA_URL.



The GitHub PostgreSQL workflow passed on commit 0652f2a:67 tests, migration checks and byte-exact source validation. Run: https://github.com/LighthouseCollection/CTM/actions/runs/39659081375. Container image build verification does not establish compatibility of every heavyweight OCR/media worker dependency.



## Next independent work



1. Reconcile initial models/migrations with every contract entity/column, then implement and test forced RLS, runtime grants and all closed-record/delete invariants.

2. Restore pinned Plenix documentation access and build the universal provider login and locked council/applicant layouts.

3. Complete background scan/extraction/indexing/transcription and incoming/outgoing communication adapters using isolated test services.

4. Configure real provider test credentials through protected server secrets; verify each integration and complete bilingual institutional content.

5. Run the synthetic ten-user browser exercise, backup restore and relocation rehearsal, then deploy through the reviewed reverse proxy.



Container Dockerfiles now copy an explicit source allowlist rather than the complete build context. An isolated test credential was rotated after the initial broader validation build; no operational CTM credential was used. The rebuilt image was checked to contain neither the validation environment file nor the source archive.



## Source privacy implementation — 2026-10-21



Migration 0011 adds forced PostgreSQL row policies to 14 private-source tables. Raw queries under a non-owner, non-bypass role verify applicant isolation, private drafts, latest-only attachments, exact decree releases, medical-release scope, private communications and audit visibility. Server-derived actor context is transaction-local and restored after nested operations. External priest submissions use an exact expiring request capability; verified payment recovery uses a validated paid-filing identity rather than an interactive login. Submitted provenance cannot be reset into a disposable draft.



The latest isolated Linux/PostgreSQL suite passes 92 tests. It includes signature-checked synthetic Stripe callbacks with an unrelated signed-in browser identity, external priest responses and assigned-manager notifications, migration reverse/reapply and helper execution ACL checks. A read-only review found no additional concrete issue in this slice after four reported defects were fixed and covered by regressions.



This is partial security implementation: runtime role grants, remaining domain-table policies and background worker/maintenance identities still block production. The migration credential remains explicitly privileged. The isolated fixture's broad grants are test scaffolding and must never become the production grant template. See [database-source-privacy.md](database-source-privacy.md).



GitHub validation also passed on commit `1c26120`: 92 PostgreSQL tests, migration drift check and preserved-source structural validation. Run: https://github.com/LighthouseCollection/CTM/actions/runs/39665560875.



## Local council attendance workflow — 2026-10-21



Admin/secretary can record session defaults and individual hearing attendance through `/api/sessions/{id}/attendance/`. All changes append a dated actor-attributed record. A hearing copies current session attendance into its own snapshot, treating unrecorded active council accounts as absent. The assigned presenter's attendance must be explicitly recorded first. Session-default corrections do not rewrite earlier hearing snapshots.



An absent assigned presenter defers the case for manual agenda placement; session closure also detects recorded presenter absence rather than automatically carrying the case forward. Only the assigned member presents. Closed sessions, closed proceedings and completed appeal hearings reject attendance edits. Hearing creation rechecks assignment and lifecycle under locks. Testimony scheduling now uses the same session-before-agenda lock order.



Local Python 3.13 validation: 79 tests passed, 29 PostgreSQL-only tests skipped. The existing Python 3.12 environment crashed in migration rendering; the separate ignored `.tmp/venv313` environment avoids that observed crash. PostgreSQL-specific concurrency and database policy verification remain required. No VM container, proxy, production database or credential changed during this local implementation.



Latest GitHub PostgreSQL validation passed on `9f7c371`: **108 tests**, migration drift and preserved-source structural checks. Run: https://github.com/LighthouseCollection/CTM/actions/runs/39676229102. This run verifies the complete current test suite, not full production readiness or a dedicated concurrent-load exercise.



## Assigned-manager agenda placement — 2026-10-21



The existing agenda endpoint now lets the current assigned case manager place their case in part 2 of a planned dated session, including a pending appeal. Part 1 remains restricted to admin/secretary. Permission is rechecked against the locked case, so a previously assigned member cannot place it after reassignment. Invalid agenda parts, closed sessions and closed cases without pending appeals are rejected. Repeated placement retains one agenda item and one placement audit event; conflicting existing agenda parts require explicit handling rather than being silently changed.



Local validation: 92 tests passed and 29 PostgreSQL-only tests skipped; migration drift and critical lint checks passed. Pinned Plenix documentation access was retried and still timed out. This remains backend implementation; no browser interface or VM service changed.



Carryover preserves an existing next-session placement even if its agenda part differs; it records the relationship in the case audit rather than failing session closure or changing the placement. The Windows interpreter also crashed once under Python 3.13; the full rerun passed. The runtime issue is not confined to Python 3.12.



Latest agenda-workflow PostgreSQL CI passed: **121 tests** on `3e3ac4d`, including migration drift and source structural checks. Run: https://github.com/LighthouseCollection/CTM/actions/runs/39677076540.



## Plenix documentation access recovered



Pinned version 0.58.0 documentation was retrieved successfully through the existing LAN reverse proxy using `curl --resolve design-system.lighthouseway.org:443:10.0.0.20` with normal TLS certificate validation. The index reports version 0.58.0 and 766 documentation records; account-menu documentation is readable. Earlier public-route timeouts remain recorded above, but documentation access is no longer an implementation blocker. Documentation reference files are in ignored temporary storage; no CDN component/style assets were copied into the app and runtime CDN URLs remain pinned as specified. Browser access via public DNS is not established by this operator-side override.


## Initial local Plenix interface - 2026-10-21

The root and `/accounts/login/` now render the same pinned-CDN React shell. Only configured identity providers are shown. No password form or demo-login bypass was introduced. Role-specific navigation, initial case/session/application views, archive, private case communications and account language settings use authenticated APIs. Messages offer recipient selection and immediate/after-session email timing through existing services. Unsupported destinations remain disabled.

The interface uses documented Plenix components without application CSS, raw visual values or application inline styles. Arabic uses direction-aware markup and translated visible labels; submitted content is preserved. Full localization/accessibility acceptance and remaining editors are still required. Both language settings use one validated, locked service and record before/after audit metadata.

The reproducible Chromium smoke loads real CDN components through an optional TLS-validated LAN resolver override, with synthetic authenticated API responses. It passed English/Arabic login, role navigation, case/back/profile navigation, repeated current-page selection, communications composition/send, preservation of unsent text across language changes, applicant draft display and mobile width checks. No console errors, mobile overflow or closed-state runtime inline styles were observed. This is not a provider login or full authenticated browser/server acceptance test.

Latest local suite:106 passed,29 PostgreSQL-only skipped. Intermittent Windows interpreter crashes persist; the full rerun passed. No VM, proxy or operational database was changed. All151-table reconciliation and remaining production gates still apply.

## Council database privacy - 2026-10-21

Forced PostgreSQL row policies now protect23 domain tables, including nine council session/hearing/attendance/notes/assignment tables added in0012. Applicant/anonymous raw access is denied. Assigned presenters can create a scoped initial attendance snapshot but cannot append administrative corrections. Session date/context and closed-session state remain guarded. Legitimate restricted-role workflow writes and raw denial regressions passed in the147-test PostgreSQL suite on0f089ad: https://github.com/LighthouseCollection/CTM/actions/runs/39681111852.

The change was developed and validated on an isolated GitHub branch, reviewed, then fast-forwarded to main. No operational migrations ran. Remaining table policies, production grants and full schema reconciliation still block public deployment.


## Private file delivery and initial evidence screens - 2026-10-21

Authenticated original delivery now supports single byte ranges for audio/video seeking, HEAD metadata, If-Range validators, private no-store responses, safe inline MIME types and audited view/download actions. Authorization and scan validation precede source metadata. Unsatisfiable ranges return no file bytes; abandoned bounded streams close their handles. Originals remain private.

The new paginated case-file endpoint filters ownership before pagination, includes submitted application uploads linked to the case, defaults to the latest clean version and allows council-only version history. It excludes medical, report-request and decree sources, which require their dedicated workflows. A pending latest upload does not expose an older clean version as current. No total attachment-count limit was added.

Council Documents and Evidence now use documented pinned Plenix SplitView/ReadingPane components. Images use DocumentViewer, audio/video use MediaPlayer, PDFs open in a private browser PDF tab, and Word files download. This is the initial reading interface; uploading/editing workflows and dedicated medical/report/decree screens remain incomplete. Browser smoke uses synthetic API fixtures with real CDN components, checks selection/history and mobile width, and passed without JavaScript errors. One empty style attribute comes from the CDN Checkbox; no application styling was added.

PostgreSQL CI passed168 tests on083cb39 (https://github.com/LighthouseCollection/CTM/actions/runs/39682545743); local suite127 passed with41 PostgreSQL-only skips. The earlier failing streaming tests closed Django test responses twice, invalidating the enclosing PostgreSQL test transaction; the test harness was corrected. Additional pagination regression and UI validation are being completed. No operational deployment or database migration was performed.


## Report reading interface - 2026-10-21

The council Reports destination now uses a Plenix split list/reading pane for completed ordinary reports. It displays the sent question snapshots beside their attributed answers, completion date, revision number, internal observations and links to the original report for follow-ups. Medical/psychological records are reserved for their separate assessment section. This change does not add editing permissions or expose staff-authored reports to applicants. API projections omit invitation credentials and preserve existing applicant-only response filtering. Remaining report work includes request/editor UI, history, recording/transcript tabs and print/upload workflows.

The real-CDN browser smoke now checks report selection, sent question text and internal observations using synthetic council fixtures. Local validation130 passed,41 PostgreSQL-only skipped; critical lint passed. Independent code review found no additional privacy/state issue in this reading slice. No operational deployment changed.


## Private-response headers - 2026-10-21

A middleware boundary now sets private/no-store caching, no-referrer and nosniff on CTM API, account/login, capability-report and root-shell responses. It also covers missing-resource and CSRF/access rejection responses, rather than relying on individual successful views. Static CDN assets remain outside this boundary. Local135 tests passed with41 PostgreSQL-only skips; the previous report-reading commit passed171 PostgreSQL tests in CI. Public deployment remains blocked on the documented integration and schema/security acceptance work.


## Notification inbox and real-API browser validation - 2026-10-21

Both portal roles now have a header Notifications destination. Its paginated inbox displays translated event summaries, local dates, read/unread status and links to authorized cases. Read updates are recipient-scoped and preserve the first-read timestamp. Raw event payloads are not rendered. This is an inbox, not yet a live push subscription or email delivery integration.

`scripts/browser_integration.py` now validates the real Django API/UI boundary in addition to the synthetic-API component smoke. It creates an isolated ignored SQLite database and private media directory, synthetic accounts/case/report, and Django test-client sessions. It starts only a loopback WSGI server and does not add a login endpoint, call production identity/payment providers, send email, alter the VM or use operational records. The real browser persisted notification read status and a private case message, read the sent report question snapshot, received a206 private byte range and was denied access from an unrelated authenticated applicant. No browser JavaScript errors were observed. PostgreSQL row security remains separately tested in CI; this local browser run does not prove provider authentication or all workflows.

Run with the optional browser dependencies: `uv sync --group browser`, install the matching Chromium, then `uv run --group browser python scripts/browser_integration.py`. The same optional CTM_CDN_LAN_IP/CTM_BROWSER_EXECUTABLE environment overrides as `browser_smoke.py` are supported. Each synthetic database/artifact directory is created under ignored `.tmp/browser-integration-*`. Full local suite136 passed,41 PostgreSQL-only skipped. No operational deployment changed.


## Session attendance interface - 2026-10-21

The session agenda now displays its Council Session date and baseline attendance. Only admin/secretary on a planned session receive recording controls; other council users see attendance read-only. Changes use the existing append-only attendance service, show the selected value immediately and roll back the display on save failure. Unrecorded attendance is distinct from absence. Recorded inactive members remain visible read-only rather than disappearing with the current active-member roster. Hearing-specific attendance and hearing/outcome controls still need their UI.

The real-API browser check now records an administrator-entered attendance value and confirms its database row, alongside the earlier report/message/notification/file checks. It also checks an applicant can read their own case/report response but cannot read council-only evidence. Local141 tests passed with41 PostgreSQL-only skips; critical lint and migration drift checks passed. Intermittent Windows interpreter crashes persist; a full rerun succeeded. PostgreSQL CI for the preceding inbox commit passed177 tests. No operational deployment changed.


## Report revision reading - 2026-10-21

Council members can now read preserved report revisions through the existing revisions URL (GET added; POST authorization unchanged). The Plenix reading pane offers a version selector with editor/time and the preserved sent question labels. Applicants cannot call this history endpoint. Medical/psychological history additionally requires the exact subject/request disclosure granting council access. The real-API browser selects an earlier interview revision and verifies its original answer. Independent review found no additional privacy/state defect in this slice. Production routing was verified separately; source protection/readiness gates remain in place.

## Deployment initialization review - 2026-10-21

The staged fresh-cluster role script previously interpolated passwords into a dollar-quoted DO body; special password content could break that SQL framing. The canonical initialization SQL now reads environment variables through psql and quotes them as SQL literals before format/gexec. The shell wrapper supplies its connection password through the environment, ignores psqlrc and calls one read-only mounted SQL source. New runtime roles explicitly lack superuser, role creation, database creation, replication, RLS bypass and inherited role privileges. Existing role passwords are preserved. This initializes roles/schema privileges only; production domain-table/function grants remain incomplete and are not bypassed.

A disposable GitHub PostgreSQL regression checks special-character/newline passwords, idempotency and absence of application-table read access. It never changes preexisting roles and does not execute against the operational VM. Reference: https://www.postgresql.org/docs/16/app-psql.html (getenv, SQL literal interpolation and gexec).


## Production image paths and private-volume startup - 2026-10-21

An isolated existing validation image confirmed that its runtime media/static paths were absent. The production Dockerfile now creates private media storage for UID1000 and collects application static files at the configured runtime path. Static assets are served from the immutable image, rather than a persistent static volume that could hide an upgrade's new app.js. No CDN component files are copied; the application still links pinned Plenix.

A one-shot storage service prepares only the media directory's UID/GID/mode before media-writing services start. It changes no existing file ownership recursively. Its root filesystem is read-only, it has no network, and capabilities are limited to ownership/mode maintenance plus read/search needed to reopen an existing UID1000/0700 directory. The image smoke runs this initializer twice with the production security flags, checks existing file ownership remains unchanged, verifies a non-root upload write, and checks packaged app.js exists. This runs in disposable GitHub containers/volumes; no operational volume was changed. Existing files with incompatible ownership still require explicit inspection rather than blanket ownership replacement.


## Public CDN and image validation - 2026-10-21

Pinned Plenix assets now return200 over public DNS/TLS without the LAN override. The full real-API browser script passed through this public CDN path, including report revision selection, saved attendance/messages, notification reads and applicant isolation. Provider login remains a separate acceptance gate.

CI39686788415 passed185 PostgreSQL tests, built the production image and ran private-volume initialization twice with the configured restricted capabilities. It verified the non-root application user can write media, existing file ownership is preserved and the packaged app.js is present. A further CI HTTP smoke will launch that production image on the disposable runner's loopback address and compare the served app.js to the source. No operational VM application, database, volume or public upstream was changed.


## Demo priorities and local Microsoft review - 2026-10-21

User confirmed OCR and audio recording are low priority and clearly labelled placeholders are acceptable for this demo. They do not block delivery of sign-in and core case workflows. This does not relax private-file access or upload safety.

A separate loopback-only Microsoft OAuth review server is available via scripts/local_microsoft.py. It reads provider configuration from protected SSH stdin into process memory, uses an isolated local database, preauthorizes the administrator by verified Microsoft subject and does not inject authenticated sessions. The Azure application has an additive localhost Web callback; production callback remains configured. Successful provider callback acceptance remains to be verified. The synthetic local preview remains separate at port18843.

The requested Microsoft account is frraphaelmaher@lacopts.org; its tenant subject was verified via Microsoft Graph. The genuine local OAuth flow now reaches Microsoft password entry for that account. Completion awaits user authentication/MFA; no callback success is claimed. Browser testing exposed that no-referrer suppressed the Origin on same-origin form POSTs. Private responses now use same-origin referrer policy, retaining no external referrer while allowing normal CSRF checks. Five private-header tests pass.


## Local OAuth server lifetime - 2026-10-21

User callback encountered a connection failure because the foreground local server was no longer listening after the prior turn. Added scripts/start-local-microsoft.ps1 for a hidden independent background process, retaining loopback binding and SSH-to-stdin provider credentials. Verified HTTP200 from the restored listener and reopened a fresh provider flow. The current attempt awaits user password/MFA. Sanitized local diagnostics record only exception categories, state presence and AADSTS codes, never callback codes, tokens or response bodies. Callback acceptance is not yet confirmed.


## Microsoft callback verified - 2026-10-21

Genuine Microsoft OAuth for frraphaelmaher@lacopts.org now completes into the council portal on localhost18844. An actual callback exposed AttributeError in allauth default user display: the email-only Account has no username field. Set ACCOUNT_USER_MODEL_USERNAME_FIELD=None. A new regression reproduces the actual logged-in template failure before the fix and passes afterward; the related subset passes12 tests. Browser verified the authenticated name Fr. Raphael Maher, Council portal navigation and Home. This verifies local provider callback acceptance only, not the undeployed public route. Added sanitized server exception frame diagnostics to the local tool (no tokens, query strings or exception values).

## Council session archive record-of-truth — 2026-10-22

The council-session archive is database-backed. The archived-session list reads
`CouncilSession` records through `GET /api/sessions/`; its case-assignment and
hearing totals are aggregates of related `AgendaItem` rows. Selecting a session
reads `GET /api/sessions/{id}/agenda/`, which uses that same session identifier
to retrieve its agenda, then derives the displayed case, party, case-manager,
status, grounds, hearing, and recommendation values from the linked `Case`,
`Party`, `Account`, `Application`, `Hearing`, and `HearingOutcome` records.
The browser has no hard-coded session dates, people, counts, or agenda rows.
A session marked Adjourned is complete and immediately appears in Archived; its
linked agenda rows remain available through the selected archived-session record.

Session creation, placement, assignment, presentation, adjournment, and outcome
updates are service commands that persist to those records and write their
existing audit events. The archive is therefore a read model over the tribunal
record, rather than a separate editable copy.

The `localhost:18844` Microsoft-review environment is an isolated SQLite review
database. When populated with `seed_workflow_demo`, its names and cases are
synthetic fixtures, as documented in `demo-scenarios.md`; they are not
operational tribunal data. The same API and projection path reads production
records only after the application is deployed against its operational database.
No production database data is loaded into the local review environment.
