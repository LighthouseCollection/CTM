from tribunal.db.context import core_operation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from tribunal.models import (
    Account,
    Case,
    Party,
    Proceeding,
    DecisionRevision,
    Vote,
    PresidentialApproval,
    Decree,
    DecreeRelease,
    FileVersion,
    Application,
    OpenCaseClaim,
    AppealDisposition,
    AppealSupplement,
    Hearing,
    SignatureAttestation,
)
from tribunal.policy import (
    active,
    staff,
    administrator,
    writer,
    open_proceeding,
    application_for,
)
from .common import audit, lock_key, notify, notify_manager
from .applications import safe_file
from .closed_filings import CLOSED_INTAKE, council_filing, require_new_information
from tribunal.db.context import database_actor, database_settings
from tribunal.validation import validate_json_value, revision_replay, UNBOUND_VERSION

DECISION_TYPES = {
    "diss-applicant",
    "diss-respondent",
    "diss-both",
    "diss-conditional",
    "null-granted",
    "null-conditional",
    "denied",
    "deferred",
}


def lock_proceeding(proceeding_id):
    case_id = Proceeding.objects.values_list("case_id", flat=True).get(pk=proceeding_id)
    case = Case.objects.select_for_update(of=("self",)).get(pk=case_id)
    proceeding = Proceeding.objects.select_for_update(of=("self",)).get(
        pk=proceeding_id
    )
    proceeding.case = case
    return proceeding


def lock_decision(decision_id):
    decision = DecisionRevision.objects.get(pk=decision_id)
    decision.proceeding = lock_proceeding(decision.proceeding_id)
    return decision


@transaction.atomic
def record_decision(actor, proceeding_id, type, grounds, entitlements, conditions="", *, expected_version=UNBOUND_VERSION):
    proceeding = lock_proceeding(proceeding_id)
    writer(actor, proceeding.case)
    open_proceeding(proceeding)
    if (not isinstance(type, str) or type not in DECISION_TYPES
            or not isinstance(grounds, str) or not grounds.strip() or len(grounds)>100_000
            or not isinstance(conditions, str) or len(conditions)>100_000):
        raise ValidationError("Record the decision type and grounds/reason.")
    validate_json_value({"grounds": grounds, "conditions": conditions, "entitlements": entitlements})
    parties = {str(x) for x in proceeding.case.parties.values_list("pk", flat=True)}
    if (
        not isinstance(entitlements, dict)
        or not set(entitlements) <= parties
        or any(not isinstance(value, str) or value not in {"certificate", "notice_only"} for value in entitlements.values())
    ):
        raise ValidationError(
            "Decision entitlements must reference this case's parties."
        )
    if type == "null-granted" and any(
        entitlements.get(p) != "certificate" for p in parties
    ):
        raise ValidationError("Declaration of Nullity entitles both parties.")
    if type.endswith("conditional") and not conditions.strip():
        raise ValidationError("State the parties and conditions explicitly.")
    latest = DecisionRevision.objects.filter(proceeding=proceeding).order_by("-number").first()
    if revision_replay(latest, actor, expected_version, type=type, grounds=grounds,
                       entitlements=entitlements, conditions=conditions):
        return latest
    number = latest.number + 1 if latest else 1
    revision = DecisionRevision.objects.create(
        proceeding=proceeding,
        number=number,
        type=type,
        grounds=grounds,
        entitlements=entitlements,
        conditions=conditions,
        actor=actor,
    )
    audit(actor, "decision_recorded", revision, proceeding.case)
    return revision


def current_decision(decision):
    if DecisionRevision.objects.filter(
        proceeding=decision.proceeding, number__gt=decision.number
    ).exists():
        raise ValidationError("This decision has been revised; use the latest version.")


@transaction.atomic
def cast_vote(actor, decision_id, choice, member_id=None, *, idempotency_key=None):
    staff(actor)
    decision = lock_decision(decision_id)
    open_proceeding(decision.proceeding)
    current_decision(decision)
    member = Account.objects.get(pk=member_id or actor.pk, is_active=True)
    staff(member)
    if member.role not in {"president", "secretary", "member"}:
        raise PermissionDenied("Only council members may be recorded as voters.")
    if member.pk != actor.pk:
        administrator(actor)
    if not isinstance(choice, str) or choice not in {"approve", "deny", "abstain"}:
        raise ValidationError("Invalid vote.")
    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key)>100:
            raise ValidationError("Provide a nonempty vote key up to100 characters.")
        validate_json_value(idempotency_key)
        previous = Vote.objects.filter(decision=decision, member=member, idempotency_key=idempotency_key).first()
        if previous:
            if previous.actor_id == actor.pk and previous.choice == choice:
                return previous
            raise ValidationError("Vote key already identifies a different choice or recorder.")
    vote = Vote.objects.create(
        decision=decision, member=member, actor=actor, choice=choice, idempotency_key=idempotency_key
    )
    audit(actor, "vote_recorded", vote, decision.proceeding.case)
    return vote


@transaction.atomic
def approve_decision(actor, decision_id, president_id=None):
    decision = lock_decision(decision_id)
    open_proceeding(decision.proceeding)
    current_decision(decision)
    if actor.role == "president":
        president = actor
        active(actor)
    else:
        administrator(actor)
        president = Account.objects.get(
            pk=president_id, role="president", is_active=True
        )
    approval = PresidentialApproval.objects.create(
        decision=decision, president=president, actor=actor
    )
    audit(actor, "president_approved", approval, decision.proceeding.case)
    if decision.type == "denied":
        close_case(actor, decision.proceeding.case, "petition_denied")
    return approval


@core_operation("close")
def close_case(actor, case, reason, notify_parties=True):
    now = timezone.now()
    case.status = "closed"
    case.closed_at = now
    case.save(update_fields=["status", "closed_at"])
    Proceeding.objects.filter(case=case, status="open").update(
        status="closed", closed_at=now
    )
    OpenCaseClaim.objects.filter(case=case).delete()
    from tribunal.models import ReportRequest

    ReportRequest.objects.filter(case=case, state="draft").update(state="cancelled")
    ReportRequest.objects.filter(case=case, state="sent").update(
        state="closed"
    )
    audit(actor, reason, case, case)
    if notify_parties:
        for party in case.parties.select_related("account"):
            if party.account:
                notify(party.account, reason, case, case=case)


@transaction.atomic
def issue_decree(actor, decision_id, file_id, signer_id, language="en"):
    administrator(actor)
    decision = lock_decision(decision_id)
    case = decision.proceeding.case
    open_proceeding(decision.proceeding)
    current_decision(decision)
    if decision.type in {"denied", "deferred"} or language not in {"en", "ar", "both"}:
        raise ValidationError("This outcome does not issue a decree certificate.")
    if not PresidentialApproval.objects.filter(
        decision=decision, president_id=signer_id
    ).exists():
        raise ValidationError("Matching presidential approval is required.")
    file = FileVersion.objects.select_related("attachment").get(pk=file_id)
    if (
        file.attachment.case_id != case.pk
        or file.attachment.visibility != "council"
        or file.mime_type != "application/pdf"
        or not safe_file(file)
    ):
        raise ValidationError(
            "Store the safe council-only signed PDF in this case first."
        )
    signer = Account.objects.get(pk=signer_id, role="president", is_active=True)
    if not SignatureAttestation.objects.filter(file=file, signer=signer).exists():
        raise ValidationError(
            "Record the president signature evidence/method for this exact stored PDF before issuance."
        )
    suffix = (
        f"-A{decision.proceeding.sequence}"
        if decision.proceeding.kind == "appeal"
        else ""
    )
    decree = Decree.objects.create(
        decision=decision,
        reference=f"DCR-{case.number}{suffix}",
        language=language,
        signed_file=file,
        signer=signer,
        issued_at=timezone.now(),
    )
    close_case(actor, case, "decree_issued")
    audit(actor, "decree_issued", decree, case)
    return decree


@transaction.atomic
def attest_signature(actor, file_id, signer_id, method, evidence):
    active(actor)
    signer = Account.objects.get(pk=signer_id, role="president", is_active=True)
    if actor.pk != signer.pk:
        administrator(actor)
    if (
        method not in {"digital", "signed_scan"}
        or not isinstance(evidence, dict)
        or not evidence.get("confirmed_signed")
    ):
        raise ValidationError(
            "Record digital signature or uploaded signed scan evidence."
        )
    file = FileVersion.objects.select_related("attachment").get(pk=file_id)
    if (
        not file.attachment.case
        or file.attachment.visibility != "council"
        or file.mime_type != "application/pdf"
        or not safe_file(file)
    ):
        raise ValidationError(
            "Signed PDF must be safely stored in the council case area."
        )
    record = SignatureAttestation.objects.create(
        file=file,
        signer=signer,
        actor=actor,
        method=method,
        signed_at=timezone.now(),
        evidence=evidence,
    )
    audit(actor, "president_signature_recorded", record, file.attachment.case)
    return record


@transaction.atomic
def release_decree(actor, decree_id, party_id, action="release"):
    administrator(actor)
    decree = Decree.objects.select_related("decision__proceeding__case").get(
        pk=decree_id
    )
    party = Party.objects.get(pk=party_id, case=decree.decision.proceeding.case)
    if action not in {"release", "withdraw"}:
        raise ValidationError("Invalid release action.")
    if decree.decision.entitlements.get(str(party.pk)) != "certificate":
        raise PermissionDenied("Party is entitled to notice only.")
    event = DecreeRelease.objects.create(
        decree=decree, party=party, actor=actor, action=action
    )
    if action == "release" and party.account:
        notify(party.account, "decree_available", event, case=party.case)
    audit(actor, "decree_access_" + action, event, party.case)
    return event


@transaction.atomic
@core_operation("withdraw")
def withdraw_application(actor, application_id, *, expected_version=None):
    app = application_for(actor, application_id)
    app = (
        Application.objects.select_for_update(of=("self",))
        .select_related("case", "party")
        .get(pk=app.pk)
    )
    if app.owner_id != actor.pk and actor.role != "admin":
        raise PermissionDenied("Only owner or admin can withdraw petition.")
    from .applications import check_filing_version
    check_filing_version(app, expected_version)
    if app.status not in {"submitted", "accepted", "returned"}:
        raise ValidationError("Filing is not eligible for withdrawal.")
    if app.kind == "appeal" or (app.origin == CLOSED_INTAKE and app.status == "submitted"):
        if (
            actor.pk != app.owner_id
            or AppealDisposition.objects.filter(application=app).exists()
        ):
            raise PermissionDenied(
                "Only the appellant can withdraw before disposition."
            )
        # Serialize the pending-appeal status transition with hearing attendance
        # checks, which hold the same case lock and never lock the application.
        Case.objects.select_for_update(of=("self",)).get(pk=app.case_id)
    else:
        proceeding_id = app.proceeding_id
        if app.origin == CLOSED_INTAKE:
            disposition = AppealDisposition.objects.get(application=app, result="accept")
            proceeding_id = app.case.proceedings.get(status="open").pk
        open_proceeding(lock_proceeding(proceeding_id))
    pending_closed_intake = app.origin == CLOSED_INTAKE and app.status == "submitted"
    app.status = "withdrawn"
    app.save(update_fields=["status"])
    if app.kind == "petition" and not pending_closed_intake and app.party:
        app.party.withdrawn_at = timezone.now()
        app.party.save(update_fields=["withdrawn_at"])
        if not app.case.parties.filter(
            participating=True, withdrawn_at__isnull=True
        ).exists():
            close_case(actor, app.case, "petitions_withdrawn", notify_parties=False)
    # Withdrawal never triggers other applicant notification.
    notify_manager(app.case, "filing_withdrawn", app)
    audit(actor, "filing_withdrawn", app, app.case)
    return app


@transaction.atomic
def add_appeal_information(actor, application_id, text, file_ids=None, *, expected_version=None, idempotency_key=None):
    app = application_for(actor, application_id)
    app = Application.objects.select_for_update(of=("self",)).get(pk=app.pk)
    from .applications import check_filing_version
    check_filing_version(app, expected_version)
    if actor.pk != app.owner_id:
        raise PermissionDenied("Only the filing owner can supplement it.")
    if not isinstance(text, str) or len(text) > 100000:
        raise ValidationError("Supplement text must be within the supported size.")
    if file_ids is None:
        file_ids = []
    if not isinstance(file_ids, list) or len(file_ids) != len(set(map(str, file_ids))):
        raise ValidationError("Provide distinct evidence identifiers as a list.")
    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 100:
            raise ValidationError("A nonempty supplement idempotency_key up to100 characters is required.")
        previous = AppealSupplement.objects.filter(application=app, idempotency_key=idempotency_key).first()
        if previous:
            if previous.text == text and [x["id"] for x in previous.manifest] == list(map(str, file_ids)):
                return previous
            raise ValidationError("This supplement key already identifies different information.")
    if (
        actor.pk != app.owner_id
        or not council_filing(app)
        or app.status != "submitted"
        or AppealDisposition.objects.filter(application=app).exists()
    ):
        raise PermissionDenied("Only the owner may supplement a pending appeal.")
    if not text.strip() and not file_ids:
        raise ValidationError("Provide additional information or evidence.")
    manifest = []
    for file_id in file_ids or []:
        file = FileVersion.objects.select_related("attachment").get(pk=file_id)
        if (file.attachment.application_id != app.pk or file.attachment.owner_id != actor.pk
                or file.attachment.report_request_id or file.attachment.visibility != "own"
                or file.attachment.case_id != app.case_id or not safe_file(file)
                or file.attachment.versions.order_by("-number").first().pk != file.pk):
            raise PermissionDenied("Evidence must belong to this appeal.")
        manifest.append({"id": str(file.pk), "sha256": file.sha256})
    extra = AppealSupplement.objects.create(
        application=app, actor=actor, text=text, manifest=manifest, idempotency_key=idempotency_key
    )
    notify_manager(app.case, "appeal_added", extra, digest=True)
    audit(actor, "appeal_added", extra, app.case)
    return extra


@transaction.atomic
def decide_appeal(actor, application_id, hearing_id, result, explanation=""):
    with database_actor(actor), database_settings({"ctm.council_result": str(application_id),
        "ctm.result_hearing": str(hearing_id), "ctm.result_choice": str(result)}):
        return _decide_appeal(actor, application_id, hearing_id, result, explanation)


def _decide_appeal(actor, application_id, hearing_id, result, explanation=""):
    app = (
        Application.objects.select_for_update(of=("self",))
        .select_related("case")
        .get(pk=application_id)
    )
    writer(actor, app.case)
    if (
        not council_filing(app)
        or app.status != "submitted"
        or result not in {"accept", "decline"}
        or AppealDisposition.objects.filter(application=app).exists()
    ):
        raise ValidationError("No pending appeal or invalid result.")
    hearing = Hearing.objects.select_related("agenda").get(
        pk=hearing_id, agenda__case=app.case, state="held", agenda__part=2
    )
    if app.origin == CLOSED_INTAKE and hearing.created_at < app.submitted_at:
        raise ValidationError("Council must present this filing after it was submitted.")
    if hearing.presenter_id != app.case.assigned_member_id:
        raise ValidationError("Appeal must be heard by its assigned member.")
    case = Case.objects.select_for_update(of=("self",)).get(pk=app.case_id)
    proceeding = None
    reopened = False
    if result == "accept":
        if app.origin == CLOSED_INTAKE:
            formal = app.submissions.select_related("revision").order_by("-created_at", "-id").first()
            if formal is None:
                raise ValidationError("The formal filing is missing.")
            require_new_information(app, formal.revision.answers)
        party = Party.objects.select_for_update().get(account_id=app.owner_id, case=case)
        party.participating = True
        party.withdrawn_at = None
        party.save(update_fields=["participating", "withdrawn_at"])
        parties = list(
            case.parties.filter(participating=True, person__isnull=False, account__isnull=False).order_by(
                "person_id"
            )
        )
        for party in parties:
            lock_key(f"person:{party.person_id}")
            conflict = (
                OpenCaseClaim.objects.filter(person=party.person)
                .exclude(case=case)
                .exists()
            )
            if conflict:
                raise ValidationError(
                    "A participating applicant has another open case."
                )
        proceeding = case.proceedings.filter(status="open").first()
        if proceeding is None:
            sequence = (case.proceedings.aggregate(n=Max("sequence"))["n"] or 0) + 1
            proceeding = Proceeding.objects.create(
                case=case, kind="appeal", sequence=sequence
            )
            case.status = "open"
            case.closed_at = None
            case.save(update_fields=["status", "closed_at"])
            reopened = True
        for party in parties:
            OpenCaseClaim.objects.get_or_create(
                person=party.person, defaults={"case": case}
            )
    result_record = AppealDisposition.objects.create(
        application=app,
        hearing=hearing,
        actor=actor,
        result=result,
        explanation=explanation,
        reopened_proceeding=proceeding,
    )
    app.status = "accepted" if result == "accept" else "declined"
    app.save(update_fields=["status"])
    notify(
        app.owner,
        ("closed_intake_" if app.origin == CLOSED_INTAKE else "appeal_") + result,
        result_record,
        case=case,
        payload={"explanation": explanation},
    )
    if reopened:
        for party in case.parties.select_related("account"):
            if party.account:
                notify(party.account, "case_reopened", result_record, case=case)
    audit(actor, ("closed_intake_" if app.origin == CLOSED_INTAKE else "appeal_") + result, result_record, case)
    return result_record
