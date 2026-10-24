"""Authoring conflicts, frozen sources, publication validation and retained evidence."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import pytest
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import connection, connections, transaction, DatabaseError
from django.utils import timezone
from tribunal import models as m
from tribunal.services.reports import create_request, send_request, complete_request, revise_report
from tribunal.services.configuration import create_template, save_setting, publish_questionnaire
from tribunal.validation import VersionConflict
from tests.test_own_requests import filed, login

pytestmark = pytest.mark.django_db


@pytest.fixture
def authored_report(filed, people):
    question = m.ReportQuestion.objects.create(code="AUTHOR-Q", category="test", wording_en="Synthetic question")
    request = create_request(people["admin"], filed.proceeding_id, filed.party_id, "interview", "Interview", [question.code])
    send_request(people["admin"], request.pk)
    return complete_request(people["admin"], request.pk, {question.code: "Original"})


def test_report_http_compare_save_conflict_recovery_and_metadata(client, authored_report, people):
    report = authored_report
    login(client, people["admin"])
    url = f"/api/reports/{report.pk}/revisions/"
    row = client.get(url).json()
    assert row["current_version"] == 1 and row["can_revise"]
    answers = {"AUTHOR-Q": "Corrected", "confirmed": True}
    assert client.post(url, {"answers": answers}, content_type="application/json").status_code == 422
    for version in [True, "1", 0, -1]:
        assert client.post(url, {"answers": answers, "expected_version": version}, content_type="application/json").status_code == 422
    payload = {"answers": answers, "expected_version": 1}
    first = client.post(url, payload, content_type="application/json")
    assert first.status_code == 201 and first.json()["version"] == 2
    assert client.post(url, payload, content_type="application/json").json() == first.json()
    changed = client.post(url, {**payload, "answers": {"AUTHOR-Q": "Different"}}, content_type="application/json")
    assert changed.status_code == 409 and changed.json() == {"error": "version_conflict", "current_version": 2}
    # JSON booleans are not equivalent to numeric payloads in replay identity.
    assert client.post(url, {**payload, "answers": {"AUTHOR-Q": "Corrected", "confirmed": 1}}, content_type="application/json").status_code == 409
    assert report.revisions.count() == 2
    login(client, people["member"])
    assert client.get(url).json()["can_revise"] is False
    assert client.post(url, {**payload, "expected_version": 2}, content_type="application/json").status_code == 403
    login(client, report.request.subject.account)
    assert client.get(url).status_code == 403


@pytest.mark.parametrize("answers,observations", [([], ""), ({}, ""), ({"AUTHOR-Q": " "}, ""), ({"AUTHOR-Q": "x"}, []), ({"AUTHOR-Q": "x", "files": "bad"}, ""), ({"AUTHOR-Q": "x", "files": [1]}, ""), ({"AUTHOR-Q": "x", "files": ["invalid"]}, ""), ({"AUTHOR-Q": "x", "bad": float("nan")}, "")])
def test_revision_invalid_content_retains_history(authored_report, people, answers, observations):
    with pytest.raises(ValidationError):
        revise_report(people["admin"], authored_report.pk, answers, observations, expected_version=1)
    assert authored_report.revisions.count() == 1


def test_revision_file_scope_scan_and_current_version(authored_report, people):
    request = authored_report.request
    attachment = m.Attachment.objects.create(case=request.case, proceeding=request.proceeding,
        report_request=request, owner=request.subject.account, category="REPORT", visibility="own")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key="synthetic-report-source",
        original_name="report.pdf", display_name="report.pdf", mime_type="application/pdf", byte_count=5, sha256="a"*64)
    def revise(ids):
        return revise_report(people["admin"], authored_report.pk, {"AUTHOR-Q": "Evidence", "files": ids}, expected_version=1)
    with pytest.raises(ValidationError):
        revise([str(file.pk)])
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    with pytest.raises(ValidationError):
        revise([str(file.pk), str(file.pk)])
    unrelated = m.FileVersion.objects.filter(attachment__application__owner=request.subject.account).first()
    with pytest.raises(PermissionDenied):
        revise([str(unrelated.pk)])
    revision = revise([str(file.pk)])
    assert revision.number == 2 and revision.answers["files"] == [str(file.pk)]
    later = m.FileVersion.objects.create(attachment=attachment, number=2, object_key="synthetic-new-report-source",
        original_name="report.pdf", display_name="report.pdf", mime_type="application/pdf", byte_count=5, sha256="b"*64)
    with pytest.raises(ValidationError):
        revise_report(people["admin"], authored_report.pk, {"AUTHOR-Q": "Superseded", "files": [str(file.pk)]}, expected_version=2)
    with pytest.raises(ValidationError):
        revise_report(people["admin"], authored_report.pk, {"AUTHOR-Q": "Unsafe", "files": [str(later.pk)]}, expected_version=2)
    assert authored_report.revisions.count() == 2


def test_medical_revision_requires_own_exact_signed_scope(filed, people):
    request = create_request(people["admin"], filed.proceeding_id, filed.party_id, "medical", "Synthetic assessment", [])
    report = m.Report.objects.create(request=request, author=people["admin"])
    m.ReportRevision.objects.create(report=report, number=1, actor=people["admin"], answers={"legacy": "Retained source"})
    with pytest.raises(PermissionDenied):
        revise_report(people["admin"], report.pk, {"response": "Not authorized"}, expected_version=1)
    assert report.revisions.count() == 1


def test_report_retry_after_closure_does_not_authorize_new_narrative(authored_report, people, client):
    report = authored_report
    first = revise_report(people["admin"], report.pk, {"AUTHOR-Q": "Retained"}, expected_version=1)
    m.Proceeding.objects.filter(pk=report.request.proceeding_id).update(status="closed")
    assert revise_report(people["admin"], report.pk, first.answers, expected_version=1).pk == first.pk
    with pytest.raises(ValidationError):
        revise_report(people["admin"], report.pk, {"AUTHOR-Q": "New"}, expected_version=2)
    login(client, people["admin"])
    assert client.get(f"/api/reports/{report.pk}/revisions/").json()["can_revise"] is False


@pytest.mark.django_db(transaction=True)
def test_concurrent_report_saves_reject_one_stale_writer(authored_report, people):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row-lock contention")
    barrier = Barrier(2)
    def save(text):
        try:
            actor = m.Account.objects.get(pk=people["admin"].pk)
            barrier.wait(timeout=10)
            try:
                return revise_report(actor, authored_report.pk, {"AUTHOR-Q": text}, expected_version=1).number
            except VersionConflict as exc:
                return ("conflict", exc.current_version)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(save, ["One", "Two"]))
    assert 2 in result and ("conflict", 2) in result
    assert authored_report.revisions.count() == 2


@pytest.mark.django_db(transaction=True)
def test_revision_waits_for_proceeding_closure(authored_report, people):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL closure lock")
    started = Event()
    def save():
        try:
            actor = m.Account.objects.get(pk=people["admin"].pk)
            started.set()
            with pytest.raises(ValidationError):
                revise_report(actor, authored_report.pk, {"AUTHOR-Q": "After closure"}, expected_version=1)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            proceeding = m.Proceeding.objects.select_for_update().get(pk=authored_report.request.proceeding_id)
            future = pool.submit(save)
            assert started.wait(5)
            proceeding.status = "closed"
            proceeding.save(update_fields=["status"])
        future.result(timeout=10)
    assert authored_report.revisions.count() == 1


@pytest.mark.parametrize("title,questions,shared", [(None, [], False), (" ", [], False), ("T"*201, [], False), ("T", [], "false"), ("T", "Q", False), ("T", ["Q", "Q"], False), ("T", [{}], False)])
def test_invalid_template_is_atomic(people, title, questions, shared):
    with pytest.raises(ValidationError):
        create_template(people["admin"], title, questions, shared)
    assert not m.ReportTemplate.objects.exists()


@pytest.mark.parametrize("definition", [
    {"fields": {}}, {"fields": [None]},
    {"fields": [{"code": "x", "type": "text"}, {"code": "x", "type": "text"}]},
    {"fields": [{"code": 1, "type": "text"}]},
    {"fields": [{"code": "x", "type": "text", "required": "false"}]},
    {"fields": [{"code": "x", "type": "choice", "choices": ["a", "a"]}]},
    {"fields": [{"code": "x", "type": "choice", "choices": []}]},
    {"fields": [{"code": "x", "type": "text", "when": {"field": "missing", "equals": "x"}}]},
    {"fields": [{"code": "x", "type": "text", "when": {"field": "x", "equals": "x"}}]},
    {"fields": [{"code": "x", "type": "text", "when": {"field": "y", "equals": "x"}}, {"code": "y", "type": "text", "when": {"field": "x", "equals": "y"}}]},
    {"fields": [{"code": "x", "type": "boolean"}, {"code": "y", "type": "text", "when": {"field": "x", "equals": "true"}}]},
    {"required_document_categories": "MC"}, {"required_document_categories": ["MC", "MC"]}, {"required_document_categories": ["unsupported"]},
])
def test_invalid_questionnaire_never_publishes_or_rebinds(people, unpaid_application, definition):
    original = unpaid_application.questionnaire_id
    before = m.QuestionnaireVersion.objects.count()
    with pytest.raises(ValidationError):
        publish_questionnaire(people["admin"], "petition", definition, "Synthetic EN", "إقرار تجريبي")
    unpaid_application.refresh_from_db()
    assert unpaid_application.questionnaire_id == original and m.QuestionnaireVersion.objects.count() == before


@pytest.mark.parametrize("en,ar", [(None, "AR"), ("EN", []), (" ", "AR"), ("EN", " ")])
def test_declarations_are_typed_bilingual_inputs(people, en, ar):
    with pytest.raises(ValidationError):
        publish_questionnaire(people["admin"], "petition", {}, en, ar)


def test_valid_conditional_questionnaire_rebinds_without_erasing_answers(people, unpaid_application):
    definition = {"fields": [{"code": "flag", "type": "boolean"}, {"code": "explanation", "type": "text", "required": True, "when": {"field": "flag", "equals": True}}], "required_document_categories": ["CMC"]}
    version = publish_questionnaire(people["admin"], "petition", definition, "Synthetic EN", "إقرار تجريبي")
    unpaid_application.refresh_from_db()
    assert unpaid_application.questionnaire_id == version.pk and unpaid_application.revisions.count() == 1
    from tribunal.validation import validate_answers
    validate_answers(version, {"flag": False})
    with pytest.raises(ValidationError):
        validate_answers(version, {"flag": True})


@pytest.mark.parametrize("value", [{"nested": [{"API-Key": "synthetic"}]}, {"ClientSecret": "synthetic"}, {"Authorization": "synthetic"}, {"access token": "synthetic"}, {"number": float("inf")}, {1: "not-string-key"}, {"oversize": "x"*100_001}, {"text": "\x00"}, {"text": "\ud800"}])
def test_settings_reject_secret_variants_and_non_json(people, value):
    with pytest.raises(ValidationError):
        save_setting(people["admin"], "tribunal_contact", value)
    assert not m.SettingRevision.objects.exists()


def test_settings_compare_save_keeps_both_attributed_revisions(client, people):
    first = save_setting(people["admin"], "tribunal_contact", {"display": "First"}, expected_version=0)
    login(client, people["secretary"])
    response = client.post("/api/system/settings/", {"key": "tribunal_contact", "value": {"display": "Stale"}, "expected_version": 0}, content_type="application/json")
    assert response.status_code == 409 and response.json()["current_version"] == 1
    second = save_setting(people["secretary"], "tribunal_contact", {"display": "Second"}, expected_version=1)
    assert second.number == 2 and first.actor_id != second.actor_id


def test_settings_nested_content_is_bounded(people):
    value = "leaf"
    for _ in range(22):
        value = {"child": value}
    with pytest.raises(ValidationError):
        save_setting(people["admin"], "tribunal_contact", value)


@pytest.mark.django_db(transaction=True)
def test_settings_compare_save_serializes_concurrent_admins(people):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL advisory-lock contention")
    barrier = Barrier(2)
    def save(role):
        try:
            actor = m.Account.objects.get(pk=people[role].pk)
            barrier.wait(timeout=10)
            try:
                return save_setting(actor, "tribunal_contact", {"display": role}, expected_version=0).number
            except VersionConflict as exc:
                return ("conflict", exc.current_version)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(save, ["admin", "secretary"]))
    assert 1 in result and ("conflict", 1) in result
    assert m.SettingRevision.objects.filter(key="tribunal_contact").count() == 1
