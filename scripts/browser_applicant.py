"""Applicant module + real pinned CDN, synthetic API contract fixtures only.

Run: uv run --group browser python scripts/browser_applicant.py
No provider login, real case records, production readiness or backend acceptance claimed.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://design-system.lighthouseway.org/cdn/0.58.0/"
OUT = ROOT / ".tmp" / "applicant-browser"
OUT.mkdir(parents=True, exist_ok=True)

HARNESS = """<!doctype html><html lang="en" data-plx-density-policy="compact"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script src="BASEtheme-boot.js"></script><link rel="stylesheet" href="BASEfonts.css">
<link rel="stylesheet" href="BASEplenix.css">
<script src="BASEvendor/react.production.min.js"></script>
<script src="BASEvendor/react-dom.production.min.js"></script><script src="BASEplenix.js"></script>
<script src="/applicant-files.js"></script><script src="/applicant-filing.js"></script><script src="/applicant.js"></script></head><body><div id="root"></div><script>
const R = React, P = Plenix, h = R.createElement;
const api = async (url, options) => {
  const response = await fetch(url, options);
  if (!response.ok) throw {status: response.status};
  return response.json();
};
function Harness() {
  const [lang, setLang] = R.useState('en');
  R.useEffect(() => { document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'; }, [lang]);
  return h(P.ThemeProvider, null, h(P.PageContent, null,
    h(P.Button, {onClick: () => setLang(lang === 'en' ? 'ar' : 'en')}, lang === 'en' ? 'العربية' : 'English'),
    h(CTMApplicant.ApplicationEditor, {applicationId: 'synthetic-draft', api, lang,
      onBack: () => { window.leftEditor = true; }})));
}
ReactDOM.createRoot(document.getElementById('root')).render(h(Harness));
</script></body></html>""".replace("BASE", BASE)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = (ROOT / ("static/ctm" + self.path)).read_bytes() if self.path in {"/applicant.js", "/applicant-filing.js", "/applicant-files.js"} else HARNESS.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript" if self.path.endswith(".js") else "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass


def fixture():
    return dict(id="synthetic-draft", status="draft", version=3, can_edit=True,
                answers={"first_name": "Original", "opaque_field": {"keep": True}},
                questionnaire=dict(id="synthetic-form", version=1, published=True, definition={"fields": [
                    dict(code="first_name", type="text", required=True, label_en="First name", label_ar="الاسم الأول"),
                    dict(code="statement", type="textarea", label_en="Statement", label_ar="البيان"),
                    dict(code="birth_date", type="date", label_en="Birth date", label_ar="تاريخ الميلاد"),
                    dict(code="gender", type="choice", label_en="Gender", label_ar="الجنس", choices=[
                        dict(value="M", label_en="Male", label_ar="ذكر"),
                        dict(value="F", label_en="Female", label_ar="أنثى")]),
                    dict(code="grounds", type="list", label_en="Grounds", label_ar="الأسباب", choices=[
                        dict(value="abuse", label_en="Abuse", label_ar="الإساءة")]),
                ]}))


server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
checks = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        app = fixture()
        writes = []
        fail_save = False
        fail_submit = False
        action_requests = []
        documents = {"can_upload":False,"items":[],"requirements":[]}

        def route_api(route):
            if route.request.url.endswith("/files/"):
                projection=documents
                if app["answers"].get("has_order") is True:
                    projection={**documents,"requirements":[*documents["requirements"],{
                        "category":"RO","context":"order-b","label_en":"Second order copy","label_ar":"نسخة الأمر الثاني","required":True}]}
                route.fulfill(json=projection)
            elif route.request.url.endswith("/submit/"):
                action_requests.append(route.request.post_data_json)
                if fail_submit:
                    route.abort("failed")
                else:
                    route.fulfill(status=201, json={"id": "synthetic-submission"})
            elif route.request.url.endswith("/checkout/"):
                route.fulfill(status=201, json={"intent":"synthetic", "checkout_url":"https://evil.example.test/"})
            elif route.request.method == "GET":
                route.fulfill(json=app)
            elif fail_save:
                route.fulfill(status=400, json={"error": "synthetic stale version"})
            else:
                payload = route.request.post_data_json
                writes.append(payload)
                app.update(answers=payload["answers"], version=app["version"] + 1)
                route.fulfill(status=201, json={"version": app["version"]})

        def uncertain_upload(route):
            # Simulate a received replacement whose response is lost. The server
            # listing, not a browser assumption, supplies the subsequent state.
            documents["items"][0]["scan_state"] = "pending"
            route.abort("failed")

        page.route("**/api/applications/synthetic-draft/**", route_api)
        page.route("**/api/files/", uncertain_upload)
        page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
        expect(page.get_by_label("First name", exact=False)).to_have_value("Original")
        page.get_by_label("First name", exact=False).fill("")
        page.get_by_label("Statement", exact=True).fill("Synthetic statement <script>alert(1)</script>")
        page.get_by_label("Gender", exact=True).select_option("F")
        page.get_by_label("Abuse", exact=True).check()
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Your answers have been saved.", exact=True)).to_be_visible()
        assert writes[-1]["expected_version"] == 3
        assert writes[-1]["answers"]["first_name"] == ""
        assert writes[-1]["answers"]["opaque_field"] == {"keep": True}
        assert writes[-1]["answers"]["grounds"] == ["abuse"]
        checks.append("Partial draft save preserves unknown data and stable option values")
        page.get_by_role("button", name="Review answers", exact=True).click()
        expect(page.get_by_text("Synthetic statement <script>alert(1)</script>", exact=True)).to_be_visible()
        expect(page.get_by_text("Female", exact=True)).to_be_visible()
        assert page.locator("section input").count() == 0
        checks.append("Review shows local answers as escaped text")
        page.get_by_role("button", name="Continue editing", exact=True).click()
        page.get_by_label("First name", exact=False).fill("Unsaved local")
        page.get_by_role("button", name="العربية", exact=True).click()
        expect(page.get_by_label("الاسم الأول", exact=False)).to_have_value("Unsaved local")
        assert page.locator("html").get_attribute("dir") == "rtl"
        checks.append("EN/AR switching preserves unsaved answers and uses RTL")
        page.get_by_role("button", name="English", exact=True).click()
        page.get_by_role("button", name="Back", exact=True).click()
        expect(page.get_by_text("Reloading or leaving will discard your unsaved changes.", exact=True)).to_be_visible()
        assert not page.evaluate("!!window.leftEditor")
        page.get_by_role("button", name="Keep editing", exact=True).click()
        fail_save = True
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Your changes were not saved.", exact=False)).to_be_visible()
        expect(page.get_by_label("First name", exact=False)).to_have_value("Unsaved local")
        page.get_by_role("button", name="Reload saved answers", exact=True).click()
        page.get_by_role("button", name="Keep editing", exact=True).click()
        expect(page.get_by_label("First name", exact=False)).to_have_value("Unsaved local")
        checks.append("Failed save and cancelled reload/navigation retain local changes")
        for width in (1280, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            for lang in ("en", "ar"):
                if page.locator("html").get_attribute("lang") != lang:
                    page.get_by_role("button", name="العربية" if lang == "ar" else "English", exact=True).click()
                assert page.locator("[style]").count() == 0, page.locator("[style]").evaluate_all("els => els.map(e => e.outerHTML.slice(0, 700))")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                # Playwright's default caret hiding leaves empty style attributes
                # on controls; preserve the caret so QA measures application DOM.
                page.screenshot(path=str(OUT / f"{lang}-{width}.png"), full_page=True, caret="initial")
        checks.append("1280/390px EN/AR: no runtime inline style or horizontal overflow")
        page.get_by_role("button", name="English", exact=True).click()
        page.get_by_role("button", name="Reload saved answers", exact=True).click()
        page.get_by_role("button", name="Discard unsaved changes", exact=True).click()
        expect(page.get_by_label("First name", exact=False)).to_have_value("")
        checks.append("Explicit discard reloads acknowledged saved answers")
        app["questionnaire"]["definition"]["fields"][0].pop("label_ar")
        page.reload(wait_until="networkidle")
        expect(page.get_by_text("The approved application form is not available.", exact=False)).to_be_visible()
        assert page.locator("section input").count() == 0
        checks.append("Missing Arabic question wording blocks editing")
        app = fixture()
        app.update(can_submit=True, fee={"amount_minor":25000,"currency":"USD","status":"waived"})
        app["questionnaire"].update(declaration_en="Approved synthetic declaration", declaration_ar="إقرار تجريبي معتمد")
        page.reload(wait_until="networkidle")
        expect(page.get_by_role("button", name="Submit application", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Review answers", exact=True).click()
        page.get_by_label("I have read and accept this declaration.", exact=True).check()
        page.get_by_label("Your full name", exact=False).fill("Synthetic Applicant")
        for width in (1280,390):
            page.set_viewport_size({"width":width,"height":1000})
            for lang in ("en","ar"):
                if page.locator("html").get_attribute("lang") != lang:
                    page.get_by_role("button", name="العربية" if lang=="ar" else "English", exact=True).click()
                expect(page.get_by_label("اسمك الكامل" if lang=="ar" else "Your full name",exact=False)).to_have_value("Synthetic Applicant")
                assert page.locator("[style]").count() == 0
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(OUT/f"filing-{lang}-{width}.png"),full_page=True,caret="initial")
        page.get_by_role("button", name="English", exact=True).click()
        checks.append("Declaration/signature/fee controls retain consent in EN/AR at desktop/mobile without styles/overflow")
        fail_submit = True
        page.get_by_role("button", name="Submit application", exact=True).click()
        expect(page.get_by_text("Submission was not confirmed.", exact=False)).to_be_visible()
        expect(page.get_by_label("Your full name", exact=False)).to_be_disabled()
        expect(page.get_by_role("button", name="Continue editing", exact=True)).to_be_disabled()
        expect(page.get_by_role("button", name="Refresh documents", exact=True)).to_be_disabled()
        fail_submit = False
        page.get_by_role("button", name="Submit application", exact=True).click()
        expect(page.get_by_text("The server acknowledged your submission.", exact=False)).to_be_visible()
        assert action_requests[-1] == action_requests[-2]
        checks.append("Waived filing requires review/signature; uncertain retry freezes payload and idempotency key")
        app = fixture()
        app.update(status="returned", can_edit=False, can_resubmit=True, return_instructions="Synthetic correction: clarify your statement.",
                   fee={"amount_minor":25000,"currency":"USD","status":"paid"})
        page.reload(wait_until="networkidle")
        expect(page.get_by_text(app["return_instructions"], exact=True)).to_be_visible()
        page.get_by_role("button", name="Review answers", exact=True).click()
        assert page.get_by_label("I have read and accept this declaration.", exact=True).count() == 0
        assert page.get_by_role("button", name="Continue to secure payment", exact=True).count() == 0
        page.get_by_role("button", name="Resubmit corrections", exact=True).click()
        expect(page.get_by_text("The server acknowledged your submission.", exact=False)).to_be_visible()
        assert "attestation" not in action_requests[-1]
        checks.append("Returned correction instructions and resubmission reuse fee/signature without checkout")
        app = fixture()
        app.update(can_checkout=True, fee={"amount_minor":25000,"currency":"USD","status":"due"})
        app["questionnaire"].update(declaration_en="Approved synthetic declaration", declaration_ar="إقرار تجريبي معتمد")
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Review answers", exact=True).click()
        page.get_by_label("I have read and accept this declaration.", exact=True).check()
        page.get_by_label("Your full name", exact=False).fill("Synthetic Applicant")
        page.get_by_role("button", name="Continue to secure payment", exact=True).click()
        expect(page.get_by_text("Payment could not be started.", exact=False)).to_be_visible()
        assert page.url.startswith("http://127.0.0.1:")
        assert page.get_by_text("The server acknowledged your submission.", exact=False).count() == 0
        checks.append("Untrusted checkout URL is rejected without navigation or invented payment success")
        app = fixture()
        app.update(can_submit=True, fee={"amount_minor":25000,"currency":"USD","status":"waived"})
        app["questionnaire"].update(declaration_en="Approved synthetic declaration", declaration_ar="إقرار تجريبي معتمد")
        documents = {"can_upload":True,"requirements":[{"category":"RO","context":"order-a",
                     "label_en":"Order copy","label_ar":"نسخة الأمر","required":True}],
                     "items":[{"id":"11111111-1111-4111-8111-111111111111","attachment_id":"attachment-a",
                     "category":"RO","context":"order-a","name":"Synthetic order.pdf","scan_state":"clean",
                     "download_url":"/api/files/11111111-1111-4111-8111-111111111111/"}]}
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Review answers", exact=True).click()
        page.get_by_label("I have read and accept this declaration.", exact=True).check()
        page.get_by_label("Your full name", exact=False).fill("Synthetic Applicant")
        expect(page.get_by_role("button", name="Submit application", exact=True)).to_be_enabled()
        page.locator('input[type="file"]').set_input_files({"name":"synthetic.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 replacement"})
        page.get_by_role("button", name="Upload corrected original", exact=True).click()
        expect(page.get_by_text("The upload was not confirmed.", exact=False)).to_be_visible()
        expect(page.get_by_role("button", name="Submit application", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Refresh documents", exact=True).click()
        expect(page.get_by_text("Synthetic order.pdf · Safety checks pending", exact=True)).to_be_visible()
        assert page.get_by_role("link", name="Download original", exact=True).count() == 0
        page.get_by_role("button", name="Review answers", exact=True).click()
        expect(page.get_by_role("button", name="Submit application", exact=True)).to_be_disabled()
        documents["items"][0]["scan_state"] = "clean"
        page.get_by_role("button", name="Refresh documents", exact=True).click()
        expect(page.get_by_text("Synthetic order.pdf · Safety checks passed", exact=True)).to_be_visible()
        page.get_by_role("button", name="Review answers", exact=True).click()
        page.get_by_label("I have read and accept this declaration.", exact=True).check()
        page.get_by_label("Your full name", exact=False).fill("Synthetic Applicant")
        expect(page.get_by_role("button", name="Submit application", exact=True)).to_be_enabled()
        checks.append("Uncertain replacement blocks filing until refreshed safe documents and explicit review/signature")
        app = fixture()
        app["questionnaire"]["definition"]["fields"].extend([
            {"code":"has_order","type":"boolean","required":True,"label_en":"Has order?","label_ar":"هل يوجد أمر؟"},
            {"code":"order_details","type":"text","label_en":"Order details","label_ar":"تفاصيل الأمر",
             "when":{"field":"has_order","equals":True}}])
        fail_save = False
        page.reload(wait_until="networkidle")
        expect(page.get_by_role("radio", name="No", exact=True)).not_to_be_checked()
        expect(page.get_by_role("radio", name="Yes", exact=True)).not_to_be_checked()
        assert page.get_by_label("Order details", exact=True).count() == 0
        page.get_by_role("radio", name="Yes", exact=True).check()
        page.get_by_label("Order details", exact=True).fill("Retained contextual detail")
        page.get_by_role("radio", name="No", exact=True).check()
        assert page.get_by_label("Order details", exact=True).count() == 0
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Your answers have been saved.", exact=True)).to_be_visible()
        assert writes[-1]["answers"]["has_order"] is False
        assert writes[-1]["answers"]["order_details"] == "Retained contextual detail"
        page.get_by_role("button", name="العربية", exact=True).click()
        expect(page.get_by_role("radio", name="لا", exact=True)).to_be_checked()
        checks.append("Boolean unanswered/false values and conditional hidden answers survive save and Arabic switch")
        page.get_by_role("button", name="English", exact=True).click()
        page.get_by_role("radio", name="Yes", exact=True).check()
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Your answers have been saved.", exact=True)).to_be_visible()
        expect(page.get_by_role("region", name="Second order copy", exact=True)).to_be_visible()
        checks.append("Acknowledged answer save automatically refreshes newly required document contexts")
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()

result = {"checks": checks, "passed": len(checks), "page_errors": errors,
          "scope": "Synthetic API contract fixtures with real Plenix CDN 0.58.0; not backend/provider E2E"}
(OUT / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
