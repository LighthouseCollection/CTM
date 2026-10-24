"""Focused HTTP/browser journey under actual ctm_app PostgreSQL login.
This preserves rather than replaces the separate strict-suite status findings.
"""
import json,uuid
from pathlib import Path
from playwright.sync_api import expect

def run(browser,base,settings,fixture_db,session_cookie,admin_cookie,output,runtime_database,errors):
    from tribunal import models as m
    checks=[];denials=[];contexts=[];failure=None
    def account(label):
        actor=fixture_db(lambda:m.Account.objects.create_user(email=label+'-'+uuid.uuid4().hex+'@example.test',email_verified=True,first_name=label,last_name='Fictional'))
        return actor,fixture_db(lambda:session_cookie(actor))
    def context(cookie):
        ctx=browser.new_context(viewport={'width':1280,'height':1000});contexts.append(ctx)
        ctx.add_cookies([{'name':settings.SESSION_COOKIE_NAME,'value':cookie,'url':base}]);ctx.request.get(base+'/api/session/')
        csrf=next(c['value'] for c in ctx.cookies() if c['name']=='csrftoken');return ctx,csrf
    def post(ctx,csrf,path,data):return ctx.request.post(base+path,data=data,headers={'X-CSRFToken':csrf})
    def denied(response,scope):
        # Here the assertion is non-disclosure; the original strict403 test stays unchanged.
        assert response.status in {403,404},response.text()
        body=response.json();assert body.get('error') in {'forbidden','resource_or_input_invalid'} and 'items' not in body and 'answers' not in body
        assert 'Maya restricted-role statement' not in response.text()
        denials.append({'scope':scope,'status':response.status,'error':body['error']})
    try:
        actor,cookie=account('Maya');other,other_cookie=account('Owen')
        own,csrf=context(cookie);foreign,foreign_csrf=context(other_cookie);staff,staff_csrf=context(admin_cookie)
        page=own.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base,wait_until='networkidle');page.get_by_role('button',name='My application',exact=True).click()
        with page.expect_response(lambda r:r.url==base+'/api/applications/' and r.request.method=='POST') as started:
            page.get_by_role('button',name='Start or resume application',exact=True).click()
        assert started.value.status==201,started.value.text();app_id=started.value.json()['id']
        for label,value in [('First name','Maya'),('Last name','Fictional'),('Birth date','1989-03-04'),('Marriage date','2004-06-07')]:page.get_by_label(label,exact=False).fill(value)
        page.get_by_label('Gender',exact=False).select_option('F');page.get_by_label('Abuse',exact=True).check()
        page.get_by_role('textbox',name='Statement',exact=False).fill('Maya restricted-role statement')
        with page.expect_response(lambda r:r.url==f'{base}/api/applications/{app_id}/' and r.request.method=='POST') as saved:
            page.get_by_role('button',name='Save draft',exact=True).click()
        assert saved.value.status==201,saved.value.text()
        checks.append('Actual ctm_app session/bootstrap permits own draft start and browser answer save while all domain tables force RLS')
        original=own.request.get(f'{base}/api/applications/{app_id}/').json();assert original['version']==1
        for ctx,scope in [(foreign,'outsider private draft'),(staff,'council private draft')]:
            denied(ctx.request.get(f'{base}/api/applications/{app_id}/'),scope)
            denied(ctx.request.get(f'{base}/api/applications/{app_id}/history/'),scope+' history')
        denied(post(foreign,foreign_csrf,f'/api/applications/{app_id}/',{'answers':{'first_name':'forged'},'expected_version':1}),'foreign answer write')
        assert own.request.get(f'{base}/api/applications/{app_id}/').json()['answers']==original['answers']
        checks.append('Runtime-role outsider/council draft and history denial returns no source payload; foreign write preserves exact own answers (403/404 observations retained)')
        listing=own.request.get(f'{base}/api/applications/{app_id}/files/').json();files=[]
        for requirement in listing['requirements']:
            if not requirement['required']:continue
            image=requirement['category']=='PHOTO'
            upload=own.request.post(base+'/api/files/',multipart={'application_id':app_id,'category':requirement['category'],
                'file':{'name':'fictional.png' if image else 'fictional.pdf','mimeType':'image/png' if image else 'application/pdf',
                    'buffer':b'\x89PNG\r\n\x1a\nsynthetic' if image else b'%PDF-1.7 synthetic restricted-role original'}},headers={'X-CSRFToken':csrf})
            assert upload.status==201,upload.text();files.append(upload.json()['id'])
        for file in files:
            assert own.request.get(f'{base}/api/files/{file}/').status==200
            denied(foreign.request.get(f'{base}/api/files/{file}/'),'foreign original download')
        checks.append('Runtime-role own required-original uploads/downloads work with controlled scan policy; foreign original bytes remain denied')
        waived=post(staff,staff_csrf,f'/api/applications/{app_id}/waiver/',{});assert waived.status==201,waived.text()
        page.get_by_role('button',name='Refresh documents',exact=True).click()
        expect(page.get_by_role('link',name='Download original',exact=True)).to_have_count(len(files))
        page.get_by_role('button',name='Refresh application status',exact=True).click()
        expect(page.get_by_role('region',name='Payment status and history',exact=True).get_by_text('Application fee: $250.00 · Authorized fee waiver',exact=True)).to_be_visible()
        expect(page.get_by_role('link',name='Download original',exact=True)).to_have_count(len(files))
        expect(page.get_by_text('No unresolved checkout is recorded.',exact=True)).to_be_visible()
        page.get_by_role('button',name='Review answers',exact=True).click()
        expect(page.get_by_role('button',name='Continue editing',exact=True)).to_be_visible()
        page.get_by_label('I have read and accept this declaration.',exact=True).check()
        page.get_by_label('Your full name',exact=False).fill('Maya Fictional')
        with page.expect_response(lambda r:r.url==f'{base}/api/applications/{app_id}/submit/' and r.request.method=='POST') as submitted:
            page.get_by_role('button',name='Submit application',exact=True).click()
        assert submitted.value.status==201,submitted.value.text()
        receipt=submitted.value.json();payload=submitted.value.request.post_data_json
        exact=post(own,csrf,f'/api/applications/{app_id}/submit/',payload)
        assert exact.status==201 and exact.json()['id']==receipt['id']
        first=fixture_db(lambda:list(m.Submission.objects.filter(application_id=app_id).values('id','revision_id','manifest','attestation','actor_id')))
        assert len(first)==1 and str(first[0]['actor_id'])==str(actor.pk)
        checks.append('Runtime-role authorized waiver and browser declaration/submission commit one attributed formal receipt; exact replay returns it without another submission')
        returned=post(staff,staff_csrf,f'/api/applications/{app_id}/review/',{'result':'reject','instructions':'Synthetic correction request for restricted-role acceptance'})
        assert returned.status==201,returned.text()
        page.reload(wait_until='networkidle');page.get_by_role('button',name='My application',exact=True).click();page.get_by_role('button',name='Open application',exact=True).click()
        expect(page.get_by_label('First name',exact=False)).to_have_value('Maya')
        page.get_by_label('First name',exact=False).fill('Maya corrected')
        with page.expect_response(lambda r:r.url==f'{base}/api/applications/{app_id}/' and r.request.method=='POST') as corrected:
            page.get_by_role('button',name='Save corrections',exact=True).click()
        assert corrected.value.status==201,corrected.value.text()
        history=own.request.get(f'{base}/api/applications/{app_id}/history/').json()['items']
        assert [r['answers']['first_name'] for r in history]==['Maya','Maya corrected']
        assert fixture_db(lambda:list(m.Submission.objects.filter(application_id=app_id).values('id','revision_id','manifest','attestation','actor_id')))==first
        checks.append('Runtime-role returned corrections save as a new own revision while original formal revision/manifest/attestation/actor remain exact')
        # PostgreSQL projection refresh can finish before the document component's
        # version-bound readiness refresh. Reviewing earlier is intentionally
        # invalidated when that later refresh completes, so wait for every
        # required original before entering the final review state.
        expect(page.get_by_role('link',name='Download original',exact=True)).to_have_count(len(files))
        page.get_by_role('button',name='Review answers',exact=True).click()
        expect(page.get_by_role('button',name='Resubmit corrections',exact=True)).to_be_enabled()
        with page.expect_response(lambda r:r.url==f'{base}/api/applications/{app_id}/submit/' and r.request.method=='POST') as resubmitted:
            page.get_by_role('button',name='Resubmit corrections',exact=True).click()
        assert resubmitted.value.status==201,resubmitted.value.text()
        assert 'attestation' not in resubmitted.value.request.post_data_json
        final=own.request.get(f'{base}/api/applications/{app_id}/').json()
        assert final['status']=='submitted' and final['fee']['status']=='waived'
        assert fixture_db(lambda:m.Submission.objects.filter(application_id=app_id).count())==2
        checks.append('Runtime-role resubmission retains fee waiver and original signature, records corrected submission and does not request another attestation')
        notice=fixture_db(lambda:m.Notification.objects.create(recipient=actor,key='focused-'+uuid.uuid4().hex,kind='case_update',payload={}).pk)
        own_items=own.request.get(base+'/api/notifications/?offset=0').json()['items'];assert any(r['id']==str(notice) for r in own_items)
        ack=post(own,csrf,'/api/notifications/',{'id':str(notice)});assert ack.status==200 and ack.json()=={'updated':True}
        assert post(own,csrf,'/api/notifications/',{'id':str(notice)}).json()=={'updated':False}
        assert post(foreign,foreign_csrf,'/api/notifications/',{'id':str(notice)}).json()=={'updated':False}
        checks.append('Runtime-role own notification acknowledgement commits once; exact repeat and foreign acknowledgement cannot change it')
        assert not errors,errors
    except Exception as exc:
        failure={'type':type(exc).__name__,'message':str(exc)[:4000]}
        if 'page' in locals():
            (Path(output)/'postgres-focused-page.txt').write_text(page.locator('body').inner_text(),encoding='utf-8')
        raise
    finally:
        for ctx in contexts:ctx.close()
        report={'backend_sha':__import__('os').environ['CTM_TEST_BACKEND_SHA'],'completed_groups':len(checks),'checks':checks,'failure':failure,'runtime_database':runtime_database,'denial_observations':denials,'scope':'Focused PostgreSQL applicant journey; synthetic authentication/content/scan policy/waiver, not full strict suite or institutional/live acceptance'}
        (Path(output)/'postgres-focused-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
