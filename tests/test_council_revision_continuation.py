import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.db import connection, connections, transaction, DatabaseError
from tribunal import models as m
from tribunal.services.council import save_note, save_finding
from tribunal.services.decisions import record_decision, cast_vote
from tribunal.services.historical import stage, publish
from tribunal.validation import VersionConflict
from tests.test_own_requests import filed, login

pytestmark = pytest.mark.django_db


def test_note_edit_versions_replay_and_latest_capability(client, filed, people):
    actor = people["admin"]
    note = save_note(actor, filed.proceeding_id, "Original", expected_version=0)
    save_note(actor, filed.proceeding_id, "Corrected", note.pk, expected_version=1)
    assert save_note(actor, filed.proceeding_id, "Corrected", note.pk, expected_version=1).pk == note.pk
    assert m.NoteRevision.objects.filter(note=note).count() == 2
    with pytest.raises(VersionConflict) as exc:
        save_note(actor, filed.proceeding_id, "Stale", note.pk, expected_version=1)
    assert exc.value.current_version == 2
    with pytest.raises(PermissionDenied):
        save_note(people["secretary"], filed.proceeding_id, "Other author", note.pk, expected_version=2)
    login(client, actor)
    rows = client.get(f"/api/proceedings/{filed.proceeding_id}/notes/").json()["items"]
    assert [row["current"] for row in rows] == [False, True]
    assert [row["can_edit"] for row in rows] == [False, True]


@pytest.mark.parametrize("text", [None, [], " ", "x"*100001, "\x00"])
def test_invalid_note_retains_no_partial_root(filed, people, text):
    with pytest.raises(ValidationError):
        save_note(people["admin"], filed.proceeding_id, text)
    assert not m.CaseNote.objects.exists()


def test_finding_versions_and_scoped_note_citations(client, filed, people):
    actor = people["admin"]
    note = save_note(actor, filed.proceeding_id, "Evidence")
    sources = [{"note_id": str(note.pk)}]
    first = save_finding(actor, filed.proceeding_id, "fact", {"value": "First"}, sources, expected_version=0)
    assert save_finding(actor, filed.proceeding_id, "fact", first.value, sources, expected_version=0).pk == first.pk
    with pytest.raises(VersionConflict):
        save_finding(actor, filed.proceeding_id, "fact", {"value": "Stale"}, sources, expected_version=0)
    other_case = m.Case.objects.create(number="OTHER-CITATION")
    other = m.Proceeding.objects.create(case=other_case)
    foreign_note = save_note(actor, other.pk, "Different source")
    with pytest.raises(ObjectDoesNotExist):
        save_finding(actor, filed.proceeding_id, "foreign", {}, [{"note_id": str(foreign_note.pk)}])
    assert not m.FindingRevision.objects.filter(fact_code="foreign").exists()


def test_finding_file_and_medical_report_sources_keep_authorization(filed, people):
    actor = people["admin"]
    file = m.FileVersion.objects.filter(attachment__application=filed).first()
    row = save_finding(actor, filed.proceeding_id, "document", {"text": "Source"}, [{"file_id": str(file.pk)}])
    assert row.sources == [{"file_id": str(file.pk)}]
    from tribunal.services.reports import create_request
    request = create_request(actor, filed.proceeding_id, filed.party_id, "medical", "Assessment", [])
    report = m.Report.objects.create(request=request, author=filed.owner)
    with pytest.raises(PermissionDenied):
        save_finding(actor, filed.proceeding_id, "medical", {}, [{"report_id": str(report.pk)}])
    assert not m.FindingRevision.objects.filter(fact_code="medical").exists()


@pytest.mark.parametrize("code,value,sources", [(None, {}, []), (" ", {}, []), ("x"*101, {}, []), ("fact", {"bad": float("nan")}, []), ("fact", {}, "source"), ("fact", {}, [{"url": "http://example.test"}]), ("fact", {}, [{"note_id": "bad"}]), ("fact", {}, [{"note_id": []}])])
def test_finding_invalid_sources_and_content(filed, people, code, value, sources):
    with pytest.raises(ValidationError):
        save_finding(people["admin"], filed.proceeding_id, code, value, sources)
    assert not m.FindingRevision.objects.exists()


def test_decision_http_versions_and_exact_retry(client, filed, people):
    login(client, people["admin"])
    url = f"/api/proceedings/{filed.proceeding_id}/decision/"
    assert client.get(url).json()["current_version"] == 0
    assert client.get(url).json()["can_record"]
    payload = {"type": "deferred", "grounds": "Consider evidence", "expected_version": 0}
    first = client.post(url, payload, content_type="application/json")
    assert first.status_code == 201
    assert client.post(url, payload, content_type="application/json").json() == first.json()
    stale = client.post(url, {**payload, "grounds": "Changed"}, content_type="application/json")
    assert stale.status_code == 409 and stale.json()["current_version"] == 1
    assert m.DecisionRevision.objects.count() == 1
    login(client, people["member"])
    assert not client.get(url).json()["can_record"]


@pytest.mark.parametrize("kind,grounds,entitlements,conditions", [([], "Reason", {}, ""), ("deferred", None, {}, ""), ("deferred", "Reason", {"x": []}, ""), ("deferred", "Reason", {}, []), ("deferred", "x"*100001, {}, ""), ("deferred", "Reason", {}, "\x00")])
def test_decision_malformed_content_is_validation(filed, people, kind, grounds, entitlements, conditions):
    with pytest.raises(ValidationError):
        record_decision(people["admin"], filed.proceeding_id, kind, grounds, entitlements, conditions)
    assert not m.DecisionRevision.objects.exists()


def test_vote_key_retains_choice_and_actual_recorder(filed, people):
    decision = record_decision(people["admin"], filed.proceeding_id, "deferred", "Reason", {})
    first = cast_vote(people["admin"], decision.pk, "approve", people["member"].pk, idempotency_key="one")
    assert cast_vote(people["admin"], decision.pk, "approve", people["member"].pk, idempotency_key="one").pk == first.pk
    with pytest.raises(ValidationError):
        cast_vote(people["admin"], decision.pk, "deny", people["member"].pk, idempotency_key="one")
    with pytest.raises(ValidationError):
        cast_vote(people["secretary"], decision.pk, "approve", people["member"].pk, idempotency_key="one")
    assert m.Vote.objects.count() == 1
    cast_vote(people["member"], decision.pk, "deny", idempotency_key="two")
    assert m.Vote.objects.count() == 2


@pytest.mark.parametrize("key", [True, [], " ", "x"*101, "\x00"])
def test_vote_key_is_typed(filed, people, key):
    decision = record_decision(people["admin"], filed.proceeding_id, "deferred", "Reason", {})
    with pytest.raises(ValidationError):
        cast_vote(people["member"], decision.pk, "approve", idempotency_key=key)


def test_historical_private_recovery_compare_publish_and_provenance(client, people):
    actor = people["admin"]
    payload = {"number": "SYNTHETIC-OLD", "status": "closed"}
    workspace = stage(actor, payload)
    changed = {**payload, "parties": [{"slot": "A", "name": "Recorded"}]}
    assert stage(actor, changed, workspace.pk, expected_version=1).version == 2
    assert stage(actor, changed, workspace.pk, expected_version=1).version == 2
    with pytest.raises(VersionConflict):
        stage(actor, payload, workspace.pk, expected_version=1)
    with pytest.raises(VersionConflict):
        publish(actor, workspace.pk, expected_version=1)
    login(client, actor)
    url = f"/api/historical/{workspace.pk}/"
    assert client.get(url).json()["payload"] == changed
    assert client.get(url).json()["version"] == 2
    login(client, people["secretary"])
    assert client.get(url).status_code == 403
    outsider = m.Account.objects.create_user(email="other-admin@example.test", role="admin", email_verified=True)
    login(client, outsider)
    assert client.get(url).status_code == 404
    case = publish(actor, workspace.pk, expected_version=2)
    assert publish(actor, workspace.pk, expected_version=2).pk == case.pk
    if connection.vendor == "postgresql":
        for changes in [{"payload": payload}, {"version": 1}, {"actor": outsider}, {"finalized_case": None}]:
            with pytest.raises(DatabaseError):
                with transaction.atomic():
                    m.HistoricalWorkspace.objects.filter(pk=workspace.pk).update(**changes)


@pytest.mark.parametrize("payload", [{"bad": float("inf")}, {"large": "x"*500001}, {"bad": "\x00"}])
def test_historical_staging_is_strict_and_bounded(people, payload):
    with pytest.raises(ValidationError):
        stage(people["admin"], payload)
    assert not m.HistoricalWorkspace.objects.exists()


def test_historical_version_comparison_matches_jsonb_numeric_semantics(people):
    workspace = stage(people["admin"], {"number": "OLD", "status": "closed", "count": 1})
    assert stage(people["admin"], {"number": "OLD", "status": "closed", "count": 1.0}, workspace.pk, expected_version=1).version == 1
    assert stage(people["admin"], {"number": "OLD", "status": "closed", "count": True}, workspace.pk, expected_version=1).version == 2
    large = stage(people["admin"], {"count": 1e100})
    assert stage(people["admin"], {"count": 10**100}, large.pk, expected_version=1).version == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", ["note", "finding", "decision", "vote", "workspace"])
def test_concurrent_compare_writes_and_vote_replays(filed, people, kind):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row lock contention")
    actor = people["admin"]
    note = save_note(actor, filed.proceeding_id, "Original") if kind == "note" else None
    decision = record_decision(actor, filed.proceeding_id, "deferred", "Original", {}) if kind == "vote" else None
    workspace = stage(actor, {"number": "OLD", "status": "closed"}) if kind == "workspace" else None
    barrier = Barrier(2)
    def save(text):
        try:
            user = m.Account.objects.get(pk=actor.pk)
            barrier.wait(timeout=10)
            try:
                if kind == "note":
                    return str(save_note(user, filed.proceeding_id, text, note.pk, expected_version=1).pk)
                if kind == "finding":
                    return str(save_finding(user, filed.proceeding_id, "fact", {"text": text}, expected_version=0).pk)
                if kind == "decision":
                    return str(record_decision(user, filed.proceeding_id, "deferred", text, {}, expected_version=0).pk)
                if kind == "workspace":
                    return str(stage(user, {"number": text, "status": "closed"}, workspace.pk, expected_version=1).pk)
                return str(cast_vote(user, decision.pk, "approve", people["member"].pk, idempotency_key="concurrent").pk)
            except VersionConflict:
                return "conflict"
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ["One", "Two"]))
    if kind == "vote":
        assert results[0] == results[1] and m.Vote.objects.count() == 1
    else:
        assert results.count("conflict") == 1
