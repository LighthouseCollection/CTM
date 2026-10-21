# CTM field-level data dictionary

Generated from `generate_schema.py`. JSONB is limited to versioned configuration, attributed structured evidence, variable answers, snapshots or safe event metadata. Core relations, ownership, payments and lifecycle references remain typed columns.

Every table has an opaque UUID primary key and UTC server creation timestamp. All foreign keys default to RESTRICT; intentional eligible draft cleanup requires explicit child-first transactional deletion. No blanket cascade.

## persons

Stable person identity; consolidation never rewrites original event actors

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| canonical_person_id | uuid | No | → persons |
| identity_state | text | Yes |  |
| row_version | bigint | Yes | 1 |

Database constraints: Primary key and declared foreign keys.

## person_identity_versions

Attributed identity corrections; issued CTM references stay frozen

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| person_id | uuid | Yes | → persons |
| version | integer | Yes |  |
| first_name_en | text | No |  |
| last_name_en | text | No |  |
| name_ar | text | No |  |
| birth_date | date | No |  |
| gender | text | No |  |
| facts | jsonb | Yes |  |
| source | text | Yes |  |

Database constraints: UNIQUE(person_id,version); CHECK(gender IS NULL OR gender IN ('M','F'))

## accounts

Provider-only account; no usable local password credential

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| person_id | uuid | No | → persons |
| status | text | Yes |  |
| ui_locale | text | Yes | 'en' |
| notification_locale | text | Yes | 'en' |
| row_version | bigint | Yes | 1 |

Database constraints: CHECK(status IN ('pending','active','suspended','disabled')); CHECK(ui_locale IN ('en','ar')); CHECK(notification_locale IN ('en','ar'))

## account_identities

Bind validated issuer and subject, never email-only role inference

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| account_id | uuid | Yes | → accounts |
| provider | text | Yes |  |
| issuer | text | Yes |  |
| subject | text | Yes |  |
| tenant_id | text | No |  |
| verified_email | text | No |  |
| linked_at | timestamptz | Yes |  |
| revoked_at | timestamptz | No |  |

Database constraints: UNIQUE(issuer,subject); CHECK(provider IN ('microsoft','google','apple'))

## account_email_versions

Verified contact history; changing email does not rewrite filings

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| account_id | uuid | Yes | → accounts |
| email | text | Yes |  |
| normalized_email | text | Yes |  |
| verified_at | timestamptz | No |  |
| superseded_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## verification_tokens

Hashed one-use email/invitation token; not password recovery

Domain: identity. Retention: transient_secret_metadata.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| account_id | uuid | No | → accounts |
| purpose | text | Yes |  |
| token_hash | text | Yes |  |
| expires_at | timestamptz | Yes |  |
| consumed_at | timestamptz | No |  |
| revoked_at | timestamptz | No |  |

Database constraints: UNIQUE(token_hash)

## app_sessions

Server sessions; no application inactivity logout; revocation remains enforceable

Domain: identity. Retention: security_policy.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| account_id | uuid | Yes | → accounts |
| session_hash | text | Yes |  |
| provider_identity_id | uuid | Yes | → account_identities |
| authenticated_at | timestamptz | Yes |  |
| revoked_at | timestamptz | No |  |
| provider_expires_at | timestamptz | No |  |

Database constraints: UNIQUE(session_hash)

## tribunals

One operating tribunal, not a new multi-tenant product

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| name_en | text | Yes |  |
| name_ar | text | No |  |
| timezone | text | Yes | 'America/Los_Angeles' |

Database constraints: UNIQUE(code); CHECK(timezone='America/Los_Angeles')

## staff_memberships

Explicit admin-authorized council enrollment

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| account_id | uuid | Yes | → accounts |
| tribunal_id | uuid | Yes | → tribunals |
| appointed_by_id | uuid | Yes | → accounts |
| active_from | timestamptz | Yes |  |
| active_until | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## staff_roles

Effective role grants; only existing admin creates council membership

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| membership_id | uuid | Yes | → staff_memberships |
| role | text | Yes |  |
| granted_by_id | uuid | Yes | → accounts |
| revoked_at | timestamptz | No |  |

Database constraints: CHECK(role IN ('admin','secretary','president','member'))

## account_events

Status changes, role changes, identity linking and authentication events

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| account_id | uuid | No | → accounts |
| event_type | text | Yes |  |
| restricted_details | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## identity_consolidations

Verified primary account and canonical person; retained duplicate histories

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| source_person_id | uuid | Yes | → persons |
| target_person_id | uuid | Yes | → persons |
| primary_account_id | uuid | Yes | → accounts |
| disabled_account_id | uuid | No | → accounts |
| evidence | jsonb | Yes |  |

Database constraints: CHECK(source_person_id<>target_person_id)

## identity_review_holds

Exact duplicate-person review blocks payment/submission, not draft saves

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| application_id | uuid | Yes | → applications |
| matching_rule | text | Yes |  |
| protected_candidate_snapshot | jsonb | Yes |  |
| status | text | Yes |  |
| resolved_by_id | uuid | No | → accounts |
| resolved_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## ctm_applicants

CTM identity independent of account and case reference

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| person_id | uuid | Yes | → persons |
| tribunal_id | uuid | Yes | → tribunals |
| internal_temporary_label | text | No |  |

Database constraints: UNIQUE(person_id,tribunal_id)

## dioceses

Optional directory; submitted text assertions remain original

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| name_en | text | Yes |  |
| name_ar | text | No |  |
| contact | jsonb | Yes |  |
| active | boolean | Yes | true |

Database constraints: Primary key and declared foreign keys.

## parishes

Optional parish reference; no forced normalization of submitted spelling

Domain: identity. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| diocese_id | uuid | No | → dioceses |
| name_en | text | Yes |  |
| name_ar | text | No |  |
| location | jsonb | Yes |  |
| active | boolean | Yes | true |

Database constraints: Primary key and declared foreign keys.

## marriages

Matching registry separate from both parties attributed assertions

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| marriage_date | date | No |  |
| spouse_birth_date_low | date | No |  |
| spouse_birth_date_high | date | No |  |
| matching_state | text | Yes |  |

Database constraints: CHECK(spouse_birth_date_low IS NULL OR spouse_birth_date_high IS NULL OR spouse_birth_date_low<=spouse_birth_date_high)

## cases

Shared permanent case with original number and separate proceedings

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| tribunal_id | uuid | Yes | → tribunals |
| marriage_id | uuid | No | → marriages |
| origin | text | Yes |  |
| status | text | Yes |  |
| opened_at | timestamptz | No |  |
| closed_at | timestamptz | No |  |
| row_version | bigint | Yes | 1 |

Database constraints: CHECK(origin IN ('new','historical')); CHECK(status IN ('open','closed'))

## case_identifiers

Original, canonical and alias identifiers; never reused or renumbered

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| reference | text | Yes |  |
| namespace | text | Yes |  |
| is_primary | boolean | Yes |  |
| allocation_date | date | No |  |
| daily_sequence | integer | No |  |

Database constraints: CHECK(daily_sequence IS NULL OR daily_sequence BETWEEN 1 AND 99)

## case_number_counters

Atomic Los Angeles daily sequence allocation

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| local_date | date | Yes |  |
| last_value | integer | Yes |  |

Database constraints: UNIQUE(local_date); CHECK(last_value BETWEEN 0 AND 99)

## case_parties

Known spouse and participating applicant are different states

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| person_id | uuid | No | → persons |
| applicant_id | uuid | No | → ctm_applicants |
| party_slot | text | Yes |  |
| participation_state | text | Yes |  |
| source_name_snapshot | jsonb | Yes |  |

Database constraints: UNIQUE(case_id,party_slot); CHECK(party_slot IN ('A','B'))

## applicant_references

Frozen case-based or historical applicant reference, never an access key

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| party_id | uuid | Yes | → case_parties |
| reference | text | Yes |  |
| origin | text | Yes |  |
| issued_components | jsonb | Yes |  |
| issued_at | timestamptz | Yes |  |

Database constraints: UNIQUE(party_id)

## person_open_case_claims

One open case per canonical participating person; includes historical cases

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| person_id | uuid | Yes | → persons |
| case_id | uuid | Yes | → cases |
| party_id | uuid | Yes | → case_parties |

Database constraints: UNIQUE(person_id); UNIQUE(party_id)

## person_active_draft_claims

One new-case draft; mutually exclusive with different open case claim

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| person_id | uuid | Yes | → persons |
| application_id | uuid | Yes | → applications |

Database constraints: UNIQUE(person_id); UNIQUE(application_id)

## case_proceedings

Closed original proceedings never unlock; accepted appeal creates new section

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| kind | text | Yes |  |
| status | text | Yes |  |
| opened_at | timestamptz | Yes |  |
| closed_at | timestamptz | No |  |
| appeal_decree_sequence | integer | No |  |

Database constraints: CHECK(kind IN ('initial','appeal')); CHECK(status IN ('open','closed')); CHECK(appeal_decree_sequence IS NULL OR appeal_decree_sequence>0)

## case_lifecycle_events

Opening, closure, reopening, retained association and historical correction history

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | No | → case_proceedings |
| event_type | text | Yes |  |
| source_reference | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## case_association_events

Preserved matching evidence, original case aliases and wrong-association corrections

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| case_id | uuid | Yes | → cases |
| application_id | uuid | No | → applications |
| matching_rule | text | Yes |  |
| source_snapshot | jsonb | Yes |  |
| result | text | Yes |  |

Database constraints: Primary key and declared foreign keys.

## case_party_onboarding

Pending intended email; activate only on matching verified registration

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| party_id | uuid | Yes | → case_parties |
| first_name | text | Yes |  |
| last_name | text | Yes |  |
| normalized_email | text | Yes |  |
| entered_by_id | uuid | Yes | → accounts |
| status | text | Yes |  |
| activated_account_id | uuid | No | → accounts |
| activated_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## registration_invitation_events

Staff-initiated invitation email only; not an automatic enrollment side effect

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| onboarding_id | uuid | Yes | → case_party_onboarding |
| communication_id | uuid | Yes | → communications |

Database constraints: Primary key and declared foreign keys.

## case_assignments

President-authorized single current case manager; separate entering actor

Domain: cases. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| member_id | uuid | Yes | → staff_memberships |
| president_id | uuid | Yes | → staff_memberships |
| recorded_by_id | uuid | Yes | → accounts |
| session_id | uuid | No | → council_sessions |
| authorized_at | timestamptz | Yes |  |
| starts_at | timestamptz | Yes |  |
| ends_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## historical_entry_workspaces

Private admin historical entry staging; no fee or fabricated required facts

Domain: cases. Retention: historical_workspace.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| created_by_id | uuid | Yes | → accounts |
| draft_payload | jsonb | Yes |  |
| published_case_id | uuid | No | → cases |
| declared_status | text | No |  |
| finalized_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## questionnaires

Versioned applicant/appeal form identity

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| purpose | text | Yes |  |

Database constraints: UNIQUE(code)

## questionnaire_versions

Immutable published form; exact version retained on submission

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| questionnaire_id | uuid | Yes | → questionnaires |
| version | integer | Yes |  |
| state | text | Yes |  |
| definition | jsonb | Yes |  |
| digest | text | Yes |  |
| published_by_id | uuid | No | → accounts |
| published_at | timestamptz | No |  |

Database constraints: UNIQUE(questionnaire_id,version)

## declaration_versions

Exact bilingual declaration or medical-release wording

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| purpose | text | Yes |  |
| version | integer | Yes |  |
| text_en | text | Yes |  |
| text_ar | text | Yes |  |
| digest | text | Yes |  |
| published_by_id | uuid | Yes | → accounts |
| published_at | timestamptz | Yes |  |

Database constraints: UNIQUE(purpose,version)

## applications

Private draft, independent filing owner, same application on return/resubmission

Domain: filings. Retention: draft_until_first_submission_then_permanent.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| owner_person_id | uuid | Yes | → persons |
| owner_account_id | uuid | Yes | → accounts |
| case_id | uuid | No | → cases |
| party_id | uuid | No | → case_parties |
| proceeding_id | uuid | No | → case_proceedings |
| purpose | text | Yes |  |
| status | text | Yes |  |
| origin | text | Yes |  |
| questionnaire_version_id | uuid | Yes | → questionnaire_versions |
| last_applicant_activity_at | timestamptz | Yes |  |
| first_submitted_at | timestamptz | No |  |
| row_version | bigint | Yes | 1 |

Database constraints: CHECK(purpose IN ('petition','appeal')); CHECK(status IN ('draft','submitted','returned','accepted','withdrawn','expired','deleted'))

## application_revisions

Immutable committed snapshot; frozen revision at payment/submission

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| application_id | uuid | Yes | → applications |
| version | integer | Yes |  |
| predecessor_id | uuid | No | → application_revisions |
| questionnaire_version_id | uuid | Yes | → questionnaire_versions |
| digest | text | Yes |  |

Database constraints: UNIQUE(application_id,version)

## application_person_assertions

Self/spouse facts, explicit missing-value states, no shared overwrite

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| subject | text | Yes |  |
| first_name_en | text | No |  |
| middle_name_en | text | No |  |
| last_name_en | text | No |  |
| name_ar | text | No |  |
| birth_date | date | No |  |
| gender | text | No |  |
| nationality | text | No |  |
| birth_country | text | No |  |
| address | jsonb | Yes |  |
| contacts | jsonb | Yes |  |
| immigration_status | text | No |  |
| parish | text | No |  |
| father_of_confession | text | No |  |
| residence_country | text | No |  |
| religious_affiliation | text | No |  |
| denomination | text | No |  |
| additional_facts | jsonb | Yes |  |
| answer_states | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id,subject); CHECK(subject IN ('self','spouse')); CHECK(gender IS NULL OR gender IN ('M','F'))

## application_marriage_assertions

Exact source marriage/date/certificate assertion and prior religious affiliation

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| church_marriage_date | date | No |  |
| certificate_number | text | No |  |
| church_name | text | No |  |
| church_location | text | No |  |
| diocese | text | No |  |
| officiating_priest | text | No |  |
| outside_coptic_marriage | boolean | No |  |
| outside_denomination | text | No |  |
| additional_facts | jsonb | Yes |  |
| answer_states | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id)

## application_separation_assertions

Attributed separation/civil-divorce/counseling assertions

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| separation_date | date | No |  |
| initiated_by | text | No |  |
| civil_divorce_date | date | No |  |
| court_name | text | No |  |
| court_case_number | text | No |  |
| facts | jsonb | Yes |  |
| answer_states | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id)

## application_repeat_entries

Stable collection row identity across application revisions

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| application_id | uuid | Yes | → applications |
| collection_code | text | Yes |  |

Database constraints: Primary key and declared foreign keys.

## application_children

Child name, DOB, gender and lives-with; Unknown allowed where approved

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| entry_id | uuid | Yes | → application_repeat_entries |
| names | jsonb | Yes |  |
| birth_date | date | No |  |
| gender | text | No |  |
| lives_with | text | No |  |
| answer_states | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id,entry_id)

## application_restraining_orders

Multiple reported orders; each requires court, case number, status and copy

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| entry_id | uuid | Yes | → application_repeat_entries |
| court_name | text | No |  |
| court_case_number | text | No |  |
| current_status | text | No |  |
| order_date | date | No |  |
| expiry_date | date | No |  |
| named_person | text | No |  |
| answer_states | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id,entry_id)

## application_prior_records

Separate previous marriages, prior tribunal applications and priest-name entries

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| entry_id | uuid | Yes | → application_repeat_entries |
| kind | text | Yes |  |
| record_date | date | No |  |
| spouse_name | text | No |  |
| ecclesiastical_permit | text | No |  |
| council_or_diocese | text | No |  |
| outcome | text | No |  |
| priest_name | text | No |  |
| answer_states | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id,entry_id); CHECK(kind IN ('prior_marriage','prior_application','counseling_priest'))

## application_answers

Other versioned semantic fields; one editable binding per field

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| question_code | text | Yes |  |
| entry_id | uuid | No | → application_repeat_entries |
| answer_type | text | Yes |  |
| answer_state | text | Yes |  |
| value | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## ground_definitions

Six approved grounds with versioned bilingual labels

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| version | integer | Yes |  |
| label_en | text | Yes |  |
| label_ar | text | Yes |  |
| retired_at | timestamptz | No |  |

Database constraints: UNIQUE(code,version)

## application_selected_grounds

Multiple grounds; never council findings

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → application_revisions |
| ground_id | uuid | Yes | → ground_definitions |

Database constraints: UNIQUE(revision_id,ground_id)

## application_answer_changes

Field/repeat-entry change, actual actor/time; no reason or re-sign required

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| application_id | uuid | Yes | → applications |
| from_revision_id | uuid | Yes | → application_revisions |
| to_revision_id | uuid | Yes | → application_revisions |
| question_code | text | Yes |  |
| entry_id | uuid | No | → application_repeat_entries |
| before_value | jsonb | Yes |  |
| after_value | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## filing_candidates

Frozen checkout candidate for idempotent payment-to-submission recovery

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| application_id | uuid | Yes | → applications |
| revision_id | uuid | Yes | → application_revisions |
| idempotency_key | text | Yes |  |
| frozen_manifest | jsonb | Yes |  |
| attestation_snapshot | jsonb | Yes |  |
| state | text | Yes |  |

Database constraints: UNIQUE(idempotency_key)

## application_submissions

Immutable original or resubmission; signed version is never replaced

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| application_id | uuid | Yes | → applications |
| revision_id | uuid | Yes | → application_revisions |
| candidate_id | uuid | No | → filing_candidates |
| previous_submission_id | uuid | No | → application_submissions |
| declaration_version_id | uuid | No | → declaration_versions |
| signature_file_version_id | uuid | No | → file_versions |
| attestation | jsonb | Yes |  |
| submitted_by_id | uuid | Yes | → accounts |
| received_at | timestamptz | Yes |  |
| digest | text | Yes |  |

Database constraints: UNIQUE(candidate_id)

## application_completeness_reviews

Accept/Reject for completeness; Reject returns same filing with instructions

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| submission_id | uuid | Yes | → application_submissions |
| result | text | Yes |  |
| correction_instructions | text | No |  |

Database constraints: CHECK(result IN ('accept','reject')); CHECK(result<>'reject' OR nullif(btrim(correction_instructions),'') IS NOT NULL)

## draft_schema_migrations

Applicant drafts update to published form without losing answers; report draft rules differ

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| application_id | uuid | Yes | → applications |
| from_version_id | uuid | Yes | → questionnaire_versions |
| to_version_id | uuid | Yes | → questionnaire_versions |
| preserved_mapping | jsonb | Yes |  |
| notice_id | uuid | No | → notifications |

Database constraints: Primary key and declared foreign keys.

## party_withdrawals

Own petition withdrawal; admin may act for all; no reason or approval

Domain: filings. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| party_id | uuid | Yes | → case_parties |
| application_id | uuid | Yes | → applications |
| on_behalf | boolean | Yes |  |

Database constraints: Primary key and declared foreign keys.

## document_categories

Stable document meaning, editable labels/code; historical names recorded

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| label_en | text | Yes |  |
| label_ar | text | Yes |  |
| row_version | bigint | Yes | 1 |
| retired_at | timestamptz | No |  |

Database constraints: UNIQUE(code)

## files

Logical owner and contextual location; no independent message attachment store

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | No | → cases |
| proceeding_id | uuid | No | → case_proceedings |
| owner_application_id | uuid | No | → applications |
| owner_party_id | uuid | No | → case_parties |
| report_request_id | uuid | No | → report_requests |
| category_id | uuid | Yes | → document_categories |
| visibility | text | Yes |  |
| row_version | bigint | Yes | 1 |

Database constraints: CHECK(visibility IN ('applicant_own','council_only','medical_scoped','decree_entitled'))

## file_versions

Private immutable original; opaque key, latest safe default, version history council only

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| file_id | uuid | Yes | → files |
| version | integer | Yes |  |
| object_key | text | Yes |  |
| original_name | text | Yes |  |
| presented_name | text | Yes |  |
| size_bytes | bigint | Yes |  |
| mime_type | text | Yes |  |
| checksum_sha256 | text | Yes |  |
| uploaded_by_id | uuid | No | → accounts |
| external_link_id | uuid | No | → external_report_links |
| uploaded_at | timestamptz | Yes |  |
| technical_state | text | Yes |  |
| wrong_upload_removed_at | timestamptz | No |  |

Database constraints: UNIQUE(file_id,version); UNIQUE(object_key); CHECK(size_bytes>=0); CHECK(num_nonnulls(uploaded_by_id,external_link_id)=1)

## file_name_events

Code rename changes presented filename, never source bytes or original manifest

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| file_version_id | uuid | Yes | → file_versions |
| previous_name | text | Yes |  |
| new_name | text | Yes |  |
| category_snapshot | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## file_context_links

Correct question/order/request/evidence context, exact version and description

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| file_version_id | uuid | Yes | → file_versions |
| application_revision_id | uuid | No | → application_revisions |
| repeat_entry_id | uuid | No | → application_repeat_entries |
| report_revision_id | uuid | No | → report_revisions |
| medical_report_id | uuid | No | → evaluation_reports |
| question_code | text | No |  |
| purpose | text | Yes |  |
| description | text | No |  |

Database constraints: Primary key and declared foreign keys.

## submission_file_manifest

Exact filenames/checksums/versions retained with submitted filing

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| submission_id | uuid | Yes | → application_submissions |
| file_version_id | uuid | Yes | → file_versions |
| metadata_snapshot | jsonb | Yes |  |

Database constraints: UNIQUE(submission_id,file_version_id)

## upload_sessions

Resumable upload with final authorization and technical validation

Domain: files. Retention: transient_until_retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| file_id | uuid | Yes | → files |
| uploader_id | uuid | No | → accounts |
| external_link_id | uuid | No | → external_report_links |
| expected_bytes | bigint | No |  |
| capture_kind | text | Yes |  |
| status | text | Yes |  |
| expires_at | timestamptz | No |  |
| completed_version_id | uuid | No | → file_versions |

Database constraints: CHECK(num_nonnulls(uploader_id,external_link_id)=1)

## file_technical_events

Safety/type/size scan separate from council acceptance

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| file_version_id | uuid | Yes | → file_versions |
| task | text | Yes |  |
| engine_version | text | Yes |  |
| result | text | Yes |  |
| safe_metadata | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## file_derivatives

Private OCR, extraction, preview or media derivative; original unchanged

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| source_version_id | uuid | Yes | → file_versions |
| kind | text | Yes |  |
| object_key | text | No |  |
| extracted_text | text | No |  |
| engine_version | text | Yes |  |
| languages | jsonb | Yes |  |
| status | text | Yes |  |
| checksum_sha256 | text | No |  |

Database constraints: Primary key and declared foreign keys.

## file_access_events

Audited view/download/playback with source permission recheck

Domain: files. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| file_version_id | uuid | Yes | → file_versions |
| action | text | Yes |  |
| result | text | Yes |  |
| correlation_id | uuid | Yes |  |

Database constraints: Primary key and declared foreign keys.

## search_documents

Rebuildable Meilisearch provenance, no independent authorization

Domain: files. Retention: rebuildable.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| party_id | uuid | No | → case_parties |
| source_kind | text | Yes |  |
| source_id | uuid | Yes |  |
| source_version_id | uuid | Yes |  |
| security_scope | text | Yes |  |
| locale | text | Yes |  |
| index_generation | text | Yes |  |
| indexed_at | timestamptz | No |  |

Database constraints: UNIQUE(source_kind,source_version_id,locale)

## fee_obligations

One USD250 fee per filing; historical exemption/waiver distinct from payment

Domain: payments. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| application_id | uuid | Yes | → applications |
| amount_minor | bigint | Yes | 25000 |
| currency | text | Yes | 'USD' |
| disposition | text | Yes |  |
| assessed_at | timestamptz | Yes |  |

Database constraints: UNIQUE(application_id); CHECK(amount_minor=25000); CHECK(currency='USD'); CHECK(disposition IN ('due','paid','waived','historical_exempt'))

## fee_waivers

Admin/secretary handles outside applicant application

Domain: payments. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| obligation_id | uuid | Yes | → fee_obligations |
| reason | text | No |  |

Database constraints: Primary key and declared foreign keys.

## payment_attempts

Provider references only; no card data; browser redirect never proof

Domain: payments. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| obligation_id | uuid | Yes | → fee_obligations |
| candidate_id | uuid | Yes | → filing_candidates |
| provider | text | Yes |  |
| provider_reference | text | Yes |  |
| idempotency_key | text | Yes |  |
| amount_minor | bigint | Yes |  |
| currency | text | Yes |  |
| status | text | Yes |  |

Database constraints: UNIQUE(provider,provider_reference); UNIQUE(idempotency_key); CHECK(amount_minor>0)

## payment_events

Verified, deduplicated payment success/reversal/chargeback events

Domain: payments. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| attempt_id | uuid | Yes | → payment_attempts |
| provider_event_id | text | Yes |  |
| event_type | text | Yes |  |
| verified_at | timestamptz | Yes |  |
| safe_payload | jsonb | Yes |  |

Database constraints: UNIQUE(provider_event_id)

## payment_allocations

A successful charge is allocated to exactly one filing obligation

Domain: payments. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| attempt_id | uuid | Yes | → payment_attempts |
| obligation_id | uuid | Yes | → fee_obligations |
| submission_id | uuid | Yes | → application_submissions |
| amount_minor | bigint | Yes |  |

Database constraints: UNIQUE(attempt_id)

## refund_events

Only accidental duplicate refunds; authorization and provider result distinct

Domain: payments. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| attempt_id | uuid | Yes | → payment_attempts |
| provider_refund_id | text | No |  |
| status | text | Yes |  |
| amount_minor | bigint | Yes |  |
| reason | text | Yes |  |

Database constraints: CHECK(amount_minor>0)

## topic_groups

Accepted Topic groups; views do not duplicate questions

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| labels | jsonb | Yes |  |
| position | integer | Yes |  |

Database constraints: UNIQUE(code)

## question_categories

Reusable Question categories, not duplicate Question topic headings

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| labels | jsonb | Yes |  |
| position | integer | Yes |  |

Database constraints: UNIQUE(code)

## report_questions

Stable accepted question IDs

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| foundational | boolean | Yes |  |
| retired_at | timestamptz | No |  |

Database constraints: UNIQUE(code)

## report_question_versions

Exact main wording, optional contextual prompts and translation versions

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| question_id | uuid | Yes | → report_questions |
| version | integer | Yes |  |
| wording_en | text | Yes |  |
| wording_ar | text | No |  |
| conditional_guidance | jsonb | Yes |  |
| published_by_id | uuid | No | → accounts |
| published_at | timestamptz | No |  |

Database constraints: UNIQUE(question_id,version)

## topic_category_memberships

Reusable categories across Topic groups

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| topic_group_id | uuid | Yes | → topic_groups |
| category_id | uuid | Yes | → question_categories |
| position | integer | Yes |  |

Database constraints: UNIQUE(topic_group_id,category_id)

## category_question_memberships

Question/category mapping; selected question appears once unless explicit distinct event

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| category_id | uuid | Yes | → question_categories |
| question_id | uuid | Yes | → report_questions |
| position | integer | Yes |  |

Database constraints: UNIQUE(category_id,question_id)

## report_templates

Shared or personal template identity; personal has owner

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| scope | text | Yes |  |
| owner_member_id | uuid | No | → staff_memberships |
| title | text | Yes |  |
| retired_at | timestamptz | No |  |

Database constraints: CHECK((scope='personal' AND owner_member_id IS NOT NULL) OR (scope='shared' AND owner_member_id IS NULL))

## report_template_versions

Immutable published selection/order; no answers or private case facts in reusable templates

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| template_id | uuid | Yes | → report_templates |
| version | integer | Yes |  |
| definition | jsonb | Yes |  |
| digest | text | Yes |  |
| state | text | Yes |  |
| published_by_id | uuid | No | → accounts |

Database constraints: UNIQUE(template_id,version)

## template_publication_submissions

Publish separate shared copy; retain personal original

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| personal_version_id | uuid | Yes | → report_template_versions |
| shared_version_id | uuid | No | → report_template_versions |
| status | text | Yes |  |
| reviewed_by_id | uuid | No | → accounts |

Database constraints: Primary key and declared foreign keys.

## report_requests

Request first; assigned intake, freeform external priest or professional assessment

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | Yes | → case_proceedings |
| subject_party_id | uuid | Yes | → case_parties |
| parent_report_id | uuid | No | → reports |
| kind | text | Yes |  |
| created_by_id | uuid | Yes | → accounts |
| title | text | Yes |  |
| identifier_text | text | No |  |
| language | text | Yes |  |
| status | text | Yes |  |
| sent_at | timestamptz | No |  |
| closed_at | timestamptz | No |  |
| template_version_id | uuid | No | → report_template_versions |
| instructions | jsonb | Yes |  |
| row_version | bigint | Yes | 1 |

Database constraints: CHECK(kind IN ('applicant_intake','manager_interview','external_priest','medical','psychological')); CHECK(language IN ('en','ar','both'))

## sent_intake_question_snapshots

Immutable exact sent questions, not all optional interviewer guidance

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| request_id | uuid | Yes | → report_requests |
| source_question_version_id | uuid | No | → report_question_versions |
| question_code | text | Yes |  |
| position | integer | Yes |  |
| text_en | text | No |  |
| text_ar | text | No |  |
| source_context_snapshot | jsonb | Yes |  |

Database constraints: UNIQUE(request_id,position)

## external_report_links

External priest request only; direct link expires in30days; hash only

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| request_id | uuid | Yes | → report_requests |
| recipient_email | text | No |  |
| priest_name | text | Yes |  |
| token_hash | text | Yes |  |
| issued_at | timestamptz | Yes |  |
| expires_at | timestamptz | Yes |  |
| revoked_at | timestamptz | No |  |
| used_submission_at | timestamptz | No |  |

Database constraints: UNIQUE(token_hash); CHECK(expires_at=issued_at + interval '30 days')

## external_response_drafts

Limited request-scoped save/resume; no case browsing

Domain: reports. Retention: request_scoped.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| request_id | uuid | Yes | → report_requests |
| response | jsonb | Yes |  |
| saved_at | timestamptz | Yes |  |

Database constraints: UNIQUE(request_id)

## reports

Completed and working reports; follow-up is also an individual report

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| request_id | uuid | Yes | → report_requests |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | Yes | → case_proceedings |
| subject_party_id | uuid | Yes | → case_parties |
| parent_report_id | uuid | No | → reports |
| author_account_id | uuid | No | → accounts |
| external_author_name | text | No |  |
| recorded_by_id | uuid | No | → accounts |
| completion_date | date | No |  |
| identifier_text | text | No |  |
| title | text | Yes |  |
| method | text | Yes |  |
| status | text | Yes |  |
| submitted_at | timestamptz | No |  |
| row_version | bigint | Yes | 1 |

Database constraints: UNIQUE(request_id)

## report_revisions

Original author narrative edits while authorized/open; actual external/applicant response stays distinct

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| report_id | uuid | Yes | → reports |
| version | integer | Yes |  |
| predecessor_id | uuid | No | → report_revisions |
| narrative | jsonb | Yes |  |
| internal_observations | text | No |  |
| digest | text | Yes |  |

Database constraints: UNIQUE(report_id,version)

## report_answers

Structured or rich text typed answers separate from generated transcript

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| revision_id | uuid | Yes | → report_revisions |
| question_snapshot_id | uuid | Yes | → sent_intake_question_snapshots |
| answer_type | text | Yes |  |
| value | jsonb | Yes |  |

Database constraints: UNIQUE(revision_id,question_snapshot_id)

## report_source_links

Exact application/evidence version displayed or confirmed; never silently rewrite source

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| report_revision_id | uuid | Yes | → report_revisions |
| question_snapshot_id | uuid | No | → sent_intake_question_snapshots |
| source_application_revision_id | uuid | No | → application_revisions |
| source_file_version_id | uuid | No | → file_versions |
| question_code | text | No |  |
| context_snapshot | jsonb | Yes |  |
| confirmation | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## recordings

Whole-report or council testimony audio; finalize before transcription

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| report_id | uuid | No | → reports |
| testimony_appointment_id | uuid | No | → testimony_appointments |
| file_version_id | uuid | Yes | → file_versions |
| captured_by_id | uuid | No | → accounts |
| recording_notice | jsonb | Yes |  |
| finalized_at | timestamptz | No |  |
| duration_ms | bigint | No |  |
| origin | text | Yes |  |

Database constraints: CHECK(num_nonnulls(report_id,testimony_appointment_id)=1); CHECK(duration_ms IS NULL OR duration_ms>=0)

## processing_runs

Server-side task; local/API transcription per approved purpose; failure keeps source usable

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| recording_id | uuid | No | → recordings |
| file_version_id | uuid | No | → file_versions |
| task | text | Yes |  |
| provider | text | Yes |  |
| model_version | text | Yes |  |
| input_digest | text | Yes |  |
| status | text | Yes |  |
| safe_error | text | No |  |
| started_at | timestamptz | No |  |
| finished_at | timestamptz | No |  |

Database constraints: CHECK(num_nonnulls(recording_id,file_version_id)=1)

## transcript_versions

Original AI output plus all edits; source/mixed transcript and full English/Arabic

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| recording_id | uuid | Yes | → recordings |
| run_id | uuid | No | → processing_runs |
| kind | text | Yes |  |
| language | text | Yes |  |
| version | integer | Yes |  |
| predecessor_id | uuid | No | → transcript_versions |
| source_transcript_id | uuid | No | → transcript_versions |
| origin | text | Yes |  |
| text_content | text | Yes |  |

Database constraints: UNIQUE(recording_id,kind,language,version)

## transcript_segments

Timestamped text with applicant/council speaker labels

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| text_version_id | uuid | Yes | → transcript_versions |
| ordinal | integer | Yes |  |
| start_ms | bigint | Yes |  |
| end_ms | bigint | Yes |  |
| speaker_label | text | Yes |  |
| speaker_person_id | uuid | No | → persons |
| content | text | Yes |  |
| source_segment_id | uuid | No | → transcript_segments |

Database constraints: UNIQUE(text_version_id,ordinal); CHECK(start_ms>=0 AND end_ms>=start_ms)

## text_review_events

Exact version review; report manager versus testimony admin/secretary

Domain: reports. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| text_version_id | uuid | Yes | → transcript_versions |
| action | text | Yes |  |
| reviewer_member_id | uuid | Yes | → staff_memberships |

Database constraints: Primary key and declared foreign keys.

## recommended_providers

Optional recommended doctors; no external doctor account requirement

Domain: medical. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| display_name | text | Yes |  |
| specialty | text | Yes |  |
| contact | jsonb | Yes |  |
| active | boolean | Yes | true |

Database constraints: Primary key and declared foreign keys.

## evaluation_requests

Separate professional assessment workflow over a report request

Domain: medical. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| report_request_id | uuid | Yes | → report_requests |
| subject_party_id | uuid | Yes | → case_parties |
| purpose | text | Yes |  |
| provider_details | jsonb | Yes |  |
| recommended_provider_snapshots | jsonb | Yes |  |

Database constraints: UNIQUE(report_request_id)

## evaluation_release_attestations

Exact signed scoped release, not inferred from uploading report

Domain: medical. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| evaluation_request_id | uuid | Yes | → evaluation_requests |
| declaration_version_id | uuid | Yes | → declaration_versions |
| subject_person_id | uuid | Yes | → persons |
| signer_person_id | uuid | Yes | → persons |
| signature_file_version_id | uuid | Yes | → file_versions |
| signed_at | timestamptz | Yes |  |
| language | text | Yes |  |
| exact_text | text | Yes |  |
| purpose | text | Yes |  |
| attestation | jsonb | Yes |  |

Database constraints: CHECK(subject_person_id=signer_person_id)

## evaluation_release_scopes

Release scope applied to bytes/OCR/search/context and disclosures

Domain: medical. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| attestation_id | uuid | Yes | → evaluation_release_attestations |
| recipient_scope | jsonb | Yes |  |
| purpose | text | Yes |  |
| file_scope | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## evaluation_reports

Report receipt, authorization and OCR readiness are separate states

Domain: medical. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| evaluation_request_id | uuid | Yes | → evaluation_requests |
| report_id | uuid | Yes | → reports |
| release_attestation_id | uuid | No | → evaluation_release_attestations |
| provider_details | jsonb | Yes |  |
| completion_date | date | Yes |  |
| authorization_state | text | Yes |  |

Database constraints: UNIQUE(report_id)

## evaluation_disclosures

Accessor, release scope, exact original/derivative and timestamp

Domain: medical. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| evaluation_report_id | uuid | Yes | → evaluation_reports |
| release_scope_id | uuid | Yes | → evaluation_release_scopes |
| file_version_id | uuid | No | → file_versions |
| action | text | Yes |  |

Database constraints: Primary key and declared foreign keys.

## case_findings

Council finding never overwrites either applicant answer

Domain: review. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | Yes | → case_proceedings |
| fact_code | text | Yes |  |

Database constraints: UNIQUE(proceeding_id,fact_code)

## finding_versions

Assigned/admin/secretary revisions while proceeding open

Domain: review. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| finding_id | uuid | Yes | → case_findings |
| version | integer | Yes |  |
| value | jsonb | Yes |  |
| sources | jsonb | Yes |  |

Database constraints: UNIQUE(finding_id,version)

## case_notes

Council only; original author edits own note with current write eligibility

Domain: review. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | Yes | → case_proceedings |
| author_id | uuid | Yes | → accounts |

Database constraints: Primary key and declared foreign keys.

## note_versions

Preserve every edit; case closure locks notes

Domain: review. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| note_id | uuid | Yes | → case_notes |
| version | integer | Yes |  |
| content | text | Yes |  |

Database constraints: UNIQUE(note_id,version)

## council_sessions

One dated session; rescheduling planned meeting moves cases and removes cancelled row

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| session_date | date | Yes |  |
| reference | text | Yes |  |
| state | text | Yes |  |
| created_by_id | uuid | Yes | → accounts |
| closed_at | timestamptz | No |  |

Database constraints: UNIQUE(session_date); UNIQUE(reference)

## agenda_requests

Assigned member asks to place own case; no global agenda authority

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| case_id | uuid | Yes | → cases |
| requested_session_id | uuid | No | → council_sessions |
| placed_item_id | uuid | No | → session_agenda_items |

Database constraints: Primary key and declared foreign keys.

## session_agenda_items

Two ordered parts; one case hearing item can include both pending appeals

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| session_id | uuid | Yes | → council_sessions |
| case_id | uuid | Yes | → cases |
| part | integer | Yes |  |
| position | integer | Yes |  |
| status | text | Yes |  |
| carried_from_id | uuid | No | → session_agenda_items |

Database constraints: CHECK(part IN (1,2)); UNIQUE(session_id,part,position); UNIQUE(session_id,case_id)

## agenda_transfer_events

Case audit preserves old/new date facts without retaining cancelled meeting

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| case_id | uuid | Yes | → cases |
| from_session_snapshot | jsonb | Yes |  |
| to_session_id | uuid | No | → council_sessions |
| destination_item_id | uuid | No | → session_agenda_items |
| reason | text | Yes |  |

Database constraints: Primary key and declared foreign keys.

## session_attendance

Session default attendance; actual hearing attendance separate

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| session_id | uuid | Yes | → council_sessions |
| member_id | uuid | Yes | → staff_memberships |
| present | boolean | Yes |  |
| recorded_by_id | uuid | Yes | → accounts |

Database constraints: UNIQUE(session_id,member_id)

## case_hearings

Only assigned member presents; testimony is a limited separate segment

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| agenda_item_id | uuid | Yes | → session_agenda_items |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | No | → case_proceedings |
| presenter_member_id | uuid | Yes | → staff_memberships |
| occurred_at | timestamptz | Yes |  |
| result | text | Yes |  |

Database constraints: UNIQUE(agenda_item_id)

## hearing_attendance

Hearing-specific presence does not hide members from vote UI

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| hearing_id | uuid | Yes | → case_hearings |
| member_id | uuid | Yes | → staff_memberships |
| present | boolean | Yes |  |
| recorded_by_id | uuid | Yes | → accounts |

Database constraints: UNIQUE(hearing_id,member_id)

## hearing_outcome_revisions

Internal recommendations and applicant message remain distinct; later corrections no resend

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| hearing_id | uuid | Yes | → case_hearings |
| version | integer | Yes |  |
| internal_text | text | Yes |  |
| recommendations | text | Yes |  |
| applicant_message_snapshot | text | No |  |
| communication_id | uuid | No | → communications |

Database constraints: UNIQUE(hearing_id,version)

## testimony_appointments

Private applicant testimony invitation; never simultaneous both applicants

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| party_id | uuid | Yes | → case_parties |
| agenda_item_id | uuid | Yes | → session_agenda_items |
| status | text | Yes |  |
| created_by_id | uuid | Yes | → accounts |

Database constraints: Primary key and declared foreign keys.

## testimony_appointment_versions

Rescheduling requests fresh Confirm/Reject while preserving former response

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| appointment_id | uuid | Yes | → testimony_appointments |
| version | integer | Yes |  |
| starts_at | timestamptz | Yes |  |
| ends_at | timestamptz | No |  |
| instructions | text | Yes |  |
| attendance_location | jsonb | Yes |  |
| cancelled | boolean | Yes |  |

Database constraints: UNIQUE(appointment_id,version); CHECK(ends_at IS NULL OR ends_at>starts_at)

## testimony_invitation_responses

Applicant Confirm/Reject only; rejection explanation optional

Domain: sessions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| appointment_version_id | uuid | Yes | → testimony_appointment_versions |
| party_id | uuid | Yes | → case_parties |
| response | text | Yes |  |
| explanation | text | No |  |

Database constraints: CHECK(response IN ('confirm','reject'))

## decision_types

Prototype type catalog, not invented generic canonical outcomes

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| code | text | Yes |  |
| label_en | text | Yes |  |
| label_ar | text | No |  |
| entitlement_rule | jsonb | Yes |  |
| active | boolean | Yes | true |

Database constraints: UNIQUE(code)

## case_decision_versions

Exact type/grounds/reason and party entitlement shown before voting

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | Yes | → case_proceedings |
| hearing_id | uuid | No | → case_hearings |
| version | integer | Yes |  |
| type_id | uuid | Yes | → decision_types |
| grounds_reason | text | Yes |  |
| party_outcomes | jsonb | Yes |  |
| conditions | text | No |  |

Database constraints: UNIQUE(proceeding_id,version)

## council_votes

Self vote or admin/secretary on behalf; history per exact decision version

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| decision_version_id | uuid | Yes | → case_decision_versions |
| voting_member_id | uuid | Yes | → staff_memberships |
| vote | text | Yes |  |
| supersedes_vote_id | uuid | No | → council_votes |

Database constraints: CHECK(vote IN ('approve','deny','abstain'))

## presidential_approvals

Actual approving president distinct from entering actor; votes optional

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| decision_version_id | uuid | Yes | → case_decision_versions |
| president_member_id | uuid | Yes | → staff_memberships |
| approved_at | timestamptz | Yes |  |
| revoked_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## decree_template_versions

Bilingual type-specific template; issued certificate never changes retroactively

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| type_id | uuid | Yes | → decision_types |
| version | integer | Yes |  |
| content_en | text | Yes |  |
| content_ar | text | Yes |  |
| layout_definition | jsonb | Yes |  |
| published_by_id | uuid | Yes | → accounts |
| digest | text | Yes |  |

Database constraints: UNIQUE(type_id,version)

## decrees

One decree per decree-producing proceeding, original or appeal suffix; no replacement workflow

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | Yes | → case_proceedings |
| decision_version_id | uuid | Yes | → case_decision_versions |
| decree_reference | text | Yes |  |
| template_version_id | uuid | Yes | → decree_template_versions |
| language | text | Yes |  |
| prepared_by_id | uuid | Yes | → accounts |

Database constraints: UNIQUE(proceeding_id); UNIQUE(decree_reference); CHECK(language IN ('en','ar','both'))

## decree_certificates

Stored president-signed PDF; no clerical replacement orchestration

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| decree_id | uuid | Yes | → decrees |
| signed_file_version_id | uuid | Yes | → file_versions |
| president_member_id | uuid | Yes | → staff_memberships |
| signature_method | text | Yes |  |
| signature_metadata | jsonb | Yes |  |
| prepared_by_id | uuid | Yes | → accounts |

Database constraints: UNIQUE(decree_id)

## decree_issuance_events

Signed certificate plus current approval required; atomic case/proceeding closure

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| decree_id | uuid | Yes | → decrees |
| certificate_id | uuid | Yes | → decree_certificates |
| approval_id | uuid | Yes | → presidential_approvals |
| issued_at | timestamptz | Yes |  |

Database constraints: UNIQUE(decree_id)

## decree_entitlements

Recipient certificate entitlement separate from official notice and explicit release

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| decree_id | uuid | Yes | → decrees |
| party_id | uuid | Yes | → case_parties |
| entitlement | text | Yes |  |

Database constraints: UNIQUE(decree_id,party_id); CHECK(entitlement IN ('certificate','notice_only'))

## decree_release_events

Explicit admin/secretary release or access withdrawal; original appeal access unchanged by default

Domain: decisions. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| entitlement_id | uuid | Yes | → decree_entitlements |
| certificate_id | uuid | Yes | → decree_certificates |
| action | text | Yes |  |

Database constraints: CHECK(action IN ('release','withdraw'))

## appeal_applications

Separate each applicant filing, statement and new information; shared case

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| application_id | uuid | Yes | → applications |
| case_id | uuid | Yes | → cases |
| party_id | uuid | Yes | → case_parties |
| challenged_decision_id | uuid | No | → case_decision_versions |
| challenged_decree_id | uuid | No | → decrees |
| status | text | Yes |  |

Database constraints: UNIQUE(application_id)

## pending_appeal_claims

Only one draft/pending appeal per applicant/case; sibling remains independent

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| person_id | uuid | Yes | → persons |
| appeal_id | uuid | Yes | → appeal_applications |

Database constraints: UNIQUE(case_id,person_id); UNIQUE(appeal_id)

## appeal_supplements

Append-only applicant additions; never overwrite submitted appeal

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| appeal_id | uuid | Yes | → appeal_applications |
| text_content | text | Yes |  |
| file_manifest | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## hearing_appeals

Separate appeals considered in a single case hearing

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| hearing_id | uuid | Yes | → case_hearings |
| appeal_id | uuid | Yes | → appeal_applications |

Database constraints: UNIQUE(hearing_id,appeal_id)

## appeal_dispositions

Accept or Decline separately, with optional explanation and no new approval gate

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| appeal_id | uuid | Yes | → appeal_applications |
| hearing_id | uuid | Yes | → case_hearings |
| result | text | Yes |  |
| explanation | text | No |  |
| reopened_proceeding_id | uuid | No | → case_proceedings |

Database constraints: UNIQUE(appeal_id); CHECK(result IN ('accept','decline'))

## proceeding_appeals

Sibling accepted appeals share one reopened proceeding

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| proceeding_id | uuid | Yes | → case_proceedings |
| appeal_id | uuid | Yes | → appeal_applications |

Database constraints: UNIQUE(appeal_id)

## appeal_withdrawals

Owner withdrawal before disposition; fee retained, original ruling unchanged

Domain: appeals. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| appeal_id | uuid | Yes | → appeal_applications |

Database constraints: UNIQUE(appeal_id)

## communications

Permanent in-app/email message or manual call record; applicant isolation

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| proceeding_id | uuid | No | → case_proceedings |
| sender_account_id | uuid | No | → accounts |
| direction | text | Yes |  |
| channel | text | Yes |  |
| subject | text | No |  |
| body | text | Yes |  |
| sent_at | timestamptz | No |  |
| email_timing | text | Yes |  |
| council_session_id | uuid | No | → council_sessions |
| template_snapshot | jsonb | Yes |  |

Database constraints: CHECK(channel IN ('portal','email','call')); CHECK(email_timing IN ('immediate','after_council_session','none'))

## communication_recipients

Private recipient copy; no cross-party thread or reply disclosure

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| communication_id | uuid | Yes | → communications |
| party_id | uuid | No | → case_parties |
| account_id | uuid | No | → accounts |
| external_email | text | No |  |
| recipient_snapshot | jsonb | Yes |  |
| read_at | timestamptz | No |  |

Database constraints: Primary key and declared foreign keys.

## communication_file_links

Reference file in real case location; no separate message file storage

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| communication_id | uuid | Yes | → communications |
| file_version_id | uuid | Yes | → file_versions |

Database constraints: UNIQUE(communication_id,file_version_id)

## call_details

Manual actual call date/time/person/outcome/notes; no dialer or recording

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| communication_id | uuid | Yes | → communications |
| contacted_person | text | Yes |  |
| call_at | timestamptz | Yes |  |
| outcome | text | Yes |  |
| notes | text | No |  |

Database constraints: UNIQUE(communication_id)

## reply_routes

Hashed opaque inbound route; verified sender/recipient, not subject-only matching

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| recipient_id | uuid | Yes | → communication_recipients |
| token_hash | text | Yes |  |
| revoked_at | timestamptz | No |  |

Database constraints: UNIQUE(token_hash)

## inbound_email_receipts

Deduplicated retained safe body/header; rejected attachments not evidence

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| provider | text | Yes |  |
| message_id | text | Yes |  |
| sender_snapshot | jsonb | Yes |  |
| safe_headers | jsonb | Yes |  |
| body | text | Yes |  |
| received_at | timestamptz | Yes |  |
| routing_state | text | Yes |  |
| recipient_id | uuid | No | → communication_recipients |
| communication_id | uuid | No | → communications |

Database constraints: UNIQUE(provider,message_id)

## email_attachment_returns

Return/notify attachment rejection; transient payload outside permanent document store

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| receipt_id | uuid | Yes | → inbound_email_receipts |
| metadata | jsonb | Yes |  |
| temporary_payload_key | text | No |  |
| cleanup_due_at | timestamptz | No |  |
| return_delivery_id | uuid | No | → channel_deliveries |
| status | text | Yes |  |

Database constraints: Primary key and declared foreign keys.

## notifications

Immediate private portal activity/read flag, distinct from email scheduling

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| recipient_account_id | uuid | Yes | → accounts |
| case_id | uuid | No | → cases |
| event_key | text | Yes |  |
| purpose | text | Yes |  |
| safe_payload | jsonb | Yes |  |
| read_at | timestamptz | No |  |

Database constraints: UNIQUE(recipient_account_id,event_key,purpose)

## channel_deliveries

Per-recipient exact rendered payload and retry/delivery evidence

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| communication_recipient_id | uuid | No | → communication_recipients |
| notification_id | uuid | No | → notifications |
| channel | text | Yes |  |
| address_snapshot | text | Yes |  |
| rendered_payload | jsonb | Yes |  |
| due_at | timestamptz | No |  |
| state | text | Yes |  |
| provider_id | text | No |  |
| idempotency_key | text | Yes |  |

Database constraints: CHECK(num_nonnulls(communication_recipient_id,notification_id)=1); UNIQUE(idempotency_key)

## delivery_events

Provider acceptance/delivery/bounce is not human reading

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| delivery_id | uuid | Yes | → channel_deliveries |
| provider_event_key | text | Yes |  |
| result | text | Yes |  |
| occurred_at | timestamptz | Yes |  |

Database constraints: UNIQUE(provider_event_key)

## notification_batches

Applicant changes digest after10quiet minutes; resolve current manager at send

Domain: communications. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| case_id | uuid | Yes | → cases |
| source_person_id | uuid | Yes | → persons |
| due_at | timestamptz | Yes |  |
| status | text | Yes |  |
| event_keys | jsonb | Yes |  |
| delivered_to_id | uuid | No | → accounts |

Database constraints: Primary key and declared foreign keys.

## audit_events

Append-only case/system audit, restricted projection; no raw secrets

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| case_id | uuid | No | → cases |
| subject_person_id | uuid | No | → persons |
| operation | text | Yes |  |
| source_table | text | Yes |  |
| source_id | uuid | Yes |  |
| classification | text | Yes |  |
| safe_details | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## outbox_events

Atomic domain-event handoff; retries do not duplicate business actions

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| event_key | text | Yes |  |
| kind | text | Yes |  |
| aggregate_id | uuid | Yes |  |
| source_version_id | uuid | No |  |
| safe_payload | jsonb | Yes |  |
| processed_at | timestamptz | No |  |

Database constraints: UNIQUE(event_key)

## background_jobs

Durable scans/OCR/transcription/search/email/cleanup retries and leases

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| outbox_id | uuid | No | → outbox_events |
| kind | text | Yes |  |
| source_reference | jsonb | Yes |  |
| status | text | Yes |  |
| due_at | timestamptz | Yes |  |
| attempt | integer | Yes | 0 |
| lease_until | timestamptz | No |  |
| safe_error | text | No |  |

Database constraints: CHECK(attempt>=0)

## draft_retention_events

180day inactivity,7day warning, deletion versus retained-submission barrier

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| application_id | uuid | No | → applications |
| application_snapshot_id | uuid | Yes |  |
| event_type | text | Yes |  |
| deadline | timestamptz | Yes |  |
| retained_metadata | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

## system_setting_versions

Admin system configuration; not applicant settings or permissions bypass

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| key | text | Yes |  |
| version | integer | Yes |  |
| safe_value | jsonb | Yes |  |
| edited_by_id | uuid | Yes | → accounts |

Database constraints: UNIQUE(key,version)

## translation_prompt_versions

Exact user master prompt preserved/versioned; all translation purposes

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| version | integer | Yes |  |
| content | text | Yes |  |
| digest | text | Yes |  |
| edited_by_id | uuid | Yes | → accounts |

Database constraints: UNIQUE(version)

## integration_configurations

Server-only secret reference, ordered primary/fallback; no plaintext key in UI

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| purpose | text | Yes |  |
| priority | integer | Yes |  |
| provider | text | Yes |  |
| mode | text | Yes |  |
| safe_configuration | jsonb | Yes |  |
| secret_reference | text | No |  |
| enabled | boolean | Yes | false |

Database constraints: UNIQUE(purpose,priority); CHECK(priority>0)

## translation_jobs

Source/version/prompt/provider provenance, restricted medical egress boundary

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| source_kind | text | Yes |  |
| source_id | uuid | Yes |  |
| source_version | text | Yes |  |
| source_locale | text | Yes |  |
| target_locale | text | Yes |  |
| prompt_version_id | uuid | Yes | → translation_prompt_versions |
| provider_configuration_id | uuid | No | → integration_configurations |
| status | text | Yes |  |
| content_class | text | Yes |  |

Database constraints: Primary key and declared foreign keys.

## translation_versions

Original and reviewed translated text are separate retained versions

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| actor_id | uuid | No | → accounts |
| request_id | uuid | No |  |
| job_id | uuid | Yes | → translation_jobs |
| version | integer | Yes |  |
| content | text | Yes |  |
| state | text | Yes |  |
| reviewer_id | uuid | No | → accounts |

Database constraints: UNIQUE(job_id,version)

## ui_resource_versions

Reviewed en/ar UI bundles, not live per-render AI translation

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| resource_key | text | Yes |  |
| version | integer | Yes |  |
| text_en | text | Yes |  |
| text_ar | text | Yes |  |
| published_by_id | uuid | Yes | → accounts |
| digest | text | Yes |  |

Database constraints: UNIQUE(resource_key,version)

## recovery_manifests

Database/file/key backup integrity and restore evidence, not user export

Domain: operations. Retention: retained.

| Column | PostgreSQL type | Required | Relationship / default |
|---|---|---|---|
| id | uuid | Yes | gen_random_uuid() |
| created_at | timestamptz | Yes | now() |
| backup_reference | text | Yes |  |
| file_manifest_digest | text | Yes |  |
| database_backup_reference | text | Yes |  |
| secret_backup_reference | text | Yes |  |
| restore_verified_at | timestamptz | No |  |
| result | jsonb | Yes |  |

Database constraints: Primary key and declared foreign keys.

