"""Real own supplement read/write/recovery checks with isolated synthetic records."""
import uuid
from pathlib import Path
from playwright.sync_api import expect


def run(page,context,staff,base,csrf,staff_csrf,app_id,source_file_id,fixture_db,output,outsider_cookie,session_cookie_name):
    from tribunal import models as m
    checks=[]
    url=f"{base}/api/appeals/{app_id}/additions/"
    def post(payload):return context.request.post(url,data=payload,headers={"X-CSRFToken":csrf})
    def detail():return context.request.get(f"{base}/api/applications/{app_id}/")
    before=detail();row=before.json();assert row["can_supplement"] and row["supplements"]==[]
    assert "no-store" in before.headers["cache-control"]
    checks.append("Actual own pending appeal exposes private empty supplement history and authoritative capability without council controls")
    files=context.request.get(f"{base}/api/applications/{app_id}/files/").json()["items"]
    evidence=next(file for file in files if file["scan_state"]=="clean")
    outsider=context.browser.new_context()
    try:
        outsider.add_cookies([{"name":session_cookie_name,"value":outsider_cookie,"url":base}])
        outsider.request.get(base+"/api/session/")
        other_csrf=next(cookie["value"] for cookie in outsider.cookies() if cookie["name"]=="csrftoken")
        assert outsider.request.get(f"{base}/api/applications/{app_id}/").status==403
        response=outsider.request.post(url,data={"text":"Foreign addition","file_ids":[],"expected_version":row["version"],"idempotency_key":str(uuid.uuid4())},headers={"X-CSRFToken":other_csrf})
        assert response.status==403,response.text()
    finally:outsider.close()
    checks.append("A distinct other applicant cannot read another applicant's supplement history or author additions")
    version=row["version"]
    baseline={"text":"Version-bound supplement","file_ids":[],"expected_version":version,"idempotency_key":str(uuid.uuid4())}
    for payload in [{k:v for k,v in baseline.items() if k!="idempotency_key"},{**baseline,"expected_version":version-1},
        {**baseline,"file_ids":"not-a-list"},{**baseline,"file_ids":[evidence["id"],evidence["id"]]}]:
        response=post(payload);assert response.status==422,response.text()
    assert post({**baseline,"file_ids":[source_file_id]}).status==403
    staff_denied=staff.request.post(url,data=baseline,headers={"X-CSRFToken":staff_csrf});assert staff_denied.status==403
    assert detail().json()["supplements"]==[]
    checks.append("Actual supplement append rejects absent key, stale version, malformed/duplicate evidence, other-application file and staff authorship")
    replaced=evidence
    replacement=context.request.post(base+"/api/files/",multipart={"application_id":app_id,"category":evidence["category"],"attachment_id":evidence["attachment_id"],
        "file":{"name":"supplement-current.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 synthetic current supplement evidence"}},headers={"X-CSRFToken":csrf})
    assert replacement.status==201,replacement.text()
    current_id=replacement.json()["id"]
    assert post({**baseline,"file_ids":[replaced["id"]]}).status==403
    fixture_db(lambda:m.FileTechnicalEvent.objects.create(file_id=current_id,task="scan",result="pending"))
    assert post({**baseline,"file_ids":[current_id]}).status==403
    pending_file=next(file for file in context.request.get(f"{base}/api/applications/{app_id}/files/").json()["items"] if file["id"]==current_id)
    assert not pending_file.get("download_url") and context.request.get(f"{base}/api/files/{current_id}/").status==403
    fixture_db(lambda:m.FileTechnicalEvent.objects.create(file_id=current_id,task="scan",result="clean"))
    evidence=next(file for file in context.request.get(f"{base}/api/applications/{app_id}/files/").json()["items"] if file["id"]==current_id)
    checks.append("Actual replacement invalidates superseded supplement evidence; pending scans deny append/links/bytes and explicit clean event restores current evidence")
    page.get_by_role("button",name="Refresh application status",exact=True).click()
    panel=page.get_by_role("region",name="Additional filing information",exact=True)
    expect(panel.get_by_label("New additional information",exact=True)).to_be_visible()
    content="Own additional evidence <script>retained as text</script>"
    panel.get_by_label("New additional information",exact=True).fill(content)
    panel.get_by_role("checkbox",name=evidence["name"],exact=True).check()
    page.get_by_role("button",name="Back",exact=True).click()
    expect(page.get_by_text("Reloading or leaving will discard your unsaved changes.",exact=True)).to_be_visible()
    page.get_by_role("button",name="Keep editing",exact=True).click()
    assert page.evaluate("(()=>{const e=new Event('beforeunload',{cancelable:true});dispatchEvent(e);return e.defaultPrevented;})()")
    panel.get_by_role("button",name="Review supplement",exact=True).click()
    attempts=[]
    def lost_ack(route):
        attempts.append(route.request.post_data_json)
        actual=route.fetch();assert actual.status==201,actual.text()
        route.fulfill(status=500,json={"error":"synthetic lost acknowledgement after commit"})
    page.route(url,lost_ack)
    panel.get_by_role("button",name="Submit additional information",exact=True).click()
    expect(panel.get_by_text("Submission was not confirmed.",exact=False)).to_be_visible()
    expect(panel.get_by_role("button",name="Submit additional information",exact=True)).to_be_disabled()
    assert len(attempts)==1
    payload=attempts[0];assert payload["text"]==content and payload["file_ids"]==[evidence["id"]] and payload["expected_version"]==version
    assert len(payload["idempotency_key"])==36
    retained=detail().json()["supplements"];assert len(retained)==1
    receipt=retained[0];assert receipt["text"]==content and receipt["idempotency_key"]==payload["idempotency_key"]
    assert receipt["manifest"][0]["id"]==evidence["id"] and len(receipt["manifest"][0]["sha256"])==64
    checks.append("Browser reviews escaped own text/current evidence, guards navigation and freezes version/key; lost HTTP acknowledgement follows one real committed append")
    panel.get_by_role("button",name="Refresh supplement history and evidence",exact=True).click()
    expect(panel.get_by_text("The server received your supplement.",exact=False)).to_be_visible()
    expect(panel.get_by_role("button",name="Clear local entry and start a new supplement",exact=True)).to_be_visible()
    assert len(attempts)==1
    assert panel.get_by_role("link",name="Download supporting original",exact=True).count()>=1
    checks.append("Explicit actual own refresh recovers the matching key/text/file receipt without another POST or invented actor/file metadata")
    page.unroute(url,lost_ack)
    def counts():return (m.AppealSupplement.objects.filter(application_id=app_id).count(),m.Notification.objects.count(),m.Outbox.objects.count())
    once=fixture_db(counts)
    replay=post(payload);assert replay.status==201 and replay.json()["id"]==receipt["id"]
    changed=post({**payload,"text":"Changed with retained key"});assert changed.status==422
    assert fixture_db(counts)==once
    current=detail().json();assert current["answers"]==row["answers"] and current["fee"]==row["fee"]
    checks.append("Exact actual replay returns one supplement receipt without extra alerts; changed-key payload rejects and original formal answers/fee remain unchanged")
    page.get_by_role("button",name="العربية",exact=True).click();page.set_viewport_size({"width":390,"height":1000})
    panel_ar=page.get_by_role("region",name="معلومات إضافية للطلب",exact=True)
    expect(panel_ar.get_by_text(content,exact=True).first).to_be_visible()
    assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    panel_ar.screenshot(path=str(Path(output)/"ar-supplement-receipt-390.png"),caret="initial")
    page.get_by_role("button",name="English",exact=True).click();page.set_viewport_size({"width":1280,"height":1000})
    checks.append("Actual hashed receipt history and recovery render escaped content in Arabic mobile without runtime inline styles or horizontal overflow")
    # Later withdrawal does not remove immutable own history or exact replay recovery.
    withdrawn=context.request.post(f"{base}/api/applications/{app_id}/withdraw/",data={"expected_version":version},headers={"X-CSRFToken":csrf})
    assert withdrawn.status==200,withdrawn.text()
    replay=post(payload);assert replay.status==201 and replay.json()["id"]==receipt["id"]
    closed=detail().json();assert not closed["can_supplement"] and closed["supplements"]==retained
    fresh=post({**payload,"idempotency_key":str(uuid.uuid4())});assert fresh.status==403
    panel.get_by_role("button",name="Refresh supplement history and evidence",exact=True).click()
    expect(panel.get_by_text("This filing is not accepting additional information.",exact=True)).to_be_visible()
    expect(panel.get_by_role("button",name="Submit additional information",exact=True)).to_be_disabled()
    assert fixture_db(lambda:m.AppealSupplement.objects.filter(application_id=app_id).count())==1
    checks.append("After actual pending withdrawal, immutable own history and exact original replay remain readable; fresh additions and browser submit are disabled")
    return checks
