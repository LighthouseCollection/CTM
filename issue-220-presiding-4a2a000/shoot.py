"""Usage: shoot.py <build_dir> <tag> ; fictional data; real Plenix CDN; system Chrome."""
import os, sys, threading, json, base64
build, tag = sys.argv[1], sys.argv[2]
out = os.environ["OUT"]
os.chdir(build); sys.path.insert(0, build)
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
import django; django.setup()
from django.conf import settings
settings.DEBUG = True
settings.SOCIALACCOUNT_PROVIDERS = {"google": {"APPS": [{"client_id": "x", "secret": "x"}]}}
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server, WSGIRequestHandler
class Q(WSGIRequestHandler):
    def log_message(self, *a): pass
srv = make_server("127.0.0.1", 0, StaticFilesHandler(get_wsgi_application()), handler_class=Q)
PORT = srv.server_port
threading.Thread(target=srv.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright
svg = '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"><rect width="96" height="96" fill="#7a8fa6"/><circle cx="48" cy="38" r="18" fill="#e8d5c0"/><rect x="18" y="60" width="60" height="40" rx="22" fill="#e8d5c0"/></svg>'
PHOTO = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
SID = "22222222-2222-2222-2222-222222222222"
def session(photo, name):
    return {"id": SID, "date": "2026-11-05", "reference": "CS20261105", "starts_at": "2026-11-05T10:00:00-08:00",
            "presiding_member_id": "m1", "presiding_member_name": name, "location": "Fictional Hall, Sample City",
            "adjourned_at": None, "assigned_case_count": 0, "hearing_case_count": 0, "state": "planned",
            "can_manage": True, "can_close": True, "can_activate": False, "can_reschedule": True, "can_record_attendance": True,
            **({"presiding_member_photo_url": PHOTO} if photo else {"presiding_member_photo_url": None})}
NAMES = {"en": "Synthetic President", "ar": "الرئيس التجريبي"}
def run(browser, lang, photo):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errs = []; page.on("pageerror", lambda e: errs.append(str(e)))
    member = {"id": "m1", "name": NAMES[lang], "photo_url": None}
    def api(route):
        u = route.request.url
        if u.endswith("/api/session/"):
            return route.fulfill(json={"id": "u1", "name": "Council Tester", "role": "admin", "portal": "council", "ui_language": lang, "csrf_token": "x"})
        if "/agenda/" in u: return route.fulfill(json={"session": session(photo, NAMES[lang]), "items": []})
        if "/attendance/" in u: return route.fulfill(json={"items": [], "roster": []})
        if u.rstrip("/").endswith("/api/sessions"): return route.fulfill(json={"items": [session(photo, NAMES[lang])]})
        if "/api/council/members" in u: return route.fulfill(json={"items": [member], "assignment_authorities": []})
        return route.fulfill(json={"items": [], "next_offset": None})
    page.route("**/api/**", api)
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    cur = "Current" if lang == "en" else "الحالية"
    page.get_by_role("button", name=cur, exact=True).click(timeout=20000)
    hdr = page.locator("header.plx-entity-header").first
    try: hdr.wait_for(timeout=15000)
    except Exception:
        page.screenshot(path=f"{out}/debug-{lang}.png"); print(page.inner_text("body")[:600], errs); raise
    page.wait_for_timeout(1500)
    n = f"{out}/{tag}-{lang}-{'photo' if photo else 'nophoto'}"
    page.screenshot(path=n + "-full.png")
    hdr.screenshot(path=n + "-header.png")
    info = page.evaluate("""() => { const h=document.querySelector('header.plx-entity-header'); return {avatarImg: h.querySelectorAll('.plx-avatar img').length, avatars: h.querySelectorAll('.plx-avatar').length, svgIcons: h.querySelectorAll('.plx-entity-header__fact-icon, [class*=fact] [class*=icon]').length, text: h.innerText.slice(0,200)} }""")
    print(tag, lang, "photo" if photo else "nophoto", json.dumps(info, ensure_ascii=False), "errors:", errs, flush=True)
    page.close()
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    for lang in ("en", "ar"):
        for photo in (False, True):
            run(b, lang, photo)
