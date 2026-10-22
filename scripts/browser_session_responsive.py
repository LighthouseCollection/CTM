"""Session shell responsive/RTL checks against synthetic APIs and real CDN."""
import json
import os
from playwright.sync_api import sync_playwright

base = os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18860/")
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for language in ["en", "ar"]:
        for width in [390, 768, 1253]:
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.set_default_timeout(6000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            def session(route):
                response = route.fetch()
                data = response.json()
                data["ui_language"] = language
                route.fulfill(response=response, json=data)
            page.route("**/api/session/", session)
            page.goto(base)
            page.get_by_role("heading", name="Home" if language == "en" else "الرئيسية", exact=True).wait_for()
            logo = page.locator(".plx-app-header__brand img")
            assert logo.evaluate("async e => { try { await e.decode(); return e.naturalWidth > 0; } catch { return false; } }"), "Logo must decode"
            page.get_by_role("button", name="Tribunal Sessions" if language == "en" else "جلسات المجلس", exact=True).first.click()
            page.get_by_role("grid").first.get_by_role("row").nth(1).click()
            page.locator(".plx-record-page__header--lg").wait_for()
            assert page.locator(".plx-record-page__title").bounding_box()["width"] > 150, "Session title must not collapse beside actions"
            title = "Council attendance" if language == "en" else "حضور أعضاء المجلس"
            page.get_by_role("heading", name=title, exact=True).wait_for()
            panel = page.locator(".plx-panel").filter(has=page.get_by_role("heading", name=title, exact=True))
            collapse = f"Collapse {title}" if language == "en" else f"طي {title}"
            expand = f"Expand {title}" if language == "en" else f"توسيع {title}"
            panel.get_by_role("button", name=collapse, exact=True).click()
            panel.get_by_role("button", name=expand, exact=True).click()
            assert page.locator("html").get_attribute("dir") == ("rtl" if language == "ar" else "ltr")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "page overflow"
            reader = page.locator(".plx-reading-pane").bounding_box()
            assert reader["width"] > 0 and reader["x"] >= 0 and reader["x"] + reader["width"] <= width + 1
            assert not errors, errors
            if language == "en" and width == 1253:
                page.screenshot(path=".tmp/session-record-header.png", full_page=True)
            checks.append({"language": language, "width": width})
            page.close()
    browser.close()
print(json.dumps({"passed": checks}))
