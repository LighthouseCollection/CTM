"""Own answer history and notification acceptance on isolated real Django APIs."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import expect


def history_checks(browser,page,context,base,app_id,cookies,settings,output):
    checks=[]
    before=context.request.get(f"{base}/api/applications/{app_id}/").json()
    versions=context.request.get(f"{base}/api/applications/{app_id}/history/")
    assert versions.status==200 and "no-store" in versions.headers['cache-control']
    retained=versions.json()['items'];assert len(retained)==2 and [row['version'] for row in retained]==[1,2]
    page.get_by_role('button',name='View saved answer history',exact=True).click()
    panel=page.get_by_role('dialog',name='My saved answer history',exact=True)
    expect(panel.get_by_label('Saved version',exact=True)).to_have_value('2')
    expect(panel.get_by_text('/last_name',exact=True)).to_be_visible()
    expect(panel.get_by_text('Previous saved value: "Applicant"',exact=True)).to_be_visible()
    expect(panel.get_by_text('Selected saved value: "Concurrent saved correction"',exact=True)).to_be_visible()
    checks.append('Actual own saved history shows retained original/concurrent revisions and attributed server time without changing answers')
    panel.get_by_label('Saved version',exact=True).select_option('1')
    expect(panel.get_by_text('Recorded by: '+retained[0]['actor'],exact=True)).to_be_visible()
    assert panel.get_by_role('button',name='Download own answer history JSON',exact=True).count()==0
    assert retained[0]['answers']['children'][0]['id']
    checks.append('Own history modal preserves saved repeat IDs and supplied actor with current-label provenance and no product export')
    page.keyboard.press('Escape')
    page.get_by_role('textbox',name='First name',exact=False).fill('Unsaved during history refresh')
    page.get_by_role('button',name='View saved answer history',exact=True).click()
    panel.get_by_role('button',name='Refresh answer history',exact=True).click()
    expect(panel.get_by_label('Saved version',exact=True)).to_have_value('2')
    expect(page.get_by_role('textbox',name='First name',exact=False)).to_have_value('Unsaved during history refresh')
    assert context.request.get(f"{base}/api/applications/{app_id}/").json()['answers']==before['answers']
    page.keyboard.press('Escape')
    page.get_by_role('button',name='Back',exact=True).click();page.get_by_role('button',name='Keep editing',exact=True).click()
    checks.append('Actual history refresh and inspection preserve local unsaved draft and guard navigation while server answers/revisions stay unchanged')
    page.get_by_role('button',name='العربية',exact=True).click();page.set_viewport_size({'width':390,'height':1000})
    page.get_by_role('button',name='عرض سجل الإجابات المحفوظة',exact=True).click()
    expect(page.get_by_role('dialog',name='سجل إجاباتي المحفوظة',exact=True)).to_be_visible()
    assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('dialog',name='سجل إجاباتي المحفوظة',exact=True).screenshot(path=str(Path(output)/'ar-own-history-390.png'),caret='initial')
    page.keyboard.press('Escape')
    with page.expect_response(lambda response:response.url==base+'/api/account/settings/' and response.request.method=='POST') as language:
        page.get_by_role('button',name='English',exact=True).click()
    assert language.value.status==200;page.set_viewport_size({'width':1280,'height':1000})
    for name in ['outsider','admin']:
        other=browser.new_context()
        try:
            other.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':cookies[name],'url':base}])
            denied=other.request.get(f"{base}/api/applications/{app_id}/history/")
            if os.environ.get('CTM_APPLICANT_PRIVATE_RESOURCE_DENIAL_CONTRACT')=='hidden404':
                missing=other.request.get(f"{base}/api/applications/{uuid.uuid4()}/history/")
                assert denied.status==missing.status==404 and denied.json()==missing.json()
            else:assert denied.status==403
        finally:other.close()
    page.get_by_role('button',name='Refresh application status',exact=True).click();page.get_by_role('button',name='Discard unsaved changes',exact=True).click()
    expect(page.get_by_role('textbox',name='First name',exact=False)).to_have_value(before['answers']['first_name'])
    checks.append('Own draft history stays private from outsider/council and renders safely in Arabic390px; explicit discard restores the saved editor')
    return checks


def notification_checks(browser,page,context,base,owner_id,cookies,settings,fixture_db,output):
    from tribunal import models as m
    checks=[]
    def seed():
        owner=m.Account.objects.get(pk=owner_id)
        return [str(m.Notification.objects.create(recipient=owner,key=f"private-audit-notice-{i}-{uuid.uuid4()}",kind='case_update',payload={'internal':'NEVER EXPOSE NOTICE PAYLOAD'}).pk) for i in range(51)]
    private=set(fixture_db(seed))
    page.goto(base,wait_until='networkidle');page.get_by_role('button',name='Notifications',exact=True).click()
    expect(page.get_by_role('heading',name='My notifications',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Load more notifications',exact=True)).to_be_visible()
    seen=set();offset=0;before=None
    while True:
        response=context.request.get(f"{base}/api/notifications/?offset={offset}");assert response.status==200
        data=response.json();before=before or data;seen.update(row['id'] for row in data['items'])
        if data['next_offset'] is None:break
        offset=data['next_offset']
    assert private<=seen
    while page.get_by_role('button',name='Load more notifications',exact=True).count():
        with page.expect_response(lambda response:'/api/notifications/?offset=' in response.url) as loaded:
            page.get_by_role('button',name='Load more notifications',exact=True).click()
        assert loaded.value.status==200
        page.wait_for_function("!Array.from(document.querySelectorAll('button')).some(b=>b.textContent==='Load more notifications'&&b.disabled)")
    assert page.get_by_text('NEVER EXPOSE NOTICE PAYLOAD',exact=False).count()==0
    checks.append('Actual private inbox loads all own notice pages and authoritative count while omitting raw payload internals')
    before_rows=before['items'];first=next(row for row in before_rows if row['id'] in private)
    # The newest synthetic notices are first and unread.
    with page.expect_response(lambda response:response.url==base+'/api/notifications/' and response.request.method=='POST') as ack:
        page.get_by_role('button',name='Mark notification as read',exact=True).first.click()
    assert ack.value.status==200 and ack.value.json()=={'updated':True}
    payload=ack.value.request.post_data_json;assert payload['id'] in private
    csrf=next(cookie['value'] for cookie in context.cookies() if cookie['name']=='csrftoken')
    initial_time=fixture_db(lambda:m.Notification.objects.get(pk=payload['id']).read_at.isoformat())
    repeat=context.request.post(base+'/api/notifications/',data=payload,headers={'X-CSRFToken':csrf})
    assert repeat.status==200 and repeat.json()=={'updated':False}
    assert fixture_db(lambda:m.Notification.objects.get(pk=payload['id']).read_at.isoformat())==initial_time
    checks.append('Explicit actual acknowledgement marks only the requested own notification; exact repeat retains first server read time')
    page.get_by_role('button',name='Refresh notifications',exact=True).click();expect(page.get_by_text('Read',exact=True).first).to_be_visible()
    assert context.request.get(base+'/api/notifications/?offset=0').json()['unread_count']==before['unread_count']-1
    for name in ['outsider','admin']:
        other=browser.new_context()
        try:
            other.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':cookies[name],'url':base}]);other.request.get(base+'/api/session/')
            other_csrf=next(cookie['value'] for cookie in other.cookies() if cookie['name']=='csrftoken');offset=0
            while True:
                data=other.request.get(f"{base}/api/notifications/?offset={offset}").json();assert not private.intersection(row['id'] for row in data['items'])
                if data['next_offset'] is None:break
                offset=data['next_offset']
            hidden=other.request.post(base+'/api/notifications/',data={'id':next(iter(private))},headers={'X-CSRFToken':other_csrf})
            assert hidden.status==200 and hidden.json()=={'updated':False}
        finally:other.close()
    checks.append('Actual outsider/council inbox pages exclude every seeded private notification and foreign acknowledgement returns false without mutation')
    page.get_by_role('button',name='العربية',exact=True).click();page.set_viewport_size({'width':390,'height':1000})
    expect(page.get_by_role('heading',name='إشعاراتي',exact=True)).to_be_visible()
    assert page.locator('[style]').count()==0 and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(Path(output)/'ar-private-notifications-390.png'),full_page=True,caret='initial')
    with page.expect_response(lambda response:response.url==base+'/api/account/settings/' and response.request.method=='POST') as language:
        page.get_by_role('button',name='English',exact=True).click()
    assert language.value.status==200;page.set_viewport_size({'width':1280,'height':1000})
    checks.append('Actual own read status/count refresh and Arabic390px notification UI remain separate from message read or email-delivery evidence')
    return checks
