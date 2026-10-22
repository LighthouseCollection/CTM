"""Real private-message browser/API acceptance on an isolated synthetic case."""
import uuid
from pathlib import Path
from playwright.sync_api import expect


def run(browser,page,context,staff,base,csrf,staff_csrf,case_id,case_number,party_id,outsider_cookie,settings,fixture_db,output,admin_id):
    from tribunal import models as m
    checks=[]
    def seed():
        from tribunal.services.communications import send_message
        admin=m.Account.objects.get(pk=admin_id)
        return [str(send_message(admin,case_id,f"Synthetic private paginated message {index}",[party_id],idempotency_key=f"pagination-{index}").pk) for index in range(51)]
    private_ids=set(fixture_db(seed))
    page.goto(base,wait_until="networkidle")
    page.get_by_role("button",name="Past cases",exact=True).click()
    page.get_by_text(case_number,exact=True).click()
    page.get_by_role("button",name="Communications",exact=True).click()
    expect(page.get_by_role("heading",name="Private case messages",exact=True)).to_be_visible()
    expect(page.get_by_role("button",name="Load more messages",exact=True)).to_be_visible()
    assert fixture_db(lambda:m.MessageRecipient.objects.filter(message__case_id=case_id,party_id=party_id,read_at__isnull=False).count())==0
    page.get_by_role("button",name="Load more messages",exact=True).click()
    expect(page.get_by_role("button",name="Load more messages",exact=True)).to_have_count(0)
    expect(page.get_by_text("Synthetic private paginated message 50",exact=True)).to_be_visible()
    messages=context.request.get(f"{base}/api/cases/{case_id}/messages/?offset=0").json()
    assert len(messages["items"])==50 and messages["next_offset"]==50
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
    assert staff.request.post(f"{base}/api/messages/{first['id']}/read/",data={},headers={"X-CSRFToken":staff_csrf}).status==403
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
        assert stranger.request.post(f"{base}/api/messages/{first['id']}/read/",data={},headers={"X-CSRFToken":other_csrf}).status==403
        forged=stranger.request.post(f"{base}/api/cases/{case_id}/messages/",data={"body":"Foreign thread","party_ids":[party_id],"idempotency_key":str(uuid.uuid4())},headers={"X-CSRFToken":other_csrf})
        assert forged.status==403,forged.text()
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
