"""Plenix CDN smoke for the auto-upgrade: does CTM still load on the pinned Plenix?

Starts CTM locally (synthetic settings, no identity provider), opens the sign-in
page against the real CDN and fails on: any CDN file that does not load, any
browser error, Plenix not loading, the sign-in page not rendering, or Arabic not
switching to right-to-left. Saves screenshots to .tmp/ (EN and AR, desktop width only).

Run: uv run --group browser python scripts/browser_cdn_smoke.py
Optional CTM_CDN_LAN_IP bypasses public hairpin DNS with normal TLS validation.
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


PORT = 18842
CDN_HOST = "design-system.lighthouseway.org"
server = make_server("127.0.0.1", PORT, StaticFilesHandler(get_wsgi_application()), handler_class=Quiet)
threading.Thread(target=server.serve_forever, daemon=True).start()

from playwright.sync_api import sync_playwright

problems = []
shots = []


def watch(page):
    page.on("pageerror", lambda e: problems.append(f"browser error: {e}"))
    page.on("requestfailed", lambda r: CDN_HOST in r.url and problems.append(f"CDN request failed: {r.url} ({r.failure})"))
    page.on("response", lambda r: CDN_HOST in r.url and r.status >= 400 and problems.append(f"CDN HTTP {r.status}: {r.url}"))


def check_page(page, name, heading=None):
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="load")
    try:
        if heading:
            page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=20000)
        else:
            page.locator("h1, h2").first.wait_for(timeout=20000)
    except Exception:
        problems.append(f"{name}: sign-in page did not render" + (f" (no '{heading}' heading)" if heading else ""))
    if not page.evaluate("typeof window.Plenix !== 'undefined'"):
        problems.append(f"{name}: window.Plenix is not defined (design system did not load)")
    page.wait_for_timeout(1500)  # let entrance transitions settle before the screenshot
    path = f".tmp/plenix-{name}.png"
    page.screenshot(path=path, full_page=True)
    shots.append(path)


with sync_playwright() as p:
    executable = os.environ.get("CTM_BROWSER_EXECUTABLE", p.chromium.executable_path)
    args = [f"--host-resolver-rules=MAP {CDN_HOST} {os.environ['CTM_CDN_LAN_IP']}"] if os.environ.get("CTM_CDN_LAN_IP") else []
    browser = p.chromium.launch(executable_path=str(executable), headless=True, args=args)

    page = browser.new_page(reduced_motion="reduce", viewport={"width": 1440, "height": 1000})
    watch(page)
    check_page(page, "signin-en-desktop", heading="Sign in")

    # Desktop width only (owner, 2026-11-05). Since Plenix 0.89.0 a phone-sized window shows the CDN's
    # "Screen size not supported" notice on every page, sign-in included (#108, #124), so there is no phone sign-in to check.

    arabic = browser.new_page(reduced_motion="reduce", viewport={"width": 1440, "height": 1000})
    watch(arabic)
    arabic.add_init_script("try { localStorage.setItem('ctm-language', 'ar') } catch (e) {}")
    check_page(arabic, "signin-ar-desktop")
    direction = arabic.evaluate("document.documentElement.dir || document.body.dir || getComputedStyle(document.body).direction")
    if direction != "rtl":
        problems.append(f"signin-ar-desktop: page direction is '{direction}', expected 'rtl'")

    browser.close()

server.shutdown()
print("Screenshots:", ", ".join(shots))
if problems:
    print(f"CDN smoke FAILED ({len(problems)} problem(s)):")
    for item in dict.fromkeys(problems):
        print("  -", item)
    sys.exit(1)
print("CDN smoke OK")
