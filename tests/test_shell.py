import json
import re

import pytest
from django.test import override_settings

pytestmark = pytest.mark.django_db


def test_account_login_uses_the_same_universal_shell_without_password_form(client):
    response = client.get("/accounts/login/")
    assert response.status_code == 200
    assert b'id="ctm-root"' in response.content
    assert b'type="password"' not in response.content


def test_public_shell_uses_pinned_cdn_in_required_order_and_csrf(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    html = response.content.decode()
    base = "https://design-system.lighthouseway.org/cdn/0.58.0/"
    files = [
        "theme-boot.js",
        "fonts.css",
        "plenix.css",
        "vendor/react.production.min.js",
        "vendor/react-dom.production.min.js",
        "plenix.js",
    ]
    positions = [html.index(base + name) for name in files]
    assert positions == sorted(positions)
    assert "csrftoken" in response.cookies
    assert response["Cache-Control"] == "no-store"
    assert "style=" not in html


def test_shell_boot_configuration_contains_only_enabled_provider_names(client):
    with override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APPS": [
                    {"client_id": "test-client", "secret": "private-provider-secret"}
                ]
            }
        },
        MICROSOFT_TENANT_ID="",
    ):
        html = client.get("/").content.decode()
    match = re.search(
        r'<script id="ctm-config" type="application/json">(.*?)</script>', html
    )
    assert match
    assert json.loads(match.group(1))["providers"] == ["google"]
    assert "private-provider-secret" not in html
    assert "test-client" not in html


def test_shell_does_not_enable_incomplete_microsoft_configuration(client):
    with override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "microsoft": {"APPS": [{"client_id": "id", "secret": "secret"}]}
        },
        MICROSOFT_TENANT_ID="organizations",
    ):
        html = client.get("/").content.decode()
    match = re.search(
        r'<script id="ctm-config" type="application/json">(.*?)</script>', html
    )
    assert json.loads(match.group(1))["providers"] == []
