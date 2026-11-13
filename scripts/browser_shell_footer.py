"""CTM#324: every council and applicant page ends with the Plenix footer (StatusBar in the AppShell footer slot).
Real CDN, synthetic API fixtures (fictional data only). Checks EN and AR at desktop size that the footer is there
and that neither the page's last content nor the side nav's last item reaches the window's bottom edge.
Run: uv run --group browser python scripts/browser_shell_footer.py
Set CTM_FOOTER_BEFORE=1 to take the "before" pictures only (no footer assertions).
"""

import os, sys, threading
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


PORT = 18849
server = make_server(
    "127.0.0.1", PORT, StaticFilesHandler(get_wsgi_application()), handler_class=Quiet
)
threading.Thread(target=server.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright

BEFORE = os.environ.get("CTM_FOOTER_BEFORE") == "1"
TAG = "before" if BEFORE else "after"
CASE = {
    "assigned_member_id": "synthetic",
    "id": "11111111-1111-1111-1111-111111111111",
    "number": "20261021-01",
    "status": "open",
    "assigned_member": "Council Tester",
}


def run(browser, portal, lang):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/api/**", lambda r: r.fulfill(json={"items": [], "next_offset": None}))
    page.route("**/api/cases/", lambda r: r.fulfill(json={"items": [CASE]}))
    page.route(
        "**/api/session/",
        lambda r: r.fulfill(
            json={
                "id": "synthetic",
                "name": "Council Tester" if portal == "council" else "Applicant Tester",
                "role": "member" if portal == "council" else "applicant",
                "portal": portal,
                "ui_language": lang,
                "csrf_token": "synthetic",
            }
        ),
    )
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    page.locator("main h1, main h2").first.wait_for()
    page.wait_for_timeout(1500)
    shot = f".tmp/ctm-footer-{portal}-{lang}-{TAG}.png"
    page.screenshot(path=shot)
    print("Screenshot:", shot)
    assert not errors, errors
    page.evaluate("""() => { for (const e of document.querySelectorAll('main, main *')) { const o = getComputedStyle(e).overflowY; if ((o === 'auto' || o === 'scroll') && e.scrollHeight > e.clientHeight) e.scrollTop = e.scrollHeight; } window.scrollTo(0, document.body.scrollHeight); }""")
    page.wait_for_timeout(300)
    page.screenshot(path=f".tmp/ctm-footer-{portal}-{lang}-{TAG}-bottom.png")
    if BEFORE:
        page.close()
        return
    footer = page.locator(".plx-app-shell > .plx-status-bar")
    footer.wait_for()
    label = {"council": {"en": "Council portal", "ar": "بوابة المجلس"},
             "applicant": {"en": "Applicant portal", "ar": "بوابة مقدم الطلب"}}[portal][lang]
    assert footer.inner_text().strip() == label, footer.inner_text()
    assert page.locator("html").get_attribute("dir") == ("rtl" if lang == "ar" else "ltr")
    top = footer.bounding_box()["y"]
    assert top + footer.bounding_box()["height"] <= 768 + 0.5, "footer stays in the window"
    body = page.locator(".plx-app-shell__body").bounding_box()
    assert body["y"] + body["height"] <= top + 0.5, "the panes end above the footer"
    nav_items = page.locator(".plx-app-shell__side--start button, .plx-app-shell__side--start a")
    if nav_items.count():
        last = nav_items.last.bounding_box()
        assert last["y"] + last["height"] < top, "the side nav's last item ends above the footer"
    # The page's last part ends above the footer with PageContent's own bottom padding (no CTM spacing).
    content = page.locator(".plx-page-content > .plx-stack").bounding_box()
    padding = page.locator(".plx-page-content").evaluate("e => parseFloat(getComputedStyle(e).paddingBottom)")
    assert padding > 0 and content["y"] + content["height"] + padding <= top + 0.5, (content, padding, top)
    if portal == "council" and lang == "en":
        # Every page that renders a bounded part (split list/detail, Listing) keeps its bounded column above the
        # footer, derived from what the page renders (PageColumn), not from a page list (G5a on PR #327).
        for nav_name, shot_name in (("All Active Cases", "cases"), ("My Cases", "my-cases")):
            page.get_by_role("button", name=nav_name, exact=True).click()
            page.get_by_text("20261021-01").first.wait_for()
            column = page.locator(".plx-page-content > .plx-stack")
            page.wait_for_function(
                "() => document.querySelector('.plx-page-content > .plx-stack').classList.contains('plx-u-min-h-0')"
            )
            assert "plx-u-min-h-0" in column.get_attribute("class"), nav_name
            pc = page.locator(".plx-page-content")
            assert pc.evaluate("e => e.scrollHeight <= e.clientHeight + 1"), f"{nav_name}: the column does not overflow"
            box = pc.bounding_box()
            assert box["y"] + box["height"] <= top + 0.5, nav_name
            page.screenshot(path=f".tmp/ctm-footer-council-en-after-{shot_name}.png")
    if portal == "applicant" and lang == "en":
        # Fix round 2 on PR #327: applicant Documents/Evidence render a bare SplitView; the column must stay bounded
        # (PageColumn derives it) so the list and reading pane scroll alone above the footer.
        for section, heading in (("documents", "Documents"), ("evidence", "Evidence")):
            page.goto(f"http://127.0.0.1:{PORT}/cases/{CASE['id']}/{section}", wait_until="domcontentloaded")
            page.locator("main h1").filter(has_text=heading).first.wait_for()
            page.locator(".plx-split-view").first.wait_for()
            page.wait_for_function(
                "() => document.querySelector('.plx-page-content > .plx-stack').classList.contains('plx-u-min-h-0')"
            )
            pc = page.locator(".plx-page-content")
            assert pc.evaluate("e => e.scrollHeight <= e.clientHeight + 1"), f"{section}: the column does not overflow"
            box = pc.bounding_box()
            assert box["y"] + box["height"] <= top + 0.5, section
            split = page.locator(".plx-split-view").first.bounding_box()
            assert split["y"] + split["height"] <= top + 0.5, f"{section}: the split view ends above the footer"
            page.screenshot(path=f".tmp/ctm-footer-applicant-en-after-{section}.png")
    page.close()


with sync_playwright() as p:
    executable = os.environ.get("CTM_BROWSER_EXECUTABLE", p.chromium.executable_path)
    browser = p.chromium.launch(
        executable_path=str(executable),
        headless=True,
        args=(
            [f"--host-resolver-rules=MAP design-system.lighthouseway.org {os.environ['CTM_CDN_LAN_IP']}"]
            if os.environ.get("CTM_CDN_LAN_IP")
            else []
        ),
    )
    for portal in ("council", "applicant"):
        for lang in ("en", "ar"):
            run(browser, portal, lang)
    browser.close()
print("CTM shell footer: OK" if not BEFORE else "CTM shell footer: before pictures taken")
server.shutdown()
