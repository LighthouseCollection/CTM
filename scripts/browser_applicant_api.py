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
        page.get_by_label("Statement",exact=False).fill("Synthetic applicant statement")
        page.get_by_role("button",name="Add another entry",exact=True).click()
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
        expect(page.get_by_text("Document access is no longer available.",exact=True)).to_be_visible()
        assert page.get_by_role("button",name="Submit application",exact=True).count()==0
        checks.append("Missing real draft-file endpoint remains visibly unavailable and cannot enable filing")
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
            for suffix in ("","history/"):
                assert other.request.get(f"{BASE}/api/applications/{app_id}/{suffix}").status==403
            other.close()
        checks.append("Real API denies outsider and council draft/detail/history access")
        assert page.locator("[style]").count()==0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors,errors
        browser.close()
finally:
    server.shutdown()
result={"backend_sha":os.environ["CTM_TEST_BACKEND_SHA"],"passed":len(checks),"checks":checks,
        "page_errors":errors,"scope":"Real Django APIs, isolated SQLite and synthetic test-client sessions; no provider/payment/antivirus acceptance"}
(ROOT/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
