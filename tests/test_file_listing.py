import pytest
from tribunal.models import Account, Attachment, FileVersion, FileTechnicalEvent
from tribunal.services.applications import submit_application

pytestmark = pytest.mark.django_db


@pytest.fixture
def listing(client, ready_application):
    app = ready_application
    submit_application(
        app.owner, app.pk, "files-list", {"accepted": True, "name": "John Smith"}
    )
    app.refresh_from_db()
    client.force_login(
        app.owner, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    return app, f"/api/cases/{app.case_id}/files/"


def test_case_files_include_application_uploads_without_storage_keys(listing, client):
    app, url = listing
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 4
    assert data["next_offset"] is None
    assert all("object_key" not in row and "sha256" not in row for row in data["items"])
    assert all(row["download_url"].startswith("/api/files/") for row in data["items"])


def test_applicant_cannot_list_other_case_or_request_history(listing, client):
    _, url = listing
    assert client.get(url + "?history=1").status_code == 403
    stranger = Account.objects.create_user(
        email="stranger@example.test", email_verified=True
    )
    client.force_login(
        stranger, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert client.get(url).status_code == 403


def test_file_listing_keeps_other_owners_and_council_sources_private(listing, client):
    app, url = listing
    source = app.attachments.get(category="MC").versions.get()
    for owner, visibility in [
        (None, "own"),
        (app.owner, "council"),
        (app.owner, "medical"),
    ]:
        attachment = Attachment.objects.create(
            case=app.case, owner=owner, category="OTHER", visibility=visibility
        )
        version = FileVersion.objects.create(
            attachment=attachment,
            number=1,
            object_key=f"private/{attachment.pk}",
            original_name="private.pdf",
            display_name="private.pdf",
            mime_type="application/pdf",
            byte_count=5,
            sha256=source.sha256,
        )
        FileTechnicalEvent.objects.create(file=version, task="scan", result="clean")
    assert len(client.get(url).json()["items"]) == 4


def test_latest_only_and_explicit_council_history(listing, client, people):
    app, url = listing
    source = app.attachments.get(category="MC").versions.get()
    newer = FileVersion.objects.create(
        attachment=source.attachment,
        number=2,
        object_key="replacement/mc",
        original_name="new.pdf",
        display_name="new.pdf",
        mime_type="application/pdf",
        byte_count=5,
        sha256=source.sha256,
    )
    FileTechnicalEvent.objects.create(file=newer, task="scan", result="clean")
    items = client.get(url).json()["items"]
    assert str(source.pk) not in {x["id"] for x in items}
    assert str(newer.pk) in {x["id"] for x in items}
    client.force_login(
        people["member"], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    assert len(client.get(url + "?history=1").json()["items"]) == 5


def test_pending_latest_is_not_replaced_by_old_clean_version(listing, client):
    app, url = listing
    source = app.attachments.get(category="MC").versions.get()
    FileVersion.objects.create(
        attachment=source.attachment,
        number=2,
        object_key="pending/mc",
        original_name="new.pdf",
        display_name="new.pdf",
        mime_type="application/pdf",
        byte_count=5,
        sha256=source.sha256,
    )
    assert len(client.get(url).json()["items"]) == 3


@pytest.mark.parametrize("offset", ["-1", str(10**40)])
def test_invalid_offset_is_rejected(listing, client, offset):
    _, url = listing
    assert client.get(url, {"offset": offset}).status_code == 422


def test_listing_paginates_without_a_fixed_attachment_count_limit(listing, client):
    app, url = listing
    attachment = Attachment.objects.create(
        case=app.case, owner=app.owner, category="OTHER"
    )
    versions = [
        FileVersion(
            attachment=attachment,
            number=n,
            object_key=f"pages/{n}",
            original_name="item.pdf",
            display_name="item.pdf",
            mime_type="application/pdf",
            byte_count=5,
            sha256="b" * 64,
        )
        for n in range(1, 53)
    ]
    FileVersion.objects.bulk_create(versions)
    FileTechnicalEvent.objects.bulk_create(
        [FileTechnicalEvent(file=row, task="scan", result="clean") for row in versions]
    )
    from tribunal.models import Account

    member = Account.objects.create_user(
        email="history@example.test", role="member", email_verified=True
    )
    client.force_login(
        member, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    first = client.get(url + "?history=1").json()
    second = client.get(url + f"?history=1&offset={first['next_offset']}").json()
    assert len(first["items"]) == 50
    assert len(second["items"]) == 6
    assert second["next_offset"] is None
    assert not {x["id"] for x in first["items"]} & {x["id"] for x in second["items"]}


def test_application_file_access_is_audited_under_its_linked_case(
    listing, client, settings, tmp_path
):
    from tribunal.models import AuditEvent
    from tribunal.services.files import private_path

    app, _ = listing
    settings.MEDIA_ROOT = tmp_path
    source = app.attachments.get(category="MC").versions.get()
    path = private_path(source.object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-test")
    assert client.head(f"/api/files/{source.pk}/").status_code == 200
    assert (
        AuditEvent.objects.get(action="file_metadata_accessed").case_id == app.case_id
    )
