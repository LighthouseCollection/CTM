"""Grid Actions column and dialog Close label on the real Plenix CDN (#184).

Loads the pinned Plenix CDN and CTM's own static/ctm/shell-layout.js in a small page (no Django, no data) and checks,
in English and Arabic (RTL) at desktop width:
  - the Actions buttons are hidden at rest, shown when the row is hovered, and shown when the row's button has
    keyboard focus (Plenix reveals a kind "actions" cell on hover and on focus);
  - the 12rem Actions column keeps the Open button inside its cell (it was clipped at 9rem);
  - a Dialog given CTM's translated closeLabel exposes it on the close button (Plenix's own default is English).
Screenshots (rest, hover, focus, dialog) go to .tmp/grid-actions-<lang>-*.png.
Run: uv run --group browser python scripts/browser_grid_actions.py   (CTM_BROWSER_EXECUTABLE / CTM_CDN_LAN_IP as in browser_cdn_smoke.py)
"""
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"
TMP.mkdir(exist_ok=True)
CDN_HOST = "design-system.lighthouseway.org"
base = re.search(r'PLENIX_BASE = "([^"]+)"', (ROOT / "ctm/settings.py").read_text()).group(1)
SHELL = (ROOT / "static/ctm/shell-layout.js").as_uri()
PAGE = TMP / "grid-actions.html"
PAGE.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>grid actions</title>
<script src="{base}theme-boot.js"></script>
<link rel="stylesheet" href="{base}fonts.css"><link rel="stylesheet" href="{base}plenix.css">
<script defer src="{base}vendor/react.production.min.js"></script>
<script defer src="{base}vendor/react-dom.production.min.js"></script>
<script defer src="{base}plenix.js"></script>
<script defer src="{base}plenix-icons-plenix.js"></script>
<script defer src="{base}plenix-engines.js"></script>
<script defer src="{SHELL}"></script></head><body><div id="root"></div>
<script defer>
addEventListener("load", () => {{
  const q = new URLSearchParams(location.search), ar = q.get("lang") === "ar";
  document.documentElement.lang = ar ? "ar" : "en"; document.documentElement.dir = ar ? "rtl" : "ltr";
  const P = window.Plenix, h = React.createElement;
  const w = ar ? {{actions: "إجراءات", open: "فتح", move: "نقل", close: "إغلاق", cancel: "إلغاء", name: "الاسم"}}
               : {{actions: "Actions", open: "Open", move: "Move case", close: "Close", cancel: "Cancel", name: "Name"}};
  const rows = [1, 2, 3].map(i => ({{id: "r" + i, name: "Case " + i}}));
  const columns = [{{title: w.name, field: "name", width: "14rem"}},
    {{title: w.actions, field: "open_action", minWidth: "12rem", pill: false,
      render: () => h(P.Inline, {{gap: "xs"}}, h(P.Button, {{size: "xs", icon: "open", "data-act": "open"}}, w.open), h(P.Button, {{size: "xs"}}, w.move))}}];
  const App = () => {{
    const [d, setD] = React.useState(q.get("dlg") === "1");
    return h("div", {{style: {{padding: "16px"}}}}, h(window.CTMShell.Table, {{label: "Agenda", rows, columns}}),
      h(P.Dialog, {{open: d, title: "T", size: "sm", closeLabel: w.close, onClose: () => setD(false), footer: h(P.Button, null, w.cancel)}}, "x"));
  }};
  ReactDOM.createRoot(document.getElementById("root")).render(h(App));
}});
</script></body></html>""")

# Effective opacity of an element: the product over its ancestors (Plenix hides the actions cell with opacity 0).
OPACITY = """(el) => { let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; }"""
problems = []


def check(ok, message):
    if not ok:
        problems.append(message)


with sync_playwright() as p:
    executable = os.environ.get("CTM_BROWSER_EXECUTABLE", p.chromium.executable_path)
    args = [f"--host-resolver-rules=MAP {CDN_HOST} {os.environ['CTM_CDN_LAN_IP']}"] if os.environ.get("CTM_CDN_LAN_IP") else []
    browser = p.chromium.launch(executable_path=str(executable), headless=True, args=args)
    for lang in ("en", "ar"):
        page = browser.new_page(reduced_motion="reduce", viewport={"width": 1366, "height": 768})
        page.on("pageerror", lambda e, lang=lang: problems.append(f"{lang}: browser error: {e}"))
        page.goto(f"{PAGE.as_uri()}?lang={lang}")
        open_buttons = page.locator("[data-act=open]")
        open_buttons.first.wait_for(state="attached", timeout=20000)
        page.wait_for_timeout(800)
        first = open_buttons.first
        second = open_buttons.nth(1)
        opacity = lambda loc: loc.evaluate(OPACITY)
        page.screenshot(path=str(TMP / f"grid-actions-{lang}-rest.png"))
        check(opacity(first) == 0, f"{lang}: actions are visible at rest (expected hidden until hover or focus)")
        page.get_by_text("Case 2", exact=True).hover()
        page.wait_for_timeout(400)
        page.screenshot(path=str(TMP / f"grid-actions-{lang}-hover.png"))
        check(opacity(second) == 1, f"{lang}: hovering a row did not reveal its actions")
        page.mouse.move(5, 700)
        page.wait_for_timeout(300)
        page.evaluate("document.activeElement && document.activeElement.blur()")
        for _ in range(16):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement && document.activeElement.getAttribute('data-act')") == "open":
                break
        else:
            problems.append(f"{lang}: Tab never reached the Open button")
        page.wait_for_timeout(400)
        page.screenshot(path=str(TMP / f"grid-actions-{lang}-focus.png"))
        focused = page.locator("[data-act=open]:focus")
        check(focused.count() == 1 and opacity(focused) == 1, f"{lang}: keyboard focus on a row's Open button did not reveal its actions")
        # The Open button sits inside its Actions cell (clipped by ~11px at 9rem).
        header = page.get_by_role("columnheader", name=re.compile("Actions|إجراءات")).bounding_box()
        box = focused.bounding_box() if focused.count() else None
        if header and box:
            inside = box["x"] >= header["x"] - 0.5 and box["x"] + box["width"] <= header["x"] + header["width"] + 0.5
            check(inside, f"{lang}: Open button {box} is outside the Actions column {header}")
        else:
            problems.append(f"{lang}: could not measure the Actions column")
        page.goto(f"{PAGE.as_uri()}?lang={lang}&dlg=1")
        page.wait_for_timeout(1200)
        labels = page.evaluate("[...document.querySelectorAll('[role=dialog] button')].map(b => b.getAttribute('aria-label')).filter(Boolean)")
        expect = "إغلاق" if lang == "ar" else "Close"
        check(expect in labels, f"{lang}: dialog close button labels {labels}, expected {expect!r}")
        page.screenshot(path=str(TMP / f"grid-actions-{lang}-dialog.png"))
    browser.close()

if problems:
    print(f"Grid actions check FAILED ({len(problems)} problem(s)):")
    for item in problems:
        print(" -", item)
    sys.exit(1)
print("Grid actions check OK")
