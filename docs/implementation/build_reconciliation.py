"""Evidence inventory, not an instruction to create tables or rewrite approved sources."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
schema = json.loads((root / "docs/architecture/build-spec/schema.json").read_text())
inventory = json.loads((root / "docs/implementation/model-inventory.json").read_text())
models = {row["model"].split(".")[-1]: row for row in inventory["models"]}

# Explicit candidate adapters. Multiple approved concepts can reside in one current
# model/JSON field; a candidate association is never equivalence or acceptance.
groups = {
    "Person": "persons person_identity_versions",
    "Account": "accounts account_email_versions account_events",
    "Tribunal": "tribunals", "StaffMembership": "staff_memberships", "StaffRole": "staff_roles",
    "Case": "cases case_identifiers marriages", "CaseNumberCounter": "case_number_counters",
    "Party": "case_parties applicant_references party_withdrawals",
    "OpenCaseClaim": "person_open_case_claims", "Proceeding": "case_proceedings case_lifecycle_events",
    "PendingPartyLink": "case_party_onboarding registration_invitation_events",
    "CaseAssignment": "case_assignments", "HistoricalWorkspace": "historical_entry_workspaces",
    "QuestionnaireVersion": "questionnaires questionnaire_versions declaration_versions",
    "Application": "applications appeal_applications pending_appeal_claims person_active_draft_claims",
    "AnswerRevision": "application_revisions application_answers application_person_assertions application_marriage_assertions application_separation_assertions application_repeat_entries application_children application_restraining_orders application_prior_records application_selected_grounds application_answer_changes",
    "CheckoutIntent": "filing_candidates payment_attempts",
    "Submission": "application_submissions submission_file_manifest",
    "CompletenessReview": "application_completeness_reviews",
    "Attachment": "files file_context_links", "FileVersion": "file_versions file_name_events",
    "FileTechnicalEvent": "file_technical_events", "DocumentText": "file_derivatives",
    "FeeObligation": "fee_obligations fee_waivers", "PaymentEvent": "payment_events refund_events payment_allocations",
    "ReportQuestion": "report_questions report_question_versions",
    "ReportTemplate": "report_templates template_publication_submissions", "TemplateVersion": "report_template_versions",
    "ReportRequest": "report_requests sent_intake_question_snapshots external_report_links external_response_drafts evaluation_requests",
    "Report": "reports report_source_links evaluation_reports", "ReportRevision": "report_revisions report_answers",
    "Recording": "recordings", "ProcessingRun": "processing_runs", "TranscriptRevision": "transcript_versions transcript_segments",
    "TranscriptReview": "text_review_events", "MedicalRelease": "evaluation_release_attestations evaluation_release_scopes evaluation_disclosures",
    "CaseNote": "case_notes", "NoteRevision": "note_versions", "FindingRevision": "case_findings finding_versions",
    "CouncilSession": "council_sessions", "AgendaItem": "agenda_requests session_agenda_items",
    "AgendaTransferEvent": "agenda_transfer_events", "Attendance": "session_attendance hearing_attendance",
    "Hearing": "case_hearings hearing_appeals", "HearingOutcome": "hearing_outcome_revisions",
    "TestimonyAppointment": "testimony_appointments", "TestimonyAppointmentVersion": "testimony_appointment_versions",
    "AppointmentResponse": "testimony_invitation_responses", "DecisionRevision": "case_decision_versions",
    "Vote": "council_votes", "PresidentialApproval": "presidential_approvals",
    "SignatureAttestation": "decree_certificates", "Decree": "decrees decree_issuance_events decree_entitlements",
    "DecreeRelease": "decree_release_events", "AppealSupplement": "appeal_supplements",
    "AppealDisposition": "appeal_dispositions proceeding_appeals appeal_withdrawals",
    "Message": "communications communication_file_links", "MessageRecipient": "communication_recipients",
    "CallRecord": "call_details", "Notification": "notifications",
    "Outbox": "outbox_events background_jobs channel_deliveries delivery_events notification_batches",
    "AuditEvent": "audit_events draft_retention_events", "SettingRevision": "system_setting_versions translation_prompt_versions integration_configurations",
}
assert set(groups) == set(models), (set(models)-set(groups), set(groups)-set(models))
approved = {row["name"] for row in schema["tables"]}
assert all(name in approved for names in groups.values() for name in names.split())
rows = []
for table in schema["tables"]:
    candidates = [name for name, targets in groups.items() if table["name"] in targets.split()]
    direct = set().union(*(set(field["column"] for field in models[name]["fields"]) for name in candidates)) if candidates else set()
    rows.append({"approved_table": table["name"], "domain": table["domain"], "purpose": table["purpose"],
        "candidate_adapters": candidates,
        "status": "candidate_adapter_requires_review" if candidates else "unmapped_requires_review",
        "columns_without_same_named_adapter_column": [c["name"] for c in table["columns"] if c["name"] not in direct],
        "limitation": "Name/column association is not field-semantic, ownership, lifecycle or acceptance equivalence; JSON/relationship mapping needs explicit review."})
result = {"status": "review inventory; no automatic missing-table or completion claim",
    "approved_table_count": len(rows), "current_model_count": len(models),
    "candidate_mapped_count": sum(bool(row["candidate_adapters"]) for row in rows),
    "unmapped_count": sum(not row["candidate_adapters"] for row in rows), "tables": rows}
(root / "docs/implementation/schema-reconciliation.json").write_text(json.dumps(result, indent=2)+"\n")
print({key: value for key, value in result.items() if key != "tables"})
