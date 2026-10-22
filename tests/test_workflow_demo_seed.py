import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from tribunal.models import Account, Case, FileVersion, OpenCaseClaim, Outbox


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
    from tribunal.models import ReportRequest

    assert all(request.questions[0]["en"] for request in ReportRequest.objects.all())
    assert not OpenCaseClaim.objects.filter(case__status="closed").exists()
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
