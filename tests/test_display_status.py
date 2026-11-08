"""#259: an open case with no case manager shows "Unassigned".

display_status is derived for the council's case list and case page; the
stored status never changes. Applicants keep the normal status.
"""
import pytest

from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.council import assign_case
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def filed(ready_application):
    app = ready_application
    submit_application(app.owner, app.pk, "status-259", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return app.case


def get(granted_roles, client, actor, url):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.get(url).json()


def test_open_case_without_manager_reads_unassigned(granted_roles, client, people, filed):
    detail = get(granted_roles, client, people["secretary"], f"/api/cases/{filed.pk}/")
    assert detail["status"] == "open" and detail["display_status"] == "unassigned"
    row = next(r for r in get(granted_roles, client, people["secretary"], "/api/cases/")["items"] if r["id"] == str(filed.pk))
    assert row["status"] == "open" and row["display_status"] == "unassigned"
    filed.refresh_from_db()
    assert filed.status == "open"  # never stored


def test_assigned_or_closed_case_reads_its_status(granted_roles, client, people, filed):
    assign_case(people["admin"], filed.pk, people["member"].pk, people["president"].pk)
    assert get(granted_roles, client, people["secretary"], f"/api/cases/{filed.pk}/")["display_status"] == "open"
    closed = m.Case.objects.create(number="20990101-09", origin="synthetic", status="closed")
    row = next(r for r in get(granted_roles, client, people["secretary"], "/api/cases/")["items"] if r["id"] == str(closed.pk))
    assert row["display_status"] == "closed"


def test_applicant_sees_the_normal_status(granted_roles, client, filed):
    owner = filed.parties.get(slot="A").account
    assert get(granted_roles, client, owner, f"/api/cases/{filed.pk}/")["display_status"] == "open"
    row = get(granted_roles, client, owner, "/api/cases/")["items"][0]
    assert row["display_status"] == "open"
