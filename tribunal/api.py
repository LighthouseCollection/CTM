"""Explicit authenticated endpoints. Never serialize model internals automatically."""

import json
from functools import wraps
from datetime import date, datetime
from pathlib import Path
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from django.shortcuts import render
from tribunal import models as m
from tribunal.policy import (
    active,
    staff,
    administrator,
    writer,
    visible_applications,
    application_for,
    case_for,
)
from tribunal.services.common import audit


def endpoint(methods=("GET",)):
    def decorate(fn):
        @wraps(fn)
        def inner(request, *args, **kwargs):
            if request.method not in methods:
                return JsonResponse({"error": "method_not_allowed"}, status=405)
            if not request.user.is_authenticated:
                return JsonResponse({"error": "authentication_required"}, status=401)
            try:
                active(request.user)
                return fn(request, *args, **kwargs)
            except PermissionDenied as exc:
                return JsonResponse(
                    {"error": "forbidden", "detail": str(exc)}, status=403
                )
            except (ObjectDoesNotExist, ValueError, TypeError, KeyError):
                return JsonResponse({"error": "resource_or_input_invalid"}, status=404)
            except ValidationError as exc:
                return JsonResponse(
                    {"error": "validation", "messages": exc.messages}, status=422
                )
            except IntegrityError:
                return JsonResponse(
                    {
                        "error": "conflict",
                        "detail": "The operation conflicts with another saved record.",
                    },
                    status=409,
                )

        return inner

    return decorate


def body(request):
    if len(request.body) > 1024 * 1024:
        raise ValidationError("JSON request is too large.")
    try:
        value = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("Invalid JSON.")
    if not isinstance(value, dict):
        raise ValidationError("Expected JSON object.")
    return value


def encoded(obj, **extra):
    return {"id": str(obj.pk), **extra}


def filing_version(data):
    version = data.get("expected_version")
    if type(version) is not int or version < 0:
        raise ValidationError("expected_version must be a non-negative integer.")
    return version


def application_data(app, actor):
    revision = app.revisions.filter(number=app.current_version).first()
    fee = getattr(app, "fee", None)
    result = encoded(
        app,
        kind=app.kind,
        status=app.status,
        case_id=str(app.case_id) if app.case_id else None,
        case_number=app.case.number if app.case else None,
        version=app.current_version,
        answers=revision.answers if revision else {},
        fee={
            "amount_minor": fee.amount_minor,
            "currency": fee.currency,
            "status": fee.status,
        }
        if fee
        else None,
    )
    if app.owner_id == actor.pk:
        from tribunal.services.applications import (
            required_documents,
            validate_petition,
            validate_filing_declaration,
        )
        from tribunal.validation import validate_answers

        questionnaire = app.questionnaire
        result["questionnaire"] = (
            encoded(
                questionnaire,
                version=questionnaire.number,
                published=questionnaire.published,
                definition=questionnaire.definition,
                declaration_en=questionnaire.declaration_en,
                declaration_ar=questionnaire.declaration_ar,
            )
            if questionnaire else None
        )
        editable = app.status not in {"withdrawn", "expired", "deleted"}
        if app.submitted_at:
            editable = bool(
                editable and app.kind == "petition" and app.proceeding
                and app.proceeding.status == "open" and app.case.status == "open"
            )
        ready = bool(
            editable and actor.email_verified and not app.duplicate_hold
            and app.status in {"draft", "returned"} and revision and questionnaire
        )
        if ready:
            try:
                validate_answers(questionnaire, revision.answers)
                if app.kind == "petition":
                    validate_petition(revision.answers)
                elif not revision.answers.get("new_information"):
                    ready = False
                required_documents(app, revision.answers)
                if not app.submitted_at:
                    validate_filing_declaration(app)
            except ValidationError:
                ready = False
        satisfied = bool(fee and fee.status in {"paid", "waived", "historical_exempt"})
        returned = bool(app.status == "returned" and app.submitted_at)
        latest_review = m.CompletenessReview.objects.filter(
            submission__application=app
        ).order_by("-created_at", "-id").first()
        result.update(
            can_edit=editable,
            can_checkout=bool(
                ready and app.status == "draft" and fee and fee.status == "due"
            ),
            can_submit=bool(ready and satisfied and not returned),
            can_resubmit=bool(ready and satisfied and returned),
            duplicate_hold=app.duplicate_hold,
            return_instructions=(
                latest_review.instructions
                if returned and latest_review and latest_review.result == "reject"
                else ""
            ),
        )
    return result


@require_GET
def health(request):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "application": "ctm", "version": "0.1.0"})


@require_GET
@ensure_csrf_cookie
def shell(request):
    providers = []
    for name in ("microsoft", "google", "apple"):
        config = settings.SOCIALACCOUNT_PROVIDERS.get(name, {})
        if not any(
            app.get("client_id") and app.get("secret") for app in config.get("APPS", [])
        ):
            continue
        if name == "microsoft" and (
            not settings.MICROSOFT_TENANT_ID
            or settings.MICROSOFT_TENANT_ID.lower()
            in {"common", "organizations", "consumers"}
        ):
            continue
        providers.append(name)
    response = render(
        request, "tribunal/shell.html", {"boot": {"providers": providers}}
    )
    response["Cache-Control"] = "no-store"
    return response


@ensure_csrf_cookie
@endpoint()
def session(request):
    user = request.user
    return JsonResponse(
        {
            "id": str(user.pk),
            "name": f"{user.first_name} {user.last_name}".strip(),
            "role": user.role,
            "portal": "applicant" if user.role == "applicant" else "council",
            "ui_language": user.ui_language,
            "notification_language": user.notification_language,
            "csrf_token": get_token(request),
        }
    )


@endpoint(("GET", "POST"))
def applications(request):
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    application_data(x, request.user)
                    for x in visible_applications(request.user)[:100]
                ]
            }
        )
    from tribunal.services.applications import start_application

    data = body(request)
    result = start_application(
        request.user, data.get("case_id"), data.get("kind", "petition")
    )
    return JsonResponse(application_data(result, request.user), status=201)


@endpoint(("GET", "POST"))
def application(request, app_id):
    if request.method == "GET":
        return JsonResponse(
            application_data(application_for(request.user, app_id), request.user)
        )
    from tribunal.services.applications import save_answers

    data = body(request)
    revision = save_answers(
        request.user, app_id, data["answers"], data["expected_version"]
    )
    return JsonResponse(encoded(revision, version=revision.number), status=201)


@endpoint()
def answer_history(request, app_id):
    app = application_for(request.user, app_id)
    return JsonResponse(
        {
            "items": [
                encoded(
                    x,
                    version=x.number,
                    answers=x.answers,
                    actor=f"{x.actor.first_name} {x.actor.last_name}".strip(),
                    timestamp=x.created_at.isoformat(),
                )
                for x in app.revisions.select_related("actor").order_by("number")
            ]
        }
    )


@endpoint(("POST",))
def submit(request, app_id):
    from tribunal.services.applications import submit_application

    data = body(request)
    result = submit_application(
        request.user, app_id, data["idempotency_key"], data.get("attestation"),
        expected_version=filing_version(data),
    )
    return JsonResponse(encoded(result), status=201)


@endpoint(("POST",))
def review(request, app_id):
    from tribunal.services.applications import review_application

    data = body(request)
    return JsonResponse(
        encoded(
            review_application(
                request.user, app_id, data["result"], data.get("instructions", "")
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def waiver(request, app_id):
    from tribunal.services.applications import waive_fee

    return JsonResponse(encoded(waive_fee(request.user, app_id)), status=201)


@endpoint(("POST",))
def withdraw(request, app_id):
    from tribunal.services.decisions import withdraw_application

    return JsonResponse(encoded(withdraw_application(request.user, app_id)))


@endpoint(("POST",))
def checkout(request, app_id):
    from tribunal.services.payments import create_checkout

    data = body(request)
    base = (
        "https://ctm.lighthouseway.org"
        if not settings.DEBUG
        else request.build_absolute_uri("/").rstrip("/")
    )
    return JsonResponse(
        create_checkout(
            request.user, app_id, data["attestation"], base,
            expected_version=filing_version(data),
        )
    )


@csrf_exempt
@require_POST
def stripe_webhook(request):
    import stripe
    from tribunal.services.payments import process_paid_checkout, finalize_paid_intent

    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({"error": "not_configured"}, status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({"error": "invalid_signature"}, status=400)
    if event.type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        try:
            intent = process_paid_checkout(event.id, event.data.object)
        except ValidationError:
            # No durable paid record exists: retain provider retries instead of acknowledging loss.
            return JsonResponse(
                {"error": "payment_requires_reconciliation"}, status=503
            )
        try:
            finalize_paid_intent(intent.pk)
        except ValidationError:
            # Durable paid candidate/outbox stays for reconciliation; do not repeatedly charge.
            return JsonResponse({"received": True, "reconciliation_required": True})
    return JsonResponse({"received": True})


@endpoint()
def cases(request):
    qs = m.Case.objects.all()
    if request.user.role == "applicant":
        qs = qs.filter(parties__account=request.user).distinct()
    return JsonResponse(
        {
            "items": [
                encoded(
                    c,
                    number=c.number,
                    status=c.status,
                    assigned_member=f"{c.assigned_member.first_name} {c.assigned_member.last_name}".strip()
                    if c.assigned_member
                    else None,
                )
                for c in qs.select_related("assigned_member").order_by("-created_at")[
                    :100
                ]
            ]
        }
    )


@endpoint()
def case_detail(request, case_id):
    case = case_for(request.user, case_id)
    parties = case.parties.all()
    return JsonResponse(
        encoded(
            case,
            number=case.number,
            status=case.status,
            can_message=request.user.role in {"applicant", "admin", "secretary"}
            or case.assigned_member_id == request.user.pk,
            parties=[
                encoded(
                    p,
                    name=p.name,
                    is_self=p.account_id == request.user.pk,
                    can_receive=p.account_id is not None,
                    reference=p.reference
                    if p.account_id == request.user.pk or request.user.is_staff
                    else None,
                )
                for p in parties
            ],
            proceedings=[
                encoded(p, kind=p.kind, status=p.status, sequence=p.sequence)
                for p in case.proceedings.all()
            ],
        )
    )


@endpoint(("POST",))
def assign(request, case_id):
    from tribunal.services.council import assign_case

    data = body(request)
    return JsonResponse(
        encoded(
            assign_case(request.user, case_id, data["member_id"], data["president_id"])
        ),
        status=201,
    )


@endpoint()
def members(request):
    staff(request.user)
    return JsonResponse(
        {
            "items": [
                encoded(x, name=f"{x.first_name} {x.last_name}".strip(), role=x.role)
                for x in m.Account.objects.filter(is_active=True).exclude(
                    role="applicant"
                )
            ]
        }
    )


@endpoint(("POST",))
def enroll(request):
    from tribunal.services.identity import enroll_council

    data = body(request)
    return JsonResponse(
        encoded(
            enroll_council(
                request.user,
                data["email"],
                data.get("first_name", ""),
                data.get("last_name", ""),
                data.get("role", "member"),
                data.get("microsoft_subject"),
            )
        ),
        status=201,
    )


@endpoint(("GET", "POST"))
def sessions(request):
    staff(request.user)
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    encoded(
                        x, date=x.date.isoformat(), reference=x.reference, state=x.state
                    )
                    for x in m.CouncilSession.objects.order_by("-date")[:100]
                ]
            }
        )
    from tribunal.services.council import create_session

    return JsonResponse(
        encoded(
            create_session(request.user, date.fromisoformat(body(request)["date"]))
        ),
        status=201,
    )


@endpoint(("GET", "POST"))
def agenda(request, session_id):
    staff(request.user)
    if request.method == "GET":
        session = m.CouncilSession.objects.get(pk=session_id)
        return JsonResponse(
            {
                "session": encoded(
                    session,
                    date=session.date.isoformat(),
                    state=session.state,
                    can_record_attendance=request.user.role in {"admin", "secretary"}
                    and session.state == "planned",
                ),
                "items": [
                    encoded(
                        x,
                        case_id=str(x.case_id),
                        case_number=x.case.number,
                        part=x.part,
                        state=x.state,
                    )
                    for x in m.AgendaItem.objects.filter(session_id=session_id)
                    .select_related("case")
                    .order_by("part", "position")
                ],
            }
        )
    from tribunal.services.council import place_agenda

    data = body(request)
    return JsonResponse(
        encoded(
            place_agenda(request.user, session_id, data["case_id"], data.get("part", 2))
        ),
        status=201,
    )


@endpoint(("POST",))
def close_session(request, session_id):
    from tribunal.services.council import close_session as command

    return JsonResponse(encoded(command(request.user, session_id)))


@endpoint(("POST",))
def hear(request, item_id):
    from tribunal.services.council import hear_case

    hearing = hear_case(request.user, item_id)
    if hearing is None:
        return JsonResponse(
            {"state": "presenter_absent", "awaiting_manual_placement": True}
        )
    return JsonResponse(encoded(hearing), status=201)


@endpoint(("GET", "POST"))
def attendance(request, session_id):
    from tribunal.services.council import attendance_for, record_attendance

    staff(request.user)
    if request.method == "GET":
        rows = attendance_for(
            request.user, session_id, request.GET.get("hearing_id") or None
        )
        return JsonResponse(
            {
                "items": [
                    encoded(
                        row,
                        member_id=str(row.member_id),
                        member_name=f"{row.member.first_name} {row.member.last_name}".strip(),
                        member_active=row.member.is_active,
                        present=row.present,
                        actor_id=str(row.actor_id),
                        timestamp=row.created_at.isoformat(),
                    )
                    for row in rows.values()
                ]
            }
        )
    data = body(request)
    row = record_attendance(
        request.user,
        session_id,
        data["member_id"],
        data["present"],
        data.get("hearing_id"),
    )
    return JsonResponse(encoded(row), status=201)


@endpoint(("GET", "POST"))
def messages(request, case_id):
    from tribunal.services.communications import messages_for, send_message

    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    encoded(
                        x,
                        body=x.body,
                        sender=f"{x.sender.first_name} {x.sender.last_name}".strip(),
                        channel=x.channel,
                        timestamp=x.created_at.isoformat(),
                        file_links=x.file_links,
                    )
                    for x in messages_for(request.user, case_id).select_related(
                        "sender"
                    )[:250]
                ]
            }
        )
    data = body(request)
    return JsonResponse(
        encoded(
            send_message(
                request.user,
                case_id,
                data["body"],
                data["party_ids"],
                data.get("email_timing", "immediate"),
                data.get("session_id"),
                data.get("file_ids"),
                data.get("channel", "portal"),
            )
        ),
        status=201,
    )


@endpoint(("GET", "POST"))
def notifications(request):
    qs = m.Notification.objects.filter(recipient=request.user)
    if request.method == "POST":
        updated = qs.filter(pk=body(request)["id"], read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return JsonResponse({"updated": bool(updated)})
    offset = int(request.GET.get("offset", "0"))
    if not 0 <= offset <= 2**63 - 52:
        raise ValidationError("Offset is outside the supported range.")
    rows = list(
        qs.select_related("case").order_by("-created_at", "-id")[offset : offset + 51]
    )
    return JsonResponse(
        {
            "items": [
                encoded(
                    x,
                    kind=x.kind,
                    payload=x.payload,
                    read=x.read_at is not None,
                    timestamp=x.created_at.isoformat(),
                    case_id=str(x.case_id) if x.case_id else None,
                    case_number=x.case.number if x.case_id else None,
                )
                for x in rows[:50]
            ],
            "next_offset": offset + 50 if len(rows) > 50 else None,
            "unread_count": qs.filter(read_at__isnull=True).count(),
        }
    )


@endpoint(("POST",))
def upload(request):
    from tribunal.services.files import upload as command

    result = command(
        request.user,
        request.FILES["file"],
        request.POST["category"],
        request.POST.get("application_id"),
        request.POST.get("case_id"),
        request.POST.get("attachment_id"),
        request.POST.get("context", ""),
        request.POST.get("visibility", "own"),
        request.POST.get("request_id"),
    )
    return JsonResponse(
        encoded(
            result,
            name=result.display_name,
            scan_state=result.scan_state,
            sha256=result.sha256,
        ),
        status=201,
    )


@endpoint(("GET", "HEAD"))
def download(request, file_id):
    from tribunal.file_delivery import deliver_file

    return deliver_file(request, file_id)


@endpoint()
def report_questions(request):
    staff(request.user)
    return JsonResponse(
        {
            "items": [
                encoded(
                    x,
                    code=x.code,
                    version=x.version,
                    category=x.category,
                    wording_en=x.wording_en,
                    wording_ar=x.wording_ar,
                    foundational=x.foundational,
                    guidance=x.guidance,
                )
                for x in m.ReportQuestion.objects.order_by(
                    "category", "code", "-version"
                )
            ]
        }
    )


@endpoint(("GET", "POST"))
def report_requests(request, case_id):
    case = case_for(request.user, case_id)
    if request.method == "GET":
        qs = m.ReportRequest.objects.filter(case=case)
        if request.user.role == "applicant":
            qs = (
                qs.filter(subject__account=request.user)
                .exclude(kind__in=["external_priest", "interview"])
                .exclude(state="draft")
            )
        return JsonResponse(
            {
                "items": [
                    encoded(
                        x,
                        title=x.title,
                        kind=x.kind,
                        state=x.state,
                        questions=x.questions,
                        instructions=x.instructions,
                    )
                    for x in qs.order_by("-created_at")
                ]
            }
        )
    from tribunal.services.reports import create_request

    data = body(request)
    return JsonResponse(
        encoded(
            create_request(
                request.user,
                data["proceeding_id"],
                data["party_id"],
                data["kind"],
                data["title"],
                data.get("questions", []),
                data.get("instructions", ""),
                data.get("language", "en"),
                data.get("parent_id"),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def send_report_request(request, request_id):
    from tribunal.services.reports import send_request

    data = body(request)
    value = send_request(
        request.user,
        request_id,
        data.get("external_name", ""),
        data.get("external_email", ""),
    )
    response = JsonResponse(
        {"id": str(request_id), "token": value if isinstance(value, str) else None}
    )
    response["Cache-Control"] = "no-store"
    return response


@endpoint(("POST",))
def complete_report_request(request, request_id):
    from tribunal.services.reports import complete_request

    data = body(request)
    return JsonResponse(
        encoded(
            complete_request(
                request.user,
                request_id,
                data.get("answers", {}),
                data.get("observations", ""),
            )
        ),
        status=201,
    )


@endpoint()
def reports(request, case_id):
    case = case_for(request.user, case_id)
    qs = m.Report.objects.filter(request__case=case).select_related("request__subject")
    if request.user.role == "applicant":
        qs = qs.filter(
            request__subject__account=request.user, author=request.user
        ).exclude(request__kind__in=["interview", "external_priest"])
    items = []
    for report in qs.order_by("-completion_date"):
        revision = report.revisions.order_by("-number").first()
        if (
            report.request.kind in {"medical", "psychological"}
            and request.user.role != "applicant"
            and not m.MedicalRelease.objects.filter(
                request=report.request, scope__council=True
            ).exists()
        ):
            items.append(encoded(report, restricted=True))
            continue
        items.append(
            encoded(
                report,
                title=report.request.title,
                kind=report.request.kind,
                questions=report.request.questions,
                subject=report.request.subject.name,
                version=revision.number if revision else None,
                date=report.completion_date.isoformat(),
                parent_report_id=str(report.request.parent_report_id)
                if report.request.parent_report_id
                else None,
                answers=revision.answers if revision else {},
                observations=revision.observations
                if revision and request.user.is_staff
                else None,
            )
        )
    return JsonResponse({"items": items})


@endpoint(("POST",))
def medical_release(request, request_id):
    from tribunal.services.reports import sign_medical_release

    data = body(request)
    return JsonResponse(
        encoded(
            sign_medical_release(
                request.user, request_id, data["file_id"], data["scope"]
            )
        ),
        status=201,
    )


@endpoint(("GET", "POST"))
def notes(request, proceeding_id):
    proceeding = m.Proceeding.objects.select_related("case").get(pk=proceeding_id)
    staff(request.user)
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    encoded(x, note_id=str(x.note_id), version=x.number, text=x.text)
                    for x in m.NoteRevision.objects.filter(
                        note__proceeding=proceeding
                    ).order_by("created_at")
                ]
            }
        )
    from tribunal.services.council import save_note

    data = body(request)
    return JsonResponse(
        encoded(
            save_note(request.user, proceeding_id, data["text"], data.get("note_id"))
        ),
        status=201,
    )


@endpoint(("POST",))
def decision(request, proceeding_id):
    from tribunal.services.decisions import record_decision

    data = body(request)
    return JsonResponse(
        encoded(
            record_decision(
                request.user,
                proceeding_id,
                data["type"],
                data["grounds"],
                data.get("entitlements", {}),
                data.get("conditions", ""),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def vote(request, decision_id):
    from tribunal.services.decisions import cast_vote

    data = body(request)
    return JsonResponse(
        encoded(
            cast_vote(request.user, decision_id, data["choice"], data.get("member_id"))
        ),
        status=201,
    )


@endpoint(("POST",))
def approval(request, decision_id):
    from tribunal.services.decisions import approve_decision

    return JsonResponse(
        encoded(
            approve_decision(
                request.user, decision_id, body(request).get("president_id")
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def decree(request, decision_id):
    from tribunal.services.decisions import issue_decree

    data = body(request)
    return JsonResponse(
        encoded(
            issue_decree(
                request.user,
                decision_id,
                data["file_id"],
                data["signer_id"],
                data.get("language", "en"),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def release_decree(request, decree_id):
    from tribunal.services.decisions import release_decree as command

    data = body(request)
    return JsonResponse(
        encoded(
            command(
                request.user, decree_id, data["party_id"], data.get("action", "release")
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def appeal_addition(request, app_id):
    from tribunal.services.decisions import add_appeal_information

    data = body(request)
    return JsonResponse(
        encoded(
            add_appeal_information(
                request.user, app_id, data.get("text", ""), data.get("file_ids")
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def appeal_result(request, app_id):
    from tribunal.services.decisions import decide_appeal

    data = body(request)
    return JsonResponse(
        encoded(
            decide_appeal(
                request.user,
                app_id,
                data["hearing_id"],
                data["result"],
                data.get("explanation", ""),
            )
        ),
        status=201,
    )


@endpoint()
def case_audit(request, case_id):
    staff(request.user)
    case = case_for(request.user, case_id)
    return JsonResponse(
        {
            "items": [
                encoded(
                    x,
                    action=x.action,
                    timestamp=x.created_at.isoformat(),
                    source=x.source,
                    source_id=str(x.source_id),
                    actor=str(x.actor_id) if x.actor_id else None,
                )
                for x in m.AuditEvent.objects.filter(case=case).order_by("-created_at")[
                    :250
                ]
            ]
        }
    )


@endpoint()
def system_audit(request):
    administrator(request.user)
    return JsonResponse(
        {
            "items": [
                encoded(
                    x,
                    action=x.action,
                    source=x.source,
                    timestamp=x.created_at.isoformat(),
                )
                for x in m.AuditEvent.objects.order_by("-created_at")[:250]
            ]
        }
    )


@csrf_exempt
def external_report(request, request_id):
    from tribunal.services.reports import external_request, complete_external
    from django.db import transaction

    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if request.method not in {"GET", "POST"}:
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        with transaction.atomic():
            m.ReportRequest.objects.select_for_update().get(pk=request_id)
            source = external_request(request_id, token)
            if request.method == "GET":
                response = JsonResponse(
                    {
                        "id": str(source.pk),
                        "title": source.title,
                        "case_number": source.case.number,
                        "subject": source.subject.name,
                        "instructions": source.instructions,
                        "language": source.language,
                        "draft": source.saved_response,
                    }
                )
            else:
                data = body(request)
                if data.get("action") == "save":
                    source.saved_response = data.get("answers", {})
                    if not isinstance(source.saved_response, dict):
                        raise ValidationError("Invalid response.")
                    source.save(update_fields=["saved_response"])
                    response = JsonResponse({"saved": True})
                else:
                    from tribunal.db.context import database_external

                    with database_external(request_id, token):
                        report = complete_external(
                            request_id, token, data.get("answers", {})
                        )
                    response = JsonResponse(
                        {"submitted": True, "report_id": str(report.pk)}, status=201
                    )
            response["Cache-Control"] = "no-store"
            response["Referrer-Policy"] = "no-referrer"
            return response
    except (PermissionDenied, ValidationError, ObjectDoesNotExist):
        return JsonResponse({"error": "link_unavailable"}, status=403)


@endpoint(("GET", "POST"))
def settings_endpoint(request):
    administrator(request.user)
    if request.method == "GET":
        current = {}
        for record in m.SettingRevision.objects.order_by("key", "-number"):
            current.setdefault(
                record.key,
                encoded(
                    record, key=record.key, version=record.number, value=record.value
                ),
            )
        return JsonResponse({"items": list(current.values())})
    from tribunal.services.configuration import save_setting

    data = body(request)
    return JsonResponse(
        encoded(save_setting(request.user, data["key"], data["value"])), status=201
    )


@endpoint(("GET", "POST"))
def templates(request):
    staff(request.user)
    if request.method == "GET":
        from django.db.models import Q

        return JsonResponse(
            {
                "items": [
                    encoded(t, title=t.title, shared=t.shared, retired=t.retired)
                    for t in m.ReportTemplate.objects.filter(
                        Q(shared=True) | Q(owner=request.user)
                    ).order_by("title")
                ]
            }
        )
    from tribunal.services.configuration import create_template

    data = body(request)
    return JsonResponse(
        encoded(
            create_template(
                request.user,
                data["title"],
                data.get("questions", []),
                data.get("shared", False),
            )
        ),
        status=201,
    )


@endpoint(("GET", "POST"))
def account_settings(request):
    from tribunal.services.identity import save_preferences

    user = request.user
    if request.method == "POST":
        user = save_preferences(request.user, body(request))
    return JsonResponse(
        {
            "ui_language": user.ui_language,
            "notification_language": user.notification_language,
            "email": user.email,
        }
    )


@endpoint()
def search(request):
    from tribunal.services.search import search as command

    return JsonResponse(
        command(
            request.user,
            request.GET.get("q", ""),
            request.GET.get("history") == "true",
            request.GET.get("case_id"),
        )
    )


@endpoint(("POST",))
def delete_draft(request, app_id):
    from tribunal.services.retention import remove_draft

    return JsonResponse(encoded(remove_draft(request.user, app_id)))


@endpoint(("POST",))
def publish_questionnaire(request):
    from tribunal.services.configuration import publish_questionnaire as command

    data = body(request)
    return JsonResponse(
        encoded(
            command(
                request.user,
                data["purpose"],
                data["definition"],
                data["declaration_en"],
                data["declaration_ar"],
            )
        ),
        status=201,
    )


@endpoint()
def dashboard(request):
    if request.user.role == "applicant":
        return JsonResponse(
            {
                "open_cases": m.Case.objects.filter(
                    status="open", parties__account=request.user
                )
                .distinct()
                .count(),
                "drafts": m.Application.objects.filter(
                    owner=request.user, status="draft"
                ).count(),
                "unread_notifications": m.Notification.objects.filter(
                    recipient=request.user, read_at__isnull=True
                ).count(),
            }
        )
    return JsonResponse(
        {
            "my_cases": m.Case.objects.filter(
                status="open", assigned_member=request.user
            ).count(),
            "review_queue": m.Application.objects.filter(
                status="submitted", kind="petition"
            ).count()
            if request.user.role in {"admin", "secretary"}
            else None,
            "upcoming_sessions": [
                {"id": str(s.pk), "date": s.date.isoformat()}
                for s in m.CouncilSession.objects.filter(
                    state="planned", date__gte=timezone.localdate()
                ).order_by("date")[:5]
            ],
        }
    )


@endpoint(("GET", "POST"))
def calls(request, case_id):
    case = case_for(request.user, case_id)
    staff(request.user)
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    encoded(
                        x,
                        party_id=str(x.party_id),
                        occurred_at=x.occurred_at.isoformat(),
                        recorded_at=x.created_at.isoformat(),
                        outcome=x.outcome,
                        notes=x.notes,
                    )
                    for x in m.CallRecord.objects.filter(case=case).order_by(
                        "-occurred_at"
                    )
                ]
            }
        )
    from tribunal.services.communications import log_call

    data = body(request)
    return JsonResponse(
        encoded(
            log_call(
                request.user,
                case_id,
                data["party_id"],
                datetime.fromisoformat(data["occurred_at"]),
                data["outcome"],
                data.get("notes", ""),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def add_party(request, case_id):
    from tribunal.services.identity import add_other_party

    data = body(request)
    return JsonResponse(
        encoded(
            add_other_party(
                request.user,
                case_id,
                data["first_name"],
                data["last_name"],
                data["email"],
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def signature(request, file_id):
    from tribunal.services.decisions import attest_signature

    data = body(request)
    return JsonResponse(
        encoded(
            attest_signature(
                request.user,
                file_id,
                data["signer_id"],
                data["method"],
                data["evidence"],
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def hearing_outcome(request, hearing_id):
    from tribunal.services.council import save_hearing_outcome

    data = body(request)
    return JsonResponse(
        encoded(
            save_hearing_outcome(
                request.user,
                hearing_id,
                data.get("internal_text", ""),
                data.get("recommendations", ""),
                data.get("applicant_message"),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def testimony(request, item_id):
    from tribunal.services.council import schedule_testimony

    data = body(request)
    return JsonResponse(
        encoded(
            schedule_testimony(
                request.user,
                item_id,
                data["party_id"],
                datetime.fromisoformat(data["starts_at"]),
                datetime.fromisoformat(data["ends_at"]),
                data["instructions"],
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def testimony_response(request, appointment_id):
    from tribunal.services.council import respond_testimony

    data = body(request)
    return JsonResponse(
        encoded(
            respond_testimony(
                request.user,
                appointment_id,
                data["version"],
                data["response"],
                data.get("explanation", ""),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def recording(request):
    from tribunal.services.reports import create_recording

    data = body(request)
    return JsonResponse(
        encoded(
            create_recording(
                request.user,
                data["file_id"],
                data.get("report_id"),
                data.get("appointment_id"),
                data.get("notice_recorded", False),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def recording_finalize(request, recording_id):
    from tribunal.services.reports import finalize_recording

    return JsonResponse(
        encoded(finalize_recording(request.user, recording_id)), status=201
    )


@endpoint(("GET", "POST"))
def report_revision(request, report_id):
    from tribunal.services.reports import revise_report

    if request.method == "GET":
        staff(request.user)
        report = m.Report.objects.select_related("request__subject").get(pk=report_id)
        case_for(request.user, report.request.case_id)
        if (
            report.request.kind in {"medical", "psychological"}
            and not m.MedicalRelease.objects.filter(
                request=report.request,
                subject=report.request.subject.account,
                scope__council=True,
            ).exists()
        ):
            raise PermissionDenied("Signed scoped medical disclosure is required.")
        return JsonResponse(
            {
                "items": [
                    encoded(
                        row,
                        version=row.number,
                        answers=row.answers,
                        observations=row.observations,
                        actor=f"{row.actor.first_name} {row.actor.last_name}".strip()
                        if row.actor
                        else None,
                        timestamp=row.created_at.isoformat(),
                    )
                    for row in report.revisions.select_related("actor").order_by(
                        "-number"
                    )
                ]
            }
        )

    data = body(request)
    return JsonResponse(
        encoded(
            revise_report(
                request.user, report_id, data["answers"], data.get("observations", "")
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def finding(request, proceeding_id):
    from tribunal.services.council import save_finding

    data = body(request)
    return JsonResponse(
        encoded(
            save_finding(
                request.user,
                proceeding_id,
                data["fact_code"],
                data["value"],
                data.get("sources"),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def historical_stage(request):
    from tribunal.services.historical import stage

    data = body(request)
    return JsonResponse(
        encoded(stage(request.user, data["payload"], data.get("workspace_id"))),
        status=201,
    )


@endpoint(("POST",))
def historical_publish(request, workspace_id):
    from tribunal.services.historical import publish

    case = publish(request.user, workspace_id)
    return JsonResponse(encoded(case, number=case.number), status=201)


@endpoint()
def case_files(request, case_id):
    from tribunal.services.files import case_file_listing

    if request.GET.get("history", "0") not in {"0", "1"}:
        raise ValidationError("History must be 0 or 1.")
    result = case_file_listing(
        request.user,
        case_id,
        history=request.GET.get("history") == "1",
        offset=int(request.GET.get("offset", "0")),
    )
    response = JsonResponse(result)
    response["Cache-Control"] = "private, no-store"
    return response
