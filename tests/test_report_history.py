import pytest
from tribunal.services.applications import submit_application
from tribunal.services.reports import (
    create_request,
    send_request,
    complete_request,
    revise_report,
)

pytestmark = pytest.mark.django_db


def test_council_can_read_all_report_revisions_but_applicant_cannot(
    client, ready_application, people
):
    app = ready_application
    submit_application(
        app.owner, app.pk, "report-history", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    request = create_request(
        people["admin"], app.proceeding_id, app.party_id, "interview", "Interview", []
    )
    send_request(people["admin"], request.pk)
    report = complete_request(
        people["admin"], request.pk, {"answer": "Original"}, "Original observation"
    )
    revise_report(
        people["admin"], report.pk, {"answer": "Corrected"}, "Corrected observation", expected_version=1
    )
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.get(f"/api/reports/{report.pk}/revisions/")
    assert response.status_code == 200
    rows = response.json()["items"]
    assert [x["version"] for x in rows] == [2, 1]
    assert rows[0]["answers"]["answer"] == "Corrected"
    assert rows[1]["answers"]["answer"] == "Original"
    assert rows[0]["actor"] == "admin Test"
    assert rows[0]["timestamp"]
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert client.get(f"/api/reports/{report.pk}/revisions/").status_code == 403


def test_medical_report_history_requires_its_signed_council_disclosure(
    client, ready_application, people
):
    from tribunal.models import Report, ReportRevision

    app = ready_application
    submit_application(
        app.owner, app.pk, "medical-history", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    request = create_request(
        people["admin"], app.proceeding_id, app.party_id, "medical", "Assessment", []
    )
    # Synthetic historical source whose disclosure has not been granted to council.
    report = Report.objects.create(request=request, author=app.owner)
    ReportRevision.objects.create(
        report=report,
        number=1,
        actor=app.owner,
        answers={"private": "Medical narrative"},
    )
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.get(f"/api/reports/{report.pk}/revisions/")
    assert response.status_code == 403
    assert b"Medical narrative" not in response.content
