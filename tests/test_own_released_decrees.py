"""Own explicit certificate releases: list and exact original bytes revoke together."""
import hashlib
import pytest
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.decisions import record_decision, approve_decision, attest_signature, issue_decree, release_decree
from tribunal.services.files import write_private_original, private_path

pytestmark = pytest.mark.django_db
PDF = b"%PDF-1.4\nSynthetic test signed-original bytes\n%%EOF"


@pytest.fixture
def issued(ready_application, people, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    app = ready_application
    submit_application(app.owner, app.pk, "own-decree", {"accepted": True, "name": "John Smith"})
    app.refresh_from_db()
    other = m.Account.objects.create_user(email="certificate-other@example.test", email_verified=True)
    party = m.Party.objects.create(case=app.case, account=other, person=other.person, slot="B", name="Other spouse")
    decision = record_decision(people["admin"], app.proceeding_id, "diss-both", "Recorded grounds",
        {str(app.party_id): "certificate", str(party.pk): "certificate"})
    approve_decision(people["president"], decision.pk)
    attachment = m.Attachment.objects.create(case=app.case, proceeding=app.proceeding, category="DEC", visibility="council")
    file = m.FileVersion.objects.create(attachment=attachment, number=1, object_key="certificates/synthetic.pdf",
        original_name="signed.pdf", display_name="signed.pdf", mime_type="application/pdf",
        byte_count=len(PDF), sha256=hashlib.sha256(PDF).hexdigest(), actor=people["admin"])
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    write_private_original(private_path(file.object_key), PDF)
    attest_signature(people["president"], file.pk, people["president"].pk, "signed_scan", {"confirmed_signed": True})
    decree = issue_decree(people["admin"], decision.pk, file.pk, people["president"].pk, "both")
    return app, decree, file, other, party


def login(client, actor):
    client.force_login(actor, backend="allauth.account.auth_backends.AuthenticationBackend")


def test_own_released_decree_projection_and_retained_byte_links_revoke(client, issued, people):
    app, decree, file, other, party = issued
    url = f"/api/cases/{app.case_id}/"
    login(client, app.owner)
    assert client.get(url).json()["released_decrees"] == []
    release = release_decree(people["secretary"], decree.pk, app.party_id)
    detail = client.get(url)
    assert detail["Cache-Control"] == "private, no-store"
    rows = detail.json()["released_decrees"]
    assert rows == [{"id": str(decree.pk), "reference": decree.reference, "language": "bilingual",
        "released_at": release.created_at.isoformat(), "signed_file": {"id": str(file.pk),
        "name": rows[0]["signed_file"]["name"], "scan_state": "clean", "download_url": f"/api/files/{file.pk}/"}}]
    retained = rows[0]["signed_file"]["download_url"]
    response = client.get(retained)
    assert response.status_code == 200 and b"".join(response.streaming_content) == PDF
    assert client.head(retained).status_code == 200
    response = client.get(retained, HTTP_RANGE="bytes=0-7")
    assert response.status_code == 206 and b"".join(response.streaming_content) == PDF[:8]
    response = client.get(retained + "?view=1")
    assert response.status_code == 200 and b"".join(response.streaming_content) == PDF
    login(client, other)
    assert client.get(url).json()["released_decrees"] == []
    assert client.get(retained).status_code in {403, 404}
    login(client, app.owner)
    release_decree(people["secretary"], decree.pk, app.party_id, "withdraw")
    assert client.get(url).json()["released_decrees"] == []
    for method, suffix, kwargs in [("get", "", {}), ("head", "", {}),
        ("get", "", {"HTTP_RANGE": "bytes=0-7"}), ("get", "?view=1", {})]:
        assert getattr(client, method)(retained + suffix, **kwargs).status_code in {403, 404}
    assert m.DecreeRelease.objects.filter(decree=decree, party_id=app.party_id).count() == 2


def test_own_release_scan_gate_does_not_expose_unsigned_or_nonclean_sources(client, issued, people):
    app, decree, file, other, party = issued
    release_decree(people["secretary"], decree.pk, app.party_id)
    login(client, app.owner)
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="pending")
    assert client.get(f"/api/cases/{app.case_id}/").json()["released_decrees"] == []
    assert client.get(f"/api/files/{file.pk}/").status_code in {403, 404}
    m.FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    assert len(client.get(f"/api/cases/{app.case_id}/").json()["released_decrees"]) == 1
