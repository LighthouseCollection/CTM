from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone
from tribunal.models import Account, AgendaItem, Case, CouncilSession, FileVersion, OpenCaseClaim, Outbox


@pytest.mark.django_db
def test_seed_requires_explicit_isolated_demo_opt_in(monkeypatch):
    monkeypatch.delenv("CTM_SYNTHETIC_DEMO", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_workflow_demo")
    assert not Case.objects.exists()


@pytest.mark.django_db
@pytest.mark.skipif(
    connection.vendor != "sqlite",
    reason="Local review fixtures intentionally reject PostgreSQL",
)
def test_workflow_demo_is_repeatable_private_and_delivery_free(
    monkeypatch, settings, tmp_path
):
    monkeypatch.setenv("CTM_SYNTHETIC_DEMO", "true")
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_workflow_demo")
    count = Case.objects.count()
    file_count = FileVersion.objects.count()
    call_command("seed_workflow_demo")
    assert Case.objects.count() == count == 8
    assert FileVersion.objects.count() == file_count
    assert Account.objects.filter(
        role="president", email="bishopserapion@lacopts.org"
    ).exists()
    assert Account.objects.filter(
        role="secretary", email="frmauritiusmikhail@lacopts.org"
    ).exists()
    assert Account.objects.filter(role="applicant", first_name="James").exists()
    assert all(not a.has_usable_password() for a in Account.objects.all())
    assert not Account.objects.exclude(microsoft_subject="").exists()
    assert not Outbox.objects.exists()
    # Returned review still exposes the exact formally submitted original to council.
    from tribunal.models import Application
    from tribunal.services.files import authorized_file

    returned = Application.objects.filter(status="returned").first()
    accepted = Application.objects.filter(status="accepted", kind="petition").first()
    answers = accepted.revisions.get(number=accepted.current_version).answers
    assert answers["church_marriage_date"] == "2010-06-12"
    assert answers["church_name"] == "St. Mark Coptic Orthodox Church"
    assert answers["married_outside_coptic_church"] == "No"
    assert answers["spouse_occupation"] == "Teacher"
    original = FileVersion.objects.filter(attachment__application=returned).first()
    reviewer = Account.objects.get(email="frraphaelmaher@lacopts.org")
    assert original is not None
    assert authorized_file(reviewer, original.pk).pk == original.pk
    from tribunal.models import ReportRequest

    assert all(request.questions[0]["en"] for request in ReportRequest.objects.all())
    assert not OpenCaseClaim.objects.filter(case__status="closed").exists()
    today = timezone.localdate()
    current = CouncilSession.objects.get(date=today, state="planned")
    upcoming = CouncilSession.objects.get(date=today + timedelta(days=7), state="planned")
    archived = CouncilSession.objects.get(date=today - timedelta(days=14), state="closed")
    for session in (current, upcoming, archived):
        assert session.starts_at and session.presiding_member and session.location
    assert AgendaItem.objects.filter(session=current).exists()
    assert AgendaItem.objects.filter(session=upcoming).exists()
    for source in FileVersion.objects.filter(mime_type="application/pdf"):
        data = (tmp_path / source.object_key).read_bytes()
        assert data.startswith(b"%PDF-") and b"xref" in data
        assert b"CTM document preview" in data and b"DEMO" not in data


@pytest.mark.django_db
def test_seed_refuses_existing_non_demo_case(monkeypatch):
    monkeypatch.setenv("CTM_SYNTHETIC_DEMO", "true")
    Case.objects.create(number="20261021-99")
    with pytest.raises(CommandError):
        call_command("seed_workflow_demo")
