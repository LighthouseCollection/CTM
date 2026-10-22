"""Meilisearch is only a candidate finder; source authorization is always reapplied."""

import os
import requests
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from tribunal.models import FileVersion, DocumentText
from tribunal.policy import staff
from .files import authorized_file
from .filing_privacy import file_visible


def excluded_assessment(file):
    attachment = file.attachment
    return attachment.visibility == "medical" or bool(
        attachment.report_request_id and attachment.report_request.kind in {"medical", "psychological"}
    )


def search(actor, query, include_history=False, case_id=None):
    staff(actor)
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 200:
        raise ValidationError("Use a search phrase of2–200characters.")
    url = os.environ.get("MEILI_URL", "").rstrip("/")
    key = os.environ.get("MEILI_MASTER_KEY", "")
    if not url or not key:
        raise ValidationError("Search engine is not configured.")
    try:
        response = requests.post(
            url + "/indexes/ctm_documents/search",
            headers={"Authorization": "Bearer " + key},
            json={"q": query, "limit": 100, "attributesToRetrieve": ["file_id"]},
            timeout=10,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])
    except (requests.RequestException, ValueError):
        raise ValidationError(
            "Search is temporarily unavailable; source documents are unchanged."
        )
    results = []
    seen = set()
    for hit in hits:
        try:
            file = authorized_file(actor, hit["file_id"])
        except (PermissionDenied, ObjectDoesNotExist, ValueError, KeyError):
            continue
        if excluded_assessment(file):
            continue
        if case_id and str(file.attachment.case_id) != str(case_id):
            continue
        if (
            not include_history
            and (not file_visible(file, current=True) or any(
                file_visible(later, current=True)
                for later in file.attachment.versions.filter(number__gt=file.number)
            ))
        ):
            continue
        if file.pk in seen:
            continue
        seen.add(file.pk)
        # Snippet comes from the source-authorized derivative, never a cached raw hit.
        derivative = (
            DocumentText.objects.filter(file=file).order_by("-created_at").first()
        )
        results.append(
            {
                "file_id": str(file.pk),
                "case_id": str(file.attachment.case_id),
                "name": file.display_name,
                "snippet": derivative.text[:300] if derivative else "",
            }
        )
    return {"items": results, "returned_count": len(results)}


def index_text(derivative):
    file = derivative.file
    if excluded_assessment(file):
        return None
    url = os.environ.get("MEILI_URL", "").rstrip("/")
    key = os.environ.get("MEILI_MASTER_KEY", "")
    if not url or not key:
        raise ValidationError("Search engine is not configured.")
    # Applicant drafts are not published into council search.
    app = file.attachment.application
    if app and (not app.submitted_at or not file_visible(file)):
        return None
    headers = {"Authorization": "Bearer " + key}
    response = requests.post(
        url + "/indexes/ctm_documents/documents",
        headers=headers,
        json=[
            {
                "id": str(derivative.pk),
                "file_id": str(file.pk),
                "text": derivative.text,
                "case_id": str(file.attachment.case_id),
            }
        ],
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
