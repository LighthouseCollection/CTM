"""#9 F09 / AS-F09 and F25 / AS-F25: resubmission rechecks and exact submitted files.

F09: a return needs instructions, only one review can decide a submission
(also under a real PostgreSQL race), and resubmission rechecks the latest
file safety instead of reusing the first filing's result.
F25: the completeness reader shows the exact file versions that were
submitted, not a later replacement or one whose scan is still pending.
Synthetic data only.
"""
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections, transaction

from tribunal import models as m
from tribunal.services.applications import review_application, submit_application
from tribunal.services.files import upload

ATTESTATION = {"accepted": True, "name": "John Smith"}


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


def returned_with_pending_replacement(app, people, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    formal = submit_application(app.owner, app.pk, "f09-first", ATTESTATION)
    review_application(people["secretary"], app.pk, "reject", "Replace the certificate.")
    app.refresh_from_db()
    settings.CTM_SCAN_REQUIRED = True
    settings.CLAMAV_HOST = ""  # no scanner: the new file stays pending, never faked clean
    attachment = app.attachments.get(category="MC")
    replacement = upload(app.owner, SimpleUploadedFile("replacement.pdf", b"%PDF-replacement"),
                         "MC", app_id=app.pk, attachment_id=attachment.pk)
    app.refresh_from_db()
    return formal, replacement


@pytest.mark.django_db
@pytest.mark.parametrize("instructions", ["", "   \n "])
def test_f09_return_requires_instructions(ready_application, people, instructions):
    app = ready_application
    submit_application(app.owner, app.pk, "f09-first", ATTESTATION)
    with pytest.raises(ValidationError, match="correction instructions"):
        review_application(people["secretary"], app.pk, "reject", instructions)
    app.refresh_from_db()
    assert app.status == "submitted"
    assert not m.CompletenessReview.objects.filter(submission__application=app).exists()


@pytest.mark.django_db
def test_f09_second_review_of_the_same_submission_is_refused(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "f09-first", ATTESTATION)
    review_application(people["secretary"], app.pk, "reject", "Correct the dates.")
    with pytest.raises(ValidationError, match="awaiting completeness review"):
        review_application(people["admin"], app.pk, "accept")
    app.refresh_from_db()
    assert app.status == "returned"
    assert m.CompletenessReview.objects.filter(submission__application=app).count() == 1


@pytest.mark.django_db(transaction=True)
def test_f09_concurrent_reviews_decide_once_postgres(ready_application, people):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row-lock contention test")
    app = ready_application
    submit_application(app.owner, app.pk, "f09-first", ATTESTATION)

    def accept():
        try:
            admin = m.Account.objects.get(pk=people["admin"].pk)
            return review_application(admin, app.pk, "accept")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            review_application(people["secretary"], app.pk, "reject", "Correct the dates.")
            future = pool.submit(accept)  # waits on the application row lock
        with pytest.raises(ValidationError, match="awaiting completeness review"):
            future.result(timeout=10)
    app.refresh_from_db()
    assert app.status == "returned"
    reviews = m.CompletenessReview.objects.filter(submission__application=app)
    assert [row.result for row in reviews] == ["reject"]


@pytest.mark.django_db
def test_f09_resubmit_rechecks_latest_file_safety(ready_application, people, settings, tmp_path):
    app = ready_application
    formal, replacement = returned_with_pending_replacement(app, people, settings, tmp_path)
    with pytest.raises(ValidationError, match="Required document missing: MC"):
        submit_application(app.owner, app.pk, "f09-second", expected_version=app.current_version)
    app.refresh_from_db()
    assert app.status == "returned" and app.submissions.count() == 1
    m.FileTechnicalEvent.objects.create(file=replacement, task="scan", result="clean")
    second = submit_application(app.owner, app.pk, "f09-second", expected_version=app.current_version)
    ids = {row["id"] for row in second.manifest}
    assert str(replacement.pk) in ids
    formal.refresh_from_db()
    assert str(replacement.pk) not in {row["id"] for row in formal.manifest}
    assert second.attestation == {"original_submission": str(formal.pk)}
    assert app.fee.status == "waived"


@pytest.mark.django_db
def test_f25_reader_binds_exact_submitted_file_versions(client, ready_application, people, settings, tmp_path):
    app = ready_application
    formal, replacement = returned_with_pending_replacement(app, people, settings, tmp_path)
    formal_ids = [row["id"] for row in formal.manifest]
    login(client, people["secretary"])
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert [row["file_id"] for row in data["manifest"]] == formal_ids
    assert str(replacement.pk) not in formal_ids
    assert all(row["scan_state"] == "clean" for row in data["manifest"])

    m.FileTechnicalEvent.objects.create(file=replacement, task="scan", result="clean")
    second = submit_application(app.owner, app.pk, "f25-second", expected_version=app.current_version)
    data = client.get(f"/api/applications/{app.pk}/").json()
    assert [row["file_id"] for row in data["manifest"]] == [row["id"] for row in second.manifest]
    assert str(replacement.pk) in {row["file_id"] for row in data["manifest"]}
    formal.refresh_from_db()
    assert [row["id"] for row in formal.manifest] == formal_ids  # first snapshot unchanged


@pytest.mark.django_db
def test_f36_returned_filing_never_auto_expires(ready_application, people):
    from django.utils import timezone
    from tribunal.services.retention import process_drafts

    app = ready_application
    submit_application(app.owner, app.pk, "f36-first", ATTESTATION)
    review_application(people["secretary"], app.pk, "reject", "Correct the dates.")
    m.Application.objects.filter(pk=app.pk).update(last_activity=timezone.now() - timezone.timedelta(days=500))
    process_drafts()
    app.refresh_from_db()
    assert app.status == "returned"
    assert app.submissions.count() == 1 and app.revisions.count() == 1
    assert not m.Notification.objects.filter(recipient=app.owner, kind="draft_expiring").exists()


@pytest.mark.django_db
def test_f35_identity_hold_blocks_payment_and_submission_not_draft_saves(unpaid_application):
    from tribunal.services.applications import save_answers
    from tribunal.services.payments import prepare_checkout

    app = unpaid_application
    m.Application.objects.filter(pk=app.pk).update(duplicate_hold=True)
    answers = app.revisions.get(number=app.current_version).answers
    saved = save_answers(app.owner, app.pk, {**answers, "statement": "Saved during hold"}, app.current_version)
    app.refresh_from_db()
    assert app.current_version == saved.number
    with pytest.raises(ValidationError):
        prepare_checkout(app.owner, app.pk, ATTESTATION, expected_version=app.current_version)
    assert not m.CheckoutIntent.objects.filter(application=app).exists()
    with pytest.raises(ValidationError, match="Duplicate identity review"):
        submit_application(app.owner, app.pk, "f35-submit", ATTESTATION, expected_version=app.current_version)
    assert not app.submissions.exists()
