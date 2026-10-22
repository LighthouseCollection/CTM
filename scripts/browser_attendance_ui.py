"""Synthetic fixture UI regression; does not establish backend authorization."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100})
    page.set_default_timeout(6000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18859/"))
    page.locator(".plx-nav-list").get_by_role("button", name="Tribunal Sessions", exact=True).click()
    page.get_by_role("grid").get_by_role("row").nth(1).click()
    panel = page.locator(".plx-panel").filter(has=page.get_by_role("heading", name="Council attendance", exact=True))
    panel.get_by_role("radio", name="Present", exact=True).first.wait_for()
    assert panel.get_by_role("radio", name="Not recorded", exact=True).count() == 0
    before = [radio.is_checked() for radio in panel.get_by_role("radio").all()]
    panel.get_by_role("button", name="Collapse Council attendance", exact=True).click()
    assert panel.get_by_role("radio").count() == 0 or not panel.get_by_role("radio").first.is_visible()
    panel.get_by_role("button", name="Expand Council attendance", exact=True).click()
    assert [radio.is_checked() for radio in panel.get_by_role("radio").all()] == before
    reader = page.locator(".plx-reading-pane")
    assert reader.get_by_role("grid").count() == 2, "agenda needs two tables"
    for label in ["Part 1 — New case assignments", "Part 2 — Case hearings"]:
        grid = reader.get_by_role("grid", name=label, exact=True)
        grid.wait_for()
        assert grid.locator("xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' plx-panel ')]").count() == 0
    candidate = page.get_by_label("Add accepted case for assignment", exact=True)
    candidate.select_option(candidate.locator("option").nth(1).get_attribute("value"))
    reader.get_by_role("button", name="Add case", exact=True).first.click()
    reader.get_by_role("button", name="Open case", exact=True).first.wait_for()
    reader.get_by_role("button", name="Record assignment", exact=True).first.click()
    page.get_by_role("dialog").wait_for()
    page.get_by_role("dialog").get_by_role("button", name="Cancel", exact=True).last.click()
    for action in ["Reschedule session", "Close session"]:
        reader.get_by_role("button", name=action, exact=True).click()
        dialog = page.locator('[role="dialog"], [role="alertdialog"]')
        dialog.wait_for()
        dialog.get_by_role("button", name="Cancel", exact=True).last.click()
        assert not dialog.is_visible()
    assert not errors, errors
    print("PASS: attendance options/collapse; two unwrapped agenda tables; add-case and assignment dialog; no browser errors")
    browser.close()
