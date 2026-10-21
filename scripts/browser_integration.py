"""Local real-API browser regression using an isolated synthetic SQLite database.

No mocked API responses, production credentials, provider login or public service.
Run with the optional browser dependency group. Fixture sessions are issued by
Django's test client; the application contains no test-login HTTP endpoint.
"""

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid
from pathlib import Path
from datetime import date
from wsgiref.simple_server import WSGIRequestHandler, make_server

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root))
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
from django.conf import settings

run_dir = root / ".tmp" / ("browser-integration-" + uuid.uuid4().hex)
run_dir.mkdir(parents=True)
settings.DATABASES["default"]["NAME"] = str(run_dir / "isolated.sqlite3")
settings.MEDIA_ROOT = run_dir / "media"
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
settings.DEBUG = True
import django

django.setup()
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from tribunal.models import (
    Account,
    Case,
    Proceeding,
    Party,
    ReportQuestion,
    Notification,
    Message,
)
from tribunal.services.council import create_session
from tribunal.models import Attendance
from tribunal.services.files import upload
from tribunal.services.reports import create_request, send_request, complete_request

call_command("migrate", verbosity=0, interactive=False)
manager = Account.objects.create_user(
    email="manager@example.test",
    first_name="Council",
    last_name="Tester",
    role="member",
    email_verified=True,
)
applicant = Account.objects.create_user(
    email="applicant@example.test",
    first_name="Applicant",
    last_name="Tester",
    email_verified=True,
)
outsider = Account.objects.create_user(
    email="outsider@example.test", email_verified=True
)
admin = Account.objects.create_user(
    email="admin@example.test",
    first_name="Admin",
    last_name="Tester",
    role="admin",
    email_verified=True,
)
session = create_session(admin, date(2030, 1, 2))
case = Case.objects.create(number="20261021-01", assigned_member=manager)
proceeding = Proceeding.objects.create(case=case)
party = Party.objects.create(
    case=case, account=applicant, slot="A", name="Applicant Tester", participating=True
)
ReportQuestion.objects.create(
    code="OPEN-TEST",
    category="Identity",
    wording_en="Please state your full name.",
    foundational=True,
)
request = create_request(
    manager, proceeding.pk, party.pk, "intake", "Marriage clarification", []
)
send_request(manager, request.pk)
report = complete_request(applicant, request.pk, {"OPEN-TEST": "Applicant Tester"})
source = upload(
    manager,
    SimpleUploadedFile("marriage.pdf", b"%PDF-1.4\nSynthetic browser validation only."),
    "MC",
    case_id=case.pk,
)

# The generated synthetic session is the same mechanism used by Django tests.
fixture_client = Client()
fixture_client.force_login(
    manager, backend="allauth.account.auth_backends.AuthenticationBackend"
)
session_cookie = fixture_client.cookies[settings.SESSION_COOKIE_NAME].value


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


server = make_server(
    "127.0.0.1", 18842, StaticFilesHandler(get_wsgi_application()), handler_class=Quiet
)
threading.Thread(target=server.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright

pool = ThreadPoolExecutor(max_workers=1)


def database_check(fn):
    return pool.submit(fn).result()


def fixture_cookie(account):
    client = Client()
    client.force_login(
        account, backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    return client.cookies[settings.SESSION_COOKIE_NAME].value


try:
    with sync_playwright() as p:
        args = (
            [
                f"--host-resolver-rules=MAP design-system.lighthouseway.org {os.environ['CTM_CDN_LAN_IP']}"
            ]
            if os.environ.get("CTM_CDN_LAN_IP")
            else []
        )
        browser = p.chromium.launch(
            executable_path=os.environ.get(
                "CTM_BROWSER_EXECUTABLE", p.chromium.executable_path
            ),
            headless=True,
            args=args,
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie,
                    "url": "http://127.0.0.1:18842/",
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ]
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:18842/", wait_until="domcontentloaded")
        page.get_by_role("heading", name="Home", exact=True).wait_for()
        page.get_by_role("button", name="Notifications", exact=True).click()
        page.get_by_text("A report was received.", exact=True).wait_for()
        page.get_by_role("button", name="Mark as read", exact=True).click()
        page.get_by_role("button", name="Mark as read", exact=True).wait_for(
            state="detached"
        )
        assert (
            database_check(
                lambda: (
                    Notification.objects.get(
                        recipient=manager, kind="report_received"
                    ).read_at
                )
            )
            is not None
        )
        page.get_by_role("button", name="Open case", exact=True).click()
        page.get_by_role("heading", name=case.number, exact=True).wait_for()
        page.get_by_role("button", name="Documents", exact=True).click()
        page.get_by_role("heading", name="Documents", exact=True).wait_for()
        page.get_by_role("button", name=source.display_name, exact=True).click()
        page.get_by_role("button", name="Download", exact=True).wait_for()
        response = context.request.get(
            f"http://127.0.0.1:18842/api/files/{source.pk}/?view=1",
            headers={"Range": "bytes=0-3"},
        )
        assert response.status == 206 and response.body() == b"%PDF"
        assert response.headers["cache-control"] == "private, no-store"
        page.get_by_role("button", name="Reports", exact=True).click()
        page.get_by_role("button", name="Marriage clarification", exact=True).click()
        page.get_by_text("Please state your full name.", exact=True).wait_for()
        page.get_by_role("button", name="Communications", exact=True).click()
        page.get_by_role("checkbox", name="Applicant Tester", exact=True).check()
        page.get_by_role("textbox", name="Message", exact=True).fill(
            "Real API browser verification message"
        )
        page.get_by_role("button", name="Send", exact=True).click()
        page.get_by_text("Real API browser verification message", exact=True).wait_for()
        assert (
            database_check(
                lambda: Message.objects.filter(
                    case=case, body="Real API browser verification message"
                ).count()
            )
            == 1
        )
        assert not errors, errors
        page.screenshot(path=str(run_dir / "real-api-council.png"), full_page=True)
        # A separate authenticated applicant account cannot see this case or its files.
        outsider_cookie = database_check(lambda: fixture_cookie(outsider))
        other = browser.new_context()
        other.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": outsider_cookie,
                    "url": "http://127.0.0.1:18842/",
                }
            ]
        )
        assert (
            other.request.get(f"http://127.0.0.1:18842/api/cases/{case.pk}/").status
            == 403
        )
        assert (
            other.request.get(
                f"http://127.0.0.1:18842/api/files/{source.pk}/?view=1"
            ).status
            == 403
        )
        applicant_cookie = database_check(lambda: fixture_cookie(applicant))
        own = browser.new_context()
        own.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": applicant_cookie,
                    "url": "http://127.0.0.1:18842/",
                }
            ]
        )
        assert (
            own.request.get(f"http://127.0.0.1:18842/api/cases/{case.pk}/").status
            == 200
        )
        assert (
            own.request.get(f"http://127.0.0.1:18842/api/files/{source.pk}/").status
            == 403
        )
        own_report = own.request.get(
            f"http://127.0.0.1:18842/api/cases/{case.pk}/reports/"
        ).json()["items"][0]
        assert own_report["answers"]["OPEN-TEST"] == "Applicant Tester"
        assert own_report["observations"] is None
        admin_cookie = database_check(lambda: fixture_cookie(admin))
        administrative = browser.new_context(viewport={"width": 1440, "height": 1000})
        administrative.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": admin_cookie,
                    "url": "http://127.0.0.1:18842/",
                }
            ]
        )
        attendance_page = administrative.new_page()
        attendance_page.on("pageerror", lambda error: errors.append(str(error)))
        attendance_page.goto("http://127.0.0.1:18842/", wait_until="domcontentloaded")
        attendance_page.get_by_role("heading", name="Home", exact=True).wait_for()
        attendance_page.get_by_role(
            "button", name="Tribunal Sessions", exact=True
        ).click()
        attendance_page.get_by_role(
            "button", name="Council Session 2030-01-02", exact=True
        ).click()
        group = attendance_page.get_by_role("group", name="Council Tester", exact=True)
        group.get_by_role("radio", name="Present", exact=True).check()
        group.get_by_role("radio", name="Present", exact=True).wait_for()
        attendance_page.wait_for_function(
            "() => !Array.from(document.querySelectorAll('input[type=radio]')).some(input=>input.disabled && input.value==='present')"
        )
        assert (
            database_check(
                lambda: (
                    Attendance.objects.get(
                        session=session, member=manager, hearing__isnull=True
                    ).present
                )
            )
            is True
        )
        attendance_page.screenshot(path=str(run_dir / "attendance.png"), full_page=True)
        assert not errors, errors
        browser.close()
        print(
            json.dumps(
                {
                    "status": "passed",
                    "real_api": True,
                    "provider_login": False,
                    "database": "isolated synthetic SQLite",
                    "report_question_snapshot": True,
                    "notification_read_persisted": True,
                    "attendance_persisted": True,
                    "message_persisted": True,
                    "private_range": 206,
                    "other_applicant_denied": True,
                    "browser_errors": errors,
                    "artifacts": str(run_dir),
                }
            )
        )
finally:
    pool.shutdown()
    server.shutdown()
    server.server_close()
