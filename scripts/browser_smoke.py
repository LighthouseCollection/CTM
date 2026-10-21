"""Real-CDN component smoke with synthetic API fixtures, not an identity-provider E2E test.
Run: uv sync --group browser; uv run --group browser python scripts/browser_smoke.py
Optional CTM_CDN_LAN_IP bypasses public hairpin DNS with normal TLS validation.
Install the compatible Chromium once: uv run --group browser playwright install chromium
"""

import os, sys, json, threading
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
(root / ".tmp").mkdir(exist_ok=True)
sys.path.insert(0, str(root))
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
import django

django.setup()
from django.conf import settings

settings.DEBUG = True
settings.SOCIALACCOUNT_PROVIDERS = {
    "google": {"APPS": [{"client_id": "synthetic-only", "secret": "synthetic-only"}]}
}
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server, WSGIRequestHandler


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


server = make_server(
    "127.0.0.1", 18841, StaticFilesHandler(get_wsgi_application()), handler_class=Quiet
)
threading.Thread(target=server.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    executable = os.environ.get("CTM_BROWSER_EXECUTABLE", p.chromium.executable_path)
    browser = p.chromium.launch(
        executable_path=str(executable),
        headless=True,
        args=(
            [
                f"--host-resolver-rules=MAP design-system.lighthouseway.org {os.environ['CTM_CDN_LAN_IP']}"
            ]
            if os.environ.get("CTM_CDN_LAN_IP")
            else []
        ),
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: (errors.append(str(e)), print("BROWSER ERROR:", e, flush=True)))
    page.goto("http://127.0.0.1:18841/", wait_until="networkidle")
    page.get_by_role("heading", name="Sign in to CTM").wait_for()
    page.screenshot(path=".tmp/ctm-login.png", full_page=True)
    page.get_by_role("button", name="العربية", exact=True).click()
    page.get_by_role("heading", name="تسجيل الدخول", exact=True).wait_for()
    assert page.locator("html").get_attribute("dir") == "rtl"
    page.get_by_role("button", name="English", exact=True).click()
    page.route(
        "**/api/session/",
        lambda r: r.fulfill(
            json={
                "id": "synthetic",
                "name": "Council Tester",
                "role": "member",
                "portal": "council",
                "ui_language": "en",
                "csrf_token": "synthetic",
            }
        ),
    )
    page.route(
        "**/api/cases/",
        lambda r: r.fulfill(
            json={
                "items": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "number": "20261021-01",
                        "status": "open",
                        "assigned_member": "Council Tester",
                    }
                ]
            }
        ),
    )
    page.route(
        "**/api/cases/11111111-1111-1111-1111-111111111111/",
        lambda r: r.fulfill(
            json={
                "id": "11111111-1111-1111-1111-111111111111",
                "number": "20261021-01",
                "status": "open",
                "can_message": True,
                "parties": [
                    {
                        "id": "party",
                        "name": "Test Party",
                        "can_receive": True,
                        "is_self": False,
                    }
                ],
                "proceedings": [
                    {
                        "id": "proceeding",
                        "kind": "initial",
                        "status": "open",
                        "sequence": 0,
                    }
                ],
            }
        ),
    )
    messages = []

    def messages_route(route):
        if route.request.method == "POST":
            payload = route.request.post_data_json
            assert payload["party_ids"] == ["party"]
            assert route.request.headers.get("x-csrftoken")
            messages.append(
                {
                    "id": "message",
                    "sender": "Council Tester",
                    "body": payload["body"],
                    "timestamp": "2026-10-21T20:00:00Z",
                    "file_links": [],
                }
            )
            route.fulfill(status=201, json={"id": "message"})
        else:
            route.fulfill(json={"items": messages})

    page.route(
        "**/api/cases/11111111-1111-1111-1111-111111111111/messages/", messages_route
    )
    page.route("**/api/sessions/", lambda r: r.fulfill(json={"items": []}))
    def preferences_route(route):
        assert route.request.method=='POST'
        values={'ui_language':'en','notification_language':'en'}
        values.update(route.request.post_data_json)
        route.fulfill(json=values)
    page.route('**/api/account/settings/',preferences_route)
    page.reload(wait_until="networkidle")
    page.get_by_role("heading", name="Home", exact=True).wait_for()
    page.screenshot(path=".tmp/ctm-council-home.png", full_page=True)
    page.get_by_role("button", name="Cases", exact=True).click()
    page.get_by_role("heading", name="Cases", exact=True).wait_for()
    page.get_by_role("button", name="Cases", exact=True).click()
    page.get_by_role("heading", name="Cases", exact=True).wait_for(timeout=2000)
    page.get_by_role("button", name="20261021-01", exact=True).click()
    page.get_by_role("heading", name="20261021-01", exact=True).wait_for()
    page.route("**/api/cases/*/files/?*", lambda r: r.fulfill(json={"items":[{"id":"file-one","name":"20261021-01-MC-20261021-1200.pdf","category":"MC","version":1,"mime_type":"application/pdf","download_url":"/api/files/file-one/","preview_url":"/api/files/file-one/?view=1"}],"next_offset":None}))
    page.get_by_role("button", name="Documents", exact=True).click()
    page.get_by_role("heading", name="Documents", exact=True).wait_for()
    page.get_by_role("button", name="20261021-01-MC-20261021-1200.pdf", exact=True).click()
    page.get_by_role("button", name="Download", exact=True).wait_for()
    page.get_by_role("checkbox", name="Include older versions", exact=True).check()
    page.get_by_role("button", name="20261021-01-MC-20261021-1200.pdf", exact=True).wait_for()
    page.get_by_role("button", name="20261021-01-MC-20261021-1200.pdf", exact=True).click()
    page.get_by_role("button", name="Download", exact=True).wait_for()
    page.screenshot(path=".tmp/ctm-documents.png", full_page=True)
    print("Document runtime styles:", page.locator("#ctm-root [style]").evaluate_all("els=>els.map(e=>({tag:e.tagName,cls:e.className,style:e.getAttribute('style')}))"))
    page.set_viewport_size({"width":390,"height":844})
    assert page.locator("body").evaluate("e=>e.scrollWidth") <= 390
    page.screenshot(path=".tmp/ctm-documents-mobile.png", full_page=True)
    page.set_viewport_size({"width":1440,"height":1000})
    page.route("**/api/cases/*/reports/", lambda r: r.fulfill(json={"items":[{"id":"report-one","title":"Marriage interview","kind":"interview","date":"2026-10-21","version":1,"subject":"Test Party","questions":[{"code":"OPEN-01","en":"Please state your full name."}],"answers":{"OPEN-01":"Test Party"},"observations":"Internal observation","parent_report_id":None}]}))
    page.get_by_role("button", name="Reports", exact=True).click()
    page.get_by_role("heading", name="Reports", exact=True).wait_for()
    page.get_by_role("button", name="Marriage interview", exact=True).click()
    page.get_by_text("Please state your full name.", exact=True).wait_for()
    page.get_by_text("Internal observation", exact=True).wait_for()
    page.screenshot(path=".tmp/ctm-reports.png", full_page=True)
    page.get_by_role("button", name="Communications", exact=True).click()
    page.get_by_role("heading", name="Communications", exact=True).wait_for()
    page.get_by_role("checkbox", name="Test Party", exact=True).check()
    page.get_by_role("textbox", name="Message", exact=True).fill(
        "Browser verification message"
    )
    page.get_by_role('button',name='العربية',exact=True).click()
    page.get_by_role('heading',name='المراسلات',exact=True).wait_for()
    assert page.get_by_role('textbox',name='الرسالة',exact=True).input_value()=='Browser verification message'
    assert page.get_by_role('checkbox',name='Test Party',exact=True).is_checked()
    page.screenshot(path='.tmp/ctm-communications-arabic.png',full_page=True)
    page.get_by_role('button',name='English',exact=True).click()
    page.get_by_role('heading',name='Communications',exact=True).wait_for()
    page.get_by_role("button", name="Send", exact=True).click()
    page.get_by_text("Browser verification message", exact=True).wait_for()
    assert len(messages) == 1
    page.get_by_role("button", name="Back to cases", exact=True).click()
    page.get_by_role("heading", name="Cases", exact=True).wait_for()
    page.get_by_role("button", name="Council Tester", exact=True).click()
    page.get_by_role("menuitem", name="My Profile", exact=True).click()
    page.get_by_role("heading", name="Profile", exact=True).wait_for()
    page.get_by_role("button", name="Home", exact=True).click()
    page.get_by_role("heading", name="Home", exact=True).wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=".tmp/ctm-council-mobile.png", full_page=True)
    print(
        json.dumps(
            {
                "browser_errors": errors,
                "body_scroll_width": page.locator("body").evaluate(
                    "(e)=>e.scrollWidth"
                ),
                "viewport": 390,
                "app_inline_styles": page.locator("#ctm-root [style]").count(),
                "rendered_text": page.locator("body").inner_text()[:600],
            }
        )
    )
    assert not errors, errors
    assert page.locator("body").evaluate("(e)=>e.scrollWidth") <= 390
    applicant = browser.new_page(viewport={"width": 1440, "height": 1000})
    applicant.on("pageerror", lambda e: errors.append(str(e)))
    applicant.route(
        "**/api/session/",
        lambda r: r.fulfill(
            json={
                "id": "applicant",
                "name": "Applicant Tester",
                "role": "applicant",
                "portal": "applicant",
                "ui_language": "en",
            }
        ),
    )
    applicant.route("**/api/cases/", lambda r: r.fulfill(json={"items": []}))
    applicant.route(
        "**/api/applications/",
        lambda r: r.fulfill(
            json={
                "items": [
                    {
                        "id": "draft",
                        "kind": "petition",
                        "status": "draft",
                        "version": 1,
                        "answers": {},
                        "fee": {"status": "due"},
                    }
                ]
            }
        ),
    )
    applicant.goto("http://127.0.0.1:18841/", wait_until="networkidle")
    applicant.get_by_role("heading", name="Petition", exact=True).wait_for()
    assert (
        applicant.get_by_role("button", name="Tribunal Sessions", exact=True).count()
        == 0
    )
    applicant.screenshot(path=".tmp/ctm-applicant-home.png", full_page=True)
    applicant.get_by_role("button", name="My application", exact=True).click()
    applicant.get_by_role("heading", name="My application", exact=True).wait_for()
    assert not errors, errors
    browser.close()
server.shutdown()
