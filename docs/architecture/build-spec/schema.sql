-- CTM structural baseline. NOT a complete production security migration.

-- See transactions-and-acceptance.md and permissions.md. No public grants.

-- Target: PostgreSQL 17+; pin and validate exact deployment release separately.

BEGIN;

CREATE SCHEMA ctm;

REVOKE ALL ON SCHEMA ctm FROM PUBLIC;

CREATE TABLE ctm.persons (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  canonical_person_id uuid,
  identity_state text NOT NULL,
  row_version bigint NOT NULL DEFAULT 1
);

CREATE TABLE ctm.person_identity_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  person_id uuid NOT NULL,
  version integer NOT NULL,
  first_name_en text,
  last_name_en text,
  name_ar text,
  birth_date date,
  gender text,
  facts jsonb NOT NULL,
  source text NOT NULL,
  UNIQUE(person_id,version),
  CHECK(gender IS NULL OR gender IN ('M','F'))
);

CREATE TABLE ctm.accounts (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  person_id uuid,
  status text NOT NULL,
  ui_locale text NOT NULL DEFAULT 'en',
  notification_locale text NOT NULL DEFAULT 'en',
  row_version bigint NOT NULL DEFAULT 1,
  CHECK(status IN ('pending','active','suspended','disabled')),
  CHECK(ui_locale IN ('en','ar')),
  CHECK(notification_locale IN ('en','ar'))
);

CREATE TABLE ctm.account_identities (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  account_id uuid NOT NULL,
  provider text NOT NULL,
  issuer text NOT NULL,
  subject text NOT NULL,
  tenant_id text,
  verified_email text,
  linked_at timestamptz NOT NULL,
  revoked_at timestamptz,
  UNIQUE(issuer,subject),
  CHECK(provider IN ('microsoft','google','apple'))
);

CREATE TABLE ctm.account_email_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  account_id uuid NOT NULL,
  email text NOT NULL,
  normalized_email text NOT NULL,
  verified_at timestamptz,
  superseded_at timestamptz
);

CREATE TABLE ctm.verification_tokens (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  account_id uuid,
  purpose text NOT NULL,
  token_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz,
  revoked_at timestamptz,
  UNIQUE(token_hash)
);

CREATE TABLE ctm.app_sessions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  account_id uuid NOT NULL,
  session_hash text NOT NULL,
  provider_identity_id uuid NOT NULL,
  authenticated_at timestamptz NOT NULL,
  revoked_at timestamptz,
  provider_expires_at timestamptz,
  UNIQUE(session_hash)
);

CREATE TABLE ctm.tribunals (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  name_en text NOT NULL,
  name_ar text,
  timezone text NOT NULL DEFAULT 'America/Los_Angeles',
  UNIQUE(code),
  CHECK(timezone='America/Los_Angeles')
);

CREATE TABLE ctm.staff_memberships (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  account_id uuid NOT NULL,
  tribunal_id uuid NOT NULL,
  appointed_by_id uuid NOT NULL,
  active_from timestamptz NOT NULL,
  active_until timestamptz
);

CREATE TABLE ctm.staff_roles (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  membership_id uuid NOT NULL,
  role text NOT NULL,
  granted_by_id uuid NOT NULL,
  revoked_at timestamptz,
  CHECK(role IN ('admin','secretary','president','member'))
);

CREATE TABLE ctm.account_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  account_id uuid,
  event_type text NOT NULL,
  restricted_details jsonb NOT NULL
);

CREATE TABLE ctm.identity_consolidations (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  source_person_id uuid NOT NULL,
  target_person_id uuid NOT NULL,
  primary_account_id uuid NOT NULL,
  disabled_account_id uuid,
  evidence jsonb NOT NULL,
  CHECK(source_person_id<>target_person_id)
);

CREATE TABLE ctm.identity_review_holds (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  application_id uuid NOT NULL,
  matching_rule text NOT NULL,
  protected_candidate_snapshot jsonb NOT NULL,
  status text NOT NULL,
  resolved_by_id uuid,
  resolved_at timestamptz
);

CREATE TABLE ctm.ctm_applicants (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  person_id uuid NOT NULL,
  tribunal_id uuid NOT NULL,
  internal_temporary_label text,
  UNIQUE(person_id,tribunal_id)
);

CREATE TABLE ctm.dioceses (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  name_en text NOT NULL,
  name_ar text,
  contact jsonb NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE ctm.parishes (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  diocese_id uuid,
  name_en text NOT NULL,
  name_ar text,
  location jsonb NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE ctm.marriages (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  marriage_date date,
  spouse_birth_date_low date,
  spouse_birth_date_high date,
  matching_state text NOT NULL,
  CHECK(spouse_birth_date_low IS NULL OR spouse_birth_date_high IS NULL OR spouse_birth_date_low<=spouse_birth_date_high)
);

CREATE TABLE ctm.cases (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  tribunal_id uuid NOT NULL,
  marriage_id uuid,
  origin text NOT NULL,
  status text NOT NULL,
  opened_at timestamptz,
  closed_at timestamptz,
  row_version bigint NOT NULL DEFAULT 1,
  CHECK(origin IN ('new','historical')),
  CHECK(status IN ('open','closed'))
);

CREATE TABLE ctm.case_identifiers (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  reference text NOT NULL,
  namespace text NOT NULL,
  is_primary boolean NOT NULL,
  allocation_date date,
  daily_sequence integer,
  CHECK(daily_sequence IS NULL OR daily_sequence BETWEEN 1 AND 99)
);

CREATE TABLE ctm.case_number_counters (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  local_date date NOT NULL,
  last_value integer NOT NULL,
  UNIQUE(local_date),
  CHECK(last_value BETWEEN 0 AND 99)
);

CREATE TABLE ctm.case_parties (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  person_id uuid,
  applicant_id uuid,
  party_slot text NOT NULL,
  participation_state text NOT NULL,
  source_name_snapshot jsonb NOT NULL,
  UNIQUE(case_id,party_slot),
  CHECK(party_slot IN ('A','B'))
);

CREATE TABLE ctm.applicant_references (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  party_id uuid NOT NULL,
  reference text NOT NULL,
  origin text NOT NULL,
  issued_components jsonb NOT NULL,
  issued_at timestamptz NOT NULL,
  UNIQUE(party_id)
);

CREATE TABLE ctm.person_open_case_claims (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  person_id uuid NOT NULL,
  case_id uuid NOT NULL,
  party_id uuid NOT NULL,
  UNIQUE(person_id),
  UNIQUE(party_id)
);

CREATE TABLE ctm.person_active_draft_claims (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  person_id uuid NOT NULL,
  application_id uuid NOT NULL,
  UNIQUE(person_id),
  UNIQUE(application_id)
);

CREATE TABLE ctm.case_proceedings (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  kind text NOT NULL,
  status text NOT NULL,
  opened_at timestamptz NOT NULL,
  closed_at timestamptz,
  appeal_decree_sequence integer,
  CHECK(kind IN ('initial','appeal')),
  CHECK(status IN ('open','closed')),
  CHECK(appeal_decree_sequence IS NULL OR appeal_decree_sequence>0)
);

CREATE TABLE ctm.case_lifecycle_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  case_id uuid NOT NULL,
  proceeding_id uuid,
  event_type text NOT NULL,
  source_reference jsonb NOT NULL
);

CREATE TABLE ctm.case_association_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  case_id uuid NOT NULL,
  application_id uuid,
  matching_rule text NOT NULL,
  source_snapshot jsonb NOT NULL,
  result text NOT NULL
);

CREATE TABLE ctm.case_party_onboarding (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  party_id uuid NOT NULL,
  first_name text NOT NULL,
  last_name text NOT NULL,
  normalized_email text NOT NULL,
  entered_by_id uuid NOT NULL,
  status text NOT NULL,
  activated_account_id uuid,
  activated_at timestamptz
);

CREATE TABLE ctm.registration_invitation_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  onboarding_id uuid NOT NULL,
  communication_id uuid NOT NULL
);

CREATE TABLE ctm.case_assignments (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  member_id uuid NOT NULL,
  president_id uuid NOT NULL,
  recorded_by_id uuid NOT NULL,
  session_id uuid,
  authorized_at timestamptz NOT NULL,
  starts_at timestamptz NOT NULL,
  ends_at timestamptz
);

CREATE TABLE ctm.historical_entry_workspaces (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by_id uuid NOT NULL,
  draft_payload jsonb NOT NULL,
  published_case_id uuid,
  declared_status text,
  finalized_at timestamptz
);

CREATE TABLE ctm.questionnaires (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  purpose text NOT NULL,
  UNIQUE(code)
);

CREATE TABLE ctm.questionnaire_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  questionnaire_id uuid NOT NULL,
  version integer NOT NULL,
  state text NOT NULL,
  definition jsonb NOT NULL,
  digest text NOT NULL,
  published_by_id uuid,
  published_at timestamptz,
  UNIQUE(questionnaire_id,version)
);

CREATE TABLE ctm.declaration_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  purpose text NOT NULL,
  version integer NOT NULL,
  text_en text NOT NULL,
  text_ar text NOT NULL,
  digest text NOT NULL,
  published_by_id uuid NOT NULL,
  published_at timestamptz NOT NULL,
  UNIQUE(purpose,version)
);

CREATE TABLE ctm.applications (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  owner_person_id uuid NOT NULL,
  owner_account_id uuid NOT NULL,
  case_id uuid,
  party_id uuid,
  proceeding_id uuid,
  purpose text NOT NULL,
  status text NOT NULL,
  origin text NOT NULL,
  questionnaire_version_id uuid NOT NULL,
  last_applicant_activity_at timestamptz NOT NULL,
  first_submitted_at timestamptz,
  row_version bigint NOT NULL DEFAULT 1,
  CHECK(purpose IN ('petition','appeal')),
  CHECK(status IN ('draft','submitted','returned','accepted','withdrawn','expired','deleted'))
);

CREATE TABLE ctm.application_revisions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  application_id uuid NOT NULL,
  version integer NOT NULL,
  predecessor_id uuid,
  questionnaire_version_id uuid NOT NULL,
  digest text NOT NULL,
  UNIQUE(application_id,version)
);

CREATE TABLE ctm.application_person_assertions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  subject text NOT NULL,
  first_name_en text,
  middle_name_en text,
  last_name_en text,
  name_ar text,
  birth_date date,
  gender text,
  nationality text,
  birth_country text,
  address jsonb NOT NULL,
  contacts jsonb NOT NULL,
  immigration_status text,
  parish text,
  father_of_confession text,
  residence_country text,
  religious_affiliation text,
  denomination text,
  additional_facts jsonb NOT NULL,
  answer_states jsonb NOT NULL,
  UNIQUE(revision_id,subject),
  CHECK(subject IN ('self','spouse')),
  CHECK(gender IS NULL OR gender IN ('M','F'))
);

CREATE TABLE ctm.application_marriage_assertions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  church_marriage_date date,
  certificate_number text,
  church_name text,
  church_location text,
  diocese text,
  officiating_priest text,
  outside_coptic_marriage boolean,
  outside_denomination text,
  additional_facts jsonb NOT NULL,
  answer_states jsonb NOT NULL,
  UNIQUE(revision_id)
);

CREATE TABLE ctm.application_separation_assertions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  separation_date date,
  initiated_by text,
  civil_divorce_date date,
  court_name text,
  court_case_number text,
  facts jsonb NOT NULL,
  answer_states jsonb NOT NULL,
  UNIQUE(revision_id)
);

CREATE TABLE ctm.application_repeat_entries (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  application_id uuid NOT NULL,
  collection_code text NOT NULL
);

CREATE TABLE ctm.application_children (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  entry_id uuid NOT NULL,
  names jsonb NOT NULL,
  birth_date date,
  gender text,
  lives_with text,
  answer_states jsonb NOT NULL,
  UNIQUE(revision_id,entry_id)
);

CREATE TABLE ctm.application_restraining_orders (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  entry_id uuid NOT NULL,
  court_name text,
  court_case_number text,
  current_status text,
  order_date date,
  expiry_date date,
  named_person text,
  answer_states jsonb NOT NULL,
  UNIQUE(revision_id,entry_id)
);

CREATE TABLE ctm.application_prior_records (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  entry_id uuid NOT NULL,
  kind text NOT NULL,
  record_date date,
  spouse_name text,
  ecclesiastical_permit text,
  council_or_diocese text,
  outcome text,
  priest_name text,
  answer_states jsonb NOT NULL,
  UNIQUE(revision_id,entry_id),
  CHECK(kind IN ('prior_marriage','prior_application','counseling_priest'))
);

CREATE TABLE ctm.application_answers (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  question_code text NOT NULL,
  entry_id uuid,
  answer_type text NOT NULL,
  answer_state text NOT NULL,
  value jsonb NOT NULL
);

CREATE TABLE ctm.ground_definitions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  version integer NOT NULL,
  label_en text NOT NULL,
  label_ar text NOT NULL,
  retired_at timestamptz,
  UNIQUE(code,version)
);

CREATE TABLE ctm.application_selected_grounds (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  ground_id uuid NOT NULL,
  UNIQUE(revision_id,ground_id)
);

CREATE TABLE ctm.application_answer_changes (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  application_id uuid NOT NULL,
  from_revision_id uuid NOT NULL,
  to_revision_id uuid NOT NULL,
  question_code text NOT NULL,
  entry_id uuid,
  before_value jsonb NOT NULL,
  after_value jsonb NOT NULL
);

CREATE TABLE ctm.filing_candidates (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  application_id uuid NOT NULL,
  revision_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  frozen_manifest jsonb NOT NULL,
  attestation_snapshot jsonb NOT NULL,
  state text NOT NULL,
  UNIQUE(idempotency_key)
);

CREATE TABLE ctm.application_submissions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  application_id uuid NOT NULL,
  revision_id uuid NOT NULL,
  candidate_id uuid,
  previous_submission_id uuid,
  declaration_version_id uuid,
  signature_file_version_id uuid,
  attestation jsonb NOT NULL,
  submitted_by_id uuid NOT NULL,
  received_at timestamptz NOT NULL,
  digest text NOT NULL,
  UNIQUE(candidate_id)
);

CREATE TABLE ctm.application_completeness_reviews (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  submission_id uuid NOT NULL,
  result text NOT NULL,
  correction_instructions text,
  CHECK(result IN ('accept','reject')),
  CHECK(result<>'reject' OR nullif(btrim(correction_instructions),'') IS NOT NULL)
);

CREATE TABLE ctm.draft_schema_migrations (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  application_id uuid NOT NULL,
  from_version_id uuid NOT NULL,
  to_version_id uuid NOT NULL,
  preserved_mapping jsonb NOT NULL,
  notice_id uuid
);

CREATE TABLE ctm.party_withdrawals (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  party_id uuid NOT NULL,
  application_id uuid NOT NULL,
  on_behalf boolean NOT NULL
);

CREATE TABLE ctm.document_categories (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  label_en text NOT NULL,
  label_ar text NOT NULL,
  row_version bigint NOT NULL DEFAULT 1,
  retired_at timestamptz,
  UNIQUE(code)
);

CREATE TABLE ctm.files (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid,
  proceeding_id uuid,
  owner_application_id uuid,
  owner_party_id uuid,
  report_request_id uuid,
  category_id uuid NOT NULL,
  visibility text NOT NULL,
  row_version bigint NOT NULL DEFAULT 1,
  CHECK(visibility IN ('applicant_own','council_only','medical_scoped','decree_entitled'))
);

CREATE TABLE ctm.file_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  file_id uuid NOT NULL,
  version integer NOT NULL,
  object_key text NOT NULL,
  original_name text NOT NULL,
  presented_name text NOT NULL,
  size_bytes bigint NOT NULL,
  mime_type text NOT NULL,
  checksum_sha256 text NOT NULL,
  uploaded_by_id uuid,
  external_link_id uuid,
  uploaded_at timestamptz NOT NULL,
  technical_state text NOT NULL,
  wrong_upload_removed_at timestamptz,
  UNIQUE(file_id,version),
  UNIQUE(object_key),
  CHECK(size_bytes>=0),
  CHECK(num_nonnulls(uploaded_by_id,external_link_id)=1)
);

CREATE TABLE ctm.file_name_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  file_version_id uuid NOT NULL,
  previous_name text NOT NULL,
  new_name text NOT NULL,
  category_snapshot jsonb NOT NULL
);

CREATE TABLE ctm.file_context_links (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  file_version_id uuid NOT NULL,
  application_revision_id uuid,
  repeat_entry_id uuid,
  report_revision_id uuid,
  medical_report_id uuid,
  question_code text,
  purpose text NOT NULL,
  description text
);

CREATE TABLE ctm.submission_file_manifest (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  submission_id uuid NOT NULL,
  file_version_id uuid NOT NULL,
  metadata_snapshot jsonb NOT NULL,
  UNIQUE(submission_id,file_version_id)
);

CREATE TABLE ctm.upload_sessions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  file_id uuid NOT NULL,
  uploader_id uuid,
  external_link_id uuid,
  expected_bytes bigint,
  capture_kind text NOT NULL,
  status text NOT NULL,
  expires_at timestamptz,
  completed_version_id uuid,
  CHECK(num_nonnulls(uploader_id,external_link_id)=1)
);

CREATE TABLE ctm.file_technical_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  file_version_id uuid NOT NULL,
  task text NOT NULL,
  engine_version text NOT NULL,
  result text NOT NULL,
  safe_metadata jsonb NOT NULL
);

CREATE TABLE ctm.file_derivatives (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  source_version_id uuid NOT NULL,
  kind text NOT NULL,
  object_key text,
  extracted_text text,
  engine_version text NOT NULL,
  languages jsonb NOT NULL,
  status text NOT NULL,
  checksum_sha256 text
);

CREATE TABLE ctm.file_access_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  file_version_id uuid NOT NULL,
  action text NOT NULL,
  result text NOT NULL,
  correlation_id uuid NOT NULL
);

CREATE TABLE ctm.search_documents (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  party_id uuid,
  source_kind text NOT NULL,
  source_id uuid NOT NULL,
  source_version_id uuid NOT NULL,
  security_scope text NOT NULL,
  locale text NOT NULL,
  index_generation text NOT NULL,
  indexed_at timestamptz,
  UNIQUE(source_kind,source_version_id,locale)
);

CREATE TABLE ctm.fee_obligations (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  application_id uuid NOT NULL,
  amount_minor bigint NOT NULL DEFAULT 25000,
  currency text NOT NULL DEFAULT 'USD',
  disposition text NOT NULL,
  assessed_at timestamptz NOT NULL,
  UNIQUE(application_id),
  CHECK(amount_minor=25000),
  CHECK(currency='USD'),
  CHECK(disposition IN ('due','paid','waived','historical_exempt'))
);

CREATE TABLE ctm.fee_waivers (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  obligation_id uuid NOT NULL,
  reason text
);

CREATE TABLE ctm.payment_attempts (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  obligation_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  provider text NOT NULL,
  provider_reference text NOT NULL,
  idempotency_key text NOT NULL,
  amount_minor bigint NOT NULL,
  currency text NOT NULL,
  status text NOT NULL,
  UNIQUE(provider,provider_reference),
  UNIQUE(idempotency_key),
  CHECK(amount_minor>0)
);

CREATE TABLE ctm.payment_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  attempt_id uuid NOT NULL,
  provider_event_id text NOT NULL,
  event_type text NOT NULL,
  verified_at timestamptz NOT NULL,
  safe_payload jsonb NOT NULL,
  UNIQUE(provider_event_id)
);

CREATE TABLE ctm.payment_allocations (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  attempt_id uuid NOT NULL,
  obligation_id uuid NOT NULL,
  submission_id uuid NOT NULL,
  amount_minor bigint NOT NULL,
  UNIQUE(attempt_id)
);

CREATE TABLE ctm.refund_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  attempt_id uuid NOT NULL,
  provider_refund_id text,
  status text NOT NULL,
  amount_minor bigint NOT NULL,
  reason text NOT NULL,
  CHECK(amount_minor>0)
);

CREATE TABLE ctm.topic_groups (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  labels jsonb NOT NULL,
  position integer NOT NULL,
  UNIQUE(code)
);

CREATE TABLE ctm.question_categories (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  labels jsonb NOT NULL,
  position integer NOT NULL,
  UNIQUE(code)
);

CREATE TABLE ctm.report_questions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  foundational boolean NOT NULL,
  retired_at timestamptz,
  UNIQUE(code)
);

CREATE TABLE ctm.report_question_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  question_id uuid NOT NULL,
  version integer NOT NULL,
  wording_en text NOT NULL,
  wording_ar text,
  conditional_guidance jsonb NOT NULL,
  published_by_id uuid,
  published_at timestamptz,
  UNIQUE(question_id,version)
);

CREATE TABLE ctm.topic_category_memberships (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  topic_group_id uuid NOT NULL,
  category_id uuid NOT NULL,
  position integer NOT NULL,
  UNIQUE(topic_group_id,category_id)
);

CREATE TABLE ctm.category_question_memberships (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  category_id uuid NOT NULL,
  question_id uuid NOT NULL,
  position integer NOT NULL,
  UNIQUE(category_id,question_id)
);

CREATE TABLE ctm.report_templates (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  scope text NOT NULL,
  owner_member_id uuid,
  title text NOT NULL,
  retired_at timestamptz,
  CHECK((scope='personal' AND owner_member_id IS NOT NULL) OR (scope='shared' AND owner_member_id IS NULL))
);

CREATE TABLE ctm.report_template_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  template_id uuid NOT NULL,
  version integer NOT NULL,
  definition jsonb NOT NULL,
  digest text NOT NULL,
  state text NOT NULL,
  published_by_id uuid,
  UNIQUE(template_id,version)
);

CREATE TABLE ctm.template_publication_submissions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  personal_version_id uuid NOT NULL,
  shared_version_id uuid,
  status text NOT NULL,
  reviewed_by_id uuid
);

CREATE TABLE ctm.report_requests (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  proceeding_id uuid NOT NULL,
  subject_party_id uuid NOT NULL,
  parent_report_id uuid,
  kind text NOT NULL,
  created_by_id uuid NOT NULL,
  title text NOT NULL,
  identifier_text text,
  language text NOT NULL,
  status text NOT NULL,
  sent_at timestamptz,
  closed_at timestamptz,
  template_version_id uuid,
  instructions jsonb NOT NULL,
  row_version bigint NOT NULL DEFAULT 1,
  CHECK(kind IN ('applicant_intake','manager_interview','external_priest','medical','psychological')),
  CHECK(language IN ('en','ar','both'))
);

CREATE TABLE ctm.sent_intake_question_snapshots (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  request_id uuid NOT NULL,
  source_question_version_id uuid,
  question_code text NOT NULL,
  position integer NOT NULL,
  text_en text,
  text_ar text,
  source_context_snapshot jsonb NOT NULL,
  UNIQUE(request_id,position)
);

CREATE TABLE ctm.external_report_links (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  request_id uuid NOT NULL,
  recipient_email text,
  priest_name text NOT NULL,
  token_hash text NOT NULL,
  issued_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  used_submission_at timestamptz,
  UNIQUE(token_hash),
  CHECK(expires_at=issued_at + interval '30 days')
);

CREATE TABLE ctm.external_response_drafts (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  request_id uuid NOT NULL,
  response jsonb NOT NULL,
  saved_at timestamptz NOT NULL,
  UNIQUE(request_id)
);

CREATE TABLE ctm.reports (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  request_id uuid NOT NULL,
  case_id uuid NOT NULL,
  proceeding_id uuid NOT NULL,
  subject_party_id uuid NOT NULL,
  parent_report_id uuid,
  author_account_id uuid,
  external_author_name text,
  recorded_by_id uuid,
  completion_date date,
  identifier_text text,
  title text NOT NULL,
  method text NOT NULL,
  status text NOT NULL,
  submitted_at timestamptz,
  row_version bigint NOT NULL DEFAULT 1,
  UNIQUE(request_id)
);

CREATE TABLE ctm.report_revisions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  report_id uuid NOT NULL,
  version integer NOT NULL,
  predecessor_id uuid,
  narrative jsonb NOT NULL,
  internal_observations text,
  digest text NOT NULL,
  UNIQUE(report_id,version)
);

CREATE TABLE ctm.report_answers (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  revision_id uuid NOT NULL,
  question_snapshot_id uuid NOT NULL,
  answer_type text NOT NULL,
  value jsonb NOT NULL,
  UNIQUE(revision_id,question_snapshot_id)
);

CREATE TABLE ctm.report_source_links (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  report_revision_id uuid NOT NULL,
  question_snapshot_id uuid,
  source_application_revision_id uuid,
  source_file_version_id uuid,
  question_code text,
  context_snapshot jsonb NOT NULL,
  confirmation jsonb NOT NULL
);

CREATE TABLE ctm.recordings (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  report_id uuid,
  testimony_appointment_id uuid,
  file_version_id uuid NOT NULL,
  captured_by_id uuid,
  recording_notice jsonb NOT NULL,
  finalized_at timestamptz,
  duration_ms bigint,
  origin text NOT NULL,
  CHECK(num_nonnulls(report_id,testimony_appointment_id)=1),
  CHECK(duration_ms IS NULL OR duration_ms>=0)
);

CREATE TABLE ctm.processing_runs (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  recording_id uuid,
  file_version_id uuid,
  task text NOT NULL,
  provider text NOT NULL,
  model_version text NOT NULL,
  input_digest text NOT NULL,
  status text NOT NULL,
  safe_error text,
  started_at timestamptz,
  finished_at timestamptz,
  CHECK(num_nonnulls(recording_id,file_version_id)=1)
);

CREATE TABLE ctm.transcript_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  recording_id uuid NOT NULL,
  run_id uuid,
  kind text NOT NULL,
  language text NOT NULL,
  version integer NOT NULL,
  predecessor_id uuid,
  source_transcript_id uuid,
  origin text NOT NULL,
  text_content text NOT NULL,
  UNIQUE(recording_id,kind,language,version)
);

CREATE TABLE ctm.transcript_segments (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  text_version_id uuid NOT NULL,
  ordinal integer NOT NULL,
  start_ms bigint NOT NULL,
  end_ms bigint NOT NULL,
  speaker_label text NOT NULL,
  speaker_person_id uuid,
  content text NOT NULL,
  source_segment_id uuid,
  UNIQUE(text_version_id,ordinal),
  CHECK(start_ms>=0 AND end_ms>=start_ms)
);

CREATE TABLE ctm.text_review_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  text_version_id uuid NOT NULL,
  action text NOT NULL,
  reviewer_member_id uuid NOT NULL
);

CREATE TABLE ctm.recommended_providers (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  display_name text NOT NULL,
  specialty text NOT NULL,
  contact jsonb NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE ctm.evaluation_requests (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  report_request_id uuid NOT NULL,
  subject_party_id uuid NOT NULL,
  purpose text NOT NULL,
  provider_details jsonb NOT NULL,
  recommended_provider_snapshots jsonb NOT NULL,
  UNIQUE(report_request_id)
);

CREATE TABLE ctm.evaluation_release_attestations (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  evaluation_request_id uuid NOT NULL,
  declaration_version_id uuid NOT NULL,
  subject_person_id uuid NOT NULL,
  signer_person_id uuid NOT NULL,
  signature_file_version_id uuid NOT NULL,
  signed_at timestamptz NOT NULL,
  language text NOT NULL,
  exact_text text NOT NULL,
  purpose text NOT NULL,
  attestation jsonb NOT NULL,
  CHECK(subject_person_id=signer_person_id)
);

CREATE TABLE ctm.evaluation_release_scopes (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  attestation_id uuid NOT NULL,
  recipient_scope jsonb NOT NULL,
  purpose text NOT NULL,
  file_scope jsonb NOT NULL
);

CREATE TABLE ctm.evaluation_reports (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  evaluation_request_id uuid NOT NULL,
  report_id uuid NOT NULL,
  release_attestation_id uuid,
  provider_details jsonb NOT NULL,
  completion_date date NOT NULL,
  authorization_state text NOT NULL,
  UNIQUE(report_id)
);

CREATE TABLE ctm.evaluation_disclosures (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  evaluation_report_id uuid NOT NULL,
  release_scope_id uuid NOT NULL,
  file_version_id uuid,
  action text NOT NULL
);

CREATE TABLE ctm.case_findings (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  proceeding_id uuid NOT NULL,
  fact_code text NOT NULL,
  UNIQUE(proceeding_id,fact_code)
);

CREATE TABLE ctm.finding_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  finding_id uuid NOT NULL,
  version integer NOT NULL,
  value jsonb NOT NULL,
  sources jsonb NOT NULL,
  UNIQUE(finding_id,version)
);

CREATE TABLE ctm.case_notes (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  proceeding_id uuid NOT NULL,
  author_id uuid NOT NULL
);

CREATE TABLE ctm.note_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  note_id uuid NOT NULL,
  version integer NOT NULL,
  content text NOT NULL,
  UNIQUE(note_id,version)
);

CREATE TABLE ctm.council_sessions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  session_date date NOT NULL,
  reference text NOT NULL,
  state text NOT NULL,
  created_by_id uuid NOT NULL,
  closed_at timestamptz,
  UNIQUE(session_date),
  UNIQUE(reference)
);

CREATE TABLE ctm.agenda_requests (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  case_id uuid NOT NULL,
  requested_session_id uuid,
  placed_item_id uuid
);

CREATE TABLE ctm.session_agenda_items (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  session_id uuid NOT NULL,
  case_id uuid NOT NULL,
  part integer NOT NULL,
  position integer NOT NULL,
  status text NOT NULL,
  carried_from_id uuid,
  CHECK(part IN (1,2)),
  UNIQUE(session_id,part,position),
  UNIQUE(session_id,case_id)
);

CREATE TABLE ctm.agenda_transfer_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  case_id uuid NOT NULL,
  from_session_snapshot jsonb NOT NULL,
  to_session_id uuid,
  destination_item_id uuid,
  reason text NOT NULL
);

CREATE TABLE ctm.session_attendance (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  session_id uuid NOT NULL,
  member_id uuid NOT NULL,
  present boolean NOT NULL,
  recorded_by_id uuid NOT NULL,
  UNIQUE(session_id,member_id)
);

CREATE TABLE ctm.case_hearings (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  agenda_item_id uuid NOT NULL,
  case_id uuid NOT NULL,
  proceeding_id uuid,
  presenter_member_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL,
  result text NOT NULL,
  UNIQUE(agenda_item_id)
);

CREATE TABLE ctm.hearing_attendance (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  hearing_id uuid NOT NULL,
  member_id uuid NOT NULL,
  present boolean NOT NULL,
  recorded_by_id uuid NOT NULL,
  UNIQUE(hearing_id,member_id)
);

CREATE TABLE ctm.hearing_outcome_revisions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  hearing_id uuid NOT NULL,
  version integer NOT NULL,
  internal_text text NOT NULL,
  recommendations text NOT NULL,
  applicant_message_snapshot text,
  communication_id uuid,
  UNIQUE(hearing_id,version)
);

CREATE TABLE ctm.testimony_appointments (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  party_id uuid NOT NULL,
  agenda_item_id uuid NOT NULL,
  status text NOT NULL,
  created_by_id uuid NOT NULL
);

CREATE TABLE ctm.testimony_appointment_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  appointment_id uuid NOT NULL,
  version integer NOT NULL,
  starts_at timestamptz NOT NULL,
  ends_at timestamptz,
  instructions text NOT NULL,
  attendance_location jsonb NOT NULL,
  cancelled boolean NOT NULL,
  UNIQUE(appointment_id,version),
  CHECK(ends_at IS NULL OR ends_at>starts_at)
);

CREATE TABLE ctm.testimony_invitation_responses (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  appointment_version_id uuid NOT NULL,
  party_id uuid NOT NULL,
  response text NOT NULL,
  explanation text,
  CHECK(response IN ('confirm','reject'))
);

CREATE TABLE ctm.decision_types (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  code text NOT NULL,
  label_en text NOT NULL,
  label_ar text,
  entitlement_rule jsonb NOT NULL,
  active boolean NOT NULL DEFAULT true,
  UNIQUE(code)
);

CREATE TABLE ctm.case_decision_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  case_id uuid NOT NULL,
  proceeding_id uuid NOT NULL,
  hearing_id uuid,
  version integer NOT NULL,
  type_id uuid NOT NULL,
  grounds_reason text NOT NULL,
  party_outcomes jsonb NOT NULL,
  conditions text,
  UNIQUE(proceeding_id,version)
);

CREATE TABLE ctm.council_votes (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  decision_version_id uuid NOT NULL,
  voting_member_id uuid NOT NULL,
  vote text NOT NULL,
  supersedes_vote_id uuid,
  CHECK(vote IN ('approve','deny','abstain'))
);

CREATE TABLE ctm.presidential_approvals (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  decision_version_id uuid NOT NULL,
  president_member_id uuid NOT NULL,
  approved_at timestamptz NOT NULL,
  revoked_at timestamptz
);

CREATE TABLE ctm.decree_template_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  type_id uuid NOT NULL,
  version integer NOT NULL,
  content_en text NOT NULL,
  content_ar text NOT NULL,
  layout_definition jsonb NOT NULL,
  published_by_id uuid NOT NULL,
  digest text NOT NULL,
  UNIQUE(type_id,version)
);

CREATE TABLE ctm.decrees (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  proceeding_id uuid NOT NULL,
  decision_version_id uuid NOT NULL,
  decree_reference text NOT NULL,
  template_version_id uuid NOT NULL,
  language text NOT NULL,
  prepared_by_id uuid NOT NULL,
  UNIQUE(proceeding_id),
  UNIQUE(decree_reference),
  CHECK(language IN ('en','ar','both'))
);

CREATE TABLE ctm.decree_certificates (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  decree_id uuid NOT NULL,
  signed_file_version_id uuid NOT NULL,
  president_member_id uuid NOT NULL,
  signature_method text NOT NULL,
  signature_metadata jsonb NOT NULL,
  prepared_by_id uuid NOT NULL,
  UNIQUE(decree_id)
);

CREATE TABLE ctm.decree_issuance_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  decree_id uuid NOT NULL,
  certificate_id uuid NOT NULL,
  approval_id uuid NOT NULL,
  issued_at timestamptz NOT NULL,
  UNIQUE(decree_id)
);

CREATE TABLE ctm.decree_entitlements (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  decree_id uuid NOT NULL,
  party_id uuid NOT NULL,
  entitlement text NOT NULL,
  UNIQUE(decree_id,party_id),
  CHECK(entitlement IN ('certificate','notice_only'))
);

CREATE TABLE ctm.decree_release_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  entitlement_id uuid NOT NULL,
  certificate_id uuid NOT NULL,
  action text NOT NULL,
  CHECK(action IN ('release','withdraw'))
);

CREATE TABLE ctm.appeal_applications (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  application_id uuid NOT NULL,
  case_id uuid NOT NULL,
  party_id uuid NOT NULL,
  challenged_decision_id uuid,
  challenged_decree_id uuid,
  status text NOT NULL,
  UNIQUE(application_id)
);

CREATE TABLE ctm.pending_appeal_claims (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  person_id uuid NOT NULL,
  appeal_id uuid NOT NULL,
  UNIQUE(case_id,person_id),
  UNIQUE(appeal_id)
);

CREATE TABLE ctm.appeal_supplements (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  appeal_id uuid NOT NULL,
  text_content text NOT NULL,
  file_manifest jsonb NOT NULL
);

CREATE TABLE ctm.hearing_appeals (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  hearing_id uuid NOT NULL,
  appeal_id uuid NOT NULL,
  UNIQUE(hearing_id,appeal_id)
);

CREATE TABLE ctm.appeal_dispositions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  appeal_id uuid NOT NULL,
  hearing_id uuid NOT NULL,
  result text NOT NULL,
  explanation text,
  reopened_proceeding_id uuid,
  UNIQUE(appeal_id),
  CHECK(result IN ('accept','decline'))
);

CREATE TABLE ctm.proceeding_appeals (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  proceeding_id uuid NOT NULL,
  appeal_id uuid NOT NULL,
  UNIQUE(appeal_id)
);

CREATE TABLE ctm.appeal_withdrawals (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  appeal_id uuid NOT NULL,
  UNIQUE(appeal_id)
);

CREATE TABLE ctm.communications (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  proceeding_id uuid,
  sender_account_id uuid,
  direction text NOT NULL,
  channel text NOT NULL,
  subject text,
  body text NOT NULL,
  sent_at timestamptz,
  email_timing text NOT NULL,
  council_session_id uuid,
  template_snapshot jsonb NOT NULL,
  CHECK(channel IN ('portal','email','call')),
  CHECK(email_timing IN ('immediate','after_council_session','none'))
);

CREATE TABLE ctm.communication_recipients (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  communication_id uuid NOT NULL,
  party_id uuid,
  account_id uuid,
  external_email text,
  recipient_snapshot jsonb NOT NULL,
  read_at timestamptz
);

CREATE TABLE ctm.communication_file_links (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  communication_id uuid NOT NULL,
  file_version_id uuid NOT NULL,
  UNIQUE(communication_id,file_version_id)
);

CREATE TABLE ctm.call_details (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  communication_id uuid NOT NULL,
  contacted_person text NOT NULL,
  call_at timestamptz NOT NULL,
  outcome text NOT NULL,
  notes text,
  UNIQUE(communication_id)
);

CREATE TABLE ctm.reply_routes (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  recipient_id uuid NOT NULL,
  token_hash text NOT NULL,
  revoked_at timestamptz,
  UNIQUE(token_hash)
);

CREATE TABLE ctm.inbound_email_receipts (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  provider text NOT NULL,
  message_id text NOT NULL,
  sender_snapshot jsonb NOT NULL,
  safe_headers jsonb NOT NULL,
  body text NOT NULL,
  received_at timestamptz NOT NULL,
  routing_state text NOT NULL,
  recipient_id uuid,
  communication_id uuid,
  UNIQUE(provider,message_id)
);

CREATE TABLE ctm.email_attachment_returns (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  receipt_id uuid NOT NULL,
  metadata jsonb NOT NULL,
  temporary_payload_key text,
  cleanup_due_at timestamptz,
  return_delivery_id uuid,
  status text NOT NULL
);

CREATE TABLE ctm.notifications (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  recipient_account_id uuid NOT NULL,
  case_id uuid,
  event_key text NOT NULL,
  purpose text NOT NULL,
  safe_payload jsonb NOT NULL,
  read_at timestamptz,
  UNIQUE(recipient_account_id,event_key,purpose)
);

CREATE TABLE ctm.channel_deliveries (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  communication_recipient_id uuid,
  notification_id uuid,
  channel text NOT NULL,
  address_snapshot text NOT NULL,
  rendered_payload jsonb NOT NULL,
  due_at timestamptz,
  state text NOT NULL,
  provider_id text,
  idempotency_key text NOT NULL,
  CHECK(num_nonnulls(communication_recipient_id,notification_id)=1),
  UNIQUE(idempotency_key)
);

CREATE TABLE ctm.delivery_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  delivery_id uuid NOT NULL,
  provider_event_key text NOT NULL,
  result text NOT NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE(provider_event_key)
);

CREATE TABLE ctm.notification_batches (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  case_id uuid NOT NULL,
  source_person_id uuid NOT NULL,
  due_at timestamptz NOT NULL,
  status text NOT NULL,
  event_keys jsonb NOT NULL,
  delivered_to_id uuid
);

CREATE TABLE ctm.audit_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  case_id uuid,
  subject_person_id uuid,
  operation text NOT NULL,
  source_table text NOT NULL,
  source_id uuid NOT NULL,
  classification text NOT NULL,
  safe_details jsonb NOT NULL
);

CREATE TABLE ctm.outbox_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  event_key text NOT NULL,
  kind text NOT NULL,
  aggregate_id uuid NOT NULL,
  source_version_id uuid,
  safe_payload jsonb NOT NULL,
  processed_at timestamptz,
  UNIQUE(event_key)
);

CREATE TABLE ctm.background_jobs (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  outbox_id uuid,
  kind text NOT NULL,
  source_reference jsonb NOT NULL,
  status text NOT NULL,
  due_at timestamptz NOT NULL,
  attempt integer NOT NULL DEFAULT 0,
  lease_until timestamptz,
  safe_error text,
  CHECK(attempt>=0)
);

CREATE TABLE ctm.draft_retention_events (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  application_id uuid,
  application_snapshot_id uuid NOT NULL,
  event_type text NOT NULL,
  deadline timestamptz NOT NULL,
  retained_metadata jsonb NOT NULL
);

CREATE TABLE ctm.system_setting_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  key text NOT NULL,
  version integer NOT NULL,
  safe_value jsonb NOT NULL,
  edited_by_id uuid NOT NULL,
  UNIQUE(key,version)
);

CREATE TABLE ctm.translation_prompt_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  version integer NOT NULL,
  content text NOT NULL,
  digest text NOT NULL,
  edited_by_id uuid NOT NULL,
  UNIQUE(version)
);

CREATE TABLE ctm.integration_configurations (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  purpose text NOT NULL,
  priority integer NOT NULL,
  provider text NOT NULL,
  mode text NOT NULL,
  safe_configuration jsonb NOT NULL,
  secret_reference text,
  enabled boolean NOT NULL DEFAULT false,
  UNIQUE(purpose,priority),
  CHECK(priority>0)
);

CREATE TABLE ctm.translation_jobs (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  source_kind text NOT NULL,
  source_id uuid NOT NULL,
  source_version text NOT NULL,
  source_locale text NOT NULL,
  target_locale text NOT NULL,
  prompt_version_id uuid NOT NULL,
  provider_configuration_id uuid,
  status text NOT NULL,
  content_class text NOT NULL
);

CREATE TABLE ctm.translation_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid,
  request_id uuid,
  job_id uuid NOT NULL,
  version integer NOT NULL,
  content text NOT NULL,
  state text NOT NULL,
  reviewer_id uuid,
  UNIQUE(job_id,version)
);

CREATE TABLE ctm.ui_resource_versions (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  resource_key text NOT NULL,
  version integer NOT NULL,
  text_en text NOT NULL,
  text_ar text NOT NULL,
  published_by_id uuid NOT NULL,
  digest text NOT NULL,
  UNIQUE(resource_key,version)
);

CREATE TABLE ctm.recovery_manifests (
  id uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  backup_reference text NOT NULL,
  file_manifest_digest text NOT NULL,
  database_backup_reference text NOT NULL,
  secret_backup_reference text NOT NULL,
  restore_verified_at timestamptz,
  result jsonb NOT NULL
);

ALTER TABLE ctm.persons ADD CONSTRAINT fk_persons_canonical_person_id FOREIGN KEY (canonical_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_identity_versions ADD CONSTRAINT fk_person_identity_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_identity_versions ADD CONSTRAINT fk_person_identity_versions_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.accounts ADD CONSTRAINT fk_accounts_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.account_identities ADD CONSTRAINT fk_account_identities_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.account_email_versions ADD CONSTRAINT fk_account_email_versions_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.verification_tokens ADD CONSTRAINT fk_verification_tokens_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.app_sessions ADD CONSTRAINT fk_app_sessions_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.app_sessions ADD CONSTRAINT fk_app_sessions_provider_identity_id FOREIGN KEY (provider_identity_id) REFERENCES ctm.account_identities(id) ON DELETE RESTRICT;

ALTER TABLE ctm.staff_memberships ADD CONSTRAINT fk_staff_memberships_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.staff_memberships ADD CONSTRAINT fk_staff_memberships_tribunal_id FOREIGN KEY (tribunal_id) REFERENCES ctm.tribunals(id) ON DELETE RESTRICT;

ALTER TABLE ctm.staff_memberships ADD CONSTRAINT fk_staff_memberships_appointed_by_id FOREIGN KEY (appointed_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.staff_roles ADD CONSTRAINT fk_staff_roles_membership_id FOREIGN KEY (membership_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.staff_roles ADD CONSTRAINT fk_staff_roles_granted_by_id FOREIGN KEY (granted_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.account_events ADD CONSTRAINT fk_account_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.account_events ADD CONSTRAINT fk_account_events_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_consolidations ADD CONSTRAINT fk_identity_consolidations_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_consolidations ADD CONSTRAINT fk_identity_consolidations_source_person_id FOREIGN KEY (source_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_consolidations ADD CONSTRAINT fk_identity_consolidations_target_person_id FOREIGN KEY (target_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_consolidations ADD CONSTRAINT fk_identity_consolidations_primary_account_id FOREIGN KEY (primary_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_consolidations ADD CONSTRAINT fk_identity_consolidations_disabled_account_id FOREIGN KEY (disabled_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_review_holds ADD CONSTRAINT fk_identity_review_holds_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_review_holds ADD CONSTRAINT fk_identity_review_holds_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.identity_review_holds ADD CONSTRAINT fk_identity_review_holds_resolved_by_id FOREIGN KEY (resolved_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.ctm_applicants ADD CONSTRAINT fk_ctm_applicants_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.ctm_applicants ADD CONSTRAINT fk_ctm_applicants_tribunal_id FOREIGN KEY (tribunal_id) REFERENCES ctm.tribunals(id) ON DELETE RESTRICT;

ALTER TABLE ctm.parishes ADD CONSTRAINT fk_parishes_diocese_id FOREIGN KEY (diocese_id) REFERENCES ctm.dioceses(id) ON DELETE RESTRICT;

ALTER TABLE ctm.cases ADD CONSTRAINT fk_cases_tribunal_id FOREIGN KEY (tribunal_id) REFERENCES ctm.tribunals(id) ON DELETE RESTRICT;

ALTER TABLE ctm.cases ADD CONSTRAINT fk_cases_marriage_id FOREIGN KEY (marriage_id) REFERENCES ctm.marriages(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_identifiers ADD CONSTRAINT fk_case_identifiers_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_parties ADD CONSTRAINT fk_case_parties_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_parties ADD CONSTRAINT fk_case_parties_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_parties ADD CONSTRAINT fk_case_parties_applicant_id FOREIGN KEY (applicant_id) REFERENCES ctm.ctm_applicants(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applicant_references ADD CONSTRAINT fk_applicant_references_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_open_case_claims ADD CONSTRAINT fk_person_open_case_claims_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_open_case_claims ADD CONSTRAINT fk_person_open_case_claims_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_open_case_claims ADD CONSTRAINT fk_person_open_case_claims_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_active_draft_claims ADD CONSTRAINT fk_person_active_draft_claims_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.person_active_draft_claims ADD CONSTRAINT fk_person_active_draft_claims_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_proceedings ADD CONSTRAINT fk_case_proceedings_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_lifecycle_events ADD CONSTRAINT fk_case_lifecycle_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_lifecycle_events ADD CONSTRAINT fk_case_lifecycle_events_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_lifecycle_events ADD CONSTRAINT fk_case_lifecycle_events_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_association_events ADD CONSTRAINT fk_case_association_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_association_events ADD CONSTRAINT fk_case_association_events_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_association_events ADD CONSTRAINT fk_case_association_events_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_party_onboarding ADD CONSTRAINT fk_case_party_onboarding_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_party_onboarding ADD CONSTRAINT fk_case_party_onboarding_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_party_onboarding ADD CONSTRAINT fk_case_party_onboarding_entered_by_id FOREIGN KEY (entered_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_party_onboarding ADD CONSTRAINT fk_case_party_onboarding_activated_account_id FOREIGN KEY (activated_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.registration_invitation_events ADD CONSTRAINT fk_registration_invitation_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.registration_invitation_events ADD CONSTRAINT fk_registration_invitation_events_onboarding_id FOREIGN KEY (onboarding_id) REFERENCES ctm.case_party_onboarding(id) ON DELETE RESTRICT;

ALTER TABLE ctm.registration_invitation_events ADD CONSTRAINT fk_registration_invitation_events_communication_id FOREIGN KEY (communication_id) REFERENCES ctm.communications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_assignments ADD CONSTRAINT fk_case_assignments_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_assignments ADD CONSTRAINT fk_case_assignments_member_id FOREIGN KEY (member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_assignments ADD CONSTRAINT fk_case_assignments_president_id FOREIGN KEY (president_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_assignments ADD CONSTRAINT fk_case_assignments_recorded_by_id FOREIGN KEY (recorded_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_assignments ADD CONSTRAINT fk_case_assignments_session_id FOREIGN KEY (session_id) REFERENCES ctm.council_sessions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.historical_entry_workspaces ADD CONSTRAINT fk_historical_entry_workspaces_created_by_id FOREIGN KEY (created_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.historical_entry_workspaces ADD CONSTRAINT fk_historical_entry_workspaces_published_case_id FOREIGN KEY (published_case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.questionnaire_versions ADD CONSTRAINT fk_questionnaire_versions_questionnaire_id FOREIGN KEY (questionnaire_id) REFERENCES ctm.questionnaires(id) ON DELETE RESTRICT;

ALTER TABLE ctm.questionnaire_versions ADD CONSTRAINT fk_questionnaire_versions_published_by_id FOREIGN KEY (published_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.declaration_versions ADD CONSTRAINT fk_declaration_versions_published_by_id FOREIGN KEY (published_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applications ADD CONSTRAINT fk_applications_owner_person_id FOREIGN KEY (owner_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applications ADD CONSTRAINT fk_applications_owner_account_id FOREIGN KEY (owner_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applications ADD CONSTRAINT fk_applications_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applications ADD CONSTRAINT fk_applications_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applications ADD CONSTRAINT fk_applications_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.applications ADD CONSTRAINT fk_applications_questionnaire_version_id FOREIGN KEY (questionnaire_version_id) REFERENCES ctm.questionnaire_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_revisions ADD CONSTRAINT fk_application_revisions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_revisions ADD CONSTRAINT fk_application_revisions_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_revisions ADD CONSTRAINT fk_application_revisions_predecessor_id FOREIGN KEY (predecessor_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_revisions ADD CONSTRAINT fk_application_revisions_questionnaire_version_id FOREIGN KEY (questionnaire_version_id) REFERENCES ctm.questionnaire_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_person_assertions ADD CONSTRAINT fk_application_person_assertions_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_marriage_assertions ADD CONSTRAINT fk_application_marriage_assertions_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_separation_assertions ADD CONSTRAINT fk_application_separation_assertions_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_repeat_entries ADD CONSTRAINT fk_application_repeat_entries_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_children ADD CONSTRAINT fk_application_children_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_children ADD CONSTRAINT fk_application_children_entry_id FOREIGN KEY (entry_id) REFERENCES ctm.application_repeat_entries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_restraining_orders ADD CONSTRAINT fk_application_restraining_orders_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_restraining_orders ADD CONSTRAINT fk_application_restraining_orders_entry_id FOREIGN KEY (entry_id) REFERENCES ctm.application_repeat_entries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_prior_records ADD CONSTRAINT fk_application_prior_records_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_prior_records ADD CONSTRAINT fk_application_prior_records_entry_id FOREIGN KEY (entry_id) REFERENCES ctm.application_repeat_entries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answers ADD CONSTRAINT fk_application_answers_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answers ADD CONSTRAINT fk_application_answers_entry_id FOREIGN KEY (entry_id) REFERENCES ctm.application_repeat_entries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_selected_grounds ADD CONSTRAINT fk_application_selected_grounds_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_selected_grounds ADD CONSTRAINT fk_application_selected_grounds_ground_id FOREIGN KEY (ground_id) REFERENCES ctm.ground_definitions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answer_changes ADD CONSTRAINT fk_application_answer_changes_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answer_changes ADD CONSTRAINT fk_application_answer_changes_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answer_changes ADD CONSTRAINT fk_application_answer_changes_from_revision_id FOREIGN KEY (from_revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answer_changes ADD CONSTRAINT fk_application_answer_changes_to_revision_id FOREIGN KEY (to_revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_answer_changes ADD CONSTRAINT fk_application_answer_changes_entry_id FOREIGN KEY (entry_id) REFERENCES ctm.application_repeat_entries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.filing_candidates ADD CONSTRAINT fk_filing_candidates_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.filing_candidates ADD CONSTRAINT fk_filing_candidates_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_candidate_id FOREIGN KEY (candidate_id) REFERENCES ctm.filing_candidates(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_previous_submission_id FOREIGN KEY (previous_submission_id) REFERENCES ctm.application_submissions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_declaration_version_id FOREIGN KEY (declaration_version_id) REFERENCES ctm.declaration_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_signature_file_version_id FOREIGN KEY (signature_file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_submissions ADD CONSTRAINT fk_application_submissions_submitted_by_id FOREIGN KEY (submitted_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_completeness_reviews ADD CONSTRAINT fk_application_completeness_reviews_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.application_completeness_reviews ADD CONSTRAINT fk_application_completeness_reviews_submission_id FOREIGN KEY (submission_id) REFERENCES ctm.application_submissions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_schema_migrations ADD CONSTRAINT fk_draft_schema_migrations_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_schema_migrations ADD CONSTRAINT fk_draft_schema_migrations_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_schema_migrations ADD CONSTRAINT fk_draft_schema_migrations_from_version_id FOREIGN KEY (from_version_id) REFERENCES ctm.questionnaire_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_schema_migrations ADD CONSTRAINT fk_draft_schema_migrations_to_version_id FOREIGN KEY (to_version_id) REFERENCES ctm.questionnaire_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_schema_migrations ADD CONSTRAINT fk_draft_schema_migrations_notice_id FOREIGN KEY (notice_id) REFERENCES ctm.notifications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.party_withdrawals ADD CONSTRAINT fk_party_withdrawals_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.party_withdrawals ADD CONSTRAINT fk_party_withdrawals_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.party_withdrawals ADD CONSTRAINT fk_party_withdrawals_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.files ADD CONSTRAINT fk_files_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.files ADD CONSTRAINT fk_files_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.files ADD CONSTRAINT fk_files_owner_application_id FOREIGN KEY (owner_application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.files ADD CONSTRAINT fk_files_owner_party_id FOREIGN KEY (owner_party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.files ADD CONSTRAINT fk_files_report_request_id FOREIGN KEY (report_request_id) REFERENCES ctm.report_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.files ADD CONSTRAINT fk_files_category_id FOREIGN KEY (category_id) REFERENCES ctm.document_categories(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_versions ADD CONSTRAINT fk_file_versions_file_id FOREIGN KEY (file_id) REFERENCES ctm.files(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_versions ADD CONSTRAINT fk_file_versions_uploaded_by_id FOREIGN KEY (uploaded_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_versions ADD CONSTRAINT fk_file_versions_external_link_id FOREIGN KEY (external_link_id) REFERENCES ctm.external_report_links(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_name_events ADD CONSTRAINT fk_file_name_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_name_events ADD CONSTRAINT fk_file_name_events_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_context_links ADD CONSTRAINT fk_file_context_links_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_context_links ADD CONSTRAINT fk_file_context_links_application_revision_id FOREIGN KEY (application_revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_context_links ADD CONSTRAINT fk_file_context_links_repeat_entry_id FOREIGN KEY (repeat_entry_id) REFERENCES ctm.application_repeat_entries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_context_links ADD CONSTRAINT fk_file_context_links_report_revision_id FOREIGN KEY (report_revision_id) REFERENCES ctm.report_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_context_links ADD CONSTRAINT fk_file_context_links_medical_report_id FOREIGN KEY (medical_report_id) REFERENCES ctm.evaluation_reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.submission_file_manifest ADD CONSTRAINT fk_submission_file_manifest_submission_id FOREIGN KEY (submission_id) REFERENCES ctm.application_submissions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.submission_file_manifest ADD CONSTRAINT fk_submission_file_manifest_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.upload_sessions ADD CONSTRAINT fk_upload_sessions_file_id FOREIGN KEY (file_id) REFERENCES ctm.files(id) ON DELETE RESTRICT;

ALTER TABLE ctm.upload_sessions ADD CONSTRAINT fk_upload_sessions_uploader_id FOREIGN KEY (uploader_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.upload_sessions ADD CONSTRAINT fk_upload_sessions_external_link_id FOREIGN KEY (external_link_id) REFERENCES ctm.external_report_links(id) ON DELETE RESTRICT;

ALTER TABLE ctm.upload_sessions ADD CONSTRAINT fk_upload_sessions_completed_version_id FOREIGN KEY (completed_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_technical_events ADD CONSTRAINT fk_file_technical_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_technical_events ADD CONSTRAINT fk_file_technical_events_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_derivatives ADD CONSTRAINT fk_file_derivatives_source_version_id FOREIGN KEY (source_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_access_events ADD CONSTRAINT fk_file_access_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.file_access_events ADD CONSTRAINT fk_file_access_events_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.search_documents ADD CONSTRAINT fk_search_documents_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.search_documents ADD CONSTRAINT fk_search_documents_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.fee_obligations ADD CONSTRAINT fk_fee_obligations_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.fee_waivers ADD CONSTRAINT fk_fee_waivers_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.fee_waivers ADD CONSTRAINT fk_fee_waivers_obligation_id FOREIGN KEY (obligation_id) REFERENCES ctm.fee_obligations(id) ON DELETE RESTRICT;

ALTER TABLE ctm.payment_attempts ADD CONSTRAINT fk_payment_attempts_obligation_id FOREIGN KEY (obligation_id) REFERENCES ctm.fee_obligations(id) ON DELETE RESTRICT;

ALTER TABLE ctm.payment_attempts ADD CONSTRAINT fk_payment_attempts_candidate_id FOREIGN KEY (candidate_id) REFERENCES ctm.filing_candidates(id) ON DELETE RESTRICT;

ALTER TABLE ctm.payment_events ADD CONSTRAINT fk_payment_events_attempt_id FOREIGN KEY (attempt_id) REFERENCES ctm.payment_attempts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.payment_allocations ADD CONSTRAINT fk_payment_allocations_attempt_id FOREIGN KEY (attempt_id) REFERENCES ctm.payment_attempts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.payment_allocations ADD CONSTRAINT fk_payment_allocations_obligation_id FOREIGN KEY (obligation_id) REFERENCES ctm.fee_obligations(id) ON DELETE RESTRICT;

ALTER TABLE ctm.payment_allocations ADD CONSTRAINT fk_payment_allocations_submission_id FOREIGN KEY (submission_id) REFERENCES ctm.application_submissions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.refund_events ADD CONSTRAINT fk_refund_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.refund_events ADD CONSTRAINT fk_refund_events_attempt_id FOREIGN KEY (attempt_id) REFERENCES ctm.payment_attempts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_question_versions ADD CONSTRAINT fk_report_question_versions_question_id FOREIGN KEY (question_id) REFERENCES ctm.report_questions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_question_versions ADD CONSTRAINT fk_report_question_versions_published_by_id FOREIGN KEY (published_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.topic_category_memberships ADD CONSTRAINT fk_topic_category_memberships_topic_group_id FOREIGN KEY (topic_group_id) REFERENCES ctm.topic_groups(id) ON DELETE RESTRICT;

ALTER TABLE ctm.topic_category_memberships ADD CONSTRAINT fk_topic_category_memberships_category_id FOREIGN KEY (category_id) REFERENCES ctm.question_categories(id) ON DELETE RESTRICT;

ALTER TABLE ctm.category_question_memberships ADD CONSTRAINT fk_category_question_memberships_category_id FOREIGN KEY (category_id) REFERENCES ctm.question_categories(id) ON DELETE RESTRICT;

ALTER TABLE ctm.category_question_memberships ADD CONSTRAINT fk_category_question_memberships_question_id FOREIGN KEY (question_id) REFERENCES ctm.report_questions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_templates ADD CONSTRAINT fk_report_templates_owner_member_id FOREIGN KEY (owner_member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_template_versions ADD CONSTRAINT fk_report_template_versions_template_id FOREIGN KEY (template_id) REFERENCES ctm.report_templates(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_template_versions ADD CONSTRAINT fk_report_template_versions_published_by_id FOREIGN KEY (published_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.template_publication_submissions ADD CONSTRAINT fk_template_publication_submissions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.template_publication_submissions ADD CONSTRAINT fk_template_publication_submissions_personal_version_id FOREIGN KEY (personal_version_id) REFERENCES ctm.report_template_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.template_publication_submissions ADD CONSTRAINT fk_template_publication_submissions_shared_version_id FOREIGN KEY (shared_version_id) REFERENCES ctm.report_template_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.template_publication_submissions ADD CONSTRAINT fk_template_publication_submissions_reviewed_by_id FOREIGN KEY (reviewed_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_requests ADD CONSTRAINT fk_report_requests_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_requests ADD CONSTRAINT fk_report_requests_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_requests ADD CONSTRAINT fk_report_requests_subject_party_id FOREIGN KEY (subject_party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_requests ADD CONSTRAINT fk_report_requests_parent_report_id FOREIGN KEY (parent_report_id) REFERENCES ctm.reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_requests ADD CONSTRAINT fk_report_requests_created_by_id FOREIGN KEY (created_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_requests ADD CONSTRAINT fk_report_requests_template_version_id FOREIGN KEY (template_version_id) REFERENCES ctm.report_template_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.sent_intake_question_snapshots ADD CONSTRAINT fk_sent_intake_question_snapshots_request_id FOREIGN KEY (request_id) REFERENCES ctm.report_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.sent_intake_question_snapshots ADD CONSTRAINT fk_sent_intake_question_snapshots_source_question_version_id FOREIGN KEY (source_question_version_id) REFERENCES ctm.report_question_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.external_report_links ADD CONSTRAINT fk_external_report_links_request_id FOREIGN KEY (request_id) REFERENCES ctm.report_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.external_response_drafts ADD CONSTRAINT fk_external_response_drafts_request_id FOREIGN KEY (request_id) REFERENCES ctm.report_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_request_id FOREIGN KEY (request_id) REFERENCES ctm.report_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_subject_party_id FOREIGN KEY (subject_party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_parent_report_id FOREIGN KEY (parent_report_id) REFERENCES ctm.reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_author_account_id FOREIGN KEY (author_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reports ADD CONSTRAINT fk_reports_recorded_by_id FOREIGN KEY (recorded_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_revisions ADD CONSTRAINT fk_report_revisions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_revisions ADD CONSTRAINT fk_report_revisions_report_id FOREIGN KEY (report_id) REFERENCES ctm.reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_revisions ADD CONSTRAINT fk_report_revisions_predecessor_id FOREIGN KEY (predecessor_id) REFERENCES ctm.report_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_answers ADD CONSTRAINT fk_report_answers_revision_id FOREIGN KEY (revision_id) REFERENCES ctm.report_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_answers ADD CONSTRAINT fk_report_answers_question_snapshot_id FOREIGN KEY (question_snapshot_id) REFERENCES ctm.sent_intake_question_snapshots(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_source_links ADD CONSTRAINT fk_report_source_links_report_revision_id FOREIGN KEY (report_revision_id) REFERENCES ctm.report_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_source_links ADD CONSTRAINT fk_report_source_links_question_snapshot_id FOREIGN KEY (question_snapshot_id) REFERENCES ctm.sent_intake_question_snapshots(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_source_links ADD CONSTRAINT fk_report_source_links_source_application_revision_id FOREIGN KEY (source_application_revision_id) REFERENCES ctm.application_revisions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.report_source_links ADD CONSTRAINT fk_report_source_links_source_file_version_id FOREIGN KEY (source_file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.recordings ADD CONSTRAINT fk_recordings_report_id FOREIGN KEY (report_id) REFERENCES ctm.reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.recordings ADD CONSTRAINT fk_recordings_testimony_appointment_id FOREIGN KEY (testimony_appointment_id) REFERENCES ctm.testimony_appointments(id) ON DELETE RESTRICT;

ALTER TABLE ctm.recordings ADD CONSTRAINT fk_recordings_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.recordings ADD CONSTRAINT fk_recordings_captured_by_id FOREIGN KEY (captured_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.processing_runs ADD CONSTRAINT fk_processing_runs_recording_id FOREIGN KEY (recording_id) REFERENCES ctm.recordings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.processing_runs ADD CONSTRAINT fk_processing_runs_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_versions ADD CONSTRAINT fk_transcript_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_versions ADD CONSTRAINT fk_transcript_versions_recording_id FOREIGN KEY (recording_id) REFERENCES ctm.recordings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_versions ADD CONSTRAINT fk_transcript_versions_run_id FOREIGN KEY (run_id) REFERENCES ctm.processing_runs(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_versions ADD CONSTRAINT fk_transcript_versions_predecessor_id FOREIGN KEY (predecessor_id) REFERENCES ctm.transcript_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_versions ADD CONSTRAINT fk_transcript_versions_source_transcript_id FOREIGN KEY (source_transcript_id) REFERENCES ctm.transcript_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_segments ADD CONSTRAINT fk_transcript_segments_text_version_id FOREIGN KEY (text_version_id) REFERENCES ctm.transcript_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_segments ADD CONSTRAINT fk_transcript_segments_speaker_person_id FOREIGN KEY (speaker_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.transcript_segments ADD CONSTRAINT fk_transcript_segments_source_segment_id FOREIGN KEY (source_segment_id) REFERENCES ctm.transcript_segments(id) ON DELETE RESTRICT;

ALTER TABLE ctm.text_review_events ADD CONSTRAINT fk_text_review_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.text_review_events ADD CONSTRAINT fk_text_review_events_text_version_id FOREIGN KEY (text_version_id) REFERENCES ctm.transcript_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.text_review_events ADD CONSTRAINT fk_text_review_events_reviewer_member_id FOREIGN KEY (reviewer_member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_requests ADD CONSTRAINT fk_evaluation_requests_report_request_id FOREIGN KEY (report_request_id) REFERENCES ctm.report_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_requests ADD CONSTRAINT fk_evaluation_requests_subject_party_id FOREIGN KEY (subject_party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_release_attestations ADD CONSTRAINT fk_evaluation_release_attestations_evaluation_request_id FOREIGN KEY (evaluation_request_id) REFERENCES ctm.evaluation_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_release_attestations ADD CONSTRAINT fk_evaluation_release_attestations_declaration_version_id FOREIGN KEY (declaration_version_id) REFERENCES ctm.declaration_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_release_attestations ADD CONSTRAINT fk_evaluation_release_attestations_subject_person_id FOREIGN KEY (subject_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_release_attestations ADD CONSTRAINT fk_evaluation_release_attestations_signer_person_id FOREIGN KEY (signer_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_release_attestations ADD CONSTRAINT fk_evaluation_release_attestations_signature_file_version_id FOREIGN KEY (signature_file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_release_scopes ADD CONSTRAINT fk_evaluation_release_scopes_attestation_id FOREIGN KEY (attestation_id) REFERENCES ctm.evaluation_release_attestations(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_reports ADD CONSTRAINT fk_evaluation_reports_evaluation_request_id FOREIGN KEY (evaluation_request_id) REFERENCES ctm.evaluation_requests(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_reports ADD CONSTRAINT fk_evaluation_reports_report_id FOREIGN KEY (report_id) REFERENCES ctm.reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_reports ADD CONSTRAINT fk_evaluation_reports_release_attestation_id FOREIGN KEY (release_attestation_id) REFERENCES ctm.evaluation_release_attestations(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_disclosures ADD CONSTRAINT fk_evaluation_disclosures_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_disclosures ADD CONSTRAINT fk_evaluation_disclosures_evaluation_report_id FOREIGN KEY (evaluation_report_id) REFERENCES ctm.evaluation_reports(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_disclosures ADD CONSTRAINT fk_evaluation_disclosures_release_scope_id FOREIGN KEY (release_scope_id) REFERENCES ctm.evaluation_release_scopes(id) ON DELETE RESTRICT;

ALTER TABLE ctm.evaluation_disclosures ADD CONSTRAINT fk_evaluation_disclosures_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_findings ADD CONSTRAINT fk_case_findings_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_findings ADD CONSTRAINT fk_case_findings_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.finding_versions ADD CONSTRAINT fk_finding_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.finding_versions ADD CONSTRAINT fk_finding_versions_finding_id FOREIGN KEY (finding_id) REFERENCES ctm.case_findings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_notes ADD CONSTRAINT fk_case_notes_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_notes ADD CONSTRAINT fk_case_notes_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_notes ADD CONSTRAINT fk_case_notes_author_id FOREIGN KEY (author_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.note_versions ADD CONSTRAINT fk_note_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.note_versions ADD CONSTRAINT fk_note_versions_note_id FOREIGN KEY (note_id) REFERENCES ctm.case_notes(id) ON DELETE RESTRICT;

ALTER TABLE ctm.council_sessions ADD CONSTRAINT fk_council_sessions_created_by_id FOREIGN KEY (created_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_requests ADD CONSTRAINT fk_agenda_requests_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_requests ADD CONSTRAINT fk_agenda_requests_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_requests ADD CONSTRAINT fk_agenda_requests_requested_session_id FOREIGN KEY (requested_session_id) REFERENCES ctm.council_sessions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_requests ADD CONSTRAINT fk_agenda_requests_placed_item_id FOREIGN KEY (placed_item_id) REFERENCES ctm.session_agenda_items(id) ON DELETE RESTRICT;

ALTER TABLE ctm.session_agenda_items ADD CONSTRAINT fk_session_agenda_items_session_id FOREIGN KEY (session_id) REFERENCES ctm.council_sessions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.session_agenda_items ADD CONSTRAINT fk_session_agenda_items_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.session_agenda_items ADD CONSTRAINT fk_session_agenda_items_carried_from_id FOREIGN KEY (carried_from_id) REFERENCES ctm.session_agenda_items(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_transfer_events ADD CONSTRAINT fk_agenda_transfer_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_transfer_events ADD CONSTRAINT fk_agenda_transfer_events_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_transfer_events ADD CONSTRAINT fk_agenda_transfer_events_to_session_id FOREIGN KEY (to_session_id) REFERENCES ctm.council_sessions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.agenda_transfer_events ADD CONSTRAINT fk_agenda_transfer_events_destination_item_id FOREIGN KEY (destination_item_id) REFERENCES ctm.session_agenda_items(id) ON DELETE RESTRICT;

ALTER TABLE ctm.session_attendance ADD CONSTRAINT fk_session_attendance_session_id FOREIGN KEY (session_id) REFERENCES ctm.council_sessions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.session_attendance ADD CONSTRAINT fk_session_attendance_member_id FOREIGN KEY (member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.session_attendance ADD CONSTRAINT fk_session_attendance_recorded_by_id FOREIGN KEY (recorded_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_hearings ADD CONSTRAINT fk_case_hearings_agenda_item_id FOREIGN KEY (agenda_item_id) REFERENCES ctm.session_agenda_items(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_hearings ADD CONSTRAINT fk_case_hearings_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_hearings ADD CONSTRAINT fk_case_hearings_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_hearings ADD CONSTRAINT fk_case_hearings_presenter_member_id FOREIGN KEY (presenter_member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_attendance ADD CONSTRAINT fk_hearing_attendance_hearing_id FOREIGN KEY (hearing_id) REFERENCES ctm.case_hearings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_attendance ADD CONSTRAINT fk_hearing_attendance_member_id FOREIGN KEY (member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_attendance ADD CONSTRAINT fk_hearing_attendance_recorded_by_id FOREIGN KEY (recorded_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_outcome_revisions ADD CONSTRAINT fk_hearing_outcome_revisions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_outcome_revisions ADD CONSTRAINT fk_hearing_outcome_revisions_hearing_id FOREIGN KEY (hearing_id) REFERENCES ctm.case_hearings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_outcome_revisions ADD CONSTRAINT fk_hearing_outcome_revisions_communication_id FOREIGN KEY (communication_id) REFERENCES ctm.communications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_appointments ADD CONSTRAINT fk_testimony_appointments_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_appointments ADD CONSTRAINT fk_testimony_appointments_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_appointments ADD CONSTRAINT fk_testimony_appointments_agenda_item_id FOREIGN KEY (agenda_item_id) REFERENCES ctm.session_agenda_items(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_appointments ADD CONSTRAINT fk_testimony_appointments_created_by_id FOREIGN KEY (created_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_appointment_versions ADD CONSTRAINT fk_testimony_appointment_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_appointment_versions ADD CONSTRAINT fk_testimony_appointment_versions_appointment_id FOREIGN KEY (appointment_id) REFERENCES ctm.testimony_appointments(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_invitation_responses ADD CONSTRAINT fk_testimony_invitation_responses_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_invitation_responses ADD CONSTRAINT fk_testimony_invitation_responses_appointment_version_id FOREIGN KEY (appointment_version_id) REFERENCES ctm.testimony_appointment_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.testimony_invitation_responses ADD CONSTRAINT fk_testimony_invitation_responses_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_decision_versions ADD CONSTRAINT fk_case_decision_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_decision_versions ADD CONSTRAINT fk_case_decision_versions_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_decision_versions ADD CONSTRAINT fk_case_decision_versions_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_decision_versions ADD CONSTRAINT fk_case_decision_versions_hearing_id FOREIGN KEY (hearing_id) REFERENCES ctm.case_hearings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.case_decision_versions ADD CONSTRAINT fk_case_decision_versions_type_id FOREIGN KEY (type_id) REFERENCES ctm.decision_types(id) ON DELETE RESTRICT;

ALTER TABLE ctm.council_votes ADD CONSTRAINT fk_council_votes_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.council_votes ADD CONSTRAINT fk_council_votes_decision_version_id FOREIGN KEY (decision_version_id) REFERENCES ctm.case_decision_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.council_votes ADD CONSTRAINT fk_council_votes_voting_member_id FOREIGN KEY (voting_member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.council_votes ADD CONSTRAINT fk_council_votes_supersedes_vote_id FOREIGN KEY (supersedes_vote_id) REFERENCES ctm.council_votes(id) ON DELETE RESTRICT;

ALTER TABLE ctm.presidential_approvals ADD CONSTRAINT fk_presidential_approvals_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.presidential_approvals ADD CONSTRAINT fk_presidential_approvals_decision_version_id FOREIGN KEY (decision_version_id) REFERENCES ctm.case_decision_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.presidential_approvals ADD CONSTRAINT fk_presidential_approvals_president_member_id FOREIGN KEY (president_member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_template_versions ADD CONSTRAINT fk_decree_template_versions_type_id FOREIGN KEY (type_id) REFERENCES ctm.decision_types(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_template_versions ADD CONSTRAINT fk_decree_template_versions_published_by_id FOREIGN KEY (published_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decrees ADD CONSTRAINT fk_decrees_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decrees ADD CONSTRAINT fk_decrees_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decrees ADD CONSTRAINT fk_decrees_decision_version_id FOREIGN KEY (decision_version_id) REFERENCES ctm.case_decision_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decrees ADD CONSTRAINT fk_decrees_template_version_id FOREIGN KEY (template_version_id) REFERENCES ctm.decree_template_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decrees ADD CONSTRAINT fk_decrees_prepared_by_id FOREIGN KEY (prepared_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_certificates ADD CONSTRAINT fk_decree_certificates_decree_id FOREIGN KEY (decree_id) REFERENCES ctm.decrees(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_certificates ADD CONSTRAINT fk_decree_certificates_signed_file_version_id FOREIGN KEY (signed_file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_certificates ADD CONSTRAINT fk_decree_certificates_president_member_id FOREIGN KEY (president_member_id) REFERENCES ctm.staff_memberships(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_certificates ADD CONSTRAINT fk_decree_certificates_prepared_by_id FOREIGN KEY (prepared_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_issuance_events ADD CONSTRAINT fk_decree_issuance_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_issuance_events ADD CONSTRAINT fk_decree_issuance_events_decree_id FOREIGN KEY (decree_id) REFERENCES ctm.decrees(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_issuance_events ADD CONSTRAINT fk_decree_issuance_events_certificate_id FOREIGN KEY (certificate_id) REFERENCES ctm.decree_certificates(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_issuance_events ADD CONSTRAINT fk_decree_issuance_events_approval_id FOREIGN KEY (approval_id) REFERENCES ctm.presidential_approvals(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_entitlements ADD CONSTRAINT fk_decree_entitlements_decree_id FOREIGN KEY (decree_id) REFERENCES ctm.decrees(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_entitlements ADD CONSTRAINT fk_decree_entitlements_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_release_events ADD CONSTRAINT fk_decree_release_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_release_events ADD CONSTRAINT fk_decree_release_events_entitlement_id FOREIGN KEY (entitlement_id) REFERENCES ctm.decree_entitlements(id) ON DELETE RESTRICT;

ALTER TABLE ctm.decree_release_events ADD CONSTRAINT fk_decree_release_events_certificate_id FOREIGN KEY (certificate_id) REFERENCES ctm.decree_certificates(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_applications ADD CONSTRAINT fk_appeal_applications_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_applications ADD CONSTRAINT fk_appeal_applications_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_applications ADD CONSTRAINT fk_appeal_applications_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_applications ADD CONSTRAINT fk_appeal_applications_challenged_decision_id FOREIGN KEY (challenged_decision_id) REFERENCES ctm.case_decision_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_applications ADD CONSTRAINT fk_appeal_applications_challenged_decree_id FOREIGN KEY (challenged_decree_id) REFERENCES ctm.decrees(id) ON DELETE RESTRICT;

ALTER TABLE ctm.pending_appeal_claims ADD CONSTRAINT fk_pending_appeal_claims_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.pending_appeal_claims ADD CONSTRAINT fk_pending_appeal_claims_person_id FOREIGN KEY (person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.pending_appeal_claims ADD CONSTRAINT fk_pending_appeal_claims_appeal_id FOREIGN KEY (appeal_id) REFERENCES ctm.appeal_applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_supplements ADD CONSTRAINT fk_appeal_supplements_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_supplements ADD CONSTRAINT fk_appeal_supplements_appeal_id FOREIGN KEY (appeal_id) REFERENCES ctm.appeal_applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_appeals ADD CONSTRAINT fk_hearing_appeals_hearing_id FOREIGN KEY (hearing_id) REFERENCES ctm.case_hearings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.hearing_appeals ADD CONSTRAINT fk_hearing_appeals_appeal_id FOREIGN KEY (appeal_id) REFERENCES ctm.appeal_applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_dispositions ADD CONSTRAINT fk_appeal_dispositions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_dispositions ADD CONSTRAINT fk_appeal_dispositions_appeal_id FOREIGN KEY (appeal_id) REFERENCES ctm.appeal_applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_dispositions ADD CONSTRAINT fk_appeal_dispositions_hearing_id FOREIGN KEY (hearing_id) REFERENCES ctm.case_hearings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_dispositions ADD CONSTRAINT fk_appeal_dispositions_reopened_proceeding_id FOREIGN KEY (reopened_proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.proceeding_appeals ADD CONSTRAINT fk_proceeding_appeals_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.proceeding_appeals ADD CONSTRAINT fk_proceeding_appeals_appeal_id FOREIGN KEY (appeal_id) REFERENCES ctm.appeal_applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_withdrawals ADD CONSTRAINT fk_appeal_withdrawals_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.appeal_withdrawals ADD CONSTRAINT fk_appeal_withdrawals_appeal_id FOREIGN KEY (appeal_id) REFERENCES ctm.appeal_applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communications ADD CONSTRAINT fk_communications_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communications ADD CONSTRAINT fk_communications_proceeding_id FOREIGN KEY (proceeding_id) REFERENCES ctm.case_proceedings(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communications ADD CONSTRAINT fk_communications_sender_account_id FOREIGN KEY (sender_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communications ADD CONSTRAINT fk_communications_council_session_id FOREIGN KEY (council_session_id) REFERENCES ctm.council_sessions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communication_recipients ADD CONSTRAINT fk_communication_recipients_communication_id FOREIGN KEY (communication_id) REFERENCES ctm.communications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communication_recipients ADD CONSTRAINT fk_communication_recipients_party_id FOREIGN KEY (party_id) REFERENCES ctm.case_parties(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communication_recipients ADD CONSTRAINT fk_communication_recipients_account_id FOREIGN KEY (account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communication_file_links ADD CONSTRAINT fk_communication_file_links_communication_id FOREIGN KEY (communication_id) REFERENCES ctm.communications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.communication_file_links ADD CONSTRAINT fk_communication_file_links_file_version_id FOREIGN KEY (file_version_id) REFERENCES ctm.file_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.call_details ADD CONSTRAINT fk_call_details_communication_id FOREIGN KEY (communication_id) REFERENCES ctm.communications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.reply_routes ADD CONSTRAINT fk_reply_routes_recipient_id FOREIGN KEY (recipient_id) REFERENCES ctm.communication_recipients(id) ON DELETE RESTRICT;

ALTER TABLE ctm.inbound_email_receipts ADD CONSTRAINT fk_inbound_email_receipts_recipient_id FOREIGN KEY (recipient_id) REFERENCES ctm.communication_recipients(id) ON DELETE RESTRICT;

ALTER TABLE ctm.inbound_email_receipts ADD CONSTRAINT fk_inbound_email_receipts_communication_id FOREIGN KEY (communication_id) REFERENCES ctm.communications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.email_attachment_returns ADD CONSTRAINT fk_email_attachment_returns_receipt_id FOREIGN KEY (receipt_id) REFERENCES ctm.inbound_email_receipts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.email_attachment_returns ADD CONSTRAINT fk_email_attachment_returns_return_delivery_id FOREIGN KEY (return_delivery_id) REFERENCES ctm.channel_deliveries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.notifications ADD CONSTRAINT fk_notifications_recipient_account_id FOREIGN KEY (recipient_account_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.notifications ADD CONSTRAINT fk_notifications_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.channel_deliveries ADD CONSTRAINT fk_channel_deliveries_communication_recipient_id FOREIGN KEY (communication_recipient_id) REFERENCES ctm.communication_recipients(id) ON DELETE RESTRICT;

ALTER TABLE ctm.channel_deliveries ADD CONSTRAINT fk_channel_deliveries_notification_id FOREIGN KEY (notification_id) REFERENCES ctm.notifications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.delivery_events ADD CONSTRAINT fk_delivery_events_delivery_id FOREIGN KEY (delivery_id) REFERENCES ctm.channel_deliveries(id) ON DELETE RESTRICT;

ALTER TABLE ctm.notification_batches ADD CONSTRAINT fk_notification_batches_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.notification_batches ADD CONSTRAINT fk_notification_batches_source_person_id FOREIGN KEY (source_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.notification_batches ADD CONSTRAINT fk_notification_batches_delivered_to_id FOREIGN KEY (delivered_to_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.audit_events ADD CONSTRAINT fk_audit_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.audit_events ADD CONSTRAINT fk_audit_events_case_id FOREIGN KEY (case_id) REFERENCES ctm.cases(id) ON DELETE RESTRICT;

ALTER TABLE ctm.audit_events ADD CONSTRAINT fk_audit_events_subject_person_id FOREIGN KEY (subject_person_id) REFERENCES ctm.persons(id) ON DELETE RESTRICT;

ALTER TABLE ctm.background_jobs ADD CONSTRAINT fk_background_jobs_outbox_id FOREIGN KEY (outbox_id) REFERENCES ctm.outbox_events(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_retention_events ADD CONSTRAINT fk_draft_retention_events_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.draft_retention_events ADD CONSTRAINT fk_draft_retention_events_application_id FOREIGN KEY (application_id) REFERENCES ctm.applications(id) ON DELETE RESTRICT;

ALTER TABLE ctm.system_setting_versions ADD CONSTRAINT fk_system_setting_versions_edited_by_id FOREIGN KEY (edited_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.translation_prompt_versions ADD CONSTRAINT fk_translation_prompt_versions_edited_by_id FOREIGN KEY (edited_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.translation_jobs ADD CONSTRAINT fk_translation_jobs_prompt_version_id FOREIGN KEY (prompt_version_id) REFERENCES ctm.translation_prompt_versions(id) ON DELETE RESTRICT;

ALTER TABLE ctm.translation_jobs ADD CONSTRAINT fk_translation_jobs_provider_configuration_id FOREIGN KEY (provider_configuration_id) REFERENCES ctm.integration_configurations(id) ON DELETE RESTRICT;

ALTER TABLE ctm.translation_versions ADD CONSTRAINT fk_translation_versions_actor_id FOREIGN KEY (actor_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.translation_versions ADD CONSTRAINT fk_translation_versions_job_id FOREIGN KEY (job_id) REFERENCES ctm.translation_jobs(id) ON DELETE RESTRICT;

ALTER TABLE ctm.translation_versions ADD CONSTRAINT fk_translation_versions_reviewer_id FOREIGN KEY (reviewer_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

ALTER TABLE ctm.ui_resource_versions ADD CONSTRAINT fk_ui_resource_versions_published_by_id FOREIGN KEY (published_by_id) REFERENCES ctm.accounts(id) ON DELETE RESTRICT;

CREATE INDEX ix_persons_canonical_person_id ON ctm.persons(canonical_person_id);

CREATE INDEX ix_person_identity_versions_actor_id ON ctm.person_identity_versions(actor_id);

CREATE INDEX ix_person_identity_versions_person_id ON ctm.person_identity_versions(person_id);

CREATE INDEX ix_accounts_person_id ON ctm.accounts(person_id);

CREATE INDEX ix_account_identities_account_id ON ctm.account_identities(account_id);

CREATE INDEX ix_account_email_versions_account_id ON ctm.account_email_versions(account_id);

CREATE INDEX ix_verification_tokens_account_id ON ctm.verification_tokens(account_id);

CREATE INDEX ix_app_sessions_account_id ON ctm.app_sessions(account_id);

CREATE INDEX ix_app_sessions_provider_identity_id ON ctm.app_sessions(provider_identity_id);

CREATE INDEX ix_staff_memberships_account_id ON ctm.staff_memberships(account_id);

CREATE INDEX ix_staff_memberships_tribunal_id ON ctm.staff_memberships(tribunal_id);

CREATE INDEX ix_staff_memberships_appointed_by_id ON ctm.staff_memberships(appointed_by_id);

CREATE UNIQUE INDEX staff_current_account ON ctm.staff_memberships(account_id) WHERE active_until IS NULL;

CREATE INDEX ix_staff_roles_membership_id ON ctm.staff_roles(membership_id);

CREATE INDEX ix_staff_roles_granted_by_id ON ctm.staff_roles(granted_by_id);

CREATE UNIQUE INDEX role_current ON ctm.staff_roles(membership_id,role) WHERE revoked_at IS NULL;

CREATE INDEX ix_account_events_actor_id ON ctm.account_events(actor_id);

CREATE INDEX ix_account_events_account_id ON ctm.account_events(account_id);

CREATE INDEX ix_identity_consolidations_actor_id ON ctm.identity_consolidations(actor_id);

CREATE INDEX ix_identity_consolidations_source_person_id ON ctm.identity_consolidations(source_person_id);

CREATE INDEX ix_identity_consolidations_target_person_id ON ctm.identity_consolidations(target_person_id);

CREATE INDEX ix_identity_consolidations_primary_account_id ON ctm.identity_consolidations(primary_account_id);

CREATE INDEX ix_identity_consolidations_disabled_account_id ON ctm.identity_consolidations(disabled_account_id);

CREATE INDEX ix_identity_review_holds_actor_id ON ctm.identity_review_holds(actor_id);

CREATE INDEX ix_identity_review_holds_application_id ON ctm.identity_review_holds(application_id);

CREATE INDEX ix_identity_review_holds_resolved_by_id ON ctm.identity_review_holds(resolved_by_id);

CREATE INDEX ix_ctm_applicants_person_id ON ctm.ctm_applicants(person_id);

CREATE INDEX ix_ctm_applicants_tribunal_id ON ctm.ctm_applicants(tribunal_id);

CREATE INDEX ix_parishes_diocese_id ON ctm.parishes(diocese_id);

CREATE INDEX ix_cases_tribunal_id ON ctm.cases(tribunal_id);

CREATE INDEX ix_cases_marriage_id ON ctm.cases(marriage_id);

CREATE INDEX ix_case_identifiers_case_id ON ctm.case_identifiers(case_id);

CREATE UNIQUE INDEX allocated_case_number ON ctm.case_identifiers(reference) WHERE namespace='ctm';

CREATE UNIQUE INDEX primary_case_number ON ctm.case_identifiers(case_id) WHERE is_primary;

CREATE INDEX ix_case_parties_case_id ON ctm.case_parties(case_id);

CREATE INDEX ix_case_parties_person_id ON ctm.case_parties(person_id);

CREATE INDEX ix_case_parties_applicant_id ON ctm.case_parties(applicant_id);

CREATE UNIQUE INDEX case_known_person ON ctm.case_parties(case_id,person_id) WHERE person_id IS NOT NULL;

CREATE INDEX ix_applicant_references_party_id ON ctm.applicant_references(party_id);

CREATE INDEX ix_person_open_case_claims_person_id ON ctm.person_open_case_claims(person_id);

CREATE INDEX ix_person_open_case_claims_case_id ON ctm.person_open_case_claims(case_id);

CREATE INDEX ix_person_open_case_claims_party_id ON ctm.person_open_case_claims(party_id);

CREATE INDEX ix_person_active_draft_claims_person_id ON ctm.person_active_draft_claims(person_id);

CREATE INDEX ix_person_active_draft_claims_application_id ON ctm.person_active_draft_claims(application_id);

CREATE INDEX ix_case_proceedings_case_id ON ctm.case_proceedings(case_id);

CREATE UNIQUE INDEX one_open_proceeding ON ctm.case_proceedings(case_id) WHERE status='open';

CREATE UNIQUE INDEX appeal_decree_sequence_unique ON ctm.case_proceedings(case_id,appeal_decree_sequence) WHERE appeal_decree_sequence IS NOT NULL;

CREATE INDEX ix_case_lifecycle_events_actor_id ON ctm.case_lifecycle_events(actor_id);

CREATE INDEX ix_case_lifecycle_events_case_id ON ctm.case_lifecycle_events(case_id);

CREATE INDEX ix_case_lifecycle_events_proceeding_id ON ctm.case_lifecycle_events(proceeding_id);

CREATE INDEX ix_case_association_events_actor_id ON ctm.case_association_events(actor_id);

CREATE INDEX ix_case_association_events_case_id ON ctm.case_association_events(case_id);

CREATE INDEX ix_case_association_events_application_id ON ctm.case_association_events(application_id);

CREATE INDEX ix_case_party_onboarding_case_id ON ctm.case_party_onboarding(case_id);

CREATE INDEX ix_case_party_onboarding_party_id ON ctm.case_party_onboarding(party_id);

CREATE INDEX ix_case_party_onboarding_entered_by_id ON ctm.case_party_onboarding(entered_by_id);

CREATE INDEX ix_case_party_onboarding_activated_account_id ON ctm.case_party_onboarding(activated_account_id);

CREATE INDEX ix_registration_invitation_events_actor_id ON ctm.registration_invitation_events(actor_id);

CREATE INDEX ix_registration_invitation_events_onboarding_id ON ctm.registration_invitation_events(onboarding_id);

CREATE INDEX ix_registration_invitation_events_communication_id ON ctm.registration_invitation_events(communication_id);

CREATE INDEX ix_case_assignments_case_id ON ctm.case_assignments(case_id);

CREATE INDEX ix_case_assignments_member_id ON ctm.case_assignments(member_id);

CREATE INDEX ix_case_assignments_president_id ON ctm.case_assignments(president_id);

CREATE INDEX ix_case_assignments_recorded_by_id ON ctm.case_assignments(recorded_by_id);

CREATE INDEX ix_case_assignments_session_id ON ctm.case_assignments(session_id);

CREATE UNIQUE INDEX one_case_manager ON ctm.case_assignments(case_id) WHERE ends_at IS NULL;

CREATE INDEX ix_historical_entry_workspaces_created_by_id ON ctm.historical_entry_workspaces(created_by_id);

CREATE INDEX ix_historical_entry_workspaces_published_case_id ON ctm.historical_entry_workspaces(published_case_id);

CREATE INDEX ix_questionnaire_versions_questionnaire_id ON ctm.questionnaire_versions(questionnaire_id);

CREATE INDEX ix_questionnaire_versions_published_by_id ON ctm.questionnaire_versions(published_by_id);

CREATE INDEX ix_declaration_versions_published_by_id ON ctm.declaration_versions(published_by_id);

CREATE INDEX ix_applications_owner_person_id ON ctm.applications(owner_person_id);

CREATE INDEX ix_applications_owner_account_id ON ctm.applications(owner_account_id);

CREATE INDEX ix_applications_case_id ON ctm.applications(case_id);

CREATE INDEX ix_applications_party_id ON ctm.applications(party_id);

CREATE INDEX ix_applications_proceeding_id ON ctm.applications(proceeding_id);

CREATE INDEX ix_applications_questionnaire_version_id ON ctm.applications(questionnaire_version_id);

CREATE INDEX ix_application_revisions_actor_id ON ctm.application_revisions(actor_id);

CREATE INDEX ix_application_revisions_application_id ON ctm.application_revisions(application_id);

CREATE INDEX ix_application_revisions_predecessor_id ON ctm.application_revisions(predecessor_id);

CREATE INDEX ix_application_revisions_questionnaire_version_id ON ctm.application_revisions(questionnaire_version_id);

CREATE INDEX ix_application_person_assertions_revision_id ON ctm.application_person_assertions(revision_id);

CREATE INDEX ix_application_marriage_assertions_revision_id ON ctm.application_marriage_assertions(revision_id);

CREATE INDEX ix_application_separation_assertions_revision_id ON ctm.application_separation_assertions(revision_id);

CREATE INDEX ix_application_repeat_entries_application_id ON ctm.application_repeat_entries(application_id);

CREATE INDEX ix_application_children_revision_id ON ctm.application_children(revision_id);

CREATE INDEX ix_application_children_entry_id ON ctm.application_children(entry_id);

CREATE INDEX ix_application_restraining_orders_revision_id ON ctm.application_restraining_orders(revision_id);

CREATE INDEX ix_application_restraining_orders_entry_id ON ctm.application_restraining_orders(entry_id);

CREATE INDEX ix_application_prior_records_revision_id ON ctm.application_prior_records(revision_id);

CREATE INDEX ix_application_prior_records_entry_id ON ctm.application_prior_records(entry_id);

CREATE INDEX ix_application_answers_revision_id ON ctm.application_answers(revision_id);

CREATE INDEX ix_application_answers_entry_id ON ctm.application_answers(entry_id);

CREATE UNIQUE INDEX application_scalar_answer ON ctm.application_answers(revision_id,question_code) WHERE entry_id IS NULL;

CREATE UNIQUE INDEX application_collection_answer ON ctm.application_answers(revision_id,question_code,entry_id) WHERE entry_id IS NOT NULL;

CREATE INDEX ix_application_selected_grounds_revision_id ON ctm.application_selected_grounds(revision_id);

CREATE INDEX ix_application_selected_grounds_ground_id ON ctm.application_selected_grounds(ground_id);

CREATE INDEX ix_application_answer_changes_actor_id ON ctm.application_answer_changes(actor_id);

CREATE INDEX ix_application_answer_changes_application_id ON ctm.application_answer_changes(application_id);

CREATE INDEX ix_application_answer_changes_from_revision_id ON ctm.application_answer_changes(from_revision_id);

CREATE INDEX ix_application_answer_changes_to_revision_id ON ctm.application_answer_changes(to_revision_id);

CREATE INDEX ix_application_answer_changes_entry_id ON ctm.application_answer_changes(entry_id);

CREATE INDEX ix_filing_candidates_application_id ON ctm.filing_candidates(application_id);

CREATE INDEX ix_filing_candidates_revision_id ON ctm.filing_candidates(revision_id);

CREATE INDEX ix_application_submissions_application_id ON ctm.application_submissions(application_id);

CREATE INDEX ix_application_submissions_revision_id ON ctm.application_submissions(revision_id);

CREATE INDEX ix_application_submissions_candidate_id ON ctm.application_submissions(candidate_id);

CREATE INDEX ix_application_submissions_previous_submission_id ON ctm.application_submissions(previous_submission_id);

CREATE INDEX ix_application_submissions_declaration_version_id ON ctm.application_submissions(declaration_version_id);

CREATE INDEX ix_application_submissions_signature_file_version_id ON ctm.application_submissions(signature_file_version_id);

CREATE INDEX ix_application_submissions_submitted_by_id ON ctm.application_submissions(submitted_by_id);

CREATE INDEX ix_application_completeness_reviews_actor_id ON ctm.application_completeness_reviews(actor_id);

CREATE INDEX ix_application_completeness_reviews_submission_id ON ctm.application_completeness_reviews(submission_id);

CREATE INDEX ix_draft_schema_migrations_actor_id ON ctm.draft_schema_migrations(actor_id);

CREATE INDEX ix_draft_schema_migrations_application_id ON ctm.draft_schema_migrations(application_id);

CREATE INDEX ix_draft_schema_migrations_from_version_id ON ctm.draft_schema_migrations(from_version_id);

CREATE INDEX ix_draft_schema_migrations_to_version_id ON ctm.draft_schema_migrations(to_version_id);

CREATE INDEX ix_draft_schema_migrations_notice_id ON ctm.draft_schema_migrations(notice_id);

CREATE INDEX ix_party_withdrawals_actor_id ON ctm.party_withdrawals(actor_id);

CREATE INDEX ix_party_withdrawals_party_id ON ctm.party_withdrawals(party_id);

CREATE INDEX ix_party_withdrawals_application_id ON ctm.party_withdrawals(application_id);

CREATE INDEX ix_files_case_id ON ctm.files(case_id);

CREATE INDEX ix_files_proceeding_id ON ctm.files(proceeding_id);

CREATE INDEX ix_files_owner_application_id ON ctm.files(owner_application_id);

CREATE INDEX ix_files_owner_party_id ON ctm.files(owner_party_id);

CREATE INDEX ix_files_report_request_id ON ctm.files(report_request_id);

CREATE INDEX ix_files_category_id ON ctm.files(category_id);

CREATE INDEX ix_file_versions_file_id ON ctm.file_versions(file_id);

CREATE INDEX ix_file_versions_uploaded_by_id ON ctm.file_versions(uploaded_by_id);

CREATE INDEX ix_file_versions_external_link_id ON ctm.file_versions(external_link_id);

CREATE INDEX ix_file_name_events_actor_id ON ctm.file_name_events(actor_id);

CREATE INDEX ix_file_name_events_file_version_id ON ctm.file_name_events(file_version_id);

CREATE INDEX ix_file_context_links_file_version_id ON ctm.file_context_links(file_version_id);

CREATE INDEX ix_file_context_links_application_revision_id ON ctm.file_context_links(application_revision_id);

CREATE INDEX ix_file_context_links_repeat_entry_id ON ctm.file_context_links(repeat_entry_id);

CREATE INDEX ix_file_context_links_report_revision_id ON ctm.file_context_links(report_revision_id);

CREATE INDEX ix_file_context_links_medical_report_id ON ctm.file_context_links(medical_report_id);

CREATE INDEX ix_submission_file_manifest_submission_id ON ctm.submission_file_manifest(submission_id);

CREATE INDEX ix_submission_file_manifest_file_version_id ON ctm.submission_file_manifest(file_version_id);

CREATE INDEX ix_upload_sessions_file_id ON ctm.upload_sessions(file_id);

CREATE INDEX ix_upload_sessions_uploader_id ON ctm.upload_sessions(uploader_id);

CREATE INDEX ix_upload_sessions_external_link_id ON ctm.upload_sessions(external_link_id);

CREATE INDEX ix_upload_sessions_completed_version_id ON ctm.upload_sessions(completed_version_id);

CREATE INDEX ix_file_technical_events_actor_id ON ctm.file_technical_events(actor_id);

CREATE INDEX ix_file_technical_events_file_version_id ON ctm.file_technical_events(file_version_id);

CREATE INDEX ix_file_derivatives_source_version_id ON ctm.file_derivatives(source_version_id);

CREATE INDEX ix_file_access_events_actor_id ON ctm.file_access_events(actor_id);

CREATE INDEX ix_file_access_events_file_version_id ON ctm.file_access_events(file_version_id);

CREATE INDEX ix_search_documents_case_id ON ctm.search_documents(case_id);

CREATE INDEX ix_search_documents_party_id ON ctm.search_documents(party_id);

CREATE INDEX ix_fee_obligations_application_id ON ctm.fee_obligations(application_id);

CREATE INDEX ix_fee_waivers_actor_id ON ctm.fee_waivers(actor_id);

CREATE INDEX ix_fee_waivers_obligation_id ON ctm.fee_waivers(obligation_id);

CREATE INDEX ix_payment_attempts_obligation_id ON ctm.payment_attempts(obligation_id);

CREATE INDEX ix_payment_attempts_candidate_id ON ctm.payment_attempts(candidate_id);

CREATE INDEX ix_payment_events_attempt_id ON ctm.payment_events(attempt_id);

CREATE INDEX ix_payment_allocations_attempt_id ON ctm.payment_allocations(attempt_id);

CREATE INDEX ix_payment_allocations_obligation_id ON ctm.payment_allocations(obligation_id);

CREATE INDEX ix_payment_allocations_submission_id ON ctm.payment_allocations(submission_id);

CREATE INDEX ix_refund_events_actor_id ON ctm.refund_events(actor_id);

CREATE INDEX ix_refund_events_attempt_id ON ctm.refund_events(attempt_id);

CREATE INDEX ix_report_question_versions_question_id ON ctm.report_question_versions(question_id);

CREATE INDEX ix_report_question_versions_published_by_id ON ctm.report_question_versions(published_by_id);

CREATE INDEX ix_topic_category_memberships_topic_group_id ON ctm.topic_category_memberships(topic_group_id);

CREATE INDEX ix_topic_category_memberships_category_id ON ctm.topic_category_memberships(category_id);

CREATE INDEX ix_category_question_memberships_category_id ON ctm.category_question_memberships(category_id);

CREATE INDEX ix_category_question_memberships_question_id ON ctm.category_question_memberships(question_id);

CREATE INDEX ix_report_templates_owner_member_id ON ctm.report_templates(owner_member_id);

CREATE INDEX ix_report_template_versions_template_id ON ctm.report_template_versions(template_id);

CREATE INDEX ix_report_template_versions_published_by_id ON ctm.report_template_versions(published_by_id);

CREATE INDEX ix_template_publication_submissions_actor_id ON ctm.template_publication_submissions(actor_id);

CREATE INDEX ix_template_publication_submissions_personal_version_id ON ctm.template_publication_submissions(personal_version_id);

CREATE INDEX ix_template_publication_submissions_shared_version_id ON ctm.template_publication_submissions(shared_version_id);

CREATE INDEX ix_template_publication_submissions_reviewed_by_id ON ctm.template_publication_submissions(reviewed_by_id);

CREATE INDEX ix_report_requests_case_id ON ctm.report_requests(case_id);

CREATE INDEX ix_report_requests_proceeding_id ON ctm.report_requests(proceeding_id);

CREATE INDEX ix_report_requests_subject_party_id ON ctm.report_requests(subject_party_id);

CREATE INDEX ix_report_requests_parent_report_id ON ctm.report_requests(parent_report_id);

CREATE INDEX ix_report_requests_created_by_id ON ctm.report_requests(created_by_id);

CREATE INDEX ix_report_requests_template_version_id ON ctm.report_requests(template_version_id);

CREATE INDEX ix_sent_intake_question_snapshots_request_id ON ctm.sent_intake_question_snapshots(request_id);

CREATE INDEX ix_sent_intake_question_snapshots_source_question_version_id ON ctm.sent_intake_question_snapshots(source_question_version_id);

CREATE INDEX ix_external_report_links_request_id ON ctm.external_report_links(request_id);

CREATE INDEX ix_external_response_drafts_request_id ON ctm.external_response_drafts(request_id);

CREATE INDEX ix_reports_request_id ON ctm.reports(request_id);

CREATE INDEX ix_reports_case_id ON ctm.reports(case_id);

CREATE INDEX ix_reports_proceeding_id ON ctm.reports(proceeding_id);

CREATE INDEX ix_reports_subject_party_id ON ctm.reports(subject_party_id);

CREATE INDEX ix_reports_parent_report_id ON ctm.reports(parent_report_id);

CREATE INDEX ix_reports_author_account_id ON ctm.reports(author_account_id);

CREATE INDEX ix_reports_recorded_by_id ON ctm.reports(recorded_by_id);

CREATE INDEX ix_report_revisions_actor_id ON ctm.report_revisions(actor_id);

CREATE INDEX ix_report_revisions_report_id ON ctm.report_revisions(report_id);

CREATE INDEX ix_report_revisions_predecessor_id ON ctm.report_revisions(predecessor_id);

CREATE INDEX ix_report_answers_revision_id ON ctm.report_answers(revision_id);

CREATE INDEX ix_report_answers_question_snapshot_id ON ctm.report_answers(question_snapshot_id);

CREATE INDEX ix_report_source_links_report_revision_id ON ctm.report_source_links(report_revision_id);

CREATE INDEX ix_report_source_links_question_snapshot_id ON ctm.report_source_links(question_snapshot_id);

CREATE INDEX ix_report_source_links_source_application_revision_id ON ctm.report_source_links(source_application_revision_id);

CREATE INDEX ix_report_source_links_source_file_version_id ON ctm.report_source_links(source_file_version_id);

CREATE INDEX ix_recordings_report_id ON ctm.recordings(report_id);

CREATE INDEX ix_recordings_testimony_appointment_id ON ctm.recordings(testimony_appointment_id);

CREATE INDEX ix_recordings_file_version_id ON ctm.recordings(file_version_id);

CREATE INDEX ix_recordings_captured_by_id ON ctm.recordings(captured_by_id);

CREATE INDEX ix_processing_runs_recording_id ON ctm.processing_runs(recording_id);

CREATE INDEX ix_processing_runs_file_version_id ON ctm.processing_runs(file_version_id);

CREATE INDEX ix_transcript_versions_actor_id ON ctm.transcript_versions(actor_id);

CREATE INDEX ix_transcript_versions_recording_id ON ctm.transcript_versions(recording_id);

CREATE INDEX ix_transcript_versions_run_id ON ctm.transcript_versions(run_id);

CREATE INDEX ix_transcript_versions_predecessor_id ON ctm.transcript_versions(predecessor_id);

CREATE INDEX ix_transcript_versions_source_transcript_id ON ctm.transcript_versions(source_transcript_id);

CREATE INDEX ix_transcript_segments_text_version_id ON ctm.transcript_segments(text_version_id);

CREATE INDEX ix_transcript_segments_speaker_person_id ON ctm.transcript_segments(speaker_person_id);

CREATE INDEX ix_transcript_segments_source_segment_id ON ctm.transcript_segments(source_segment_id);

CREATE INDEX ix_text_review_events_actor_id ON ctm.text_review_events(actor_id);

CREATE INDEX ix_text_review_events_text_version_id ON ctm.text_review_events(text_version_id);

CREATE INDEX ix_text_review_events_reviewer_member_id ON ctm.text_review_events(reviewer_member_id);

CREATE INDEX ix_evaluation_requests_report_request_id ON ctm.evaluation_requests(report_request_id);

CREATE INDEX ix_evaluation_requests_subject_party_id ON ctm.evaluation_requests(subject_party_id);

CREATE INDEX ix_evaluation_release_attestations_evaluation_request_id ON ctm.evaluation_release_attestations(evaluation_request_id);

CREATE INDEX ix_evaluation_release_attestations_declaration_version_id ON ctm.evaluation_release_attestations(declaration_version_id);

CREATE INDEX ix_evaluation_release_attestations_subject_person_id ON ctm.evaluation_release_attestations(subject_person_id);

CREATE INDEX ix_evaluation_release_attestations_signer_person_id ON ctm.evaluation_release_attestations(signer_person_id);

CREATE INDEX ix_evaluation_release_attestations_signature_file_version_id ON ctm.evaluation_release_attestations(signature_file_version_id);

CREATE INDEX ix_evaluation_release_scopes_attestation_id ON ctm.evaluation_release_scopes(attestation_id);

CREATE INDEX ix_evaluation_reports_evaluation_request_id ON ctm.evaluation_reports(evaluation_request_id);

CREATE INDEX ix_evaluation_reports_report_id ON ctm.evaluation_reports(report_id);

CREATE INDEX ix_evaluation_reports_release_attestation_id ON ctm.evaluation_reports(release_attestation_id);

CREATE INDEX ix_evaluation_disclosures_actor_id ON ctm.evaluation_disclosures(actor_id);

CREATE INDEX ix_evaluation_disclosures_evaluation_report_id ON ctm.evaluation_disclosures(evaluation_report_id);

CREATE INDEX ix_evaluation_disclosures_release_scope_id ON ctm.evaluation_disclosures(release_scope_id);

CREATE INDEX ix_evaluation_disclosures_file_version_id ON ctm.evaluation_disclosures(file_version_id);

CREATE INDEX ix_case_findings_case_id ON ctm.case_findings(case_id);

CREATE INDEX ix_case_findings_proceeding_id ON ctm.case_findings(proceeding_id);

CREATE INDEX ix_finding_versions_actor_id ON ctm.finding_versions(actor_id);

CREATE INDEX ix_finding_versions_finding_id ON ctm.finding_versions(finding_id);

CREATE INDEX ix_case_notes_case_id ON ctm.case_notes(case_id);

CREATE INDEX ix_case_notes_proceeding_id ON ctm.case_notes(proceeding_id);

CREATE INDEX ix_case_notes_author_id ON ctm.case_notes(author_id);

CREATE INDEX ix_note_versions_actor_id ON ctm.note_versions(actor_id);

CREATE INDEX ix_note_versions_note_id ON ctm.note_versions(note_id);

CREATE INDEX ix_council_sessions_created_by_id ON ctm.council_sessions(created_by_id);

CREATE INDEX ix_agenda_requests_actor_id ON ctm.agenda_requests(actor_id);

CREATE INDEX ix_agenda_requests_case_id ON ctm.agenda_requests(case_id);

CREATE INDEX ix_agenda_requests_requested_session_id ON ctm.agenda_requests(requested_session_id);

CREATE INDEX ix_agenda_requests_placed_item_id ON ctm.agenda_requests(placed_item_id);

CREATE INDEX ix_session_agenda_items_session_id ON ctm.session_agenda_items(session_id);

CREATE INDEX ix_session_agenda_items_case_id ON ctm.session_agenda_items(case_id);

CREATE INDEX ix_session_agenda_items_carried_from_id ON ctm.session_agenda_items(carried_from_id);

CREATE INDEX ix_agenda_transfer_events_actor_id ON ctm.agenda_transfer_events(actor_id);

CREATE INDEX ix_agenda_transfer_events_case_id ON ctm.agenda_transfer_events(case_id);

CREATE INDEX ix_agenda_transfer_events_to_session_id ON ctm.agenda_transfer_events(to_session_id);

CREATE INDEX ix_agenda_transfer_events_destination_item_id ON ctm.agenda_transfer_events(destination_item_id);

CREATE INDEX ix_session_attendance_session_id ON ctm.session_attendance(session_id);

CREATE INDEX ix_session_attendance_member_id ON ctm.session_attendance(member_id);

CREATE INDEX ix_session_attendance_recorded_by_id ON ctm.session_attendance(recorded_by_id);

CREATE INDEX ix_case_hearings_agenda_item_id ON ctm.case_hearings(agenda_item_id);

CREATE INDEX ix_case_hearings_case_id ON ctm.case_hearings(case_id);

CREATE INDEX ix_case_hearings_proceeding_id ON ctm.case_hearings(proceeding_id);

CREATE INDEX ix_case_hearings_presenter_member_id ON ctm.case_hearings(presenter_member_id);

CREATE INDEX ix_hearing_attendance_hearing_id ON ctm.hearing_attendance(hearing_id);

CREATE INDEX ix_hearing_attendance_member_id ON ctm.hearing_attendance(member_id);

CREATE INDEX ix_hearing_attendance_recorded_by_id ON ctm.hearing_attendance(recorded_by_id);

CREATE INDEX ix_hearing_outcome_revisions_actor_id ON ctm.hearing_outcome_revisions(actor_id);

CREATE INDEX ix_hearing_outcome_revisions_hearing_id ON ctm.hearing_outcome_revisions(hearing_id);

CREATE INDEX ix_hearing_outcome_revisions_communication_id ON ctm.hearing_outcome_revisions(communication_id);

CREATE INDEX ix_testimony_appointments_case_id ON ctm.testimony_appointments(case_id);

CREATE INDEX ix_testimony_appointments_party_id ON ctm.testimony_appointments(party_id);

CREATE INDEX ix_testimony_appointments_agenda_item_id ON ctm.testimony_appointments(agenda_item_id);

CREATE INDEX ix_testimony_appointments_created_by_id ON ctm.testimony_appointments(created_by_id);

CREATE INDEX ix_testimony_appointment_versions_actor_id ON ctm.testimony_appointment_versions(actor_id);

CREATE INDEX ix_testimony_appointment_versions_appointment_id ON ctm.testimony_appointment_versions(appointment_id);

CREATE INDEX ix_testimony_invitation_responses_actor_id ON ctm.testimony_invitation_responses(actor_id);

CREATE INDEX ix_testimony_invitation_responses_appointment_version_id ON ctm.testimony_invitation_responses(appointment_version_id);

CREATE INDEX ix_testimony_invitation_responses_party_id ON ctm.testimony_invitation_responses(party_id);

CREATE INDEX ix_case_decision_versions_actor_id ON ctm.case_decision_versions(actor_id);

CREATE INDEX ix_case_decision_versions_case_id ON ctm.case_decision_versions(case_id);

CREATE INDEX ix_case_decision_versions_proceeding_id ON ctm.case_decision_versions(proceeding_id);

CREATE INDEX ix_case_decision_versions_hearing_id ON ctm.case_decision_versions(hearing_id);

CREATE INDEX ix_case_decision_versions_type_id ON ctm.case_decision_versions(type_id);

CREATE INDEX ix_council_votes_actor_id ON ctm.council_votes(actor_id);

CREATE INDEX ix_council_votes_decision_version_id ON ctm.council_votes(decision_version_id);

CREATE INDEX ix_council_votes_voting_member_id ON ctm.council_votes(voting_member_id);

CREATE INDEX ix_council_votes_supersedes_vote_id ON ctm.council_votes(supersedes_vote_id);

CREATE INDEX ix_presidential_approvals_actor_id ON ctm.presidential_approvals(actor_id);

CREATE INDEX ix_presidential_approvals_decision_version_id ON ctm.presidential_approvals(decision_version_id);

CREATE INDEX ix_presidential_approvals_president_member_id ON ctm.presidential_approvals(president_member_id);

CREATE INDEX ix_decree_template_versions_type_id ON ctm.decree_template_versions(type_id);

CREATE INDEX ix_decree_template_versions_published_by_id ON ctm.decree_template_versions(published_by_id);

CREATE INDEX ix_decrees_case_id ON ctm.decrees(case_id);

CREATE INDEX ix_decrees_proceeding_id ON ctm.decrees(proceeding_id);

CREATE INDEX ix_decrees_decision_version_id ON ctm.decrees(decision_version_id);

CREATE INDEX ix_decrees_template_version_id ON ctm.decrees(template_version_id);

CREATE INDEX ix_decrees_prepared_by_id ON ctm.decrees(prepared_by_id);

CREATE INDEX ix_decree_certificates_decree_id ON ctm.decree_certificates(decree_id);

CREATE INDEX ix_decree_certificates_signed_file_version_id ON ctm.decree_certificates(signed_file_version_id);

CREATE INDEX ix_decree_certificates_president_member_id ON ctm.decree_certificates(president_member_id);

CREATE INDEX ix_decree_certificates_prepared_by_id ON ctm.decree_certificates(prepared_by_id);

CREATE INDEX ix_decree_issuance_events_actor_id ON ctm.decree_issuance_events(actor_id);

CREATE INDEX ix_decree_issuance_events_decree_id ON ctm.decree_issuance_events(decree_id);

CREATE INDEX ix_decree_issuance_events_certificate_id ON ctm.decree_issuance_events(certificate_id);

CREATE INDEX ix_decree_issuance_events_approval_id ON ctm.decree_issuance_events(approval_id);

CREATE INDEX ix_decree_entitlements_decree_id ON ctm.decree_entitlements(decree_id);

CREATE INDEX ix_decree_entitlements_party_id ON ctm.decree_entitlements(party_id);

CREATE INDEX ix_decree_release_events_actor_id ON ctm.decree_release_events(actor_id);

CREATE INDEX ix_decree_release_events_entitlement_id ON ctm.decree_release_events(entitlement_id);

CREATE INDEX ix_decree_release_events_certificate_id ON ctm.decree_release_events(certificate_id);

CREATE INDEX ix_appeal_applications_application_id ON ctm.appeal_applications(application_id);

CREATE INDEX ix_appeal_applications_case_id ON ctm.appeal_applications(case_id);

CREATE INDEX ix_appeal_applications_party_id ON ctm.appeal_applications(party_id);

CREATE INDEX ix_appeal_applications_challenged_decision_id ON ctm.appeal_applications(challenged_decision_id);

CREATE INDEX ix_appeal_applications_challenged_decree_id ON ctm.appeal_applications(challenged_decree_id);

CREATE INDEX ix_pending_appeal_claims_case_id ON ctm.pending_appeal_claims(case_id);

CREATE INDEX ix_pending_appeal_claims_person_id ON ctm.pending_appeal_claims(person_id);

CREATE INDEX ix_pending_appeal_claims_appeal_id ON ctm.pending_appeal_claims(appeal_id);

CREATE INDEX ix_appeal_supplements_actor_id ON ctm.appeal_supplements(actor_id);

CREATE INDEX ix_appeal_supplements_appeal_id ON ctm.appeal_supplements(appeal_id);

CREATE INDEX ix_hearing_appeals_hearing_id ON ctm.hearing_appeals(hearing_id);

CREATE INDEX ix_hearing_appeals_appeal_id ON ctm.hearing_appeals(appeal_id);

CREATE INDEX ix_appeal_dispositions_actor_id ON ctm.appeal_dispositions(actor_id);

CREATE INDEX ix_appeal_dispositions_appeal_id ON ctm.appeal_dispositions(appeal_id);

CREATE INDEX ix_appeal_dispositions_hearing_id ON ctm.appeal_dispositions(hearing_id);

CREATE INDEX ix_appeal_dispositions_reopened_proceeding_id ON ctm.appeal_dispositions(reopened_proceeding_id);

CREATE INDEX ix_proceeding_appeals_proceeding_id ON ctm.proceeding_appeals(proceeding_id);

CREATE INDEX ix_proceeding_appeals_appeal_id ON ctm.proceeding_appeals(appeal_id);

CREATE INDEX ix_appeal_withdrawals_actor_id ON ctm.appeal_withdrawals(actor_id);

CREATE INDEX ix_appeal_withdrawals_appeal_id ON ctm.appeal_withdrawals(appeal_id);

CREATE INDEX ix_communications_case_id ON ctm.communications(case_id);

CREATE INDEX ix_communications_proceeding_id ON ctm.communications(proceeding_id);

CREATE INDEX ix_communications_sender_account_id ON ctm.communications(sender_account_id);

CREATE INDEX ix_communications_council_session_id ON ctm.communications(council_session_id);

CREATE INDEX ix_communication_recipients_communication_id ON ctm.communication_recipients(communication_id);

CREATE INDEX ix_communication_recipients_party_id ON ctm.communication_recipients(party_id);

CREATE INDEX ix_communication_recipients_account_id ON ctm.communication_recipients(account_id);

CREATE INDEX ix_communication_file_links_communication_id ON ctm.communication_file_links(communication_id);

CREATE INDEX ix_communication_file_links_file_version_id ON ctm.communication_file_links(file_version_id);

CREATE INDEX ix_call_details_communication_id ON ctm.call_details(communication_id);

CREATE INDEX ix_reply_routes_recipient_id ON ctm.reply_routes(recipient_id);

CREATE INDEX ix_inbound_email_receipts_recipient_id ON ctm.inbound_email_receipts(recipient_id);

CREATE INDEX ix_inbound_email_receipts_communication_id ON ctm.inbound_email_receipts(communication_id);

CREATE INDEX ix_email_attachment_returns_receipt_id ON ctm.email_attachment_returns(receipt_id);

CREATE INDEX ix_email_attachment_returns_return_delivery_id ON ctm.email_attachment_returns(return_delivery_id);

CREATE INDEX ix_notifications_recipient_account_id ON ctm.notifications(recipient_account_id);

CREATE INDEX ix_notifications_case_id ON ctm.notifications(case_id);

CREATE INDEX ix_channel_deliveries_communication_recipient_id ON ctm.channel_deliveries(communication_recipient_id);

CREATE INDEX ix_channel_deliveries_notification_id ON ctm.channel_deliveries(notification_id);

CREATE INDEX ix_delivery_events_delivery_id ON ctm.delivery_events(delivery_id);

CREATE INDEX ix_notification_batches_case_id ON ctm.notification_batches(case_id);

CREATE INDEX ix_notification_batches_source_person_id ON ctm.notification_batches(source_person_id);

CREATE INDEX ix_notification_batches_delivered_to_id ON ctm.notification_batches(delivered_to_id);

CREATE INDEX ix_audit_events_actor_id ON ctm.audit_events(actor_id);

CREATE INDEX ix_audit_events_case_id ON ctm.audit_events(case_id);

CREATE INDEX ix_audit_events_subject_person_id ON ctm.audit_events(subject_person_id);

CREATE INDEX ix_background_jobs_outbox_id ON ctm.background_jobs(outbox_id);

CREATE INDEX ix_draft_retention_events_actor_id ON ctm.draft_retention_events(actor_id);

CREATE INDEX ix_draft_retention_events_application_id ON ctm.draft_retention_events(application_id);

CREATE INDEX ix_system_setting_versions_edited_by_id ON ctm.system_setting_versions(edited_by_id);

CREATE INDEX ix_translation_prompt_versions_edited_by_id ON ctm.translation_prompt_versions(edited_by_id);

CREATE INDEX ix_translation_jobs_prompt_version_id ON ctm.translation_jobs(prompt_version_id);

CREATE INDEX ix_translation_jobs_provider_configuration_id ON ctm.translation_jobs(provider_configuration_id);

CREATE INDEX ix_translation_versions_actor_id ON ctm.translation_versions(actor_id);

CREATE INDEX ix_translation_versions_job_id ON ctm.translation_versions(job_id);

CREATE INDEX ix_translation_versions_reviewer_id ON ctm.translation_versions(reviewer_id);

CREATE INDEX ix_ui_resource_versions_published_by_id ON ctm.ui_resource_versions(published_by_id);

REVOKE ALL ON ALL TABLES IN SCHEMA ctm FROM PUBLIC;

COMMIT;

-- Intentionally no login roles, public grants, production secrets or policy-free API access.
