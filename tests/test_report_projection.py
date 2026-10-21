import pytest
from tribunal.models import ReportQuestion
from tribunal.services.applications import submit_application
from tribunal.services.reports import create_request, send_request, complete_request

pytestmark = pytest.mark.django_db


def test_report_reading_projection_keeps_sent_questions_and_private_observations(
    client, ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "report-reading", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    ReportQuestion.objects.create(
        code="OPEN-TEST",
        category="Identity",
        wording_en="Please state your name.",
        foundational=True,
    )
    request = create_request(
        people["admin"],
        app.proceeding_id,
        app.party_id,
        "intake",
        "Application clarification",
        [],
    )
    send_request(people["admin"], request.pk)
    report = complete_request(app.owner, request.pk, {"OPEN-TEST": "My response"})
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    row = client.get(f"/api/cases/{app.case_id}/reports/").json()["items"][0]
    assert row["id"] == str(report.pk)
    assert row["questions"] == request.questions
    assert row["questions"][0]["en"] == "Please state your name."
    assert row["kind"] == "intake"
    assert row["version"] == 1
    assert row["observations"] is None
    assert row["subject"] == app.party.name
    assert "external_email" not in row
    assert "token_hash" not in row
