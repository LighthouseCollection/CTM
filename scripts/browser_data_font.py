"""Data font check (#325): case numbers, dates, times and counts in Plenix's data font (Reddit Mono); names not.

Runs against the synthetic council fixture (fictional data only) and the real pinned Plenix CDN:
  node scripts/council_fixture.cjs 18871 secretary --contract=pr7 --decree-read
  uv run --group browser python scripts/browser_data_font.py
CTM_REVIEW_URL overrides the address; CTM_DATA_FONT_LABEL names the pictures (default "after";
"before" only takes pictures). English and Arabic; screenshots go to .tmp/data-font/.
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get("CTM_REVIEW_URL", "http://127.0.0.1:18871").rstrip("/")
LABEL = os.environ.get("CTM_DATA_FONT_LABEL", "after")
OUT = Path(__file__).resolve().parents[1] / ".tmp" / "data-font"
OUT.mkdir(parents=True, exist_ok=True)
MONO = "Reddit Mono"

# The fonts of the innermost visible elements in main whose own text matches the pattern.
FONTS = """pattern => {
  const re = new RegExp(pattern);
  return [...document.querySelectorAll('main *')]
    .filter(el => el.childElementCount === 0 && el.getClientRects().length
      && re.test(el.textContent.replace(/[\\u2068\\u2069]/g, '').trim()))
    .map(el => ({ text: el.textContent.trim(), font: getComputedStyle(el).fontFamily }));
}"""

# page, path, [(what, pattern, must be data font)]
PAGES = [
    ("cases", "/cases/active", [("case number", r"^\d{8}-\d{2}$", True), ("member name", r"^Fr\. Synthetic Member$", False)]),
    ("sessions", "/sessions/archived", [("session date", r"^2026-10-08$", True), ("missing time word", r"^Time not recorded$", False)]),
    ("case", "/cases/c-4", [("case number", r"^20261001-01$", True)]),
]

failures = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
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
        for name, path, expectations in PAGES:
            page.goto(BASE + path)
            page.locator("main").first.wait_for(state="attached")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT / f"{LABEL}-{name}-{language}.png"), full_page=True)
            if LABEL != "after" or language != "en":
                continue  # patterns use English formats; Arabic is checked by its pictures
            for what, pattern, data in expectations:
                hits = page.evaluate(FONTS, pattern)
                if not hits:
                    failures.append(f"{name}: no {what} found")
                for hit in hits:
                    if (MONO in hit["font"]) != data:
                        failures.append(f"{name}: {what} {hit['text']!r} {'not ' if data else ''}in the data font ({hit['font']})")
        if errors:
            failures.append(f"{language}: page errors {errors}")
        page.close()
    browser.close()

if failures:
    print("Data font check failed:\n  - " + "\n  - ".join(failures))
    sys.exit(1)
print(f"Data font check: OK ({LABEL}); pictures in {OUT}")
