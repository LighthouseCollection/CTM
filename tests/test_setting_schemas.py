"""Typed nonsecret settings, legacy reads and compare/save under actual app RLS."""
from copy import deepcopy
import pytest
from django.core.exceptions import ValidationError
from tribunal.models import SettingRevision
from tribunal.services.configuration import save_setting
from tests.test_core_policy_completion import granted_roles

pytestmark=pytest.mark.django_db

VALUES={
 'translation_prompt':{'text':'Synthetic test prompt; not approved published source'},
 'translation_routing':{'mode':'ai','primary':{'provider':'synthetic-adapter','model':'synthetic-model','enabled':True,'timeout_seconds':30,'max_retries':2}},
 'tribunal_contact':{'display':'Synthetic test tribunal','email':'contact@example.test'},
 'email_templates':{'templates':[{'code':'submission_received','subject_en':'Synthetic','subject_ar':'اختبار','body_en':'Test body','body_ar':'نص تجريبي'}]},
 'document_categories':{'categories':[{'code':'MC','label_en':'Synthetic label','label_ar':'اختبار'}]},
 'recommended_doctors':{'doctors':[{'id':'11111111-1111-4111-8111-111111111111','name':'Synthetic test doctor','specialty':'medical','contact':'test@example.test','active':True}]},
}

@pytest.mark.parametrize('key',list(VALUES))
def test_typed_family_http_compare_save_and_metadata(granted_roles,people,client,key):
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        descriptor=client.get('/api/system/settings/').json()['schemas'][key]
        assert descriptor['current_version']==0 and descriptor['schema_version']==1
        assert descriptor['expected_version_required'] is True
        assert descriptor['activation_supported'] is False
        assert descriptor['max_json_bytes']==100_000 and descriptor['max_json_depth']==20
        if key=='translation_routing':
            assert len(descriptor['value_schema']['allOf'])==2
        payload={'key':key,'value':deepcopy(VALUES[key]),'expected_version':0,'schema_version':1}
        first=client.post('/api/system/settings/',payload,content_type='application/json')
        assert first.status_code==201,first.content
        assert first.json()['version']==1
        stale=client.post('/api/system/settings/',payload,content_type='application/json')
        assert stale.status_code==409 and stale.json()['current_version']==1
        read=client.get('/api/system/settings/').json()
        row=next(x for x in read['items'] if x['key']==key)
        assert row['value']==VALUES[key] and row['validation_state']=='valid'
        assert read['schemas'][key]['current_version']==1
    assert SettingRevision.objects.filter(key=key).count()==1


@pytest.mark.parametrize('key,value',[
 ('translation_prompt',{'text':{}}),('translation_prompt',{'text':'  '}),
 ('tribunal_contact',{'email':'not-an-email'}),('tribunal_contact',{'display':'X','role':'admin'}),
 ('translation_routing',{'mode':'ai'}),
 ('translation_routing',{'mode':'local','primary':VALUES['translation_routing']['primary']}),
 ('translation_routing',{'mode':'local','endpoint':'http://127.0.0.1/internal'}),
 ('translation_routing',{'mode':'ai','primary':{**VALUES['translation_routing']['primary'],'max_retries':True}}),
 ('translation_routing',{'mode':'ai','primary':{**VALUES['translation_routing']['primary'],'timeout_seconds':301}}),
 ('email_templates',{'templates':[VALUES['email_templates']['templates'][0]]*2}),
 ('document_categories',{'categories':[{'code':'MC','label_en':'X','label_ar':'Y','required':False}]}),
 ('document_categories',{'categories':[{'code':'invented','label_en':'X','label_ar':'Y'}]}),
 ('recommended_doctors',{'doctors':[VALUES['recommended_doctors']['doctors'][0]]*2}),
 ('recommended_doctors',{'doctors':[{**VALUES['recommended_doctors']['doctors'][0],'active':'true'}]}),
])
def test_family_validation_rejects_unsafe_or_untyped_values(people,key,value):
    with pytest.raises(ValidationError):
        save_setting(people['admin'],key,value,expected_version=0)
    assert not SettingRevision.objects.exists()


@pytest.mark.parametrize('patch',[
 {'expected_version':None},{'expected_version':True},{'schema_version':2},
 {'schema_version':True},{'actor':'someone-else'},
])
def test_http_write_contract_rejects_invalid_versions_and_fields(granted_roles,people,client,patch):
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        response=client.post('/api/system/settings/',{'key':'tribunal_contact','value':VALUES['tribunal_contact'],'expected_version':0,**patch},content_type='application/json')
        assert response.status_code==422,response.content
    assert not SettingRevision.objects.exists()


def test_missing_expected_version_is_rejected(granted_roles,people,client):
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        response=client.post('/api/system/settings/',{'key':'tribunal_contact','value':VALUES['tribunal_contact']},content_type='application/json')
        assert response.status_code==422


def test_legacy_shapes_preserved_and_secret_legacy_values_redacted(granted_roles,people,client):
    legacy=SettingRevision.objects.create(key='tribunal_contact',number=1,value={'legacy_address':'Unconverted'},actor=people['admin'])
    unsafe=SettingRevision.objects.create(key='translation_routing',number=1,value={'password':'synthetic-test-secret'},actor=people['admin'])
    SettingRevision.objects.create(key='unsupported_legacy',number=1,value='synthetic-unsupported-secret',actor=people['admin'])
    client.force_login(people['secretary'])
    with granted_roles('ctm_app',session=True):
        response=client.get('/api/system/settings/')
        assert response.status_code==200,response.content
        rows={row['key']:row for row in response.json()['items']}
        assert rows['tribunal_contact']['validation_state']=='legacy_requires_review'
        assert rows['tribunal_contact']['value']==legacy.value
        assert rows['translation_routing']['validation_state']=='unsafe_legacy_value'
        assert rows['translation_routing']['value'] is None
        assert b'synthetic-test-secret' not in response.content
        assert rows['unsupported_legacy']['validation_state']=='unsupported_legacy_key'
        assert rows['unsupported_legacy']['value'] is None
        assert b'synthetic-unsupported-secret' not in response.content
        replacement=client.post('/api/system/settings/',{'key':'tribunal_contact','value':{'display':'Reviewed replacement'},'expected_version':1},content_type='application/json')
        assert replacement.status_code==201,replacement.content
    legacy.refresh_from_db();unsafe.refresh_from_db()
    assert legacy.value=={'legacy_address':'Unconverted'}
    assert unsafe.value=={'password':'synthetic-test-secret'}


@pytest.mark.parametrize('role',['applicant','member','president'])
def test_settings_schemas_and_values_remain_administrative(granted_roles,people,client,role):
    client.force_login(people[role])
    with granted_roles('ctm_app',session=True):
        for method in ['get','post']:
            response=getattr(client,method)('/api/system/settings/')
            assert response.status_code==403
            assert b'value_schema' not in response.content
