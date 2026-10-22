"""Real Django API checks against an isolated copy of the backend stream.

Run: uv run --group browser python scripts/browser_applicant_api.py
Archives the reviewed backend ref into ignored .tmp, copies applicant assets and
applies the proposed shell patch only there. No branch merge/source backend edit.
Synthetic accounts/forms and test-client sessions only; no production providers.
"""
import io
import http.client
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
INTEGRATED = os.environ.get("CTM_APPLICANT_INTEGRATED", "false") == "true"
CHECK_RETURNED_PRIVACY = os.environ.get("CTM_APPLICANT_ACCEPTANCE", "returned_privacy") == "returned_privacy"
SHARED_LOOPBACK = len(sys.argv) >= 2 and sys.argv[1] == "--shared-loopback"

if len(sys.argv) == 1:
    backend_sha = subprocess.check_output(["git","rev-parse",BACKEND_REF],cwd=SOURCE,text=True).strip()
    target = SOURCE / ".tmp" / ("applicant-real-api-" + uuid.uuid4().hex)
    target.mkdir(parents=True)
    archive = subprocess.check_output(["git","archive",backend_sha],cwd=SOURCE)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(target,filter="data")
    if not INTEGRATED:
        for asset in (SOURCE/"static/ctm").glob("applicant*.js"):
            shutil.copyfile(asset,target/"static/ctm"/asset.name)
        subprocess.run(["git","init","--quiet",str(target)],check=True)
        subprocess.run(["git","apply",str(SOURCE/"docs/implementation/applicant/shell-integration.patch")],cwd=target,check=True)
    environment = {**os.environ,"CTM_TEST_BACKEND_SHA":backend_sha}
    result=subprocess.run([sys.executable,__file__,"--run",str(target)],cwd=target,env=environment)
    raise SystemExit(result.returncode)

if len(sys.argv) != 3 or sys.argv[1] not in {"--run", "--shared-loopback"}:
    raise RuntimeError("Use --run <isolated archive> or --shared-loopback <immutable release>.")

shared_config = None
image_evidence = {}
if SHARED_LOOPBACK:
    from applicant_shared_loopback import (
        build_config,
        inspect_image_evidence,
        redact_runtime_environment,
        safe_preflight_evidence,
    )
    shared_config = build_config(os.environ)
    if Path(sys.argv[2]).resolve() != shared_config.source_dir:
        raise RuntimeError("Shared-loopback argument must match the guarded immutable release.")
    image_evidence = inspect_image_evidence(shared_config)
    owner_database_url = shared_config.owner_url
    app_database_url = shared_config.app_url
    sanitized_environment = redact_runtime_environment(os.environ)
    os.environ.clear()
    os.environ.update(sanitized_environment)
    os.environ["CTM_TEST_BACKEND_SHA"] = shared_config.expected_sha
else:
    owner_database_url = os.environ.get("CTM_APPLICANT_POSTGRES_OWNER_URL")
    app_database_url = os.environ.get("CTM_APPLICANT_POSTGRES_APP_URL")

ROOT=Path(sys.argv[2]).resolve()
if Path.cwd().resolve()!=ROOT:
    raise RuntimeError("Run isolated acceptance from its archive directory to prevent mixed imports.")
sys.path.insert(0,str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"]="ctm.settings_test"
from django.conf import settings

POSTGRES_OWNER=owner_database_url
if POSTGRES_OWNER:
    import dj_database_url
    settings.DATABASES={"default":dj_database_url.parse(POSTGRES_OWNER)}
else:
    settings.DATABASES["default"]["NAME"]=str(ROOT/"isolated.sqlite3")
ARTIFACT_ROOT=shared_config.acceptance_root if shared_config else ROOT
OUTPUT_PATH=shared_config.output_path if shared_config else ROOT/"result.json"
settings.MEDIA_ROOT=shared_config.media_dir if shared_config else ROOT/"test-media"
settings.DEBUG=not SHARED_LOOPBACK
settings.ALLOWED_HOSTS=["127.0.0.1"] if SHARED_LOOPBACK else ["127.0.0.1","localhost","testserver"]
import django
django.setup()
import tribunal.models as isolated_models
if not Path(isolated_models.__file__).resolve().is_relative_to(ROOT):
    raise RuntimeError("Acceptance imported models outside the pinned archive.")
logging.getLogger("django.request").setLevel(logging.CRITICAL)
from django.core.management import call_command
from django.test import Client
from tribunal.models import Account,QuestionnaireVersion

call_command("migrate",verbosity=0,interactive=False)
fixture_tag=(shared_config.run_id if shared_config else uuid.uuid4().hex).lower()
owner=Account.objects.create_user(email=f"applicant-{fixture_tag}@example.invalid",email_verified=True,first_name="Synthetic",last_name="Applicant")
outsider=Account.objects.create_user(email=f"outsider-{fixture_tag}@example.invalid",email_verified=True)
admin=Account.objects.create_user(email=f"admin-{fixture_tag}@example.invalid",email_verified=True,role="admin")
member=Account.objects.create_user(email=f"member-{fixture_tag}@example.invalid",email_verified=True,role="member")
president=Account.objects.create_user(email=f"president-{fixture_tag}@example.invalid",email_verified=True,role="president")
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
def next_questionnaire_number(purpose):
    latest=QuestionnaireVersion.objects.filter(purpose=purpose).order_by("-number").values_list("number",flat=True).first()
    return (latest or 0)+1

QuestionnaireVersion.objects.create(purpose="petition",number=next_questionnaire_number("petition"),published=True,
    definition={"fields":fields,"required_document_categories":["CMC"]},
    declaration_en="Synthetic test declaration only",declaration_ar="إقرار تجريبي للاختبار فقط")
QuestionnaireVersion.objects.create(purpose="appeal",number=next_questionnaire_number("appeal"),published=True,
    definition={"fields":[{"code":"new_information","type":"textarea","required":True,
        "label_en":"New information for consideration","label_ar":"معلومات جديدة للنظر فيها"}]},
    declaration_en="Synthetic appeal declaration only",declaration_ar="إقرار استئناف تجريبي للاختبار فقط")
release_definition=QuestionnaireVersion.objects.create(purpose="medical_release",number=next_questionnaire_number("medical_release"),published=True,definition={},
    declaration_en="Synthetic bound professional disclosure only",declaration_ar="تفويض إفصاح مهني تجريبي مرتبط فقط")

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
runtime_database={"mode":"sqlite"}
application=StaticFilesHandler(get_wsgi_application())
def runtime_application(environ,start_response):
    if POSTGRES_OWNER:
        import dj_database_url
        from django.db import connections
        connection=connections["default"]
        if connection.settings_dict["USER"]!="ctm_app":
            connection.close()
            # Change only this HTTP thread's wrapper, never the fixture/setup connection.
            connection.settings_dict={**connection.settings_dict,**dj_database_url.parse(app_database_url)}
        if runtime_database["mode"]!="postgresql_runtime":
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_user,session_user,rolsuper,rolbypassrls,rolinherit FROM pg_roles WHERE rolname=current_user")
                user,session,superuser,bypass,inherit=cursor.fetchone()
                assert user==session=="ctm_app" and not any([superuser,bypass,inherit])
                tables=[model._meta.db_table for model in isolated_models.__dict__.values() if isinstance(model,type) and hasattr(model,"_meta") and model._meta.app_label=="tribunal" and not model._meta.abstract]
                cursor.execute("SELECT count(*),count(*) FILTER(WHERE relrowsecurity AND relforcerowsecurity),count(*) FILTER(WHERE pg_has_role(current_user,relowner,'MEMBER')) FROM pg_class WHERE relname=ANY(%s)",[tables])
                total,forced,owned=cursor.fetchone();assert total==forced and owned==0
            runtime_database.update(mode="postgresql_runtime",current_user=user,session_user=session,superuser=superuser,bypass_rls=bypass,inherit=inherit,domain_tables=total,forced_rls_tables=forced,owner_memberships=owned)
    return application(environ,start_response)
server=make_server(shared_config.bind_host if shared_config else "127.0.0.1",shared_config.bind_port if shared_config else 0,runtime_application,handler_class=Quiet)
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
        page.get_by_role("button",name="My application",exact=True).click()
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
        if POSTGRES_OWNER:
            from applicant_postgres_acceptance import run as run_postgres_focus
            run_postgres_focus(browser,BASE,settings,fixture_db,session_cookie,cookies["admin"],ARTIFACT_ROOT,runtime_database,errors)
        from applicant_history_notice_acceptance import history_checks
        checks.extend(history_checks(browser,page,context,BASE,app_id,cookies,settings,ARTIFACT_ROOT))
        for name in ("outsider","admin"):
            other=browser.new_context()
            other.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies[name],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
            for suffix in ("","history/","files/","payments/"):
                denied=other.request.get(f"{BASE}/api/applications/{app_id}/{suffix}")
                if os.environ.get('CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT')=='hidden404':
                    missing=other.request.get(f"{BASE}/api/applications/{uuid.uuid4()}/{suffix}")
                    assert denied.status==missing.status==404 and denied.json()==missing.json()
                else:assert denied.status==403
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
        hidden_file=stranger.request.get(f"{BASE}/api/files/{file_id}/",headers={"Range":"bytes=0-3"})
        if os.environ.get('CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT')=='hidden404':
            absent_file=stranger.request.get(f"{BASE}/api/files/{uuid.uuid4()}/",headers={"Range":"bytes=0-3"})
            assert hidden_file.status==absent_file.status==404 and hidden_file.json()==absent_file.json()
        else:assert hidden_file.status==403
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
        superseded_original=context.request.get(f"{BASE}/api/files/{file_id}/")
        if os.environ.get('CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT')=='hidden404':
            absent_original=context.request.get(f"{BASE}/api/files/{uuid.uuid4()}/")
            assert superseded_original.status==absent_original.status==404,(superseded_original.status,absent_original.status)
            assert superseded_original.json()==absent_original.json(),(superseded_original.text(),absent_original.text())
        else:assert superseded_original.status==403,superseded_original.text()
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
        # Wait for the language write before synthetic DB setup; SQLite cannot
        # safely overlap that browser transaction with the fixture writer.
        with page.expect_response(lambda response:response.url==BASE+"/api/account/settings/" and response.request.method=="POST") as language_saved:
            page.get_by_role("button",name="English",exact=True).click()
        assert language_saved.value.status==200,language_saved.value.text()
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
        def pending_checkout_fixture():
            from tribunal.services.payments import prepare_checkout
            return str(prepare_checkout(owner,app_id,{"accepted":True,"name":"Original synthetic checkout signer"},
                expected_version=ready_version).pk)
        ready_version=context.request.get(f"{BASE}/api/applications/{app_id}/").json()["version"]
        pending_intent=fixture_db(pending_checkout_fixture)  # Local candidate only, no provider session or payment.
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        expect(page.get_by_text("An existing payment attempt must be resolved",exact=False)).to_be_visible()
        page.get_by_role("button",name="Review answers",exact=True).click()
        expect(page.get_by_role("button",name="Continue to secure payment",exact=True)).to_have_count(0)
        assert page.get_by_label("Your full name",exact=True).count()==0
        assert page.get_by_role("button",name="Resume existing secure checkout",exact=True).count()==0
        checks.append("Actual pending checkout history blocks new checkout/signature; legacy candidate without retained provider URL/expiry cannot enable resume")
        fixture_db(lambda:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.filter(pk=pending_intent).update(state="expired"))
        def retained_checkout_fixture():
            from types import SimpleNamespace
            from unittest.mock import patch
            from django.utils import timezone
            from tribunal.services.payments import create_checkout
            original=settings.STRIPE_SECRET_KEY
            try:
                settings.STRIPE_SECRET_KEY="synthetic-provider-adapter-test-only"
                session=SimpleNamespace(id="cs_synthetic_retained_checkout",url="https://checkout.stripe.com/c/synthetic-retained",
                    expires_at=int((timezone.now()+timezone.timedelta(hours=1)).timestamp()))
                with patch("tribunal.services.payments.stripe.checkout.Session.create",return_value=session) as provider:
                    result=create_checkout(owner,app_id,{"accepted":True,"name":"Original retained synthetic signer"},BASE,
                        expected_version=ready_version)
                    assert provider.call_count==1
                    return result["intent"]
            finally:settings.STRIPE_SECRET_KEY=original
        retained_intent=fixture_db(retained_checkout_fixture)
        retained=context.request.get(f"{BASE}/api/applications/{app_id}/")
        retained_payload=retained.json()
        original_checkout=retained_payload["pending_checkout"]
        assert "no-store" in retained.headers["cache-control"] and retained.json()["can_resume_checkout"]
        assert not retained.json()["can_checkout"] and not retained.json()["can_delete_draft"]
        assert original_checkout["id"]==retained_intent and original_checkout["version"]==ready_version
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        expect(page.get_by_role("button",name="Resume existing secure checkout",exact=True)).to_be_visible()
        expect(page.get_by_text("Original signer: Original retained synthetic signer",exact=True)).to_be_visible()
        assert page.get_by_label("Your full name",exact=True).count()==0
        assert page.get_by_role("button",name="Delete unsubmitted draft",exact=True).count()==0
        checks.append("Actual provider-adapter fixture retains one original checkout; own private GET binds signer/declaration/version and disables fresh charge/signature/deletion")
        page.get_by_role("button",name="العربية",exact=True).click();page.set_viewport_size({"width":390,"height":1000})
        expect(page.get_by_text(original_checkout["declaration_ar"],exact=True)).to_be_visible()
        expect(page.get_by_role("button",name="استئناف محاولة الدفع الآمنة القائمة",exact=True)).to_be_visible()
        assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(ARTIFACT_ROOT/"ar-retained-checkout-390.png"),full_page=True,caret="initial")
        page.get_by_role("button",name="English",exact=True).click();page.set_viewport_size({"width":1280,"height":1000})
        checkout_posts=[]
        page.on("request",lambda request:checkout_posts.append(request.url) if request.method=="POST" and "/checkout/" in request.url else None)
        page.route(original_checkout["checkout_url"],lambda route:route.fulfill(content_type="text/html",body="Synthetic provider destination only"))
        page.get_by_role("button",name="Resume existing secure checkout",exact=True).click()
        page.wait_for_url(original_checkout["checkout_url"])
        assert not checkout_posts
        assert fixture_db(lambda:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.filter(application_id=app_id).count())==2
        checks.append("EN/AR retained declaration renders at mobile width; resume follows exact original URL without checkout POST or replacement attestation")
        page.goto(BASE,wait_until="networkidle")
        page.get_by_role("button",name="My application",exact=True).click()
        page.get_by_role("button",name="Start or resume application",exact=True).click()
        expect(page.get_by_role("button",name="Resume existing secure checkout",exact=True)).to_be_visible()
        probe=browser.new_context();probe.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["outsider"],"url":BASE}])
        hidden_app=probe.request.get(f"{BASE}/api/applications/{app_id}/")
        if os.environ.get('CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT')=='hidden404':
            absent_app=probe.request.get(f"{BASE}/api/applications/{uuid.uuid4()}/")
            assert hidden_app.status==absent_app.status==404 and hidden_app.json()==absent_app.json()
        else:assert hidden_app.status==403
        probe.close()
        if POSTGRES_OWNER:
            # Finance states are monotonic in PostgreSQL. Exercise each terminal or
            # in-flight projection on its own clone-only synthetic application
            # instead of rewinding a successful payment candidate.
            def finance_candidate_fixture():
                import hashlib
                from tribunal.models import Application,AnswerRevision,Attachment,FeeObligation,FileVersion,FileTechnicalEvent
                from tribunal.services.applications import required_documents
                from tribunal.services.files import private_path,write_private_original
                source=Application.objects.select_related("questionnaire").get(pk=app_id)
                actor=Account.objects.create_user(email=f"finance-{uuid.uuid4().hex}@example.invalid",email_verified=True)
                candidate=Application.objects.create(owner=actor,kind="petition",status="draft",current_version=1,questionnaire=source.questionnaire)
                FeeObligation.objects.create(application=candidate)
                revision=AnswerRevision.objects.create(application=candidate,number=1,answers=retained_payload["answers"],actor=actor,questionnaire=source.questionnaire)
                for source_file in required_documents(source,retained_payload["answers"]):
                    payload=private_path(source_file.object_key).read_bytes()
                    attachment=Attachment.objects.create(application=candidate,owner=actor,category=source_file.attachment.category,
                        context=source_file.attachment.context,visibility="own")
                    copied=FileVersion.objects.create(attachment=attachment,number=1,object_key=f"synthetic-finance/{uuid.uuid4().hex}",
                        original_name=source_file.original_name,display_name=source_file.display_name,mime_type=source_file.mime_type,
                        byte_count=len(payload),sha256=hashlib.sha256(payload).hexdigest(),actor=actor)
                    FileTechnicalEvent.objects.create(file=copied,task="scan",result="clean")
                    write_private_original(private_path(copied.object_key),payload)
                return str(candidate.pk),str(revision.pk),actor
            def finance_state_fixture(candidate_id,revision_id,state):
                from tribunal.models import Application,AnswerRevision,CheckoutIntent
                from tribunal.services.applications import required_documents
                candidate=Application.objects.get(pk=candidate_id);revision=AnswerRevision.objects.get(pk=revision_id)
                manifest=[{"id":str(file.pk),"sha256":file.sha256} for file in required_documents(candidate,revision.answers)]
                intent=CheckoutIntent.objects.create(application=candidate,revision=revision,attestation={"accepted":True,"name":"Synthetic finance state"},manifest=manifest,
                    provider_reference=f"cs_{state}_{uuid.uuid4().hex}",state=state)
                return str(intent.pk)
            for payment_state in ["processing","paid","needs_review"]:
                candidate_id,candidate_revision,candidate_actor=fixture_db(finance_candidate_fixture)
                candidate_context=browser.new_context()
                try:
                    candidate_context.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":session_cookie(candidate_actor),"url":BASE}])
                    ready_candidate=candidate_context.request.get(f"{BASE}/api/applications/{candidate_id}/").json()
                    assert ready_candidate["can_checkout"] and not ready_candidate["can_resume_checkout"]
                    candidate_intent=fixture_db(lambda state=payment_state:finance_state_fixture(candidate_id,candidate_revision,state))
                    candidate_projection=candidate_context.request.get(f"{BASE}/api/applications/{candidate_id}/").json()
                    assert not candidate_projection["can_resume_checkout"] and candidate_projection["pending_checkout"] is None
                    assert not candidate_projection["can_checkout"]
                    assert fixture_db(lambda intent=candidate_intent:isolated_models.CheckoutIntent.objects.get(pk=intent).state)==payment_state
                finally:candidate_context.close()
        else:
            for payment_state in ["processing","paid","needs_review"]:
                fixture_db(lambda state=payment_state:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.filter(pk=retained_intent).update(state=state))
                page.get_by_role("button",name="Refresh application status",exact=True).click()
                expect(page.get_by_text("An existing payment attempt must be resolved",exact=False)).to_be_visible()
                expect(page.get_by_role("button",name="Resume existing secure checkout",exact=True)).to_have_count(0)
                assert page.get_by_label("Your full name",exact=True).count()==0 and not checkout_posts
            fixture_db(lambda:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.filter(pk=retained_intent).update(state="pending"))
        assert fixture_db(lambda:isolated_models.CheckoutIntent.objects.get(pk=retained_intent).state)=="pending"
        checks.append("Actual processing/paid/reconciliation candidates remove checkout/resume capability from otherwise-ready filings while preserving exact immutable states; foreign owner cannot read original checkout")
        from unittest.mock import patch
        from django.utils import timezone
        future=timezone.now()+timezone.timedelta(hours=2)
        with patch("tribunal.services.payments.timezone.now",return_value=future):
            expired_projection=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert expired_projection["pending_checkout"] is None and not expired_projection["can_resume_checkout"] and not expired_projection["can_checkout"]
        assert fixture_db(lambda:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.get(pk=retained_intent).state)=="pending"
        checks.append("Authoritative provider-expiry read hides resume while preserving pending candidate and blocking fresh charge; elapsed time is not payment reconciliation")
        changed_answers={**retained_payload["answers"],"statement":"Changed after original checkout"}
        changed=context.request.post(f"{BASE}/api/applications/{app_id}/",data={"answers":changed_answers,"expected_version":ready_version},headers={"X-CSRFToken":csrf})
        assert changed.status==201,changed.text()
        changed_projection=context.request.get(f"{BASE}/api/applications/{app_id}/").json()
        assert not changed_projection["can_resume_checkout"] and changed_projection["pending_checkout"] is None and not changed_projection["can_checkout"]
        assert fixture_db(lambda:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.get(pk=retained_intent).attestation)==original_checkout["attestation"]
        fixture_db(lambda:__import__('tribunal.models',fromlist=['CheckoutIntent']).CheckoutIntent.objects.filter(pk=retained_intent).update(state="expired"))
        checks.append("Saved revision change disables original checkout resume without altering original attestation; candidate reconciliation remains explicit synthetic setup")
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
        if CHECK_RETURNED_PRIVACY:
            # Separate acceptance probe: fails if any direct-owner F08 boundary regresses.
            assigned=staff.request.post(f"{BASE}/api/cases/{current['case_id']}/assignment/",data={
                "member_id":str(member.pk),"president_id":str(president.pk)},headers={"X-CSRFToken":staff_csrf})
            assert assigned.status==201,assigned.text()
            def correction_notice_counts():
                from tribunal.models import Notification,Outbox
                kinds=["answer_changed","file_uploaded"]
                return (Notification.objects.filter(recipient=member,kind__in=kinds).count(),
                        Outbox.objects.filter(recipient=member,kind__in=kinds).count())
            notice_counts=fixture_db(correction_notice_counts)
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
            # AS-F25-1: a later pending scan must not displace the clean formal snapshot.
            fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=pending_file,task="scan",result="pending"))
            pending_detail=staff.request.get(f"{BASE}/api/applications/{app_id}/").json()
            pending_listing=staff.request.get(f"{BASE}/api/cases/{current['case_id']}/files/").json()
            pending_scan_checks={
                "pending_replacement_keeps_formal_manifest":replacement_id in json.dumps(pending_detail.get("manifest",[])) and pending_file not in json.dumps(pending_detail.get("manifest",[])),
                "pending_replacement_keeps_formal_listing":replacement_id in json.dumps(pending_listing) and pending_file not in json.dumps(pending_listing),
                "formal_original_download_survives_pending_replacement":staff.request.get(f"{BASE}/api/files/{replacement_id}/").status==200,
                "council_cannot_download_pending_replacement":staff.request.get(f"{BASE}/api/files/{pending_file}/").status in {403,404},
                "owner_cannot_download_unscanned_replacement":context.request.get(f"{BASE}/api/files/{pending_file}/").status in {403,404},
            }
            assert all(pending_scan_checks.values()),"Pending replacement displaced formal submission or exposed unscanned bytes"
            fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=pending_file,task="scan",result="clean"))
            checks.append("AS-F25 pending replacement keeps prior clean formal manifest/list/download while pending bytes remain denied to owner and council")
            staff_detail=staff.request.get(f"{BASE}/api/applications/{app_id}/").json()
            staff_history=staff.request.get(f"{BASE}/api/applications/{app_id}/history/").json()
            case_files=staff.request.get(f"{BASE}/api/cases/{current['case_id']}/files/").json()
            staff_audit=staff.request.get(f"{BASE}/api/cases/{current['case_id']}/audit/").json()
            owner_revision=context.request.get(f"{BASE}/api/applications/{app_id}/history/").json()["items"][-1]["id"]
            # wsgiref may emit a body on HEAD errors; use a HEAD-aware reader and close it.
            head_connection=http.client.HTTPConnection("127.0.0.1",server.server_port)
            try:
                head_connection.request("HEAD",f"/api/files/{pending_file}/",headers={"Cookie":f"{settings.SESSION_COOKIE_NAME}={cookies['admin']}"})
                pending_head_status=head_connection.getresponse().status
            finally:head_connection.close()
            privacy={
                "council_detail_keeps_formal_answers":staff_detail["answers"].get("first_name")==formal["answers"].get("first_name"),
                "council_version_keeps_formal_revision":staff_detail["version"]==formal["version"],
                "council_history_excludes_pending_answers":marker not in json.dumps(staff_history),
                "council_case_files_exclude_pending_original":pending_file not in json.dumps(case_files),
                "council_direct_download_denies_pending_original":staff.request.get(f"{BASE}/api/files/{pending_file}/").status in {403,404},
                "council_range_denies_pending_original":staff.request.get(f"{BASE}/api/files/{pending_file}/",headers={"Range":"bytes=0-3"}).status in {403,404},
                "council_preview_denies_pending_original":staff.request.get(f"{BASE}/api/files/{pending_file}/?view=1").status in {403,404},
                "council_manifest_keeps_submitted_original":replacement_id in json.dumps(staff_detail.get("manifest",[])) and pending_file not in json.dumps(staff_detail.get("manifest",[])),
                "council_head_denies_pending_original":pending_head_status in {403,404},
                "council_listing_keeps_formal_original":replacement_id in json.dumps(case_files),
                "council_formal_original_download_survives":staff.request.get(f"{BASE}/api/files/{replacement_id}/").status==200,
                "council_audit_excludes_pending_sources":pending_file not in json.dumps(staff_audit) and owner_revision not in json.dumps(staff_audit),
                "assigned_manager_receives_no_early_correction_alert":fixture_db(correction_notice_counts)==notice_counts,
            }
            owner_checks={"owner_keeps_saved_answers":context.request.get(f"{BASE}/api/applications/{app_id}/").json()["answers"]["first_name"]==marker,
                          "owner_keeps_pending_original":context.request.get(f"{BASE}/api/files/{pending_file}/").status==200}
            report={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],"acceptance":"F08/F25 direct-owner returned privacy",
                    "checks":privacy,"owner_checks":owner_checks,"pending_scan_checks":pending_scan_checks,
                    "remaining_surfaces":["live search integration","live email delivery","PostgreSQL RLS"],
                    "scope":"Isolated SQLite/browser API fixtures; no actual case data"}
            (ARTIFACT_ROOT/"returned-privacy-result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report,indent=2))
            assert all(privacy.values()) and all(owner_checks.values()),"Returned privacy acceptance failed; see returned-privacy-result.json"
            checks.append("Returned privacy isolates pending answers/originals/audit/alerts while owner retains corrections and council retains formal snapshot")
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
        if CHECK_RETURNED_PRIVACY:
            published=staff.request.get(f"{BASE}/api/applications/{app_id}/").json()
            report["post_resubmission_checks"]={
                "council_sees_formally_resubmitted_answers":published["answers"]["first_name"]==marker,
                "new_manifest_binds_resubmitted_original":pending_file in json.dumps(published.get("manifest",[])),
                "new_manifest_does_not_bind_superseded_original":replacement_id not in json.dumps(published.get("manifest",[])),
                "council_can_download_resubmitted_original":staff.request.get(f"{BASE}/api/files/{pending_file}/").status==200,
                "earlier_submitted_original_retained":private_path(latest.object_key).read_bytes()==replacement,
            }
            (ARTIFACT_ROOT/"returned-privacy-result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            assert all(report["post_resubmission_checks"].values()),"Formal resubmission visibility failed"
            checks.append("Formal resubmission publishes corrected answers/exact current original while retaining prior submitted bytes")
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
        page.get_by_role("button",name="My appointments",exact=True).click()
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
        stranger.close()
        checks.append("Actual cancellation removes browser response actions; cancelled and outsider responses are denied by server")
        def own_requests_fixture():
            from django.utils import timezone
            from tribunal.models import ReportRequest,Proceeding
            proceeding=Proceeding.objects.filter(case_id=current["case_id"],status="open").first()
            for kind,state,title in [("intake","sent","Own sent intake"),("intake","sent","Own unresolved intake"),("medical","sent","Own assessment"),
                                     ("intake","draft","Private staff draft"),("interview","sent","Private interview"),
                                     ("external_priest","sent","Private external request")]:
                ReportRequest.objects.create(case_id=current["case_id"],proceeding=proceeding,subject_id=party_id,
                    author=admin,kind=kind,state=state,title=title,language="both",sent_at=timezone.now() if state=="sent" else None,
                    instructions="Own private request instructions",questions=[{"code":"Q1","version":1,
                        "en":"Own bound request question" if title=="Own sent intake" else "Unresolved bound question",
                        "ar":"سؤال خاص بالطلب"}] if kind=="intake" else [])
        fixture_db(own_requests_fixture)  # Synthetic sent snapshots; not institution wording/send acceptance.
        own_requests=context.request.get(f"{BASE}/api/cases/{current['case_id']}/requests/").json()["items"]
        assert {row["title"] for row in own_requests}=={"Own sent intake","Own unresolved intake","Own assessment"}
        assert all(isinstance(row["can_respond"],bool) and len(row["request_version"])==64 for row in own_requests)
        intake_request=next(row for row in own_requests if row["title"]=="Own sent intake")
        assessment_request=next(row for row in own_requests if row["title"]=="Own assessment")
        page.get_by_role("button",name="Home",exact=True).click()
        page.get_by_text(current["case_number"],exact=True).click()
        intake_panel=page.get_by_role("region",name="Own sent intake",exact=True)
        intake_panel.get_by_role("button",name="Open request",exact=True).click()
        expect(page.get_by_label("Own bound request question",exact=True)).to_be_enabled()
        page.get_by_label("Own bound request question",exact=True).fill("Own private bound intake answer")
        assert not errors,errors
        page.locator("#main").get_by_role("button",name="Back to cases",exact=True).last.click()
        expect(page.get_by_text("Your local response has not been submitted.",exact=False)).to_be_visible()
        page.get_by_role("button",name="Keep editing",exact=True).click()
        assert context.request.post(f"{BASE}/api/requests/{intake_request['id']}/complete/",data={
            "expected_version":"0"*64,"answers":{"Q1":"Stale"}},headers={"X-CSRFToken":csrf}).status==422
        page.get_by_role("button",name="Review response",exact=True).click()
        with page.expect_response(lambda response:response.url==f"{BASE}/api/requests/{intake_request['id']}/complete/") as intake_sent:
            page.get_by_role("button",name="Submit response",exact=True).click()
        assert intake_sent.value.status==201,intake_sent.value.text()
        intake_payload=intake_sent.value.request.post_data_json;intake_report=intake_sent.value.json()["id"]
        assert intake_payload=={"expected_version":intake_request["request_version"],"answers":{"Q1":"Own private bound intake answer"}}
        expect(page.get_by_role("region",name="Own response receipt",exact=True)).to_be_visible()
        replay=context.request.post(f"{BASE}/api/requests/{intake_request['id']}/complete/",data=intake_payload,headers={"X-CSRFToken":csrf})
        assert replay.status==201 and replay.json()["id"]==intake_report
        changed={**intake_payload,"answers":{"Q1":"Changed retry"}}
        assert context.request.post(f"{BASE}/api/requests/{intake_request['id']}/complete/",data=changed,headers={"X-CSRFToken":csrf}).status==422
        from tribunal.models import ReportRevision,MedicalRelease
        assert fixture_db(lambda:ReportRevision.objects.filter(report_id=intake_report).count())==1
        checks.append("Actual intake browser binds fingerprint/questions, guards local navigation, rejects stale write and recovers one receipt on exact replay")
        page.get_by_role("button",name="Back to requests",exact=True).click()
        page.get_by_role("region",name="Own assessment",exact=True).get_by_role("button",name="Open request",exact=True).click()
        expect(page.get_by_text("Synthetic bound professional disclosure only",exact=True)).to_be_visible()
        expect(page.get_by_text("No signed release is recorded.",exact=True)).to_be_visible()
        assert page.get_by_role("button",name="Submit response",exact=True).count()==0
        assert context.request.post(f"{BASE}/api/requests/{assessment_request['id']}/complete/",data={
            "expected_version":assessment_request["request_version"],"answers":{"files":[]}},headers={"X-CSRFToken":csrf}).status==422
        checks.append("Actual assessment read binds published bilingual disclosure and explicit capability; upload alone cannot stand in for consent or report submission")
        request_pdf=b"%PDF-1.7 synthetic-request-original-only"
        for purpose,legend,name in [("report","Report or response evidence","assessment.pdf"),("consent","Signed release original","consent.pdf")]:
            slot=page.get_by_role("group",name=legend,exact=True)
            slot.locator('input[type="file"]').set_input_files({"name":name,"mimeType":"application/pdf","buffer":request_pdf})
            with page.expect_response(lambda response:response.url==BASE+"/api/files/" and response.request.method=="POST") as original:
                slot.get_by_role("button",name="Upload original",exact=True).click()
            assert original.value.status==201,original.value.text()
            expect(page.get_by_text("The server acknowledged the upload.",exact=False)).to_be_visible()
            expect(page.get_by_role("button",name="Refresh request and files",exact=True)).to_be_enabled()
        request_files=context.request.get(f"{BASE}/api/requests/{assessment_request['id']}/files/")
        assert request_files.status==200 and "no-store" in request_files.headers.get("cache-control","")
        files=request_files.json()["items"];consent_original=next(file for file in files if file["purpose"]=="consent")
        report_original=next(file for file in files if file["purpose"]=="report")
        assert all(file["scan_state"]=="clean" and file["download_url"]==f"/api/files/{file['id']}/" for file in files)
        assert staff.request.get(f"{BASE}/api/files/{report_original['id']}/").status==403
        alien=browser.new_context();alien.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["outsider"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        assert alien.request.get(f"{BASE}/api/requests/{assessment_request['id']}/files/").status==403
        assert alien.request.get(f"{BASE}/api/files/{report_original['id']}/").status==403
        alien.close()
        checks.append("Actual request multipart uploads derive subject/case/proceeding, preserve consent/report purpose and deny other subjects and unconsented council bytes")
        fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=report_original["id"],task="scan",result="pending"))
        page.get_by_role("button",name="Refresh request and files",exact=True).click()
        expect(page.get_by_text("Report or response evidence · Safety check pending",exact=True)).to_be_visible()
        assert context.request.get(f"{BASE}/api/files/{report_original['id']}/").status==403
        fixture_db(lambda:FileTechnicalEvent.objects.create(file_id=report_original["id"],task="scan",result="clean"))
        page.get_by_role("button",name="Refresh request and files",exact=True).click()
        expect(page.get_by_text("Report or response evidence · Safety check passed",exact=True)).to_be_visible()
        checks.append("Latest actual technical event removes unsafe request byte access; clean refresh restores current original without implying consent")
        page.get_by_role("button",name="العربية",exact=True).click()
        expect(page.get_by_text("تفويض إفصاح مهني تجريبي مرتبط فقط",exact=True)).to_be_visible()
        page.set_viewport_size({"width":390,"height":1100})
        assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.get_by_role("button",name="English",exact=True).click();page.set_viewport_size({"width":1280,"height":1000})
        page.get_by_label("Choose the signed release original",exact=True).select_option(consent_original["id"])
        expect(page.get_by_role("button",name="Review disclosure consent",exact=True)).to_be_disabled()
        page.get_by_role("checkbox",name="I have read and accept this exact disclosure declaration for the council and this request.",exact=True).check()
        page.get_by_role("button",name="Review disclosure consent",exact=True).click()
        with page.expect_response(lambda response:response.url==f"{BASE}/api/requests/{assessment_request['id']}/release/") as signed:
            page.get_by_role("button",name="Confirm disclosure consent",exact=True).click()
        assert signed.value.status==201,signed.value.text()
        consent_payload=signed.value.request.post_data_json
        assert consent_payload=={"expected_version":assessment_request["request_version"],"declaration_id":str(release_definition.pk),
            "accepted":True,"file_id":consent_original["id"],"scope":{"council":True}}
        expect(page.get_by_text("A signed release for this request and purpose is recorded.",exact=True)).to_be_visible()
        own_after_sign=next(row for row in context.request.get(f"{BASE}/api/cases/{current['case_id']}/requests/").json()["items"] if row["id"]==assessment_request["id"])
        assert own_after_sign["can_respond"] and not own_after_sign["can_sign_release"]
        assert own_after_sign["signed_releases"][0]["scope"]=={"council":True,"purpose":"medical","request_id":assessment_request["id"],"proceeding_id":assessment_request["proceeding_id"]}
        assert staff.request.get(f"{BASE}/api/files/{report_original['id']}/").status==200
        checks.append("Actual explicit consent binds displayed declaration ID, literal acceptance and exact safe CONSENT original; server retains request/purpose scope and enables report response")
        replacement= context.request.post(BASE+"/api/files/",multipart={"request_id":assessment_request["id"],
            "expected_request_version":assessment_request["request_version"],"category":"CONSENT","attachment_id":consent_original["attachment_id"],
            "file":{"name":"replacement.pdf","mimeType":"application/pdf","buffer":request_pdf}},headers={"X-CSRFToken":csrf})
        assert replacement.status==422,replacement.text()
        assert context.request.get(f"{BASE}/api/files/{consent_original['id']}/").body()==request_pdf
        page.get_by_role("checkbox",name=report_original["name"],exact=True).check()
        page.get_by_role("button",name="Review response",exact=True).click()
        with page.expect_response(lambda response:response.url==f"{BASE}/api/requests/{assessment_request['id']}/complete/") as assessment_sent:
            page.get_by_role("button",name="Submit response",exact=True).click()
        assert assessment_sent.value.status==201,assessment_sent.value.text()
        assessment_payload=assessment_sent.value.request.post_data_json;assessment_report=assessment_sent.value.json()["id"]
        assert assessment_payload=={"expected_version":assessment_request["request_version"],"answers":{"files":[report_original["id"]]}}
        expect(page.get_by_role("region",name="Own response receipt",exact=True)).to_be_visible()
        assert context.request.post(f"{BASE}/api/requests/{assessment_request['id']}/complete/",data=assessment_payload,headers={"X-CSRFToken":csrf}).json()["id"]==assessment_report
        assert fixture_db(lambda:ReportRevision.objects.filter(report_id=assessment_report).count())==1
        assert fixture_db(lambda:MedicalRelease.objects.filter(request_id=assessment_request["id"]).count())==1
        assert page.locator('input[type="file"]').count()==0
        checks.append("Actual assessment submission uses distinct report original, preserves signed consent original and recovers exactly one report/release without another signature")
        page.get_by_role("button",name="Back to requests",exact=True).click()
        def closed_case_fixture():
            from tribunal.models import Case,Proceeding,OpenCaseClaim
            Case.objects.filter(pk=current["case_id"]).update(status="closed")
            Proceeding.objects.filter(case_id=current["case_id"],status="open").update(status="closed")
            OpenCaseClaim.objects.filter(case_id=current["case_id"]).delete()
        fixture_db(closed_case_fixture)  # Explicit closed-case setup, not decree/closure acceptance.
        page.locator("#main").get_by_role("button",name="Back to cases",exact=True).last.click()
        page.get_by_role("button",name="Past cases",exact=True).click()
        page.get_by_text(current["case_number"],exact=True).click()
        expect(page.get_by_text("Own sent intake",exact=True)).to_be_visible()
        expect(page.get_by_text("Own bound request question",exact=True)).to_be_visible()
        expect(page.get_by_text("Own assessment",exact=True)).to_be_visible()
        assert page.get_by_text("Private staff draft",exact=True).count()==0
        assert page.get_by_text("Private interview",exact=True).count()==0
        assert page.get_by_text("Private external request",exact=True).count()==0
        checks.append("Actual own request list renders bound questions and assessment instructions while excluding staff drafts/interviews/external requests")
        expect(page.get_by_role("button",name="Start or resume appeal",exact=True)).to_be_visible()
        expect(page.get_by_text("No certificate is currently released to your account.",exact=True)).to_be_visible()
        assert page.get_by_role("link",name="View or download signed PDF",exact=True).count()==0
        checks.append("Actual own case read confirms no active decree releases and exposes no certificate links")
        page.get_by_role("button",name="Start or resume appeal",exact=True).click()
        expect(page.get_by_label("New information for consideration",exact=False)).to_be_visible()
        appeal=next(row for row in context.request.get(BASE+"/api/applications/").json()["items"] if row["kind"]=="appeal")
        appeal_id=appeal["id"]
        assert appeal["case_id"]==current["case_id"] and appeal["status"]=="draft"
        reused=context.request.post(BASE+"/api/applications/",data={"kind":"appeal","case_id":current["case_id"]},headers={"X-CSRFToken":csrf})
        assert reused.status==201 and reused.json()["id"]==appeal_id
        assert context.request.get(f"{BASE}/api/cases/{current['case_id']}/").json()["status"]=="closed"
        page.get_by_label("New information for consideration",exact=False).fill("New supporting information for the closed case")
        page.get_by_role("button",name="Save draft",exact=True).click()
        expect(page.get_by_text("Your answers have been saved.",exact=True)).to_be_visible()
        assert context.request.get(f"{BASE}/api/applications/{appeal_id}/").json()["answers"]["new_information"].startswith("New supporting")
        checks.append("Applicant closed-case appeal entry opens published appeal form, reuses draft and saves new information without reopening case")
        appeal_requirements=context.request.get(f"{BASE}/api/applications/{appeal_id}/files/").json()["requirements"]
        petition_copy=next(row for row in appeal_requirements if row["category"]=="PET")
        appeal_slot=page.get_by_role("region",name=petition_copy["label_en"],exact=True)
        appeal_slot.locator('input[type="file"]').set_input_files({"name":"appeal.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 synthetic-appeal-evidence"})
        appeal_slot.get_by_role("button",name="Upload original",exact=True).click()
        expect(appeal_slot.get_by_role("link",name="Download original",exact=True)).to_be_visible()
        waived=staff.request.post(f"{BASE}/api/applications/{appeal_id}/waiver/",data={},headers={"X-CSRFToken":staff_csrf})
        assert waived.status==201,waived.text()
        page.get_by_role("button",name="Refresh application status",exact=True).click()
        page.get_by_role("button",name="Review answers",exact=True).click()
        page.get_by_label("I have read and accept this declaration.",exact=True).check()
        page.get_by_label("Your full name",exact=False).fill("Synthetic Applicant")
        with page.expect_response(lambda response:response.url==f"{BASE}/api/applications/{appeal_id}/submit/") as appeal_submitted:
            page.get_by_role("button",name="Submit application",exact=True).click()
        assert appeal_submitted.value.status==201,appeal_submitted.value.text()
        pending_appeal=context.request.get(f"{BASE}/api/applications/{appeal_id}/").json()
        assert pending_appeal["status"]=="submitted" and not pending_appeal["can_edit"]
        assert context.request.get(f"{BASE}/api/cases/{current['case_id']}/").json()["status"]=="closed"
        checks.append("Browser appeal evidence/declaration and actual authorized waiver submit to same closed case without reopening or mutating original proceeding")
        from applicant_supplement_acceptance import run as run_supplement_acceptance
        checks.extend(run_supplement_acceptance(page,context,staff,BASE,csrf,staff_csrf,appeal_id,uploaded[0][0],fixture_db,ARTIFACT_ROOT,cookies["outsider"],settings.SESSION_COOKIE_NAME))
        def sibling_reopened_fixture():
            from tribunal.models import Case,Proceeding,Party,OpenCaseClaim
            Case.objects.filter(pk=current["case_id"]).update(status="open")
            Application.objects.filter(pk=appeal_id).update(status="accepted")
            proceeding=Proceeding.objects.filter(case_id=current["case_id"]).order_by("-sequence").first()
            Proceeding.objects.create(case_id=current["case_id"],kind="appeal",status="open",sequence=proceeding.sequence+1)
            Party.objects.update_or_create(case_id=current["case_id"],slot="B",defaults={
                "person_id":outsider.person_id,"account":outsider,"name":"Synthetic linked spouse"})
            for actor in (owner,outsider):
                OpenCaseClaim.objects.update_or_create(person_id=actor.person_id,defaults={"case_id":current["case_id"]})
        fixture_db(sibling_reopened_fixture)  # State fixture only; not council acceptance or identity-linking proof.
        sibling=browser.new_context(viewport={"width":1280,"height":1000})
        sibling.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["outsider"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        assert sibling.request.get(BASE+"/api/applications/").json()["items"]==[]
        sibling_page=sibling.new_page();sibling_page.on("pageerror",lambda error:errors.append(str(error)))
        sibling_page.goto(BASE,wait_until="networkidle")
        sibling_page.get_by_text(current["case_number"],exact=True).click()
        assert sibling.request.get(f"{BASE}/api/cases/{current['case_id']}/requests/").json()=={"items":[]}
        expect(sibling_page.get_by_text("No requests are currently listed for you.",exact=True)).to_be_visible()
        assert sibling_page.get_by_text("Own sent intake",exact=True).count()==0
        hidden_appeal=sibling.request.get(f"{BASE}/api/applications/{appeal_id}/")
        if os.environ.get('CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT')=='hidden404':
            absent_appeal=sibling.request.get(f"{BASE}/api/applications/{uuid.uuid4()}/")
            assert hidden_appeal.status==absent_appeal.status==404 and hidden_appeal.json()==absent_appeal.json()
        else:assert hidden_appeal.status==403
        sibling_csrf=next(cookie["value"] for cookie in sibling.cookies() if cookie["name"]=="csrftoken")
        assert sibling.request.post(f"{BASE}/api/appeals/{appeal_id}/additions/",data={"text":"Not my supplement","file_ids":[],
            "expected_version":pending_appeal["version"],"idempotency_key":str(uuid.uuid4())},headers={"X-CSRFToken":sibling_csrf}).status==403
        checks.append("Linked spouse cannot read another applicant's requests or supplement history, or author additions")
        expect(sibling_page.get_by_role("button",name="Start or resume appeal",exact=True)).to_be_visible()
        sibling_page.get_by_role("button",name="Start or resume appeal",exact=True).click()
        expect(sibling_page.get_by_label("New information for consideration",exact=False)).to_be_visible()
        sibling_appeal=sibling.request.get(BASE+"/api/applications/").json()["items"][0]
        assert sibling_appeal["kind"]=="appeal" and sibling_appeal["case_id"]==current["case_id"] and sibling_appeal["id"]!=appeal_id
        sibling.close()
        checks.append("Previously non-filing linked spouse can start own appeal from reopened-sibling case context without exposing the first spouse's appeal")
        signed_file=next(row["id"] for row in context.request.get(f"{BASE}/api/applications/{app_id}/files/").json()["items"] if row["category"]=="CMC" and row["scan_state"]=="clean")
        signed_bytes=context.request.get(f"{BASE}/api/files/{signed_file}/").body()
        def decree_access_fixture():
            import hashlib
            from django.utils import timezone
            from tribunal.models import DecisionRevision,Decree,Proceeding,Attachment,FileVersion,FileTechnicalEvent,Case
            from tribunal.services.files import write_private_original,private_path
            proceeding=Proceeding.objects.filter(case_id=current["case_id"],kind="initial").first()
            attachment=Attachment.objects.create(case_id=current["case_id"],proceeding=proceeding,category="DEC",visibility="council")
            file=FileVersion.objects.create(attachment=attachment,number=1,object_key=f"synthetic-decrees/{uuid.uuid4().hex}.pdf",
                original_name="synthetic-signed.pdf",display_name="synthetic-signed.pdf",mime_type="application/pdf",
                byte_count=len(signed_bytes),sha256=hashlib.sha256(signed_bytes).hexdigest(),actor=admin)
            FileTechnicalEvent.objects.create(file=file,task="scan",result="clean")
            write_private_original(private_path(file.object_key),signed_bytes)
            decision=DecisionRevision.objects.create(proceeding=proceeding,number=1,type="nullity",grounds="Synthetic access test only",actor=admin,
                entitlements={party_id:"certificate"})
            decree=Decree.objects.create(decision=decision,reference="DCR-SYNTHETIC-ACCESS",language="both",
                signed_file=file,signer=president,issued_at=timezone.now())
            Case.objects.filter(pk=current["case_id"]).update(status="closed")
            return str(decree.pk),str(file.pk)
        decree_id,signed_file=fixture_db(decree_access_fixture)  # Synthetic stored signed bytes/closed state only, not issuance/signature acceptance.
        assert context.request.get(f"{BASE}/api/files/{signed_file}/").status==403
        release=staff.request.post(f"{BASE}/api/decrees/{decree_id}/release/",data={"party_id":party_id,"action":"release"},headers={"X-CSRFToken":staff_csrf})
        assert release.status==201,release.text()
        case_detail=context.request.get(f"{BASE}/api/cases/{current['case_id']}/")
        released_row=case_detail.json()["released_decrees"][0]
        assert "no-store" in case_detail.headers.get("cache-control","")
        assert released_row["id"]==decree_id and released_row["language"]=="bilingual"
        assert released_row["signed_file"]["download_url"]==f"/api/files/{signed_file}/"
        page.get_by_role("button",name="Past cases",exact=True).click()
        page.get_by_text(current["case_number"],exact=True).click()
        expect(page.get_by_text("DCR-SYNTHETIC-ACCESS",exact=True)).to_be_visible()
        expect(page.get_by_text("English and Arabic",exact=True)).to_be_visible()
        certificate=page.get_by_role("link",name="View or download signed PDF",exact=True)
        expect(certificate).to_have_attribute("href",f"/api/files/{signed_file}/")
        page.get_by_role("button",name="العربية",exact=True).click()
        expect(page.get_by_text("الإنجليزية والعربية",exact=True)).to_be_visible()
        expect(page.get_by_role("link",name="عرض أو تنزيل ملف PDF الموقّع",exact=True)).to_have_attribute("href",f"/api/files/{signed_file}/")
        page.set_viewport_size({"width":390,"height":950})
        assert page.locator("[style]").count()==0
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.get_by_role("button",name="English",exact=True).click()
        page.set_viewport_size({"width":1280,"height":1000})
        other_recipient=browser.new_context()
        other_recipient.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookies["outsider"],"url":BASE,"httpOnly":True,"sameSite":"Lax"}])
        assert other_recipient.request.get(f"{BASE}/api/cases/{current['case_id']}/").json()["released_decrees"]==[]
        assert other_recipient.request.get(f"{BASE}/api/files/{signed_file}/").status==403
        other_recipient.close()
        checks.append("Actual own release list renders bilingual certificate metadata and exact PDF action while linked spouse receives no release or bytes")
        released=context.request.get(f"{BASE}/api/files/{signed_file}/")
        assert released.status==200 and released.body()==signed_bytes and "no-store" in released.headers.get("cache-control","")
        assert context.request.get(f"{BASE}/api/files/{signed_file}/",headers={"Range":"bytes=0-3"}).status==206
        assert context.request.get(f"{BASE}/api/files/{signed_file}/?view=1").status==200
        revoked=staff.request.post(f"{BASE}/api/decrees/{decree_id}/release/",data={"party_id":party_id,"action":"withdraw"},headers={"X-CSRFToken":staff_csrf})
        assert revoked.status==201,revoked.text()
        page.get_by_role("button",name="Refresh released certificates",exact=True).click()
        expect(page.get_by_text("No certificate is currently released to your account.",exact=True)).to_be_visible()
        expect(certificate).to_have_count(0)
        assert context.request.get(f"{BASE}/api/cases/{current['case_id']}/").json()["released_decrees"]==[]
        for suffix,headers in [("",{}),("",{"Range":"bytes=0-3"}),("?view=1",{})]:
            assert context.request.get(f"{BASE}/api/files/{signed_file}/{suffix}",headers=headers).status==403
        head=http.client.HTTPConnection("127.0.0.1",server.server_port)
        try:
            head.request("HEAD",f"/api/files/{signed_file}/",headers={"Cookie":f"{settings.SESSION_COOKIE_NAME}={cookies['owner']}"})
            assert head.getresponse().status==403
        finally:head.close()
        checks.append("Real explicit decree release grants exact stored synthetic PDF; withdrawal revokes retained full/range/preview/HEAD URLs with no-store delivery")
        # Default acceptance includes closure privacy. Explicit 0 is a baseline-only run.
        if os.environ.get("CTM_APPLICANT_REQUEST_CLOSURE_AUDIT","1")=="1":
            def close_requests_fixture():
                from tribunal.models import Case
                from tribunal.services.decisions import close_case
                close_case(admin,Case.objects.get(pk=current["case_id"]),"synthetic_request_closure_audit",notify_parties=False)
            fixture_db(close_requests_fixture)
            closed_requests=context.request.get(f"{BASE}/api/cases/{current['case_id']}/requests/").json()["items"]
            closure_report={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],
                "scope":"Isolated synthetic request closure privacy diagnostic",
                "preceding_scenario_groups_passed":len(checks),
                "unsent_staff_draft_excluded":not any(row["title"]=="Private staff draft" for row in closed_requests),
                "sent_request_retained":any(row["title"]=="Own unresolved intake" and row["state"]=="closed" for row in closed_requests)}
            (ARTIFACT_ROOT/"request-closure-privacy-result.json").write_text(json.dumps(closure_report,indent=2),encoding="utf-8")
            print(json.dumps(closure_report,indent=2))
            assert closure_report["unsent_staff_draft_excluded"],"Backend request closure exposes unsent staff draft; see request-closure-privacy-result.json"
            assert closure_report["sent_request_retained"]
            for request_id,payload,report_id in [(intake_request["id"],intake_payload,intake_report),
                    (assessment_request["id"],assessment_payload,assessment_report)]:
                recovered=context.request.post(f"{BASE}/api/requests/{request_id}/complete/",data=payload,headers={"X-CSRFToken":csrf})
                assert recovered.status==201 and recovered.json()["id"]==report_id
            checks.append("Actual closure preserves never-sent draft privacy and sent closed reads; exact intake/assessment receipt replays still recover after closure")
        from applicant_filing_acceptance import run as run_filing_acceptance
        checks.extend(run_filing_acceptance(browser,BASE,settings,fixture_db,session_cookie,staff,staff_csrf,errors))
        from applicant_message_acceptance import run as run_message_acceptance
        checks.extend(run_message_acceptance(browser,page,context,staff,BASE,csrf,staff_csrf,current["case_id"],current["case_number"],party_id,cookies["outsider"],settings,fixture_db,ARTIFACT_ROOT,admin.pk))
        from applicant_history_notice_acceptance import notification_checks
        checks.extend(notification_checks(browser,page,context,BASE,str(owner.pk),cookies,settings,fixture_db,ARTIFACT_ROOT))
        staff.close()
        assert page.locator("[style]").count()==0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors,errors
        browser.close()
except Exception as failure:
    partial={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],"completed_groups":len(checks),"checks":checks,"page_errors":errors,"runtime_database":runtime_database,"failure":{"type":type(failure).__name__,"message":str(failure)[:5000]},"scope":"Interrupted isolated acceptance; completed groups are not a full-suite pass"}
    if shared_config:partial["preflight"]=safe_preflight_evidence(shared_config,image_evidence)
    (ARTIFACT_ROOT/"partial-result.json").write_text(json.dumps(partial,indent=2),encoding="utf-8")
    raise
finally:
    server.shutdown()
result={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],"passed":len(checks),"checks":checks,
        "page_errors":errors,"runtime_database":runtime_database,"scope":"Real Django APIs, isolated "+("PostgreSQL runtime role" if POSTGRES_OWNER else "SQLite")+"/synthetic sessions; authorized fixture waiver; scanner bypass test policy; no live provider payment/antivirus acceptance"}
if shared_config:
    from applicant_shared_loopback import source_tree_sha256
    ending_source_hash=source_tree_sha256(shared_config.source_dir)
    if ending_source_hash!=shared_config.expected_source_tree_sha256:
        raise RuntimeError("Immutable source tree changed during shared-loopback acceptance.")
    result["preflight"]=safe_preflight_evidence(shared_config,image_evidence)
    result["source_tree_sha256_after"]=ending_source_hash
OUTPUT_PATH.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
