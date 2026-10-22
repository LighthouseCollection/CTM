"""Compare actual pinned validators; isolate each invalid field from row-ID checks."""
import ast,hashlib,json,subprocess,types
from pathlib import Path
from django.core.exceptions import ValidationError
ROOT=Path(__file__).resolve().parents[1]
BASE='104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc';CURRENT='ff8571720ae1940034832bfbb69ddf9503f94c0e'
ID='abcdefab-1234-4234-8234-123456789abc'
fields=[{'code':'name','type':'text','required':True},{'code':'birth_date','type':'date'},
 {'code':'gender','type':'choice','choices':['M','F','unknown']},{'code':'lives_with','type':'choice','choices':['self','spouse','unknown']},
 {'code':'confirmed','type':'boolean'}]
schema={'fields':[{'code':'children','type':'list','item_fields':fields}]}
def child(**values):return {'id':ID,'name':'Fictional Child',**values}
cases=[('nested-required',schema,{'children':[{'id':ID}]},'rejected','children[0].name'),
 ('nested-date',schema,{'children':[child(birth_date='not-a-date')]},'rejected','children[0].birth_date'),
 ('nested-choice',schema,{'children':[child(gender='invalid')]},'rejected','children[0].gender'),
 ('nested-boolean',schema,{'children':[child(confirmed='false')]},'rejected','children[0].confirmed'),
 ('repeat-object-shape',schema,{'children':['not-an-object']},'rejected','Repeat rows must be objects'),
 ('duplicate-repeat-id',schema,{'children':[child(),child(name='Second Child')]},'rejected','distinct stable UUIDs'),
 ('case-normalized-duplicate-id',schema,{'children':[child(),child(id=ID.upper())]},'rejected','distinct stable UUIDs'),
 ('missing-repeat-id',schema,{'children':[{'name':'Fictional Child'}]},'rejected','distinct stable UUIDs'),
 ('textarea-type',{'fields':[{'code':'statement','type':'textarea'}]},{'statement':{'object':'invalid'}},'rejected','statement'),
 ('primitive-list-choice',{'fields':[{'code':'grounds','type':'list','choices':['abuse']}]},{'grounds':['unpublished']},'rejected','grounds'),
 ('top-level-date',{'fields':[{'code':'date','type':'date'}]},{'date':'not-a-date'},'rejected','date'),
 ('top-level-required',{'fields':[{'code':'name','type':'text','required':True}]},{'name':'   '},'rejected','name'),
 ('top-level-boolean',{'fields':[{'code':'flag','type':'boolean'}]},{'flag':'false'},'rejected','flag'),
 ('valid-configured-unknown',schema,{'children':[child(gender='unknown',lives_with='unknown')]},'accepted',None),
 ('valid-textarea',{'fields':[{'code':'statement','type':'textarea'}]},{'statement':'Original narrative'},'accepted',None),
 ('row-local-hidden-required',{'fields':[{'code':'rows','type':'list','item_fields':[{'code':'details','type':'text','required':True,'when':{'field':'other','equals':True}},{'code':'other','type':'boolean'}]}]},{'rows':[{'id':ID,'other':False}]},'accepted',None),
 ('row-local-shown-required',{'fields':[{'code':'rows','type':'list','item_fields':[{'code':'details','type':'text','required':True,'when':{'field':'other','equals':True}},{'code':'other','type':'boolean'}]}]},{'rows':[{'id':ID,'other':True}]},'rejected','rows[0].details')]
outputs={}
for ref in [BASE,CURRENT]:
 raw=subprocess.check_output(['git','show',ref+':tribunal/validation.py'],cwd=ROOT).decode('utf-8')
 namespace={};exec(compile(raw,ref+'/tribunal/validation.py','exec'),namespace)
 results=[]
 for code,definition,answers,expected,location in cases:
  error=None
  try:namespace['validate_answers'](types.SimpleNamespace(definition=definition),answers);actual='accepted'
  except ValidationError as exc:actual='rejected';error='; '.join(exc.messages)
  except Exception as exc:actual=type(exc).__name__;error=str(exc)
  results.append({'id':code,'expected':expected,'actual':actual,'error':error,'expected_location':location,
   'outcome_matches':actual==expected,'location_matches':location is None or bool(error and location in error)})
 config=subprocess.check_output(['git','show',ref+':tribunal/services/configuration.py'],cwd=ROOT).decode('utf-8')
 tree=ast.parse(config)
 sets=[{item.value for item in n.elts if isinstance(item,ast.Constant)} for n in ast.walk(tree) if isinstance(n,ast.Set)]
 outputs[ref]={'checks':results,'outcomes_matching':sum(r['outcome_matches'] for r in results),'total':len(results),
  'publisher_type_vocabulary_includes_textarea':any({'text','date','choice','boolean','list','textarea'}<=s for s in sets),
  'validation_sha256':hashlib.sha256(raw.encode()).hexdigest(),'configuration_sha256':hashlib.sha256(config.encode()).hexdigest()}
assert all(r['outcome_matches'] and r['location_matches'] for r in outputs[CURRENT]['checks']),outputs[CURRENT]
result={'scope':'Direct actual validator functions from pinned source, not publication/database/live acceptance; rejection cases have otherwise-valid UUIDs to avoid masking field validation','baseline':BASE,'current':CURRENT,'runs':outputs}
out=ROOT/'docs/implementation/applicant/field-mapping/backend-validation-comparison.json';out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'current':CURRENT,'passed':outputs[CURRENT]['outcomes_matching'],'total':len(cases),'baseline_matching':outputs[BASE]['outcomes_matching']}))
