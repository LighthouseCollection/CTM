"""Applicant #1 checkpoint: recursive final validation and publisher agreement."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from django.core.exceptions import ValidationError
from tribunal.validation import validate_answers
from tribunal.services.configuration import validate_questionnaire_definition

ROW_ID='11111111-1111-4111-8111-111111111111'
FIELDS=[{'code':'name','type':'text','required':True},
 {'code':'birth_date','type':'date'},
 {'code':'gender','type':'choice','choices':['M','F','unknown']},
 {'code':'lives_with','type':'choice','choices':['self','spouse','unknown']}]
SCHEMA=SimpleNamespace(definition={'fields':[{'code':'children','type':'list','item_fields':FIELDS}]})

@pytest.mark.parametrize('rows',[
 [{}], [{'id':ROW_ID}], [{'id':ROW_ID,'name':'Child','birth_date':'not-a-date'}],
 [{'id':ROW_ID,'name':'Child','gender':'invalid'}],
 [{'id':ROW_ID,'name':'Child','lives_with':'invalid'}], ['not-an-object'],
 [{'id':ROW_ID,'name':'A'},{'id':ROW_ID,'name':'B'}],
 [{'id':ROW_ID,'name':'A'},{'id':ROW_ID.upper(),'name':'B'}],
 [{'id':'bad-id','name':'A'}],
])
def test_final_repeat_validation_rejects_malformed_rows(rows):
    with pytest.raises(ValidationError):
        validate_answers(SCHEMA,{'children':rows})


def test_valid_unknown_repeat_and_textarea_publish_and_validate():
    definition=deepcopy(SCHEMA.definition)
    definition['fields'].append({'code':'statement','type':'textarea'})
    validate_questionnaire_definition(definition)
    schema=SimpleNamespace(definition=definition)
    validate_answers(schema,{'children':[{'id':ROW_ID,'name':'Child','gender':'unknown','lives_with':'unknown'}],'statement':'Narrative'})
    with pytest.raises(ValidationError):
        validate_answers(schema,{'statement':{'unexpected':'object'}})


@pytest.mark.parametrize('fields',[
 [{'code':'x','type':'unsupported'}],
 [{'code':'x','type':'text'},{'code':'x','type':'text'}],
 [{'code':'x','type':'choice','choices':[]}],
 [{'code':'x','type':'text','when':{'field':'missing','equals':True}}],
])
def test_publisher_rejects_invalid_nested_definitions(fields):
    with pytest.raises(ValidationError):
        validate_questionnaire_definition({'fields':[{'code':'rows','type':'list','item_fields':fields}]})


def test_nested_conditions_are_scoped_to_the_same_row():
    schema=SimpleNamespace(definition={'fields':[{'code':'rows','type':'list','item_fields':[
        {'code':'known','type':'boolean'},
        {'code':'details','type':'textarea','required':True,'when':{'field':'known','equals':True}}
    ]}]})
    validate_questionnaire_definition(schema.definition)
    validate_answers(schema,{'rows':[{'id':ROW_ID,'known':False}]})
    with pytest.raises(ValidationError):
        validate_answers(schema,{'rows':[{'id':ROW_ID,'known':True}]})


@pytest.mark.django_db
def test_missing_civil_certificate_blocks_even_without_configured_category(ready_application):
    from tribunal.services.applications import required_documents, document_requirements
    from tribunal.models import FileTechnicalEvent, FileVersion, Attachment
    app=ready_application
    answers=app.revisions.get(number=app.current_version).answers
    assert {'MC','CMC'} <= {r['category'] for r in document_requirements(app,answers) if r['required']}
    attachment=app.attachments.get(category='CMC')
    FileTechnicalEvent.objects.filter(file__attachment=attachment).delete()
    FileVersion.objects.filter(attachment=attachment).delete()
    attachment.delete()
    with pytest.raises(ValidationError,match='CMC'):
        required_documents(app,answers)


@pytest.mark.django_db
@pytest.mark.parametrize('metadata',[
 {'court':'Court','case_number':'123','status':'active'},
 {'court':'Court','number':'123','status':'active'},
 {'court':'Court','case_number':'123','number':'123','status':'active'},
])
def test_restraining_order_number_aliases_preserve_context_copy_requirement(ready_application,metadata):
    from tribunal.services.applications import required_documents
    from tribunal.models import Attachment,FileVersion,FileTechnicalEvent
    app=ready_application
    answers=deepcopy(app.revisions.get(number=app.current_version).answers)
    answers['restraining_orders']=[{'id':ROW_ID,**metadata}]
    with pytest.raises(ValidationError,match='RO'):
        required_documents(app,answers)
    attachment=Attachment.objects.create(application=app,owner=app.owner,category='RO',context=ROW_ID)
    file=FileVersion.objects.create(attachment=attachment,number=1,object_key='test/order',original_name='order.pdf',
        display_name='order.pdf',mime_type='application/pdf',byte_count=5,sha256='b'*64,actor=app.owner)
    FileTechnicalEvent.objects.create(file=file,task='scan',result='clean')
    assert file in required_documents(app,answers)
    answers['restraining_orders'][0]['case_number']='different'
    answers['restraining_orders'][0]['number']='123'
    with pytest.raises(ValidationError,match='conflict'):
        required_documents(app,answers)
    answers['restraining_orders'][0].pop('number')
    answers['restraining_orders'][0]['court']={'untrusted':'object'}
    with pytest.raises(ValidationError,match='court'):
        required_documents(app,answers)


@pytest.mark.parametrize('change',[
 {'grounds':{'untrusted':'object'}}, {'grounds':[{}]}, {'first_name':{}},
 {'children':['not-an-object']}, {'children':{}},
 {'children':[{'gender':{},'lives_with':'unknown'}]},
 {'spouse_birth_date':'not-a-date'},
])
def test_petition_rejects_malformed_unconfigured_values_as_validation_errors(change):
    from tribunal.services.applications import validate_petition
    answers={'first_name':'A','last_name':'B','gender':'M','birth_date':'1980-01-01',
             'marriage_date':'2005-01-01','grounds':['infidelity'],**change}
    with pytest.raises(ValidationError):
        validate_petition(answers)


@pytest.mark.parametrize('permit',[True,{},[]])
def test_prior_marriage_permit_matches_approved_text_storage(permit):
    from tribunal.services.applications import validate_petition
    answers={'first_name':'A','last_name':'B','gender':'M','birth_date':'1980-01-01',
             'marriage_date':'2005-01-01','grounds':['infidelity'],
             'prior_marriages':[{'id':ROW_ID,'spouse_name':'Previous spouse','ecclesiastical_permit':permit}]}
    with pytest.raises(ValidationError):
        validate_petition(answers)


def test_prior_marriage_text_binding_preserves_absence_and_text():
    from tribunal.services.applications import validate_petition
    answers={'first_name':'A','last_name':'B','gender':'M','birth_date':'1980-01-01',
             'marriage_date':'2005-01-01','grounds':['infidelity'],
             'prior_marriages':[{'id':ROW_ID,'spouse_name':'Previous spouse','ecclesiastical_permit':'Recorded permit reference'}]}
    validate_petition(answers)
    answers['prior_marriages'][0].pop('ecclesiastical_permit')
    validate_petition(answers)
