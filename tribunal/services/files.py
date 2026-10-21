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

        request = ReportRequest.objects.select_related(
            "subject", "proceeding__case"
        ).get(pk=request_id)
        if actor.role == "applicant":
            if request.subject.account_id != actor.pk:
                raise PermissionDenied("Not your report request.")
        else:
            writer(actor, request.case)
        open_proceeding(request.proceeding)
        if request.state != "sent":
            raise ValidationError("Report request is not accepting uploads.")
        case = request.case
        proceeding = request.proceeding
        owner = request.subject.account
        visibility = (
            "medical" if request.kind in {"medical", "psychological"} else "own"
        )
    elif app_id:
        app = application_for(actor, app_id, write=True)
        case = app.case
        proceeding = app.proceeding
        if app.status in {"withdrawn", "expired", "deleted", "declined"}:
            raise ValidationError("Application is no longer accepting documents.")
        if app.submitted_at and app.kind != "appeal":
            open_proceeding(proceeding)
        if app.kind == "appeal" and app.status not in {"draft", "submitted"}:
            raise ValidationError("Appeal is not pending.")
        owner = app.owner
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
    if app and app.submitted_at and actor.pk == app.owner_id:
        notify_manager(case, "file_uploaded", file, digest=True)
    return file


def authorized_file(actor, file_id):
    active(actor)
    file = FileVersion.objects.select_related(
        "attachment__application", "attachment__case"
    ).get(pk=file_id)
    attachment = file.attachment
    if not safe_file(file):
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
