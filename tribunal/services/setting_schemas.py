"""Server-owned value schemas for nonsecret versioned configuration storage."""
from copy import deepcopy
import uuid
import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

SCHEMA_VERSION = 1


def text(maximum=2000, *, minimum=1, **extra):
    return {'type':'string','minLength':minimum,'maxLength':maximum,'pattern':r'\S',**extra}


def record(properties, required=(), **extra):
    return {'type':'object','properties':properties,'required':list(required),
            'additionalProperties':False,**extra}


def collection(items, *, unique_by=None):
    schema={'type':'array','items':items}
    if unique_by:
        schema['uniqueBy']=unique_by
    return schema


def schemas():
    from tribunal.services.applications import DOCUMENT_LABELS
    from tribunal.tasks import EMAIL_KINDS
    provider=record({'provider':text(100),'model':text(200),'enabled':{'type':'boolean'},
        'timeout_seconds':{'type':'integer','minimum':1,'maximum':300},
        'max_retries':{'type':'integer','minimum':0,'maximum':5}},
        ['provider','model','enabled','timeout_seconds','max_retries'])
    return {
        'translation_prompt':record({'text':text(100_000)},['text']),
        'translation_routing':record({'mode':{'type':'string','enum':['ai','local']},
            'primary':provider,'fallback':deepcopy(provider)},['mode'],allOf=[
                {'if':{'properties':{'mode':{'const':'ai'}}},'then':{'required':['primary'],
                    'properties':{'primary':{'properties':{'enabled':{'const':True}}}}}},
                {'if':{'properties':{'mode':{'const':'local'}}},'then':{'properties':{
                    'primary':{'properties':{'enabled':{'const':False}}},
                    'fallback':{'properties':{'enabled':{'const':False}}}}}},
            ]),
        'tribunal_contact':record({'display':text(300),'email':text(254,format='email'),
            'phone':text(100),'address':text(2000)},minProperties=1),
        'email_templates':record({'templates':collection(record({
            'code':{'type':'string','enum':sorted(EMAIL_KINDS)},
            'subject_en':text(300,**{'not':{'pattern':r'[\r\n]'}}),'subject_ar':text(300,**{'not':{'pattern':r'[\r\n]'}}),
            'body_en':text(20_000),'body_ar':text(20_000)},
            ['code','subject_en','subject_ar','body_en','body_ar']),unique_by='code')},['templates']),
        'document_categories':record({'categories':collection(record({
            'code':{'type':'string','enum':list(DOCUMENT_LABELS)},
            'label_en':text(300),'label_ar':text(300)},
            ['code','label_en','label_ar']),unique_by='code')},['categories']),
        'recommended_doctors':record({'doctors':collection(record({
            'id':text(36,format='uuid'),'name':text(300),
            'specialty':{'type':'string','enum':['medical','psychological','both']},
            'contact':text(2000),'active':{'type':'boolean'}},
            ['id','name','specialty','contact','active']),unique_by='id')},['doctors']),
    }


def validate_setting_value(key, value, *, schema_version=SCHEMA_VERSION):
    if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
        raise ValidationError('Unsupported setting schema_version.')
    schema=schemas().get(key)
    if schema is None:
        raise ValidationError('Unsupported setting key.')

    def visit(node, definition, path):
        kind=definition['type']
        valid={'object':isinstance(node,dict),'array':isinstance(node,list),
               'string':isinstance(node,str),'boolean':type(node) is bool,
               'integer':type(node) is int}[kind]
        if not valid:
            raise ValidationError(f'Invalid configuration type: {path}')
        if 'enum' in definition and node not in definition['enum']:
            raise ValidationError(f'Unsupported configuration choice: {path}')
        if kind=='object':
            properties=definition['properties']
            if set(node)-set(properties) or set(definition['required'])-set(node):
                raise ValidationError(f'Use the declared configuration fields: {path}')
            if len(node)<definition.get('minProperties',0):
                raise ValidationError(f'Configuration fields are required: {path}')
            for name,child in node.items():
                visit(child,properties[name],f'{path}.{name}')
        elif kind=='array':
            seen=set()
            for index,child in enumerate(node):
                visit(child,definition['items'],f'{path}[{index}]')
                if 'uniqueBy' in definition:
                    name=definition['uniqueBy']
                    identity=child[name]
                    if definition['items']['properties'][name].get('format')=='uuid':
                        identity=str(uuid.UUID(identity))
                    if identity in seen:
                        raise ValidationError(f'Duplicate configuration identity: {path}')
                    seen.add(identity)
        elif kind=='string':
            if (not definition.get('minLength',0)<=len(node)<=definition.get('maxLength',100_000) or not node.strip()):
                raise ValidationError(f'Configuration text length is invalid: {path}')
            if not re.search(definition.get('pattern',r'\S'),node):
                raise ValidationError(f'Invalid configuration text: {path}')
            if 'not' in definition and re.search(definition['not']['pattern'],node):
                raise ValidationError(f'Invalid configuration text: {path}')
            if definition.get('format')=='email':
                try:
                    validate_email(node)
                except ValidationError:
                    raise ValidationError(f'Invalid configuration email: {path}')
            if definition.get('format')=='uuid':
                try:
                    uuid.UUID(node)
                except ValueError:
                    raise ValidationError(f'Invalid configuration UUID: {path}')
        elif kind=='integer' and not definition['minimum']<=node<=definition['maximum']:
            raise ValidationError(f'Configuration integer is outside its bounds: {path}')
    visit(value,schema,key)
    if key=='translation_routing':
        if value['mode']=='ai' and ('primary' not in value or not value['primary']['enabled']):
            raise ValidationError('AI routing requires an explicitly enabled primary configuration.')
        if value['mode']=='local' and any(value.get(slot,{}).get('enabled') for slot in ['primary','fallback']):
            raise ValidationError('Local routing cannot enable an external provider slot.')


def schema_descriptors(current_versions):
    return {key:{'schema_version':SCHEMA_VERSION,'value_schema':value,
        'current_version':current_versions.get(key,0), 'expected_version_required':True,
        'activation_supported':False,'runtime_consumers':(['account_status_email'] if key=='email_templates' else ['filing_document_labels'] if key=='document_categories' else []),'max_json_bytes':100_000,'max_json_depth':20} for key,value in schemas().items()}
