"""Actual Django/SQLite account/admin browser checks on disposable synthetic data.

No API interception/provider credentials; does not establish PostgreSQL RLS acceptance.
"""
import json
import os
import sys
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root))
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
from django.conf import settings
run_dir = root / ".tmp" / ("ui-acceptance-" + uuid.uuid4().hex)
run_dir.mkdir(parents=True)
settings.DATABASES["default"]["NAME"] = str(run_dir / "isolated.sqlite3")
settings.MEDIA_ROOT = run_dir / "media"
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
settings.DEBUG = True
import django
django.setup()
from django.core.management import call_command
call_command("migrate", verbosity=0)
from django.test import Client
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from tribunal.models import Account
from tribunal.models import Case, HistoricalWorkspace
from tribunal.services.configuration import save_setting
fixture = SimpleNamespace(**{key: Account.objects.create_user(email=f"{key}@example.test", first_name="UI", last_name=key.title(), role=role) for key, role in [("admin","admin"),("manager","member"),("applicant","applicant")]})

save_setting(fixture.admin, "tribunal_contact", {"email": "office@example.test"}, expected_version=0)
principals = [fixture.admin, fixture.manager, fixture.applicant]
cookies = {}
for account in principals:
    client = Client()
    client.force_login(account, backend="allauth.account.auth_backends.AuthenticationBackend")
    cookies[str(account.pk)] = client.cookies[settings.SESSION_COOKIE_NAME].value

class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass

class LocalServer(WSGIServer):
    # The shell loads many separate static modules; avoid the test server's tiny backlog.
    request_queue_size = 32

server = make_server("127.0.0.1", 0, StaticFilesHandler(get_wsgi_application()), handler_class=Quiet, server_class=LocalServer)
url = f"http://127.0.0.1:{server.server_port}/"
threading.Thread(target=server.serve_forever, daemon=True).start()
checks = []
try:
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for account in principals:
            context = browser.new_context(viewport={"width":1253,"height":1100})
            context.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies[str(account.pk)],"url":url}])
            page = context.new_page()
            historical_posts = []
            page.on("request", lambda request: historical_posts.append(request.post_data_json) if request.method == "POST" and request.url.endswith("/api/historical/") else None)
            page.set_default_timeout(8000)
            errors = []
            page.on("pageerror", lambda error: (errors.append(str(error)), print("BROWSER ERROR", str(error), flush=True)))
            page.goto(url)
            page.locator(".plx-app-header__item--account").click()
            page.get_by_role("menuitem", name="My account", exact=True).click()
            page.locator(".plx-page-content").get_by_text(account.email, exact=True).wait_for()
            page.get_by_role("button", name="Account Settings", exact=True).click()
            link = page.get_by_role("button", name="CTM Administration", exact=True)
            if account.role == "admin":
                link.click()
                page.get_by_role("grid").wait_for()
                page.get_by_role("button", name="Expand Add council member", exact=True).click()
                form = page.get_by_role("form", name="Add council member", exact=True)
                form.get_by_label("First name").fill("UI")
                form.get_by_label("Last name").fill("Enrolled")
                form.get_by_label("Email").fill("ui-enrolled@example.test")
                form.get_by_role("button", name="Add member", exact=True).click()
                page.get_by_text("Council member added.", exact=True).wait_for()
                page.get_by_role("grid").get_by_text("UI Enrolled", exact=True).wait_for()
                page.get_by_role("button", name="Configuration", exact=True).click()
                page.get_by_role("grid").get_by_role("row").nth(1).click()
                page.locator(".plx-reading-pane").get_by_text("office@example.test", exact=True).wait_for()
                page.get_by_role("button", name="System audit", exact=True).click()
                page.get_by_label("Action", exact=True).select_option("council_enrolled")
                page.get_by_role("grid").get_by_text("council_enrolled", exact=True).first.wait_for()
                page.get_by_role("button", name="Historical case entry", exact=True).click()
                historical = page.get_by_role("form", name="Historical case entry", exact=True)
                historical.get_by_label("Original case reference").fill("Legacy / UI-07")
                page.get_by_role("button", name="Configuration", exact=True).click()
                page.get_by_role("button", name="Stay", exact=True).click()
                assert historical.get_by_label("Original case reference").input_value() == "Legacy / UI-07"
                historical.get_by_label("Case status").select_option("closed")
                historical.get_by_label("Name, if known", exact=True).first.fill("Legacy Party")
                historical.get_by_label("Original party reference, if known", exact=True).first.fill("Original-A-07")
                historical.get_by_role("button", name="Save entry", exact=True).click()
                page.get_by_text("Entry saved.", exact=True).wait_for()
                historical.get_by_label("Name, if known", exact=True).first.fill("Legacy Party Corrected")
                original = historical_posts[0]["payload"]
                concurrent = json.loads(json.dumps(original))
                concurrent["parties"][0]["name"] = "Concurrent saved name"
                saved_id = page.get_by_label("Resume saved entry", exact=True).input_value()
                csrf = next(cookie["value"] for cookie in context.cookies() if cookie["name"] == settings.CSRF_COOKIE_NAME)
                response = context.request.post(url + "api/historical/", data={"workspace_id":saved_id,"expected_version":1,"payload":concurrent}, headers={"X-CSRFToken":csrf})
                assert response.status == 201
                historical.get_by_role("button", name="Save entry", exact=True).click()
                page.get_by_text("This record changed. Reload and try again.", exact=True).wait_for()
                assert historical.get_by_label("Name, if known", exact=True).first.input_value() == "Legacy Party Corrected"
                page.get_by_role("button", name="Open entry", exact=True).click()
                page.get_by_role("button", name="Discard and leave", exact=True).click()
                expect(historical.get_by_label("Name, if known", exact=True).first).to_have_value("Concurrent saved name")
                historical.get_by_label("Name, if known", exact=True).first.fill("Legacy Party Corrected")
                historical.get_by_role("button", name="Save entry", exact=True).click()
                page.get_by_text("Entry saved.", exact=True).wait_for()
                assert len(historical_posts) == 3 and historical_posts[1]["expected_version"] == 1 and historical_posts[2]["expected_version"] == 2
                historical.get_by_role("button", name="Publish historical case", exact=True).click()
                page.locator('[role="dialog"], [role="alertdialog"]').get_by_role("button", name="Publish historical case", exact=True).click()
                page.get_by_text("Historical case published.", exact=True).wait_for()
                assert page.get_by_role("button", name="Save entry", exact=True).count() == 0
                page.locator(".plx-page-content").get_by_text("Legacy Party Corrected", exact=True).wait_for()
                page.screenshot(path=str(run_dir / "historical-published.png"))
                page.get_by_role("button", name="Open case", exact=True).click()
                page.get_by_role("heading", name="Legacy / UI-07", exact=True).wait_for()
            else:
                assert link.count() == 0
                assert context.request.get(url + "api/system/audit/").status == 403
                assert context.request.get(url + "api/system/settings/").status == 403
            assert not errors, errors
            checks.append(account.role)
            context.close()
        browser.close()
    assert Account.objects.get(email="ui-enrolled@example.test").role == "member"
    assert Case.objects.get(number="Legacy / UI-07").status == "closed"
    historical = HistoricalWorkspace.objects.get(finalized_case__number="Legacy / UI-07")
    assert historical.version == 3 and historical.payload["parties"][0]["legacy_reference"] == "Original-A-07"
    print(json.dumps({"passed":checks,"database":"isolated SQLite","api_interception":False}))
finally:
    server.shutdown()
    server.server_close()
