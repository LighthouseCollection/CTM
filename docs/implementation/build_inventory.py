import json
import os
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
os.chdir(root)
sys.path.insert(0,str(root))
os.environ['DJANGO_SETTINGS_MODULE']='ctm.settings_test'
import django
django.setup()
from django.apps import apps
from django.urls import get_resolver,URLPattern

models=[]
for model in apps.get_app_config('tribunal').get_models():
    fields=[]
    for field in model._meta.local_fields:
        item={'name':field.name,'column':field.column,'type':field.get_internal_type(),'nullable':field.null,'primary_key':field.primary_key}
        if field.is_relation:item['target']=field.related_model._meta.label
        fields.append(item)
    models.append({'model':model._meta.label,'table':model._meta.db_table,'fields':fields})
contract=json.loads(Path('docs/architecture/build-spec/schema.json').read_text(encoding='utf-8'))
inventory={'status':'partial implementation; not a contract replacement','contract_table_count':len(contract['tables']),'implemented_domain_model_count':len(models),'models':models}
Path('docs/implementation/model-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
routes=[{'route':str(pattern.pattern),'handler':pattern.callback.__name__} for pattern in get_resolver().url_patterns if isinstance(pattern,URLPattern)]
Path('docs/implementation/api-routes.json').write_text(json.dumps(routes,indent=2),encoding='utf-8')
print(f'Inventory: {len(models)} implemented domain models / {len(contract["tables"])} contract tables; {len(routes)} explicit routes')
