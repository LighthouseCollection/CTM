"""Generate a reviewable PostgreSQL structural contract; never connects to a DB."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLES = []


def table(name, domain, purpose, fields, constraints=(), indexes=(), retention='retained'):
    columns = [{'name': 'id', 'type': 'uuid', 'nullable': False, 'default': 'gen_random_uuid()', 'primary_key': True},
               {'name': 'created_at', 'type': 'timestamptz', 'nullable': False, 'default': 'now()'}]
    for item in fields.split(';'):
        item = item.strip()
        if not item:
            continue
        parts = item.split()
        col, typ = parts[:2]
        nullable = col.endswith('?')
        col = col.rstrip('?')
        ref = typ[1:] if typ.startswith('@') else None
        columns.append({'name': col, 'type': 'uuid' if ref else typ, 'nullable': nullable,
                        **({'references': ref} if ref else {}),
                        **({'default': ' '.join(parts[2:])} if len(parts) > 2 else {})})
    TABLES.append(dict(name=name, domain=domain, purpose=purpose, columns=columns,
                       constraints=list(constraints), indexes=list(indexes), retention=retention))


def event(name, domain, purpose, fields, **kwargs):
    table(name, domain, purpose, 'actor_id? @accounts; request_id? uuid;' + fields, **kwargs)


# All references are added after table creation, allowing explicit cyclic relationships.
table('persons','identity','Stable person identity; consolidation never rewrites original event actors',
      'canonical_person_id? @persons; identity_state text; row_version bigint 1')
event('person_identity_versions','identity','Attributed identity corrections; issued CTM references stay frozen',
      'person_id @persons; version integer; first_name_en? text; last_name_en? text; name_ar? text; birth_date? date; gender? text; facts jsonb; source text',
      constraints=['UNIQUE(person_id,version)',"CHECK(gender IS NULL OR gender IN ('M','F'))"])
table('accounts','identity','Provider-only account; no usable local password credential',
      "person_id? @persons; status text; ui_locale text 'en'; notification_locale text 'en'; row_version bigint 1",
      constraints=["CHECK(status IN ('pending','active','suspended','disabled'))","CHECK(ui_locale IN ('en','ar'))","CHECK(notification_locale IN ('en','ar'))"])
table('account_identities','identity','Bind validated issuer and subject, never email-only role inference',
      'account_id @accounts; provider text; issuer text; subject text; tenant_id? text; verified_email? text; linked_at timestamptz; revoked_at? timestamptz',
      constraints=['UNIQUE(issuer,subject)',"CHECK(provider IN ('microsoft','google','apple'))"])
table('account_email_versions','identity','Verified contact history; changing email does not rewrite filings',
      'account_id @accounts; email text; normalized_email text; verified_at? timestamptz; superseded_at? timestamptz')
table('verification_tokens','identity','Hashed one-use email/invitation token; not password recovery',
      'account_id? @accounts; purpose text; token_hash text; expires_at timestamptz; consumed_at? timestamptz; revoked_at? timestamptz',constraints=['UNIQUE(token_hash)'],retention='transient_secret_metadata')
table('app_sessions','identity','Server sessions; no application inactivity logout; revocation remains enforceable',
      'account_id @accounts; session_hash text; provider_identity_id @account_identities; authenticated_at timestamptz; revoked_at? timestamptz; provider_expires_at? timestamptz',constraints=['UNIQUE(session_hash)'],retention='security_policy')
table('tribunals','identity','One operating tribunal, not a new multi-tenant product',
      "code text; name_en text; name_ar? text; timezone text 'America/Los_Angeles'",constraints=['UNIQUE(code)',"CHECK(timezone='America/Los_Angeles')"])
table('staff_memberships','identity','Explicit admin-authorized council enrollment',
      'account_id @accounts; tribunal_id @tribunals; appointed_by_id @accounts; active_from timestamptz; active_until? timestamptz',indexes=['UNIQUE INDEX staff_current_account ON staff_memberships(account_id) WHERE active_until IS NULL'])
table('staff_roles','identity','Effective role grants; only existing admin creates council membership',
      'membership_id @staff_memberships; role text; granted_by_id @accounts; revoked_at? timestamptz',
      constraints=["CHECK(role IN ('admin','secretary','president','member'))"],indexes=['UNIQUE INDEX role_current ON staff_roles(membership_id,role) WHERE revoked_at IS NULL'])
event('account_events','identity','Status changes, role changes, identity linking and authentication events',
      'account_id? @accounts; event_type text; restricted_details jsonb')
event('identity_consolidations','identity','Verified primary account and canonical person; retained duplicate histories',
      'source_person_id @persons; target_person_id @persons; primary_account_id @accounts; disabled_account_id? @accounts; evidence jsonb',constraints=['CHECK(source_person_id<>target_person_id)'])
event('identity_review_holds','identity','Exact duplicate-person review blocks payment/submission, not draft saves',
      'application_id @applications; matching_rule text; protected_candidate_snapshot jsonb; status text; resolved_by_id? @accounts; resolved_at? timestamptz')
table('ctm_applicants','identity','CTM identity independent of account and case reference',
      'person_id @persons; tribunal_id @tribunals; internal_temporary_label? text',constraints=['UNIQUE(person_id,tribunal_id)'])
table('dioceses','identity','Optional directory; submitted text assertions remain original',
      'name_en text; name_ar? text; contact jsonb; active boolean true')
table('parishes','identity','Optional parish reference; no forced normalization of submitted spelling',
      'diocese_id? @dioceses; name_en text; name_ar? text; location jsonb; active boolean true')

table('marriages','cases','Matching registry separate from both parties attributed assertions',
      'marriage_date? date; spouse_birth_date_low? date; spouse_birth_date_high? date; matching_state text',
      constraints=['CHECK(spouse_birth_date_low IS NULL OR spouse_birth_date_high IS NULL OR spouse_birth_date_low<=spouse_birth_date_high)'])
table('cases','cases','Shared permanent case with original number and separate proceedings',
      'tribunal_id @tribunals; marriage_id? @marriages; origin text; status text; opened_at? timestamptz; closed_at? timestamptz; row_version bigint 1',
      constraints=["CHECK(origin IN ('new','historical'))","CHECK(status IN ('open','closed'))"])
table('case_identifiers','cases','Original, canonical and alias identifiers; never reused or renumbered',
      'case_id @cases; reference text; namespace text; is_primary boolean; allocation_date? date; daily_sequence? integer',
      constraints=["CHECK(daily_sequence IS NULL OR daily_sequence BETWEEN 1 AND 99)"],
      indexes=["UNIQUE INDEX allocated_case_number ON case_identifiers(reference) WHERE namespace='ctm'",'UNIQUE INDEX primary_case_number ON case_identifiers(case_id) WHERE is_primary'])
table('case_number_counters','cases','Atomic Los Angeles daily sequence allocation',
      'local_date date; last_value integer',constraints=['UNIQUE(local_date)','CHECK(last_value BETWEEN 0 AND 99)'])
table('case_parties','cases','Known spouse and participating applicant are different states',
      'case_id @cases; person_id? @persons; applicant_id? @ctm_applicants; party_slot text; participation_state text; source_name_snapshot jsonb',
      constraints=['UNIQUE(case_id,party_slot)',"CHECK(party_slot IN ('A','B'))"],indexes=['UNIQUE INDEX case_known_person ON case_parties(case_id,person_id) WHERE person_id IS NOT NULL'])
table('applicant_references','cases','Frozen case-based or historical applicant reference, never an access key',
      'party_id @case_parties; reference text; origin text; issued_components jsonb; issued_at timestamptz',constraints=['UNIQUE(party_id)'])
table('person_open_case_claims','cases','One open case per canonical participating person; includes historical cases',
      'person_id @persons; case_id @cases; party_id @case_parties',constraints=['UNIQUE(person_id)','UNIQUE(party_id)'])
table('person_active_draft_claims','cases','One new-case draft; mutually exclusive with different open case claim',
      'person_id @persons; application_id @applications',constraints=['UNIQUE(person_id)','UNIQUE(application_id)'])
table('case_proceedings','cases','Closed original proceedings never unlock; accepted appeal creates new section',
      'case_id @cases; kind text; status text; opened_at timestamptz; closed_at? timestamptz; appeal_decree_sequence? integer',
      constraints=["CHECK(kind IN ('initial','appeal'))","CHECK(status IN ('open','closed'))",'CHECK(appeal_decree_sequence IS NULL OR appeal_decree_sequence>0)'],
      indexes=["UNIQUE INDEX one_open_proceeding ON case_proceedings(case_id) WHERE status='open'",'UNIQUE INDEX appeal_decree_sequence_unique ON case_proceedings(case_id,appeal_decree_sequence) WHERE appeal_decree_sequence IS NOT NULL'])
event('case_lifecycle_events','cases','Opening, closure, reopening, retained association and historical correction history',
      'case_id @cases; proceeding_id? @case_proceedings; event_type text; source_reference jsonb')
event('case_association_events','cases','Preserved matching evidence, original case aliases and wrong-association corrections',
      'case_id @cases; application_id? @applications; matching_rule text; source_snapshot jsonb; result text')
table('case_party_onboarding','cases','Pending intended email; activate only on matching verified registration',
      'case_id @cases; party_id @case_parties; first_name text; last_name text; normalized_email text; entered_by_id @accounts; status text; activated_account_id? @accounts; activated_at? timestamptz')
event('registration_invitation_events','cases','Staff-initiated invitation email only; not an automatic enrollment side effect',
      'onboarding_id @case_party_onboarding; communication_id @communications')
table('case_assignments','cases','President-authorized single current case manager; separate entering actor',
      'case_id @cases; member_id @staff_memberships; president_id @staff_memberships; recorded_by_id @accounts; session_id? @council_sessions; authorized_at timestamptz; starts_at timestamptz; ends_at? timestamptz',
      indexes=['UNIQUE INDEX one_case_manager ON case_assignments(case_id) WHERE ends_at IS NULL'])
table('historical_entry_workspaces','cases','Private admin historical entry staging; no fee or fabricated required facts',
      'created_by_id @accounts; draft_payload jsonb; published_case_id? @cases; declared_status? text; finalized_at? timestamptz',retention='historical_workspace')

table('questionnaires','filings','Versioned applicant/appeal form identity','code text; purpose text',constraints=['UNIQUE(code)'])
table('questionnaire_versions','filings','Immutable published form; exact version retained on submission',
      'questionnaire_id @questionnaires; version integer; state text; definition jsonb; digest text; published_by_id? @accounts; published_at? timestamptz',constraints=['UNIQUE(questionnaire_id,version)'])
table('declaration_versions','filings','Exact bilingual declaration or medical-release wording',
      'purpose text; version integer; text_en text; text_ar text; digest text; published_by_id @accounts; published_at timestamptz',constraints=['UNIQUE(purpose,version)'])
table('applications','filings','Private draft, independent filing owner, same application on return/resubmission',
      'owner_person_id @persons; owner_account_id @accounts; case_id? @cases; party_id? @case_parties; proceeding_id? @case_proceedings; purpose text; status text; origin text; questionnaire_version_id @questionnaire_versions; last_applicant_activity_at timestamptz; first_submitted_at? timestamptz; row_version bigint 1',
      constraints=["CHECK(purpose IN ('petition','appeal'))","CHECK(status IN ('draft','submitted','returned','accepted','withdrawn','expired','deleted'))"],retention='draft_until_first_submission_then_permanent')
event('application_revisions','filings','Immutable committed snapshot; frozen revision at payment/submission',
      'application_id @applications; version integer; predecessor_id? @application_revisions; questionnaire_version_id @questionnaire_versions; digest text',constraints=['UNIQUE(application_id,version)'])
table('application_person_assertions','filings','Self/spouse facts, explicit missing-value states, no shared overwrite',
      'revision_id @application_revisions; subject text; first_name_en? text; middle_name_en? text; last_name_en? text; name_ar? text; birth_date? date; gender? text; nationality? text; birth_country? text; address jsonb; contacts jsonb; immigration_status? text; parish? text; father_of_confession? text; residence_country? text; religious_affiliation? text; denomination? text; additional_facts jsonb; answer_states jsonb',
      constraints=['UNIQUE(revision_id,subject)',"CHECK(subject IN ('self','spouse'))","CHECK(gender IS NULL OR gender IN ('M','F'))"])
table('application_marriage_assertions','filings','Exact source marriage/date/certificate assertion and prior religious affiliation',
      'revision_id @application_revisions; church_marriage_date? date; certificate_number? text; church_name? text; church_location? text; diocese? text; officiating_priest? text; outside_coptic_marriage? boolean; outside_denomination? text; additional_facts jsonb; answer_states jsonb',constraints=['UNIQUE(revision_id)'])
table('application_separation_assertions','filings','Attributed separation/civil-divorce/counseling assertions',
      'revision_id @application_revisions; separation_date? date; initiated_by? text; civil_divorce_date? date; court_name? text; court_case_number? text; facts jsonb; answer_states jsonb',constraints=['UNIQUE(revision_id)'])
table('application_repeat_entries','filings','Stable collection row identity across application revisions',
      'application_id @applications; collection_code text')
table('application_children','filings','Child name, DOB, gender and lives-with; Unknown allowed where approved',
      'revision_id @application_revisions; entry_id @application_repeat_entries; names jsonb; birth_date? date; gender? text; lives_with? text; answer_states jsonb',constraints=['UNIQUE(revision_id,entry_id)'])
table('application_restraining_orders','filings','Multiple reported orders; each requires court, case number, status and copy',
      'revision_id @application_revisions; entry_id @application_repeat_entries; court_name? text; court_case_number? text; current_status? text; order_date? date; expiry_date? date; named_person? text; answer_states jsonb',constraints=['UNIQUE(revision_id,entry_id)'])
table('application_prior_records','filings','Separate previous marriages, prior tribunal applications and priest-name entries',
      'revision_id @application_revisions; entry_id @application_repeat_entries; kind text; record_date? date; spouse_name? text; ecclesiastical_permit? text; council_or_diocese? text; outcome? text; priest_name? text; answer_states jsonb',constraints=['UNIQUE(revision_id,entry_id)',"CHECK(kind IN ('prior_marriage','prior_application','counseling_priest'))"])
table('application_answers','filings','Other versioned semantic fields; one editable binding per field',
      'revision_id @application_revisions; question_code text; entry_id? @application_repeat_entries; answer_type text; answer_state text; value jsonb',
      indexes=['UNIQUE INDEX application_scalar_answer ON application_answers(revision_id,question_code) WHERE entry_id IS NULL','UNIQUE INDEX application_collection_answer ON application_answers(revision_id,question_code,entry_id) WHERE entry_id IS NOT NULL'])
table('ground_definitions','filings','Six approved grounds with versioned bilingual labels',
      'code text; version integer; label_en text; label_ar text; retired_at? timestamptz',constraints=['UNIQUE(code,version)'])
table('application_selected_grounds','filings','Multiple grounds; never council findings',
      'revision_id @application_revisions; ground_id @ground_definitions',constraints=['UNIQUE(revision_id,ground_id)'])
event('application_answer_changes','filings','Field/repeat-entry change, actual actor/time; no reason or re-sign required',
      'application_id @applications; from_revision_id @application_revisions; to_revision_id @application_revisions; question_code text; entry_id? @application_repeat_entries; before_value jsonb; after_value jsonb')
table('filing_candidates','filings','Frozen checkout candidate for idempotent payment-to-submission recovery',
      'application_id @applications; revision_id @application_revisions; idempotency_key text; frozen_manifest jsonb; attestation_snapshot jsonb; state text',constraints=['UNIQUE(idempotency_key)'])
table('application_submissions','filings','Immutable original or resubmission; signed version is never replaced',
      'application_id @applications; revision_id @application_revisions; candidate_id? @filing_candidates; previous_submission_id? @application_submissions; declaration_version_id? @declaration_versions; signature_file_version_id? @file_versions; attestation jsonb; submitted_by_id @accounts; received_at timestamptz; digest text',constraints=['UNIQUE(candidate_id)'])
event('application_completeness_reviews','filings','Accept/Reject for completeness; Reject returns same filing with instructions',
      'submission_id @application_submissions; result text; correction_instructions? text',constraints=["CHECK(result IN ('accept','reject'))","CHECK(result<>'reject' OR nullif(btrim(correction_instructions),'') IS NOT NULL)"])
event('draft_schema_migrations','filings','Applicant drafts update to published form without losing answers; report draft rules differ',
      'application_id @applications; from_version_id @questionnaire_versions; to_version_id @questionnaire_versions; preserved_mapping jsonb; notice_id? @notifications')
event('party_withdrawals','filings','Own petition withdrawal; admin may act for all; no reason or approval',
      'party_id @case_parties; application_id @applications; on_behalf boolean')

table('document_categories','files','Stable document meaning, editable labels/code; historical names recorded',
      'code text; label_en text; label_ar text; row_version bigint 1; retired_at? timestamptz',constraints=['UNIQUE(code)'])
table('files','files','Logical owner and contextual location; no independent message attachment store',
      'case_id? @cases; proceeding_id? @case_proceedings; owner_application_id? @applications; owner_party_id? @case_parties; report_request_id? @report_requests; category_id @document_categories; visibility text; row_version bigint 1',
      constraints=["CHECK(visibility IN ('applicant_own','council_only','medical_scoped','decree_entitled'))"])
table('file_versions','files','Private immutable original; opaque key, latest safe default, version history council only',
      'file_id @files; version integer; object_key text; original_name text; presented_name text; size_bytes bigint; mime_type text; checksum_sha256 text; uploaded_by_id? @accounts; external_link_id? @external_report_links; uploaded_at timestamptz; technical_state text; wrong_upload_removed_at? timestamptz',
      constraints=['UNIQUE(file_id,version)','UNIQUE(object_key)','CHECK(size_bytes>=0)','CHECK(num_nonnulls(uploaded_by_id,external_link_id)=1)'])
event('file_name_events','files','Code rename changes presented filename, never source bytes or original manifest',
      'file_version_id @file_versions; previous_name text; new_name text; category_snapshot jsonb')
table('file_context_links','files','Correct question/order/request/evidence context, exact version and description',
      'file_version_id @file_versions; application_revision_id? @application_revisions; repeat_entry_id? @application_repeat_entries; report_revision_id? @report_revisions; medical_report_id? @evaluation_reports; question_code? text; purpose text; description? text')
table('submission_file_manifest','files','Exact filenames/checksums/versions retained with submitted filing',
      'submission_id @application_submissions; file_version_id @file_versions; metadata_snapshot jsonb',constraints=['UNIQUE(submission_id,file_version_id)'])
table('upload_sessions','files','Resumable upload with final authorization and technical validation',
      'file_id @files; uploader_id? @accounts; external_link_id? @external_report_links; expected_bytes? bigint; capture_kind text; status text; expires_at? timestamptz; completed_version_id? @file_versions',constraints=['CHECK(num_nonnulls(uploader_id,external_link_id)=1)'],retention='transient_until_retained')
event('file_technical_events','files','Safety/type/size scan separate from council acceptance',
      'file_version_id @file_versions; task text; engine_version text; result text; safe_metadata jsonb')
table('file_derivatives','files','Private OCR, extraction, preview or media derivative; original unchanged',
      'source_version_id @file_versions; kind text; object_key? text; extracted_text? text; engine_version text; languages jsonb; status text; checksum_sha256? text')
event('file_access_events','files','Audited view/download/playback with source permission recheck',
      'file_version_id @file_versions; action text; result text; correlation_id uuid')
table('search_documents','files','Rebuildable Meilisearch provenance, no independent authorization',
      'case_id @cases; party_id? @case_parties; source_kind text; source_id uuid; source_version_id uuid; security_scope text; locale text; index_generation text; indexed_at? timestamptz',constraints=['UNIQUE(source_kind,source_version_id,locale)'],retention='rebuildable')

table('fee_obligations','payments','One USD250 fee per filing; historical exemption/waiver distinct from payment',
      "application_id @applications; amount_minor bigint 25000; currency text 'USD'; disposition text; assessed_at timestamptz",
      constraints=['UNIQUE(application_id)','CHECK(amount_minor=25000)',"CHECK(currency='USD')","CHECK(disposition IN ('due','paid','waived','historical_exempt'))"])
event('fee_waivers','payments','Admin/secretary handles outside applicant application',
      'obligation_id @fee_obligations; reason? text')
table('payment_attempts','payments','Provider references only; no card data; browser redirect never proof',
      'obligation_id @fee_obligations; candidate_id @filing_candidates; provider text; provider_reference text; idempotency_key text; amount_minor bigint; currency text; status text',constraints=['UNIQUE(provider,provider_reference)','UNIQUE(idempotency_key)','CHECK(amount_minor>0)'])
table('payment_events','payments','Verified, deduplicated payment success/reversal/chargeback events',
      'attempt_id @payment_attempts; provider_event_id text; event_type text; verified_at timestamptz; safe_payload jsonb',constraints=['UNIQUE(provider_event_id)'])
table('payment_allocations','payments','A successful charge is allocated to exactly one filing obligation',
      'attempt_id @payment_attempts; obligation_id @fee_obligations; submission_id @application_submissions; amount_minor bigint',constraints=['UNIQUE(attempt_id)'])
event('refund_events','payments','Only accidental duplicate refunds; authorization and provider result distinct',
      'attempt_id @payment_attempts; provider_refund_id? text; status text; amount_minor bigint; reason text',constraints=['CHECK(amount_minor>0)'])

table('topic_groups','reports','Accepted Topic groups; views do not duplicate questions','code text; labels jsonb; position integer',constraints=['UNIQUE(code)'])
table('question_categories','reports','Reusable Question categories, not duplicate Question topic headings','code text; labels jsonb; position integer',constraints=['UNIQUE(code)'])
table('report_questions','reports','Stable accepted question IDs','code text; foundational boolean; retired_at? timestamptz',constraints=['UNIQUE(code)'])
table('report_question_versions','reports','Exact main wording, optional contextual prompts and translation versions',
      'question_id @report_questions; version integer; wording_en text; wording_ar? text; conditional_guidance jsonb; published_by_id? @accounts; published_at? timestamptz',constraints=['UNIQUE(question_id,version)'])
table('topic_category_memberships','reports','Reusable categories across Topic groups',
      'topic_group_id @topic_groups; category_id @question_categories; position integer',constraints=['UNIQUE(topic_group_id,category_id)'])
table('category_question_memberships','reports','Question/category mapping; selected question appears once unless explicit distinct event',
      'category_id @question_categories; question_id @report_questions; position integer',constraints=['UNIQUE(category_id,question_id)'])
table('report_templates','reports','Shared or personal template identity; personal has owner',
      'scope text; owner_member_id? @staff_memberships; title text; retired_at? timestamptz',constraints=["CHECK((scope='personal' AND owner_member_id IS NOT NULL) OR (scope='shared' AND owner_member_id IS NULL))"])
table('report_template_versions','reports','Immutable published selection/order; no answers or private case facts in reusable templates',
      'template_id @report_templates; version integer; definition jsonb; digest text; state text; published_by_id? @accounts',constraints=['UNIQUE(template_id,version)'])
event('template_publication_submissions','reports','Publish separate shared copy; retain personal original',
      'personal_version_id @report_template_versions; shared_version_id? @report_template_versions; status text; reviewed_by_id? @accounts')
table('report_requests','reports','Request first; assigned intake, freeform external priest or professional assessment',
      'case_id @cases; proceeding_id @case_proceedings; subject_party_id @case_parties; parent_report_id? @reports; kind text; created_by_id @accounts; title text; identifier_text? text; language text; status text; sent_at? timestamptz; closed_at? timestamptz; template_version_id? @report_template_versions; instructions jsonb; row_version bigint 1',
      constraints=["CHECK(kind IN ('applicant_intake','manager_interview','external_priest','medical','psychological'))","CHECK(language IN ('en','ar','both'))"])
table('sent_intake_question_snapshots','reports','Immutable exact sent questions, not all optional interviewer guidance',
      'request_id @report_requests; source_question_version_id? @report_question_versions; question_code text; position integer; text_en? text; text_ar? text; source_context_snapshot jsonb',constraints=['UNIQUE(request_id,position)'])
table('external_report_links','reports','External priest request only; direct link expires in30days; hash only',
      'request_id @report_requests; recipient_email? text; priest_name text; token_hash text; issued_at timestamptz; expires_at timestamptz; revoked_at? timestamptz; used_submission_at? timestamptz',constraints=['UNIQUE(token_hash)',"CHECK(expires_at=issued_at + interval '30 days')"])
table('external_response_drafts','reports','Limited request-scoped save/resume; no case browsing',
      'request_id @report_requests; response jsonb; saved_at timestamptz',constraints=['UNIQUE(request_id)'],retention='request_scoped')
table('reports','reports','Completed and working reports; follow-up is also an individual report',
      'request_id @report_requests; case_id @cases; proceeding_id @case_proceedings; subject_party_id @case_parties; parent_report_id? @reports; author_account_id? @accounts; external_author_name? text; recorded_by_id? @accounts; completion_date? date; identifier_text? text; title text; method text; status text; submitted_at? timestamptz; row_version bigint 1',constraints=['UNIQUE(request_id)'])
event('report_revisions','reports','Original author narrative edits while authorized/open; actual external/applicant response stays distinct',
      'report_id @reports; version integer; predecessor_id? @report_revisions; narrative jsonb; internal_observations? text; digest text',constraints=['UNIQUE(report_id,version)'])
table('report_answers','reports','Structured or rich text typed answers separate from generated transcript',
      'revision_id @report_revisions; question_snapshot_id @sent_intake_question_snapshots; answer_type text; value jsonb',constraints=['UNIQUE(revision_id,question_snapshot_id)'])
table('report_source_links','reports','Exact application/evidence version displayed or confirmed; never silently rewrite source',
      'report_revision_id @report_revisions; question_snapshot_id? @sent_intake_question_snapshots; source_application_revision_id? @application_revisions; source_file_version_id? @file_versions; question_code? text; context_snapshot jsonb; confirmation jsonb')
table('recordings','reports','Whole-report or council testimony audio; finalize before transcription',
      'report_id? @reports; testimony_appointment_id? @testimony_appointments; file_version_id @file_versions; captured_by_id? @accounts; recording_notice jsonb; finalized_at? timestamptz; duration_ms? bigint; origin text',constraints=['CHECK(num_nonnulls(report_id,testimony_appointment_id)=1)','CHECK(duration_ms IS NULL OR duration_ms>=0)'])
table('processing_runs','reports','Server-side task; local/API transcription per approved purpose; failure keeps source usable',
      'recording_id? @recordings; file_version_id? @file_versions; task text; provider text; model_version text; input_digest text; status text; safe_error? text; started_at? timestamptz; finished_at? timestamptz',constraints=['CHECK(num_nonnulls(recording_id,file_version_id)=1)'])
event('transcript_versions','reports','Original AI output plus all edits; source/mixed transcript and full English/Arabic',
      'recording_id @recordings; run_id? @processing_runs; kind text; language text; version integer; predecessor_id? @transcript_versions; source_transcript_id? @transcript_versions; origin text; text_content text',constraints=['UNIQUE(recording_id,kind,language,version)'])
table('transcript_segments','reports','Timestamped text with applicant/council speaker labels',
      'text_version_id @transcript_versions; ordinal integer; start_ms bigint; end_ms bigint; speaker_label text; speaker_person_id? @persons; content text; source_segment_id? @transcript_segments',constraints=['UNIQUE(text_version_id,ordinal)','CHECK(start_ms>=0 AND end_ms>=start_ms)'])
event('text_review_events','reports','Exact version review; report manager versus testimony admin/secretary',
      'text_version_id @transcript_versions; action text; reviewer_member_id @staff_memberships')

table('recommended_providers','medical','Optional recommended doctors; no external doctor account requirement',
      'display_name text; specialty text; contact jsonb; active boolean true')
table('evaluation_requests','medical','Separate professional assessment workflow over a report request',
      'report_request_id @report_requests; subject_party_id @case_parties; purpose text; provider_details jsonb; recommended_provider_snapshots jsonb',constraints=['UNIQUE(report_request_id)'])
table('evaluation_release_attestations','medical','Exact signed scoped release, not inferred from uploading report',
      'evaluation_request_id @evaluation_requests; declaration_version_id @declaration_versions; subject_person_id @persons; signer_person_id @persons; signature_file_version_id @file_versions; signed_at timestamptz; language text; exact_text text; purpose text; attestation jsonb',constraints=['CHECK(subject_person_id=signer_person_id)'])
table('evaluation_release_scopes','medical','Release scope applied to bytes/OCR/search/context and disclosures',
      'attestation_id @evaluation_release_attestations; recipient_scope jsonb; purpose text; file_scope jsonb')
table('evaluation_reports','medical','Report receipt, authorization and OCR readiness are separate states',
      'evaluation_request_id @evaluation_requests; report_id @reports; release_attestation_id? @evaluation_release_attestations; provider_details jsonb; completion_date date; authorization_state text',constraints=['UNIQUE(report_id)'])
event('evaluation_disclosures','medical','Accessor, release scope, exact original/derivative and timestamp',
      'evaluation_report_id @evaluation_reports; release_scope_id @evaluation_release_scopes; file_version_id? @file_versions; action text')

table('case_findings','review','Council finding never overwrites either applicant answer',
      'case_id @cases; proceeding_id @case_proceedings; fact_code text',constraints=['UNIQUE(proceeding_id,fact_code)'])
event('finding_versions','review','Assigned/admin/secretary revisions while proceeding open',
      'finding_id @case_findings; version integer; value jsonb; sources jsonb',constraints=['UNIQUE(finding_id,version)'])
table('case_notes','review','Council only; original author edits own note with current write eligibility',
      'case_id @cases; proceeding_id @case_proceedings; author_id @accounts')
event('note_versions','review','Preserve every edit; case closure locks notes',
      'note_id @case_notes; version integer; content text',constraints=['UNIQUE(note_id,version)'])

table('council_sessions','sessions','One dated session; rescheduling planned meeting moves cases and removes cancelled row',
      'session_date date; reference text; state text; created_by_id @accounts; closed_at? timestamptz',constraints=['UNIQUE(session_date)','UNIQUE(reference)'])
event('agenda_requests','sessions','Assigned member asks to place own case; no global agenda authority',
      'case_id @cases; requested_session_id? @council_sessions; placed_item_id? @session_agenda_items')
table('session_agenda_items','sessions','Two ordered parts; one case hearing item can include both pending appeals',
      'session_id @council_sessions; case_id @cases; part integer; position integer; status text; carried_from_id? @session_agenda_items',constraints=['CHECK(part IN (1,2))','UNIQUE(session_id,part,position)','UNIQUE(session_id,case_id)'])
event('agenda_transfer_events','sessions','Case audit preserves old/new date facts without retaining cancelled meeting',
      'case_id @cases; from_session_snapshot jsonb; to_session_id? @council_sessions; destination_item_id? @session_agenda_items; reason text')
table('session_attendance','sessions','Session default attendance; actual hearing attendance separate',
      'session_id @council_sessions; member_id @staff_memberships; present boolean; recorded_by_id @accounts',constraints=['UNIQUE(session_id,member_id)'])
table('case_hearings','sessions','Only assigned member presents; testimony is a limited separate segment',
      'agenda_item_id @session_agenda_items; case_id @cases; proceeding_id? @case_proceedings; presenter_member_id @staff_memberships; occurred_at timestamptz; result text',constraints=['UNIQUE(agenda_item_id)'])
table('hearing_attendance','sessions','Hearing-specific presence does not hide members from vote UI',
      'hearing_id @case_hearings; member_id @staff_memberships; present boolean; recorded_by_id @accounts',constraints=['UNIQUE(hearing_id,member_id)'])
event('hearing_outcome_revisions','sessions','Internal recommendations and applicant message remain distinct; later corrections no resend',
      'hearing_id @case_hearings; version integer; internal_text text; recommendations text; applicant_message_snapshot? text; communication_id? @communications',constraints=['UNIQUE(hearing_id,version)'])
table('testimony_appointments','sessions','Private applicant testimony invitation; never simultaneous both applicants',
      'case_id @cases; party_id @case_parties; agenda_item_id @session_agenda_items; status text; created_by_id @accounts')
event('testimony_appointment_versions','sessions','Rescheduling requests fresh Confirm/Reject while preserving former response',
      'appointment_id @testimony_appointments; version integer; starts_at timestamptz; ends_at? timestamptz; instructions text; attendance_location jsonb; cancelled boolean',constraints=['UNIQUE(appointment_id,version)','CHECK(ends_at IS NULL OR ends_at>starts_at)'])
event('testimony_invitation_responses','sessions','Applicant Confirm/Reject only; rejection explanation optional',
      'appointment_version_id @testimony_appointment_versions; party_id @case_parties; response text; explanation? text',constraints=["CHECK(response IN ('confirm','reject'))"])

table('decision_types','decisions','Prototype type catalog, not invented generic canonical outcomes',
      'code text; label_en text; label_ar? text; entitlement_rule jsonb; active boolean true',constraints=['UNIQUE(code)'])
event('case_decision_versions','decisions','Exact type/grounds/reason and party entitlement shown before voting',
      'case_id @cases; proceeding_id @case_proceedings; hearing_id? @case_hearings; version integer; type_id @decision_types; grounds_reason text; party_outcomes jsonb; conditions? text',constraints=['UNIQUE(proceeding_id,version)'])
event('council_votes','decisions','Self vote or admin/secretary on behalf; history per exact decision version',
      'decision_version_id @case_decision_versions; voting_member_id @staff_memberships; vote text; supersedes_vote_id? @council_votes',constraints=["CHECK(vote IN ('approve','deny','abstain'))"])
event('presidential_approvals','decisions','Actual approving president distinct from entering actor; votes optional',
      'decision_version_id @case_decision_versions; president_member_id @staff_memberships; approved_at timestamptz; revoked_at? timestamptz')
table('decree_template_versions','decisions','Bilingual type-specific template; issued certificate never changes retroactively',
      'type_id @decision_types; version integer; content_en text; content_ar text; layout_definition jsonb; published_by_id @accounts; digest text',constraints=['UNIQUE(type_id,version)'])
table('decrees','decisions','One decree per decree-producing proceeding, original or appeal suffix; no replacement workflow',
      'case_id @cases; proceeding_id @case_proceedings; decision_version_id @case_decision_versions; decree_reference text; template_version_id @decree_template_versions; language text; prepared_by_id @accounts',constraints=['UNIQUE(proceeding_id)','UNIQUE(decree_reference)',"CHECK(language IN ('en','ar','both'))"])
table('decree_certificates','decisions','Stored president-signed PDF; no clerical replacement orchestration',
      'decree_id @decrees; signed_file_version_id @file_versions; president_member_id @staff_memberships; signature_method text; signature_metadata jsonb; prepared_by_id @accounts',constraints=['UNIQUE(decree_id)'])
event('decree_issuance_events','decisions','Signed certificate plus current approval required; atomic case/proceeding closure',
      'decree_id @decrees; certificate_id @decree_certificates; approval_id @presidential_approvals; issued_at timestamptz',constraints=['UNIQUE(decree_id)'])
table('decree_entitlements','decisions','Recipient certificate entitlement separate from official notice and explicit release',
      'decree_id @decrees; party_id @case_parties; entitlement text',constraints=['UNIQUE(decree_id,party_id)',"CHECK(entitlement IN ('certificate','notice_only'))"])
event('decree_release_events','decisions','Explicit admin/secretary release or access withdrawal; original appeal access unchanged by default',
      'entitlement_id @decree_entitlements; certificate_id @decree_certificates; action text',constraints=["CHECK(action IN ('release','withdraw'))"])

table('appeal_applications','appeals','Separate each applicant filing, statement and new information; shared case',
      'application_id @applications; case_id @cases; party_id @case_parties; challenged_decision_id? @case_decision_versions; challenged_decree_id? @decrees; status text',constraints=['UNIQUE(application_id)'])
table('pending_appeal_claims','appeals','Only one draft/pending appeal per applicant/case; sibling remains independent',
      'case_id @cases; person_id @persons; appeal_id @appeal_applications',constraints=['UNIQUE(case_id,person_id)','UNIQUE(appeal_id)'])
event('appeal_supplements','appeals','Append-only applicant additions; never overwrite submitted appeal',
      'appeal_id @appeal_applications; text_content text; file_manifest jsonb')
table('hearing_appeals','appeals','Separate appeals considered in a single case hearing',
      'hearing_id @case_hearings; appeal_id @appeal_applications',constraints=['UNIQUE(hearing_id,appeal_id)'])
event('appeal_dispositions','appeals','Accept or Decline separately, with optional explanation and no new approval gate',
      'appeal_id @appeal_applications; hearing_id @case_hearings; result text; explanation? text; reopened_proceeding_id? @case_proceedings',constraints=['UNIQUE(appeal_id)',"CHECK(result IN ('accept','decline'))"])
table('proceeding_appeals','appeals','Sibling accepted appeals share one reopened proceeding',
      'proceeding_id @case_proceedings; appeal_id @appeal_applications',constraints=['UNIQUE(appeal_id)'])
event('appeal_withdrawals','appeals','Owner withdrawal before disposition; fee retained, original ruling unchanged',
      'appeal_id @appeal_applications',constraints=['UNIQUE(appeal_id)'])

table('communications','communications','Permanent in-app/email message or manual call record; applicant isolation',
      'case_id @cases; proceeding_id? @case_proceedings; sender_account_id? @accounts; direction text; channel text; subject? text; body text; sent_at? timestamptz; email_timing text; council_session_id? @council_sessions; template_snapshot jsonb',
      constraints=["CHECK(channel IN ('portal','email','call'))","CHECK(email_timing IN ('immediate','after_council_session','none'))"])
table('communication_recipients','communications','Private recipient copy; no cross-party thread or reply disclosure',
      'communication_id @communications; party_id? @case_parties; account_id? @accounts; external_email? text; recipient_snapshot jsonb; read_at? timestamptz')
table('communication_file_links','communications','Reference file in real case location; no separate message file storage',
      'communication_id @communications; file_version_id @file_versions',constraints=['UNIQUE(communication_id,file_version_id)'])
table('call_details','communications','Manual actual call date/time/person/outcome/notes; no dialer or recording',
      'communication_id @communications; contacted_person text; call_at timestamptz; outcome text; notes? text',constraints=['UNIQUE(communication_id)'])
table('reply_routes','communications','Hashed opaque inbound route; verified sender/recipient, not subject-only matching',
      'recipient_id @communication_recipients; token_hash text; revoked_at? timestamptz',constraints=['UNIQUE(token_hash)'])
table('inbound_email_receipts','communications','Deduplicated retained safe body/header; rejected attachments not evidence',
      'provider text; message_id text; sender_snapshot jsonb; safe_headers jsonb; body text; received_at timestamptz; routing_state text; recipient_id? @communication_recipients; communication_id? @communications',constraints=['UNIQUE(provider,message_id)'])
table('email_attachment_returns','communications','Return/notify attachment rejection; transient payload outside permanent document store',
      'receipt_id @inbound_email_receipts; metadata jsonb; temporary_payload_key? text; cleanup_due_at? timestamptz; return_delivery_id? @channel_deliveries; status text')
table('notifications','communications','Immediate private portal activity/read flag, distinct from email scheduling',
      'recipient_account_id @accounts; case_id? @cases; event_key text; purpose text; safe_payload jsonb; read_at? timestamptz',constraints=['UNIQUE(recipient_account_id,event_key,purpose)'])
table('channel_deliveries','communications','Per-recipient exact rendered payload and retry/delivery evidence',
      'communication_recipient_id? @communication_recipients; notification_id? @notifications; channel text; address_snapshot text; rendered_payload jsonb; due_at? timestamptz; state text; provider_id? text; idempotency_key text',constraints=['CHECK(num_nonnulls(communication_recipient_id,notification_id)=1)','UNIQUE(idempotency_key)'])
table('delivery_events','communications','Provider acceptance/delivery/bounce is not human reading',
      'delivery_id @channel_deliveries; provider_event_key text; result text; occurred_at timestamptz',constraints=['UNIQUE(provider_event_key)'])
table('notification_batches','communications','Applicant changes digest after10quiet minutes; resolve current manager at send',
      'case_id @cases; source_person_id @persons; due_at timestamptz; status text; event_keys jsonb; delivered_to_id? @accounts')

event('audit_events','operations','Append-only case/system audit, restricted projection; no raw secrets',
      'case_id? @cases; subject_person_id? @persons; operation text; source_table text; source_id uuid; classification text; safe_details jsonb')
table('outbox_events','operations','Atomic domain-event handoff; retries do not duplicate business actions',
      'event_key text; kind text; aggregate_id uuid; source_version_id? uuid; safe_payload jsonb; processed_at? timestamptz',constraints=['UNIQUE(event_key)'])
table('background_jobs','operations','Durable scans/OCR/transcription/search/email/cleanup retries and leases',
      'outbox_id? @outbox_events; kind text; source_reference jsonb; status text; due_at timestamptz; attempt integer 0; lease_until? timestamptz; safe_error? text',constraints=['CHECK(attempt>=0)'])
event('draft_retention_events','operations','180day inactivity,7day warning, deletion versus retained-submission barrier',
      'application_id? @applications; application_snapshot_id uuid; event_type text; deadline timestamptz; retained_metadata jsonb')
table('system_setting_versions','operations','Admin system configuration; not applicant settings or permissions bypass',
      'key text; version integer; safe_value jsonb; edited_by_id @accounts',constraints=['UNIQUE(key,version)'])
table('translation_prompt_versions','operations','Exact user master prompt preserved/versioned; all translation purposes',
      'version integer; content text; digest text; edited_by_id @accounts',constraints=['UNIQUE(version)'])
table('integration_configurations','operations','Server-only secret reference, ordered primary/fallback; no plaintext key in UI',
      'purpose text; priority integer; provider text; mode text; safe_configuration jsonb; secret_reference? text; enabled boolean false',constraints=['UNIQUE(purpose,priority)','CHECK(priority>0)'])
table('translation_jobs','operations','Source/version/prompt/provider provenance, restricted medical egress boundary',
      'source_kind text; source_id uuid; source_version text; source_locale text; target_locale text; prompt_version_id @translation_prompt_versions; provider_configuration_id? @integration_configurations; status text; content_class text')
event('translation_versions','operations','Original and reviewed translated text are separate retained versions',
      'job_id @translation_jobs; version integer; content text; state text; reviewer_id? @accounts',constraints=['UNIQUE(job_id,version)'])
table('ui_resource_versions','operations','Reviewed en/ar UI bundles, not live per-render AI translation',
      'resource_key text; version integer; text_en text; text_ar text; published_by_id @accounts; digest text',constraints=['UNIQUE(resource_key,version)'])
table('recovery_manifests','operations','Database/file/key backup integrity and restore evidence, not user export',
      'backup_reference text; file_manifest_digest text; database_backup_reference text; secret_backup_reference text; restore_verified_at? timestamptz; result jsonb')


def generate():
    by_name = {t['name']: t for t in TABLES}
    assert len(by_name) == len(TABLES)
    for t in TABLES:
        assert len({c['name'] for c in t['columns']}) == len(t['columns']), t['name']
        for c in t['columns']:
            if c.get('references'):
                assert c['references'] in by_name, (t['name'], c)
    schema = {'version':'ctm-build-contract-2026-10-21-v1','database':'PostgreSQL',
              'status':'structural_baseline_requires_guarded_Django_migrations', 'tables':TABLES}
    (ROOT/'schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sql = ['-- CTM structural baseline. NOT a complete production security migration.',
           '-- See transactions-and-acceptance.md and permissions.md. No public grants.',
           '-- Target: PostgreSQL 17+; pin and validate exact deployment release separately.',
           'BEGIN;', 'CREATE SCHEMA ctm;', 'REVOKE ALL ON SCHEMA ctm FROM PUBLIC;']
    fk = []
    indexes = []
    dictionary = ['# CTM field-level data dictionary','',
                  'Generated from `generate_schema.py`. JSONB is limited to versioned configuration, attributed structured evidence, variable answers, snapshots or safe event metadata. Core relations, ownership, payments and lifecycle references remain typed columns.',
                  '', 'Every table has an opaque UUID primary key and UTC server creation timestamp. All foreign keys default to RESTRICT; intentional eligible draft cleanup requires explicit child-first transactional deletion. No blanket cascade.', '']
    for t in TABLES:
        cols = []
        dictionary.extend([f"## {t['name']}", '', t['purpose'], '', f"Domain: {t['domain']}. Retention: {t['retention']}.", '', '| Column | PostgreSQL type | Required | Relationship / default |','|---|---|---|---|'])
        for c in t['columns']:
            part = f"  {c['name']} {c['type']}"
            if c.get('primary_key'): part += ' PRIMARY KEY'
            if not c['nullable']: part += ' NOT NULL'
            if c.get('default'): part += f" DEFAULT {c['default']}"
            cols.append(part)
            ref = c.get('references')
            if ref:
                cname = f"fk_{t['name']}_{c['name']}"
                if len(cname)>63: cname=cname[:50]+'_'+hashlib.sha256(cname.encode()).hexdigest()[:10]
                fk.append(f"ALTER TABLE ctm.{t['name']} ADD CONSTRAINT {cname} FOREIGN KEY ({c['name']}) REFERENCES ctm.{ref}(id) ON DELETE RESTRICT;")
                idx = f"ix_{t['name']}_{c['name']}"
                if len(idx)>63: idx=idx[:50]+'_'+hashlib.sha256(idx.encode()).hexdigest()[:10]
                indexes.append(f"CREATE INDEX {idx} ON ctm.{t['name']}({c['name']});")
            dictionary.append(f"| {c['name']} | {c['type']} | {'No' if c['nullable'] else 'Yes'} | {('→ '+ref) if ref else c.get('default','')} |")
        cols.extend('  '+x for x in t['constraints'])
        sql.append(f"CREATE TABLE ctm.{t['name']} (\n"+',\n'.join(cols)+'\n);')
        for idx in t['indexes']:
            indexes.append('CREATE '+idx.replace(' ON '+t['name']+'(', ' ON ctm.'+t['name']+'(')+';')
        dictionary.extend(['', 'Database constraints: '+('; '.join(t['constraints']) or 'Primary key and declared foreign keys.'), ''])
    sql += fk + indexes + ['REVOKE ALL ON ALL TABLES IN SCHEMA ctm FROM PUBLIC;', 'COMMIT;',
                            '-- Intentionally no login roles, public grants, production secrets or policy-free API access.']
    (ROOT/'schema.sql').write_text('\n\n'.join(sql)+'\n',encoding='utf-8')
    (ROOT/'data-dictionary.md').write_text('\n'.join(dictionary)+'\n',encoding='utf-8')
    files = sorted(ROOT.parent.glob('*.md')) + sorted(ROOT.parent.glob('*.txt'))
    files += sorted((ROOT.parent/'reference-study').glob('interview-*.json'))
    source = []
    for p in files:
        data=p.read_bytes()
        source.append({'path':p.relative_to(ROOT.parent).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    (ROOT/'source-register.json').write_text(json.dumps({'captured_at':'2026-10-21','sources':source},indent=2)+'\n',encoding='utf-8')
    import re
    import html
    prototype = ROOT.parents[2]/'ctm-admin'/'admin-case-decree.html'
    types = []
    for code, label in re.findall(r'name="decision" value="([^"]+)".*?TXT_decisionOptText">(.*?)</div>',prototype.read_text(encoding='utf-8')):
        types.append({'prototype_code':code,'prototype_label':html.unescape(re.sub('<[^>]+>','',label)),
                      'implementation_disposition': 'map_to_withdrawal_not_separate_outcome' if code=='reconciled' else 'hearing_pending_no_decree' if code=='deferred' else 'withdrawal_no_approval' if code=='withdrawn' else 'denial_no_certificate' if code=='denied' else 'decision_type_with_party_entitlement'})
    (ROOT/'prototype-decision-types.json').write_text(json.dumps({'source':'ctm-admin/admin-case-decree.html','types':types},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bank=json.loads((ROOT.parent/'reference-study'/'interview-current-question-bank.json').read_text(encoding='utf-8'))
    questions=[dict(q,category='Foundational questions') for q in bank['fixed']]
    for category in bank['categories']:
        questions += [dict(q,category=category['title']) for q in category['questions']]
    (ROOT/'accepted-question-seed.json').write_text(json.dumps({'source':'reference-study/interview-current-question-bank.json','questions':[{'code':q['id'],'category':q['category'],'wording_en':q['text'],'foundational':q['id'] in {x['id'] for x in bank['fixed']},'conditional_guidance':bank['contextPrompts'].get(q['id'],{})} for q in questions]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'tables':len(TABLES),'foreign_keys':len(fk),'indexes':len(indexes),'sources':len(source)}))


if __name__ == '__main__':
    generate()
