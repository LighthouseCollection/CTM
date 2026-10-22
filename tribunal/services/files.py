"""Private original storage with automatic technical safety gate; no public MEDIA_URL."""

import hashlib
import io
import os
import socket
import struct
import uuid
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from tribunal.models import (
    Attachment,
    FileVersion,
    FileTechnicalEvent,
    MedicalRelease,
    DecreeRelease,
    Decree,
)
from tribunal.policy import active, application_for, case_for, open_proceeding, writer
from .applications import safe_file
from .common import audit, notify_manager
from .closed_filings import council_filing


def validate_category(category, mime):
    images = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    documents = images | {"application/pdf"}
    allowed = {
        "PHOTO": images,
        "SPOUSE_PHOTO": images,
        "MC": documents,
        "CMC": documents,
        "CDD": documents,
        "RO": documents,
        "PET": {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    }
    if category in allowed and mime not in allowed[category]:
        raise ValidationError(f"Invalid file format for {category}.")


def write_private_original(path, data):
    # Explicit permissions apply to service writes, independent of web-upload settings.
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        os.chmod(path.parent, 0o700)
    staging = path.with_name(path.name + ".staging-" + uuid.uuid4().hex)
    try:
        descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def identify(data):
    head = data[:64]
    if head.startswith(b"%PDF-"):
        return "application/pdf", "pdf", 25
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png", 25
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg", 25
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", "gif", 25
    if head.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp", "webp", 25
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" in z.namelist():
                    return (
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "docx",
                        25,
                    )
        except zipfile.BadZipFile:
            pass
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "application/msword", "doc", 25
    if head.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        return "audio/mpeg", "mp3", 100
    if head.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "audio/wav", "wav", 100
    if head.startswith(b"OggS"):
        return "audio/ogg", "ogg", 100
    if data[4:8] == b"ftyp":
        return "video/mp4", "mp4", 500
    if head.startswith(b"\x1aE\xdf\xa3"):
        return "video/webm", "webm", 500
    raise ValidationError("Unsupported file format or invalid file signature.")


def scan(data):
    if not settings.CTM_SCAN_REQUIRED:
        return "clean"
    if not settings.CLAMAV_HOST:
        return "pending"
    try:
        with socket.create_connection(
            (settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=30
        ) as sock:
            sock.sendall(b"zINSTREAM\0")
            for offset in range(0, len(data), 65536):
                chunk = data[offset : offset + 65536]
                sock.sendall(struct.pack("!I", len(chunk)) + chunk)
            sock.sendall(b"\0\0\0\0")
            result = sock.recv(4096)
        return "clean" if result.rstrip(b"\0\n").endswith(b": OK") else "rejected"
    except (OSError, socket.timeout):
        return "pending"


def private_path(key):
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise PermissionDenied("Invalid file object key.")
    return path


def display_filename(file):
    attachment = file.attachment
    case = attachment.case or (
        attachment.application.case if attachment.application else None
    )
    if not case:
        return file.display_name
    stamp = file.created_at.astimezone(ZoneInfo("America/Los_Angeles")).strftime(
        "%Y%m%d-%H%M"
    )
    suffix = Path(file.object_key).suffix
    return f"{case.number}-{attachment.category}-{stamp}{suffix}"


@transaction.atomic
def upload(
    actor,
    uploaded,
    category,
    app_id=None,
    case_id=None,
    attachment_id=None,
    context="",
    visibility="own",
    request_id=None,
    expected_request_version=None,
):
    active(actor)
    if not category or not category.replace("_", "").isalnum() or len(category) > 30:
        raise ValidationError("Invalid document category code.")
    app = None
    case = None
    proceeding = None
    request = None
    if request_id:
        from tribunal.models import ReportRequest

        from .reports import lock_request
        from .request_contracts import own_request, check_request_version

        request = lock_request(request_id)
        if actor.role == "applicant":
            own_request(actor, request)
            check_request_version(request, expected_request_version)
        else:
            writer(actor, request.case)
        open_proceeding(request.proceeding)
        if request.state != "sent":
            raise ValidationError("Report request is not accepting uploads.")
        if category == "CONSENT":
            if request.kind not in {"medical", "psychological"}:
                raise ValidationError("Consent files belong to assessment requests.")
            if MedicalRelease.objects.filter(request=request).exists():
                raise ValidationError("The signed disclosure original is retained.")
        case = request.case
        proceeding = request.proceeding
        if request.kind in {"external_priest", "interview"}:
            owner, visibility = None, "council"
        else:
            owner = request.subject.account
            visibility = "medical" if request.kind in {"medical", "psychological"} else "own"
    elif app_id:
        app = application_for(actor, app_id)
        from tribunal.models import Application, Case

        if app.owner_id == actor.pk or actor.role in {"admin", "secretary"}:
            app = Application.objects.select_for_update(of=("self",)).get(pk=app.pk)
        if app.case_id:
            # Managers may correct files without permission to UPDATE the application.
            # Case locking serializes those corrections with closure and reassignment.
            Case.objects.select_for_update(of=("self",)).get(pk=app.case_id)
            app = Application.objects.get(pk=app.pk)
        if app.owner_id != actor.pk:
            writer(actor, app.case)
        case = app.case
        proceeding = app.proceeding
        if app.status in {"withdrawn", "expired", "deleted", "declined"}:
            raise ValidationError("Application is no longer accepting documents.")
        if app.submitted_at and not council_filing(app):
            open_proceeding(proceeding)
        if council_filing(app) and app.status not in {"draft", "submitted"}:
            raise ValidationError("Appeal is not pending.")
        owner = app.owner
        if actor.role == "applicant" and visibility != "own":
            raise PermissionDenied("Application documents must use ordinary owner visibility.")
    else:
        case = case_for(actor, case_id, write=True)
        if case.status != "open":
            raise ValidationError("Closed case cannot accept ordinary uploads.")
        proceeding = case.proceedings.get(status="open")
        owner = None
        visibility = "council" if visibility == "own" else visibility
    if visibility not in {"own", "council", "medical"} or (
        actor.role == "applicant" and visibility == "council"
    ):
        raise PermissionDenied("Invalid file visibility.")
    if uploaded.size > 500 * 1024 * 1024:
        raise ValidationError("Ordinary attachment exceeds500MB.")
    data = uploaded.read()
    mime, extension, limit = identify(data)
    validate_category(category, mime)
    if len(data) > limit * 1024 * 1024:
        raise ValidationError(f"This file type has a {limit}MB limit.")
    if attachment_id:
        attachment = Attachment.objects.select_for_update(of=("self",)).get(
            pk=attachment_id
        )
        if (
            attachment.application_id != (app.pk if app else None)
            or attachment.case_id != (case.pk if case else None)
            or attachment.category != category
            or attachment.context != context
            or attachment.visibility != visibility
            or attachment.report_request_id != (request.pk if request else None)
        ):
            raise PermissionDenied("Replacement belongs to a different context.")
        if actor.role == "applicant" and attachment.owner_id != actor.pk:
            raise PermissionDenied("Not your attachment.")
    else:
        attachment = Attachment.objects.create(
            application=app,
            case=case,
            proceeding=proceeding,
            owner=owner,
            category=category,
            context=context,
            visibility=visibility,
            report_request=request,
        )
    number = (
        attachment.versions.order_by("-number").values_list("number", flat=True).first()
        or 0
    ) + 1
    key = f"originals/{uuid.uuid4().hex}.{extension}"
    path = private_path(key)
    state = scan(data)
    if state == "rejected":
        raise ValidationError("File failed automatic safety validation.")
    stamp = (
        timezone.now()
        .astimezone(ZoneInfo("America/Los_Angeles"))
        .strftime("%Y%m%d-%H%M")
    )
    display = f"{case.number if case else 'draft'}-{category}-{stamp}.{extension}"
    file = FileVersion.objects.create(
        attachment=attachment,
        number=number,
        object_key=key,
        original_name=Path(uploaded.name).name[:250],
        display_name=display,
        mime_type=mime,
        byte_count=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        actor=actor,
        scan_state=state,
    )
    # The on-commit write cannot publish uncommitted bytes. Pending scans are never downloadable.
    transaction.on_commit(lambda: write_private_original(path, data))
    FileTechnicalEvent.objects.create(file=file, task="scan", result=state)
    audit(actor, "file_uploaded", file, case, metadata={"category": category})
    if app and app.submitted_at and app.status != "returned" and actor.pk == app.owner_id:
        notify_manager(case, "file_uploaded", file, digest=True)
    return file


def application_file_listing(actor, app_id):
    """Owner-only current ordinary originals, including honest pending scan state."""
    from .applications import document_requirements

    app = application_for(actor, app_id)
    if actor.role != "applicant" or app.owner_id != actor.pk:
        raise PermissionDenied("Only the filing applicant can list draft documents.")
    can_upload = app.status not in {"withdrawn", "expired", "deleted", "declined"}
    if council_filing(app):
        can_upload = can_upload and app.status in {"draft", "submitted"}
    elif app.submitted_at:
        can_upload = bool(can_upload and app.proceeding and app.proceeding.status == "open"
                          and app.case.status == "open")
    items = []
    for attachment in app.attachments.filter(
        owner=actor, visibility="own", report_request__isnull=True
    ).order_by("created_at", "pk"):
        file = attachment.versions.order_by("-number").first()
        if not file or Decree.objects.filter(signed_file=file).exists():
            continue
        event = file.technical_events.filter(task="scan").order_by("-created_at", "-id").first()
        state = event.result if event and event.result in {"clean", "pending", "rejected"} else "pending"
        item = {"id": str(file.pk), "attachment_id": str(attachment.pk),
                "category": attachment.category, "context": attachment.context,
                "name": display_filename(file), "scan_state": state}
        if state == "clean":
            authorized_file(actor, file.pk)
            item["download_url"] = f"/api/files/{file.pk}/"
        items.append(item)
    revision = app.revisions.filter(number=app.current_version).first()
    return {"can_upload": can_upload, "items": items,
            "requirements": document_requirements(app, revision.answers if revision else {})}


def request_file_listing(actor, request_id):
    from tribunal.models import ReportRequest
    from .request_contracts import own_request, request_version, request_open

    request = ReportRequest.objects.select_related("case", "proceeding", "subject").get(pk=request_id)
    own_request(actor, request)
    items = []
    for attachment in Attachment.objects.filter(report_request=request, owner=actor,
            case=request.case, proceeding=request.proceeding).exclude(visibility="council").order_by("created_at", "id"):
        file = attachment.versions.order_by("-number").first()
        if not file:
            continue
        event = file.technical_events.filter(task="scan").order_by("-created_at", "-id").first()
        state = event.result if event and event.result in {"clean", "pending", "rejected"} else "pending"
        row = {"id": str(file.pk), "attachment_id": str(attachment.pk),
               "category": attachment.category, "purpose": "consent" if attachment.category == "CONSENT" else "report",
               "name": display_filename(file), "version": file.number, "scan_state": state}
        if state == "clean":
            authorized_file(actor, file.pk)
            row["download_url"] = f"/api/files/{file.pk}/"
        items.append(row)
    return {"request_id": str(request.pk), "proceeding_id": str(request.proceeding_id),
            "request_version": request_version(request), "can_upload": request_open(request), "items": items}


def authorized_file(actor, file_id, *, require_safe=True):
    active(actor)
    file = FileVersion.objects.select_related(
        "attachment__application", "attachment__case"
    ).get(pk=file_id)
    attachment = file.attachment
    if actor.role == "applicant" and attachment.report_request_id:
        from tribunal.models import ReportRequest
        source = ReportRequest.objects.filter(pk=attachment.report_request_id).values("kind").first()
        if source is None or source["kind"] in {"external_priest", "interview"}:
            raise PermissionDenied("Request attachment is council-only.")
    if require_safe and not safe_file(file):
        raise PermissionDenied("File has not passed technical validation.")
    if actor.role == "applicant":
        decree = Decree.objects.filter(signed_file=file).first()
        if decree:
            event = (
                DecreeRelease.objects.filter(decree=decree, party__account=actor)
                .order_by("-created_at", "-id")
                .first()
            )
            if not event or event.action != "release":
                raise PermissionDenied("Certificate is not released to this recipient.")
        elif attachment.owner_id != actor.pk or attachment.visibility == "council":
            raise PermissionDenied("Attachment is private.")
        if not decree and attachment.versions.order_by("-number").first().pk != file.pk:
            raise PermissionDenied("Applicants see only the latest version.")
    else:
        from .filing_privacy import file_visible

        if not file_visible(file):
            raise PermissionDenied("Returned corrections are private until resubmission.")
        if attachment.application and attachment.application.submitted_at is None:
            raise PermissionDenied("Applicant draft attachments are private.")
        if attachment.visibility == "medical":
            if (
                not attachment.report_request_id
                or not MedicalRelease.objects.filter(
                    request_id=attachment.report_request_id,
                    subject=attachment.owner,
                    scope__council=True,
                ).exists()
            ):
                raise PermissionDenied("Signed scoped medical disclosure is required.")
    return file


def case_file_listing(actor, case_id, *, history=False, offset=0):
    """Ordinary case evidence only; medical/report/decree sources have dedicated views."""
    from django.db.models import Exists, OuterRef, Q, Subquery
    from tribunal.policy import case_for

    case = case_for(actor, case_id)
    if history and actor.role == "applicant":
        raise PermissionDenied("Version history is council-only.")
    if not 0 <= offset <= 2**63 - 52:
        raise ValidationError("Offset is outside the supported range.")
    files = (
        FileVersion.objects.select_related(
            "attachment__case", "attachment__application"
        )
        .filter(
            Q(attachment__case=case) | Q(attachment__application__case=case),
            attachment__report_request__isnull=True,
            decree__isnull=True,
        )
        .exclude(attachment__visibility="medical")
    )
    if actor.role == "applicant":
        files = files.filter(attachment__owner=actor).exclude(
            attachment__visibility="council"
        )
    else:
        files = files.filter(
            Q(attachment__application__isnull=True)
            | Q(attachment__application__submitted_at__isnull=False)
        )
    if not history and actor.role == "applicant":
        later = FileVersion.objects.filter(
            attachment_id=OuterRef("attachment_id"), number__gt=OuterRef("number")
        )
        files = files.annotate(has_later=Exists(later)).filter(has_later=False)
    scan = (
        FileTechnicalEvent.objects.filter(file_id=OuterRef("pk"), task="scan")
        .order_by("-created_at", "-id")
        .values("result")[:1]
    )
    files = (
        files.annotate(latest_scan=Subquery(scan))
        .order_by("-created_at", "-id")
    )
    if actor.role == "applicant":
        files = files.filter(latest_scan="clean")
    if actor.role != "applicant":
        from .filing_privacy import file_visible

        # Filter before pagination and select the newest visible formal original.
        # A pending replacement must not hide the last formally submitted file.
        visible = []
        seen = set()
        for row in files:
            if not file_visible(row, current=not history):
                continue
            if not history and row.attachment_id in seen:
                continue
            seen.add(row.attachment_id)
            if row.latest_scan != "clean":
                continue
            visible.append(row)
        rows = visible[offset : offset + 51]
    else:
        rows = list(files[offset : offset + 51])
    return {
        "items": [
            {
                "id": str(row.pk),
                "attachment_id": str(row.attachment_id),
                "name": display_filename(row),
                "category": row.attachment.category,
                "context": row.attachment.context,
                "mime_type": row.mime_type,
                "byte_count": row.byte_count,
                "version": row.number,
                "created_at": row.created_at.isoformat(),
                "download_url": f"/api/files/{row.pk}/",
                "preview_url": f"/api/files/{row.pk}/?view=1"
                if row.mime_type in INLINE_TYPES_FOR_LIST
                else None,
            }
            for row in rows[:50]
        ],
        "next_offset": offset + 50 if len(rows) > 50 else None,
    }


# Shared with delivery without importing the HTTP delivery module into services.
INLINE_TYPES_FOR_LIST = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/ogg",
    "video/mp4",
    "video/webm",
}
