"""Synthetic case selector and structured audit filter regressions."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width":1253,"height":1100})
    page.set_default_timeout(6000)
    page.goto(os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18860/"))
    page.get_by_role("button", name="Tribunal Sessions", exact=True).first.click()
    page.get_by_label("Sessions", exact=True).select_option("past")
    page.get_by_role("grid").get_by_text("2026-10-08", exact=True).wait_for()
    assert page.get_by_role("grid").get_by_text("2026-11-05", exact=True).count() == 0
    posts = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" and request.url.endswith("/api/sessions/") else None)
    form = page.get_by_role("form", name="New council session", exact=True)
    form.get_by_label("Session date").fill("2026-11-05")
    form.get_by_role("button", name="Create session", exact=True).click()
    page.get_by_text("A council session already exists on that date.", exact=True).wait_for()
    assert not posts, "A hidden filtered session must still prevent duplicate creation"
    page.get_by_role("button", name="Cases", exact=True).first.click()
    page.get_by_text("20261001-01", exact=True).first.click()
    page.get_by_role("button", name="Open case", exact=True).wait_for()
    selected_row = page.get_by_role("grid").get_by_role("row").filter(has_text="20261001-01")
    assert "grid-selected" in selected_row.get_attribute("class"), "Viewed case must remain selected"
    page.get_by_role("searchbox").click()
    assert "grid-selected" in selected_row.get_attribute("class"), "Selection must survive focus leaving the table"
    page.get_by_role("searchbox").fill("no-matching-case")
    assert page.get_by_role("button", name="Open case", exact=True).count() == 0, "Filtered-out case preview remains actionable"
    page.get_by_role("searchbox").fill("")
    page.get_by_text("20261001-01", exact=True).first.click()
    page.get_by_role("button", name="Open case", exact=True).click()
    page.locator(".plx-secondary-pane").get_by_role("button", name="Case Audit", exact=True).click()
    grid = page.get_by_role("grid")
    page.get_by_label("Action", exact=True).select_option("case_assigned")
    assert grid.get_by_role("row").count() == 2
    page.get_by_role("button", name="Clear filters", exact=True).click()
    assert grid.get_by_role("row").count() > 1
    page.get_by_label("From date", exact=True).fill("2099-01-01")
    assert grid.get_by_role("row").count() == 1
    browser.close()
print("PASS: case preview follows filter visibility; case audit filters and reset")
