"""CDN header regression using synthetic authenticated API responses only."""
import base64
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1253, "height": 1042})
    page.set_default_timeout(6000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/api/**", lambda route: route.fulfill(json={"items": []}))
    identity = {"id": "header-test", "name": "Header Tester", "email": "header@example.test", "portal": "council", "role": "member", "ui_language": "en", "avatar_url": "/__profile_photo.png"}
    page.route("**/api/session/", lambda route: route.fulfill(json=identity))
    page.route("**/__profile_photo.png", lambda route: route.fulfill(content_type="image/png", body=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")))
    page.goto(os.environ.get("CTM_REVIEW_URL", "http://localhost:18844/"))
    account = page.get_by_role("button", name="Account and settings for Header Tester", exact=True)
    account.wait_for()
    account.locator("img").evaluate("(e)=>e.decode()")
    assert "plx-app-header__item--account" in account.get_attribute("class")
    notifications = page.get_by_role("button", name="Notifications", exact=True)
    assert "plx-app-header__item" in notifications.get_attribute("class")
    assert notifications.locator(".plx-icon--hdr-bell").count() == 1
    account.click()
    page.get_by_role("menu").wait_for()
    assert "header@example.test" in page.get_by_role("menu").inner_text()
    assert "raphael@lighthouseway.org" not in page.get_by_role("menu").inner_text()
    page.get_by_role("menuitem", name="My account", exact=True).click()
    page.get_by_role("heading", name="Profile", exact=True).wait_for()
    identity.pop("avatar_url")
    identity.pop("email")
    page.reload()
    account = page.get_by_role("button", name="Account and settings for Header Tester", exact=True)
    account.wait_for()
    assert account.locator("img").count() == 0
    account.click()
    page.get_by_role("menu").wait_for()
    assert "raphael@lighthouseway.org" not in page.get_by_role("menu").inner_text()
    assert not errors, errors
    browser.close()
    print("PASS: native header utilities/account menu; API photo/email, initials fallback, and no CDN sample email.")
