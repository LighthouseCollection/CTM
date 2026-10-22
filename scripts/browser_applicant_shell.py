"""Exercise governance patch in an isolated temporary shell with synthetic APIs.

Shared source files are copied under .tmp before applying the proposed patch.
The application checkout's app.js and shell.html are never modified.
"""
import json
import shutil
import subprocess
import threading
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
COPY = ROOT / ".tmp" / "applicant-integration"
for name in ("static/ctm/app.js", "tribunal/templates/tribunal/shell.html"):
    target = COPY / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
subprocess.run(["git", "apply", "--directory=.tmp/applicant-integration",
                "docs/implementation/applicant/shell-integration.patch"], cwd=ROOT, check=True)
shell = (COPY / "tribunal/templates/tribunal/shell.html").read_text(encoding="utf-8")
shell = shell.replace("{% load static %}", "")
for name in ("app.js", "applicant.js", "applicant-filing.js", "applicant-files.js"):
    shell = shell.replace("{% static 'ctm/" + name + "' %}", "/" + name)
shell = shell.replace('{{ boot|json_script:"ctm-config" }}',
                      '<script id="ctm-config" type="application/json">{"providers":[]}</script>')


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/app.js":
            content = (COPY / "static/ctm/app.js").read_bytes()
        elif self.path in {"/applicant.js", "/applicant-filing.js", "/applicant-files.js"}:
            content = (ROOT / ("static/ctm" + self.path)).read_bytes()
        else:
            content = shell.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript" if self.path.endswith(".js") else "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass


app = dict(id="synthetic", kind="petition", status="draft", version=1, can_edit=True,
           fee={"amount_minor": 25000, "currency": "USD", "status": "due"},
           answers={"name": "Saved"}, questionnaire=dict(
               id="form", version=1, published=True, definition={"fields": [
                   dict(code="name", type="text", label_en="Synthetic name", label_ar="اسم تجريبي")]}))
user = dict(id="synthetic-user", name="Synthetic Applicant", portal="applicant", role="applicant",
            ui_language="en", notification_language="en")
server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
checks = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        save_status = 201
        preference_status = 200
        documents = {"can_upload":True,"items":[],"requirements":[{
            "category":"RO","context":"order-a","label_en":"Order copy","label_ar":"نسخة الأمر","required":True}]}
        uploads = []

        def api(route):
            path = route.request.url.split("/api/", 1)[1]
            if path == "session/":
                route.fulfill(json=user)
            elif path == "cases/":
                route.fulfill(json={"items": []})
            elif path == "applications/":
                route.fulfill(json={"items": [app]})
            elif path == "applications/synthetic/files/":
                route.fulfill(json=documents)
            elif path == "files/":
                content_type = route.request.headers["content-type"]
                assert content_type.startswith("multipart/form-data; boundary=")
                message = BytesParser(policy=default).parsebytes(
                    f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + route.request.post_data_buffer)
                parts = {part.get_param("name", header="content-disposition"):part for part in message.iter_parts()}
                values = {key:part.get_content() for key,part in parts.items() if key != "file"}
                uploads.append(values)
                assert values["application_id"] == "synthetic"
                assert values["context"] == "order-a" and values["category"] == "RO"
                assert parts["file"].get_filename() == "synthetic.pdf"
                documents["items"] = [{"id":"11111111-1111-4111-8111-111111111111", "attachment_id":"attachment-a",
                                       "category":"RO","context":"order-a","name":"Synthetic original.pdf","scan_state":"pending"}]
                route.fulfill(status=201, json={"id":"11111111-1111-4111-8111-111111111111","scan_state":"pending"})
            elif path == "account/settings/":
                if preference_status != 200:
                    route.fulfill(status=preference_status, json={"error": "synthetic preference failure"})
                else:
                    user.update(route.request.post_data_json)
                    route.fulfill(json=user)
            elif path == "applications/synthetic/":
                if route.request.method == "GET":
                    route.fulfill(json=app)
                elif save_status != 201:
                    route.fulfill(status=save_status, json={"error": "synthetic denial"})
                else:
                    app.update(answers=route.request.post_data_json["answers"], version=app["version"] + 1)
                    route.fulfill(status=201, json={"version": app["version"]})
            else:
                raise AssertionError(path)

        page.route("**/api/**", api)
        page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
        page.get_by_role("button", name="Open application", exact=True).click()
        expect(page.get_by_label("Synthetic name")).to_have_value("Saved")
        page.get_by_label("Synthetic name").fill("Keep me")
        page.get_by_role("button", name="العربية", exact=True).click()
        expect(page.get_by_label("اسم تجريبي")).to_have_value("Keep me")
        page.get_by_role("button", name="English", exact=True).click()
        checks.append("Patched shared shell opens editor; language preference preserves local input")
        preference_status = 500
        page.get_by_role("button", name="العربية", exact=True).click()
        expect(page.get_by_text("Your language preference could not be saved. Please try again.", exact=True)).to_be_visible()
        expect(page.get_by_label("Synthetic name")).to_have_value("Keep me")
        preference_status = 200
        checks.append("Failed language preference keeps dirty editor mounted and input intact")
        page.get_by_role("navigation").get_by_role("button", name="Home", exact=True).click()
        expect(page.get_by_text("Reloading or leaving will discard your unsaved changes.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Keep editing", exact=True).click()
        expect(page.get_by_label("Synthetic name")).to_have_value("Keep me")
        page.get_by_role("navigation").get_by_role("button", name="Home", exact=True).click()
        page.get_by_role("button", name="Discard unsaved changes", exact=True).click()
        expect(page.get_by_role("button", name="Open application", exact=True)).to_be_visible()
        checks.append("Sidebar navigation uses editor guard; cancel retains input and discard leaves")
        page.get_by_role("button", name="Open application", exact=True).click()
        page.get_by_label("Synthetic name").fill("Leave through Back")
        page.get_by_role("button", name="Back", exact=True).click()
        page.get_by_role("button", name="Discard unsaved changes", exact=True).click()
        expect(page.get_by_role("button", name="Open application", exact=True)).to_be_visible()
        checks.append("Back discard leaves once without recursively prompting")
        for status in (403, 404):
            page.get_by_role("button", name="Open application", exact=True).click()
            page.get_by_label("Synthetic name").fill("Unsent")
            save_status = status
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_text("This application is no longer available for editing.", exact=True)).to_be_visible()
            expect(page.get_by_text("Unsent", exact=True)).to_be_visible()
            assert page.get_by_role("button", name="Save draft", exact=True).count() == 0
            assert page.locator("[style]").count() == 0
            page.reload(wait_until="networkidle")
        checks.append("Actual patched shell api preserves 403/404 and editor locks further writes")
        page.get_by_role("button", name="Open application", exact=True).click()
        expect(page.locator('input[type="file"]')).to_be_attached()
        upload = page.get_by_role("button", name="Upload original", exact=True)
        page.locator('input[type="file"]').set_input_files({"name":"synthetic.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 synthetic-only"})
        upload.click()
        expect(page.get_by_text("Synthetic original.pdf · Safety checks pending", exact=True)).to_be_visible()
        assert page.get_by_role("link", name="Download original", exact=True).count() == 0
        page.locator('input[type="file"]').set_input_files({"name":"synthetic.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 corrected synthetic-only"})
        page.get_by_role("button", name="Upload corrected original", exact=True).click()
        expect(page.get_by_text("Synthetic original.pdf · Safety checks pending", exact=True)).to_be_visible()
        assert uploads[-1]["attachment_id"] == "attachment-a"
        assert "attachment_id" not in uploads[0]
        checks.append("Actual shell multipart transport preserves application/order/replacement; pending scan has no download")
        page.get_by_role("button", name="العربية", exact=True).click()
        expect(page.get_by_text("Synthetic original.pdf · فحوص السلامة قيد الانتظار", exact=True)).to_be_visible()
        for width in (1280,390):
            page.set_viewport_size({"width":width,"height":1000})
            assert page.locator("[style]").count() == 0
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        checks.append("Context upload controls render in Arabic RTL without runtime styles/overflow")
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
print(json.dumps({"passed": len(checks), "checks": checks, "page_errors": errors,
                  "scope": "Proposed shell patch in temporary copy; synthetic API responses"}, indent=2))
