"""Bounded runtime projections for nonsecret versioned settings."""

from contextlib import contextmanager
from importlib import import_module

import pytest
from django.apps import apps
from django.db import connection, DatabaseError, transaction

from tribunal import models as m
from tribunal.db.context import database_actor
from tribunal.services.applications import submit_application
from tribunal.services.configuration import save_setting


pytestmark = pytest.mark.django_db


@pytest.fixture
def runtime_roles():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL runtime grants")
    with connection.cursor() as cursor:
        for role in ["ctm_app", "ctm_worker"]:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [role])
            if not cursor.fetchone():
                cursor.execute(
                    f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT"
                )
            cursor.execute(f"GRANT {role} TO CURRENT_USER")
        cursor.execute("GRANT USAGE ON SCHEMA public TO ctm_app")
        cursor.execute("GRANT USAGE ON SCHEMA public TO ctm_worker")
    editor = connection.schema_editor(atomic=False)
    for migration in [
        "0038_runtime_grants",
        "0043_request_author_projection",
        "0044_document_category_labels",
        "0046_withdrawal_case_scope",
        "0047_external_status_receipt",
        "0048_message_sender_projection",
        "0051_runtime_settings_consumers",
    ]:
        import_module(f"tribunal.migrations.{migration}").grant_runtime(apps, editor)

    @contextmanager
    def enter(role, actor=None, *, session=False):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SET SESSION AUTHORIZATION {role}"
                    if session
                    else f"SET LOCAL ROLE {role}"
                )
                if session:
                    cursor.execute("SET LOCAL statement_timeout='5s'")
            try:
                with database_actor(actor):
                    yield
            finally:
                if not connection.needs_rollback:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "RESET SESSION AUTHORIZATION" if session else "RESET ROLE"
                        )

    return enter


def login(client, actor):
    client.force_login(
        actor, backend="allauth.account.auth_backends.AuthenticationBackend"
    )


@pytest.fixture
def filed(ready_application):
    submit_application(
        ready_application.owner,
        ready_application.pk,
        "runtime-settings",
        {"accepted": True, "name": "John Smith"},
    )
    ready_application.refresh_from_db()
    return ready_application


def test_authenticated_applicant_reads_only_configured_tribunal_contact(
    client, people
):
    save_setting(
        people["admin"],
        "tribunal_contact",
        {
            "display": "Synthetic Tribunal",
            "email": "contact@example.test",
            "phone": "+1 555 0100",
            "address": "Synthetic address",
        },
        expected_version=0,
    )
    login(client, people["applicant"])

    response = client.get("/api/runtime/tribunal-contact/")

    assert response.status_code == 200
    assert response.json() == {
        "contact": {
            "display": "Synthetic Tribunal",
            "email": "contact@example.test",
            "phone": "+1 555 0100",
            "address": "Synthetic address",
        },
        "version": 1,
    }
    assert response["Cache-Control"] == "private, no-store"


def test_missing_contact_is_explicit_version_zero(client, people):
    login(client, people["member"])

    response = client.get("/api/runtime/tribunal-contact/")

    assert response.status_code == 200
    assert response.json() == {"contact": {}, "version": 0}


@pytest.mark.parametrize(
    "email",
    ["contact@localhost", "contact@[::1]", '"contact@name"@example.test'],
)
def test_schema_valid_contact_email_survives_actual_app_projection(
    client, people, runtime_roles, email
):
    save_setting(
        people["admin"],
        "tribunal_contact",
        {"email": email},
        expected_version=0,
    )
    login(client, people["applicant"])

    with runtime_roles("ctm_app", session=True):
        response = client.get("/api/runtime/tribunal-contact/")

    assert response.json() == {
        "contact": {"email": email},
        "version": 1,
    }


def test_invalid_latest_contact_fails_closed_without_older_fallback(client, people):
    save_setting(
        people["admin"],
        "tribunal_contact",
        {"display": "Older valid contact"},
        expected_version=0,
    )
    m.SettingRevision.objects.create(
        key="tribunal_contact",
        number=2,
        value={"display": "Unsafe partial value", "secret": "do-not-expose"},
        actor=people["admin"],
    )
    login(client, people["applicant"])

    response = client.get("/api/runtime/tribunal-contact/")

    assert response.status_code == 200
    assert response.json() == {"contact": {}, "version": 2}
    assert b"Older valid contact" not in response.content
    assert b"do-not-expose" not in response.content


def test_contact_endpoint_requires_authentication_and_get(client):
    assert client.get("/api/runtime/tribunal-contact/").status_code == 401
    assert client.post("/api/runtime/tribunal-contact/").status_code == 405


def test_council_reads_only_active_matching_recommended_doctors(
    client, people, filed
):
    save_setting(
        people["admin"],
        "recommended_doctors",
        {
            "doctors": [
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Synthetic medical doctor",
                    "specialty": "medical",
                    "contact": "medical@example.test",
                    "active": True,
                },
                {
                    "id": "22222222-2222-4222-8222-222222222222",
                    "name": "Synthetic both-specialty doctor",
                    "specialty": "both",
                    "contact": "both@example.test",
                    "active": True,
                },
                {
                    "id": "33333333-3333-4333-8333-333333333333",
                    "name": "Synthetic psychological doctor",
                    "specialty": "psychological",
                    "contact": "psych@example.test",
                    "active": True,
                },
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "name": "Inactive synthetic doctor",
                    "specialty": "medical",
                    "contact": "inactive@example.test",
                    "active": False,
                },
            ]
        },
        expected_version=0,
    )
    login(client, people["member"])

    response = client.get(
        f"/api/cases/{filed.case_id}/recommended-doctors/",
        {"specialty": "medical"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "name": "Synthetic medical doctor",
                "specialty": "medical",
                "contact": "medical@example.test",
            },
            {
                "id": "22222222-2222-4222-8222-222222222222",
                "name": "Synthetic both-specialty doctor",
                "specialty": "both",
                "contact": "both@example.test",
            },
        ],
        "version": 1,
    }
    assert response["Cache-Control"] == "private, no-store"


def test_applicant_cannot_enumerate_doctors_even_for_own_case(client, people, filed):
    login(client, filed.owner)

    response = client.get(
        f"/api/cases/{filed.case_id}/recommended-doctors/",
        {"specialty": "medical"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"specialty": "both"},
        {"specialty": "MEDICAL"},
        [("specialty", "medical"), ("specialty", "psychological")],
        [("specialty", "medical"), ("extra", "value")],
    ],
)
def test_doctor_projection_requires_one_supported_specialty(
    client, people, filed, query
):
    login(client, people["admin"])

    response = client.get(
        f"/api/cases/{filed.case_id}/recommended-doctors/", query
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation"


def test_missing_and_explicit_empty_doctors_keep_distinct_versions(
    client, people, filed
):
    login(client, people["secretary"])
    url = f"/api/cases/{filed.case_id}/recommended-doctors/"

    missing = client.get(url, {"specialty": "psychological"})
    assert missing.json() == {"items": [], "version": 0}

    save_setting(
        people["admin"],
        "recommended_doctors",
        {"doctors": []},
        expected_version=0,
    )
    empty = client.get(url, {"specialty": "psychological"})
    assert empty.json() == {"items": [], "version": 1}


def test_invalid_latest_doctors_fail_closed_at_latest_version(client, people, filed):
    save_setting(
        people["admin"],
        "recommended_doctors",
        {
            "doctors": [
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Older valid doctor",
                    "specialty": "medical",
                    "contact": "older@example.test",
                    "active": True,
                }
            ]
        },
        expected_version=0,
    )
    m.SettingRevision.objects.create(
        key="recommended_doctors",
        number=2,
        value={
            "doctors": [
                {
                    "id": "22222222-2222-4222-8222-222222222222",
                    "name": "Unsafe latest doctor",
                    "specialty": "medical",
                    "contact": "latest@example.test",
                    "active": "true",
                }
            ],
            "secret": "do-not-expose",
        },
        actor=people["admin"],
    )
    login(client, people["member"])

    response = client.get(
        f"/api/cases/{filed.case_id}/recommended-doctors/",
        {"specialty": "medical"},
    )

    assert response.json() == {"items": [], "version": 2}
    assert b"Older valid doctor" not in response.content
    assert b"Unsafe latest doctor" not in response.content
    assert b"do-not-expose" not in response.content


def test_control_whitespace_in_inactive_doctor_fails_closed_under_actual_app(
    client, people, filed, runtime_roles
):
    m.SettingRevision.objects.create(
        key="recommended_doctors",
        number=1,
        value={
            "doctors": [
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Valid active doctor",
                    "specialty": "medical",
                    "contact": "valid@example.test",
                    "active": True,
                },
                {
                    "id": "22222222-2222-4222-8222-222222222222",
                    "name": "\u001c",
                    "specialty": "medical",
                    "contact": "inactive@example.test",
                    "active": False,
                },
            ]
        },
        actor=people["admin"],
    )
    login(client, people["member"])

    with runtime_roles("ctm_app", session=True):
        response = client.get(
            f"/api/cases/{filed.case_id}/recommended-doctors/",
            {"specialty": "medical"},
        )

    assert response.json() == {"items": [], "version": 1}
    assert b"Valid active doctor" not in response.content


def test_latest_doctor_revision_refreshes_without_process_cache(client, people, filed):
    save_setting(
        people["admin"],
        "recommended_doctors",
        {"doctors": []},
        expected_version=0,
    )
    login(client, people["president"])
    url = f"/api/cases/{filed.case_id}/recommended-doctors/"
    assert client.get(url, {"specialty": "medical"}).json()["version"] == 1

    save_setting(
        people["admin"],
        "recommended_doctors",
        {
            "doctors": [
                {
                    "id": "55555555-5555-4555-8555-555555555555",
                    "name": "New revision doctor",
                    "specialty": "both",
                    "contact": "new@example.test",
                    "active": True,
                }
            ]
        },
        expected_version=1,
    )

    refreshed = client.get(url, {"specialty": "medical"}).json()
    assert refreshed["version"] == 2
    assert [row["name"] for row in refreshed["items"]] == ["New revision doctor"]


def test_runtime_consumer_descriptors_match_the_two_bounded_endpoints(client, people):
    login(client, people["admin"])

    schemas = client.get("/api/system/settings/").json()["schemas"]

    assert schemas["tribunal_contact"]["runtime_consumers"] == [
        "authenticated_tribunal_contact"
    ]
    assert schemas["recommended_doctors"]["runtime_consumers"] == [
        "council_case_recommended_doctors"
    ]


def test_actual_app_reads_projections_without_settings_access_or_writes(
    runtime_roles, filed, people, client
):
    save_setting(
        people["admin"],
        "tribunal_contact",
        {"display": "Restricted synthetic tribunal"},
        expected_version=0,
    )
    save_setting(
        people["admin"],
        "recommended_doctors",
        {
            "doctors": [
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Restricted synthetic doctor",
                    "specialty": "both",
                    "contact": "restricted@example.test",
                    "active": True,
                }
            ]
        },
        expected_version=0,
    )

    login(client, filed.owner)
    with runtime_roles("ctm_app", session=True):
        contact = client.get("/api/runtime/tribunal-contact/")
        assert contact.json() == {
            "contact": {"display": "Restricted synthetic tribunal"},
            "version": 1,
        }
        assert not m.SettingRevision.objects.exists()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolsuper,rolbypassrls,rolinherit FROM pg_roles "
                "WHERE rolname=current_user"
            )
            assert cursor.fetchone() == (False, False, False)
            cursor.execute(
                "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE oid='public.tribunal_settingrevision'::regclass"
            )
            assert cursor.fetchone() == (True, True)
            cursor.execute(
                "SELECT * FROM public.ctm_case_recommended_doctors(%s,%s)",
                [str(filed.case_id), "medical"],
            )
            assert cursor.fetchall() == []
        denied = client.get(
            f"/api/cases/{filed.case_id}/recommended-doctors/?specialty=medical"
        )
        assert denied.status_code == 403
        with pytest.raises(DatabaseError), transaction.atomic():
            m.SettingRevision.objects.create(
                key="tribunal_contact",
                number=2,
                value={"display": "Forbidden write"},
                actor=filed.owner,
            )

    login(client, people["member"])
    with runtime_roles("ctm_app", session=True):
        doctors = client.get(
            f"/api/cases/{filed.case_id}/recommended-doctors/?specialty=medical"
        )
        assert doctors.status_code == 200, doctors.content
        assert doctors.json()["items"][0]["name"] == "Restricted synthetic doctor"
        assert not m.SettingRevision.objects.exists()


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM public.ctm_runtime_tribunal_contact()",
        "SELECT * FROM public.ctm_case_recommended_doctors("
        "'11111111-1111-4111-8111-111111111111','medical')",
    ],
)
def test_runtime_settings_consumers_deny_worker_execution(
    runtime_roles, people, statement
):
    with pytest.raises(DatabaseError):
        with runtime_roles("ctm_worker", people["admin"]), connection.cursor() as cursor:
            cursor.execute(statement)


@pytest.mark.parametrize("specialty", [None, "both", "MEDICAL"])
def test_runtime_doctor_projection_rejects_invalid_direct_specialty(
    runtime_roles, filed, people, specialty
):
    with pytest.raises(DatabaseError):
        with runtime_roles("ctm_app", people["member"]), connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM public.ctm_case_recommended_doctors(%s,%s)",
                [str(filed.case_id), specialty],
            )


def test_missing_empty_and_malformed_settings_fail_closed_under_actual_app(
    runtime_roles, filed, people, client
):
    login(client, filed.owner)
    with runtime_roles("ctm_app", session=True):
        assert client.get("/api/runtime/tribunal-contact/").json() == {
            "contact": {},
            "version": 0,
        }
    login(client, people["member"])
    doctor_url = f"/api/cases/{filed.case_id}/recommended-doctors/?specialty=medical"
    with runtime_roles("ctm_app", session=True):
        assert client.get(doctor_url).json() == {"items": [], "version": 0}

    save_setting(
        people["admin"], "recommended_doctors", {"doctors": []}, expected_version=0
    )
    with runtime_roles("ctm_app", session=True):
        assert client.get(doctor_url).json() == {"items": [], "version": 1}

    m.SettingRevision.objects.create(
        key="tribunal_contact",
        number=1,
        value={"display": "Unsafe contact", "secret": "do-not-expose"},
        actor=people["admin"],
    )
    m.SettingRevision.objects.create(
        key="recommended_doctors",
        number=2,
        value={
            "doctors": [
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Unsafe doctor",
                    "specialty": "medical",
                    "contact": "unsafe@example.test",
                    "active": "true",
                }
            ]
        },
        actor=people["admin"],
    )
    login(client, filed.owner)
    with runtime_roles("ctm_app", session=True):
        response = client.get("/api/runtime/tribunal-contact/")
        assert response.json() == {"contact": {}, "version": 1}
        assert b"do-not-expose" not in response.content
    login(client, people["member"])
    with runtime_roles("ctm_app", session=True):
        response = client.get(doctor_url)
        assert response.json() == {"items": [], "version": 2}
        assert b"Unsafe doctor" not in response.content
