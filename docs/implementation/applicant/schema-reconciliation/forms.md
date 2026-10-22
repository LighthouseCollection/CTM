# Questionnaires, declarations and question wording

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `questionnaires` | `No standalone mapping` | `id`, `created_at`, `code`, `purpose` | tribunal.QuestionnaireVersion.purpose |
| `questionnaire_versions` | `tribunal.QuestionnaireVersion` | `questionnaire_id`, `state`, `digest`, `published_by_id`, `published_at` | None mapped |
| `declaration_versions` | `No standalone mapping` | `id`, `created_at`, `purpose`, `version`, `text_en`, `text_ar`, `digest`, `published_by_id`, `published_at` | tribunal.QuestionnaireVersion.declaration_en |
| `ground_definitions` | `No standalone mapping` | `id`, `created_at`, `code`, `version`, `label_en`, `label_ar`, `retired_at` | tribunal.QuestionnaireVersion.definition |
| `report_questions` | `tribunal.ReportQuestion` | `retired_at` | None mapped |
| `report_question_versions` | `No standalone mapping` | `id`, `created_at`, `question_id`, `version`, `wording_en`, `wording_ar`, `conditional_guidance`, `published_by_id`, `published_at` | tribunal.ReportQuestion.version |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
