"""Settings > Historical case entry layout check and pictures (#329), synthetic API responses only.

Serves CTM locally (synthetic settings, no database), answers every /api/ call with fictional data, signs in as
a synthetic administrator, opens Settings > Data & Records in English and Arabic at desktop width, checks that
each section is a Plenix Panel (a named region) with its buttons inside it, fills fictional values, and saves
pictures next to Settings > Configuration for comparison.

Run: uv run --group browser python scripts/browser_historical_layout.py
Output: .tmp/historical-<tag>-<lang>.png (tag from CTM_SHOT_TAG, default "after"; "before" skips the layout asserts)
"""

import json, os, sys, threading
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

root = Path(__file__).resolve().parents[1]
os.chdir(root)
(root / ".tmp").mkdir(exist_ok=True)
sys.path.insert(0, str(root))
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
import django

django.setup()
from django.conf import settings

settings.DEBUG = True
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


PORT = 18843
ENTRY = "00000000-0000-4000-8000-0000000000e1"
server = make_server("127.0.0.1", PORT, StaticFilesHandler(get_wsgi_application()), handler_class=Quiet)
threading.Thread(target=server.serve_forever, daemon=True).start()
tag = os.environ.get("CTM_SHOT_TAG", "after")
layout = tag != "before"
settings_rows = [
    {"key": "diocese_settings", "version": 1, "value": {"diocese_name": "Fictional Diocese", "system_email": "office@ctm.example.test", "case_id_prefix": "CTM", "default_session_day": "Tuesday", "session_location": "Synthetic Hall", "presiding_bishop": "Bishop Example", "tribunal_secretary": "Secretary Example"}},
    {"key": "mobile_settings", "version": 1, "value": {"system_available_mobile": True}},
]


def answer(route, lang="en"):
    path = route.request.url.split("127.0.0.1:%d" % PORT, 1)[-1].split("?")[0]
    if path == "/api/session/":
        body = {"id": "00000000-0000-4000-8000-000000000001", "name": "Admin Example", "email": "admin@ctm.example.test", "role": "admin", "portal": "council", "ui_language": lang, "notification_language": "en"}
    elif path == f"/api/historical/{ENTRY}/":
        body = {"id": ENTRY, "version": 2, "finalized_case_id": None, "payload": {"number": "HIST-2018-0007", "status": "closed", "closed_at": "2018-06-12T10:00:00-07:00",
            "parties": [{"slot": "A", "name": "Youssef Fictional", "legacy_reference": "P-0007-A", "account_id": "00000000-0000-4000-8000-0000000000a1"}, {"slot": "B", "name": "Sara Example"}]}}
    elif path == f"/api/historical/{ENTRY}/publish/":
        body = {"id": "00000000-0000-4000-8000-0000000000c1", "number": "HIST-2018-0007"}
        return route.fulfill(status=201, content_type="application/json", body=json.dumps(body))
    elif path == "/api/system/settings/":
        body = {"items": settings_rows}
    else:
        body = {"items": []}
    route.fulfill(status=200, content_type="application/json", body=json.dumps(body))


from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for lang in ["en", "ar"]:
        ar = lang == "ar"
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        context.add_init_script(f"localStorage.setItem('ctm-language', '{lang}')")
        context.route("**/api/**", lambda route, *_, lang=lang: answer(route, lang))
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"http://127.0.0.1:{PORT}/settings/configuration", wait_until="domcontentloaded")
        page.get_by_role("button", name="البيانات والسجلات" if ar else "Data & Records", exact=True).wait_for()
        page.wait_for_timeout(1500)
        page.screenshot(path=f".tmp/historical-compare-configuration-{lang}.png", full_page=True)
        page.get_by_role("button", name="البيانات والسجلات" if ar else "Data & Records", exact=True).click()
        form = page.get_by_role("form", name="إدخال قضية تاريخية" if ar else "Historical case entry", exact=True)
        form.wait_for()
        form.get_by_label("رقم القضية الأصلي" if ar else "Original case reference").fill("HIST-2019-0042")
        names = form.get_by_label("الاسم إن كان معروفًا" if ar else "Name, if known")
        names.nth(0).fill("Mina Fictional")
        names.nth(1).fill("Mariam Example")
        if layout:
            for title in (["استئناف إدخال محفوظ", "تفاصيل القضية", "الطرف أ", "الطرف ب"] if ar else ["Resume saved entry", "Case details", "Party A", "Party B"]):
                assert page.get_by_role("region", name=title, exact=True).count() == 1, (lang, title, "not a Panel region")
            resume = page.get_by_role("region", name="استئناف إدخال محفوظ" if ar else "Resume saved entry", exact=True)
            assert resume.get_by_role("button", name="فتح الإدخال" if ar else "Open entry", exact=True).count() == 1
            last = page.get_by_role("region", name="الطرف ب" if ar else "Party B", exact=True)
            assert last.get_by_role("button", name="حفظ الإدخال" if ar else "Save entry", exact=True).count() == 1
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (lang, "overflow")
        assert page.evaluate("document.documentElement.dir") == ("rtl" if ar else "ltr"), (lang, "direction")
        page.wait_for_timeout(500)
        page.screenshot(path=f".tmp/historical-{tag}-{lang}.png", full_page=True)
        if layout:
            # A resumed entry, then published: the read-only cards, with Open case at the bottom of the last card.
            resume = page.get_by_role("form", name="استئناف إدخال محفوظ" if ar else "Resume saved entry", exact=True)
            resume.get_by_label("رقم الإدخال" if ar else "Entry reference").first.fill(ENTRY)
            resume.get_by_role("button", name="فتح الإدخال" if ar else "Open entry", exact=True).click()
            leave = page.get_by_role("button", name="تجاهل ومغادرة" if ar else "Discard and leave", exact=True)
            leave.click()
            party_a = page.get_by_role("region", name="الطرف أ" if ar else "Party A", exact=True)
            party_a.get_by_text("رقم الحساب المرتبط الموجود" if ar else "Existing linked account reference", exact=True).wait_for()
            page.screenshot(path=f".tmp/historical-{tag}-resumed-{lang}.png", full_page=True)
            page.get_by_role("button", name="نشر القضية التاريخية" if ar else "Publish historical case", exact=True).click()
            page.locator("[role=dialog], [role=alertdialog]").get_by_role("button", name="نشر القضية التاريخية" if ar else "Publish historical case", exact=True).click()
            page.get_by_text("تم نشر القضية التاريخية." if ar else "Historical case published.", exact=True).wait_for()
            last = page.get_by_role("region", name="الطرف ب" if ar else "Party B", exact=True)
            assert last.get_by_role("button", name="فتح القضية" if ar else "Open case", exact=True).count() == 1, (lang, "Open case not in the last card")
            page.wait_for_timeout(300)
            page.screenshot(path=f".tmp/historical-{tag}-published-{lang}.png", full_page=True)
        context.close()
    browser.close()
server.shutdown()
assert not errors, errors
print("ok", tag)
