# Appeal entry, additions and disposition

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `appeal_applications` | `No standalone mapping` | `id`, `created_at`, `application_id`, `case_id`, `party_id`, `challenged_decision_id`, `challenged_decree_id`, `status` | tribunal.Application.kind |
| `pending_appeal_claims` | `No standalone mapping` | `id`, `created_at`, `case_id`, `person_id`, `appeal_id` | tribunal.Application.status |
| `appeal_supplements` | `tribunal.AppealSupplement` | `request_id`, `appeal_id` | None mapped |
| `hearing_appeals` | `No standalone mapping` | `id`, `created_at`, `hearing_id`, `appeal_id` | tribunal.AppealDisposition.hearing_id |
| `appeal_dispositions` | `tribunal.AppealDisposition` | `request_id`, `appeal_id` | None mapped |
| `proceeding_appeals` | `No standalone mapping` | `id`, `created_at`, `proceeding_id`, `appeal_id` | tribunal.AppealDisposition.reopened_proceeding_id |
| `appeal_withdrawals` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `appeal_id` | tribunal.Application.status |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
