from datetime import date, timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from tribunal.models import Attendance, Hearing, AuditEvent
from tribunal.services import council
from tribunal.services.applications import submit_application

pytestmark = pytest.mark.django_db


@pytest.fixture
def scheduled(ready_application, people):
    app = ready_application
    submit_application(
        app.owner, app.pk, "attendance", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    council.assign_case(
        people["admin"], app.case_id, people["member"].pk, people["president"].pk
    )
    session = council.create_session(people["admin"], date(2026, 11, 1))
    item = council.place_agenda(people["admin"], session.pk, app.case_id)
    return session, item


def test_session_attendance_is_append_only_and_latest_value_wins(scheduled, people):
    session, _ = scheduled
    first = council.record_attendance(
        people["admin"], session.pk, people["member"].pk, False
    )
    second = council.record_attendance(
        people["secretary"], session.pk, people["member"].pk, True
    )
    assert first.pk != second.pk
    assert Attendance.objects.filter(session=session).count() == 2
    assert (
        council.attendance_for(people["member"], session.pk)[people["member"].pk].pk
        == second.pk
    )
    assert first.actor_id == people["admin"].pk


@pytest.mark.parametrize("role", ["applicant", "member", "president"])
def test_only_session_administrators_record_attendance(scheduled, people, role):
    session, _ = scheduled
    with pytest.raises(PermissionDenied):
        council.record_attendance(people[role], session.pk, people["member"].pk, True)


def test_attendance_requires_a_real_boolean_and_active_council_member(
    scheduled, people
):
    session, _ = scheduled
    for value in ["false", 1, None]:
        with pytest.raises(ValidationError):
            council.record_attendance(
                people["admin"], session.pk, people["member"].pk, value
            )
    with pytest.raises(ValidationError):
        council.record_attendance(
            people["admin"], session.pk, people["applicant"].pk, True
        )


def test_hearing_requires_presenter_attendance(scheduled, people):
    _, item = scheduled
    with pytest.raises(ValidationError):
        council.hear_case(people["member"], item.pk)
    assert not Hearing.objects.exists()


def test_hearing_snapshots_attendance_without_later_baseline_changes(scheduled, people):
    session, item = scheduled
    council.record_attendance(people["admin"], session.pk, people["member"].pk, True)
    hearing = council.hear_case(people["member"], item.pk)
    council.record_attendance(people["admin"], session.pk, people["member"].pk, False)
    snapshot = council.attendance_for(people["member"], session.pk, hearing.pk)
    assert snapshot[people["member"].pk].present is True
    assert (
        Attendance.objects.filter(hearing=hearing, member=people["president"])
        .get()
        .present
        is False
    )


def test_absent_presenter_defers_for_manual_placement(scheduled, people):
    session, item = scheduled
    council.record_attendance(people["admin"], session.pk, people["member"].pk, False)
    assert council.hear_case(people["member"], item.pk) is None
    item.refresh_from_db()
    assert item.state == "presenter_absent"
    assert not Hearing.objects.exists()
    next_session = council.create_session(
        people["admin"], session.date + timedelta(days=7)
    )
    council.close_session(people["admin"], session.pk)
    assert not next_session.agenda.exists()


def test_session_close_does_not_carry_an_absent_presenters_case(scheduled, people):
    session, item = scheduled
    council.record_attendance(people["admin"], session.pk, people["member"].pk, False)
    following = council.create_session(
        people["admin"], session.date + timedelta(days=7)
    )
    council.close_session(people["secretary"], session.pk)
    item.refresh_from_db()
    assert item.state == "presenter_absent"
    assert not following.agenda.exists()


def test_hearing_attendance_corrections_do_not_change_session_defaults(
    scheduled, people
):
    session, item = scheduled
    council.record_attendance(people["admin"], session.pk, people["member"].pk, True)
    hearing = council.hear_case(people["member"], item.pk)
    council.record_attendance(
        people["secretary"], session.pk, people["president"].pk, True, hearing.pk
    )
    assert council.attendance_for(people["member"], session.pk, hearing.pk)[
        people["president"].pk
    ].present
    assert people["president"].pk not in council.attendance_for(
        people["member"], session.pk
    )


def test_closed_session_attendance_cannot_be_changed(scheduled, people):
    session, _ = scheduled
    council.close_session(people["admin"], session.pk)
    with pytest.raises(ValidationError):
        council.record_attendance(
            people["admin"], session.pk, people["member"].pk, True
        )


def test_attendance_api_denies_applicants_and_records_audit(scheduled, people, client):
    session, _ = scheduled
    url = f"/api/sessions/{session.pk}/attendance/"
    client.force_login(
        people["applicant"],
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    assert client.get(url).status_code == 403
    client.force_login(
        people["admin"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.post(
        url,
        {"member_id": str(people["member"].pk), "present": True},
        content_type="application/json",
    )
    assert response.status_code == 201
    assert AuditEvent.objects.filter(action="attendance_recorded").exists()
    assert client.get(url).json()["items"][0]["present"] is True


def test_case_closed_after_scheduling_cannot_start_an_ordinary_hearing(
    scheduled, people
):
    from tribunal.services.decisions import withdraw_application
    from tribunal.models import Application

    session, item = scheduled
    council.record_attendance(people["admin"], session.pk, people["member"].pk, True)
    app = Application.objects.get(case=item.case)
    withdraw_application(app.owner, app.pk)
    with pytest.raises(ValidationError):
        council.hear_case(people["member"], item.pk)
    assert not Hearing.objects.exists()


def test_attendance_cannot_reference_a_hearing_from_another_session(scheduled, people):
    session, item = scheduled
    council.record_attendance(people["admin"], session.pk, people["member"].pk, True)
    hearing = council.hear_case(people["member"], item.pk)
    other = council.create_session(people["admin"], session.date + timedelta(days=7))
    with pytest.raises(Hearing.DoesNotExist):
        council.record_attendance(
            people["admin"], other.pk, people["member"].pk, True, hearing.pk
        )


@pytest.mark.parametrize("outcome", ["decline", "withdraw"])
def test_finished_appeal_hearing_attendance_is_read_only(scheduled, people, outcome):
    from tribunal.services.applications import (
        start_application,
        save_answers,
        waive_fee,
    )
    from tribunal.services.decisions import withdraw_application, decide_appeal
    from tribunal.models import Application

    session, item = scheduled
    app = Application.objects.get(case=item.case)
    withdraw_application(app.owner, app.pk)
    appeal = start_application(app.owner, item.case_id, "appeal")
    save_answers(
        app.owner,
        appeal.pk,
        {"statement": "Disagree", "new_information": "New evidence"},
        0,
    )
    waive_fee(people["admin"], appeal.pk)
    submit_application(
        app.owner,
        appeal.pk,
        "attendance-appeal",
        {"accepted": True, "name": "John Smith"},
    )
    council.record_attendance(people["admin"], session.pk, people["member"].pk, True)
    hearing = council.hear_case(people["member"], item.pk)
    assert hearing.proceeding_id is None
    if outcome == "withdraw":
        withdraw_application(app.owner, appeal.pk)
    else:
        decide_appeal(people["member"], appeal.pk, hearing.pk, "decline")
    with pytest.raises(ValidationError):
        council.record_attendance(
            people["admin"], session.pk, people["president"].pk, True, hearing.pk
        )
