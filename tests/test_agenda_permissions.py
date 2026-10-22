from datetime import date

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from tribunal.models import AgendaItem, AuditEvent
from tribunal.services import council
from tribunal.services.applications import submit_application

pytestmark = pytest.mark.django_db


@pytest.fixture
def assigned(ready_application, people):
    app = ready_application
    submit_application(
        app.owner, app.pk, "agenda", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    council.assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    session = council.create_session(people["admin"], date(2026, 11, 4))
    return app, session


def test_assigned_manager_can_place_own_case_once(assigned, people):
    app, session = assigned
    first = council.place_agenda(people["member"], session.pk, app.case_id)
    again = council.place_agenda(people["member"], session.pk, app.case_id)
    assert first.pk == again.pk
    assert AgendaItem.objects.count() == 1
    assert (
        AuditEvent.objects.filter(action="agenda_placed", source_id=first.pk).count()
        == 1
    )


@pytest.mark.parametrize("role", ["applicant", "president"])
def test_unassigned_person_cannot_place_case(assigned, people, role):
    app, session = assigned
    with pytest.raises(PermissionDenied):
        council.place_agenda(people[role], session.pk, app.case_id)
    assert not AgendaItem.objects.exists()


def test_case_manager_cannot_manage_initial_assignment_agenda(assigned, people):
    app, session = assigned
    with pytest.raises(PermissionDenied):
        council.place_agenda(people["member"], session.pk, app.case_id, part=1)


@pytest.mark.parametrize("part", [True, "2", 3])
def test_invalid_agenda_part_does_not_write(assigned, people, part):
    app, session = assigned
    with pytest.raises(ValidationError):
        council.place_agenda(people["admin"], session.pk, app.case_id, part=part)
    assert not AgendaItem.objects.exists()


def test_closed_session_cannot_receive_manager_case(assigned, people):
    app, session = assigned
    council.close_session(people["admin"], session.pk)
    with pytest.raises(ValidationError):
        council.place_agenda(people["member"], session.pk, app.case_id)


def test_existing_agenda_part_cannot_be_silently_changed(assigned, people):
    app, session = assigned
    council.place_agenda(people["admin"], session.pk, app.case_id, part=1)
    with pytest.raises(ValidationError):
        council.place_agenda(people["member"], session.pk, app.case_id, part=2)


def test_manager_agenda_api_uses_same_permission(assigned, people, client):
    app, session = assigned
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.post(
        f"/api/sessions/{session.pk}/agenda/",
        {"case_id": str(app.case_id)},
        content_type="application/json",
    )
    assert response.status_code == 201


def test_former_manager_cannot_schedule_after_reassignment(assigned, people):
    app, session = assigned
    council.assign_case(
        people["admin"], app.case_id, people["president"].pk, people["president"].pk
    )
    with pytest.raises(PermissionDenied):
        council.place_agenda(people["member"], session.pk, app.case_id)
    assert not AgendaItem.objects.exists()


def test_closed_case_without_appeal_cannot_be_placed(assigned, people):
    from tribunal.services.decisions import withdraw_application

    app, session = assigned
    withdraw_application(app.owner, app.pk)
    with pytest.raises(ValidationError):
        council.place_agenda(people["member"], session.pk, app.case_id)
    assert not AgendaItem.objects.exists()


def test_session_close_preserves_existing_next_session_placement(assigned, people):
    from datetime import timedelta

    app, session = assigned
    session.state = "draft"
    session.save(update_fields=["state"])
    source = council.place_agenda(people["member"], session.pk, app.case_id, part=2)
    next_session = council.create_session(
        people["admin"], session.date + timedelta(days=7)
    )
    target = council.place_agenda(people["admin"], next_session.pk, app.case_id, part=1)
    council.close_session(people["admin"], session.pk)
    session.refresh_from_db()
    source.refresh_from_db()
    target.refresh_from_db()
    assert session.state == "closed"
    assert source.state == "unpresented"
    assert target.part == 1
    assert next_session.agenda.count() == 1
