"""Key Dates check (#239): the case Summary shows Plenix's compact grouped Timeline, in English and Arabic.

Runs against the synthetic council fixture (fictional data only) and the real pinned Plenix CDN:
  node scripts/council_fixture.cjs 18871 secretary --contract=pr7 --decree-read
  uv run --group browser python scripts/browser_key_dates.py
CTM_REVIEW_URL overrides the address. Desktop width only. Pictures go to .tmp/key-dates/.
CTM adds no CSS here: the check fails if the Key Dates panel carries inline styles.
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18871").rstrip("/")
OUT = Path(__file__).resolve().parents[1] / ".tmp" / "key-dates"
OUT.mkdir(parents=True, exist_ok=True)
TITLE = {"en": "Key Dates", "ar": "التواريخ المهمة"}

failures = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=os.environ.get('CTM_BROWSER_CHANNEL'))
    for language in ["en", "ar"]:
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def session_in(language):
            def session(route):
                response = route.fetch()
                data = response.json()
                data["ui_language"] = language
                route.fulfill(response=response, json=data)
            return session

        page.route("**/api/session/", session_in(language))
        page.goto(BASE + "/cases/c-4")
        panel = page.locator("section, [class*=panel]").filter(has_text=TITLE[language]).filter(has=page.locator(".plx-timeline")).last
        panel.wait_for(state="visible")
        page.wait_for_load_state("networkidle")
        if page.evaluate("document.dir") != ("rtl" if language == "ar" else "ltr"):
            failures.append(f"{language}: wrong page direction")
        if not panel.locator(".plx-timeline--compact").count():
            failures.append(f"{language}: Key Dates is not the compact Plenix timeline")
        if not panel.locator(".plx-timeline__year--compact").count():
            failures.append(f"{language}: no year heading in Key Dates")
        if panel.locator("[style]").count():
            failures.append(f"{language}: Key Dates carries inline styles (CTM must add no CSS)")
        panel.screenshot(path=str(OUT / f"key-dates-{language}.png"))
        if errors:
            failures.append(f"{language}: browser errors {errors}")
        page.close()
    browser.close()

if failures:
    print("FAILED:\n" + "\n".join(failures))
    sys.exit(1)
print("Key Dates: compact grouped timeline in EN and AR; pictures in", OUT)
