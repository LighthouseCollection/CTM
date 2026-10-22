# Backend gap list for VM-FRM (#2)

Draft. **Not posted on #2.** Posting waits for the owner's approval.

Pinned to backend `db820990dd2fc15e80560bd630d90ec9b22276e5` (PR #7). The schema
files on PR #16 `8572195` are identical. The approved source for every item is
`docs/architecture/build-spec/schema.json` (table named in the item) unless
another source is cited. Full per-table rows are in [`matrix.csv`](matrix.csv).
Items marked *decision* wait on [README → Decisions needed](README.md#decisions-needed).

This list is a reconciliation input, not a migration design. The backend owns the
design. It should add tables or columns without dropping current evidence, and
backfill only recorded facts (see `schema-gap-review.md` "Migration sequence").

## P1: privacy, security, data loss

| ID | Table / field / constraint | Current implementation | Required by | Action |
| --- | --- | --- | --- | --- |
| BG-01 | `person_identity_versions` (all columns, `UNIQUE(person_id,version)`); `persons.identity_state`, `row_version` | `services/applications.py:434-439` overwrites `Person.first_name/last_name/birth_date/gender` on filing | schema.json `person_identity_versions`; data-dictionary "Attributed identity corrections" | Stop the in-place overwrite. Write an attributed identity version (actor, request, source) and keep `Person` as a projection. Backfill current values with explicit unknown provenance. |
| BG-02 | `app_sessions.session_hash` `UNIQUE`, `account_id`, `provider_identity_id`, `authenticated_at`, `revoked_at`, `provider_expires_at` | Django default DB session store (raw `session_key`), no `SESSION_ENGINE` override; `django_session` DML granted to `ctm_app` in 0038 without RLS | schema.json `app_sessions`; permissions.md "Revocation/suspension is checked on each sensitive request" | Store only a hash of the session key (custom session store or a parallel `app_sessions` table). Record provider identity and revocation. Review the RLS and grants for framework session tables. |
| BG-03 | `account_identities` (`issuer`, `subject`, `tenant_id`, `verified_email`, `linked_at`, `revoked_at`); `UNIQUE(issuer,subject)`; `CHECK(provider IN ('microsoft','google','apple'))` | `Account.microsoft_subject` partial unique (`models.py:122,128-134`) plus allauth `socialaccount_socialaccount` | schema.json `account_identities`; data-dictionary "Bind validated issuer and subject" | Add a retained identity-binding table keyed on issuer and subject, with revocation. Keep the tenant and preauthorized-subject checks. Decide RLS for allauth tables. |
| BG-04 | `decree_entitlements` (`decree_id`, `party_id`, `entitlement`); `UNIQUE(decree_id,party_id)`; `CHECK(entitlement IN ('certificate','notice_only'))` | Only `DecisionRevision.entitlements` JSON (`models.py:728`) | schema.json; owner D7 "explicit per-party entitlements, never infer recipients" | Typed entitlement rows, created at decree preparation from the approved decision version. |
| BG-05 | `decree_release_events.entitlement_id`, `certificate_id`, `request_id`; `CHECK(action IN ('release','withdraw'))` | `DecreeRelease(decree, party, actor, action)` (`models.py:768-772`) | schema.json | FK the release to the entitlement and certificate, and add the CHECK. |
| BG-06 | `evaluation_release_attestations` (`exact_text`, `language`, `purpose`, `subject_person_id`, `signer_person_id`, `CHECK(subject_person_id=signer_person_id)`) | `MedicalRelease` subject is an Account; no exact text or language (`models.py:687-693`) | schema.json; permissions.md "Sign medical release: Own subject only" | Store the exact signed text and language, plus subject and signer persons with the CHECK. |
| BG-07 | `evaluation_release_scopes` (`recipient_scope`, `purpose`, `file_scope`) | `MedicalRelease.scope` JSON | schema.json | Typed scope rows referenced by the RLS helpers and disclosures. |
| BG-08 | `evaluation_reports` (`release_attestation_id`, `authorization_state`, `UNIQUE(report_id)`) | Plain `Report` | schema.json; data-dictionary "Report receipt, authorization and OCR readiness are separate states" | Separate authorization state that gates council visibility. |
| BG-09 | `evaluation_disclosures` (all columns) | Generic `AuditEvent` file_viewed/downloaded (`file_delivery.py:104-108`) without scope | schema.json | Log accessor, release scope, exact file version and action for medical reads. |
| BG-10 | `external_report_links` (`revoked_at`, `used_submission_at`, `issued_at`; `UNIQUE(token_hash)`; `CHECK(expires_at=issued_at+30 days)`) | Hash and expiry on `ReportRequest` (`services/reports.py:145-146`), overwritten on reissue | schema.json; permissions.md "Revoke on replacement/paper completion/cancellation/closure/submission" | One row per issued link, so replacement revokes it and keeps its history. |
| BG-11 | `declaration_versions` (`purpose`, `version`, `text_en`, `text_ar`, `digest`, `published_by_id`, `published_at`) | Embedded in `QuestionnaireVersion` (`models.py:223-236`), reused by `MedicalRelease.declaration` | schema.json | Independent immutable declaration versions with a digest. Submissions and releases reference them. |

## P2: workflow-blocking

| ID | Table / field / constraint | Current implementation | Action |
| --- | --- | --- | --- |
| BG-12 | `application_person_assertions`, `application_marriage_assertions`, `application_separation_assertions`, `application_repeat_entries`, `application_children`, `application_restraining_orders`, `application_prior_records`, `application_answers`, `application_selected_grounds`, `ground_definitions` | `AnswerRevision.answers` JSON | Typed rows per revision, after the applicant field mapping (#1) and answer-state semantics (*decision* DN-5) are accepted. Needed for #14 PA01–PA05 and the shared factual overview. |
| BG-13 | `decrees` `UNIQUE(proceeding_id)`, `CHECK(language IN ('en','ar','both'))`, `template_version_id`, `prepared_by_id` | `Decree.decision` is one-to-one with a decision **revision** | Add the proceeding FK and uniqueness so a second revision of one proceeding cannot get a second decree. |
| BG-14 | `decision_types`, `decree_template_versions` | `DecisionRevision.type` free text; no templates | Type catalog (seed from `prototype-decision-types.json` only after owner approval) and bilingual template versions (#14 PA23). |
| BG-15 | `staff_memberships` `UNIQUE INDEX staff_current_account (account_id) WHERE active_until IS NULL` | Not declared | Add the partial unique index. |
| BG-16 | Staff references (X3): `case_assignments.member_id/president_id`, `council_votes.voting_member_id`, `presidential_approvals.president_member_id`, `case_hearings.presenter_member_id`, `session_attendance`/`hearing_attendance.member_id`, `report_templates.owner_member_id`, `text_review_events.reviewer_member_id`, `decree_certificates.president_member_id` | FKs to `Account`; `Account.role` duplicates `StaffRole` | Point at `staff_memberships` so the role in force at action time is retained. Retire `Account.role` as an authority source. |
| BG-17 | `case_assignments` `starts_at`, `ends_at`, `session_id`; `UNIQUE INDEX one_case_manager WHERE ends_at IS NULL` | Append-only rows plus `Case.assigned_member` | Interval rows with the partial unique index. |
| BG-18 | `payment_allocations` (`UNIQUE(attempt_id)`), `payment_attempts` (`obligation_id`, `candidate_id`, `provider`, `idempotency_key`, `amount_minor`, `currency`; `UNIQUE(provider,provider_reference)`), `filing_candidates.idempotency_key`, `refund_events` actor/reason | `CheckoutIntent` serves as both candidate and attempt; allocation implicit | Split candidate from attempt, allocate each charge exactly once, and attribute refunds. |
| BG-19 | `application_submissions` `previous_submission_id`, `declaration_version_id`, `signature_file_version_id`, `digest` | `Submission` with attestation JSON | Link signing evidence and the resubmission chain. |
| BG-20 | `communications` `direction`, `subject`, `proceeding_id`, `template_snapshot`; CHECKs on `channel`/`email_timing`; `communication_recipients.account_id/external_email/recipient_snapshot`; `reply_routes`, `inbound_email_receipts`, `delivery_events`; `channel_deliveries` FK to recipient or notification | `Message` portal-only; `Outbox` unlinked | Support inbound and external recipients (#14 PA21). Link deliveries to source rows and record provider events. |
| BG-21 | `case_hearings` `occurred_at`, `result`, `case_id`; `hearing_outcome_revisions` `version` (`UNIQUE(hearing_id,version)`), `applicant_message_snapshot`, `communication_id`; `hearing_appeals` | `Hearing`, unversioned `HearingOutcome` | Version outcomes and tie each to the applicant message sent. Link multiple appeals to one hearing. |
| BG-22 | `agenda_requests` | Direct placement (`services/council.py:231`) | Record the assigned member's request and its outcome. |
| BG-23 | `identity_consolidations`, `identity_review_holds` (`matching_rule`, `protected_candidate_snapshot`, `status`, `resolved_by_id`, `resolved_at`), `case_association_events`, `account_email_versions` | `Application.duplicate_hold` boolean; nothing else | Retain matching evidence and resolution provenance. |
| BG-24 | `person_active_draft_claims`, `pending_appeal_claims`, `person_open_case_claims.party_id` | Uniqueness per owner **account** (`one_petition_draft`, `one_pending_appeal`) | Enforce per canonical **person**, as approved. |
| BG-25 | `files.visibility` CHECK (`applicant_own`, `council_only`, `medical_scoped`, `decree_entitled`); `owner_party_id`; `file_versions` `CHECK(num_nonnulls(uploaded_by_id,external_link_id)=1)`, `wrong_upload_removed_at`; `file_context_links` typed | `Attachment.visibility` default `'own'`, no CHECK; context is a string | Align vocabulary and add CHECKs and typed context links (#14 PA25). |
| BG-26 | `search_documents` | External Meilisearch only | Persist index provenance and security scope so the index can be rebuilt or reconciled. |
| BG-27 | `integration_configurations` | Environment variables | Ordered provider rows with secret references (no plaintext). |
| BG-28 | `report_requests.kind` CHECK vocabulary; `sent_intake_question_snapshots`; `report_answers`; `report_source_links` | `kind='intake'`; questions and answers in JSON | Typed sent-question snapshots so answers and source links can FK them. |
| BG-29 | `party_withdrawals` | `Party.withdrawn_at` | *Decision* DN-2, then attributed withdrawal rows. |
| BG-30 | `applications.purpose` / `appeal_applications` for closed-case later filings | `Application.origin='closed_case_intake'` | *Decision* DN-1. |

## P3: completeness (summary)

Cross-cutting:

- **X1:** add `request_id` correlation to the 40 attributed tables that lack it.
- **X2:** add `row_version` to the 8 root tables.
- **X4:** add `digest` to the 9 versioned tables.
- **X5:** add the remaining enumeration CHECKs, for example `cases.origin/status`,
  `case_proceedings.kind/status`, `fee_obligations.disposition`,
  `council_votes.vote`, `appeal_dispositions.result`, `recordings` exactly-one
  source, `testimony_appointment_versions` `ends_at>starts_at`,
  `session_agenda_items` `part` and `UNIQUE(session_id,part,position)`, and
  `transcript_versions` `UNIQUE(recording_id,kind,language,version)`.

Missing optional or administrative tables: `dioceses`, `parishes`,
`ctm_applicants`, `document_categories`, `topic_groups`,
`topic_category_memberships`, `category_question_memberships`,
`recommended_providers`, `upload_sessions`, `file_name_events`,
`draft_schema_migrations`, `template_publication_submissions`,
`translation_prompt_versions`, `translation_jobs`, `translation_versions`,
`ui_resource_versions`, `recovery_manifests`, `email_attachment_returns`,
`registration_invitation_events`, `verification_tokens`.

## Documentation corrections on PR #7

- `docs/implementation/status.md:53` says forced RLS covers 23 tables. It is now 63.
- `docs/implementation/validation-results.json` says `implemented_domain_models: 58`.
  It is now 63.
- `docs/implementation/schema-reconciliation.json`:
  - 14 rows name the wrong candidate adapter (listed in README).
  - 6 rows list alias-only columns as missing. This contradicts
    `schema-gap-review.md`.
  - 10 rows omit a partial adapter or a constraint gap.
