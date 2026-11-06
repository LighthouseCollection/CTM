"""#8 F11 / AS-F11 and F14 / AS-F14, #9 F10 / AS-F10. Synthetic data only.

F11: an ambiguous marriage match or an unexact spouse mapping stops the
filing before any case number, party, open claim or access exists.
F14: the DOB-bearing party reference never reaches notifications, queued
email, sent mail, file names, object keys, audit metadata or logs.
F10: a resubmission on an assigned case goes to the completeness reviewers
(admin and secretary) only; no recipient is added by guesswork.
"""
import json
import logging
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from tribunal import models as m
from tribunal.services.applications import review_application, submit_application
from tribunal.services.files import upload

pytestmark = pytest.mark.django_db
ATTESTATION = {"accepted": True, "name": "John Smith"}
# Fixture answers: birth_date 1985-03-14, spouse 1987-04-02, marriage 2010-05-01.
MARRIAGE, LOW, HIGH = date(2010, 5, 1), date(1985, 3, 14), date(1987, 4, 2)


def nothing_created(app, cases_before):
    app.refresh_from_db()
    assert app.status == "draft" and app.case_id is None and app.party_id is None
    assert m.Case.objects.count() == cases_before
    assert not m.Party.objects.filter(account=app.owner).exists()
    assert not m.OpenCaseClaim.objects.filter(person=app.owner.person).exists()
    assert not app.submissions.exists()


def test_f11_ambiguous_marriage_match_allocates_nothing(ready_application):
    for number in ["20200101-01", "20200101-02"]:
        m.Case.objects.create(number=number, marriage_date=MARRIAGE, spouse_dob_low=LOW, spouse_dob_high=HIGH)
    before = m.Case.objects.count()
    with pytest.raises(ValidationError, match="Ambiguous marriage match"):
        submit_application(ready_application.owner, ready_application.pk, "f11-ambiguous", ATTESTATION)
    nothing_created(ready_application, before)


def test_f11_unexact_spouse_mapping_needs_review_and_grants_nothing(ready_application):
    case = m.Case.objects.create(number="20200101-03", marriage_date=MARRIAGE, spouse_dob_low=LOW, spouse_dob_high=HIGH)
    m.Proceeding.objects.create(case=case)
    stranger = m.Person.objects.create(first_name="Other", last_name="Person", birth_date=date(1990, 1, 1))
    m.Party.objects.create(case=case, person=stranger, slot="A", name="Other Person")
    before = m.Case.objects.count()
    with pytest.raises(ValidationError, match="Exact spouse identity mapping requires review"):
        submit_application(ready_application.owner, ready_application.pk, "f11-mapping", ATTESTATION)
    nothing_created(ready_application, before)
    assert case.parties.count() == 1


def test_f14_dob_reference_stays_out_of_messages_files_audit_and_logs(
        ready_application, people, settings, tmp_path, caplog, mailoutbox):
    from tribunal.tasks import dispatch_outbox

    settings.MEDIA_ROOT = tmp_path
    settings.CTM_SCAN_REQUIRED = False
    settings.EMAIL_HOST = "configured-for-test"
    app = ready_application
    caplog.set_level(logging.DEBUG)
    submit_application(app.owner, app.pk, "f14-first", ATTESTATION)
    review_application(people["secretary"], app.pk, "reject", "Replace the certificate.")
    app.refresh_from_db()
    upload(app.owner, SimpleUploadedFile("scan.pdf", b"%PDF-f14"), "MC",
           app_id=app.pk, attachment_id=app.attachments.get(category="MC").pk)
    submit_application(app.owner, app.pk, "f14-second", expected_version=app.current_version)
    dispatch_outbox(limit=100)

    reference = m.Party.objects.get(pk=app.party_id).reference
    assert "19850314" in reference  # the reference really carries the DOB
    texts = [
        *(json.dumps(row.payload) for row in m.Notification.objects.all()),
        *(row.key + json.dumps(row.payload) for row in m.Outbox.objects.all()),
        *(f"{mail.subject}\n{mail.body}\n{[a[0] for a in mail.attachments]}" for mail in mailoutbox),
        *(f"{row.display_name} {row.object_key} {row.original_name}" for row in m.FileVersion.objects.all()),
        *(json.dumps(row.metadata) for row in m.AuditEvent.objects.all()),
        caplog.text,
    ]
    for text in texts:
        assert reference not in text
        assert "19850314" not in text and "1985-03-14" not in text


def test_f10_resubmission_on_assigned_case_goes_to_reviewers_only(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "f10-first", ATTESTATION)
    app.refresh_from_db()
    m.Case.objects.filter(pk=app.case_id).update(assigned_member=people["member"])
    review_application(people["secretary"], app.pk, "reject", "Correct the dates.")
    app.refresh_from_db()
    first = set(m.Notification.objects.values_list("pk", flat=True))
    second = submit_application(app.owner, app.pk, "f10-second", expected_version=app.current_version)
    new = m.Notification.objects.exclude(pk__in=first)
    reviewers = {people["admin"].pk, people["secretary"].pk}
    assert set(new.filter(kind="intake_submitted").values_list("recipient_id", flat=True)) == reviewers
    assert set(new.values_list("recipient_id", flat=True)) == reviewers | {app.owner_id}
    assert new.get(recipient=app.owner).kind == "submission_received"
    assert people["member"].pk not in set(new.values_list("recipient_id", flat=True))
    assert second.attestation == {"original_submission": str(app.submissions.order_by("created_at").first().pk)}
