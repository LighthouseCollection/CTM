from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from tribunal.models import (
    Application,
    AnswerRevision,
    Attachment,
    FileVersion,
    FileTechnicalEvent,
    AuditEvent,
    Notification,
    Outbox,
    DocumentText,
)
from tribunal.policy import active
from .common import audit
from .files import private_path


@transaction.atomic
def remove_draft(actor, app_id, expired=False, *, expected_version=None):
    if actor:
        active(actor)
    app = Application.objects.select_for_update(of=("self",)).get(pk=app_id)
    from .applications import check_filing_version
    check_filing_version(app, expected_version)
    if actor and app.owner_id != actor.pk:
        raise PermissionDenied("Only the draft owner can delete it.")
    if app.submitted_at or app.status != "draft":
        raise ValidationError("Submitted filings cannot be deleted.")
    if app.checkoutintent_set.exists():
        raise ValidationError("Checkout must be reconciled before draft cleanup.")
    versions = FileVersion.objects.filter(attachment__application=app)
    keys = list(versions.values_list("object_key", flat=True))
    DocumentText.objects.filter(file__in=versions).delete()
    FileTechnicalEvent.objects.filter(file__in=versions).delete()
    versions.delete()
    Attachment.objects.filter(application=app).delete()
    AnswerRevision.objects.filter(application=app).delete()
    app.status = "expired" if expired else "deleted"
    app.current_version = 0
    app.save(update_fields=["status", "current_version"])
    audit(actor, "draft_" + app.status, app)

    def clean_bytes():
        for key in keys:
            try:
                private_path(key).unlink(missing_ok=True)
            except OSError:
                Outbox.objects.get_or_create(
                    key=f"cleanup:{key}",
                    defaults={
                        "kind": "private_orphan_cleanup",
                        "payload": {"object_key": key},
                    },
                )

    transaction.on_commit(clean_bytes)
    return app


def process_drafts(now=None):
    now = now or timezone.now()
    result = {"warned": 0, "expired": 0, "held": 0}
    ids = list(
        Application.objects.filter(
            status="draft",
            submitted_at__isnull=True,
            last_activity__lte=now - timezone.timedelta(days=173),
        ).values_list("pk", flat=True)
    )
    for app_id in ids:
        with transaction.atomic():
            app = Application.objects.select_for_update(of=("self",)).get(pk=app_id)
            if app.submitted_at or app.status != "draft":
                continue
            deadline = app.last_activity + timezone.timedelta(days=180)
            if app.checkoutintent_set.exists():
                result["held"] += 1
                continue
            if deadline <= now:
                remove_draft(None, app.pk, expired=True)
                result["expired"] += 1
            else:
                key = f"draft-expiry:{app.pk}:{deadline.isoformat()}"
                _, created = Notification.objects.get_or_create(
                    recipient=app.owner,
                    key=key,
                    defaults={
                        "kind": "draft_expiring",
                        "payload": {"expires_at": deadline.isoformat()},
                    },
                )
                if created:
                    Outbox.objects.get_or_create(
                        key=key,
                        defaults={
                            "recipient": app.owner,
                            "kind": "draft_expiring",
                            "payload": {"expires_at": deadline.isoformat()},
                        },
                    )
                    result["warned"] += 1
    return result
