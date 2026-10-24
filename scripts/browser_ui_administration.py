"""Account/system UI acceptance with isolated synthetic API responses only."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

checks = []
Path(".tmp").mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for language in ["en", "ar"]:
        for role in ["admin", "secretary", "member", "president", "applicant"]:
            page = browser.new_page(viewport={"width": 390 if language == "ar" else 1253, "height": 1100})
            page.set_default_timeout(6000)
            errors, posts = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            identity = {"id": "ui-principal", "name": "API Principal", "email": "principal@example.test", "role": role, "portal": "applicant" if role == "applicant" else "council", "ui_language": language, "notification_language": "en"}
            members = [{"id":"ui-member", "name":"Directory person", "role":"member", "active":True, "can_authorize_assignment":False, "can_record_assignment":False}]
            page.route("**/api/session/", lambda route: route.fulfill(json=identity))
            page.route("**/api/council/members/", lambda route: route.fulfill(json={"items": members}))
            page.route("**/api/system/settings/", lambda route: route.fulfill(json={"items":[{"id":"setting-1","key":"tribunal_contact","version":3,"value":{"email":"office@example.test", "notes":"W" * 600}}]}))
            audit = [{"id":"audit-1","action":"setting_saved","source":"SettingRevision","timestamp":"2026-10-22T06:59:59Z"}, {"id":"audit-2","action":"council_enrolled","source":"Account","timestamp":"2026-10-22T07:00:00Z"}]
            page.route("**/api/system/audit/", lambda route: route.fulfill(json={"items":audit}))
            def enroll(route):
                posts.append(route.request.post_data_json)
                route.fulfill(status=201, json={"id":"new-member"})
            page.route("**/api/council/enroll/", enroll)
            page.goto(os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18860/"))
            page.locator(".plx-app-header__item--account").click()
            page.get_by_role("menuitem", name="My account", exact=True).click()
            page.locator(".plx-page-content").get_by_text("principal@example.test", exact=True).wait_for()
            assert page.locator(".plx-page-content").get_by_text("API Principal", exact=True).count() > 0
            page.get_by_role("button", name="Account Settings" if language == "en" else "إعدادات الحساب", exact=True).click()
            admin_link = page.get_by_role("button", name="CTM Administration" if language == "en" else "إدارة النظام", exact=True)
            if role in ["admin", "secretary"]:
                admin_link.click()
                page.get_by_role("grid").get_by_text("Directory person", exact=True).wait_for()
                page.locator(".plx-reading-pane").get_by_text("Select a record" if language == "en" else "اختر سجلًا", exact=True).wait_for()
                if role == "admin":
                    page.get_by_role("button", name="Expand Add council member" if language == "en" else "توسيع إضافة عضو إلى المجلس", exact=True).click()
                    form = page.get_by_role("form", name="Add council member" if language == "en" else "إضافة عضو إلى المجلس", exact=True)
                    form.get_by_role("button", name="Add member" if language == "en" else "إضافة العضو", exact=True).click()
                    assert not posts
                    for label, value in [("First name" if language == "en" else "الاسم الأول", "New"), ("Last name" if language == "en" else "اسم العائلة", "Member"), ("Email" if language == "en" else "البريد الإلكتروني", "new@example.test")]:
                        form.get_by_label(label).fill(value)
                    form.get_by_role("button", name="Add member" if language == "en" else "إضافة العضو", exact=True).click()
                    page.get_by_text("Council member added." if language == "en" else "تمت إضافة عضو المجلس.", exact=True).wait_for()
                    assert posts == [{"first_name":"New","last_name":"Member","email":"new@example.test","role":"member"}]
                else:
                    assert page.get_by_role("heading", name="Add council member" if language == "en" else "إضافة عضو إلى المجلس", exact=True).count() == 0
                page.get_by_role("button", name="Configuration" if language == "en" else "إعدادات النظام", exact=True).click()
                page.get_by_role("grid").get_by_role("row").nth(1).click()
                page.locator(".plx-reading-pane").get_by_text("office@example.test", exact=True).wait_for()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (role, language, "long configuration overflow")
                page.get_by_role("button", name="System audit" if language == "en" else "سجل النظام", exact=True).click()
                page.get_by_role("grid").get_by_text("setting_saved", exact=True).wait_for()
                page.get_by_label("To date" if language == "en" else "إلى تاريخ", exact=True).fill("2026-10-21")
                assert page.get_by_role("grid").get_by_text("council_enrolled", exact=True).count() == 0
                page.get_by_role("grid").get_by_text("setting_saved", exact=True).click()
                page.locator(".plx-reading-pane").get_by_text("SettingRevision", exact=True).wait_for()
                if role == "admin":
                    page.get_by_role("button", name="Historical case entry" if language == "en" else "إدخال قضية تاريخية", exact=True).click()
                    historical = page.get_by_role("form", name="Historical case entry" if language == "en" else "إدخال قضية تاريخية", exact=True)
                    reference = historical.get_by_label("Original case reference" if language == "en" else "رقم القضية الأصلي")
                    reference.fill("Legacy / UI-07")
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.get_by_role("button", name="Configuration" if language == "en" else "إعدادات النظام", exact=True).click()
                    page.get_by_role("button", name="Stay" if language == "en" else "البقاء", exact=True).click()
                    assert reference.input_value() == "Legacy / UI-07"
                    page.get_by_role("button", name="Configuration" if language == "en" else "إعدادات النظام", exact=True).click()
                    page.get_by_role("button", name="Discard and leave" if language == "en" else "تجاهل ومغادرة", exact=True).click()
                    page.get_by_role("grid").wait_for()
                page.screenshot(path=f".tmp/ui-administration-{role}-{language}.png")
            else:
                assert admin_link.count() == 0
                assert not posts
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (role, language, "overflow")
            assert not errors, errors
            checks.append({"role":role,"language":language})
            page.close()
    browser.close()
print(json.dumps({"passed":checks}))
