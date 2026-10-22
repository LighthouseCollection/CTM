"""Typed domain roots and immutable source revisions. Mutations go through services."""

import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Root(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True


class Immutable(Root):
    """ORM guard, backed by PostgreSQL immutable-row triggers in migrations."""

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Historical records cannot be overwritten.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Historical records cannot be deleted.")

    class Meta:
        abstract = True


class Person(Root):
    canonical = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1, choices=[("M", "M"), ("F", "F")], blank=True
    )


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if password is not None:
            raise ValidationError("CTM uses identity-provider authentication only.")
        if not email:
            raise ValidationError("Email is required.")
        if "person" not in extra:
            extra["person"] = Person.objects.create(
                first_name=extra.get("first_name", ""),
                last_name=extra.get("last_name", ""),
            )
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(role="admin", is_superuser=True, email_verified=True)
        return self.create_user(email, password, **extra)


class Account(AbstractBaseUser, PermissionsMixin, Root):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    person = models.OneToOneField(Person, null=True, on_delete=models.PROTECT)
    role = models.CharField(
        max_length=12,
        default="applicant",
        choices=[
            (x, x) for x in ["applicant", "member", "president", "secretary", "admin"]
        ],
    )
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    ui_language = models.CharField(
        max_length=2, default="en", choices=[("en", "English"), ("ar", "العربية")]
    )
    notification_language = models.CharField(max_length=2, default="en")
    microsoft_subject = models.CharField(max_length=200, blank=True)
    objects = AccountManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["microsoft_subject"],
                condition=~Q(microsoft_subject=""),
                name="council_microsoft_subject_unique",
            )
        ]

    @property
    def is_staff(self):
        return self.is_active and self.role != "applicant"

    def set_password(self, raw_password):
        if raw_password is not None:
            raise ValidationError("Local passwords are disabled.")
        self.set_unusable_password()


class Case(Root):
    number = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=12, default="open", choices=[("open", "Open"), ("closed", "Closed")]
    )
    origin = models.CharField(max_length=12, default="new")
    marriage_date = models.DateField(null=True)
    spouse_dob_low = models.DateField(null=True)
    spouse_dob_high = models.DateField(null=True)
    assigned_member = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assigned_cases",
    )
    closed_at = models.DateTimeField(null=True)


class CaseNumberCounter(models.Model):
    date = models.DateField(primary_key=True)
    last_value = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(last_value__lte=99), name="daily_case_cap"
            )
        ]


class Party(Root):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="parties")
    person = models.ForeignKey(Person, null=True, on_delete=models.PROTECT)
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.PROTECT
    )
    slot = models.CharField(max_length=1)
    name = models.CharField(max_length=300, blank=True)
    reference = models.CharField(max_length=150, blank=True)
    participating = models.BooleanField(default=False)
    withdrawn_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["case", "slot"], name="case_party_slot"),
            models.UniqueConstraint(
                fields=["case", "person"],
                condition=Q(person__isnull=False),
                name="case_person_once",
            ),
        ]


class OpenCaseClaim(models.Model):
    person = models.OneToOneField(Person, primary_key=True, on_delete=models.PROTECT)
    case = models.ForeignKey(Case, on_delete=models.PROTECT)


class Proceeding(Root):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="proceedings")
    kind = models.CharField(max_length=10, default="initial")
    status = models.CharField(max_length=10, default="open")
    sequence = models.PositiveIntegerField(default=0)
    closed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case"], condition=Q(status="open"), name="one_open_proceeding"
            ),
            models.UniqueConstraint(
                fields=["case", "sequence"], name="case_proceeding_sequence"
            ),
        ]


class QuestionnaireVersion(Immutable):
    purpose = models.CharField(max_length=20)
    number = models.PositiveIntegerField()
    definition = models.JSONField(default=dict)
    declaration_en = models.TextField(blank=True)
    declaration_ar = models.TextField(blank=True)
    published = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purpose", "number"], name="questionnaire_version"
            )
        ]


class Application(Root):
    owner = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="applications"
    )
    case = models.ForeignKey(
        Case, null=True, on_delete=models.PROTECT, related_name="applications"
    )
    proceeding = models.ForeignKey(Proceeding, null=True, on_delete=models.PROTECT)
    party = models.ForeignKey(Party, null=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=10, default="petition")
    status = models.CharField(max_length=15, default="draft")
    current_version = models.PositiveIntegerField(default=0)
    questionnaire = models.ForeignKey(
        QuestionnaireVersion, null=True, on_delete=models.PROTECT
    )
    last_activity = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True)
    duplicate_hold = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(kind="petition", status="draft"),
                name="one_petition_draft",
            ),
            models.UniqueConstraint(
                fields=["owner", "case"],
                condition=Q(kind="appeal", status__in=["draft", "submitted"]),
                name="one_pending_appeal",
            ),
        ]


class AnswerRevision(Immutable):
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="revisions"
    )
    number = models.PositiveIntegerField()
    answers = models.JSONField(default=dict)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    questionnaire = models.ForeignKey(
        QuestionnaireVersion, null=True, on_delete=models.PROTECT
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "number"], name="answer_revision_number"
            )
        ]


class Submission(Immutable):
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="submissions"
    )
    revision = models.ForeignKey(AnswerRevision, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=200, unique=True)
    manifest = models.JSONField(default=list)
    attestation = models.JSONField(default=dict)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)


class FeeObligation(Root):
    application = models.OneToOneField(
        Application, on_delete=models.PROTECT, related_name="fee"
    )
    amount_minor = models.PositiveIntegerField(default=25000)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=15, default="due")
    waived_by = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_minor=25000, currency="USD"),
                name="filing_fee_usd250",
            )
        ]


class PaymentEvent(Immutable):
    provider_event_id = models.CharField(max_length=250, unique=True)
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    kind = models.CharField(max_length=50)
    amount_minor = models.IntegerField()
    currency = models.CharField(max_length=3)
    provider_reference = models.CharField(max_length=250)
    payment_reference = models.CharField(max_length=250, blank=True, default="", db_index=True)


class CheckoutIntent(Root):
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    revision = models.ForeignKey(AnswerRevision, on_delete=models.PROTECT)
    attestation = models.JSONField(default=dict)
    manifest = models.JSONField(default=list)
    provider_reference = models.CharField(max_length=250, unique=True, null=True)
    payment_reference = models.CharField(max_length=250, blank=True, default="", db_index=True)
    state = models.CharField(max_length=25, default="pending")
    failure = models.CharField(max_length=250, blank=True)


class CompletenessReview(Immutable):
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    result = models.CharField(max_length=10)
    instructions = models.TextField(blank=True)


class CaseAssignment(Immutable):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    member = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="assignment_history"
    )
    president = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="authorized_assignments"
    )
    actor = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="recorded_assignments"
    )


class Attachment(Root):
    application = models.ForeignKey(
        Application, null=True, on_delete=models.PROTECT, related_name="attachments"
    )
    case = models.ForeignKey(Case, null=True, on_delete=models.PROTECT)
    proceeding = models.ForeignKey(Proceeding, null=True, on_delete=models.PROTECT)
    owner = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    category = models.CharField(max_length=30)
    context = models.CharField(max_length=150, blank=True)
    visibility = models.CharField(max_length=20, default="own")
    report_request = models.ForeignKey(
        "ReportRequest", null=True, on_delete=models.PROTECT, related_name="attachments"
    )


class FileVersion(Immutable):
    attachment = models.ForeignKey(
        Attachment, on_delete=models.PROTECT, related_name="versions"
    )
    number = models.PositiveIntegerField()
    object_key = models.CharField(max_length=250, unique=True)
    original_name = models.CharField(max_length=250)
    display_name = models.CharField(max_length=250)
    mime_type = models.CharField(max_length=100)
    byte_count = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    actor = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    external_request = models.ForeignKey(
        "ReportRequest", null=True, on_delete=models.PROTECT
    )
    scan_state = models.CharField(max_length=15, default="pending")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attachment", "number"], name="attachment_version"
            )
        ]


class FileTechnicalEvent(Immutable):
    file = models.ForeignKey(
        FileVersion, on_delete=models.PROTECT, related_name="technical_events"
    )
    task = models.CharField(max_length=30)
    result = models.CharField(max_length=20)
    metadata = models.JSONField(default=dict)


class DocumentText(Immutable):
    file = models.ForeignKey(FileVersion, on_delete=models.PROTECT)
    language = models.CharField(max_length=10, default="en-ar")
    engine = models.CharField(max_length=100)
    text = models.TextField()


class PendingPartyLink(Root):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    state = models.CharField(max_length=15, default="pending")
    activated_party = models.ForeignKey("Party", null=True, on_delete=models.PROTECT)


class HistoricalWorkspace(Root):
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    payload = models.JSONField(default=dict)
    finalized_case = models.ForeignKey(Case, null=True, on_delete=models.PROTECT)


class CallRecord(Immutable):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    party = models.ForeignKey(Party, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    occurred_at = models.DateTimeField()
    outcome = models.CharField(max_length=150)
    notes = models.TextField(blank=True)


class SignatureAttestation(Immutable):
    file = models.OneToOneField("FileVersion", on_delete=models.PROTECT)
    signer = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="signed_certificates"
    )
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    method = models.CharField(max_length=20)
    signed_at = models.DateTimeField()
    evidence = models.JSONField(default=dict)


class AuditEvent(Immutable):
    case = models.ForeignKey(Case, null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    source = models.CharField(max_length=100)
    source_id = models.UUIDField(null=True)
    metadata = models.JSONField(default=dict)


class Outbox(Root):
    key = models.CharField(max_length=250, unique=True)
    kind = models.CharField(max_length=50)
    case = models.ForeignKey(Case, null=True, on_delete=models.PROTECT)
    recipient = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    payload = models.JSONField(default=dict)
    due_at = models.DateTimeField(default=timezone.now)
    delivered_at = models.DateTimeField(null=True)
    discarded_at = models.DateTimeField(null=True)
    lease_until = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=250, blank=True)


class Notification(Root):
    recipient = models.ForeignKey(Account, on_delete=models.PROTECT)
    case = models.ForeignKey(Case, null=True, on_delete=models.PROTECT)
    key = models.CharField(max_length=250)
    kind = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)
    read_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "key"], name="recipient_notification"
            )
        ]


class CouncilSession(Root):
    date = models.DateField(unique=True)
    state = models.CharField(max_length=12, default="planned")
    closed_at = models.DateTimeField(null=True)

    @property
    def reference(self):
        return self.date.strftime("CS%Y%m%d")


class AgendaItem(Root):
    session = models.ForeignKey(
        CouncilSession, on_delete=models.PROTECT, related_name="agenda"
    )
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    part = models.PositiveSmallIntegerField(default=2)
    position = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=20, default="scheduled")
    carried_from = models.ForeignKey("self", null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "case"], name="session_case_once"
            )
        ]


class Attendance(Immutable):
    session = models.ForeignKey(CouncilSession, on_delete=models.PROTECT)
    hearing = models.ForeignKey("Hearing", null=True, on_delete=models.PROTECT)
    member = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="attendance"
    )
    present = models.BooleanField()
    actor = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="recorded_attendance"
    )


class Hearing(Root):
    agenda = models.OneToOneField(AgendaItem, on_delete=models.PROTECT)
    proceeding = models.ForeignKey(Proceeding, null=True, on_delete=models.PROTECT)
    presenter = models.ForeignKey(Account, on_delete=models.PROTECT)
    state = models.CharField(max_length=15, default="held")


class HearingOutcome(Immutable):
    hearing = models.ForeignKey(Hearing, on_delete=models.PROTECT)
    internal_text = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)


class ReportQuestion(Immutable):
    code = models.CharField(max_length=30)
    version = models.PositiveIntegerField(default=1)
    category = models.CharField(max_length=150)
    wording_en = models.TextField()
    wording_ar = models.TextField(blank=True)
    foundational = models.BooleanField(default=False)
    guidance = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code", "version"], name="question_code_version"
            )
        ]


class ReportTemplate(Root):
    owner = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    shared = models.BooleanField(default=False)
    retired = models.BooleanField(default=False)


class TemplateVersion(Immutable):
    template = models.ForeignKey(ReportTemplate, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    questions = models.JSONField(default=list)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "number"], name="template_version"
            )
        ]


class ReportRequest(Root):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    proceeding = models.ForeignKey(Proceeding, on_delete=models.PROTECT)
    subject = models.ForeignKey(Party, on_delete=models.PROTECT)
    author = models.ForeignKey(Account, on_delete=models.PROTECT)
    kind = models.CharField(max_length=25, default="intake")
    language = models.CharField(max_length=4, default="en")
    title = models.CharField(max_length=200)
    questions = models.JSONField(default=list)
    instructions = models.TextField(blank=True)
    parent_report = models.ForeignKey("Report", null=True, on_delete=models.PROTECT)
    state = models.CharField(max_length=15, default="draft")
    token_hash = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    external_name = models.CharField(max_length=200, blank=True)
    external_email = models.EmailField(blank=True)
    saved_response = models.JSONField(default=dict)


class Report(Root):
    request = models.OneToOneField(ReportRequest, on_delete=models.PROTECT)
    author = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    completion_date = models.DateField(default=timezone.localdate)
    identifier = models.CharField(max_length=150, blank=True)
    method = models.CharField(max_length=20, default="written")


class ReportRevision(Immutable):
    report = models.ForeignKey(
        Report, on_delete=models.PROTECT, related_name="revisions"
    )
    number = models.PositiveIntegerField()
    answers = models.JSONField(default=dict)
    observations = models.TextField(blank=True)
    actor = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["report", "number"], name="report_revision")
        ]


class Recording(Root):
    report = models.ForeignKey(Report, null=True, on_delete=models.PROTECT)
    appointment = models.ForeignKey(
        "TestimonyAppointment", null=True, on_delete=models.PROTECT
    )
    file = models.OneToOneField(FileVersion, on_delete=models.PROTECT)
    notice_recorded = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True)


class ProcessingRun(Root):
    file = models.ForeignKey(FileVersion, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=30)
    state = models.CharField(max_length=15, default="queued")
    engine = models.CharField(max_length=100, blank=True)
    error = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["file", "purpose"], name="file_processing_identity"
            )
        ]


class TranscriptRevision(Immutable):
    recording = models.ForeignKey(Recording, on_delete=models.PROTECT)
    run = models.ForeignKey(ProcessingRun, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    language = models.CharField(max_length=10)
    kind = models.CharField(max_length=15, default="original")
    text = models.TextField()
    segments = models.JSONField(default=list)
    actor = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)


class TranscriptReview(Immutable):
    revision = models.ForeignKey(TranscriptRevision, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)


class MedicalRelease(Immutable):
    request = models.ForeignKey(ReportRequest, on_delete=models.PROTECT)
    subject = models.ForeignKey(Account, on_delete=models.PROTECT)
    declaration = models.ForeignKey(QuestionnaireVersion, on_delete=models.PROTECT)
    signature = models.ForeignKey(FileVersion, on_delete=models.PROTECT)
    scope = models.JSONField(default=dict)
    signed_at = models.DateTimeField(default=timezone.now)


class CaseNote(Root):
    proceeding = models.ForeignKey(Proceeding, on_delete=models.PROTECT)
    author = models.ForeignKey(Account, on_delete=models.PROTECT)


class NoteRevision(Immutable):
    note = models.ForeignKey(CaseNote, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    text = models.TextField()
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)


class FindingRevision(Immutable):
    proceeding = models.ForeignKey(Proceeding, on_delete=models.PROTECT)
    fact_code = models.CharField(max_length=100)
    number = models.PositiveIntegerField()
    value = models.JSONField(default=dict)
    sources = models.JSONField(default=list)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)


class DecisionRevision(Immutable):
    proceeding = models.ForeignKey(Proceeding, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    type = models.CharField(max_length=30)
    grounds = models.TextField()
    entitlements = models.JSONField(default=dict)
    conditions = models.TextField(blank=True)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["proceeding", "number"], name="decision_revision"
            )
        ]


class Vote(Immutable):
    decision = models.ForeignKey(DecisionRevision, on_delete=models.PROTECT)
    member = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="votes")
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    choice = models.CharField(max_length=10)


class PresidentialApproval(Immutable):
    decision = models.ForeignKey(DecisionRevision, on_delete=models.PROTECT)
    president = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="approvals"
    )
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)


class Decree(Root):
    decision = models.OneToOneField(DecisionRevision, on_delete=models.PROTECT)
    reference = models.CharField(max_length=150, unique=True)
    language = models.CharField(max_length=4, default="en")
    signed_file = models.ForeignKey(FileVersion, on_delete=models.PROTECT)
    signer = models.ForeignKey(Account, on_delete=models.PROTECT)
    issued_at = models.DateTimeField(null=True)


class DecreeRelease(Immutable):
    decree = models.ForeignKey(Decree, on_delete=models.PROTECT)
    party = models.ForeignKey(Party, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    action = models.CharField(max_length=10)


class AppealSupplement(Immutable):
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    text = models.TextField()
    manifest = models.JSONField(default=list)


class AppealDisposition(Immutable):
    application = models.OneToOneField(Application, on_delete=models.PROTECT)
    hearing = models.ForeignKey(Hearing, on_delete=models.PROTECT)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    result = models.CharField(max_length=10)
    explanation = models.TextField(blank=True)
    reopened_proceeding = models.ForeignKey(
        Proceeding, null=True, on_delete=models.PROTECT
    )


class Message(Immutable):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    sender = models.ForeignKey(Account, on_delete=models.PROTECT)
    body = models.TextField()
    channel = models.CharField(max_length=10, default="portal")
    file_links = models.JSONField(default=list)
    email_timing = models.CharField(max_length=25, default="immediate")
    session = models.ForeignKey(CouncilSession, null=True, on_delete=models.PROTECT)
    session_snapshot = models.JSONField(default=dict)


class MessageRecipient(Root):
    message = models.ForeignKey(
        Message, on_delete=models.PROTECT, related_name="recipients"
    )
    party = models.ForeignKey(Party, on_delete=models.PROTECT)
    read_at = models.DateTimeField(null=True)


class TestimonyAppointment(Root):
    __test__ = False
    agenda = models.ForeignKey(AgendaItem, on_delete=models.PROTECT)
    party = models.ForeignKey(Party, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    instructions = models.TextField()
    version = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=15, default="invited")


class TestimonyAppointmentVersion(Immutable):
    __test__ = False
    appointment = models.ForeignKey(TestimonyAppointment, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    instructions = models.TextField()
    attendance_location = models.JSONField(default=dict)
    cancelled = models.BooleanField(default=False)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    request_id = models.UUIDField(null=True)

    class Meta:
        db_table = "testimony_appointment_versions"
        constraints = [models.UniqueConstraint(fields=["appointment", "version"], name="testimony_invitation_version")]


class AgendaTransferEvent(Immutable):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    from_session_snapshot = models.JSONField()
    to_session = models.ForeignKey(CouncilSession, on_delete=models.PROTECT)
    destination_item = models.ForeignKey(AgendaItem, on_delete=models.PROTECT)
    reason = models.TextField()
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    request_id = models.UUIDField(null=True)

    class Meta:
        db_table = "agenda_transfer_events"


class AppointmentResponse(Immutable):
    appointment = models.ForeignKey(TestimonyAppointment, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)
    response = models.CharField(max_length=10)
    explanation = models.TextField(blank=True)


class SettingRevision(Immutable):
    key = models.CharField(max_length=100)
    number = models.PositiveIntegerField()
    value = models.JSONField(default=dict)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "number"], name="setting_version")
        ]
