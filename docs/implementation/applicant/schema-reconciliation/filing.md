# Filing snapshots, completeness and withdrawal

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `filing_candidates` | `tribunal.CheckoutIntent` | `idempotency_key` | None mapped |
| `application_submissions` | `tribunal.Submission` | `candidate_id`, `previous_submission_id`, `declaration_version_id`, `signature_file_version_id`, `received_at`, `digest` | None mapped |
| `application_completeness_reviews` | `tribunal.CompletenessReview` | `request_id` | None mapped |
| `party_withdrawals` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `party_id`, `application_id`, `on_behalf` | tribunal.Party.withdrawn_at |
| `case_proceedings` | `tribunal.Proceeding` | `opened_at`, `appeal_decree_sequence` | None mapped |
| `case_lifecycle_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `case_id`, `proceeding_id`, `event_type`, `source_reference` | tribunal.AuditEvent.action |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
