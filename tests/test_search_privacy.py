"""Council search is body-only and excludes assessment sources even with consent."""
from unittest.mock import Mock, patch
import pytest
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.reports import create_request
from tribunal.services.search import search, index_text

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("kind", ["medical", "psychological"])
@pytest.mark.parametrize("visibility", ["medical", "own"])
def test_assessments_are_never_indexed_or_returned_from_cached_search(ready_application, people, monkeypatch, kind, visibility):
    app = ready_application
    submit_application(app.owner, app.pk, "search-assessment", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    request = create_request(people["admin"], app.proceeding_id, app.party_id, kind, "Assessment", [])
    attachment = m.Attachment.objects.create(case=app.case, proceeding=app.proceeding,
        owner=app.owner, report_request=request, category="REPORT", visibility=visibility)
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key="assessment/private.pdf",
        original_name="private.pdf", display_name="private.pdf", mime_type="application/pdf",
        byte_count=5, sha256="d" * 64, actor=app.owner)
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    m.MedicalRelease.objects.create(request=request, subject=app.owner, signature=file,
        declaration=m.QuestionnaireVersion.objects.get(purpose="medical_release", published=True), scope={"council": True})
    text = m.DocumentText.objects.create(file=file, text="CONFIDENTIAL ASSESSMENT", engine="test")
    ordinary = app.attachments.get(category="MC").versions.first()
    monkeypatch.setenv("MEILI_URL", "https://search.example.test")
    monkeypatch.setenv("MEILI_MASTER_KEY", "synthetic-test")
    response = Mock()
    response.json.return_value = {"hits": [{"file_id": str(file.pk)}, {"file_id": str(ordinary.pk)}]}
    with patch("tribunal.services.search.requests.post", return_value=response) as post:
        assert index_text(text) is None
        post.assert_not_called()
        for history in [False, True]:
            result = search(people["member"], "assessment", include_history=history)
            assert result["returned_count"] == 1
            assert [row["file_id"] for row in result["items"]] == [str(ordinary.pk)]
            assert "CONFIDENTIAL" not in str(result)


def test_search_post_contract_does_not_accept_query_string(client, people):
    from tests.test_council_contract import login
    login(client, people["member"])
    with patch("tribunal.services.search.search", return_value={"items": [], "returned_count": 0}) as command:
        assert client.get("/api/search/?q=private-name").status_code == 405
        assert not command.called
        response = client.post("/api/search/", data={"q": "body search", "history": True, "case_id": "case-ref"}, content_type="application/json")
        assert response.status_code == 200
        command.assert_called_once_with(people["member"], "body search", True, "case-ref")
        assert client.post("/api/search/", data={"q": "body", "history": "true"}, content_type="application/json").status_code == 422
    login(client, people["applicant"])
    assert client.post("/api/search/", data={"q": "private"}, content_type="application/json").status_code == 403
