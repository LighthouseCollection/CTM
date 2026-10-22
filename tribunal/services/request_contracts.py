"""Own report requests: explicit concurrency, consent and recovery contracts."""

import hashlib
import json
from django.core.exceptions import PermissionDenied, ValidationError
from tribunal import models as m
from tribunal.policy import active


ASSESSMENTS = {"medical", "psychological"}


def own_request(actor, request):
    active(actor)
    if (actor.role != "applicant" or request.subject.account_id != actor.pk
            or request.kind in {"interview", "external_priest"} or not request.sent_at):
        raise PermissionDenied("This is not your sent request.")


def request_version(request):
    # State is separate: a completed request retains the submitted identity for recovery.
    data = [str(request.pk), str(request.proceeding_id), str(request.subject_id),
            request.kind, request.language, request.title, request.instructions,
            request.questions, request.sent_at.isoformat() if request.sent_at else None]
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def check_request_version(request, expected_version):
    if not isinstance(expected_version, str) or expected_version != request_version(request):
        raise ValidationError("Request changed. Reload the request before continuing.")


def release_definition():
    definition = m.QuestionnaireVersion.objects.filter(
        purpose="medical_release", published=True).order_by("-number").first()
    if not definition or not definition.declaration_en.strip() or not definition.declaration_ar.strip():
        return None
    return definition


def request_open(request):
    return bool(request.state == "sent" and request.sent_at
                and request.proceeding.status == "open" and request.case.status == "open")


def own_request_data(request, actor):
    own_request(actor, request)
    assessment = request.kind in ASSESSMENTS
    definition = release_definition() if assessment else None
    releases = list(m.MedicalRelease.objects.filter(request=request, subject=actor).order_by("signed_at", "id"))
    signed = [row for row in releases if row.scope.get("council") is True]
    release = signed[-1] if signed else None
    report = m.Report.objects.filter(request=request, author=actor).first()
    return {
        "request_version": request_version(request), "proceeding_id": str(request.proceeding_id),
        "can_respond": bool(request_open(request) and (not assessment or release)),
        "can_upload": request_open(request),
        "can_sign_release": bool(request_open(request) and assessment and definition and not releases),
        "release_status": "signed" if release else "out_of_scope" if releases else "none",
        "release_definition": ({"id": str(definition.pk), "version": definition.number,
            "definition": definition.definition, "declaration_en": definition.declaration_en,
            "declaration_ar": definition.declaration_ar} if definition else None),
        "signed_releases": [{"id": str(row.pk), "declaration_id": str(row.declaration_id),
            "signature_file_id": str(row.signature_id), "scope": row.scope,
            "signed_at": row.signed_at.isoformat()} for row in releases],
        "response": ({"id": str(report.pk), "submitted_at": report.created_at.isoformat(),
            "version": 1} if report else None),
    }
