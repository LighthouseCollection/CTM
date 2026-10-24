"""Real private-message browser/API acceptance on an isolated synthetic case."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import expect


def run(browser,page,context,staff,base,csrf,staff_csrf,case_id,case_number,party_id,outsider_cookie,settings,fixture_db,output,admin_id):
    from tribunal import models as m
    checks=[]
    def seed():
        from tribunal.services.communications import send_message
        admin=m.Account.objects.get(pk=admin_id)
        target=m.Party.objects.select_related("account").get(pk=party_id)
        created=[send_message(admin,case_id,f"Synthetic private paginated message {index}",[party_id],idempotency_key=f"pagination-{index}") for index in range(51)]
        ids=[str(message.pk) for message in created]
        recipients=list(m.MessageRecipient.objects.filter(message_id__in=ids).order_by("message__created_at","message_id").values("message_id","party_id","party__account_id","message__case_id","read_at"))
        return {"message_ids":ids,"message_count":m.Message.objects.filter(pk__in=ids).count(),"recipient_count":len(recipients),
            "recipients":[{"message_id":str(row["message_id"]),"party_id":str(row["party_id"]),"account_id":str(row["party__account_id"]),
                "case_id":str(row["message__case_id"]),"read_at":row["read_at"].isoformat() if row["read_at"] else None} for row in recipients],
            "target_party":{"id":str(target.pk),"account_id":str(target.account_id),"case_id":str(target.case_id)},
            "case":{"id":str(case_id),"status":m.Case.objects.get(pk=case_id).status}}
    seeded=fixture_db(seed)
    private_ids=set(seeded["message_ids"])
    message_url=f"{base}/api/cases/{case_id}/messages/?offset=0"
    case_url=f"{base}/api/cases/{case_id}/"
    trace={"case_id":str(case_id),"party_id":str(party_id),"seed":seeded}
    def response_snapshot(response):
        raw=response.text()
        try:payload=json.loads(raw)
        except json.JSONDecodeError:payload=None
        snapshot={"url":response.url,"status":response.status,"payload":payload}
        if payload is None:snapshot["body"]=raw[:10000]
        return snapshot
    try:
        case_response=context.request.get(case_url)
        direct_response=context.request.get(message_url)
        trace["direct_case_response"]=response_snapshot(case_response)
        trace["direct_message_response"]=response_snapshot(direct_response)
        page.goto(base,wait_until="networkidle")
        page.get_by_role("button",name="Past cases",exact=True).click()
        page.get_by_text(case_number,exact=True).click()
        with page.expect_response(lambda response:response.url==message_url and response.request.method=="GET") as browser_messages:
            page.get_by_role("button",name="Communications",exact=True).click()
        trace["browser_message_response"]=response_snapshot(browser_messages.value)
        expect(page.get_by_role("heading",name="Private case messages",exact=True)).to_be_visible()
        more=page.get_by_role("button",name="Load more messages",exact=True)
        trace["rendered"]={"url":page.url,"load_more_count":more.count(),"load_more_visible":more.count()>0 and more.first.is_visible(),
            "body":page.locator("body").inner_text()[:10000]}
        messages=trace["direct_message_response"]["payload"]
        browser_payload=trace["browser_message_response"]["payload"]
        assert case_response.status==200,case_response.text()
        assert direct_response.status==200,direct_response.text()
        assert browser_messages.value.status==200,browser_messages.value.text()
        assert isinstance(messages,dict) and len(messages.get("items",[]))==50 and messages.get("next_offset")==50,messages
        assert browser_payload==messages,(browser_payload,messages)
        expect(more).to_be_visible()
    except Exception:
        artifact=Path(output)
        trace["failure_state"]={"url":page.url,"viewport":page.viewport_size,
            "body":page.locator("body").inner_text()[:10000] if page.locator("body").count() else None}
        (artifact/"message-pagination-failure.json").write_text(json.dumps(trace,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        (artifact/"message-pagination-failure.html").write_text(page.content(),encoding="utf-8")
        page.screenshot(path=str(artifact/"message-pagination-failure.png"),full_page=True,caret="initial")
        raise
    assert fixture_db(lambda:m.MessageRecipient.objects.filter(message__case_id=case_id,party_id=party_id,read_at__isnull=False).count())==0
    page.get_by_role("button",name="Load more messages",exact=True).click()
    expect(page.get_by_role("button",name="Load more messages",exact=True)).to_have_count(0)
    expect(page.get_by_text("Synthetic private paginated message 50",exact=True)).to_be_visible()
    assert all(row["receipts"]==[{"party_id":party_id,"read_at":None}] for row in messages["items"])
    checks.append("Actual own closed-case communication route loads every private message through bounded continuation without auto read acknowledgement")
    first=messages["items"][0]
    # The first rendered message corresponds to the first ordered API row.
    with page.expect_response(lambda response:response.url==f"{base}/api/messages/{first['id']}/read/") as read:
        page.get_by_role("button",name="Mark my copy as read",exact=True).first.click()
    assert read.value.status==200 and read.value.request.post_data_json=={}
    received=read.value.json();assert received["id"]==first["id"] and received["read_at"]
    repeated=context.request.post(f"{base}/api/messages/{first['id']}/read/",data={},headers={"X-CSRFToken":csrf})
    assert repeated.status==200 and repeated.json()==received
    def recipient_snapshot():
        row=m.MessageRecipient.objects.get(message_id=first["id"],party_id=party_id)
        return {"id":str(row.pk),"read_at":row.read_at.isoformat() if row.read_at else None}
    retained_receipt=fixture_db(recipient_snapshot)
    assert staff.request.post(f"{base}/api/messages/{first['id']}/read/",data={},headers={"X-CSRFToken":staff_csrf}).status==403
    assert fixture_db(recipient_snapshot)==retained_receipt
    checks.append("Explicit browser own-copy read acknowledgement retains first timestamp on exact repeat; council sender cannot mark the applicant copy read")
    stranger=browser.new_context()
    try:
        stranger.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":outsider_cookie,"url":base}]);stranger.request.get(base+"/api/session/")
        other_csrf=next(cookie["value"] for cookie in stranger.cookies() if cookie["name"]=="csrftoken")
        offset=0;seen_offsets=set()
        while True:
            assert offset not in seen_offsets;seen_offsets.add(offset)
            response=stranger.request.get(f"{base}/api/cases/{case_id}/messages/?offset={offset}")
            assert response.status==200,response.text()
            hidden=response.json()
            assert not private_ids.intersection(row["id"] for row in hidden["items"])
            assert all(row["id"]!=first["id"] for row in hidden["items"])
            if hidden["next_offset"] is None:break
            offset=hidden["next_offset"]
        foreign_read=stranger.request.post(f"{base}/api/messages/{first['id']}/read/",data={},headers={"X-CSRFToken":other_csrf})
        if os.environ.get("CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT")=="hidden404":
            absent_read=stranger.request.post(f"{base}/api/messages/{uuid.uuid4()}/read/",data={},headers={"X-CSRFToken":other_csrf})
            assert foreign_read.status==absent_read.status==404,(foreign_read.status,absent_read.status)
            assert foreign_read.json()==absent_read.json(),(foreign_read.text(),absent_read.text())
        else:assert foreign_read.status==403,foreign_read.text()
        counts=lambda:(m.Message.objects.filter(case_id=case_id).count(),m.Notification.objects.count())
        before_forged=fixture_db(counts)
        send_url=f"{base}/api/cases/{case_id}/messages/"
        forged_payload={"body":"Foreign thread","party_ids":[party_id],"idempotency_key":str(uuid.uuid4())}
        forged=stranger.request.post(send_url,data=forged_payload,headers={"X-CSRFToken":other_csrf})
        absent=stranger.request.post(send_url,data={**forged_payload,"party_ids":[str(uuid.uuid4())]},headers={"X-CSRFToken":other_csrf})
        after_forged=fixture_db(counts)
        forged_trace={"case_id":str(case_id),"foreign_party_id":str(party_id),"before":before_forged,"after":after_forged,
            "foreign_response":response_snapshot(forged),"absent_response":response_snapshot(absent),
            "receipt_before":retained_receipt,"receipt_after":fixture_db(recipient_snapshot)}
        try:
            assert after_forged==before_forged,(before_forged,after_forged)
            assert forged_trace["receipt_after"]==retained_receipt
            assert forged.status==403,forged.text()
            assert forged.json().get("error")=="forbidden",forged.text()
            assert absent.status==422,absent.text()
            assert absent.json().get("error")=="validation",absent.text()
        except Exception:
            (Path(output)/"message-forged-recipient-failure.json").write_text(json.dumps(forged_trace,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            raise
    finally:stranger.close()
    checks.append("Actual linked spouse sees no other-thread message or receipt, cannot acknowledge it, and cannot send into the other party's thread")
    body="Own private message <script>literal text</script>"
    page.get_by_label("Your message",exact=True).fill(body)
    page.get_by_role("button",name="Back to cases",exact=True).last.click()
    expect(page.get_by_text("Your local message has not been confirmed.",exact=False)).to_be_visible()
    page.get_by_role("button",name="Keep editing",exact=True).click()
    page.get_by_role("button",name="Review message",exact=True).click()
    payloads=[];url=f"{base}/api/cases/{case_id}/messages/"
    def lost_ack(route):
        payloads.append(route.request.post_data_json);actual=route.fetch();assert actual.status==201,actual.text()
        route.fulfill(status=500,json={"error":"synthetic acknowledgement loss after commit"})
    page.route(url,lost_ack)
    page.get_by_role("button",name="Send private message",exact=True).click()
    expect(page.get_by_text("Sending was not confirmed.",exact=False)).to_be_visible()
    expect(page.get_by_role("button",name="Send private message",exact=True)).to_be_disabled()
    assert len(payloads)==1 and payloads[0]["party_ids"]==[party_id] and payloads[0]["body"]==body
    page.get_by_role("button",name="Refresh thread",exact=True).click()
    page.get_by_role("button",name="Load more messages",exact=True).click()
    expect(page.get_by_role("button",name="Load more messages",exact=True)).to_have_count(0)
    expect(page.get_by_text("The server received your message.",exact=True)).to_be_visible();assert len(payloads)==1
    page.unroute(url,lost_ack);payload=payloads[0]
    def counts():return (m.Message.objects.filter(case_id=case_id).count(),m.Notification.objects.count(),m.Outbox.objects.count())
    once=fixture_db(counts)
    replay=context.request.post(url,data=payload,headers={"X-CSRFToken":csrf});assert replay.status==201,replay.text()
    changed=context.request.post(url,data={**payload,"body":"Changed original key"},headers={"X-CSRFToken":csrf});assert changed.status==422
    assert fixture_db(counts)==once
    own=[row for row in context.request.get(url+"?offset=50").json()["items"] if row["idempotency_key"]==payload["idempotency_key"]]
    assert len(own)==1 and own[0]["id"]==replay.json()["id"] and own[0]["body"]==body
    checks.append("Browser reviewed own portal send freezes routing/key; lost real acknowledgement recovers from later own history page; exact replay creates no extra message/alert and changed reuse fails")
    page.get_by_role("button",name="العربية",exact=True).click();page.set_viewport_size({"width":390,"height":1000})
    expect(page.get_by_role("heading",name="رسائل القضية الخاصة",exact=True)).to_be_visible()
    assert page.locator("[style]").count()==0 and page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path=str(Path(output)/"ar-private-messages-390.png"),full_page=True,caret="initial")
    with page.expect_response(lambda response:response.url==base+"/api/account/settings/" and response.request.method=="POST") as language:
        page.get_by_role("button",name="English",exact=True).click()
    assert language.value.status==200
    page.set_viewport_size({"width":1280,"height":1000})
    checks.append("Actual private history/read receipts and escaped frozen review render in Arabic mobile without runtime inline styles or overflow; no email-delivery claim")
    return checks
