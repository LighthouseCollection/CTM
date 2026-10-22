"""Applicant10654a7: returned resubmission must not require optional spouse DOB."""
from copy import deepcopy
import pytest
from django.test import Client
from tribunal.models import Case, Party, Person
from tribunal.db.context import database_settings
from tests.test_core_policy_completion import granted_roles

pytestmark=pytest.mark.django_db


@pytest.mark.parametrize('spouse_known',[False,True])
@pytest.mark.parametrize('correction',[{'first_name':'Maya corrected'},{'birth_date':'1985-03-15'}])
def test_bound_returned_filing_resubmits_under_actual_session(granted_roles,ready_application,people,client,spouse_known,correction):
    app=ready_application
    original=deepcopy(app.revisions.get(number=app.current_version).answers)
    original['first_name']='Maya'
    if not spouse_known:
        original.pop('spouse_birth_date',None)
    client.force_login(app.owner)
    staff=Client();staff.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        saved=client.post(f'/api/applications/{app.pk}/',{'answers':original,'expected_version':app.current_version},content_type='application/json')
        assert saved.status_code==201,saved.content
        version=saved.json()['version']
        receipt=client.post(f'/api/applications/{app.pk}/submit/',{'expected_version':version,'idempotency_key':'first-returned-policy','attestation':{'accepted':True,'name':'Maya Smith'}},content_type='application/json')
        assert receipt.status_code==201,receipt.content
    app.refresh_from_db()
    source=app.submissions.get()
    frozen=(deepcopy(source.revision.answers),deepcopy(source.manifest),deepcopy(source.attestation),source.actor_id)
    party_reference=app.party.reference
    case_identity=(app.case.marriage_date,app.case.spouse_dob_low,app.case.spouse_dob_high)
    with granted_roles('ctm_app',session=True):
        returned=staff.post(f'/api/applications/{app.pk}/review/',{'result':'reject','instructions':'Synthetic correction request'},content_type='application/json')
        assert returned.status_code==201,returned.content
        save=client.post(f'/api/applications/{app.pk}/',{'answers':{**original,**correction},'expected_version':version},content_type='application/json')
        assert save.status_code==201,save.content
        payload={'expected_version':save.json()['version'],'idempotency_key':'resubmit-returned-policy'}
        result=client.post(f'/api/applications/{app.pk}/submit/',payload,content_type='application/json')
        assert result.status_code==201,result.content
        assert client.post(f'/api/applications/{app.pk}/submit/',payload,content_type='application/json').json()==result.json()
    app.refresh_from_db();source.refresh_from_db()
    assert app.status=='submitted' and app.submissions.count()==2
    assert (source.revision.answers,source.manifest,source.attestation,source.actor_id)==frozen
    assert app.party.reference==party_reference
    assert (app.case.marriage_date,app.case.spouse_dob_low,app.case.spouse_dob_high)==case_identity
    assert app.submissions.order_by('-created_at').first().revision.answers=={**original,**correction}
