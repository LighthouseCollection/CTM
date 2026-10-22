"""Search UI states and keyboard selection; intercepted synthetic search API."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for language in ["en", "ar"]:
        for width in [390, 1253]:
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.set_default_timeout(6000)
            def session(route):
                response = route.fetch()
                route.fulfill(response=response, json={**response.json(), "ui_language": language})
            page.route("**/api/session/", session)
            held = []
            page.route("**/api/search/", lambda route: held.append(route))
            page.goto(os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18860/"))
            page.get_by_role("button", name="Search" if language == "en" else "البحث", exact=True).first.click()
            grid = page.get_by_role("grid")
            none = "No permitted documents match this search." if language == "en" else "لا توجد مستندات مسموح بها تطابق هذا البحث."
            loading = "Loading…" if language == "en" else "جارٍ التحميل…"
            failed = "Unable to load this information." if language == "en" else "تعذر تحميل هذه المعلومات."
            assert none not in grid.inner_text(), "No-results message shown before searching"
            form = page.get_by_role("form", name="Search" if language == "en" else "البحث", exact=True)
            form.get_by_role("searchbox").fill("first query")
            form.get_by_role("button", name="Search" if language == "en" else "بحث", exact=True).click()
            grid.get_by_text(loading, exact=True).wait_for()
            assert len(held) == 1
            held.pop().fulfill(json={"items": [{"file_id": "f-1", "case_id": "c-4", "name": "Keyboard result", "snippet": "First result details"}]})
            row = grid.get_by_role("row").filter(has_text="Keyboard result")
            row.wait_for()
            row.focus()
            row.press("Enter")
            page.locator(".plx-reading-pane").get_by_text("First result details", exact=True).wait_for()
            form.get_by_role("searchbox").fill("second query")
            form.get_by_role("button", name="Search" if language == "en" else "بحث", exact=True).click()
            grid.get_by_text(loading, exact=True).wait_for()
            assert grid.get_by_text("Keyboard result", exact=True).count() == 0
            held.pop().fulfill(json={"items": []})
            grid.get_by_text(none, exact=True).wait_for()
            form.get_by_role("searchbox").fill("third query")
            form.get_by_role("button", name="Search" if language == "en" else "بحث", exact=True).click()
            grid.get_by_text(loading, exact=True).wait_for()
            held.pop().fulfill(status=500, json={"error": "unavailable"})
            grid.get_by_text(failed, exact=True).wait_for()
            assert none not in grid.inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.close()
    browser.close()
print("PASS: initial/pending/results/empty/error search states and Enter selection, EN/AR at 390/1253")
