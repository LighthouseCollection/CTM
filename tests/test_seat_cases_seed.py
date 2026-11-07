"""Owner 2026-11-07: every council seat holder has five open, fully filled demo cases.

The president is not a seat holder here: the app never makes the president a
case manager. Fictional data only; live demo path (PostgreSQL).
"""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from tribunal import models as m
from tribunal.services.applications import required_documents, validate_petition
from tribunal.validation import validate_answers

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(connection.vendor != "postgresql", reason="Live fictitious path requires PostgreSQL"),
]
LIVE = {"live_fictitious": True, "confirmation": "FICTITIOUS-DEMO-DATA-ONLY"}


@pytest.fixture
def seeded(settings, tmp_path, capsys):
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_workflow_demo", **LIVE)
    call_command("seed_new_applications_demo", **LIVE)
    capsys.readouterr()
    call_command("seed_seat_cases", **LIVE)
    return capsys.readouterr().out


def holders():
    from tribunal.management.commands.seed_seat_cases import seat_holders
    return seat_holders()


def test_every_seat_holder_has_five_open_cases_and_the_script_says_so(seeded):
    found = holders()
    emails = {a.email for a in found}
    assert "frraphaelmaher@lacopts.org" in emails  # admin with a seat
    assert not any(a.role == "president" for a in found)
    for holder in found:
        assert m.Case.objects.filter(assigned_member=holder, status="open").count() == 5, holder.email
        name = f"{holder.first_name} {holder.last_name}".strip()
        assert f"open cases per seat holder: {name} 5" in seeded


def test_new_cases_are_complete(seeded):
    cases = m.Case.objects.filter(number__startswith="DEMO-", origin="synthetic").exclude(number__startswith="DEMO-NEW-")
    assert cases.exists()
    for case in cases:
        app = m.Application.objects.get(case=case, kind="petition")
        revision = app.submissions.get().revision
        answers = revision.answers
        validate_answers(revision.questionnaire, answers)  # every required answer present
        validate_petition(answers)
        assert {code for code in answers["grounds"]} and "desertion" not in answers["grounds"]
        for key in ("address", "spouse_address", "mobile", "spouse_mobile", "education", "spouse_education",
                    "denomination", "spouse_denomination", "separation_date", "church_marriage_date"):
            assert answers[key], key
        assert required_documents(app, answers)  # every required document slot filled, scanned clean
        parties = list(case.parties.select_related("person").order_by("slot"))
        assert [p.slot for p in parties] == ["A", "B"] and all(p.person.birth_date for p in parties)
        assert m.CaseAssignment.objects.filter(case=case, member=case.assigned_member).exists()
        assert m.CaseNote.objects.filter(proceeding__case=case).exists()
        assert m.Message.objects.filter(case=case).exists() and m.CallRecord.objects.filter(case=case).exists()
        assert m.ReportRequest.objects.filter(case=case, kind="external_priest", state="draft").exists()
        assert app.fee.status == "waived" and not m.PaymentEvent.objects.filter(application=app).exists()
    assert m.AgendaItem.objects.filter(case__in=cases).exists()


def test_rerun_adds_nothing(seeded, capsys):
    count = m.Case.objects.count()
    call_command("seed_seat_cases", **LIVE)
    assert m.Case.objects.count() == count


def test_refuses_when_a_real_case_exists(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    m.Case.objects.create(number="20990101-01", origin="new", status="open")
    with pytest.raises(CommandError, match="non-demo"):
        call_command("seed_seat_cases", **LIVE)


def test_refuses_on_a_council_role_conflict(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    m.Account.objects.create_user(email="frjonahlabib@lacopts.org", role="secretary")
    with pytest.raises(CommandError, match="frjonahlabib@lacopts.org"):
        call_command("seed_seat_cases", **LIVE)
    assert not m.Case.objects.exists()
