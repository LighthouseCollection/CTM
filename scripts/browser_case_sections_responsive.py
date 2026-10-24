"""Read-only synthetic case-section layout/selection checks, English and Arabic."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

sections = [
    ("Communications", "المراسلات"), ("Reports", "التقارير"),
    ("Hearings", "مناقشات القضية"), ("Evidence", "الأدلة"),
    ("Documents", "المستندات"), ("Professional Assessments", "التقييمات المهنية"),
    ("Decision & Voting", "القرار والتصويت"), ("Appeals", "التماسات إعادة النظر"),
    ("Decree", "الشهادة"), ("Case Audit", "سجل القضية"),
]
checks = []
Path(".tmp").mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for language in ["en", "ar"]:
        for width in [390, 1253]:
            page = browser.new_page(viewport={"width": width, "height": 1100})
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
            for index, (english, arabic) in enumerate(sections):
                if width < 600:
                    page.get_by_role("button", name="Back to Case Overview" if language == "en" else "العودة إلى نظرة عامة على القضية", exact=True).click()
                pane = page.locator(".plx-secondary-pane")
                pane.get_by_role("button", name=english if language == "en" else arabic, exact=True).click()
                split = page.locator(".plx-split-view").first
                grid = split.locator(".plx-split-view__first").get_by_role("grid")
                grid.wait_for()
                reader = split.locator(".plx-reading-pane")
                reader.wait_for()
                if english in ["Reports", "Evidence", "Documents", "Case Audit"]:
                    grid.get_by_role("row").nth(1).click()
                    assert reader.inner_text().strip(), english
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (language, width, english, "page overflow")
                bounds = reader.bounding_box()
                assert bounds["width"] > 100 and bounds["x"] >= -1 and bounds["x"] + bounds["width"] <= width + 1, (language, width, english, bounds)
                assert not errors, errors
                checks.append({"language": language, "width": width, "section": english})
            page.screenshot(path=f".tmp/case-sections-{language}-{width}.png")
            page.close()
    browser.close()
print(json.dumps({"passed": checks}))
