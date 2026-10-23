"""Explicit authenticated endpoints. Never serialize model internals automatically."""

import json
from functools import wraps
from datetime import date, datetime
from pathlib import Path
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_headers
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
from tribunal.validation import VersionConflict


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
            except VersionConflict as exc:
                return JsonResponse({"error": "version_conflict", "current_version": exc.current_version}, status=409)
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


def optional_version(data):
    return {"expected_version": data["expected_version"]} if "expected_version" in data else {}


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
        filing_party_id=str(app.party_id) if app.party_id else None,
        filing_party_name=app.party.name if app.party_id else None,
        filing_party_role=("applicant" if app.party.slot == "A" else "respondent") if app.party_id else None,
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
            "email": user.email,
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


def _case_list_data(case):
    """Project the case-list fields from the case and its submitted filing."""
    parties = sorted(case.parties.all(), key=lambda party: party.slot)
    filings = [
        application for application in case.applications.all()
        if application.kind == "petition" and application.submitted_at is not None
    ]
    filing = max(filings, key=lambda application: (application.submitted_at, application.id), default=None)
    applicant = filing.party if filing and filing.party_id else (parties[0] if parties else None)
    respondent = next((party for party in parties if not applicant or party.pk != applicant.pk), None)
    revision = next((row for row in filing.revisions.all() if row.number == filing.current_version), None) if filing else None
    grounds = (revision.answers.get("grounds") or revision.answers.get("reason") or []) if revision else []
    if isinstance(grounds, str):
        grounds = [grounds]
    def party_gender(party):
        if not party:
            return None
        person_id = party.person_id or m.Account.objects.filter(pk=party.account_id).values_list("person_id", flat=True).first()
        return m.Person.objects.filter(pk=person_id).values_list("gender", flat=True).first() or None
    return {
        "applicant_gender": party_gender(applicant),
        "respondent_gender": party_gender(respondent),
        "applicant_name": applicant.name if applicant else None,
        "respondent_name": respondent.name if respondent else None,
        "reason": "; ".join(str(value) for value in grounds if value) or None,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
        "party_names": [party.name for party in parties],
    }


@endpoint()
def cases(request):
    from tribunal.pagination import page_records
    qs = m.Case.objects.all()
    if request.user.role == "applicant":
        qs = qs.filter(parties__account=request.user).distinct()
    return JsonResponse(page_records(
        qs.select_related("assigned_member").prefetch_related(
            "parties", "applications__party", "applications__revisions"
        ).order_by("-created_at", "-id"), request,
        default_limit=100,
        serialize=lambda c: encoded(
            c, number=c.number, status=c.status,
            assigned_member_id=str(c.assigned_member_id) if c.assigned_member_id else None,
            assigned_member=f"{c.assigned_member.first_name} {c.assigned_member.last_name}".strip()
            if c.assigned_member else None,
            **_case_list_data(c),
        ),
    ))


def _profile_value(answers, *keys):
    """Return the submitted scalar value for the first populated answer key."""
    for key in keys:
        value = answers.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return None


def _profile_address(answers, prefix=""):
    value = answers.get(f"{prefix}address")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        parts = [
            value.get("street"), value.get("city"), value.get("region") or value.get("state"),
            value.get("postal") or value.get("postal_code") or value.get("zip"), value.get("country"),
        ]
        return ", ".join(str(part).strip() for part in parts if str(part or "").strip()) or None
    return None


def _submitted_party_profile(answers, prefix=""):
    """Project only the approved spouse-card fields from one immutable filing revision."""
    key = lambda *names: _profile_value(answers, *(f"{prefix}{name}" for name in names))
    return {
        "personal": {
            "other_names": key("other_names", "aliases"),
            "place_of_birth": key("birth_country", "place_of_birth"),
            "nationality": key("nationality"),
            "awareness_of_application": key("aware_of_application", "awareness_of_application"),
        },
        "contact": {
            "address": _profile_address(answers, prefix),
            "mobile": key("mobile", "mobile_number"),
            "email": key("email", "email_address"),
            "immigration_status": key("immigration_status"),
            "residing_with": key("residing_with"),
        },
        "career": {
            "education": key("education"),
            "graduation_year": key("graduation_year", "year_of_graduation"),
            "occupation": key("occupation"),
        },
        "church_affiliation": {
            "denomination": key("denomination"),
            "bishop": key("bishop", "name_of_bishop"),
            "diocese": key("diocese"),
            "parish": key("parish", "parish_name"),
            "confessor": key("confessor", "father_of_confession"),
        },
    }


def _applicant_submission_source(application):
    """A minimal, non-PII reference to the immutable applicant filing revision."""
    if not application or not application.submitted_at:
        return None
    return {
        "kind": "applicant_submission",
        "application_id": str(application.pk),
        "revision": application.current_version,
        "submitted_at": application.submitted_at.isoformat(),
    }


def _submitted_marriage(answers):
    """Project marriage facts only from the accepted applicant filing."""
    value = lambda *keys: _profile_value(answers, *keys)
    return {
        "outside_coptic_church": value("married_outside_coptic_church", "outside_coptic_church"),
        "outside_denomination": value("religious_denomination_officiating", "outside_denomination"),
        "outside_marriage_date": value("date_of_marriage_outside_coptic_church", "outside_marriage_date"),
        "church_marriage_date": value("church_marriage_date", "marriage_date"),
        "officiating_priest": value("officiating_priest", "marriage_officiant"),
        "church_name": value("church_name", "marriage_church_name"),
        "church_location": value("church_location", "church_address", "marriage_church_location"),
        "diocese": value("marriage_diocese", "church_diocese", "diocese"),
    }


def _separation_value(answers, *keys):
    """Read a submitted separation field by its stable code or legacy alias."""
    expanded = []
    for key in keys:
        expanded.extend((key, key.replace(".", "_")))
    return _profile_value(answers, *expanded)


def _submitted_separation(answers, application, case):
    """Project applicant assertions; never infer legal or relationship facts."""
    source_party = application.party if application and application.party_id else None
    other_party = next((party for party in case.parties.all() if not source_party or party.pk != source_party.pk), None)
    initiated = _separation_value(answers, "separation.initiated_by", "initiated_by")
    subject = source_party if initiated == "self" else other_party if initiated == "spouse" else None
    orders = answers.get("restraining_orders") if isinstance(answers.get("restraining_orders"), list) else []
    return {
        "marital_status": _separation_value(answers, "separation.marital_status", "marital_status"),
        "separation_date": _separation_value(answers, "separation.date", "separation_date", "date_of_separation"),
        "initiated_by": {
            "value": initiated,
            "party": {"name": subject.name, "gender": subject.person.gender if subject and subject.person_id else None, "slot": subject.slot} if subject else None,
        } if initiated else None,
        "reason": _separation_value(answers, "grounds", "reason"),
        "civil_divorce": {
            "filed": _separation_value(answers, "civil_divorce.filed", "civil_divorce_filed"),
            "date": _separation_value(answers, "civil_divorce.date", "civil_divorce_date", "date_of_civil_divorce"),
            "court": _separation_value(answers, "civil_divorce.court", "court_name"),
            "location": _separation_value(answers, "civil_divorce.location", "court_location", "court_address"),
            "case_number": _separation_value(answers, "civil_divorce.case_number", "civil_case_number", "court_case_number"),
            "status": _separation_value(answers, "civil_divorce.status", "civil_divorce_status"),
        },
        "restraining_orders": [{
            "filed": _profile_value(order, "filed", "restraining_order_filed"),
            "date": _profile_value(order, "date", "restraining_order_date"),
            "expiration_date": _profile_value(order, "expiration_date", "expires_at"),
            "name_listed": _profile_value(order, "name_listed", "protected_person"),
            "court": _profile_value(order, "court", "court_name"),
            "case_number": _profile_value(order, "case_number", "number"),
            "status": _profile_value(order, "status"),
        } for order in orders if isinstance(order, dict)],
        "reconciliation": {
            "attempted": _separation_value(answers, "counseling.attempted", "reconciliation_attempted", "counseling_attempted"),
            "previously_applied": _separation_value(answers, "prior_application.applied", "previously_applied", "previously_applied_for_ecclesiastical_permit"),
            "when": _separation_value(answers, "prior_application.when", "previous_application_date"),
            "where": _separation_value(answers, "prior_application.where", "previous_application_where"),
            "outcome": _separation_value(answers, "prior_application.outcome", "previous_application_outcome"),
        },
        "source": _applicant_submission_source(application),
    }


def _summary_child(value):
    """Return a readable child record without discarding submitted child facts."""
    if isinstance(value, str):
        name = value.strip()
        return {"name": name} if name else None
    if not isinstance(value, dict):
        return None
    first_name = str(value.get("first_name") or value.get("firstName") or "").strip()
    last_name = str(value.get("last_name") or value.get("lastName") or "").strip()
    submitted_name = str(value.get("name") or "").strip()
    name = " ".join(part for part in (first_name, last_name) if part) or submitted_name
    if not name:
        return None
    return {
        "name": name,
        "date_of_birth": value.get("dob") or value.get("date_of_birth"),
        "gender": value.get("gender"),
        "lives_with": value.get("lives_with") or value.get("resides_with"),
    }


def _case_summary(case, application):
    """Case-summary values come only from a filing or a recorded council hearing."""
    answers = _submitted_answers(application)
    grounds = answers.get("grounds") or answers.get("reason") or []
    if isinstance(grounds, str):
        grounds = [grounds]
    children = answers.get("children") or []
    if isinstance(children, str):
        children = [children]
    last_hearing = (
        m.Hearing.objects.filter(agenda__case=case)
        .select_related("agenda__session")
        .order_by("-agenda__session__starts_at", "-created_at", "-id")
        .first()
    )
    filing_source = _applicant_submission_source(application)
    hearing_source = (
        {"kind": "council_record", "record_type": "hearing", "record_id": str(last_hearing.pk)}
        if last_hearing else None
    )
    return {
        "filing_date": filing_source["submitted_at"] if filing_source else None,
        "reason": "; ".join(str(value) for value in grounds if value),
        "children": [child for child in (_summary_child(value) for value in children) if child],
        "last_hearing_date": last_hearing.agenda.session.starts_at.isoformat() if last_hearing and last_hearing.agenda.session.starts_at else None,
        "sources": {
            "filing_date": filing_source,
            "reason": filing_source,
            "children": filing_source,
            "last_hearing_date": hearing_source,
        },
    }


def _application_photo_url(application, category):
    if not application:
        return None
    attachment = application.attachments.filter(category=category).order_by("-created_at", "-id").first()
    if not attachment:
        return None
    photo = attachment.versions.filter(scan_state="clean").order_by("-number").first()
    return f"/api/files/{photo.pk}/?view=1" if photo else None


def _council_party_photo_url(case, party):
    """Return the latest approved council-only portrait for one case party."""
    attachment = (
        case.attachment_set.filter(
            category="CASE_PHOTO", context=str(party.pk), visibility="council"
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if not attachment:
        return None
    photo = attachment.versions.filter(scan_state="clean").order_by("-number").first()
    return f"/api/files/{photo.pk}/?view=1" if photo else None


def _submitted_answers(application):
    if not application:
        return {}
    revision = next(
        (row for row in application.revisions.all() if row.number == application.current_version),
        None,
    )
    return revision.answers if revision else {}


def _council_party_profiles(case, parties):
    """Keep case-detail cards tied to the immutable submitted application answers."""
    applications = list(
        m.Application.objects.filter(
            case=case, kind="petition", submitted_at__isnull=False
        ).prefetch_related("revisions", "attachments__versions").order_by("created_at", "id")
    )
    by_party_id = {app.party_id: app for app in applications if app.party_id}

    result = {}
    for party in parties:
        direct = by_party_id.get(party.pk)
        source = direct or next((app for app in applications if app.party_id != party.pk), None)
        if direct:
            answers, prefix, photo_category = _submitted_answers(direct), "", "PHOTO"
        else:
            answers, prefix, photo_category = _submitted_answers(source), "spouse_", "SPOUSE_PHOTO"
        profile_application = direct or source
        result[party.pk] = {
            "profile": _submitted_party_profile(answers, prefix),
            "photo_url": _council_party_photo_url(case, party)
            or _application_photo_url(profile_application, photo_category),
            "profile_source": _applicant_submission_source(profile_application),
        }
    return result


def _council_case_edits(case):
    """Return the latest council-owned supplement for each editable case card.

    A submitted application is an immutable applicant record.  Council edits are
    therefore stored as versioned findings and projected separately, with their
    author and timestamp retained for the card that displays them.
    """
    proceeding = case.proceedings.filter(status="open").order_by("-sequence", "-id").first()
    if not proceeding:
        return {}
    latest = {}
    rows = (
        m.FindingRevision.objects.filter(
            proceeding=proceeding, fact_code__startswith="case_card."
        )
        .select_related("actor")
        .order_by("fact_code", "-number", "-id")
    )
    for row in rows:
        scope = row.fact_code.removeprefix("case_card.")
        if scope and scope not in latest:
            latest[scope] = {
                "value": row.value,
                "source": {
                    "kind": "council_record",
                    "record_type": "finding",
                    "record_id": str(row.pk),
                    "version": row.number,
                    "actor": f"{row.actor.first_name} {row.actor.last_name}".strip(),
                    "recorded_at": row.created_at.isoformat(),
                },
            }
    return latest


@endpoint(("GET", "DELETE"))
def case_detail(request, case_id):
    if request.method == "DELETE":
        from tribunal.services.admin_purge import purge_case
        purge_case(request.user, case_id)
        return JsonResponse({}, status=204)
    from tribunal.projections import case_capabilities
    case = case_for(request.user, case_id)
    parties = list(case.parties.select_related("person").all().order_by("slot", "id"))
    council_profiles = _council_party_profiles(case, parties) if request.user.role != "applicant" else {}
    marriage_application = (
        m.Application.objects.filter(case=case, kind="petition", submitted_at__isnull=False)
        .prefetch_related("revisions")
        .select_related("party__person")
        .order_by("created_at", "id")
        .first()
    )
    party_data = [encoded(
        p,
        name=p.name,
        slot=p.slot,
        gender=p.person.gender if p.person_id else None,
        is_self=p.account_id == request.user.pk,
        can_receive=p.account_id is not None,
        reference=p.reference if p.account_id == request.user.pk or request.user.role != "applicant" else None,
        **council_profiles.get(p.pk, {}),
    ) for p in parties]
    from django.db import connection
    if request.user.role == "applicant" and connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.ctm_applicant_parties(%s)", [str(case.pk)])
            party_data = cursor.fetchone()[0]
        if isinstance(party_data, str):
            party_data = json.loads(party_data)
    response = JsonResponse(
        encoded(
            case,
            number=case.number,
            status=case.status,
            **case_capabilities(case, request.user),
            can_message=request.user.role in {"applicant", "admin", "secretary"}
            or case.assigned_member_id == request.user.pk,
            parties=party_data,
            marriage=_submitted_marriage(_submitted_answers(marriage_application)),
            marriage_source=_applicant_submission_source(marriage_application),
            separation=_submitted_separation(_submitted_answers(marriage_application), marriage_application, case),
            summary=_case_summary(case, marriage_application),
            proceedings=[
                encoded(p, kind=p.kind, status=p.status, sequence=p.sequence)
                for p in case.proceedings.all()
            ],
            **({"council_edits": _council_case_edits(case)} if request.user.role != "applicant" else {}),
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
            assign_case(request.user, case_id, data["member_id"], data.get("president_id"))
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
                for x in m.Account.objects.filter(
                    is_active=True, role__in=["president", "secretary", "member"]
                ).order_by("created_at")
            ]
        }
    )


@endpoint()
def system_accounts(request):
    from tribunal.pagination import page_records
    from tribunal.services.account_administration import account_data, account_queryset
    administrator(request.user)
    qs=account_queryset()
    for key in ['role','active']:
        if len(request.GET.getlist(key))>1:
            raise ValidationError("Use a single account filter value.")
    role=request.GET.get('role')
    if role is not None:
        if role not in {'applicant','member','president','admin','secretary'}:
            raise ValidationError("Unsupported account role filter.")
        qs=qs.filter(role=role)
    enabled=request.GET.get('active')
    if enabled is not None:
        if enabled not in {'true','false'}:
            raise ValidationError("Use true or false for the active filter.")
        qs=qs.filter(is_active=enabled=='true')
    active_admins=m.Account.objects.filter(role='admin',is_active=True).count()
    return JsonResponse(page_records(qs.order_by('-created_at','-id'),request,
        default_limit=100,serialize=lambda row:account_data(request.user,row,active_admin_count=active_admins)))


@endpoint(("GET", "POST"))
def system_members(request):
    from tribunal.services.member_administration import create_member, member_data, member_queryset
    from tribunal.services.staff_roles import existing_admin
    existing_admin(request.user)
    if request.method == 'GET':
        from tribunal.pagination import page_records
        return JsonResponse(page_records(member_queryset().order_by('-created_at', '-id'), request,
            default_limit=100, serialize=lambda account: member_data(request.user, account)))
    account, membership, grant = create_member(request.user, body(request))
    return JsonResponse({**member_data(request.user, account),
                         'membership_id': str(membership.pk), 'enrollment_role_id': str(grant.pk)}, status=201)


@endpoint(("GET", "POST"))
def system_member(request, account_id):
    from tribunal.services.member_administration import edit_member, member_data, COUNCIL_ROLES
    from tribunal.services.staff_roles import existing_admin
    existing_admin(request.user)
    account = (edit_member(request.user, account_id, body(request)) if request.method == 'POST'
               else m.Account.objects.get(pk=account_id, role__in=COUNCIL_ROLES))
    return JsonResponse(member_data(request.user, account))


@endpoint()
def system_account(request, account_id):
    from tribunal.services.account_administration import account_data
    administrator(request.user)
    return JsonResponse(account_data(request.user,m.Account.objects.get(pk=account_id)))


@endpoint(("POST",))
def system_account_status(request, account_id):
    from tribunal.services.account_administration import account_data
    from tribunal.services.identity import set_account_status
    administrator(request.user)
    data=body(request)
    if set(data)!={'enabled','expected_version'}:
        raise ValidationError("Provide enabled and expected_version only.")
    row=set_account_status(request.user,account_id,data['enabled'],expected_version=filing_version(data))
    return JsonResponse({'account':account_data(request.user,row),
        'revoked_sessions':row.revoked_sessions,'notice_queued':row.notice_queued})


@endpoint()
def system_account_history(request, account_id):
    from tribunal.pagination import page_records
    from tribunal.services.account_administration import status_events
    administrator(request.user)
    m.Account.objects.get(pk=account_id)
    return JsonResponse(page_records(status_events(account_id).order_by('-created_at','-id'),request,
        default_limit=50,serialize=lambda row:encoded(row,action=row.action,
            actor_id=str(row.actor_id) if row.actor_id else None,timestamp=row.created_at.isoformat(),
            before=row.metadata.get('before'),after=row.metadata.get('after'),
            status_version=row.metadata.get('status_version'),
            sessions_revoked=row.metadata.get('sessions_revoked'))))


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
    from tribunal.projections import session_data
    staff(request.user)
    if request.method == "GET":
        from tribunal.pagination import page_records
        qs = m.CouncilSession.objects.select_related("presiding_member").annotate(
            assigned_case_count=Count("agenda", filter=Q(agenda__part=1)),
            hearing_case_count=Count("agenda", filter=Q(agenda__part=2)),
        )
        filters = {}
        for key in ("state", "date_from", "date_to"):
            if key not in request.GET:
                continue
            raw = request.GET.get(key)
            if len(request.GET.getlist(key)) != 1 or not raw:
                raise ValidationError(f"Provide one nonempty {key} filter.")
            if key == "state":
                if raw not in {"draft", "planned", "closed"}:
                    raise ValidationError("state must be draft, planned, or closed.")
                qs = qs.filter(state=raw)
            else:
                try:
                    parsed = date.fromisoformat(raw)
                    if parsed.isoformat() != raw:
                        raise ValueError
                except ValueError:
                    raise ValidationError(f"{key} must be a YYYY-MM-DD date.")
                filters[key] = parsed
        if filters.get("date_from", date.min) > filters.get("date_to", date.max):
            raise ValidationError("date_from must not follow date_to.")
        if "date_from" in filters:
            qs = qs.filter(date__gte=filters["date_from"])
        if "date_to" in filters:
            qs = qs.filter(date__lte=filters["date_to"])
        return JsonResponse(page_records(
            qs.order_by("-date", "-id"), request, default_limit=100,
            serialize=lambda x: encoded(x, **session_data(x, request.user)),
        ))
    from tribunal.services.council import create_session

    data = body(request)
    # The active president is configured centrally; session payloads cannot override it.
    starts_at = datetime.fromisoformat(data["starts_at"]) if data.get("starts_at") else None
    session = create_session(
        request.user,
        date.fromisoformat(data["date"]),
        starts_at=starts_at,
        location=data.get("location", ""),
        state="draft",
    )
    return JsonResponse(encoded(session, **session_data(session, request.user)), status=201)


@endpoint(("PATCH", "DELETE"))
def update_session(request, session_id):
    from tribunal.projections import session_data
    if request.method == "DELETE":
        from tribunal.services.council import delete_draft_session
        delete_draft_session(request.user, session_id)
        return JsonResponse({}, status=204)
    from tribunal.services.council import update_session as command

    data = body(request)
    session = command(
        request.user, session_id, date.fromisoformat(data["date"]),
        starts_at=datetime.fromisoformat(data["starts_at"]),
        location=data.get("location", ""),
    )
    return JsonResponse(encoded(session, **session_data(session, request.user)))


@endpoint(("GET", "POST"))
def agenda(request, session_id):
    from tribunal.projections import agenda_item_data, session_data
    from tribunal.services.council import attendance_for
    staff(request.user)
    if request.method == "GET":
        session = m.CouncilSession.objects.select_related("presiding_member").get(pk=session_id)
        return JsonResponse(
            {
                "session": encoded(session, **session_data(session, request.user)),
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
def transfer_agenda(request, item_id):
    from tribunal.projections import agenda_item_data
    from tribunal.services.council import attendance_for, transfer_agenda_item

    data = body(request)
    target_session_id = data.get("target_session_id")
    if not target_session_id:
        raise ValidationError("A destination tribunal session is required.")
    item = transfer_agenda_item(request.user, item_id, target_session_id, data.get("reason", ""))
    return JsonResponse(
        encoded(item, **agenda_item_data(item, request.user, attendance_for(request.user, item.session_id))),
        status=201,
    )


@endpoint(("POST",))
def close_session(request, session_id):
    from tribunal.services.council import close_session as command

    return JsonResponse(encoded(command(request.user, session_id)))


@endpoint(("POST",))
def activate_session(request, session_id):
    from tribunal.projections import session_data
    from tribunal.services.council import activate_session as command

    session = command(request.user, session_id)
    return JsonResponse(encoded(session, **session_data(session, request.user)))


@endpoint(("POST",))
def return_session_to_planned(request, session_id):
    from tribunal.projections import session_data
    from tribunal.services.council import return_session_to_planned as command

    session = command(request.user, session_id)
    return JsonResponse(encoded(session, **session_data(session, request.user)))


@endpoint(("POST",))
def adjourn_session(request, session_id):
    from tribunal.projections import session_data
    from tribunal.services.council import set_session_adjourned

    data = body(request)
    adjourned = data.get("adjourned")
    ended_at_text = data.get("ended_at")
    if not isinstance(adjourned, bool):
        raise ValidationError("Adjourned must be true or false.")
    if not isinstance(ended_at_text, str):
        raise ValidationError("Session end time is required.")
    try:
        ended_at = datetime.fromisoformat(ended_at_text)
    except ValueError as error:
        raise ValidationError("Session end time must be a valid timestamp.") from error
    session = set_session_adjourned(request.user, session_id, adjourned, ended_at)
    return JsonResponse(encoded(session, **session_data(session, request.user)))


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
    from tribunal.services.council import attendance_for, attendance_roster_for, record_attendance

    staff(request.user)
    if request.method == "GET":
        hearing_id = request.GET.get("hearing_id") or None
        if hearing_id:
            roster = attendance_roster_for(request.user, session_id, hearing_id)
            return JsonResponse(
                {
                    "items": [
                        {
                            "member_id": str(member.pk),
                            "member_name": f"{member.first_name} {member.last_name}".strip(),
                            "member_role": member.role,
                            "member_active": member.is_active,
                            "present": row.present if row else None,
                            "actor_id": str(row.actor_id) if row else None,
                            "timestamp": row.created_at.isoformat() if row else None,
                        }
                        for member, row in roster
                    ]
                }
            )
        rows = attendance_for(request.user, session_id)
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
    from tribunal.services.communications import messages_for, send_message, message_receipts

    if request.method == "GET":
        offset = int(request.GET.get("offset", 0))
        if not 0 <= offset <= 2**63-52:
            raise ValidationError("Message offset is outside the supported range.")
        rows = list(messages_for(request.user, case_id).order_by("created_at", "id")[offset:offset+51])
        from tribunal.services.message_projection import message_sender_names
        sender_names = message_sender_names(rows[:50])
        return JsonResponse(
            {
                "items": [
                    encoded(
                        x,
                        body=x.body,
                        sender=sender_names.get(str(x.pk)),
                        channel=x.channel,
                        timestamp=x.created_at.isoformat(),
                        file_links=x.file_links,
                        receipts=message_receipts(request.user, x),
                        idempotency_key=x.idempotency_key if x.sender_id == request.user.pk else None,
                    )
                    for x in rows[:50]
                ], "next_offset": offset+50 if len(rows)>50 else None,
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
                idempotency_key=data.get("idempotency_key"),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def message_acknowledge(request, message_id):
    from tribunal.services.communications import acknowledge_message
    row = acknowledge_message(request.user, message_id)
    return JsonResponse({"id": str(message_id), "read_at": row.read_at.isoformat()})


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
        from tribunal.services.request_projection import request_author_names, external_link_metadata
        projection_time = timezone.now()
        rows = list(qs.select_related("subject", "case", "proceeding").order_by("-created_at", "-id"))
        author_names = request_author_names(rows)
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
                        author=author_names.get(str(x.pk)),
                        **release_metadata(x, request.user),
                        **({"request_version": request_version(x),
                            **external_link_metadata(x, request.user, now=projection_time)}
                            if request.user.role != "applicant" else {}),
                        **(own_request_data(x, request.user) if request.user.role == "applicant" else {}),
                    )
                    for x in rows
                ]
            }
        )
    from tribunal.services.reports import create_request

    data = body(request)
    party_ids = data.get("party_ids")
    if party_ids is not None:
        if not isinstance(party_ids, list) or not party_ids or len(party_ids) > 2:
            raise ValidationError("Provide one or two distinct report recipients.")
        if "party_id" in data or len({str(value) for value in party_ids}) != len(party_ids):
            raise ValidationError("Provide distinct report recipients.")
        from django.db import transaction

        with transaction.atomic():
            created = [
                create_request(
                    request.user, data["proceeding_id"], party_id, data["kind"], data["title"],
                    data.get("questions", []), data.get("instructions", ""),
                    data.get("language", "en"), data.get("parent_id"),
                )
                for party_id in party_ids
            ]
        return JsonResponse({"items": [encoded(row) for row in created]}, status=201)
    return JsonResponse(encoded(create_request(
        request.user, data["proceeding_id"], data["party_id"], data["kind"], data["title"],
        data.get("questions", []), data.get("instructions", ""), data.get("language", "en"),
        data.get("parent_id"),
    )), status=201)


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


@endpoint()
def print_priest_request(request, request_id):
    from tribunal.services.priest_print import printable_priest_request
    response = render(request, 'tribunal/priest_request_print.html',
                      printable_priest_request(request.user, request_id))
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = (
        "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'")
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
                **({"completed_by": (f"{report.author.first_name} {report.author.last_name}".strip() if report.author else report.request.external_name or None),
                    "intake_by": (f"{report.author.first_name} {report.author.last_name}".strip() if report.author and report.author.role in {"admin", "secretary", "president", "member"} else None),
                    "author_id": str(report.author_id) if report.author_id else None,
                    "author": f"{report.author.first_name} {report.author.last_name}".strip() if report.author else None,
                    "submitted_at": report.created_at.isoformat(), "method": report.method,
                    "can_revise": bool(report.method not in {"paper", "recording"} and report.author_id == request.user.pk and report.author
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
        from django.db.models import OuterRef, Exists
        later = m.NoteRevision.objects.filter(note_id=OuterRef("note_id"), number__gt=OuterRef("number"))
        return JsonResponse(
            {
                "items": [
                    encoded(x, note_id=str(x.note_id), version=x.number, text=x.text,
                            author_id=str(x.note.author_id),
                            author=f"{x.note.author.first_name} {x.note.author.last_name}".strip(),
                            timestamp=x.created_at.isoformat(),
                            current=not x.has_later,
                            can_edit=bool(not x.has_later and x.note.author_id == request.user.pk
                                and proceeding.status == "open" and proceeding.case.status == "open"
                                and (request.user.role in {"admin", "secretary"} or proceeding.case.assigned_member_id == request.user.pk)))
                    for x in m.NoteRevision.objects.filter(
                        note__proceeding=proceeding
                    ).annotate(has_later=Exists(later)).select_related("note__author").order_by("created_at", "id")
                ]
            }
        )
    from tribunal.services.council import save_note

    data = body(request)
    row = save_note(request.user, proceeding_id, data["text"], data.get("note_id"), **optional_version(data))
    return JsonResponse(encoded(row, version=row.saved_version), status=201)


@endpoint(("GET", "POST"))
def decision(request, proceeding_id):
    staff(request.user)
    if request.method == "GET":
        from tribunal.projections import decision_data

        proceeding = m.Proceeding.objects.get(pk=proceeding_id)
        rows = list(m.DecisionRevision.objects.filter(proceeding=proceeding).select_related("actor", "proceeding__case").order_by("-number"))
        can_record = proceeding.status == "open" and proceeding.case.status == "open" and (
            request.user.role in {"admin", "secretary"} or proceeding.case.assigned_member_id == request.user.pk)
        return JsonResponse({"current_version": rows[0].number if rows else 0, "can_record": can_record,
                             "items": [decision_data(row, request.user)
                             for row in rows]})
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
                **optional_version(data),
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
            cast_vote(request.user, decision_id, data["choice"], data.get("member_id"), idempotency_key=data.get("idempotency_key"))
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
    from tribunal.pagination import page_records
    from tribunal.services.filing_privacy import audit_visible
    staff(request.user)
    case = case_for(request.user, case_id)
    return JsonResponse(page_records(
        m.AuditEvent.objects.filter(case=case).order_by("-created_at", "-id"), request,
        default_limit=250, visible=audit_visible,
        serialize=lambda x: encoded(x, action=x.action, timestamp=x.created_at.isoformat(),
            source=x.source, source_id=str(x.source_id),
            actor=str(x.actor_id) if x.actor_id else None),
    ))


@endpoint()
def system_audit(request):
    from tribunal.pagination import page_records
    from tribunal.services.filing_privacy import audit_visible
    administrator(request.user)
    return JsonResponse(page_records(
        m.AuditEvent.objects.order_by("-created_at", "-id"), request,
        default_limit=250, visible=audit_visible,
        serialize=lambda x: encoded(x, action=x.action, source=x.source,
                                    timestamp=x.created_at.isoformat()),
    ))


@csrf_exempt
@vary_on_headers("Accept", "Authorization")
def external_report(request, request_id):
    from tribunal.services.reports import external_request, complete_external, lock_request
    from tribunal.db.context import database_external
    from django.db import transaction

    # Browser navigation carries the capability only in its fragment. The existing
    # council page removes it before fetching this route with a Bearer header.
    # Do not inspect request existence or redirect query/header credentials.
    if (request.method == "GET" and "Authorization" not in request.headers
            and request.get_preferred_type(["application/json", "text/html"]) == "text/html"):
        from django.templatetags.static import static
        return HttpResponseRedirect(static("ctm/external-report.html"))
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
    from tribunal.services.configuration import save_setting, safe_configuration
    from tribunal.services.setting_schemas import validate_setting_value, schema_descriptors
    administrator(request.user)
    if request.method == "GET":
        current = {}
        for record in m.SettingRevision.objects.order_by("key", "-number"):
            if record.key in current:
                continue
            from tribunal.validation import validate_json_value
            from tribunal.services.setting_schemas import schemas
            value = record.value
            if record.key not in schemas():
                value, state = None, "unsupported_legacy_key"
            else:
                try:
                    validate_json_value(value, maximum=100_000)
                    safe_configuration(value)
                except ValidationError:
                    value, state = None, "unsafe_legacy_value"
                else:
                    try:
                        validate_setting_value(record.key, value)
                        state = "valid"
                    except ValidationError:
                        state = "legacy_requires_review"
            current[record.key] = encoded(record, key=record.key, version=record.number,
                value=value, schema_version=1, validation_state=state)
        return JsonResponse({"items": list(current.values()),
            "schemas": schema_descriptors({key:row["version"] for key,row in current.items()})})
    data = body(request)
    if (set(data)-{"key", "value", "expected_version", "schema_version"}
            or not {"key", "value", "expected_version"} <= set(data)):
        raise ValidationError("Provide key, value and expected_version using the declared setting write fields.")
    row = save_setting(request.user, data["key"], data["value"],
        expected_version=filing_version(data), schema_version=data.get("schema_version", 1))
    return JsonResponse(encoded(row, version=row.number, schema_version=1), status=201)


@endpoint()
def runtime_tribunal_contact(request):
    from tribunal.services.runtime_settings import tribunal_contact

    response = JsonResponse(tribunal_contact(request.user))
    response["Cache-Control"] = "private, no-store"
    return response


@endpoint()
def runtime_recommended_doctors(request, case_id):
    from tribunal.services.runtime_settings import recommended_doctors

    staff(request.user)
    specialties = request.GET.getlist("specialty")
    if len(specialties) != 1 or set(request.GET) != {"specialty"}:
        raise ValidationError("Provide one specialty query parameter.")
    response = JsonResponse(
        recommended_doctors(request.user, case_id, specialties[0])
    )
    response["Cache-Control"] = "private, no-store"
    return response


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
            "name": f"{user.first_name} {user.last_name}".strip(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "ui_language": user.ui_language,
            "notification_language": user.notification_language,
            "email": user.email,
            "role": user.role,
            "portal": "applicant" if user.role == "applicant" else "council",
        }
    )


@endpoint()
def account_activity(request):
    from tribunal.pagination import page_records
    return JsonResponse(page_records(
        m.AuditEvent.objects.filter(actor=request.user).order_by("-created_at", "-id"), request,
        default_limit=20,
        serialize=lambda row: encoded(row, action=row.action.replace("_", " "), timestamp=row.created_at.isoformat()),
    ))


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
                        direction=x.direction,
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
                data.get("direction", "sent"),
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
    from tribunal.services.reports import revise_report, require_report_disclosure

    if request.method == "GET":
        staff(request.user)
        report = m.Report.objects.select_related("request__subject").get(pk=report_id)
        case_for(request.user, report.request.case_id)
        require_report_disclosure(report.request)
        rows = list(report.revisions.select_related("actor").order_by("-number"))
        can_revise = (report.author_id == request.user.pk and request.user.role != "applicant"
                      and report.request.proceeding.status == "open" and report.request.case.status == "open"
                      and (request.user.role in {"admin", "secretary"}
                           or report.request.case.assigned_member_id == request.user.pk))
        return JsonResponse(
            {
                "current_version": rows[0].number if rows else 0,
                "can_revise": can_revise,
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
                    for row in rows
                ]
            }
        )

    data = body(request)
    row = revise_report(
        request.user, report_id, data["answers"], data.get("observations", ""),
        expected_version=filing_version(data),
    )
    return JsonResponse(encoded(row, version=row.number), status=201)


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
                **optional_version(data),
            )
        ),
        status=201,
    )


@endpoint(("POST",))
def historical_stage(request):
    from tribunal.services.historical import stage

    data = body(request)
    row = stage(request.user, data["payload"], data.get("workspace_id"), **optional_version(data))
    return JsonResponse(encoded(row, version=row.version), status=201)


@endpoint()
def historical_detail(request, workspace_id):
    administrator(request.user)
    if request.user.role != "admin":
        raise PermissionDenied("Historical workspaces belong to their original administrator.")
    row = m.HistoricalWorkspace.objects.get(pk=workspace_id, actor=request.user)
    return JsonResponse(encoded(row, version=row.version, payload=row.payload,
        finalized_case_id=str(row.finalized_case_id) if row.finalized_case_id else None))


@endpoint()
def delivery_status(request):
    from tribunal.services.queue import queue_status
    return JsonResponse(queue_status(request.user, state=request.GET.get("state"), offset=int(request.GET.get("offset", "0"))))


@endpoint(("POST",))
def delivery_retry(request, event_id):
    from tribunal.services.queue import retry_delivery
    try:
        row = retry_delivery(request.user, event_id, body(request).get("expected_attempts"))
    except VersionConflict as exc:
        return JsonResponse({"error": "attempt_conflict", "current_attempts": exc.current_version}, status=409)
    return JsonResponse(encoded(row, attempts=row.attempts, queued=True))


@endpoint(("POST",))
def historical_publish(request, workspace_id):
    from tribunal.services.historical import publish

    case = publish(request.user, workspace_id, **optional_version(body(request)))
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


@endpoint()
def account_sessions(request):
    from tribunal.pagination import page_records
    from tribunal.services.account_sessions import active_sessions, owned_session, session_handle
    return JsonResponse(page_records(
        active_sessions(), request, default_limit=50,
        visible=lambda row: owned_session(request.user, row),
        serialize=lambda row: {
            "handle": session_handle(request.user, row.session_key),
            "current": row.session_key == request.session.session_key,
            "expires_at": row.expire_date.isoformat(),
        },
    ))


@endpoint(("POST",))
def account_session_revoke(request, handle):
    from tribunal.services.account_sessions import revoke_session
    if body(request):
        raise ValidationError("Session revocation accepts an empty object only.")
    return JsonResponse(revoke_session(request.user, handle, request.session.session_key))


@endpoint()
def system_account_memberships(request, account_id):
    from tribunal.pagination import page_records
    from tribunal.services.member_history import membership_data
    administrator(request.user)
    account = m.Account.objects.exclude(role="applicant").get(pk=account_id)
    now = timezone.now()
    result = page_records(
        m.StaffMembership.objects.filter(account=account).select_related("tribunal")
        .order_by("-active_from", "-id"), request, default_limit=50,
        serialize=lambda row: membership_data(account, row, now),
    )
    return JsonResponse({"account_id": str(account.pk), "account_role": account.role,
                         "account_active": account.is_active, **result})


@endpoint()
def system_account_role_history(request, account_id):
    from tribunal.pagination import page_records
    from tribunal.services.member_history import role_history, role_data
    administrator(request.user)
    account = m.Account.objects.exclude(role="applicant").get(pk=account_id)
    now = timezone.now()
    result = page_records(role_history(account), request, default_limit=50,
                          serialize=lambda row: role_data(account, row, now))
    return JsonResponse({"account_id": str(account.pk), "account_role": account.role,
                         "account_active": account.is_active, **result})


@csrf_exempt
@vary_on_headers("Authorization")
def external_report_status(request, request_id):
    from tribunal.services.reports import external_status_receipt
    if request.method != 'GET':
        return JsonResponse({'error':'method_not_allowed'}, status=405)
    authorization = request.headers.get('Authorization','')
    token = authorization[len('Bearer '):] if authorization.startswith('Bearer ') else ''
    try:
        return JsonResponse(external_status_receipt(request_id, token))
    except (PermissionDenied, ValidationError, ObjectDoesNotExist):
        return JsonResponse({'error':'link_unavailable'}, status=403)


@endpoint(("POST",))
def complete_paper_report_request(request, request_id):
    from tribunal.services.reports import complete_external_paper
    data = body(request)
    return JsonResponse(encoded(complete_external_paper(request.user, request_id,
        data.get('file_id'), data.get('completion_date'), expected_version=data.get('expected_version'))), status=201)
