"""#299: the one-time council account correction is a dry run by default, audited and refuses unsafe cases."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from tribunal.management.commands.fix_council_accounts_299 import (
    CONFIRMATION,
    DELETE_EMAIL,
    IBRAHIM_NEW_EMAIL,
    IBRAHIM_OLD_EMAIL,
    KEEP_EMAIL,
    SOURCE,
)
from tribunal.models import Account, AuditEvent, Notification


def _accounts():
    keep = Account.objects.create_user(email=KEEP_EMAIL, first_name="Fr. Youhanna", last_name="Youssef", role="member")
    target = Account.objects.create_user(email=DELETE_EMAIL, first_name="Fr. Youhanna", last_name="Youssef", role="member")
    ibrahim = Account.objects.create_user(email=IBRAHIM_OLD_EMAIL, first_name="Fr. Youhana", last_name="Ibrahim", role="member")
    return keep, target, ibrahim


def _run(*args):
    out = StringIO()
    call_command("fix_council_accounts_299", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_dry_run_reports_and_writes_nothing():
    _keep, target, ibrahim = _accounts()
    out = _run()
    assert "DRY RUN" in out and "rolled back" in out
    assert f"deleted {DELETE_EMAIL}" in out
    assert Account.objects.filter(pk=target.pk).exists()
    ibrahim.refresh_from_db()
    assert ibrahim.email == IBRAHIM_OLD_EMAIL and ibrahim.first_name == "Fr. Youhana"
    assert not AuditEvent.objects.filter(source=SOURCE).exists()


@pytest.mark.django_db
def test_apply_needs_the_literal_confirmation():
    _keep, target, _ibrahim = _accounts()
    with pytest.raises(CommandError, match="Confirmation"):
        _run("--apply")
    assert Account.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_apply_deletes_the_unused_account_and_corrects_ibrahim_with_audit():
    keep, target, ibrahim = _accounts()
    _run("--apply", "--confirmation", CONFIRMATION)
    assert not Account.objects.filter(email__iexact=DELETE_EMAIL).exists()
    assert Account.objects.filter(pk=keep.pk, is_active=True).exists()
    ibrahim.refresh_from_db()
    assert (ibrahim.email, ibrahim.first_name, ibrahim.last_name) == (IBRAHIM_NEW_EMAIL, "Fr. Youhanna", "Ibrahim")
    actions = set(AuditEvent.objects.filter(source=SOURCE).values_list("action", flat=True))
    assert actions == {"maintenance_account_deleted", "maintenance_account_corrected"}
    assert AuditEvent.objects.get(action="maintenance_account_deleted").source_id == target.pk
    # A second run finds nothing left to do.
    out = _run("--apply", "--confirmation", CONFIRMATION)
    assert "already deleted" in out and "already correct" in out


@pytest.mark.django_db
def test_editable_references_move_to_frjohnyoussef_before_the_delete():
    keep, target, _ibrahim = _accounts()
    note = Notification.objects.create(recipient=target, key="issue-299-test", kind="test")
    _run("--apply", "--confirmation", CONFIRMATION)
    note.refresh_from_db()
    assert note.recipient_id == keep.pk
    assert not Account.objects.filter(pk=target.pk).exists()
    moved = AuditEvent.objects.get(action="maintenance_account_references_moved")
    assert moved.metadata["moved"] == {"tribunal_notification.recipient_id": 1}


@pytest.mark.django_db
def test_history_is_never_rewritten_and_stops_unless_suspension_is_chosen():
    _keep, target, _ibrahim = _accounts()
    AuditEvent.objects.create(actor=target, action="test_history", source="test")
    with pytest.raises(CommandError, match="history"):
        _run("--apply", "--confirmation", CONFIRMATION)
    target.refresh_from_db()
    assert target.is_active
    assert not AuditEvent.objects.filter(source=SOURCE).exists()

    _run("--apply", "--confirmation", CONFIRMATION, "--suspend-if-history")
    target.refresh_from_db()
    assert not target.is_active
    assert AuditEvent.objects.filter(actor=target, action="test_history").exists()
    assert AuditEvent.objects.filter(action="maintenance_account_suspended", source_id=target.pk).exists()


@pytest.mark.django_db
def test_both_ibrahim_addresses_present_stops_everything():
    _keep, target, _ibrahim = _accounts()
    Account.objects.create_user(email=IBRAHIM_NEW_EMAIL, first_name="Fr. Youhanna", last_name="Ibrahim", role="member")
    with pytest.raises(CommandError, match="both"):
        _run("--apply", "--confirmation", CONFIRMATION)
    assert Account.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_moving_needs_an_active_council_frjohnyoussef():
    Account.objects.create_user(email=DELETE_EMAIL, first_name="Fr. Youhanna", last_name="Youssef", role="member")
    target = Account.objects.get(email=DELETE_EMAIL)
    Notification.objects.create(recipient=target, key="issue-299-missing-keep", kind="test")
    with pytest.raises(CommandError, match="cannot move"):
        _run("--apply", "--confirmation", CONFIRMATION)
    assert Account.objects.filter(pk=target.pk).exists()
