from datetime import date
from zoneinfo import ZoneInfo
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from tribunal.models import (
    Account,
    Application,
    AnswerRevision,
    Case,
    CaseNumberCounter,
    Party,
    OpenCaseClaim,
    Proceeding,
    FeeObligation,
    Submission,
    CompletenessReview,
    QuestionnaireVersion,
    FileVersion,
    FileTechnicalEvent,
)
from tribunal.policy import active, administrator, application_for, open_proceeding
from .common import audit, lock_key, notify, notify_manager
from .closed_filings import CLOSED_INTAKE, council_filing, linked_never_filer, require_new_information

GROUNDS = {"infidelity", "desertion", "abuse", "faith", "addiction", "concealment"}


def check_filing_version(app, expected_version):
    """Called after locking the application; legacy internal callers may omit it."""
    if expected_version is not None and (
        type(expected_version) is not int
        or expected_version < 0
        or app.current_version != expected_version
    ):
        raise ValidationError("Another change was saved. Reload before filing.")


def validate_filing_declaration(app):
    questionnaire = app.questionnaire
    if (
        questionnaire is None
        or not questionnaire.published
        or not questionnaire.declaration_en.strip()
        or not questionnaire.declaration_ar.strip()
    ):
        raise ValidationError(
            "A published bilingual declaration is required before filing."
        )


@transaction.atomic
def start_application(actor, case_id=None, kind="petition"):
    active(actor)
    if actor.role != "applicant":
        raise PermissionDenied("Applicant account required.")
    if kind not in {"petition", "appeal"}:
        raise ValidationError("Invalid filing purpose.")
    lock_key(f"person:{actor.person_id}")
    claim = OpenCaseClaim.objects.filter(person=actor.person).first()
    case = None
    if case_id:
        party = (
            Party.objects.filter(case_id=case_id, account=actor)
            .select_related("case")
            .first()
        )
        if not party:
            raise PermissionDenied("Not a party to this case.")
        case = party.case
    if kind == "appeal" and (
        case is None or not case.proceedings.filter(status="closed").exists()
    ):
        raise ValidationError("An appeal requires an existing closed proceeding.")
    if kind == "petition" and claim and (not case or case.pk != claim.case_id):
        raise ValidationError("Only one open case per applicant; new draft blocked.")
    existing = Application.objects.filter(
        owner=actor,
        kind=kind,
        status__in=["draft", "submitted"] if kind == "appeal" else ["draft"],
    )
    if kind == "appeal":
        existing = existing.filter(case=case)
    prior = existing.first()
    if prior:
        if case and prior.case_id != case.pk:
            raise ValidationError("Continue or resolve the existing draft before starting a different case filing.")
        return prior
    if (
        case
        and kind == "petition"
        and Application.objects.filter(
            owner=actor, case=case, kind=kind, submitted_at__isnull=False
        ).exists()
    ):
        raise ValidationError("Petition already submitted for this case.")
    schema = (
        QuestionnaireVersion.objects.filter(purpose=kind, published=True)
        .order_by("-number")
        .first()
    )
    if schema is None:
        raise ValidationError("No published questionnaire is configured.")
    app = Application.objects.create(
        owner=actor, case=case, kind=kind, questionnaire=schema,
        origin=CLOSED_INTAKE if case and case.status == "closed" and kind == "petition" else "portal"
    )
    if app.origin == CLOSED_INTAKE:
        linked_never_filer(app, case)
    FeeObligation.objects.create(application=app)
    audit(actor, "draft_started", app, case)
    return app


@transaction.atomic
def save_answers(actor, app_id, answers, expected_version):
    app = application_for(actor, app_id, write=True)
    app = Application.objects.select_for_update(of=("self",)).get(pk=app.pk)
    if not isinstance(answers, dict):
        raise ValidationError("Answers must be an object.")
    if council_filing(app) and app.submitted_at:
        raise ValidationError(
            "Submitted appeal is immutable; append additional information."
        )
    if app.submitted_at:
        if not app.proceeding:
            raise ValidationError("Proceeding missing.")
        open_proceeding(app.proceeding)
    if app.status in {"withdrawn", "expired", "deleted"}:
        raise ValidationError("Application is no longer editable.")
    if app.current_version != expected_version:
        raise ValidationError("Another change was saved. Reload before editing.")
    app.current_version += 1
    revision = AnswerRevision.objects.create(
        application=app,
        number=app.current_version,
        answers=answers,
        actor=actor,
        questionnaire=app.questionnaire,
    )
    if actor.pk == app.owner_id:
        app.last_activity = timezone.now()
    app.save(update_fields=["current_version", "last_activity"])
    audit(actor, "answers_saved", revision, app.case)
    if app.submitted_at and app.status != "returned" and actor.pk == app.owner_id:
        notify_manager(app.case, "answer_changed", revision, digest=True)
    return revision


@transaction.atomic
def allocate_case_number(at=None, *, application_id=None):
    from datetime import datetime
    if at is not None and (not isinstance(at, datetime) or not timezone.is_aware(at)):
        raise ValidationError("Case numbering requires an aware server timestamp.")
    local_date = (
        (at or timezone.now()).astimezone(ZoneInfo("America/Los_Angeles")).date()
    )
    lock_key(f"case-counter:{local_date}")
    from django.db import connection
    if connection.vendor == "postgresql":
        from tribunal.db.context import database_settings
        from django.db import IntegrityError
        try:
            with database_settings({"ctm.numbering_application": str(application_id) if application_id else ""}), connection.cursor() as cursor:
                cursor.execute("SELECT public.ctm_allocate_case_number(%s)", [local_date])
                return cursor.fetchone()[0]
        except IntegrityError as exc:
            if getattr(exc.__cause__, "sqlstate", None) == "23514":
                raise ValidationError("Daily case-number capacity reached; nothing has been submitted.") from exc
            raise
    counter, _ = CaseNumberCounter.objects.select_for_update(
        of=("self",)
    ).get_or_create(date=local_date)
    if counter.last_value >= 99:
        raise ValidationError(
            "Daily case-number capacity reached; nothing has been submitted."
        )
    counter.last_value += 1
    counter.save(update_fields=["last_value"])
    return f"{local_date:%Y%m%d}-{counter.last_value:02d}"


def safe_file(file):
    result = file.technical_events.filter(task="scan").order_by("-created_at", "-id").first()
    return result is not None and result.result == "clean"


DOCUMENT_LABELS = {
    "MC": ("Marriage certificate", "شهادة الزواج"),
    "CMC": ("Church marriage certificate", "شهادة الزواج الكنسي"),
    "CDD": ("Final civil divorce decree", "حكم الطلاق المدني النهائي"),
    "PHOTO": ("Applicant photo", "صورة مقدم الطلب"),
    "SPOUSE_PHOTO": ("Spouse photo, if available", "صورة الزوج أو الزوجة إن توفرت"),
    "PET": ("Petition statement", "بيان الالتماس"),
    "RO": ("Restraining order copy", "نسخة من أمر الحماية"),
}


def document_requirements(app, answers):
    required = {"MC", "CDD", "PHOTO"} if app.kind == "petition" else set()
    if app.kind == "petition":
        required |= set(app.questionnaire.definition.get("required_document_categories", []))
    statement = answers.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        required.add("PET")
    categories = list(DOCUMENT_LABELS)[:-1] if app.kind == "petition" else ["PET"]
    categories += sorted(required - set(categories))
    requirements = [
        {"category": category, "context": "", "label_en": DOCUMENT_LABELS.get(category, (category, ""))[0],
         "label_ar": DOCUMENT_LABELS.get(category, (category, ""))[1], "required": category in required}
        for category in categories
    ]
    orders = answers.get("restraining_orders", [])
    if not isinstance(orders, list):
        raise ValidationError("Restraining orders must be a list.")
    seen = set()
    for order in orders:
        context = order.get("id") if isinstance(order, dict) else None
        if not isinstance(context, str) or not context.strip() or len(context) > 150 or context in seen:
            raise ValidationError("Every restraining order requires its own saved identifier.")
        seen.add(context)
        requirements.append({"category": "RO", "context": context,
                             "label_en": DOCUMENT_LABELS["RO"][0],
                             "label_ar": DOCUMENT_LABELS["RO"][1], "required": True})
    return requirements


def required_documents(app, answers):
    current = []
    for attachment in app.attachments.all():
        file = attachment.versions.order_by("-number").first()
        if file and safe_file(file):
            from .files import validate_category

            validate_category(attachment.category, file.mime_type)
            current.append(file)
    for requirement in document_requirements(app, answers):
        if requirement["required"] and not any(
            file.attachment.category == requirement["category"]
            and file.attachment.context == requirement["context"] for file in current
        ):
            raise ValidationError(f"Required document missing: {requirement['category']}")
    for order in answers.get("restraining_orders", []):
        if not all(
            str(order.get(k, "")).strip() and str(order[k]).lower() != "unknown"
            for k in ["court", "number", "status"]
        ):
            raise ValidationError(
                "Every restraining order requires court, case number and status."
            )
        if not any(
            f.attachment.category == "RO"
            and f.attachment.context == str(order.get("id"))
            for f in current
        ):
            raise ValidationError(
                "Every restraining order requires its own uploaded copy."
            )
    return current


def validate_petition(answers):
    required = [
        "first_name",
        "last_name",
        "birth_date",
        "gender",
        "marriage_date",
        "grounds",
    ]
    if any(not answers.get(k) for k in required):
        raise ValidationError(
            "Complete the required identity, marriage and grounds fields."
        )
    if answers["gender"] not in {"M", "F"} or not set(answers["grounds"]) <= GROUNDS:
        raise ValidationError("Invalid gender or selected grounds.")
    for field in ["birth_date", "marriage_date"]:
        try:
            value = date.fromisoformat(answers[field])
        except (TypeError, ValueError):
            raise ValidationError(f"Invalid {field} date.")
        if value > timezone.localdate():
            raise ValidationError("Future identity/marriage dates are invalid.")
    for child in answers.get("children", []):
        if not child.get("gender") or not child.get("lives_with"):
            raise ValidationError(
                "Children require gender and lives-with; Unknown is allowed."
            )


@transaction.atomic
def submit_application(
    actor, app_id, idempotency_key, attestation=None, *, expected_version=None, paid_intent_id=None
):
    app = application_for(actor, app_id)
    if actor.pk != app.owner_id:
        raise PermissionDenied("Only the applicant can attest and submit.")
    lock_key(f"person:{actor.person_id}")
    app = (
        Application.objects.select_for_update(of=("self",))
        .select_related("owner", "questionnaire", "case")
        .get(pk=app.pk)
    )
    previous = Submission.objects.filter(idempotency_key=idempotency_key).first()
    if previous:
        if previous.application_id != app.pk:
            raise ValidationError("Idempotency key belongs to another operation.")
        return previous
    check_filing_version(app, expected_version)
    if not actor.email_verified:
        raise ValidationError("Verify your email before submission.")
    if app.duplicate_hold:
        raise ValidationError("Duplicate identity review must be completed first.")
    if app.status not in {"draft", "returned"}:
        raise ValidationError("Application already submitted.")
    from tribunal.models import CheckoutIntent

    unresolved = CheckoutIntent.objects.filter(application=app, state__in=["pending", "processing", "paid", "needs_review"])
    if paid_intent_id is not None:
        unresolved = unresolved.exclude(pk=paid_intent_id)
    if unresolved.exists():
        raise ValidationError("An existing checkout requires processing or reconciliation before submission.")
    fee = FeeObligation.objects.select_for_update(of=("self",)).get(application=app)
    if fee.status not in {"paid", "waived", "historical_exempt"}:
        raise ValidationError("Successful payment or authorized waiver is required.")
    if fee.status == "paid":
        from tribunal.models import PaymentEvent

        if not PaymentEvent.objects.filter(application=app, kind="paid", amount_minor=fee.amount_minor, currency=fee.currency).exists():
            raise ValidationError("A verified provider payment is required.")
    revision = app.revisions.filter(number=app.current_version).first()
    if not revision:
        raise ValidationError("Save the completed application first.")
    answers = revision.answers
    from tribunal.validation import validate_answers

    validate_answers(app.questionnaire, answers)
    if app.kind == "petition":
        validate_petition(answers)
    elif not answers.get("new_information"):
        raise ValidationError(
            "State the new information or evidence supporting the appeal."
        )
    files = required_documents(app, answers)
    first_submission = app.submitted_at is None
    if first_submission:
        from tribunal.validation import validate_attestation

        validate_filing_declaration(app)
        validate_attestation(attestation)
    if app.kind == "petition":
        dob = date.fromisoformat(answers["birth_date"])
        spouse_dob = None
        try:
            spouse_dob = date.fromisoformat(answers.get("spouse_birth_date", ""))
        except (ValueError, TypeError):
            pass
        marriage_date = date.fromisoformat(answers["marriage_date"])
        low, high = sorted([dob, spouse_dob]) if spouse_dob else (None, None)
        if spouse_dob:
            lock_key(f"marriage:{marriage_date}:{low}:{high}")
        matched = (
            Case.objects.filter(
                marriage_date=marriage_date, spouse_dob_low=low, spouse_dob_high=high
            )
            if spouse_dob
            else Case.objects.none()
        )
        if matched.count() > 1:
            raise ValidationError("Ambiguous marriage match requires review.")
        case = app.case or matched.first()
        claim = OpenCaseClaim.objects.filter(person=actor.person).first()
        if claim and (not case or claim.case_id != case.pk):
            raise ValidationError("Applicant already has another open case.")
        if not case:
            case = Case.objects.create(
                number=allocate_case_number(application_id=app.pk),
                marriage_date=marriage_date,
                spouse_dob_low=low,
                spouse_dob_high=high,
            )
            Proceeding.objects.create(case=case)
        case = Case.objects.select_for_update(of=("self",)).get(pk=case.pk)
        closed_intake = app.origin == CLOSED_INTAKE or case.status == "closed"
        if closed_intake:
            party = linked_never_filer(app, case)
            app.origin = CLOSED_INTAKE
            require_new_information(app, answers)
        else:
            party = case.parties.filter(person=actor.person).first()
        if not party:
            if case.parties.count() >= 2:
                raise ValidationError("Party mapping requires administrator review.")
            # Existing party must match the reverse supplied DOB, never infer person equality from dates alone.
            if case.parties.exists():
                other = case.parties.select_related("person").first()
                if (
                    not spouse_dob
                    or not other.person
                    or other.person.birth_date != spouse_dob
                ):
                    raise ValidationError(
                        "Exact spouse identity mapping requires review."
                    )
            party = Party.objects.create(
                case=case,
                person=actor.person,
                account=actor,
                slot="A" if not case.parties.exists() else "B",
            )
        person = actor.person
        if not closed_intake:
            person.first_name = answers["first_name"]
            person.last_name = answers["last_name"]
            person.birth_date = dob
            person.gender = answers["gender"]
            person.save()
            if not party.reference:
                initials = answers["first_name"][0].upper() + answers["last_name"][0].upper()
                party.reference = f"{case.number}-{initials}{dob:%Y%m%d}{answers['gender']}"
            party.name = f"{answers['first_name']} {answers['last_name']}"
            party.participating = True
            party.save()
            OpenCaseClaim.objects.get_or_create(person=person, defaults={"case": case})
        app.case = case
        app.party = party
        app.proceeding = None if closed_intake else case.proceedings.get(status="open")
    else:
        if (
            not app.case
            or not Party.objects.filter(case=app.case, account=actor).exists()
        ):
            raise PermissionDenied("Appeal belongs to another case.")
    manifest = [
        {
            "id": str(f.pk),
            "sha256": f.sha256,
            "name": f.display_name,
            "category": f.attachment.category,
        }
        for f in files
    ]
    declaration = (
        {
            "name": attestation.get("name"),
            "accepted": True,
            "language": actor.ui_language,
            "text": app.questionnaire.declaration_ar
            if actor.ui_language == "ar"
            else app.questionnaire.declaration_en,
            "version": app.questionnaire.number,
        }
        if first_submission
        else {
            "original_submission": str(
                app.submissions.order_by("created_at").first().pk
            )
        }
    )
    submission = Submission.objects.create(
        application=app,
        revision=revision,
        manifest=manifest,
        actor=actor,
        idempotency_key=idempotency_key,
        attestation=declaration,
    )
    app.status = "submitted"
    app.submitted_at = app.submitted_at or timezone.now()
    app.save(update_fields=["status", "submitted_at", "case", "party", "proceeding", "origin"])
    for attachment in app.attachments.all():
        attachment.case = app.case
        attachment.proceeding = app.proceeding
        attachment.save(update_fields=["case", "proceeding"])
    audit(actor, "application_submitted", submission, app.case)
    if app.origin == CLOSED_INTAKE:
        notify_manager(app.case, "closed_intake_submitted", submission)
    for reviewer in Account.objects.filter(
        role__in=["admin", "secretary"], is_active=True
    ):
        notify(reviewer, "closed_intake_submitted" if app.origin == CLOSED_INTAKE else "intake_submitted", submission, case=app.case)
    notify(actor, "submission_received", submission, case=app.case)
    return submission


@transaction.atomic
def waive_fee(actor, app_id):
    administrator(actor)
    from django.db import connection

    fee = FeeObligation.objects.select_for_update(of=("self",)).get(application_id=app_id)
    if connection.vendor == "postgresql":
        from tribunal.db.context import database_actor

        with database_actor(actor), connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_fee_can_waive(%s)", [str(app_id)])
            eligible = cursor.fetchone()[0]
    else:
        eligible = Application.objects.filter(pk=app_id, submitted_at__isnull=True, status="draft").exists()
        from tribunal.models import CheckoutIntent

        eligible = eligible and not CheckoutIntent.objects.filter(application_id=app_id, state__in=["pending", "processing", "paid", "needs_review"]).exists()
    if not eligible:
        raise ValidationError("Only an unsubmitted filing without an unresolved checkout can be waived.")
    if fee.status != "due":
        raise ValidationError("Only an outstanding filing fee can be waived.")
    fee.status = "waived"
    fee.waived_by = actor
    fee.save(update_fields=["status", "waived_by"])
    audit(actor, "fee_waived", fee)
    return fee


@transaction.atomic
def review_application(actor, app_id, result, instructions=""):
    administrator(actor)
    app = Application.objects.select_for_update(of=("self",)).get(pk=app_id)
    if app.kind != "petition" or app.status != "submitted":
        raise ValidationError("No petition is awaiting completeness review.")
    if not app.proceeding:
        raise ValidationError("Proceeding missing.")
    open_proceeding(app.proceeding)
    if result not in {"accept", "reject"} or (
        result == "reject" and not instructions.strip()
    ):
        raise ValidationError("Reject requires correction instructions.")
    submission = app.submissions.order_by("-created_at", "-id").first()
    review = CompletenessReview.objects.create(
        submission=submission, actor=actor, result=result, instructions=instructions
    )
    app.status = "accepted" if result == "accept" else "returned"
    app.save(update_fields=["status"])
    notify(
        app.owner,
        "application_" + app.status,
        review,
        case=app.case,
        payload={"instructions": instructions},
    )
    audit(actor, "completeness_" + result, review, app.case)
    return review
