"""Configured display labels cannot change filing-document identity or safety rules."""
from copy import deepcopy
import uuid
import pytest
from django.db import connection, DatabaseError
from tribunal import models as m
from tribunal.db.context import database_actor
from tribunal.services.applications import DOCUMENT_LABELS, document_requirements, required_documents
from tribunal.services.configuration import save_setting
from tests.test_core_policy_completion import granted_roles

pytestmark=pytest.mark.django_db


def label_value(code='CMC', en='Synthetic configured civil label', ar='عنوان مدني تجريبي'):
    return {'categories':[{'code':code,'label_en':en,'label_ar':ar}]}


def get_requirements(client,app):
    result=client.get(f'/api/applications/{app.pk}/files/')
    assert result.status_code==200,result.content
    return result.json()['requirements']


def test_owner_filing_consumes_bilingual_labels_without_settings_access(granted_roles,ready_application,people,client):
    app=ready_application
    answers=app.revisions.get(number=app.current_version).answers
    original=deepcopy(answers)
    save_setting(people['admin'],'document_categories',label_value(),expected_version=0)
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        with database_actor(app.owner):
            assert not m.SettingRevision.objects.exists()
        configured=get_requirements(client,app)
        civil=next(row for row in configured if row['category']=='CMC')
        assert (civil['label_en'],civil['label_ar'])==('Synthetic configured civil label','عنوان مدني تجريبي')
        assert civil['required'] is True
        for row in configured:
            if row['category']!='CMC':
                assert (row['label_en'],row['label_ar'])==DOCUMENT_LABELS[row['category']]
        assert {row['category'] for row in configured if row['required']}=={'MC','CMC','CDD','PHOTO'}
        assert client.get('/api/system/settings/').status_code==403
        with database_actor(app.owner):
            assert not m.SettingRevision.objects.exists()
    app.revisions.get(number=app.current_version).refresh_from_db()
    assert app.revisions.get(number=app.current_version).answers==original
    assert document_requirements(app,answers)!=configured


def test_latest_label_revision_and_explicit_empty_reset(granted_roles,ready_application,people,client):
    app=ready_application
    save_setting(people['admin'],'document_categories',label_value(),expected_version=0)
    save_setting(people['admin'],'document_categories',label_value(en='Second configured label'),expected_version=1)
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        assert next(row for row in get_requirements(client,app) if row['category']=='CMC')['label_en']=='Second configured label'
    save_setting(people['admin'],'document_categories',{'categories':[]},expected_version=2)
    with granted_roles('ctm_app',session=True):
        assert next(row for row in get_requirements(client,app) if row['category']=='CMC')['label_en']==DOCUMENT_LABELS['CMC'][0]


@pytest.mark.parametrize('invalid',[
    None,[],{'categories':[1]}, {'categories':[{'code':'CMC','label_en':'Changed','label_ar':'س','password':'do-not-expose'}]},
    {'categories':[{'code':'CMC','label_en':'x'*301,'label_ar':'س'}]},
    {'categories':[{'code':'UNKNOWN','label_en':'Changed','label_ar':'س'}]},
    {'categories':[{'code':'CMC','label_en':'Changed','label_ar':'  '}]},
    {'categories':[{'code':'CMC','label_en':'Changed','label_ar':'س'},{'code':'CMC','label_en':'duplicate','label_ar':'س'}]},
    {'categories':[], 'token':'do-not-expose'},
])
def test_invalid_latest_legacy_labels_fail_closed_without_older_activation(granted_roles,ready_application,people,client,invalid):
    app=ready_application
    save_setting(people['admin'],'document_categories',label_value(),expected_version=0)
    # Owner setup models historical invalid content; never a permitted live settings write.
    from django.db.models import Value, JSONField
    stored=Value(None,output_field=JSONField()) if invalid is None else invalid
    m.SettingRevision.objects.create(key='document_categories',number=2,value=stored,actor=people['admin'])
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        result=client.get(f'/api/applications/{app.pk}/files/')
        assert result.status_code==200,result.content
        assert b'do-not-expose' not in result.content
        civil=next(row for row in result.json()['requirements'] if row['category']=='CMC')
        assert (civil['label_en'],civil['label_ar'])==DOCUMENT_LABELS['CMC']


def test_ro_context_identity_and_core_requirement_validation_are_unchanged(granted_roles,ready_application,people,client):
    from tribunal.services.applications import save_answers
    from django.core.exceptions import ValidationError
    app=ready_application
    answers=app.revisions.get(number=app.current_version).answers
    answers={**answers,'restraining_orders':[{'id':str(uuid.uuid4()),'case_number':'RO-synthetic'}]}
    save_answers(app.owner,app.pk,answers,app.current_version)
    app.refresh_from_db()
    save_setting(people['admin'],'document_categories',label_value('RO','Configured RO label','عنوان أمر تجريبي'),expected_version=0)
    client.force_login(app.owner)
    with granted_roles('ctm_app',session=True):
        row=next(row for row in get_requirements(client,app) if row['category']=='RO')
        assert row['context']==answers['restraining_orders'][0]['id'] and row['required'] is True
        assert row['label_en']=='Configured RO label'
        with database_actor(app.owner),pytest.raises(ValidationError):
            required_documents(app,answers)
    # Even an unsafe category label configuration never relaxes required documents.
    assert document_requirements(app,answers)[-1]['required'] is True


def test_label_consumer_is_app_only_and_settings_descriptor_is_truthful(granted_roles,people,client):
    save_setting(people['admin'],'document_categories',label_value(),expected_version=0)
    with granted_roles('ctm_app',session=True),connection.cursor() as cursor:
        cursor.execute('SELECT * FROM public.ctm_document_category_labels()')
        assert cursor.fetchall()==[]
    with pytest.raises(DatabaseError):
        with granted_roles('ctm_worker'),connection.cursor() as cursor:
            cursor.execute('SELECT * FROM public.ctm_document_category_labels()')
    client.force_login(people['admin'])
    with granted_roles('ctm_app',session=True):
        schema=client.get('/api/system/settings/').json()['schemas']['document_categories']
        assert schema['runtime_consumers']==['filing_document_labels']
        assert schema['activation_supported'] is False
