# Draft answers, assertions and repeat identity

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `applications` | `tribunal.Application` | `owner_person_id` | None mapped |
| `application_revisions` | `tribunal.AnswerRevision` | `request_id`, `predecessor_id`, `digest` | None mapped |
| `application_person_assertions` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `subject`, `first_name_en`, `middle_name_en`, `last_name_en`, `name_ar`, `birth_date`, `gender`, `nationality`, `birth_country`, `address`, `contacts`, `immigration_status`, `parish`, `father_of_confession`, `residence_country`, `religious_affiliation`, `denomination`, `additional_facts`, `answer_states` | tribunal.AnswerRevision.answers |
| `application_marriage_assertions` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `church_marriage_date`, `certificate_number`, `church_name`, `church_location`, `diocese`, `officiating_priest`, `outside_coptic_marriage`, `outside_denomination`, `additional_facts`, `answer_states` | tribunal.AnswerRevision.answers |
| `application_separation_assertions` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `separation_date`, `initiated_by`, `civil_divorce_date`, `court_name`, `court_case_number`, `facts`, `answer_states` | tribunal.AnswerRevision.answers |
| `application_repeat_entries` | `No standalone mapping` | `id`, `created_at`, `application_id`, `collection_code` | tribunal.AnswerRevision.answers |
| `application_children` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `entry_id`, `names`, `birth_date`, `gender`, `lives_with`, `answer_states` | tribunal.AnswerRevision.answers |
| `application_restraining_orders` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `entry_id`, `court_name`, `court_case_number`, `current_status`, `order_date`, `expiry_date`, `named_person`, `answer_states` | tribunal.AnswerRevision.answers |
| `application_prior_records` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `entry_id`, `kind`, `record_date`, `spouse_name`, `ecclesiastical_permit`, `council_or_diocese`, `outcome`, `priest_name`, `answer_states` | tribunal.AnswerRevision.answers |
| `application_answers` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `question_code`, `entry_id`, `answer_type`, `answer_state`, `value` | tribunal.AnswerRevision.answers |
| `application_selected_grounds` | `No standalone mapping` | `id`, `created_at`, `revision_id`, `ground_id` | tribunal.AnswerRevision.answers |
| `application_answer_changes` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `application_id`, `from_revision_id`, `to_revision_id`, `question_code`, `entry_id`, `before_value`, `after_value` | tribunal.AnswerRevision.answers |
| `draft_schema_migrations` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `application_id`, `from_version_id`, `to_version_id`, `preserved_mapping`, `notice_id` | None mapped |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
