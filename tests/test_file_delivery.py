import pytest
from tribunal.models import Account, AuditEvent
from tribunal.services.files import private_path

pytestmark = pytest.mark.django_db
PAYLOAD = b"0123456789abcdef"


@pytest.fixture
def delivery(client, ready_application, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    file = ready_application.attachments.get(category="MC").versions.get()
    path = private_path(file.object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PAYLOAD)
    client.force_login(
        ready_application.owner,
        backend="allauth.account.auth_backends.AuthenticationBackend",
    )
    return file, f"/api/files/{file.pk}/"


def response_bytes(response):
    try:
        return (
            b"".join(response.streaming_content)
            if response.streaming
            else response.content
        )
    finally:
        response.close()


@pytest.mark.parametrize(
    "header,expected,content_range",
    [
        ("bytes=0-3", b"0123", "bytes 0-3/16"),
        ("bytes=10-", b"abcdef", "bytes 10-15/16"),
        ("bytes=-4", b"cdef", "bytes 12-15/16"),
        ("bytes=12-999", b"cdef", "bytes 12-15/16"),
    ],
)
def test_private_file_supports_single_byte_ranges(
    delivery, client, header, expected, content_range
):
    _, url = delivery
    response = client.get(url, HTTP_RANGE=header)
    assert response.status_code == 206
    assert response["Content-Range"] == content_range
    assert response["Accept-Ranges"] == "bytes"
    assert response["Content-Length"] == str(len(expected))
    assert response_bytes(response) == expected


@pytest.mark.parametrize("header", ["bytes=16-", "bytes=8-3", "bytes=-0"])
def test_unsatisfiable_byte_range_returns_no_source_bytes(delivery, client, header):
    _, url = delivery
    response = client.get(url, HTTP_RANGE=header)
    assert response.status_code == 416
    assert response["Content-Range"] == "bytes */16"
    assert response_bytes(response) == b""


def test_unknown_range_unit_and_multiple_ranges_fall_back_to_full_response(
    delivery, client
):
    _, url = delivery
    for header in ["items=0-3", "bytes=0-1,4-5"]:
        response = client.get(url, HTTP_RANGE=header)
        assert response.status_code == 200
        assert response_bytes(response) == PAYLOAD


def test_if_range_mismatch_returns_full_representation(delivery, client):
    file, url = delivery
    response = client.get(
        url, HTTP_RANGE="bytes=0-3", HTTP_IF_RANGE='"different-version"'
    )
    assert response.status_code == 200
    assert response_bytes(response) == PAYLOAD
    response = client.get(url, HTTP_RANGE="bytes=0-3", HTTP_IF_RANGE=f'"{file.sha256}"')
    assert response.status_code == 206
    assert response_bytes(response) == b"0123"


def test_head_exposes_authorized_metadata_without_a_download_event(delivery, client):
    _, url = delivery
    response = client.head(url, HTTP_RANGE="bytes=0-3")
    assert response.status_code == 200
    assert response["Content-Length"] == "16"
    assert response.content == b""
    assert not AuditEvent.objects.filter(action="file_downloaded").exists()
    assert AuditEvent.objects.filter(action="file_metadata_accessed").exists()


def test_pdf_preview_is_private_inline_and_audited(delivery, client):
    _, url = delivery
    response = client.get(url + "?view=1")
    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("inline;")
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Frame-Options"] == "SAMEORIGIN"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response_bytes(response) == PAYLOAD
    assert AuditEvent.objects.filter(action="file_viewed").exists()


def test_range_requests_do_not_bypass_file_authorization(delivery, client):
    _, url = delivery
    other = Account.objects.create_user(
        email="not-owner@example.test", email_verified=True
    )
    client.force_login(
        other, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    response = client.get(url + "?view=1", HTTP_RANGE="bytes=0-3")
    assert response.status_code == 403
    assert "Content-Range" not in response
    assert not AuditEvent.objects.filter(action="file_viewed").exists()


def test_abandoned_range_response_closes_the_original(delivery, client, monkeypatch):
    from pathlib import Path

    file, url = delivery
    handle = private_path(file.object_key).open("rb")
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: handle)
    response = client.get(url, HTTP_RANGE="bytes=0-3")
    assert response.status_code == 206
    assert not handle.closed
    response.close()
    assert handle.closed


def test_preview_does_not_bypass_latest_scan_result(delivery, client):
    from tribunal.models import FileTechnicalEvent

    file, url = delivery
    FileTechnicalEvent.objects.create(file=file, task="scan", result="infected")
    response = client.get(url + "?view=1", HTTP_RANGE="bytes=0-3")
    assert response.status_code == 403
    assert "ETag" not in response
    assert "Content-Range" not in response
