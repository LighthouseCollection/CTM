"""Real Django API checks against an isolated copy of the backend stream.

Run: uv run --group browser python scripts/browser_applicant_api.py
Archives the reviewed backend ref into ignored .tmp, copies applicant assets and
applies the proposed shell patch only there. No branch merge/source backend edit.
Synthetic accounts/forms and test-client sessions only; no production providers.
"""
import io
import logging
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

SOURCE = Path(__file__).resolve().parents[1]
BACKEND_REF = os.environ.get("CTM_APPLICANT_BACKEND_REF", "origin/work/vm-frm-backend")

if len(sys.argv) == 1:
    backend_sha = subprocess.check_output(["git","rev-parse",BACKEND_REF],cwd=SOURCE,text=True).strip()
    target = SOURCE / ".tmp" / ("applicant-real-api-" + uuid.uuid4().hex)
    target.mkdir(parents=True)
    archive = subprocess.check_output(["git","archive",backend_sha],cwd=SOURCE)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(target,filter="data")
    for asset in (SOURCE/"static/ctm").glob("applicant*.js"):
        shutil.copyfile(asset,target/"static/ctm"/asset.name)
    subprocess.run(["git","init","--quiet",str(target)],check=True)
    subprocess.run(["git","apply",str(SOURCE/"docs/implementation/applicant/shell-integration.patch")],cwd=target,check=True)
    environment = {**os.environ,"CTM_TEST_BACKEND_SHA":backend_sha}
    result=subprocess.run([sys.executable,__file__,"--run",str(target)],cwd=target,env=environment)
    raise SystemExit(result.returncode)

ROOT=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"]="ctm.settings_test"
from django.conf import settings

settings.DATABASES["default"]["NAME"]=str(ROOT/"isolated.sqlite3")
settings.MEDIA_ROOT=ROOT/"test-media"
settings.DEBUG=True
settings.ALLOWED_HOSTS=["127.0.0.1","localhost","testserver"]
import django
django.setup()
logging.getLogger("django.request").setLevel(logging.CRITICAL)
from django.core.management import call_command
from django.test import Client
from tribunal.models import Account,QuestionnaireVersion

call_command("migrate",verbosity=0,interactive=False)
owner=Account.objects.create_user(email="applicant@example.test",email_verified=True,first_name="Synthetic",last_name="Applicant")
outsider=Account.objects.create_user(email="outsider@example.test",email_verified=True)
admin=Account.objects.create_user(email="admin@example.test",email_verified=True,role="admin")
fields=[{"code":code,"type":kind,"required":True,"label_en":en,"label_ar":ar}
        for code,kind,en,ar in [
            ("first_name","text","First name","الاسم الأول"),
            ("last_name","text","Last name","اسم العائلة"),
            ("birth_date","date","Birth date","تاريخ الميلاد"),
            ("gender","choice","Gender","الجنس"),
            ("marriage_date","date","Marriage date","تاريخ الزواج"),
            ("grounds","list","Grounds","الأسباب"),
            ("statement","textarea","Statement","البيان")]]
fields[3].update(choices=["M","F"],choice_labels={"M":{"label_en":"Male","label_ar":"ذكر"},"F":{"label_en":"Female","label_ar":"أنثى"}})
fields[5].update(choices=["abuse"],choice_labels={"abuse":{"label_en":"Abuse","label_ar":"الإساءة"}})
fields.append({"code":"children","type":"list","label_en":"Children","label_ar":"الأطفال","item_fields":[
    {"code":"gender","type":"choice","label_en":"Child gender","label_ar":"جنس الطفل","choices":["unknown"],
     "choice_labels":{"unknown":{"label_en":"Unknown","label_ar":"غير معروف"}}},
    {"code":"lives_with","type":"choice","label_en":"Child lives with","label_ar":"إقامة الطفل مع","choices":["unknown"],
     "choice_labels":{"unknown":{"label_en":"Unknown","label_ar":"غير معروف"}}}]})
fields.append({"code":"restraining_orders","type":"list","label_en":"Restraining orders","label_ar":"الأوامر التقييدية","item_fields":[
    {"code":"court","type":"text","label_en":"Order court","label_ar":"محكمة الأمر"},
    {"code":"number","type":"text","label_en":"Order case number","label_ar":"رقم قضية الأمر"},
    {"code":"status","type":"choice","label_en":"Order status","label_ar":"حالة الأمر","choices":["active"],
     "choice_labels":{"active":{"label_en":"Active","label_ar":"ساري"}}}]})
QuestionnaireVersion.objects.create(purpose="petition",number=1,published=True,
    definition={"fields":fields,"required_document_categories":["CMC"]},
    declaration_en="Synthetic test declaration only",declaration_ar="إقرار تجريبي للاختبار فقط")

def session_cookie(account):
    client=Client()
    client.force_login(account,backend="allauth.account.auth_backends.AuthenticationBackend")
    return client.cookies[settings.SESSION_COOKIE_NAME].value

cookies={name:session_cookie(account) for name,account in [("owner",owner),("outsider",outsider),("admin",admin)]}
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server,WSGIRequestHandler
class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass
server=make_server("127.0.0.1",0,StaticFilesHandler(get_wsgi_application()),handler_class=Quiet)
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=f"http://127.0.0.1:{server.server_port}"
from playwright.sync_api import sync_playwright,expect
checks=[]
def fixture_db(operation):
    # Playwright's sync driver owns an event loop; keep synthetic DB setup off it.
    def run():
        from django.db import connections
        try:return operation()
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run).result()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1280,"height":1000})
        context.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["owner"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        page=context.new_page(); errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(BASE,wait_until="networkidle")
        page.get_by_role("navigation").get_by_role("button",name="My application",exact=True).click()
        page.get_by_role("button",name="Start or resume application",exact=True).click()
        expect(page.get_by_label("First name",exact=False)).to_be_visible()
        applications=context.request.get(BASE+"/api/applications/").json()["items"]
        assert len(applications)==1
        app_id=applications[0]["id"]
        assert applications[0]["questionnaire"]["definition"]["fields"][0]["label_en"]=="First name"
        checks.append("Real start/list/detail bound questionnaire opens draft through patched shell")
        page.get_by_label("First name",exact=False).fill("Synthetic")
        page.get_by_label("Last name",exact=False).fill("Applicant")
        page.get_by_label("Birth date",exact=False).fill("1985-03-14")
        page.get_by_label("Gender",exact=False).select_option("F")
        page.get_by_label("Marriage date",exact=False).fill("2010-01-01")
        page.get_by_label("Abuse",exact=True).check()
        page.get_by_role("textbox",name="Statement",exact=False).fill("Synthetic applicant statement")
        page.get_by_role("region",name="Children",exact=True).get_by_role("button",name="Add another entry",exact=True).click()
        page.get_by_label("Child gender",exact=True).select_option("unknown")
        page.get_by_label("Child lives with",exact=True).select_option("unknown")
        page.get_by_role("button",name="Save draft",exact=True).click()
        expect(page.get_by_text("Your answers have been saved.",exact=True)).to_be_visible()
        data=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert data["version"]==1 and data["answers"]["grounds"]==["abuse"]
        assert data["answers"]["children"][0]["gender"]=="unknown"
        assert len(data["answers"]["children"][0]["id"])==36
        assert data["can_edit"] and not data["can_submit"] and not data["can_checkout"]
        checks.append("Real optimistic save persists answers/repeated child records; missing files keep server filing false")
        expect(page.get_by_text("Application documents",exact=True)).to_be_visible()
        listing=context.request.get(f"{BASE}/api/applications/{app_id}/files/")
        assert listing.status==200,listing.text()
        assert listing.json()["can_upload"] and not listing.json()["items"]
        assert {r["category"] for r in listing.json()["requirements"] if r["required"]}=={"MC","CMC","CDD","PHOTO"}
        assert page.get_by_role("button",name="Submit application",exact=True).count()==0
        checks.append("Real current-document listing supplies required slots and missing originals cannot enable filing")
        page.get_by_role("button",name="العربية",exact=True).click()
        expect(page.get_by_label("الاسم الأول",exact=False)).to_have_value("Synthetic")
        assert page.locator("html").get_attribute("dir")=="rtl"
        assert context.request.get(BASE+"/api/session/").json()["ui_language"]=="ar"
        page.get_by_role("button",name="English",exact=True).click()
        checks.append("Real CSRF-protected language preference persists and editor retains answers in RTL")
        csrf=next(cookie["value"] for cookie in context.cookies() if cookie["name"]=="csrftoken")
        concurrent={**data["answers"],"last_name":"Concurrent saved correction"}
        response=context.request.post(f"{BASE}/api/applications/{app_id}/",data={"answers":concurrent,"expected_version":1},
            headers={"X-CSRFToken":csrf})
        assert response.status==201,response.text()
        page.get_by_label("First name",exact=False).fill("Unsaved local answer")
        page.get_by_role("button",name="Save draft",exact=True).click()
        expect(page.get_by_text("Your changes were not saved.",exact=False)).to_be_visible()
        expect(page.get_by_label("First name",exact=False)).to_have_value("Unsaved local answer")
        page.get_by_role("button",name="Reload saved answers",exact=True).click()
        page.get_by_role("button",name="Discard unsaved changes",exact=True).click()
        expect(page.get_by_label("Last name",exact=False)).to_have_value("Concurrent saved correction")
        history=context.request.get(f"{BASE}/api/applications/{app_id}/history/").json()["items"]
        assert len(history)==2 and history[0]["answers"]["last_name"]=="Applicant"
        checks.append("Real concurrent save rejects stale editor write and explicit reload preserves immutable prior answer history")
        for name in ("outsider","admin"):
            other=browser.new_context()
            other.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies[name],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
            for suffix in ("","history/","files/","payments/"):
                assert other.request.get(f"{BASE}/api/applications/{app_id}/{suffix}").status==403
            other.close()
        checks.append("Real API denies outsider and council draft/detail/history access")
        uploaded=[]
        requirements=context.request.get(f"{BASE}/api/applications/{app_id}/files/").json()["requirements"]
        for category in ("MC","CMC","CDD","PHOTO"):
            # The isolated settings_test scanner bypass is explicit test policy;
            # this verifies API/storage gates, not a live antivirus engine.
            content=(b"\x89PNG\r\n\x1a\nsynthetic-image-only" if category=="PHOTO" else b"%PDF-1.7 synthetic-document-only")
            requirement=next(r for r in requirements if r["category"]==category)
            slot=page.get_by_role("region",name=requirement["label_en"],exact=True)
            slot.locator('input[type="file"]').set_input_files({
                "name":"synthetic.png" if category=="PHOTO" else "synthetic.pdf",
                "mimeType":"image/png" if category=="PHOTO" else "application/pdf","buffer":content})
            with page.expect_response(lambda response:response.url==BASE+"/api/files/" and response.request.method=="POST") as received:
                slot.get_by_role("button",name="Upload original",exact=True).click()
            response=received.value
            assert response.status==201,response.text()
            uploaded.append((response.json()["id"],content))
            expect(slot.get_by_role("link",name="Download original",exact=True)).to_be_visible()
        ready=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert ready["can_checkout"] and not ready["can_submit"]
        page.get_by_role("button",name="Refresh documents",exact=True).click()
        expect(page.get_by_text("Safety checks passed",exact=False)).to_have_count(4)
        expect(page.get_by_role("button",name="Continue to secure payment",exact=True)).to_be_visible()
        expect(page.get_by_role("link",name="Download original",exact=True)).to_have_count(4)
        checks.append("Real document refresh renders four clean current originals and updates checkout capability")
        file_id,content=uploaded[0]
        own_file=context.request.get(f"{BASE}/api/files/{file_id}/")
        assert own_file.status==200 and own_file.body()==content
        stranger=browser.new_context()
        stranger.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["outsider"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        assert stranger.request.get(f"{BASE}/api/files/{file_id}/",headers={"Range":"bytes=0-3"}).status==403
        stranger.close()
        checks.append("Real multipart required-file upload and owner download work; outsider range request denied")
        from tribunal.models import FileVersion,FileTechnicalEvent
        from tribunal.services.files import private_path
        original=fixture_db(lambda:FileVersion.objects.get(pk=file_id))
        original_bytes=private_path(original.object_key).read_bytes()
        requirement=next(r for r in requirements if r["category"]=="MC")
        slot=page.get_by_role("region",name=requirement["label_en"],exact=True)
        replacement=b"%PDF-1.7 corrected-synthetic-original"
        slot.locator('input[type="file"]').set_input_files({"name":"correction.pdf","mimeType":"application/pdf","buffer":replacement})
        with page.expect_response(lambda response:response.url==BASE+"/api/files/" and response.request.method=="POST") as received:
            slot.get_by_role("button",name="Upload corrected original",exact=True).click()
        assert received.value.status==201,received.value.text()
        replacement_id=received.value.json()["id"]
        expect(slot.get_by_role("link",name="Download original",exact=True)).to_have_attribute("href",f"/api/files/{replacement_id}/")
        latest=fixture_db(lambda:FileVersion.objects.get(pk=replacement_id))
        assert latest.attachment_id==original.attachment_id and latest.number==original.number+1
        assert private_path(original.object_key).read_bytes()==original_bytes
        assert private_path(latest.object_key).read_bytes()==replacement
        assert context.request.get(f"{BASE}/api/files/{file_id}/").status==403
        checks.append("Browser original correction retains original bytes/version and exposes only the current same-context original")
        # Synthetic technical events exercise projection/download gates, not a live scanner.
        fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=replacement_id,task="scan",result="pending"))
        page.get_by_role("button",name="Refresh documents",exact=True).click()
        expect(slot.get_by_text("Safety checks pending",exact=False)).to_be_visible()
        assert slot.get_by_role("link",name="Download original",exact=True).count()==0
        expect(page.get_by_role("button",name="Continue to secure payment",exact=True)).to_have_count(0)
        assert context.request.get(f"{BASE}/api/files/{replacement_id}/").status==403
        fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=replacement_id,task="scan",result="clean"))
        page.get_by_role("button",name="Refresh documents",exact=True).click()
        expect(slot.get_by_role("link",name="Download original",exact=True)).to_be_visible()
        expect(page.get_by_role("button",name="Continue to secure payment",exact=True)).to_be_visible()
        checks.append("Latest synthetic scan event governs actual current-file listing, browser readiness and byte access; pending blocks all three")
        orders=page.get_by_role("region",name="Restraining orders",exact=True)
        for index in range(2):
            orders.get_by_role("button",name="Add another entry",exact=True).click()
            orders.get_by_label("Order court",exact=True).nth(index).fill(f"Synthetic court {index+1}")
            orders.get_by_label("Order case number",exact=True).nth(index).fill(f"ORDER-{index+1}")
            orders.get_by_label("Order status",exact=True).nth(index).select_option("active")
        page.get_by_role("button",name="Save draft",exact=True).click()
        expect(page.get_by_text("Your answers have been saved.",exact=True)).to_be_visible()
        saved_orders=context.request.get(f"{BASE}/api/applications/{app_id}/").json()["answers"]["restraining_orders"]
        contexts=[order["id"] for order in saved_orders]
        assert len(set(contexts))==2 and all(len(identifier)==36 for identifier in contexts)
        order_requirements=context.request.get(f"{BASE}/api/applications/{app_id}/files/").json()["requirements"]
        order_requirements=[r for r in order_requirements if r["category"]=="RO"]
        assert [r["context"] for r in order_requirements]==contexts and all(r["required"] for r in order_requirements)
        ro_files=[]
        for index,requirement_row in enumerate(order_requirements):
            order_slot=page.get_by_role("region",name=requirement_row["label_en"],exact=True).nth(index)
            expect(order_slot.get_by_text(f"Order court: Synthetic court {index+1}",exact=True)).to_be_visible()
            expect(order_slot.get_by_text(f"Order case number: ORDER-{index+1}",exact=True)).to_be_visible()
            order_slot.locator('input[type="file"]').set_input_files({"name":f"order-{index+1}.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 synthetic-order-copy"})
            with page.expect_response(lambda response:response.url==BASE+"/api/files/" and response.request.method=="POST") as order_received:
                order_slot.get_by_role("button",name="Upload original",exact=True).click()
            assert order_received.value.status==201,order_received.value.text()
            ro_files.append(order_received.value.json()["id"])
            expect(order_slot.get_by_role("link",name="Download original",exact=True)).to_be_visible()
            assert context.request.get(f"{BASE}/api/applications/{app_id}/").json()["can_checkout"] is (index==1)
        listing=context.request.get(f"{BASE}/api/applications/{app_id}/files/").json()
        originals=[next(item for item in listing["items"] if item["id"]==file_id) for file_id in ro_files]
        assert [item["context"] for item in originals]==contexts
        cross=context.request.post(BASE+"/api/files/",headers={"X-CSRFToken":csrf},multipart={
            "application_id":app_id,"category":"RO","context":contexts[1],"visibility":"own","attachment_id":originals[0]["attachment_id"],
            "file":{"name":"wrong-context.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 cross-context-attempt"}})
        assert cross.status==403,cross.text()
        unchanged=context.request.get(f"{BASE}/api/applications/{app_id}/files/").json()["items"]
        assert all(any(item["id"]==original["id"] and item["context"]==original["context"] for item in unchanged) for original in originals)
        page.get_by_role("button",name="العربية",exact=True).click()
        arabic_slot=page.get_by_role("region",name=order_requirements[0]["label_ar"],exact=True).nth(0)
        expect(arabic_slot.get_by_text("محكمة الأمر: Synthetic court 1",exact=True)).to_be_visible()
        expect(arabic_slot.get_by_text("رقم قضية الأمر: ORDER-1",exact=True)).to_be_visible()
        page.set_viewport_size({"width":390,"height":1000})
        assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.set_viewport_size({"width":1280,"height":1000})
        page.get_by_role("button",name="English",exact=True).click()
        checks.append("Real repeated orders keep distinct saved IDs; each needs its own safe copy, and cross-context replacement403 preserves both originals")
        csrf=next(cookie["value"] for cookie in context.cookies() if cookie["name"]=="csrftoken")
        from tribunal.models import Application,CheckoutIntent
        fixture_db(lambda:Application.objects.filter(pk=app_id).update(duplicate_hold=True))
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        expect(page.get_by_text("Your application is awaiting identity review.",exact=False)).to_be_visible()
        page.get_by_label("First name",exact=False).fill("Held saved correction")
        page.get_by_role("button",name="Save draft",exact=True).click()
        expect(page.get_by_text("Your answers have been saved.",exact=True)).to_be_visible()
        held=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert held["can_edit"] and held["duplicate_hold"] and held["answers"]["first_name"]=="Held saved correction"
        assert not held["can_checkout"] and not held["can_submit"]
        for action,extra in (("checkout",{"attestation":{"accepted":True,"name":"Synthetic Applicant"}}),
                             ("submit",{"idempotency_key":"held-"+uuid.uuid4().hex,"attestation":{"accepted":True,"name":"Synthetic Applicant"}})):
            denied=context.request.post(f"{BASE}/api/applications/{app_id}/{action}/",data={"expected_version":held["version"],**extra},headers={"X-CSRFToken":csrf})
            assert denied.status==422,denied.text()
            assert ("not configured" if action=="checkout" else "duplicate") in denied.text().lower(),denied.text()
        def held_checkout_preparation():
            from django.core.exceptions import ValidationError
            from tribunal.services.payments import prepare_checkout
            try:
                prepare_checkout(owner,app_id,{"accepted":True,"name":"Synthetic Applicant"},expected_version=held["version"])
            except ValidationError as error:
                return "eligibility" in str(error).lower()
            return False
        assert fixture_db(held_checkout_preparation)
        assert fixture_db(lambda:CheckoutIntent.objects.filter(application_id=app_id).count())==0
        fixture_db(lambda:Application.objects.filter(pk=app_id).update(duplicate_hold=False))
        checks.append("Synthetic identity hold permits browser draft save but checkout preparation/submit reject; unconfigured provider endpoint cannot charge; no person matching simulated")
        staff=browser.new_context()
        staff.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["admin"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        staff.request.get(BASE+"/api/session/")
        staff_csrf=next(cookie["value"] for cookie in staff.cookies() if cookie["name"]=="csrftoken")
        waiver=staff.request.post(f"{BASE}/api/applications/{app_id}/waiver/",data={},headers={"X-CSRFToken":staff_csrf})
        assert waiver.status==201,waiver.text()
        ready=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert ready["fee"]["status"]=="waived" and ready["can_submit"] and not ready["can_checkout"]
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        history=page.get_by_role("region",name="Payment status and history",exact=True)
        expect(history.get_by_text("Application fee: $250.00 · Authorized fee waiver",exact=True)).to_be_visible()
        expect(history.get_by_text("No verified provider payment is recorded.",exact=False)).to_be_visible()
        financial=context.request.get(f"{BASE}/api/applications/{app_id}/payments/")
        assert financial.status==200 and financial.json()["verified_payment"] is False
        assert financial.json()["fee"]["status"]=="waived" and financial.json()["events"]==[]
        checks.append("Real owner payment history shows authorized waiver without fabricating provider success; outsider and staff draft reads denied")
        page.get_by_role("button",name="Review answers",exact=True).click()
        page.get_by_label("I have read and accept this declaration.",exact=True).check()
        page.get_by_label("Your full name",exact=False).fill("Synthetic Applicant")
        with page.expect_response(lambda response:response.url==f"{BASE}/api/applications/{app_id}/submit/" and response.request.method=="POST") as received:
            page.get_by_role("button",name="Submit application",exact=True).click()
        submitted=received.value
        payload=submitted.request.post_data_json
        assert payload["expected_version"]==ready["version"] and payload["attestation"]=={"accepted":True,"name":"Synthetic Applicant"}
        replay=context.request.post(f"{BASE}/api/applications/{app_id}/submit/",data=payload,headers={"X-CSRFToken":csrf})
        assert submitted.status==201,submitted.text()
        assert replay.status==201 and replay.json()["id"]==submitted.json()["id"]
        current=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert current["status"]=="submitted" and current["case_number"]
        checks.append("Browser review/declaration/signature and real authorized waiver finalize once; actual request key replay is idempotent")
        returned=staff.request.post(f"{BASE}/api/applications/{app_id}/review/",data={"result":"reject","instructions":"Synthetic correction instruction"},
            headers={"X-CSRFToken":staff_csrf})
        assert returned.status==201,returned.text()
        current=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert current["can_resubmit"] and not current["can_checkout"] and current["return_instructions"]=="Synthetic correction instruction"
        def returned_retention():
            from django.utils import timezone
            from tribunal.services.retention import process_drafts
            app=Application.objects.get(pk=app_id)
            before=(app.revisions.count(),FileVersion.objects.filter(attachment__application=app).count())
            Application.objects.filter(pk=app_id).update(last_activity=timezone.now()-timezone.timedelta(days=500))
            result=process_drafts()
            app.refresh_from_db()
            after=(app.revisions.count(),FileVersion.objects.filter(attachment__application=app).count())
            return result,app.status,before,after
        retention=fixture_db(returned_retention)
        assert retention[0]["expired"]==0 and retention[1]=="returned" and retention[2]==retention[3]
        delete_returned=context.request.post(f"{BASE}/api/applications/{app_id}/delete-draft/",data={},headers={"X-CSRFToken":csrf})
        assert delete_returned.status==422,delete_returned.text()
        assert private_path(original.object_key).read_bytes()==original_bytes
        checks.append("Actual retention ignores returned filing after500 idle days; draft-delete rejects it and retained answers/originals survive")
        from tribunal.models import Submission
        formal_submission_id=submitted.json()["id"]
        formal_submission=fixture_db(lambda:Submission.objects.get(pk=formal_submission_id))
        fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=replacement_id,task="scan",result="pending"))
        blocked=context.request.post(f"{BASE}/api/applications/{app_id}/submit/",data={
            "expected_version":current["version"],"idempotency_key":"blocked-scan-"+uuid.uuid4().hex},headers={"X-CSRFToken":csrf})
        assert blocked.status==422,blocked.text()
        assert fixture_db(lambda:Submission.objects.filter(application_id=app_id).count())==1
        still_returned=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert still_returned["status"]=="returned" and still_returned["fee"]["status"]=="waived" and not still_returned["can_resubmit"]
        fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=replacement_id,task="scan",result="clean"))
        checks.append("Returned resubmit rechecks latest safety event; pending required original rejects atomically without a new submission or fee change")
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        expect(page.get_by_text("Synthetic correction instruction",exact=True)).to_be_visible()
        if os.environ.get("CTM_APPLICANT_ACCEPTANCE")=="returned_privacy":
            # Separate acceptance probe: intentionally fails until direct-owner F08 is enforced.
            formal=staff.request.get(f"{BASE}/api/applications/{app_id}/").json()
            marker="Private pending returned correction"
            page.get_by_label("First name",exact=False).fill(marker)
            page.get_by_role("button",name="Save corrections",exact=True).click()
            expect(page.get_by_text("Your answers have been saved.",exact=True)).to_be_visible()
            slot=page.get_by_role("region",name=requirement["label_en"],exact=True)
            slot.locator('input[type="file"]').set_input_files({"name":"pending.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 private-pending-correction"})
            with page.expect_response(lambda response:response.url==BASE+"/api/files/" and response.request.method=="POST") as pending_received:
                slot.get_by_role("button",name="Upload corrected original",exact=True).click()
            assert pending_received.value.status==201,pending_received.value.text()
            pending_file=pending_received.value.json()["id"]
            expect(slot.get_by_role("link",name="Download original",exact=True)).to_have_attribute("href",f"/api/files/{pending_file}/")
            staff_detail=staff.request.get(f"{BASE}/api/applications/{app_id}/").json()
            staff_history=staff.request.get(f"{BASE}/api/applications/{app_id}/history/").json()
            case_files=staff.request.get(f"{BASE}/api/cases/{current['case_id']}/files/").json()
            privacy={
                "council_detail_keeps_formal_answers":staff_detail["answers"].get("first_name")==formal["answers"].get("first_name"),
                "council_version_keeps_formal_revision":staff_detail["version"]==formal["version"],
                "council_history_excludes_pending_answers":marker not in json.dumps(staff_history),
                "council_case_files_exclude_pending_original":pending_file not in json.dumps(case_files),
                "council_direct_download_denies_pending_original":staff.request.get(f"{BASE}/api/files/{pending_file}/").status in {403,404},
                "council_range_denies_pending_original":staff.request.get(f"{BASE}/api/files/{pending_file}/",headers={"Range":"bytes=0-3"}).status in {403,404},
                "council_preview_denies_pending_original":staff.request.get(f"{BASE}/api/files/{pending_file}/?view=1").status in {403,404},
                "council_manifest_keeps_submitted_original":replacement_id in json.dumps(staff_detail.get("manifest",[])) and pending_file not in json.dumps(staff_detail.get("manifest",[])),
            }
            report={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],"acceptance":"F08/F25 direct-owner returned privacy",
                    "checks":privacy,"remaining_surfaces":["search","notification routing/content","PostgreSQL RLS"],
                    "scope":"Isolated SQLite/browser API fixtures; no actual case data"}
            (ROOT/"returned-privacy-result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report,indent=2))
            assert all(privacy.values()),"Returned privacy acceptance failed; see returned-privacy-result.json"
        page.get_by_role("button",name="Review answers",exact=True).click()
        with page.expect_response(lambda response:response.url==f"{BASE}/api/applications/{app_id}/submit/" and response.request.method=="POST") as received:
            page.get_by_role("button",name="Resubmit corrections",exact=True).click()
        response=received.value
        assert response.status==201,response.text()
        assert "attestation" not in response.request.post_data_json
        correction_submission_id=response.json()["id"]
        correction_submission=fixture_db(lambda:Submission.objects.get(pk=correction_submission_id))
        assert correction_submission.pk!=formal_submission.pk
        assert correction_submission.attestation=={"original_submission":str(formal_submission.pk)}
        assert fixture_db(lambda:Submission.objects.get(pk=formal_submission_id).attestation)==formal_submission.attestation
        assert fixture_db(lambda:Submission.objects.filter(application_id=app_id).count())==2
        assert context.request.get(f"{BASE}/api/applications/{app_id}/").json()["fee"]["status"]=="waived"
        checks.append("Real return instructions and resubmission reuse original fee/signature without new attestation")
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        expect(page.get_by_text("Application status: Submitted",exact=True)).to_be_visible()
        expect(page.get_by_text("Case reference:",exact=False)).to_be_visible()
        checks.append("Explicit status refresh displays actual submitted state and allocated case reference")
        meeting=staff.request.post(BASE+"/api/sessions/",data={"date":"2030-01-02"},headers={"X-CSRFToken":staff_csrf})
        assert meeting.status==201,meeting.text()
        meeting_id=meeting.json()["id"]
        agenda=staff.request.post(f"{BASE}/api/sessions/{meeting_id}/agenda/",data={"case_id":current["case_id"],"part":2},headers={"X-CSRFToken":staff_csrf})
        assert agenda.status==201,agenda.text()
        parties=context.request.get(f"{BASE}/api/cases/{current['case_id']}/").json()["parties"]
        party_id=next(party["id"] for party in parties if party["is_self"])
        invitation=staff.request.post(f"{BASE}/api/agenda/{agenda.json()['id']}/testimony/",data={
            "party_id":party_id,"starts_at":"2030-01-02T10:00:00-08:00","ends_at":"2030-01-02T10:30:00-08:00",
            "instructions":"Private applicant appointment instructions"},headers={"X-CSRFToken":staff_csrf})
        assert invitation.status==201,invitation.text()
        invitation_id=invitation.json()["id"]
        own_invitations=context.request.get(BASE+"/api/appointments/")
        assert own_invitations.status==200 and len(own_invitations.json()["items"])==1
        private=own_invitations.json()["items"][0]
        assert private["version"]==1 and private["can_respond"] and private["case_id"]==current["case_id"]
        assert not any(key in private for key in ("agenda","session","testimony","party_name","party_id"))
        stranger=browser.new_context()
        stranger.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["outsider"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        assert stranger.request.get(BASE+"/api/appointments/").json()=={"items":[]}
        assert context.request.get(BASE+"/api/sessions/").status==403
        assert staff.request.get(BASE+"/api/appointments/").status==403
        page.get_by_role("navigation").get_by_role("button",name="My appointments",exact=True).click()
        expect(page.get_by_text("Private applicant appointment instructions",exact=True)).to_be_visible()
        with page.expect_response(lambda response:response.url==f"{BASE}/api/appointments/{invitation_id}/response/") as received:
            page.get_by_role("button",name="Confirm attendance",exact=True).click()
        assert received.value.status==201 and received.value.request.post_data_json["version"]==1
        page.get_by_role("button",name="Refresh invitations",exact=True).click()
        expect(page.get_by_text("Your current response: Confirmed",exact=True)).to_be_visible()
        checks.append("Real private invitation listing and browser confirmation work without council schedule access; outsiders see no invitations")
        moved=staff.request.post(f"{BASE}/api/sessions/{meeting_id}/reschedule/",data={"date":"2030-01-03","reason":"Synthetic scheduling correction",
            "appointments":{invitation_id:{"starts_at":"2030-01-03T11:00:00-08:00","ends_at":"2030-01-03T11:30:00-08:00","instructions":"Updated private invitation"}}},headers={"X-CSRFToken":staff_csrf})
        assert moved.status==201,moved.text()
        stale=context.request.post(f"{BASE}/api/appointments/{invitation_id}/response/",data={"version":1,"response":"confirm"},headers={"X-CSRFToken":csrf})
        assert stale.status==422,stale.text()
        page.get_by_role("button",name="Refresh invitations",exact=True).click()
        expect(page.get_by_text("Invitation version: 2",exact=True)).to_be_visible()
        expect(page.get_by_text("You have not responded to this invitation version.",exact=True)).to_be_visible()
        expect(page.get_by_text("Updated private invitation",exact=True)).to_be_visible()
        page.get_by_label("Reason for rejecting (optional)",exact=True).fill("Unavailable on the new date")
        with page.expect_response(lambda response:response.url==f"{BASE}/api/appointments/{invitation_id}/response/") as received:
            page.get_by_role("button",name="Reject invitation",exact=True).click()
        assert received.value.status==201 and received.value.request.post_data_json=={"version":2,"response":"reject","explanation":"Unavailable on the new date"}
        checks.append("Actual reschedule issues fresh version; stale response rejects and browser rejection binds updated invitation with optional reason")
        cancelled=staff.request.post(f"{BASE}/api/appointments/{invitation_id}/cancel/",data={"expected_version":2},headers={"X-CSRFToken":staff_csrf})
        assert cancelled.status==200,cancelled.text()
        page.get_by_role("button",name="Refresh invitations",exact=True).click()
        expect(page.get_by_text("This invitation is not accepting responses.",exact=True)).to_be_visible()
        assert page.get_by_role("button",name="Confirm attendance",exact=True).count()==0
        forbidden=context.request.post(f"{BASE}/api/appointments/{invitation_id}/response/",data={"version":3,"response":"confirm"},headers={"X-CSRFToken":csrf})
        assert forbidden.status==422,forbidden.text()
        stranger.request.get(BASE+"/api/session/")
        stranger_csrf=next(cookie["value"] for cookie in stranger.cookies() if cookie["name"]=="csrftoken")
        assert stranger.request.post(f"{BASE}/api/appointments/{invitation_id}/response/",data={"version":3,"response":"reject"},headers={"X-CSRFToken":stranger_csrf}).status==403
        stranger.close();staff.close()
        checks.append("Actual cancellation removes browser response actions; cancelled and outsider responses are denied by server")
        assert page.locator("[style]").count()==0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors,errors
        browser.close()
finally:
    server.shutdown()
result={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],"passed":len(checks),"checks":checks,
        "page_errors":errors,"scope":"Real Django APIs, isolated SQLite/synthetic sessions; authorized fixture waiver; scanner bypass test policy; no live provider payment/antivirus acceptance"}
(ROOT/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
