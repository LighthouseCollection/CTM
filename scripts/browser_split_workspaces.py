import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Run against: node scripts/council_fixture.cjs 18859 secretary --contract=pr7 --decree-read
# Uses only fixture data; verifies layout and interactions, not production/backend authorization.
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100})
    page.set_default_timeout(6000)
    errors, checks = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    def check(name):
        split = page.locator(".plx-split-view").first
        split.wait_for()
        first = split.locator(".plx-split-view__first")
        grid = first.get_by_role("grid")
        grid.wait_for()
        assert split.bounding_box()["height"] > 500, name
        assert split.locator(".plx-reading-pane").is_visible(), name
        checks.append(name)
        return grid
    def main_nav(name):
        page.locator(".plx-nav-list").get_by_role("button", name=name, exact=True).click()
    def case_nav(name):
        page.locator(".plx-secondary-pane").get_by_role("button", name=name, exact=True).click()
    page.goto(os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18859/"))
    for name in ["Tribunal Sessions", "Cases", "Search", "Archived"]:
        main_nav(name)
        grid = check(name)
        if name == "Tribunal Sessions":
            grid.get_by_role("row").nth(1).click()
            page.locator(".plx-reading-pane").get_by_role("heading").first.wait_for()
    main_nav("Cases")
    page.get_by_text("20261001-01", exact=True).first.click()
    page.get_by_role("button", name="Open case", exact=True).click()
    page.locator(".plx-secondary-pane").wait_for()
    for name in ["Communications", "Reports", "Hearings", "Evidence", "Documents", "Professional Assessments", "Decision & Voting", "Appeals", "Decree", "Case Audit"]:
        case_nav(name)
        grid = check(name)
        if name in ["Reports", "Evidence", "Documents", "Case Audit"]:
            assert grid.get_by_role("row").count() > 1, name
            grid.get_by_role("row").nth(1).click()
            assert page.locator(".plx-reading-pane").inner_text().strip(), name
        if name == "Reports":
            page.locator(".plx-reading-pane").get_by_text("Synthetic answer.", exact=True).wait_for()
    Path(".tmp").mkdir(exist_ok=True)
    page.screenshot(path=".tmp/restored-split-audit.png")
    assert len(checks) == 14
    assert not errors, errors
    print(json.dumps({"passed": checks, "browser_errors": errors}))
    browser.close()


