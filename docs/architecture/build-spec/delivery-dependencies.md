# Delivery dependencies and implementation sequence

No additional broad workflow questionnaire is needed before starting the database implementation. The following are concrete engineering/content inputs, not permission to reopen settled policies.

| Dependency | State / action |
|---|---|
| Linux VM/distro/resources/storage | VM access and existing container inventory needed; inspect before reuse. Size after representative OCR/audio load, not unsupported throughput promises. |
| PostgreSQL/schema rollout | DDL structural baseline generated. Build Django models/migrations, guarded services, row policies, grants and invariant tests before runtime access. No production database created. |
| Exact runtime/image versions | Select supported compatible releases and lock images/digests during packaging. Do not confuse named technology choice with version compatibility testing. |
| Plenix CDN |0.58.0 mandated. Fetch/document actual components and verify required shell/list-detail/recorder/viewer adapters; CDN availability/components not yet verified. Missing component must be reported. |
| Microsoft/Google/Apple | Actual app registrations, allowed tenant, callbacks and secret provisioning needed. No CTM password fallback. Provider account linking requires proof. |
| Payments | Stripe likely choice, not a live configured account. Confirm credentials/provider when configuring integration, use test mode for demo; do not fabricate charges. |
| Email | Outbound domain/provider and inbound routing service credentials/configuration, webhook validation and DNS authentication. |
| Audio transcription/translation | Approved provider(s) or server engine, model/resource limits and configured keys; exact user prompt already preserved. Server-side medical-document egress remains prohibited. |
| Institutional text | Final approved bilingual declarations, medical release wording/scope and type-specific decree templates/signature content. Existing prototypes/reference drafts are not automatically approved legal/canonical forms. |
| Arabic | Reviewed equivalent translations for all UI/content, isolated RTL patch now; eventual Arabic Plenix CDN replacement. No automatic publication of AI output. |
| PDF scan capture | Existing requested capability still needs compatible open-source capture adapter selection; PDF.js/OCR do not themselves provide scanner/device integration. Must not block ordinary uploads. |
| Signature implementation | Digital/paper signed upload supported; certificate-backed cryptographic signer product not selected. Do not claim a drawn/image signature is a cryptographic signature. |
| Backups | Destination still deferred; choose separate recovery location before live sensitive data, test full restoration. |
| Production hosting | Azure versus private server/VPN remains deferred. One-VM package must relocate with database/files/secrets/configuration; no cloud-specific dependency assumed. |

Engineering defaults explicitly adopted for build planning: modular Django app; provider-only django-allauth integration; PostgreSQL outbox; Celery+Redis workers (persistent outbox is durable source); private mounted file storage; Uppy/Tus/browser microphone adapters; viewers through Plenix wrappers; ClamAV/FFmpeg/WeasyPrint workers. Validate licenses/versions/integration and existing server services during packaging rather than installing all candidate alternatives. Non-AI translation and PDF capture adapters can remain disabled until defined.

## Build order

1. Establish private Git repository/worktree conventions if not already present, source-control specification and approved assets, scaffold pinned Django project and one-VM Compose package. No real applicant data in fixtures.
2. Implement custom provider-only account model before first migrations, staff authorization, person/case identity, claims and row/object policy foundation. Bootstrap first admin through controlled deployment configuration, not public self-enrollment.
3. Build migrations from schema, apply ephemeral database, run ownership/concurrency/immutability tests. Keep structural DDL as review artifact; Django migrations are deployment mechanism and must be reconciled rather than run alongside unrelated duplicate tables.
4. Implement upload/context/version safety, questionnaire drafts, declarations/fees/payment test-mode finalization, completeness returns and applicant read projections.
5. Implement sessions/assignments/hearings, reports/templates/external priest, audio processing and release-scoped Professional Assessments.
6. Implement votes/approval/decree issuance/release, withdrawals and appeal proceedings; private communications, deferred delivery and notifications.
7. Integrate OCR/search/media processing and Plenix shell/screens; test English/Arabic. No legacy UI copy or invented design-system values.
8. End-to-end ten-user demo with synthetic cases, restore/relocation rehearsal and integration failure checks. Configure real providers/VM/domain only through protected secrets; gate live data on acceptance requirements.

## Development memory

Engram is installed after specification consolidation as requested. Its installation/version/configuration results are recorded in `engram-installation.md`. It is a developer tool outside the CTM VM/application dependency graph; CTM PostgreSQL is still the business database. Store concise architecture references/decisions, not real cases, applicant or clinical data, secrets or uploaded evidence. The stock plugin can capture development prompts locally; do not put real sensitive case material into the coding chat. No bulk conversation import or cloud sync was configured by this task. Existing Codex memory files are not rewritten.
