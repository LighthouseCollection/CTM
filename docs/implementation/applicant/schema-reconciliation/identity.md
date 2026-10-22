# Identity and case ownership

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `persons` | `tribunal.Person` | `identity_state`, `row_version` | None mapped |
| `person_identity_versions` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `person_id`, `version`, `first_name_en`, `last_name_en`, `name_ar`, `birth_date`, `gender`, `facts`, `source` | tribunal.Person.first_name |
| `accounts` | `tribunal.Account` | `status`, `row_version` | None mapped |
| `account_identities` | `No standalone mapping` | `id`, `created_at`, `account_id`, `provider`, `issuer`, `subject`, `tenant_id`, `verified_email`, `linked_at`, `revoked_at` | tribunal.Account.microsoft_subject |
| `account_email_versions` | `No standalone mapping` | `id`, `created_at`, `account_id`, `email`, `normalized_email`, `verified_at`, `superseded_at` | tribunal.Account.email |
| `verification_tokens` | `No standalone mapping` | `id`, `created_at`, `account_id`, `purpose`, `token_hash`, `expires_at`, `consumed_at`, `revoked_at` | None mapped |
| `app_sessions` | `No standalone mapping` | `id`, `created_at`, `account_id`, `session_hash`, `provider_identity_id`, `authenticated_at`, `revoked_at`, `provider_expires_at` | None mapped |
| `tribunals` | `tribunal.Tribunal` | None; semantics still unverified | None mapped |
| `staff_memberships` | `tribunal.StaffMembership` | None; semantics still unverified | None mapped |
| `staff_roles` | `tribunal.StaffRole` | None; semantics still unverified | None mapped |
| `account_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `account_id`, `event_type`, `restricted_details` | None mapped |
| `identity_consolidations` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `source_person_id`, `target_person_id`, `primary_account_id`, `disabled_account_id`, `evidence` | None mapped |
| `identity_review_holds` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `application_id`, `matching_rule`, `protected_candidate_snapshot`, `status`, `resolved_by_id`, `resolved_at` | tribunal.Application.duplicate_hold |
| `ctm_applicants` | `No standalone mapping` | `id`, `created_at`, `person_id`, `tribunal_id`, `internal_temporary_label` | None mapped |
| `dioceses` | `No standalone mapping` | `id`, `created_at`, `name_en`, `name_ar`, `contact`, `active` | None mapped |
| `parishes` | `No standalone mapping` | `id`, `created_at`, `diocese_id`, `name_en`, `name_ar`, `location`, `active` | None mapped |
| `marriages` | `No standalone mapping` | `id`, `created_at`, `marriage_date`, `spouse_birth_date_low`, `spouse_birth_date_high`, `matching_state` | tribunal.Case.marriage_date |
| `cases` | `tribunal.Case` | `tribunal_id`, `marriage_id`, `opened_at`, `row_version` | None mapped |
| `case_identifiers` | `No standalone mapping` | `id`, `created_at`, `case_id`, `reference`, `namespace`, `is_primary`, `allocation_date`, `daily_sequence` | tribunal.Case.number |
| `case_number_counters` | `tribunal.CaseNumberCounter` | `id`, `created_at` | None mapped |
| `case_parties` | `tribunal.Party` | `applicant_id`, `participation_state` | None mapped |
| `applicant_references` | `No standalone mapping` | `id`, `created_at`, `party_id`, `reference`, `origin`, `issued_components`, `issued_at` | tribunal.Party.reference |
| `person_open_case_claims` | `tribunal.OpenCaseClaim` | `id`, `created_at`, `party_id` | None mapped |
| `person_active_draft_claims` | `No standalone mapping` | `id`, `created_at`, `person_id`, `application_id` | None mapped |
| `case_association_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `case_id`, `application_id`, `matching_rule`, `source_snapshot`, `result` | None mapped |
| `case_party_onboarding` | `tribunal.PendingPartyLink` | `party_id`, `activated_account_id`, `activated_at` | None mapped |
| `registration_invitation_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `onboarding_id`, `communication_id` | None mapped |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
