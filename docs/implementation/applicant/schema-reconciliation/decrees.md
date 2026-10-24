# Decision provenance and released certificates

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `decision_types` | `No standalone mapping` | `id`, `created_at`, `code`, `label_en`, `label_ar`, `entitlement_rule`, `active` | None mapped |
| `case_decision_versions` | `tribunal.DecisionRevision` | `request_id`, `case_id`, `hearing_id`, `type_id`, `grounds_reason`, `party_outcomes` | None mapped |
| `council_votes` | `tribunal.Vote` | `request_id`, `supersedes_vote_id` | None mapped |
| `presidential_approvals` | `tribunal.PresidentialApproval` | `request_id`, `approved_at`, `revoked_at` | None mapped |
| `decree_template_versions` | `No standalone mapping` | `id`, `created_at`, `type_id`, `version`, `content_en`, `content_ar`, `layout_definition`, `published_by_id`, `digest` | None mapped |
| `decrees` | `tribunal.Decree` | `case_id`, `proceeding_id`, `template_version_id`, `prepared_by_id` | None mapped |
| `decree_certificates` | `No standalone mapping` | `id`, `created_at`, `decree_id`, `signed_file_version_id`, `president_member_id`, `signature_method`, `signature_metadata`, `prepared_by_id` | tribunal.Decree.signed_file_id |
| `decree_issuance_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `decree_id`, `certificate_id`, `approval_id`, `issued_at` | tribunal.Decree.issued_at |
| `decree_entitlements` | `No standalone mapping` | `id`, `created_at`, `decree_id`, `party_id`, `entitlement` | tribunal.DecisionRevision.entitlements |
| `decree_release_events` | `tribunal.DecreeRelease` | `request_id`, `entitlement_id`, `certificate_id` | None mapped |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
