"""Additional real HTTP filing-action scenarios, isolated synthetic records only."""
import uuid
from playwright.sync_api import expect


def run(browser, base, settings, fixture_db, session_cookie, staff, staff_csrf, errors):
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
        page.get_by_role("navigation").get_by_role("button",name="My application",exact=True).click()
        page.get_by_role("button",name="Open application",exact=True).click()
        expect(page.get_by_role("heading",name="Application actions",exact=True)).to_be_visible()
        return page

    try:
        actor,ctx,csrf=new_owner("draft-action")
        app_id=start(ctx,csrf,"DraftAction")
        other,foreign,foreign_csrf=new_owner("foreign-action")
        row=detail(ctx,app_id)
        assert row["can_delete_draft"] and not row["can_withdraw"] and row["version"]==1
        for payload in [{},{"expected_version":0},{"expected_version":True},{"expected_version":"1"}]:
            response=post(ctx,csrf,f"/api/applications/{app_id}/delete-draft/",payload)
            assert response.status==422,response.text()
        assert post(foreign,foreign_csrf,f"/api/applications/{app_id}/delete-draft/",{"expected_version":1}).status==403
        assert detail(ctx,app_id)["status"]=="draft"
        checks.append("Real own draft capability rejects missing/malformed/stale versions and foreign-owner deletion without mutation")
        original_upload=ctx.request.post(base+"/api/files/",multipart={"application_id":app_id,"category":"CMC",
            "file":{"name":"delete-original.pdf","mimeType":"application/pdf","buffer":b"%PDF-1.7 synthetic original for deletion"}},headers={"X-CSRFToken":csrf})
        assert original_upload.status==201,original_upload.text()
        original_file=original_upload.json()["id"]
        assert ctx.request.get(f"{base}/api/files/{original_file}/").status==200
        page=open_editor(ctx)
        page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
        page.get_by_role("button",name="Cancel",exact=True).click()
        assert detail(ctx,app_id)["status"]=="draft"
        # Advance the authoritative answer version behind the already-open editor.
        changed=post(ctx,csrf,f"/api/applications/{app_id}/",{"expected_version":1,"answers":{**row["answers"],"statement":"New saved version"}})
        assert changed.status==201,changed.text()
        page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
        with page.expect_response(lambda r:r.url==f"{base}/api/applications/{app_id}/delete-draft/") as result:
            page.get_by_role("button",name="Confirm action",exact=True).click()
        assert result.value.status==422 and result.value.request.post_data_json=={"expected_version":1}
        expect(page.get_by_role("button",name="Confirm action",exact=True)).to_be_disabled()
        assert detail(ctx,app_id)["status"]=="draft"
        page.get_by_role("button",name="Refresh application",exact=True).click()
        expect(page.get_by_role("button",name="Delete unsubmitted draft",exact=True)).to_be_enabled()
        checks.append("Browser cancel sends no deletion; a concurrent saved revision rejects stale confirmation and requires authoritative refresh")
        page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
        page.get_by_role("button",name="العربية",exact=True).click();page.set_viewport_size({"width":390,"height":1000})
        expect(page.get_by_role("button",name="تأكيد الإجراء",exact=True)).to_be_visible()
        assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.get_by_role("button",name="English",exact=True).click()
        with page.expect_response(lambda r:r.url==f"{base}/api/applications/{app_id}/delete-draft/") as result:
            page.get_by_role("button",name="Confirm action",exact=True).click()
        assert result.value.status==200 and result.value.request.post_data_json=={"expected_version":2}
        page.get_by_role("button",name="Refresh application",exact=True).click()
        expect(page.get_by_role("button",name="Delete unsubmitted draft",exact=True)).to_have_count(0)
        assert detail(ctx,app_id)["status"]=="deleted"
        assert fixture_db(lambda:m.AnswerRevision.objects.filter(application_id=app_id).count())==0
        assert fixture_db(lambda:m.FileVersion.objects.filter(pk=original_file).count())==0
        assert ctx.request.get(f"{base}/api/files/{original_file}/").status in [403,404]
        checks.append("EN/AR mobile confirmed deletion uses current version; authoritative deleted state removes controls and draft revisions")
        # Lost acknowledgement after a real committed deletion must never retry automatically.
        lost_actor,lost,lost_csrf=new_owner("lost-delete")
        lost_id=start(lost,lost_csrf,"LostDelete")
        lost_page=open_editor(lost);attempts=[]
        def lose_ack(route):
            attempts.append(route.request.post_data_json)
            actual=route.fetch();assert actual.status==200
            route.fulfill(status=500,json={"error":"synthetic lost acknowledgement"})
        lost_page.route(f"{base}/api/applications/{lost_id}/delete-draft/",lose_ack)
        lost_page.get_by_role("button",name="Delete unsubmitted draft",exact=True).click()
        lost_page.get_by_role("button",name="Confirm action",exact=True).click()
        expect(lost_page.get_by_text("The result is uncertain.",exact=False)).to_be_visible()
        expect(lost_page.get_by_role("button",name="Confirm action",exact=True)).to_be_disabled()
        lost_page.get_by_role("button",name="Refresh application",exact=True).click()
        expect(lost_page.get_by_role("button",name="Delete unsubmitted draft",exact=True)).to_have_count(0)
        assert len(attempts)==1 and detail(lost,lost_id)["status"]=="deleted"
        checks.append("Lost acknowledgement after real deletion locks repeats; explicit own refresh recovers deleted state without a second mutation")
        # First filing uses actual uploads, waiver and submission. A second participating
        # filing is explicit synthetic state to isolate joint-withdrawal rules.
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
        def second_filing_fixture():
            original=m.Application.objects.get(pk=first_id)
            party=original.case.parties.exclude(pk=original.party_id).first()
            if party is None:party=m.Party.objects.create(case=original.case,slot="B" if original.party.slot=="A" else "A",name="Synthetic second participant")
            party.account=second;party.participating=True;party.save(update_fields=["account","participating"])
            app=m.Application.objects.create(owner=second,case=original.case,proceeding=original.proceeding,party=party,
                status="submitted",submitted_at=timezone.now(),current_version=1,questionnaire=original.questionnaire)
            m.AnswerRevision.objects.create(application=app,number=1,answers=original.revisions.get(number=1).answers,
                questionnaire=original.questionnaire,actor=second)
            m.FeeObligation.objects.create(application=app,status="waived")
            return str(app.pk)
        second_id=fixture_db(second_filing_fixture)
        original=detail(one,first_id);before_history=one.request.get(f"{base}/api/applications/{first_id}/history/").json()
        before_notifications=fixture_db(lambda:m.Notification.objects.filter(recipient=second).count())
        assert original["can_withdraw"] and not original["can_delete_draft"]
        assert post(one,one_csrf,f"/api/applications/{first_id}/delete-draft/",{"expected_version":original["version"]}).status==422
        assert post(two,two_csrf,f"/api/applications/{first_id}/withdraw/",{"expected_version":original["version"]}).status==403
        for payload in [{},{"expected_version":0}]:assert post(one,one_csrf,f"/api/applications/{first_id}/withdraw/",payload).status==422
        first_page=open_editor(one)
        assert first_page.get_by_role("button",name="Delete unsubmitted draft",exact=True).count()==0
        first_page.get_by_role("button",name="Withdraw my filing",exact=True).click()
        with first_page.expect_response(lambda r:r.url==f"{base}/api/applications/{first_id}/withdraw/") as result:
            first_page.get_by_role("button",name="Confirm action",exact=True).click()
        assert result.value.status==200 and result.value.request.post_data_json=={"expected_version":original["version"]}
        first_page.get_by_role("button",name="Refresh application",exact=True).click()
        expect(first_page.get_by_role("button",name="Withdraw my filing",exact=True)).to_have_count(0)
        assert detail(one,first_id)["status"]=="withdrawn"
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
        checks.append("Synthetic second-participant state verifies first withdrawal preserves joint case/other filing without spouse notification; last withdrawal closes case")
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
        assert post(two,two_csrf,f"/api/applications/{appeal_id}/withdraw/",{"expected_version":1}).status==403
        response=post(one,one_csrf,f"/api/applications/{appeal_id}/withdraw/",{"expected_version":1})
        assert response.status==200,response.text()
        assert detail(one,appeal_id)["status"]=="withdrawn" and detail(one,appeal_id)["fee"]==row["fee"]
        assert fixture_db(lambda:m.AnswerRevision.objects.filter(application_id=appeal_id).count())==1
        assert fixture_db(joint_state)["case"]=="closed"
        checks.append("Pending appeal fixture withdrawal remains owner-only before disposition, preserving fee/revision and closed case; admin and other applicant denied")
        return checks
    finally:
        for ctx in contexts:ctx.close()
