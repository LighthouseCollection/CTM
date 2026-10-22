"""Shared Playwright helpers for QA-01 (real Plenix 0.58.0 CDN, real assembled app, test-issued sessions)."""

from playwright.sync_api import sync_playwright

from qa_env import BASE_URL, fixtures

F = fixtures()


def context_for(browser, who, lang=None, width=1280, height=900):
    ctx = browser.new_context(viewport={"width": width, "height": height}, locale="en-US",
                              timezone_id="America/Los_Angeles")
    ctx.add_cookies([{"name": "sessionid", "value": F["cookies"][who], "url": BASE_URL}])
    return ctx


NAV_TOGGLES = ["Council portal", "Case Overview"]


def nav(page, name):
    """Click a sidebar item; on narrow screens open the collapsed navigation first."""
    item = page.get_by_role("button", name=name, exact=True).first
    page.wait_for_timeout(300)
    if not item.is_visible():
        for toggle in NAV_TOGGLES:
            t = page.get_by_role("button", name=toggle, exact=True)
            if t.count() and t.first.is_visible():
                t.first.click()
                break
    item.click()


def open_case_reports(page, case_key):
    """Home -> Cases -> case row -> Reports, the same path a council user clicks."""
    page.goto(BASE_URL + "/", wait_until="domcontentloaded")
    page.get_by_role("button", name="Notifications", exact=True).or_(page.get_by_role("button", name="الإشعارات", exact=True)).first.wait_for()
    nav(page, "Cases")
    number = F["case_numbers"][case_key]
    page.get_by_text(number, exact=True).first.click()
    # 0b10a61+: the Cases list is a split view; the row opens a preview with "Open case".
    open_case = page.get_by_role("button", name="Open case", exact=True)
    page.wait_for_timeout(500)
    if open_case.count():
        open_case.first.click()
    page.get_by_role("heading", name=number).first.wait_for()
    nav(page, "Reports")


def run(fn, headless=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            return fn(browser)
        finally:
            browser.close()
