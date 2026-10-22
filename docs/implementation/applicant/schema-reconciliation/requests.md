# Own requests, responses and medical consent

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `report_requests` | `tribunal.ReportRequest` | `identifier_text`, `closed_at`, `template_version_id`, `row_version` | None mapped |
| `sent_intake_question_snapshots` | `No standalone mapping` | `id`, `created_at`, `request_id`, `source_question_version_id`, `question_code`, `position`, `text_en`, `text_ar`, `source_context_snapshot` | tribunal.ReportRequest.questions |
| `reports` | `tribunal.Report` | `case_id`, `proceeding_id`, `subject_party_id`, `parent_report_id`, `external_author_name`, `recorded_by_id`, `title`, `status`, `submitted_at`, `row_version` | None mapped |
| `report_revisions` | `tribunal.ReportRevision` | `request_id`, `predecessor_id`, `narrative`, `digest` | None mapped |
| `report_answers` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `question_snapshot_id`, `answer_type`, `value` | tribunal.ReportRevision.answers |
| `report_source_links` | `No standalone mapping` | `id`, `created_at`, `report_revision_id`, `question_snapshot_id`, `source_application_revision_id`, `source_file_version_id`, `question_code`, `context_snapshot`, `confirmation` | tribunal.ReportRevision.answers |
| `recommended_providers` | `No standalone mapping` | `id`, `created_at`, `display_name`, `specialty`, `contact`, `active` | None mapped |
| `evaluation_requests` | `No standalone mapping` | `id`, `created_at`, `report_request_id`, `subject_party_id`, `purpose`, `provider_details`, `recommended_provider_snapshots` | tribunal.ReportRequest.kind |
| `evaluation_release_attestations` | `No standalone mapping` | `id`, `created_at`, `evaluation_request_id`, `declaration_version_id`, `subject_person_id`, `signer_person_id`, `signature_file_version_id`, `signed_at`, `language`, `exact_text`, `purpose`, `attestation` | tribunal.MedicalRelease.signature_id |
| `evaluation_release_scopes` | `No standalone mapping` | `id`, `created_at`, `attestation_id`, `recipient_scope`, `purpose`, `file_scope` | tribunal.MedicalRelease.scope |
| `evaluation_reports` | `No standalone mapping` | `id`, `created_at`, `evaluation_request_id`, `report_id`, `release_attestation_id`, `provider_details`, `completion_date`, `authorization_state` | tribunal.Report.request_id |
| `evaluation_disclosures` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `evaluation_report_id`, `release_scope_id`, `file_version_id`, `action` | tribunal.AuditEvent.action |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
