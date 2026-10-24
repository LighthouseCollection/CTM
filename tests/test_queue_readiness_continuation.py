import io
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
import pytest
from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction, DatabaseError
from django.test import override_settings
from django.utils import timezone
from django.core.management import call_command, CommandError
from tribunal import models as m
from tribunal.tasks import dispatch_outbox, claim_delivery
from tribunal.services.queue import enqueue_cleanup, cleanup_orphan, retry_delivery
from tribunal.services.retention import remove_draft
from tribunal.services.files import private_path, write_private_original
from tribunal.services.readiness import database_readiness
from tests.test_own_requests import login

pytestmark = pytest.mark.django_db


@override_settings(EMAIL_HOST="synthetic-configured-host")
@pytest.mark.parametrize("accepted", [0, None, False, True])
def test_email_without_positive_backend_ack_is_not_delivered(people, accepted):
    job = m.Outbox.objects.create(key="email-ack", kind="assignment_changed", recipient=people["member"])
    with patch("tribunal.tasks.EmailMessage.send", return_value=accepted):
        assert dispatch_outbox() == 0
    job.refresh_from_db()
    assert job.delivered_at is None and job.attempts == 1 and job.last_error


@override_settings(EMAIL_HOST="synthetic-configured-host")
@pytest.mark.parametrize("verified,email", [(False, "member@example.test"), (True, "bad\naddress@example.test")])
def test_unverified_or_invalid_recipient_never_reaches_backend(people, verified, email):
    m.Account.objects.filter(pk=people["member"].pk).update(email_verified=verified, email=email)
    job = m.Outbox.objects.create(key="email-recipient", kind="assignment_changed", recipient=people["member"])
    with patch("tribunal.tasks.EmailMessage.send") as send:
        assert dispatch_outbox() == 0 and not send.called
    job.refresh_from_db()
    assert job.delivered_at is None


@override_settings(EMAIL_HOST="synthetic-configured-host")
def test_unsupported_job_kind_cannot_become_successful_email(people):
    job = m.Outbox.objects.create(key="unsupported", kind="unknown-action", recipient=people["member"])
    with patch("tribunal.tasks.EmailMessage.send") as send:
        assert dispatch_outbox() == 0 and not send.called
    job.refresh_from_db()
    assert job.attempts == 1 and not job.delivered_at


@override_settings(EMAIL_HOST="synthetic-configured-host")
def test_leased_rows_do_not_starve_other_due_work(people, mailoutbox):
    busy = m.Outbox.objects.create(key="busy-first", kind="assignment_changed", recipient=people["member"], lease_until=timezone.now()+timezone.timedelta(minutes=5))
    next_job = m.Outbox.objects.create(key="available", kind="assignment_changed", recipient=people["member"])
    assert dispatch_outbox(limit=1) == 1
    next_job.refresh_from_db()
    busy.refresh_from_db()
    assert next_job.delivered_at and not busy.delivered_at and len(mailoutbox) == 1


@override_settings(EMAIL_HOST="synthetic-configured-host")
def test_digest_claim_respects_entire_dispatch_budget(people):
    case = m.Case.objects.create(number="BOUNDED-DIGEST", assigned_member=people["member"])
    for index in range(7):
        m.Outbox.objects.create(key=f"bounded:{index}", kind="appeal_added", case=case, recipient=people["member"])
    assert dispatch_outbox(limit=2) == 2
    assert m.Outbox.objects.filter(delivered_at__isnull=False).count() == 2
    assert m.Outbox.objects.filter(lease_token__isnull=True).count() == 7


def test_retention_commits_durable_cleanup_jobs_without_unlinking_early(unpaid_application, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    file = unpaid_application.attachments.first().versions.first()
    write_private_original(private_path(file.object_key), b"source")
    remove_draft(unpaid_application.owner, unpaid_application.pk)
    assert private_path(file.object_key).exists()
    jobs = m.Outbox.objects.filter(kind="private_orphan_cleanup")
    assert jobs.count() == 4
    assert dispatch_outbox() == 4
    assert not private_path(file.object_key).exists()


def test_cleanup_never_deletes_retained_original(unpaid_application, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    file = unpaid_application.attachments.first().versions.first()
    path = private_path(file.object_key)
    write_private_original(path, b"retained")
    job = enqueue_cleanup(file.object_key)
    assert dispatch_outbox() == 0
    job.refresh_from_db()
    assert path.read_bytes() == b"retained" and job.discarded_at and not job.delivered_at


@pytest.mark.parametrize("key", ["../outside", "/tmp/outside", "folder/../source", "./source", "folder//source"])
def test_cleanup_rejects_path_aliases(settings, tmp_path, key):
    settings.MEDIA_ROOT = tmp_path
    job = enqueue_cleanup(key)
    assert dispatch_outbox() == 0
    job.refresh_from_db()
    assert job.attempts == 1 and not job.delivered_at


def test_cleanup_rejects_in_root_symlink_alias(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    (tmp_path/"source").write_bytes(b"retained")
    (tmp_path/"alias").symlink_to(tmp_path/"source")
    enqueue_cleanup("alias")
    assert dispatch_outbox() == 0
    assert (tmp_path/"source").read_bytes() == b"retained"


def test_cleanup_failure_is_retained_and_missing_source_is_idempotent(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    job = enqueue_cleanup("private/source")
    with patch("pathlib.Path.unlink", side_effect=OSError("synthetic-private-provider-details")):
        assert dispatch_outbox() == 0
    job.refresh_from_db()
    assert job.attempts == 1 and "synthetic-private" not in job.last_error
    retry_delivery(m.Account.objects.create_user(email="retry-admin@example.test", role="admin"), job.pk, 1)
    assert dispatch_outbox() == 1


def test_cleanup_journal_rolls_back_with_draft_deletion(unpaid_application):
    try:
        with transaction.atomic():
            remove_draft(unpaid_application.owner, unpaid_application.pk)
            raise RuntimeError("synthetic rollback")
    except RuntimeError:
        pass
    unpaid_application.refresh_from_db()
    assert unpaid_application.status == "draft" and unpaid_application.attachments.exists()
    assert not m.Outbox.objects.filter(kind="private_orphan_cleanup").exists()


def test_admin_queue_projection_is_sanitized_paginated_and_retry_is_guarded(client, people):
    secret = "SYNTHETIC-PRIVATE-ERROR-AND-PATH"
    job = m.Outbox.objects.create(key=secret, kind=secret, payload={"object_key": secret}, recipient=people["applicant"], attempts=2, last_error=secret)
    for index in range(51):
        m.Outbox.objects.create(key=f"page:{index}", kind="transcribe")
    url = "/api/system/delivery/"
    login(client, people["admin"])
    listing = client.get(url)
    assert listing.status_code == 200 and secret.encode() not in listing.content
    data = listing.json()
    assert len(data["items"]) == 50 and data["next_offset"] == 50
    assert data["counts"]["failed"] == 1 and data["counts"]["pending"] == 51
    failed = client.get(url, {"state": "failed"}).json()["items"][0]
    assert failed["kind"] == "unsupported" and failed["attempts"] == 2
    retry = f"{url}{job.pk}/retry/"
    assert client.post(retry, {"expected_attempts": 1}, content_type="application/json").json() == {"error": "attempt_conflict", "current_attempts": 2}
    assert client.post(retry, {"expected_attempts": 2}, content_type="application/json").status_code == 200
    assert client.post(retry, {"expected_attempts": 2}, content_type="application/json").status_code == 200
    assert m.AuditEvent.objects.filter(action="delivery_retry_requested").count() == 1
    assert client.get(url, {"state": "failed"}).json()["counts"]["failed"] == 0
    assert client.get(url, {"state": "invalid"}).status_code == 422
    assert client.get(url, {"offset": -1}).status_code == 422
    for role in ["applicant", "member", "president"]:
        login(client, people[role])
        assert client.get(url).status_code == 403
        assert client.post(retry, {"expected_attempts": 2}, content_type="application/json").status_code == 403


@pytest.mark.parametrize("state", ["delivered", "discarded", "leased"])
def test_terminal_or_leased_delivery_cannot_be_manually_retried(people, state):
    fields = {"delivered_at": timezone.now()} if state=="delivered" else {"discarded_at": timezone.now()} if state=="discarded" else {"lease_until": timezone.now()+timezone.timedelta(minutes=5)}
    job = m.Outbox.objects.create(key="terminal", kind="transcribe", attempts=1, last_error="Generic failure", **fields)
    with pytest.raises(ValidationError):
        retry_delivery(people["admin"], job.pk, 1)


def test_database_retains_queue_source_identity(people):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL source guard")
    job = m.Outbox.objects.create(key="retained-source", kind="transcribe", payload={"run": "retained"})
    for values in [{"key": "rebound"}, {"kind": "message"}, {"recipient": people["applicant"]}, {"payload": {}}]:
        with pytest.raises(DatabaseError):
            with transaction.atomic():
                m.Outbox.objects.filter(pk=job.pk).update(**values)


def test_shared_cli_uses_domain_model_readiness_checks():
    with patch("tribunal.services.readiness.database_readiness", return_value={"blockers": ["Synthetic shared gate"]}):
        output = io.StringIO()
        with pytest.raises(CommandError):
            call_command("check_readiness", stdout=output)
    assert "Synthetic shared gate" in output.getvalue()


def test_readiness_detects_public_helpers_unsafe_paths_grants_and_empty_policy():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL readiness metadata")
    with connection.cursor() as cursor:
        cursor.execute("CREATE FUNCTION public.ctm_test_unsafe_readiness() RETURNS integer LANGUAGE sql SECURITY DEFINER AS 'SELECT 1'")
        cursor.execute("GRANT SELECT ON tribunal_case TO PUBLIC")
        cursor.execute("DROP POLICY migration_owner ON tribunal_casenumbercounter")
    report = database_readiness()
    assert "ctm_test_unsafe_readiness" in report["checks"]["public_security_definer_helpers"]
    assert "ctm_test_unsafe_readiness" in report["checks"]["unsafe_security_definer_search_paths"]
    assert "tribunal_case" in report["checks"]["public_domain_table_grants"]
    assert "tribunal_casenumbercounter" in report["checks"]["rls_tables_without_select_policy"]
    assert not report["ready_for_deployment"]


@pytest.mark.django_db(transaction=True)
def test_skip_locked_claim_does_not_wait_for_other_worker():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL skip-locked claim")
    job = m.Outbox.objects.create(key="busy-claim", kind="transcribe")
    started = Event()
    def claim():
        try:
            started.set()
            return claim_delivery(job.pk)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Outbox.objects.select_for_update().get(pk=job.pk)
            future = pool.submit(claim)
            assert started.wait(5)
            assert future.result(timeout=5) == []
