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
    from tribunal.services.filing_privacy import revision_visible
    from tribunal.services.closed_filings import CLOSED_INTAKE, require_new_information

    revision = app.revisions.filter(number=app.current_version).first()
    if actor.pk != app.owner_id and (revision is None or not revision_visible(revision)):
        formal = app.submissions.select_related("revision").order_by("-created_at", "-id").first()
        revision = formal.revision if formal else None
    fee = getattr(app, "fee", None)
    result = encoded(
        app,
        kind=app.kind,
        origin=app.origin,
        requires_new_information=app.origin == CLOSED_INTAKE,
        status=app.status,
        case_id=str(app.case_id) if app.case_id else None,
        case_number=app.case.number if app.case else None,
        version=revision.number if revision else 0,
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
        from tribunal.services.filing_actions import own_filing_actions
        from tribunal.services.payments import own_pending_checkout
        result.update(own_filing_actions(app, actor))
        result.update(own_pending_checkout(app, actor))
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
                require_new_information(app, revision.answers)
                required_documents(app, revision.answers)
                if not app.submitted_at:
                    validate_filing_declaration(app)
            except ValidationError:
                ready = False
        satisfied = bool(fee and fee.status in {"paid", "waived", "historical_exempt"})
        returned = bool(app.status == "returned" and app.submitted_at)
        unresolved = m.CheckoutIntent.objects.filter(application=app, state__in=["processing", "paid", "needs_review"]).exists()
        stale_checkout = m.CheckoutIntent.objects.filter(application=app, state="pending").exclude(revision=revision).exists()
        latest_review = m.CompletenessReview.objects.filter(
            submission__application=app
        ).order_by("-created_at", "-id").first()
        result.update(
            can_edit=editable,
            can_checkout=bool(
                ready and not unresolved and not stale_checkout
                and not m.CheckoutIntent.objects.filter(application=app, state="pending").exists()
                and app.status == "draft" and fee and fee.status == "due"
            ),
            can_submit=bool(ready and satisfied and not returned and not unresolved),
            can_resubmit=bool(ready and satisfied and returned and not unresolved),
            duplicate_hold=app.duplicate_hold,
            return_instructions=(
                latest_review.instructions
                if returned and latest_review and latest_review.result == "reject"
                else ""
            ),
        )
    else:
        from tribunal.projections import staff_application_data

        result.update(staff_application_data(app, actor))
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
        qs = visible_applications(request.user)
        if request.GET.get("state") == "awaiting_review":
            if request.user.role == "applicant":
                raise PermissionDenied("Council completeness queue required.")
            qs = qs.filter(kind="petition", status="submitted").exclude(origin="closed_case_intake")
        if request.GET.get("state") == "council_consideration":
            staff(request.user)
            from django.db.models import Q
            qs = qs.filter(status="submitted").filter(Q(kind="appeal") | Q(origin="closed_case_intake"))
        return JsonResponse(
            {
                "items": [
                    application_data(x, request.user)
                    for x in qs.order_by("created_at", "pk")[:100]
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
    from tribunal.services.filing_privacy import revision_visible
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
                for x in app.revisions.select_related("actor", "application").order_by("number")
                if app.owner_id == request.user.pk or revision_visible(x)
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

    data = body(request)
    concurrency = {"expected_version": filing_version(data)} if request.user.role == "applicant" or "expected_version" in data else {}
    return JsonResponse(encoded(withdraw_application(request.user, app_id, **concurrency)))


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
    from tribunal.services.payments import (
        process_paid_checkout, finalize_paid_intent, process_checkout_state, process_finance_event,
    )

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
            if event.type == "checkout.session.completed" and event.data.object.get("payment_status") != "paid":
                process_checkout_state(event.id, event.data.object, "processing")
                return JsonResponse({"received": True, "payment_pending": True})
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
    elif event.type in {"checkout.session.expired", "checkout.session.async_payment_failed",
                         "charge.dispute.created", "charge.dispute.closed", "charge.refunded"}:
        try:
            payload = event.data.object
            if event.type.startswith("checkout.session."):
                process_checkout_state(event.id, payload, "expired" if event.type.endswith("expired") else "failed")
            else:
                kind = "refunded" if event.type == "charge.refunded" else (
                    "chargeback" if event.type == "charge.dispute.created" else "dispute_" + str(payload.get("status", "")))
                process_finance_event(event.id, payload, kind)
        except (ValidationError, ValueError):
            return JsonResponse({"error": "payment_requires_reconciliation"}, status=503)
    return JsonResponse({"received": True})


@endpoint()
def application_payments(request, app_id):
    from tribunal.services.payments import application_payment_data

    return JsonResponse(application_payment_data(request.user, app_id))


@endpoint()
def payment_reconciliation(request):
    from tribunal.services.payments import payment_reconciliation as query

    return JsonResponse(query(request.user, int(request.GET.get("offset", "0"))))


@endpoint(("POST",))
def retry_payment(request, intent_id):
    from tribunal.services.payments import retry_paid_filing

    result = retry_paid_filing(request.user, intent_id)
    return JsonResponse({"submitted": result is not None, "submission_id": str(result.pk) if result else None})


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
    from tribunal.projections import case_capabilities
    case = case_for(request.user, case_id)
    parties = case.parties.all()
    response = JsonResponse(
        encoded(
            case,
            number=case.number,
            status=case.status,
            **case_capabilities(case, request.user),
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

    response["Cache-Control"] = "private, no-store"
    return response


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
    from tribunal.services.staff_roles import assignment_president, assignment_recorder

    staff(request.user)
    return JsonResponse(
        {
            "items": [
                encoded(x, name=f"{x.first_name} {x.last_name}".strip(), role=x.role,
                        president=x.role == "president", active=x.is_active,
                        can_authorize_assignment=assignment_president(x),
                        can_record_assignment=assignment_recorder(x))
                for x in m.Account.objects.filter(is_active=True).exclude(
                    role="applicant"
                )
            ]
        }
    )


@endpoint(("GET", "POST"))
def tribunals(request):
    from tribunal.services.staff_roles import create_tribunal, existing_admin

    existing_admin(request.user)
    if request.method == "GET":
        return JsonResponse({"items": [encoded(row, code=row.code, name_en=row.name_en,
            name_ar=row.name_ar, timezone=row.timezone) for row in m.Tribunal.objects.order_by("code")]})
    data = body(request)
    row = create_tribunal(request.user, data.get("code"), data.get("name_en"), data.get("name_ar"))
    return JsonResponse(encoded(row, code=row.code, name_en=row.name_en, name_ar=row.name_ar, timezone=row.timezone), status=201)


@endpoint(("GET", "POST"))
def assignment_authorities(request):
    from tribunal.services.staff_roles import existing_admin, grant_assignment_authority, current_tribunal_id

    existing_admin(request.user)
    if request.method == "GET":
        rows = m.StaffRole.objects.filter(role__in=["president", "admin", "secretary"], membership__tribunal_id=current_tribunal_id()).select_related("membership")
        return JsonResponse({"items": [encoded(row, role=row.role, account_id=str(row.membership.account_id),
            tribunal_id=str(row.membership.tribunal_id), membership_id=str(row.membership_id),
            granted_by_id=str(row.granted_by_id), revoked_at=row.revoked_at.isoformat() if row.revoked_at else None) for row in rows.order_by("created_at", "id")]})
    data = body(request)
    row = grant_assignment_authority(request.user, data["account_id"], data["tribunal_id"], data.get("role", "president"))
    return JsonResponse(encoded(row, role=row.role, membership_id=str(row.membership_id), granted_by_id=str(row.granted_by_id)), status=201)


@endpoint(("POST",))
def revoke_assignment_authority(request, role_id):
    from tribunal.services.staff_roles import revoke_assignment_authority as command

    row = command(request.user, role_id)
    return JsonResponse(encoded(row, revoked_at=row.revoked_at.isoformat()))


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
    from tribunal.projections import session_capabilities
    staff(request.user)
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    encoded(
                        x, date=x.date.isoformat(), reference=x.reference, state=x.state,
                        **session_capabilities(x, request.user)
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
    from tribunal.projections import agenda_item_data, session_capabilities
    from tribunal.services.council import attendance_for
    staff(request.user)
    if request.method == "GET":
        session = m.CouncilSession.objects.get(pk=session_id)
        return JsonResponse(
            {
                "session": encoded(
                    session,
                    date=session.date.isoformat(),
                    state=session.state,
                    **session_capabilities(session, request.user),
                ),
                "items": [
                    agenda_item_data(x, request.user, attendance_for(request.user, session.pk))
                    for x in m.AgendaItem.objects.filter(session_id=session_id)
                    .select_related("case__assigned_member", "session")
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
def reschedule_session(request, session_id):
    from tribunal.services.council import reschedule_session as command

    data = body(request)
    replacements = data.get("appointments", {})
    if not isinstance(replacements, dict):
        raise ValidationError("Appointments must be keyed by identifier.")
    times = {}
    for identifier, value in replacements.items():
        if not isinstance(value, dict):
            raise ValidationError("Each appointment requires new start/end times.")
        times[identifier] = {**value, "starts_at": datetime.fromisoformat(value["starts_at"]),
                             "ends_at": datetime.fromisoformat(value["ends_at"])}
    target = command(request.user, session_id, date.fromisoformat(data["date"]), times, data.get("reason", ""))
    return JsonResponse(encoded(target, date=target.date.isoformat(), reference=target.reference), status=201)


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
    from tribunal.services.filing_privacy import notice_visible
    qs = m.Notification.objects.filter(recipient=request.user)
    hidden = [pk for pk, key in qs.values_list("pk", "key") if not notice_visible(key)]
    qs = qs.exclude(pk__in=hidden)
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
        expected_request_version=request.POST.get("expected_request_version"),
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


@endpoint()
def application_files(request, app_id):
    from tribunal.services.files import application_file_listing

    if request.GET.get("history"):
        raise PermissionDenied("Applicant file history is not available.")
    return JsonResponse(application_file_listing(request.user, app_id))


@endpoint(("GET", "HEAD"))
def download(request, file_id):
    from tribunal.file_delivery import deliver_file

    return deliver_file(request, file_id)


@endpoint()
def request_files(request, request_id):
    from tribunal.services.files import request_file_listing

    return JsonResponse(request_file_listing(request.user, request_id))


@endpoint()
def file_status(request, file_id):
    from tribunal.services.files import authorized_file

    staff(request.user)
    file = authorized_file(request.user, file_id, require_safe=False)
    scan = file.technical_events.filter(task="scan").order_by("-created_at", "-id").first()
    state = scan.result if scan and scan.result in {"clean", "pending", "rejected"} else "pending"
    return JsonResponse({"id": str(file.pk), "scan_state": state,
                         "can_download": state == "clean"})


@endpoint()
def report_questions(request):
    from tribunal.projections import question_taxonomy

    staff(request.user)
    return JsonResponse(
        {
            "items": [
                encoded(
                    x,
                    code=x.code,
                    version=x.version,
                    category=x.category,
                    **question_taxonomy().get(x.code, {"category_id": None, "category_ar": None, "topic_groups": []}),
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
    from tribunal.projections import release_metadata
    from tribunal.services.request_contracts import own_request_data, request_version
    case = case_for(request.user, case_id)
    if request.method == "GET":
        qs = m.ReportRequest.objects.filter(case=case)
        if request.user.role == "applicant":
            qs = (
                qs.filter(subject__account=request.user)
                .filter(sent_at__isnull=False)
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
                        subject_party_id=str(x.subject_id),
                        subject_name=x.subject.name,
                        language=x.language,
                        created_at=x.created_at.isoformat(),
                        sent_at=x.sent_at.isoformat() if x.sent_at else None,
                        parent_report_id=str(x.parent_report_id) if x.parent_report_id else None,
                        author=f"{x.author.first_name} {x.author.last_name}".strip(),
                        **release_metadata(x, request.user),
                        **({"request_version": request_version(x)}
                            if request.user.role != "applicant" else {}),
                        **(own_request_data(x, request.user) if request.user.role == "applicant" else {}),
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
    concurrency = ({"expected_version": data.get("expected_version")}
                   if request.user.role == "applicant" or "expected_version" in data else {})
    return JsonResponse(
        encoded(
            complete_request(
                request.user,
                request_id,
                data.get("answers", {}),
                data.get("observations", ""),
                **concurrency,
            )
        ),
        status=201,
    )


@endpoint()
def reports(request, case_id):
    case = case_for(request.user, case_id)
    qs = m.Report.objects.filter(request__case=case).select_related(
        "request__subject", "request__proceeding", "request__case", "author")
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
                **({"author_id": str(report.author_id) if report.author_id else None,
                    "author": f"{report.author.first_name} {report.author.last_name}".strip() if report.author else None,
                    "submitted_at": report.created_at.isoformat(), "method": report.method,
                    "can_revise": bool(report.author_id == request.user.pk and report.author
                        and report.author.role != "applicant" and report.request.proceeding.status == "open"
                        and report.request.case.status == "open" and (request.user.role in {"admin", "secretary"}
                            or report.request.case.assigned_member_id == request.user.pk))}
                   if request.user.role != "applicant" else {}),
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
                request.user, request_id, data["file_id"], data["scope"],
                expected_version=data.get("expected_version"),
                declaration_id=data.get("declaration_id"), accepted=data.get("accepted"),
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
                    encoded(x, note_id=str(x.note_id), version=x.number, text=x.text,
                            author_id=str(x.note.author_id),
                            author=f"{x.note.author.first_name} {x.note.author.last_name}".strip(),
                            timestamp=x.created_at.isoformat(),
                            can_edit=bool(x.note.author_id == request.user.pk
                                and proceeding.status == "open" and proceeding.case.status == "open"
                                and (request.user.role in {"admin", "secretary"} or proceeding.case.assigned_member_id == request.user.pk)))
                    for x in m.NoteRevision.objects.filter(
                        note__proceeding=proceeding
                    ).select_related("note__author").order_by("created_at", "id")
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


@endpoint(("GET", "POST"))
def decision(request, proceeding_id):
    staff(request.user)
    if request.method == "GET":
        from tribunal.projections import decision_data

        proceeding = m.Proceeding.objects.get(pk=proceeding_id)
        return JsonResponse({"items": [decision_data(row, request.user)
                             for row in m.DecisionRevision.objects.filter(proceeding=proceeding)
                             .select_related("actor", "proceeding__case").order_by("-number")]})
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
    if not isinstance(data.get("idempotency_key"), str) or not data["idempotency_key"].strip():
        raise ValidationError("A supplement idempotency_key is required.")
    return JsonResponse(
        encoded(
            add_appeal_information(
                request.user, app_id, data.get("text", ""), data.get("file_ids"),
                expected_version=filing_version(data), idempotency_key=data["idempotency_key"],
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def closed_filing_result(request, app_id):
    from tribunal.services.decisions import decide_appeal
    from tribunal.services.closed_filings import CLOSED_INTAKE

    app = application_for(request.user, app_id)
    staff(request.user)
    if app.origin != CLOSED_INTAKE:
        raise ValidationError("This is not a closed-case first filing.")
    data = body(request)
    row = decide_appeal(request.user, app_id, data["hearing_id"], data["result"], data.get("explanation", ""))
    return JsonResponse(encoded(row), status=201)


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
    from tribunal.services.filing_privacy import audit_visible
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
                ] if audit_visible(x)
            ]
        }
    )


@endpoint()
def system_audit(request):
    from tribunal.services.filing_privacy import audit_visible
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
                for x in m.AuditEvent.objects.order_by("-created_at")[:250] if audit_visible(x)
            ]
        }
    )


@csrf_exempt
def external_report(request, request_id):
    from tribunal.services.reports import external_request, complete_external, lock_request
    from tribunal.db.context import database_external
    from django.db import transaction

    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if request.method not in {"GET", "POST"}:
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        with transaction.atomic(), database_external(request_id, token):
            lock_request(request_id)
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
    from tribunal.projections import template_data
    staff(request.user)
    if request.method == "GET":
        from django.db.models import Q

        return JsonResponse(
            {
                "items": [
                    template_data(t, request.user)
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


@endpoint(("POST",))
def template_publish(request, template_id):
    from tribunal.services.configuration import publish_personal_template
    from tribunal.projections import template_data

    return JsonResponse(template_data(publish_personal_template(request.user, template_id), request.user), status=201)


@endpoint(("POST",))
def template_retire(request, template_id):
    from tribunal.services.configuration import retire_template
    from tribunal.projections import template_data

    return JsonResponse(template_data(retire_template(request.user, template_id), request.user))


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


@endpoint(("POST",))
def search(request):
    from tribunal.services.search import search as command

    data = body(request)
    history = data.get("history", False)
    if type(history) is not bool:
        raise ValidationError("history must be a boolean.")
    return JsonResponse(
        command(
            request.user,
            data.get("q", ""),
            history,
            data.get("case_id"),
        )
    )


@endpoint(("POST",))
def delete_draft(request, app_id):
    from tribunal.services.retention import remove_draft

    return JsonResponse(encoded(remove_draft(request.user, app_id, expected_version=filing_version(body(request)))))


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
            ).exclude(origin="closed_case_intake").count()
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
                        actor_id=str(x.actor_id),
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


@endpoint()
def hearing_detail(request, hearing_id):
    from tribunal.projections import hearing_data

    staff(request.user)
    hearing = m.Hearing.objects.select_related("agenda__case", "proceeding").get(pk=hearing_id)
    return JsonResponse(hearing_data(hearing, request.user))


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
                email_timing=data.get("email_timing", "immediate"),
                session_id=data.get("session_id"),
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


@endpoint()
def own_testimony(request):
    from tribunal.services.council import own_testimony as query

    return JsonResponse(query(request.user))


@endpoint(("POST",))
def cancel_testimony(request, appointment_id):
    from tribunal.services.council import cancel_testimony as command

    value = command(request.user, appointment_id, body(request).get("expected_version"))
    return JsonResponse(encoded(value, version=value.version, state=value.state))


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
                duration_ms=data.get("duration_ms"), recording_notice=data.get("recording_notice"),
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


@endpoint()
def report_recordings(request, report_id):
    from tribunal.services.media import report_recordings as query
    return JsonResponse(query(request.user, report_id, offset=int(request.GET.get("offset", 0)),
        transcript_offset=int(request.GET.get("transcript_offset", 0))))


@endpoint()
def transcript_detail(request, revision_id):
    from tribunal.services.media import transcript_for, transcript_data
    return JsonResponse(transcript_data(request.user, transcript_for(request.user, revision_id)))


@endpoint(("POST",))
def transcript_review(request, revision_id):
    from tribunal.services.reports import review_transcript
    return JsonResponse(encoded(review_transcript(request.user, revision_id)), status=201)


@endpoint(("POST",))
def processing_retry(request, run_id):
    from tribunal.services.media import retry_processing
    value = retry_processing(request.user, run_id)
    return JsonResponse(encoded(value, attempt=value.attempt, state=value.state), status=201)


@endpoint(("POST",))
def transcript_correct(request, revision_id):
    from tribunal.services.media import correct_transcript
    data = body(request)
    row = correct_transcript(request.user, revision_id, data["text"], data.get("segments", []), data.get("expected_version"))
    return JsonResponse(encoded(row, version=row.number, reviewed=m.TranscriptReview.objects.filter(revision=row).exists()), status=201)


@endpoint(("POST",))
def pending_link_cancel(request, pending_id):
    from tribunal.services.identity import cancel_pending_link
    row = cancel_pending_link(request.user, pending_id)
    return JsonResponse(encoded(row, state=row.state))


@endpoint(("POST",))
def report_request_cancel(request, request_id):
    from tribunal.services.reports import cancel_request
    row = cancel_request(request.user, request_id, body(request).get("expected_version"))
    return JsonResponse(encoded(row, state=row.state))


@endpoint(("GET", "POST"))
def finding(request, proceeding_id):
    from tribunal.services.council import save_finding

    staff(request.user)
    proceeding = m.Proceeding.objects.get(pk=proceeding_id)
    if request.method == "GET":
        return JsonResponse({"items": [encoded(row, fact_code=row.fact_code,
            version=row.number, value=row.value, sources=row.sources,
            actor_id=str(row.actor_id), actor=f"{row.actor.first_name} {row.actor.last_name}".strip(),
            timestamp=row.created_at.isoformat()) for row in m.FindingRevision.objects.filter(
                proceeding=proceeding).select_related("actor").order_by("fact_code", "number", "id")]})
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
