"""Withdrawals must count participating parties even when the caller cannot read them."""
import pytest
from tribunal import models as m
from tribunal.services.applications import submit_application
from tribunal.services.decisions import withdraw_application
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


@pytest.fixture
def joint_filing(ready_application, people, granted_roles):
    from tribunal.services.identity import link_party
    from tribunal.services.applications import start_application, save_answers, waive_fee
    app = ready_application
    submit_application(app.owner, app.pk, 'withdraw-first', {'accepted': True, 'name': 'John Smith'})
    app.refresh_from_db()
    other = m.Account.objects.create_user(email='withdraw-second@example.test', role='applicant', email_verified=True)
    link_party(people['admin'], app.case, other)
    second = start_application(other, app.case_id)
    save_answers(other, second.pk, {'first_name':'Jane','last_name':'Smith','gender':'F',
        'birth_date':'1987-04-02','marriage_date':'2010-05-01','grounds':['infidelity'],'statement':'Synthetic'}, 0)
    for category in ['MC','CMC','CDD','PHOTO']:
        attachment=m.Attachment.objects.create(application=second,owner=other,category=category)
        file=m.FileVersion.objects.create(attachment=attachment,number=1,object_key=f'test/{attachment.pk}',
            original_name='file.pdf',display_name='file.pdf',mime_type='image/jpeg' if category=='PHOTO' else 'application/pdf',
            byte_count=5,sha256='c'*64,actor=other)
        m.FileTechnicalEvent.objects.create(file=file,task='scan',result='clean')
    waive_fee(people['admin'],second.pk)
    with granted_roles('ctm_app',other,session=True):
        submit_application(other,second.pk,'withdraw-second',{'accepted':True,'name':'Jane Smith'})
    second.refresh_from_db()
    return app,second


@pytest.mark.parametrize('status',['returned','submitted','accepted'])
def test_joint_withdrawal_preserves_other_filing_then_final_closes(granted_roles,joint_filing,status,people):
    first,second=joint_filing
    m.Application.objects.filter(pk=first.pk).update(status=status)
    from tribunal.services.reports import create_request,send_request
    hidden = create_request(people['admin'],first.proceeding_id,first.party_id,'external_priest','Private priest',[])
    token = send_request(people['admin'],hidden.pk,'Private Priest')
    draft = create_request(people['admin'],first.proceeding_id,second.party_id,'intake','Unsent request',[])
    before=list(m.Submission.objects.filter(application__in=[first,second]).values('id','revision_id','manifest','attestation','actor_id'))
    notices=m.Notification.objects.filter(recipient=second.owner).count()
    with granted_roles('ctm_app',first.owner,session=True):
        assert not m.Party.objects.filter(pk=second.party_id).exists()
        withdraw_application(first.owner,first.pk,expected_version=first.current_version)
        assert not m.Party.objects.filter(pk=second.party_id).exists()
    first.refresh_from_db();second.refresh_from_db();first.case.refresh_from_db()
    assert first.status=='withdrawn' and second.status=='submitted'
    assert first.case.status=='open'
    hidden.refresh_from_db();draft.refresh_from_db()
    assert hidden.state=='sent' and draft.state=='draft'
    assert m.OpenCaseClaim.objects.filter(case=first.case).count()==2
    assert m.Notification.objects.filter(recipient=second.owner).count()==notices
    assert list(m.Submission.objects.filter(application__in=[first,second]).values('id','revision_id','manifest','attestation','actor_id'))==before
    with granted_roles('ctm_app',second.owner,session=True):
        withdraw_application(second.owner,second.pk,expected_version=second.current_version)
    first.case.refresh_from_db()
    assert first.case.status=='closed'
    assert not m.Proceeding.objects.filter(case=first.case,status='open').exists()
    assert not m.OpenCaseClaim.objects.filter(case=first.case).exists()
    hidden.refresh_from_db();draft.refresh_from_db()
    assert hidden.state=='closed' and draft.state=='cancelled'
    assert hidden.token_hash
    assert not m.Notification.objects.filter(recipient=first.owner,kind='petitions_withdrawn').exists()


@pytest.mark.parametrize('bad', ['outside_operation','foreign_target','no_actor','not_withdrawn','worker'])
def test_withdrawal_helpers_fail_closed(granted_roles,joint_filing,bad):
    from django.db import connection,DatabaseError
    from tribunal.db.context import database_settings
    from contextlib import nullcontext
    first,second=joint_filing
    role='ctm_worker' if bad=='worker' else 'ctm_app'
    actor=None if bad=='no_actor' else first.owner
    if bad not in {'not_withdrawn','worker'}:
        with granted_roles('ctm_app',first.owner,session=True):
            withdraw_application(first.owner,first.pk,expected_version=first.current_version)
    target=second.pk if bad=='foreign_target' else first.pk
    with nullcontext() if bad!='worker' else pytest.raises(DatabaseError,match='permission denied'):
        with granted_roles(role,actor,session=True):
            with database_settings({'ctm.core_operation':'other' if bad=='outside_operation' else 'withdraw',
                'ctm.core_target':str(first.pk)}):
                with connection.cursor() as cursor:
                    cursor.execute('SELECT public.ctm_withdrawal_can_close(%s)',[target])
                    assert cursor.fetchone()==(False,)
    with pytest.raises(DatabaseError):
        with granted_roles(role,actor,session=True):
            with connection.cursor() as cursor:
                cursor.execute('SELECT public.ctm_closed_case_cleanup(%s)',[first.case_id])
    first.case.refresh_from_db()
    assert first.case.status=='open'
    assert m.OpenCaseClaim.objects.filter(case=first.case).count()==2


def test_stale_withdrawal_version_does_not_mutate(granted_roles,joint_filing):
    from django.core.exceptions import ValidationError
    first,second=joint_filing
    with pytest.raises(ValidationError):
        with granted_roles('ctm_app',first.owner,session=True):
            withdraw_application(first.owner,first.pk,expected_version=first.current_version+1)
    first.refresh_from_db();first.party.refresh_from_db();first.case.refresh_from_db()
    assert first.status=='submitted' and first.party.withdrawn_at is None and first.case.status=='open'
