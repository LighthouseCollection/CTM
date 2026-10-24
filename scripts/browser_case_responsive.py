"""CDN case navigation: desktop panes and phone list/detail, synthetic APIs."""
import json
import os
from playwright.sync_api import sync_playwright

checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for language in ["en", "ar"]:
        for width in [390, 1253]:
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.set_default_timeout(6000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            def session(route):
                response = route.fetch()
                route.fulfill(response=response, json={**response.json(), "ui_language": language})
            page.route("**/api/session/", session)
            page.goto(os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18860/"))
            page.get_by_role("button", name="Cases" if language == "en" else "القضايا", exact=True).first.click()
            page.get_by_text("20261001-01", exact=True).first.click()
            page.get_by_role("button", name="Open case" if language == "en" else "فتح القضية", exact=True).click()
            page.locator(".plx-secondary-pane").wait_for(state="attached")
            content = page.locator(".plx-page-content")
            if width < 600:
                assert content.bounding_box()["width"] >= width - 1, "Case content squeezed by desktop navigation on phone"
                back = "Back to Case Overview" if language == "en" else "العودة إلى نظرة عامة على القضية"
                page.get_by_role("button", name=back, exact=True).click()
                pane = page.locator(".plx-secondary-pane")
                assert pane.bounding_box()["width"] >= width - 1
                pane.get_by_role("button", name="Summary" if language == "en" else "الملخص", exact=True).click()
                assert content.bounding_box()["width"] >= width - 1
            else:
                assert page.locator(".plx-secondary-pane").is_visible()
                assert page.locator(".plx-nav-pane-rail").is_visible()
                assert content.bounding_box()["width"] > 500
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
            checks.append({"language": language, "width": width})
            page.close()
    browser.close()
print(json.dumps({"passed": checks}))
