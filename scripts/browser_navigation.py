"""Regression check for independent Plenix main/case navigation; synthetic API only."""
import os
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1253, "height": 1042})
        page.set_default_timeout(6000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        case = {"id": "11111111-1111-1111-1111-111111111111", "number": "NAV-TEST", "status": "open", "assigned_member": "Tester", "parties": [], "proceedings": [], "can_message": False}
        page.route("**/api/**", lambda route: route.fulfill(json={"items": []}))
        page.route("**/api/session/", lambda route: route.fulfill(json={"id": "navigation-test", "name": "Tester", "portal": "council", "role": "member", "ui_language": "en"}))
        page.route("**/api/cases/", lambda route: route.fulfill(json={"items": [case]}))
        page.route("**/api/cases/" + case["id"] + "/", lambda route: route.fulfill(json=case))
        page.goto(os.environ.get("CTM_REVIEW_URL", "http://localhost:18844/"))
        page.get_by_role("button", name="Cases", exact=True).first.click()
        page.get_by_text("NAV-TEST", exact=True).click()
        page.get_by_role("button", name="Open case", exact=True).click()
        page.get_by_role("button", name="Collapse Case Overview", exact=True).wait_for()
        main_rail = page.locator(".plx-nav-pane-rail")
        assert main_rail.get_by_role("button", name="Cases", exact=True).is_visible()
        assert main_rail.get_by_role("button", name="Search", exact=True).is_visible()
        assert page.get_by_role("button", name="Summary", exact=True).is_visible()
        main_rail.get_by_role("button", name="Expand sidebar", exact=True).click()
        assert page.get_by_role("button", name="Summary", exact=True).is_visible()
        page.get_by_role("button", name="Collapse sidebar", exact=True).click()
        page.get_by_role("button", name="Collapse Case Overview", exact=True).click()
        assert page.locator(".plx-secondary-pane-rail").is_visible()
        assert main_rail.is_visible()
        page.get_by_role("button", name="Expand Case Overview", exact=True).click()
        assert page.get_by_role("button", name="Summary", exact=True).is_visible()
        page.locator(".plx-secondary-pane").get_by_role("button", name="Reports", exact=True).click()
        assert page.get_by_role("button", name="Collapse Case Overview", exact=True).is_visible()
        assert main_rail.is_visible()
        assert not errors, errors
        browser.close()
        print("PASS: case starts expanded, main starts collapsed; independent controls and case-section navigation preserved.")


if __name__ == "__main__":
    main()

