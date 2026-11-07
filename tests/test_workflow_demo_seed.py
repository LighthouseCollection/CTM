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
    from tribunal.management.commands.seed_workflow_demo import AGENDA_COUPLES, COUPLES

    assert Case.objects.count() == count == len(COUPLES) + len(AGENDA_COUPLES)
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
    upcoming = CouncilSession.objects.get(date=today + timedelta(days=7), state="draft")
    archived = CouncilSession.objects.get(date=today - timedelta(days=14), state="closed")
    for session in (current, upcoming, archived):
        assert session.starts_at and session.presiding_member and session.location
        assert session.location == "St. George Coptic Orthodox Church, Bellflower, California"
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


def _assert_applicant_renderable(definition):
    """Mirror the server and applicant-form contract for a published schema (#104)."""
    from tribunal.services.configuration import validate_questionnaire_definition

    validate_questionnaire_definition(definition)
    for field in definition["fields"]:
        assert field["type"] in {"text", "textarea", "date", "choice", "boolean", "list"}
        assert field["label_en"].strip() and field["label_ar"].strip()
        for choice in field.get("choices", []):
            labels = field.get("choice_labels", {}).get(choice, {})
            assert labels.get("label_en", "").strip() and labels.get("label_ar", "").strip()


@pytest.mark.django_db
@pytest.mark.skipif(
    connection.vendor != "sqlite",
    reason="Local review fixtures intentionally reject PostgreSQL",
)
def test_workflow_demo_publishes_applicant_renderable_questionnaires(
    monkeypatch, settings, tmp_path
):
    from tribunal.models import Application, QuestionnaireVersion

    monkeypatch.setenv("CTM_SYNTHETIC_DEMO", "true")
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_workflow_demo")
    for purpose in ("petition", "appeal"):
        latest = QuestionnaireVersion.objects.filter(
            purpose=purpose, published=True
        ).order_by("-number").first()
        _assert_applicant_renderable(latest.definition)
    for app in Application.objects.select_related("questionnaire"):
        _assert_applicant_renderable(app.questionnaire.definition)


@pytest.mark.django_db
@pytest.mark.skipif(
    connection.vendor != "sqlite",
    reason="Local review fixtures intentionally reject PostgreSQL",
)
def test_workflow_demo_rerun_supersedes_broken_select_schema_for_drafts(
    monkeypatch, settings, tmp_path
):
    """Databases seeded before #104 carry an immutable `select` gender field."""
    from tribunal.management.commands.seed_workflow_demo import DATASET
    from tribunal.models import Application, QuestionnaireVersion

    monkeypatch.setenv("CTM_SYNTHETIC_DEMO", "true")
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_workflow_demo")
    latest = QuestionnaireVersion.objects.filter(purpose="petition").order_by("-number").first()
    fields = [
        {**field, "type": "select"} if field["code"] == "gender" else field
        for field in latest.definition["fields"]
    ]
    for field in fields:
        field.pop("choice_labels", None)
    broken = QuestionnaireVersion.objects.create(
        purpose="petition", number=latest.number + 1, published=True,
        definition={**latest.definition, "dataset": DATASET, "fields": fields},
        declaration_en=latest.declaration_en, declaration_ar=latest.declaration_ar,
    )
    draft = Application.objects.create(
        owner=Account.objects.filter(role="applicant").first(),
        kind="petition", status="draft", questionnaire=broken,
    )
    call_command("seed_workflow_demo")
    draft.refresh_from_db()
    assert draft.questionnaire_id != broken.pk
    _assert_applicant_renderable(draft.questionnaire.definition)
    current = QuestionnaireVersion.objects.filter(
        purpose="petition", published=True
    ).order_by("-number").first()
    assert current.pk == draft.questionnaire_id and current.number == broken.number + 1
    call_command("seed_workflow_demo")
    assert QuestionnaireVersion.objects.filter(purpose="petition").count() == current.number


def _run_seed(monkeypatch):
    """Use the guarded live path on PostgreSQL and the isolated path on SQLite."""
    if connection.vendor == "postgresql":
        call_command(
            "seed_workflow_demo",
            live_fictitious=True,
            confirmation="FICTITIOUS-DEMO-DATA-ONLY",
        )
    else:
        monkeypatch.setenv("CTM_SYNTHETIC_DEMO", "true")
        call_command("seed_workflow_demo")


@pytest.mark.django_db
def test_seed_adds_agenda_cases_and_case_text_to_an_already_seeded_database(
    monkeypatch, settings, tmp_path
):
    from tribunal import models as m
    from tribunal.management.commands import seed_workflow_demo as seed

    settings.MEDIA_ROOT = tmp_path
    extras = list(seed.AGENDA_COUPLES)
    # First run reproduces a database seeded before the extra agenda cases existed.
    monkeypatch.setattr(seed, "AGENDA_COUPLES", [])
    _run_seed(monkeypatch)
    numbers = [f"20261020-{len(seed.COUPLES) + 1 + i:02d}" for i in range(len(extras))]
    assert not Case.objects.filter(number__in=numbers).exists()
    today = timezone.localdate()
    archived = CouncilSession.objects.filter(state="closed")
    archived_agenda = sorted(
        AgendaItem.objects.filter(session__in=archived).values_list("id", "part", "position", "state")
    )

    monkeypatch.setattr(seed, "AGENDA_COUPLES", extras)
    _run_seed(monkeypatch)
    current = CouncilSession.objects.get(date=today, state="planned")
    upcoming = list(CouncilSession.objects.filter(state="draft", date__gt=today).order_by("date")[:2])
    new_items = AgendaItem.objects.filter(case__number__in=numbers).select_related("case")
    assert new_items.count() == len(extras) == 22
    on_current = new_items.filter(session=current)
    assert on_current.filter(part=2).count() == 8
    assert on_current.filter(part=2, case__assigned_member__isnull=False).count() == 8
    assert on_current.filter(part=1).count() == 6
    assert on_current.filter(part=1, case__assigned_member__isnull=True).count() == 6
    for session in upcoming:
        assert 3 <= new_items.filter(session=session).count() <= 5
        assert {1, 2} == set(new_items.filter(session=session).values_list("part", flat=True))
    assert sorted(
        AgendaItem.objects.filter(session__in=archived).values_list("id", "part", "position", "state")
    ) == archived_agenda

    # Every new case carries a long, case-specific statement and filled tabs.
    paragraphs = []
    for case in Case.objects.filter(number__in=numbers):
        app = case.applications.get(kind="petition")
        assert app.status == "accepted" and app.attachments.count() == 5
        answers = app.revisions.get(number=1).answers
        statement = answers["statement"].split("\n\n")
        assert len(statement) >= 5
        assert set(answers["grounds"]) <= {"infidelity", "abandonment", "abuse", "faith", "addiction", "concealment"}
        paragraphs.extend(statement)
        notes = m.NoteRevision.objects.filter(note__proceeding__case=case)
        messages = m.Message.objects.filter(case=case)
        assert notes.count() >= 1 and messages.count() >= 4
        assert messages.filter(sender__role="applicant").exists()
        assert messages.exclude(sender__role="applicant").exists()
        assert m.CallRecord.objects.filter(case=case).exists()
        if case.assigned_member_id:
            assert notes.filter(actor=case.assigned_member).count() >= 2
            assert m.ReportRevision.objects.filter(report__request__case=case).exclude(observations="").exists()
    assert len(paragraphs) == len(set(paragraphs))

    # The original open cases gained notes, messages and fuller hearing outcomes.
    original = Case.objects.get(number="20261020-05")
    assert m.NoteRevision.objects.filter(note__proceeding__case=original).count() >= 3
    assert m.Message.objects.filter(case=original).count() >= 4
    assert m.HearingOutcome.objects.filter(hearing__agenda__case=original).count() >= 2

    counted = [m.Case, m.Message, m.NoteRevision, m.CallRecord, m.HearingOutcome, m.ReportRevision, AgendaItem]
    before = [model.objects.count() for model in counted]
    _run_seed(monkeypatch)
    assert [model.objects.count() for model in counted] == before


@pytest.mark.django_db
@pytest.mark.skipif(connection.vendor != "postgresql", reason="Live fictitious path requires PostgreSQL")
def test_live_seed_never_changes_an_existing_staff_role():
    """The roster is the real council: a role changed on live is never reset by the demo seed."""
    staff = Account.objects.create_user(
        email="frjonahlabib@lacopts.org", first_name="Jonah", last_name="Labib", role="secretary"
    )
    with pytest.raises(CommandError, match="frjonahlabib@lacopts.org"):
        call_command("seed_workflow_demo", live_fictitious=True, confirmation="FICTITIOUS-DEMO-DATA-ONLY")
    staff.refresh_from_db()
    assert staff.role == "secretary"
    assert not Case.objects.exists()


@pytest.mark.django_db
def test_seed_gives_the_admin_a_voting_seat_and_cases_once(monkeypatch, settings, tmp_path):
    """#175: frraphaelmaher@lacopts.org stays admin, holds a voting seat and manages demo cases like members."""
    from tribunal import models as m
    from tribunal.services.council_seats import council_seat
    settings.MEDIA_ROOT = tmp_path
    _run_seed(monkeypatch)
    admin = Account.objects.get(email="frraphaelmaher@lacopts.org")
    assert admin.role == "admin"
    assert council_seat(admin) == {"seated": True, "voting": True}
    mine = Case.objects.filter(assigned_member=admin, status="open", origin="synthetic")
    assert mine.count() == 4
    assert m.CaseAssignment.objects.filter(member=admin, case__in=mine).count() == 4
    _run_seed(monkeypatch)
    assert m.CouncilSeatChange.objects.filter(account=admin).count() == 1
    assert m.CaseAssignment.objects.filter(member=admin).count() == 4
