"""Session shell responsive/RTL checks against synthetic APIs and real CDN."""
import json
import os
from playwright.sync_api import sync_playwright

base = os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18860/")
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for language in ["en", "ar"]:
        for width in [390, 768, 1253]:
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.set_default_timeout(6000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            def session(route):
                response = route.fetch()
                data = response.json()
                data["ui_language"] = language
                route.fulfill(response=response, json=data)
            page.route("**/api/session/", session)
            page.goto(base)
            page.get_by_role("heading", name="Home" if language == "en" else "الرئيسية", exact=True).wait_for()
            logo = page.locator(".plx-app-header__brand img")
            assert logo.evaluate("async e => { try { await e.decode(); return e.naturalWidth > 0; } catch { return false; } }"), "Logo must decode"
            current_label = "Current" if language == "en" else "الحالية"
            page.get_by_role("button", name=current_label, exact=True).click()
            current_header = page.locator(".plx-record-page__header--lg.plx-record-page__header--card")
            current_header.wait_for()
            current_header.get_by_text("CS20261022", exact=True).first.wait_for()
            for value in (["Synthetic President", "St. George Coptic Orthodox Church, Bellflower, California"]):
                current_header.get_by_text(value, exact=False).wait_for()
            actions = (
                ["Add a Case to Be Assigned", "Add a Case to Hearings", "Council Attendance"]
                if language == "en"
                else ["إضافة قضية للتعيين", "إضافة قضية لجلسات النظر", "حضور أعضاء المجلس"]
            )
            for action in actions:
                current_header.get_by_role("button", name=action, exact=True).wait_for()
            table_titles = (
                ["Cases to assign", "Scheduled Cases for Hearing"]
                if language == "en"
                else ["قضايا للتعيين", "القضايا المجدولة للنظر"]
            )
            for table_title in table_titles:
                page.get_by_role("heading", name=table_title, exact=True).wait_for()
            assert page.locator('input[type="date"]').count() == 0, "Current session must not show list filters"
            assignment_row = page.get_by_role("grid", name=table_titles[0]).get_by_role("row").nth(1)
            assignment_row.click()
            assert "plx-data-grid__grid-selected" in (assignment_row.get_attribute("class") or ""), "Selected case must stay highlighted"
            page.get_by_role("button", name="Home" if language == "en" else "الرئيسية", exact=True).click()
            session_name = "Council Session 2026-11-05" if language == "en" else "جلسة المجلس 2026-11-05"
            page.get_by_role("button", name=session_name, exact=True).click()
            full_header = page.locator(".plx-record-page__header--lg.plx-record-page__header--card")
            full_header.wait_for()
            assert full_header.locator(".plx-record-page__actions .plx-metric-group").count() == 1, "Full session header must keep its summary at the action edge"
            if language == "en" and width == 1253:
                page.screenshot(path=".tmp/session-full-record-header.png", full_page=True)
            page.get_by_role("button", name="Back to sessions" if language == "en" else "العودة إلى الجلسات", exact=True).click()
            page.get_by_role("button", name="Tribunal Sessions - Upcoming" if language == "en" else "جلسات المجلس - القادمة", exact=True).first.click()
            page.get_by_role("heading", name="New council session" if language == "en" else "جلسة مجلس جديدة", exact=True).wait_for()
            page.get_by_role("grid").first.get_by_role("row").nth(1).click()
            header = page.locator(".plx-record-page__header--lg.plx-record-page__header--card")
            header.wait_for()
            assert page.locator(".plx-record-page__title").bounding_box()["width"] > 150, "Session title must not collapse beside actions"
            description = (
                "Manage attendance, case assignments, and hearings for this session."
                if language == "en"
                else "إدارة الحضور وتعيين القضايا وجلسات النظر لهذه الجلسة."
            )
            header.get_by_text(description, exact=True).wait_for()
            metric_labels = ["Cases to assign", "Scheduled hearings"] if language == "en" else ["قضايا للتعيين", "جلسات النظر المجدولة"]
            for metric_label in metric_labels:
                header.get_by_text(metric_label, exact=True).wait_for()
            cases_metric = header.locator(".plx-metric").filter(has_text=metric_labels[0])
            assert cases_metric.locator(".plx-metric__value").inner_text() == "0", "Cases to assign must count pending Part 1 agenda rows"
            header.get_by_role("button", name="Reschedule session" if language == "en" else "إعادة جدولة الجلسة", exact=True).wait_for()
            title = "Council attendance" if language == "en" else "حضور أعضاء المجلس"
            page.get_by_role("heading", name=title, exact=True).wait_for()
            panel = page.locator(".plx-panel").filter(has=page.get_by_role("heading", name=title, exact=True))
            collapse = f"Collapse {title}" if language == "en" else f"طي {title}"
            expand = f"Expand {title}" if language == "en" else f"توسيع {title}"
            panel.get_by_role("button", name=collapse, exact=True).click()
            panel.get_by_role("button", name=expand, exact=True).click()
            page.get_by_role("button", name="Tribunal Sessions - Archived" if language == "en" else "جلسات المجلس - المؤرشفة", exact=True).first.click()
            page.get_by_role("grid").first.get_by_role("row").nth(1).get_by_text("2026-10-08", exact=True).wait_for()
            assert page.get_by_role("heading", name="New council session" if language == "en" else "جلسة مجلس جديدة", exact=True).count() == 0, "Archived sessions must not expose session creation"
            assert page.locator("html").get_attribute("dir") == ("rtl" if language == "ar" else "ltr")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "page overflow"
            reader = page.locator(".plx-reading-pane").bounding_box()
            assert reader["width"] > 0 and reader["x"] >= 0 and reader["x"] + reader["width"] <= width + 1
            assert not errors, errors
            if language == "en" and width == 1253:
                page.screenshot(path=".tmp/session-record-header.png", full_page=True)
            checks.append({"language": language, "width": width})
            page.close()
    browser.close()
print(json.dumps({"passed": checks}))
