"""#176 / D-0044 service and API: DELETE /api/cases/<id>/.

Admin, president and secretary delete a case by typing its number; the
reason is optional. Members and applicants are refused and nothing changes.
The database function itself is tested in tests/test_case_delete.py.
"""
import pytest

from tribunal import models as m
from tribunal.services.applications import submit_application
from tests.test_core_policy_completion import granted_roles  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


@pytest.fixture
def filed_case(ready_application):
    app = ready_application
    submit_application(app.owner, app.pk, "delete-api", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    return app.case


def delete(granted_roles, client, actor, case, **data):
    client.force_login(actor)
    with granted_roles("ctm_app", session=True):
        return client.delete(f"/api/cases/{case.pk}/", data, content_type="application/json")


@pytest.mark.parametrize("role", ["admin", "president", "secretary"])
def test_council_officers_delete_a_case_by_typing_its_number(granted_roles, client, people, filed_case, role):
    number = filed_case.number
    response = delete(granted_roles, client, people[role], filed_case, confirm_number=number, reason="Loaded by mistake")
    assert response.status_code == 204, response.content
    assert not m.Case.objects.filter(pk=filed_case.pk).exists()
    trace = m.AuditEvent.objects.get(action="case_deleted")
    assert trace.actor_id == people[role].pk and trace.source_id == filed_case.pk
    assert trace.metadata == {"case_number": number, "reason": "Loaded by mistake"}


@pytest.mark.parametrize("role", ["member", "applicant"])
def test_member_and_applicant_are_refused(granted_roles, client, people, filed_case, role):
    response = delete(granted_roles, client, people[role], filed_case, confirm_number=filed_case.number)
    assert response.status_code == 403
    assert m.Case.objects.filter(pk=filed_case.pk).exists()
    assert not m.AuditEvent.objects.filter(action="case_deleted").exists()


@pytest.mark.parametrize("typed", [None, "", "20990101-99", " "])
def test_wrong_or_missing_case_number_deletes_nothing(granted_roles, client, people, filed_case, typed):
    data = {} if typed is None else {"confirm_number": typed}
    response = delete(granted_roles, client, people["admin"], filed_case, **data)
    assert response.status_code == 422
    assert "Type the case number" in response.json()["messages"][0]
    assert m.Case.objects.filter(pk=filed_case.pk).exists()


def test_reason_is_optional_and_bounded(granted_roles, client, people, filed_case):
    response = delete(granted_roles, client, people["secretary"], filed_case,
                      confirm_number=filed_case.number, reason="x" * 501)
    assert response.status_code == 422
    assert m.Case.objects.filter(pk=filed_case.pk).exists()
    response = delete(granted_roles, client, people["secretary"], filed_case, confirm_number=filed_case.number)
    assert response.status_code == 204
    assert m.AuditEvent.objects.get(action="case_deleted").metadata["reason"] is None
