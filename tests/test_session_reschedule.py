from datetime import date, datetime, timezone as tz
from unittest.mock import patch
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.utils import timezone
from tribunal.models import CouncilSession, AgendaItem, AgendaTransferEvent, Attendance, TestimonyAppointment, Outbox, Message
from tribunal.services.applications import submit_application
from tribunal.services.council import (
    assign_case, create_session, place_agenda, schedule_testimony, respond_testimony,
    record_attendance, hear_case, reschedule_session, close_session,
)
from tribunal.services.communications import send_message
from tribunal.tasks import dispatch_outbox

pytestmark = pytest.mark.django_db


@pytest.fixture
def planned(ready_application, people):
    app = ready_application
    submit_application(app.owner, app.pk, "reschedule", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    assign_case(people["admin"], app.case_id, people["member"].pk, people["president"].pk)
    session = create_session(people["admin"], date(2030, 1, 2))
    item = place_agenda(people["member"], session.pk, app.case_id)
    record_attendance(people["admin"], session.pk, people["member"].pk, True)
    appointment = schedule_testimony(people["admin"], item.pk, app.party_id,
        datetime(2030, 1, 2, 18, tzinfo=tz.utc), datetime(2030, 1, 2, 19, tzinfo=tz.utc), "Attend remotely")
    return app, session, item, appointment


def replacement(appointment):
    return {str(appointment.pk): {"starts_at": datetime(2030, 1, 3, 18, tzinfo=tz.utc),
                                  "ends_at": datetime(2030, 1, 3, 19, tzinfo=tz.utc)}}


def test_reschedule_transfers_every_item_and_retains_versions(planned, people):
    app, source, item, appointment = planned
    source_id = source.pk
    respond_testimony(app.owner, appointment.pk, 1, "confirm")
    target = reschedule_session(people["admin"], source.pk, date(2030, 1, 3), replacement(appointment), "New meeting date")
    assert not CouncilSession.objects.filter(pk=source_id).exists()
    assert not AgendaItem.objects.filter(pk=item.pk).exists()
    assert not Attendance.objects.filter(session_id=source_id).exists()
    destination = target.agenda.get()
    assert destination.case_id == app.case_id and destination.part == item.part
    transfer = AgendaTransferEvent.objects.get()
    assert transfer.from_session_snapshot["id"] == str(source_id)
    assert transfer.to_session_id == target.pk and transfer.destination_item_id == destination.pk
    appointment.refresh_from_db()
    assert appointment.agenda_id == destination.pk and appointment.version == 2
    assert list(appointment.versions.order_by("version").values_list("starts_at", flat=True)) == [
        datetime(2030, 1, 2, 18, tzinfo=tz.utc), datetime(2030, 1, 3, 18, tzinfo=tz.utc)]
    with pytest.raises(ValidationError, match="superseded"):
        respond_testimony(app.owner, appointment.pk, 1, "confirm")
    assert respond_testimony(app.owner, appointment.pk, 2, "reject", "Unavailable").version == 2


def test_reschedule_moves_only_deferred_binding_not_message_content(planned, people):
    app, source, _, appointment = planned
    message = send_message(people["admin"], app.case_id, "Original message", [app.party_id], "after_session", source.pk)
    initial_snapshot = message.session_snapshot
    target = reschedule_session(people["secretary"], source.pk, date(2030, 1, 3), replacement(appointment), "Move date")
    message.refresh_from_db()
    assert message.body == "Original message" and message.session_id == target.pk
    assert message.session_snapshot == initial_snapshot
    event = Outbox.objects.get(kind="message_session")
    assert event.payload["session"] == str(target.pk)
    assert event.due_at > timezone.now()
    close_session(people["admin"], target.pk)
    event.refresh_from_db()
    assert event.due_at <= timezone.now()


@override_settings(EMAIL_HOST="configured-for-test")
def test_obsolete_reminders_are_discarded_without_fake_delivery(planned, people, mailoutbox):
    _, source, _, appointment = planned
    old = Outbox.objects.get(kind="testimony_reminder")
    reschedule_session(people["admin"], source.pk, date(2030, 1, 3), replacement(appointment), "Move date")
    Outbox.objects.exclude(pk=old.pk).update(due_at=timezone.now()+timezone.timedelta(days=3650))
    Outbox.objects.filter(pk=old.pk).update(due_at=timezone.now())
    assert dispatch_outbox() == 0 and not mailoutbox
    old.refresh_from_db()
    assert old.discarded_at and old.delivered_at is None
    assert "no message sent" in old.last_error


def test_missing_times_and_existing_date_roll_back_everything(planned, people):
    _, source, item, appointment = planned
    with pytest.raises(ValidationError, match="every active"):
        reschedule_session(people["admin"], source.pk, date(2030, 1, 3), {}, "Move date")
    assert CouncilSession.objects.count() == 1 and AgendaItem.objects.get().pk == item.pk
    create_session(people["admin"], date(2030, 1, 3))
    with pytest.raises(ValidationError, match="already uses"):
        reschedule_session(people["admin"], source.pk, date(2030, 1, 3), replacement(appointment), "Move date")
    appointment.refresh_from_db()
    assert appointment.version == 1


def test_hearing_history_prevents_reschedule(planned, people):
    _, source, item, appointment = planned
    hear_case(people["member"], item.pk)
    with pytest.raises(ValidationError, match="held hearing"):
        reschedule_session(people["admin"], source.pk, date(2030, 1, 3), replacement(appointment), "Move date")
    assert CouncilSession.objects.filter(pk=source.pk).exists()


def test_repeat_reschedule_preserves_restrictive_transfer_history(planned, people):
    _, source, _, appointment = planned
    target = reschedule_session(people["admin"], source.pk, date(2030, 1, 3), replacement(appointment), "Move date")
    with pytest.raises(ValidationError, match="retained transfer history"):
        reschedule_session(people["admin"], target.pk, date(2030, 1, 4), {}, "Move again")
    assert CouncilSession.objects.filter(pk=target.pk).exists() and AgendaTransferEvent.objects.count() == 1


def test_unassigned_staff_cannot_reschedule(planned, people):
    _, source, _, appointment = planned
    with pytest.raises(PermissionDenied):
        reschedule_session(people["member"], source.pk, date(2030, 1, 3), replacement(appointment), "Move date")


def test_own_invitation_api_has_no_other_party_or_internal_session_data(planned, client, people):
    app, _, _, appointment = planned
    client.force_login(app.owner, backend="allauth.account.auth_backends.AuthenticationBackend")
    data = client.get("/api/appointments/").json()["items"]
    assert len(data) == 1 and data[0]["id"] == str(appointment.pk)
    assert data[0]["can_respond"] and "agenda_id" not in data[0]
    assert "session_id" not in data[0] and "attendance" not in data[0]
    from tribunal.models import Account

    outsider = Account.objects.create_user(email="appointment-outsider@example.test", email_verified=True)
    client.force_login(outsider, backend="allauth.account.auth_backends.AuthenticationBackend")
    assert client.get("/api/appointments/").json()["items"] == []
    client.force_login(people["member"], backend="allauth.account.auth_backends.AuthenticationBackend")
    assert client.get("/api/appointments/").status_code == 403


def test_testimony_cancellation_keeps_history_and_invalidates_response(planned, people):
    from tribunal.services.council import cancel_testimony

    app, _, _, appointment = planned
    with pytest.raises(PermissionDenied):
        cancel_testimony(app.owner, appointment.pk, 1)
    with pytest.raises(ValidationError, match="latest testimony"):
        cancel_testimony(people["admin"], appointment.pk, 0)
    cancelled = cancel_testimony(people["admin"], appointment.pk, 1)
    assert cancelled.version == 2 and cancelled.state == "cancelled"
    assert list(cancelled.versions.order_by("version").values_list("cancelled", flat=True)) == [False, True]
    with pytest.raises(ValidationError):
        respond_testimony(app.owner, appointment.pk, 2, "confirm")
