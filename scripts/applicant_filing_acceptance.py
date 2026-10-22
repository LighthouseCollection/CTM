"""Additional real HTTP filing-action scenarios, isolated synthetic records only."""
import json,uuid,os
from pathlib import Path
from playwright.sync_api import expect


def run(browser, base, settings, fixture_db, session_cookie, staff, staff_csrf, errors, output, admin_id):
    from tribunal import models as m
    from django.utils import timezone
    checks=[]
    contexts=[]

    def new_owner(label):
        actor=fixture_db(lambda:m.Account.objects.create_user(email=f"{label}-{uuid.uuid4().hex}@example.test",email_verified=True))
        ctx=browser.new_context(viewport={"width":1280,"height":1000});contexts.append(ctx)
        cookie=fixture_db(lambda:session_cookie(actor))
        ctx.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookie,"url":base}])
        ctx.request.get(base+"/api/session/")
        csrf=next(c["value"] for c in ctx.cookies() if c["name"]=="csrftoken")
        return actor,ctx,csrf

    def post(ctx,csrf,path,data):
        return ctx.request.post(base+path,data=data,headers={"X-CSRFToken":csrf})

    def private_denial(actual,missing):
        if os.environ.get("CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT")=="hidden404":
            assert actual.status==missing.status==404,(actual.status,missing.status)
            assert actual.json()==missing.json(),(actual.text(),missing.text())
        else:assert actual.status==403,actual.text()

    def start(ctx,csrf,label):
        response=post(ctx,csrf,"/api/applications/",{"kind":"petition"})
        assert response.status==201,response.text()
        app_id=response.json()["id"]
        answers={"first_name":label,"last_name":"SyntheticLifecycle","birth_date":"1986-05-06","gender":"F",
            "marriage_date":"2011-02-03","grounds":["abuse"],"statement":"Synthetic lifecycle statement"}
        saved=post(ctx,csrf,f"/api/applications/{app_id}/",{"answers":answers,"expected_version":0})
        assert saved.status==201,saved.text()
        return app_id

    def detail(ctx,app_id):return ctx.request.get(f"{base}/api/applications/{app_id}/").json()

    def open_editor(ctx):
        page=ctx.new_page();page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(base,wait_until="networkidle")
        page.get_by_role("button",name="My application",exact=True).click()
        page.get_by_role("button",name="Open application",exact=True).click()
        expect(page.get_by_role("heading",name="Application actions",exact=True)).to_be_visible()
        page.wait_for_load_state("networkidle")
        return page

    def open_ready_review(page,ctx,app_id,label):
        detail_url=f"{base}/api/applications/{app_id}/"
        files_url=f"{base}/api/applications/{app_id}/files/"
        trace={"application_id":app_id,"label":label,"responses":[]}
        def summarize_files(payload):
            required={(row["category"],row.get("context") or "") for row in payload.get("requirements",[]) if row.get("required")}
            clean={(row["category"],row.get("context") or "") for row in payload.get("items",[]) if row.get("scan_state")=="clean"}
            return {"required_keys":sorted(required),"clean_keys":sorted(clean),"requirements_clean":required<=clean}
        def record(response):
            if response.request.method=="GET" and response.url in {detail_url,files_url}:
                trace["responses"].append({"url":response.url,"status":response.status})
        page.on("response",record)
        try:
            authoritative=ctx.request.get(detail_url);authoritative_files=ctx.request.get(files_url)
            assert authoritative.status==authoritative_files.status==200
            authoritative_payload=authoritative.json();authoritative_file_payload=authoritative_files.json()
            trace["authoritative"]={"status":authoritative_payload.get("status"),"version":authoritative_payload.get("version"),
                "fee_status":(authoritative_payload.get("fee") or {}).get("status"),"can_submit":authoritative_payload.get("can_submit"),
                **summarize_files(authoritative_file_payload)}
            assert authoritative_payload["status"]=="draft" and authoritative_payload["can_submit"] is True
            assert trace["authoritative"]["requirements_clean"]
            with page.expect_response(lambda r:r.url==detail_url and r.request.method=="GET") as detail_received, \
                    page.expect_response(lambda r:r.url==files_url and r.request.method=="GET") as files_received:
                page.get_by_role("button",name="Refresh application status",exact=True).click()
            refreshed=detail_received.value;refreshed_files=files_received.value
            assert refreshed.status==refreshed_files.status==200
            refreshed_payload=refreshed.json();refreshed_file_payload=refreshed_files.json()
            trace["refreshed"]={"status":refreshed_payload.get("status"),"version":refreshed_payload.get("version"),
                "fee_status":(refreshed_payload.get("fee") or {}).get("status"),"can_submit":refreshed_payload.get("can_submit"),
                **summarize_files(refreshed_file_payload)}
            assert refreshed_payload["status"]=="draft" and refreshed_payload["can_submit"] is True
            assert trace["refreshed"]["requirements_clean"]
            review=page.get_by_role("button",name="Review answers",exact=True)
            expect(review).to_be_enabled()
            review.click()
            expect(page.get_by_text("Review your answers. Submission and payment are separate steps.",exact=True)).to_be_visible()
            declaration=page.get_by_label("I have read and accept this declaration.",exact=True)
            expect(declaration).to_be_enabled()
            return trace
        except Exception:
            artifact=Path(output);artifact.mkdir(parents=True,exist_ok=True)
            trace["failure_state"]={"server_application":detail(ctx,app_id),
                "server_files":ctx.request.get(files_url).json(),"url":page.url,
                "buttons":page.get_by_role("button").all_text_contents(),
                "review_notice":page.get_by_text("Review your answers. Submission and payment are separate steps.",exact=True).count(),
                "declaration_count":page.get_by_label("I have read and accept this declaration.",exact=True).count(),
                "declaration_enabled":page.get_by_label("I have read and accept this declaration.",exact=True).count()==1 and
                    page.get_by_label("I have read and accept this declaration.",exact=True).is_enabled(),
                "body":page.locator("body").inner_text(),"viewport":page.viewport_size}
            (artifact/f"{label}-review-readiness-failure.json").write_text(json.dumps(trace,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            (artifact/f"{label}-review-readiness-failure.html").write_text(page.content(),encoding="utf-8")
            page.screenshot(path=str(artifact/f"{label}-review-readiness-failure.png"),full_page=True,caret="initial")
            raise
        finally:page.remove_listener("response",record)

    try:
        actor,ctx,csrf=new_owner("draft-action")
        app_id=start(ctx,csrf,"DraftAction")
        other,foreign,foreign_csrf=new_owner("foreign-action")
        row=detail(ctx,app_id)
        assert row["can_delete_draft"] and not row["can_withdraw"] and row["version"]==1
        for payload in [{},{"expected_version":0},{"expected_version":True},{"expected_version":"1"}]:
            response=post(ctx,csrf,f"/api/applications/{app_id}/delete-draft/",payload)
            assert response.status==422,response.text()
        foreign_delete_payload={"expected_version":1}
        private_denial(post(foreign,foreign_csrf,f"/api/applications/{app_id}/delete-draft/",foreign_delete_payload),
            post(foreign,foreign_csrf,f"/api/applications/{uuid.uuid4()}/delete-draft/",foreign_delete_payload))
        assert detail(ctx,app_id)==row
        checks.append("Real own draft capability rejects missing/malformed/stale versions and foreign-owner deletion without mutation")
        original_upload=ctx.request.post(base+"/api/files/",multipart={"application_id":app_id,"category":"CMC",
            "file":{"name":"delete-original.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 synthetic original for deletion"}},headers={"X-CSRFToken":csrf})
        assert original_upload.status==201,original_upload.text()
        original_file=original_upload.json()["id"]
        assert ctx.request.get(f"{base}/api/files/{original_file}/").status==200
        page=open_editor(ctx)
        page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
        expect(page.get_by_role("button",name="Confirm action",exact=True)).to_be_enabled()
        page.get_by_role("button",name="Cancel",exact=True).click()
        assert detail(ctx,app_id)["status"]=="draft"
        # Advance the authoritative answer version behind the already-open editor.
        changed=post(ctx,csrf,f"/api/applications/{app_id}/",{"expected_version":1,"answers":{**row["answers"],"statement":"New saved version"}})
        assert changed.status==201,changed.text()
        page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
        expect(page.get_by_role("button",name="Confirm action",exact=True)).to_be_enabled()
        with page.expect_response(lambda r:r.url==f"{base}/api/applications/{app_id}/delete-draft/") as result:
            page.get_by_role("button",name="Confirm action",exact=True).click()
        assert result.value.status==422 and result.value.request.post_data_json=={"expected_version":1}
        expect(page.get_by_role("button",name="Confirm action",exact=True)).to_be_disabled()
        assert detail(ctx,app_id)["status"]=="draft"
        transition={}
        try:
            with page.expect_response(lambda r:r.url==f"{base}/api/applications/{app_id}/" and r.request.method=="GET") as refreshed:
                page.get_by_role("button",name="Refresh application",exact=True).click()
            refreshed_row=refreshed.value
            assert refreshed_row.status==200,refreshed_row.text()
            refreshed_body=refreshed_row.json()
            assert refreshed_body["id"]==app_id and refreshed_body["status"]=="draft" and refreshed_body["version"]==2
            assert refreshed_body["can_delete_draft"] is True
            transition["authoritative_refresh"]={"status":refreshed_row.status,"application_status":refreshed_body["status"],
                "version":refreshed_body["version"],"can_delete_draft":refreshed_body["can_delete_draft"]}
            expect(page.get_by_role("button",name="Delete unsubmitted draft",exact=True)).to_be_enabled()
            checks.append("Browser cancel sends no deletion; a concurrent saved revision rejects stale confirmation and requires authoritative refresh")
            page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
            expect(page.get_by_role("button",name="Confirm action",exact=True)).to_be_enabled()
            transition["initial_english_dialog"]=True
            language_delete_requests=[]
            page.on("request",lambda request:language_delete_requests.append(request.post_data_json)
                if request.url==f"{base}/api/applications/{app_id}/delete-draft/" and request.method=="POST" else None)
            with page.expect_response(lambda r:r.url==base+"/api/account/settings/" and r.request.method=="POST") as arabic_language:
                page.get_by_role("button",name="العربية",exact=True).click()
            assert arabic_language.value.status==200,arabic_language.value.text()
            transition["arabic_language_status"]=arabic_language.value.status
            page.set_viewport_size({"width":390,"height":1000})
            expect(page.get_by_role("button",name="حذف المسودة غير المقدّمة",exact=True)).to_be_enabled()
            expect(page.get_by_role("button",name="تأكيد الإجراء",exact=True)).to_have_count(0)
            expect(page.get_by_role("button",name="إلغاء",exact=True)).to_have_count(0)
            assert language_delete_requests==[]
            assert detail(ctx,app_id)==refreshed_body
            transition["language_change_cancelled_confirmation"]={"delete_requests":0,"application_unchanged":True}
            page.get_by_role("button",name="حذف المسودة غير المقدّمة",exact=True).click()
            expect(page.get_by_role("button",name="تأكيد الإجراء",exact=True)).to_be_enabled()
            transition["reopened_arabic_dialog"]=True
            assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            with page.expect_response(lambda r:r.url==f"{base}/api/applications/{app_id}/delete-draft/") as result:
                page.get_by_role("button",name="تأكيد الإجراء",exact=True).click()
            assert result.value.status==200 and result.value.request.post_data_json=={"expected_version":2}
            assert language_delete_requests==[{"expected_version":2}]
            transition["delete"]={"status":result.value.status,"payload":result.value.request.post_data_json}
            with page.expect_response(lambda r:r.url==f"{base}/api/applications/{app_id}/" and r.request.method=="GET") as deleted_refresh:
                page.get_by_role("button",name="تحديث الطلب",exact=True).click()
            deleted_body=deleted_refresh.value.json()
            assert deleted_refresh.value.status==200 and deleted_body["id"]==app_id and deleted_body["status"]=="deleted"
            assert deleted_body["can_delete_draft"] is False
            expect(page.get_by_text("حالة الطلب: محذوف",exact=True)).to_be_visible()
            transition["deleted_refresh"]={"status":deleted_refresh.value.status,"application_status":deleted_body["status"],
                "can_delete_draft":deleted_body["can_delete_draft"],"ui_status_visible":True}
            expect(page.get_by_role("button",name="حذف المسودة غير المقدّمة",exact=True)).to_have_count(0)
            with page.expect_response(lambda r:r.url==base+"/api/account/settings/" and r.request.method=="POST") as english_language:
                page.get_by_role("button",name="English",exact=True).click()
            assert english_language.value.status==200,english_language.value.text()
            expect(page.get_by_text("Application status: Deleted",exact=True)).to_be_visible()
            expect(page.get_by_role("button",name="Delete unsubmitted draft",exact=True)).to_have_count(0)
            transition["english_deleted_status"]={"language_status":english_language.value.status,"ui_status_visible":True}
            artifact=Path(output);artifact.mkdir(parents=True,exist_ok=True)
            (artifact/"draft-delete-confirmation-state.json").write_text(json.dumps(transition,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        except Exception:
            artifact=Path(output);artifact.mkdir(parents=True,exist_ok=True)
            diagnostic={"application_id":app_id,"transitions":transition,"server_detail":detail(ctx,app_id),"url":page.url,
                "buttons":page.get_by_role("button").all_text_contents(),"body":page.locator("body").inner_text(),
                "viewport":page.viewport_size}
            (artifact/"draft-delete-confirmation-failure.json").write_text(json.dumps(diagnostic,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            page.screenshot(path=str(artifact/"draft-delete-confirmation-failure.png"),full_page=True,caret="initial")
            raise
        assert detail(ctx,app_id)["status"]=="deleted"
        assert fixture_db(lambda:m.AnswerRevision.objects.filter(application_id=app_id).count())==0
        assert fixture_db(lambda:m.FileVersion.objects.filter(pk=original_file).count())==0
        assert ctx.request.get(f"{base}/api/files/{original_file}/").status in [403,404]
        checks.append("EN/AR mobile confirmed deletion uses current version; authoritative deleted state removes controls and draft revisions")
        # Lost acknowledgement after a real committed deletion must never retry automatically.
        lost_actor,lost,lost_csrf=new_owner("lost-delete")
        lost_id=start(lost,lost_csrf,"LostDelete")
        lost_page=open_editor(lost);attempts=[]
        lost_trace={"application_id":lost_id,"before":detail(lost,lost_id)}
        def lose_ack(route):
            attempts.append(route.request.post_data_json)
            actual=route.fetch();assert actual.status==200
            route.fulfill(status=500,json={"error":"synthetic lost acknowledgement"})
        lost_page.route(f"{base}/api/applications/{lost_id}/delete-draft/",lose_ack)
        try:
            delete=lost_page.get_by_role("button",name="Delete unsubmitted draft",exact=True)
            expect(delete).to_be_enabled();delete.click()
            confirm=lost_page.get_by_role("button",name="Confirm action",exact=True)
            expect(confirm).to_be_enabled()
            with lost_page.expect_response(lambda r:r.url==f"{base}/api/applications/{lost_id}/delete-draft/" and r.request.method=="POST") as deletion:
                confirm.click()
            lost_trace["delete_response"]={"status":deletion.value.status,"payload":deletion.value.request.post_data_json,
                "body":deletion.value.text()[:4000]}
            expect(lost_page.get_by_text("The result is uncertain.",exact=False)).to_be_visible()
            expect(lost_page.get_by_role("button",name="Confirm action",exact=True)).to_be_disabled()
            with lost_page.expect_response(lambda r:r.url==f"{base}/api/applications/{lost_id}/" and r.request.method=="GET") as refreshed:
                lost_page.get_by_role("button",name="Refresh application",exact=True).click()
            refreshed_payload=refreshed.value.json()
            lost_trace["refresh"]={"status":refreshed.value.status,"application":refreshed_payload}
            assert refreshed.value.status==200 and refreshed_payload["status"]=="deleted"
            expect(lost_page.get_by_text("Application status: Deleted",exact=True)).to_be_visible()
            lost_trace["refresh"]["ui_status_visible"]=True
            expect(lost_page.get_by_role("button",name="Delete unsubmitted draft",exact=True)).to_have_count(0)
            assert len(attempts)==1 and detail(lost,lost_id)["status"]=="deleted"
        except Exception:
            artifact=Path(output);artifact.mkdir(parents=True,exist_ok=True)
            lost_trace["failure_state"]={"server_application":detail(lost,lost_id),"attempts":attempts,"url":lost_page.url,
                "buttons":lost_page.get_by_role("button").all_text_contents(),"alerts":lost_page.get_by_role("alert").all_text_contents(),
                "body":lost_page.locator("body").inner_text(),"viewport":lost_page.viewport_size}
            (artifact/"lost-delete-recovery-failure.json").write_text(json.dumps(lost_trace,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            (artifact/"lost-delete-recovery-failure.html").write_text(lost_page.content(),encoding="utf-8")
            lost_page.screenshot(path=str(artifact/"lost-delete-recovery-failure.png"),full_page=True,caret="initial")
            raise
        checks.append("Lost acknowledgement after real deletion locks repeats; explicit own refresh recovers deleted state without a second mutation")
        # Both filings use actual save/upload/waiver/submit routes. Only verified-account
        # onboarding/linking is explicit fixture setup, outside this applicant journey.
        first,one,one_csrf=new_owner("joint-first")
        first_id=start(one,one_csrf,"JointFirst")
        listing=one.request.get(f"{base}/api/applications/{first_id}/files/").json()
        for requirement in listing["requirements"]:
            if not requirement["required"]:continue
            category=requirement["category"];image=category=="PHOTO"
            response=one.request.post(base+"/api/files/",multipart={"application_id":first_id,"category":category,
                "file":{"name":"synthetic.png" if image else "synthetic.pdf","mimeType":"image/png" if image else "application/pdf",
                    "buffer":b"\x89PNG\r\n\x1a\nsynthetic" if image else b"%PDF-1.7 synthetic lifecycle"}},headers={"X-CSRFToken":one_csrf})
            assert response.status==201,response.text()
        assert post(staff,staff_csrf,f"/api/applications/{first_id}/waiver/",{}).status==201
        ready=detail(one,first_id)
        submitted=post(one,one_csrf,f"/api/applications/{first_id}/submit/",{"expected_version":ready["version"],
            "idempotency_key":str(uuid.uuid4()),"attestation":{"accepted":True,"name":"Synthetic JointFirst"}})
        assert submitted.status==201,submitted.text()
        assert post(staff,staff_csrf,f"/api/applications/{first_id}/review/",{"result":"reject","instructions":"Synthetic lifecycle return"}).status==201
        second,two,two_csrf=new_owner("joint-second")
        def linked_second_party_fixture():
            from tribunal.services.identity import link_party
            original=m.Application.objects.get(pk=first_id)
            administrator=m.Account.objects.get(pk=admin_id)
            party=link_party(administrator,original.case,second)
            assert party.account_id==second.pk and party.person_id==second.person_id and party.pk!=original.party_id
            return str(original.case_id)
        joint_case=fixture_db(linked_second_party_fixture)
        if os.environ.get("CTM_APPLICANT_LINKED_ENTRY")=="true":
            entry=two.new_page();entry.on("pageerror",lambda error:errors.append(str(error)))
            entry.goto(base,wait_until="networkidle")
            number=fixture_db(lambda:m.Case.objects.get(pk=joint_case).number)
            entry.get_by_text(number,exact=True).click()
            assert entry.get_by_role("button",name="Start or resume appeal",exact=True).count()==0
            with entry.expect_response(lambda r:r.url==base+"/api/applications/" and r.request.method=="POST") as received:
                entry.get_by_role("button",name="Start or resume my petition",exact=True).click()
            created=received.value
        else:
            created=post(two,two_csrf,"/api/applications/",{"kind":"petition","case_id":joint_case})
        assert created.status==201,created.text()
        second_id=created.json()["id"]
        second_answers={"first_name":"JointSecond","last_name":"SyntheticLifecycle","birth_date":"1987-06-07","gender":"M",
            "marriage_date":"2011-02-03","grounds":["abuse"],"statement":"Own second applicant statement, independently retained"}
        saved=post(two,two_csrf,f"/api/applications/{second_id}/",{"answers":second_answers,"expected_version":0})
        assert saved.status==201,saved.text()
        private_denial(one.request.get(f"{base}/api/applications/{second_id}/"),one.request.get(f"{base}/api/applications/{uuid.uuid4()}/"))
        private_denial(two.request.get(f"{base}/api/applications/{first_id}/"),two.request.get(f"{base}/api/applications/{uuid.uuid4()}/"))
        listing=two.request.get(f"{base}/api/applications/{second_id}/files/").json()
        for requirement in listing["requirements"]:
            if not requirement["required"]:continue
            category=requirement["category"];image=category=="PHOTO"
            received=two.request.post(base+"/api/files/",multipart={"application_id":second_id,"category":category,
                "file":{"name":"second-photo.png" if image else "second-document.pdf","mimeType":"image/png" if image else "application/pdf",
                    "buffer":b"\x89PNG\r\n\x1a\nsynthetic second photo" if image else b"%PDF-1.7 synthetic second applicant document"}},headers={"X-CSRFToken":two_csrf})
            assert received.status==201,received.text()
        assert detail(two,second_id)["fee"]["status"]=="due"
        assert post(staff,staff_csrf,f"/api/applications/{second_id}/waiver/",{}).status==201
        second_page=open_editor(two)
        open_ready_review(second_page,two,second_id,"linked-second")
        second_page.get_by_label("I have read and accept this declaration.",exact=True).check()
        second_page.get_by_label("Your full name",exact=False).fill("Synthetic JointSecond")
        with second_page.expect_response(lambda r:r.url==f"{base}/api/applications/{second_id}/submit/" and r.request.method=="POST") as submitted:
            second_page.get_by_role("button",name="Submit application",exact=True).click()
        assert submitted.value.status==201,submitted.value.text()
        assert submitted.value.request.post_data_json["attestation"]=={"accepted":True,"name":"Synthetic JointSecond"}
        second_saved=detail(two,second_id)
        assert second_saved["status"]=="submitted" and second_saved["case_id"]==joint_case
        assert second_saved["answers"]==second_answers
        assert detail(one,first_id)["answers"]!=second_answers
        private_denial(one.request.get(f"{base}/api/applications/{second_id}/history/"),one.request.get(f"{base}/api/applications/{uuid.uuid4()}/history/"))
        private_denial(two.request.get(f"{base}/api/applications/{first_id}/history/"),two.request.get(f"{base}/api/applications/{uuid.uuid4()}/history/"))
        checks.append("Linked second applicant actually starts/saves/uploads/obtains separate authorized waiver and submits through browser with own declaration; both own histories stay private")
        original=detail(one,first_id);before_history=one.request.get(f"{base}/api/applications/{first_id}/history/").json()
        before_notifications=fixture_db(lambda:m.Notification.objects.filter(recipient=second).count())
        assert original["can_withdraw"] and not original["can_delete_draft"]
        assert post(one,one_csrf,f"/api/applications/{first_id}/delete-draft/",{"expected_version":original["version"]}).status==422
        foreign_withdraw_payload={"expected_version":original["version"]}
        private_denial(post(two,two_csrf,f"/api/applications/{first_id}/withdraw/",foreign_withdraw_payload),
            post(two,two_csrf,f"/api/applications/{uuid.uuid4()}/withdraw/",foreign_withdraw_payload))
        assert detail(one,first_id)==original
        for payload in [{},{"expected_version":0}]:assert post(one,one_csrf,f"/api/applications/{first_id}/withdraw/",payload).status==422
        first_page=open_editor(one)
        assert first_page.get_by_role("button",name="Delete unsubmitted draft",exact=True).count()==0
        withdrawal_trace={"application_id":first_id,"before":original,
            "expected_payload":{"expected_version":original["version"]}}
        try:
            first_page.get_by_role("button",name="Withdraw my filing",exact=True).click()
            expect(first_page.get_by_role("button",name="Confirm action",exact=True)).to_be_enabled()
            with first_page.expect_response(lambda r:r.url==f"{base}/api/applications/{first_id}/withdraw/") as result:
                first_page.get_by_role("button",name="Confirm action",exact=True).click()
            withdrawal_response=result.value
            withdrawal_trace["response"]={"status":withdrawal_response.status,
                "payload":withdrawal_response.request.post_data_json,
                "content_type":withdrawal_response.headers.get("content-type"),
                "body":withdrawal_response.text()[:4000]}
            withdrawal_trace["after_response"]=detail(one,first_id)
            assert withdrawal_response.status==200 and withdrawal_response.request.post_data_json==withdrawal_trace["expected_payload"]
            with first_page.expect_response(lambda r:r.url==f"{base}/api/applications/{first_id}/" and r.request.method=="GET") as refreshed:
                first_page.get_by_role("button",name="Refresh application status",exact=True).click()
            refreshed_response=refreshed.value;refreshed_payload=refreshed_response.json()
            withdrawal_trace["refresh"]={"status":refreshed_response.status,"application":refreshed_payload}
            assert refreshed_response.status==200 and refreshed_payload["status"]=="withdrawn"
            assert refreshed_payload["version"]==original["version"] and refreshed_payload["can_withdraw"] is False
            expect(first_page.get_by_text("Application status: Withdrawn",exact=True)).to_be_visible()
            expect(first_page.get_by_role("button",name="Withdraw my filing",exact=True)).to_have_count(0)
        except Exception:
            artifact=Path(output);artifact.mkdir(parents=True,exist_ok=True)
            withdrawal_trace["failure_state"]={"server_application":detail(one,first_id),"url":first_page.url,
                "buttons":first_page.get_by_role("button").all_text_contents(),
                "confirm_count":first_page.get_by_role("button",name="Confirm action",exact=True).count(),
                "alerts":first_page.get_by_role("alert").all_text_contents(),
                "body":first_page.locator("body").inner_text(),"viewport":first_page.viewport_size}
            (artifact/"returned-withdrawal-failure.json").write_text(json.dumps(withdrawal_trace,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            (artifact/"returned-withdrawal-failure.html").write_text(first_page.content(),encoding="utf-8")
            first_page.screenshot(path=str(artifact/"returned-withdrawal-failure.png"),full_page=True,caret="initial")
            raise
        assert detail(one,first_id)==refreshed_payload
        assert one.request.get(f"{base}/api/applications/{first_id}/history/").json()==before_history
        assert detail(one,first_id)["fee"]==original["fee"]
        checks.append("Actual returned-filing withdrawal is owner/version bound; browser hides draft deletion, preserves fee/history and removes action after refresh")
        def joint_state():
            app=m.Application.objects.select_related("case","party").get(pk=first_id)
            return {"case":app.case.status,"withdrawn":app.party.withdrawn_at is not None,
                "second":m.Application.objects.get(pk=second_id).status,"notifications":m.Notification.objects.filter(recipient=second).count()}
        state=fixture_db(joint_state)
        assert state=={"case":"open","withdrawn":True,"second":"submitted","notifications":before_notifications}
        last=detail(two,second_id)
        assert post(two,two_csrf,f"/api/applications/{second_id}/withdraw/",{"expected_version":last["version"]}).status==200
        assert fixture_db(joint_state)["case"]=="closed"
        checks.append("Two actually submitted filings verify first withdrawal preserves joint case and other filing without spouse notification; last withdrawal closes case (account linking remains fixture)")
        if os.environ.get("CTM_APPLICANT_LINKED_ENTRY")=="true":
            closed_actor,closed_ctx,closed_csrf=new_owner("closed-never-filer")
            def closed_case_fixture():
                # Explicit imported/closed case and verified link; no claimed decree/identity acceptance.
                from copy import deepcopy
                from datetime import date
                old=m.QuestionnaireVersion.objects.filter(purpose="petition",published=True).order_by("-number").first()
                definition=deepcopy(old.definition)
                definition["fields"].append({"code":"new_information","type":"textarea","label_en":"Synthetic closed-case new information","label_ar":"معلومات جديدة تجريبية للقضية المغلقة"})
                m.QuestionnaireVersion.objects.create(purpose="petition",number=old.number+1,published=True,definition=definition,
                    declaration_en=old.declaration_en,declaration_ar=old.declaration_ar)
                case=m.Case.objects.create(number="SYNTH-CLOSED-"+uuid.uuid4().hex[:8],status="closed",marriage_date=date(2011,2,3),closed_at=timezone.now())
                m.Proceeding.objects.create(case=case,status="closed")
                m.Party.objects.create(case=case,slot="B",account=closed_actor,person=closed_actor.person,name="Synthetic closed-case spouse")
                return str(case.pk),case.number
            closed_case,closed_number=fixture_db(closed_case_fixture)
            cp=closed_ctx.new_page();cp.on("pageerror",lambda error:errors.append(str(error)))
            cp.goto(base,wait_until="networkidle");cp.get_by_role("button",name="Past cases",exact=True).click()
            cp.get_by_text(closed_number,exact=True).click()
            with cp.expect_response(lambda r:r.url==base+"/api/applications/" and r.request.method=="POST") as opened:
                cp.get_by_role("button",name="Start or resume my petition",exact=True).click()
            assert opened.value.status==201,opened.value.text()
            closed_id=opened.value.json()["id"]
            answers={"first_name":"ClosedFirst","last_name":"SyntheticLifecycle","birth_date":"1988-07-08","gender":"F",
                "marriage_date":"2011-02-03","grounds":["abuse"],"statement":"Synthetic first closed-case petition",
                "new_information":"Own new facts for council consideration"}
            assert post(closed_ctx,closed_csrf,f"/api/applications/{closed_id}/",{"answers":answers,"expected_version":0}).status==201
            listing=closed_ctx.request.get(f"{base}/api/applications/{closed_id}/files/").json()
            for requirement in listing["requirements"]:
                if not requirement["required"]:continue
                category=requirement["category"];image=category=="PHOTO"
                received=closed_ctx.request.post(base+"/api/files/",multipart={"application_id":closed_id,"category":category,
                    "file":{"name":"closed-photo.png" if image else "closed-copy.pdf","mimeType":"image/png" if image else "application/pdf",
                        "buffer":b"\x89PNG\r\n\x1a\nsynthetic closed photo" if image else b"%PDF-1.7 synthetic closed original"}},headers={"X-CSRFToken":closed_csrf})
                assert received.status==201,received.text()
            assert post(staff,staff_csrf,f"/api/applications/{closed_id}/waiver/",{}).status==201
            cp.get_by_role("button",name="Reload saved answers",exact=True).click()
            expect(cp.get_by_role("textbox",name="Synthetic closed-case new information",exact=False)).to_have_value(answers["new_information"])
            open_ready_review(cp,closed_ctx,closed_id,"closed-case-intake")
            cp.get_by_label("I have read and accept this declaration.",exact=True).check()
            cp.get_by_label("Your full name",exact=False).fill("Synthetic ClosedFirst")
            with cp.expect_response(lambda r:r.url==f"{base}/api/applications/{closed_id}/submit/" and r.request.method=="POST") as submitted:
                cp.get_by_role("button",name="Submit application",exact=True).click()
            assert submitted.value.status==201,submitted.value.text()
            row=detail(closed_ctx,closed_id)
            assert row["origin"]=="closed_case_intake" and row["status"]=="submitted" and row["case_id"]==closed_case
            assert fixture_db(lambda:m.Case.objects.get(pk=closed_case).status)=="closed"
            assert fixture_db(lambda:m.Proceeding.objects.filter(case_id=closed_case).count())==1
            private_denial(one.request.get(f"{base}/api/applications/{closed_id}/history/"),one.request.get(f"{base}/api/applications/{uuid.uuid4()}/history/"))
            checks.append("Linked never-filer starts first petition from closed case, saves new facts/uploads/separate waiver and submits in browser without reopening; closed record/link/content are explicit fixtures")
        # Explicit pending appeal state, independent of decree/signature issuance acceptance.
        def appeal_fixture():
            parent=m.Application.objects.get(pk=first_id)
            form=m.QuestionnaireVersion.objects.filter(purpose="appeal",published=True).first()
            app=m.Application.objects.create(owner=first,case=parent.case,kind="appeal",status="submitted",submitted_at=timezone.now(),current_version=1,questionnaire=form)
            m.AnswerRevision.objects.create(application=app,number=1,answers={"new_information":"Synthetic retained appeal"},questionnaire=form,actor=first)
            m.FeeObligation.objects.create(application=app,status="waived")
            return str(app.pk)
        appeal_id=fixture_db(appeal_fixture)
        row=detail(one,appeal_id)
        assert row["can_withdraw"] and not row["can_delete_draft"]
        assert post(staff,staff_csrf,f"/api/applications/{appeal_id}/withdraw/",{"expected_version":1}).status==403
        private_denial(post(two,two_csrf,f"/api/applications/{appeal_id}/withdraw/",{"expected_version":1}),
            post(two,two_csrf,f"/api/applications/{uuid.uuid4()}/withdraw/",{"expected_version":1}))
        assert detail(one,appeal_id)==row
        response=post(one,one_csrf,f"/api/applications/{appeal_id}/withdraw/",{"expected_version":1})
        assert response.status==200,response.text()
        assert detail(one,appeal_id)["status"]=="withdrawn" and detail(one,appeal_id)["fee"]==row["fee"]
        assert fixture_db(lambda:m.AnswerRevision.objects.filter(application_id=appeal_id).count())==1
        assert fixture_db(joint_state)["case"]=="closed"
        checks.append("Pending appeal fixture withdrawal remains owner-only before disposition, preserving fee/revision and closed case; admin and other applicant denied")
        return checks
    finally:
        for ctx in contexts:ctx.close()
