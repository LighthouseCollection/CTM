# Private originals, context and provenance

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `document_categories` | `No standalone mapping` | `id`, `created_at`, `code`, `label_en`, `label_ar`, `row_version`, `retired_at` | None mapped |
| `files` | `tribunal.Attachment` | `owner_party_id`, `category_id`, `row_version` | None mapped |
| `file_versions` | `tribunal.FileVersion` | `uploaded_at`, `technical_state`, `wrong_upload_removed_at` | None mapped |
| `file_name_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `file_version_id`, `previous_name`, `new_name`, `category_snapshot` | None mapped |
| `file_context_links` | `No standalone mapping` | `id`, `created_at`, `file_version_id`, `application_revision_id`, `repeat_entry_id`, `report_revision_id`, `medical_report_id`, `question_code`, `purpose`, `description` | tribunal.Attachment.context |
| `submission_file_manifest` | `No standalone mapping` | `id`, `created_at`, `submission_id`, `file_version_id`, `metadata_snapshot` | tribunal.Submission.manifest |
| `upload_sessions` | `No standalone mapping` | `id`, `created_at`, `file_id`, `uploader_id`, `external_link_id`, `expected_bytes`, `capture_kind`, `status`, `expires_at`, `completed_version_id` | None mapped |
| `file_technical_events` | `tribunal.FileTechnicalEvent` | `actor_id`, `request_id`, `engine_version` | None mapped |
| `file_derivatives` | `No standalone mapping` | `id`, `created_at`, `source_version_id`, `kind`, `object_key`, `extracted_text`, `engine_version`, `languages`, `status`, `checksum_sha256` | tribunal.DocumentText.text |
| `file_access_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `file_version_id`, `action`, `result`, `correlation_id` | None mapped |
| `search_documents` | `No standalone mapping` | `id`, `created_at`, `case_id`, `party_id`, `source_kind`, `source_id`, `source_version_id`, `security_scope`, `locale`, `index_generation`, `indexed_at` | tribunal.DocumentText.text |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
