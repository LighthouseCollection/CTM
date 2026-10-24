"""Source-pinned, non-mutating validator probes. Observations are not acceptance tests."""
import ast,json,subprocess,types
from pathlib import Path
from django.core.exceptions import ValidationError
ROOT=Path(__file__).resolve().parents[1]
REF='104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc'
raw=subprocess.check_output(['git','show',REF+':tribunal/validation.py'],cwd=ROOT).decode()
namespace={};exec(compile(raw,'pinned/tribunal/validation.py','exec'),namespace)
validate=namespace['validate_answers']
schema=types.SimpleNamespace(definition={'fields':[{'code':'children','type':'list','item_fields':[{'code':'name','type':'text','required':True},{'code':'birth_date','type':'date'},{'code':'gender','type':'choice','choices':['M','F','unknown']},{'code':'lives_with','type':'choice','choices':['self','spouse','unknown']}]}]})
rows=[]
def probe(code,definition,answers,expectation):
    try:validate(definition,answers);actual='accepted'
    except ValidationError:actual='rejected'
    except Exception as error:actual=type(error).__name__
    rows.append({'id':code,'expected':expectation,'actual':actual,'gap':actual!=expectation,'answers':answers,'source':'tribunal/validation.py:validate_answers'})
probe('nested-required',schema,{'children':[{}]},'rejected')
probe('nested-date',schema,{'children':[{'name':'Fictional Child','birth_date':'not-a-date'}]},'rejected')
probe('nested-choice',schema,{'children':[{'name':'Fictional Child','gender':'invalid','lives_with':'invalid'}]},'rejected')
probe('repeat-object-shape',schema,{'children':['not-an-object']},'rejected')
probe('duplicate-repeat-id',schema,{'children':[{'id':'11111111-1111-4111-8111-111111111111','name':'A'},{'id':'11111111-1111-4111-8111-111111111111','name':'B'}]},'rejected')
probe('textarea-type',types.SimpleNamespace(definition={'fields':[{'code':'statement','type':'textarea'}]}),{'statement':{'unexpected':'object'}},'rejected')
probe('top-level-date',types.SimpleNamespace(definition={'fields':[{'code':'date','type':'date'}]}),{'date':'not-a-date'},'rejected')
probe('top-level-required',types.SimpleNamespace(definition={'fields':[{'code':'name','type':'text','required':True}]}),{'name':'   '},'rejected')
probe('top-level-boolean',types.SimpleNamespace(definition={'fields':[{'code':'flag','type':'boolean'}]}),{'flag':'false'},'rejected')
probe('valid-nested-unknown',schema,{'children':[{'id':'11111111-1111-4111-8111-111111111111','name':'Fictional Child','gender':'unknown','lives_with':'unknown'}]},'accepted')
for row in rows:
    row['exposure']='unsupported definition: publish_questionnaire rejects textarea; frontend/runtime vocabulary mismatch' if row['id']=='textarea-type' else 'list/item_fields or supported primitive definition; final submission has additional checks'
result={'candidate_sha':REF,'scope':'Direct actual validate_answers function from pinned source, no HTTP/database; submit additionally calls validate_petition and required_documents','probes':rows,'gaps':sum(r['gap'] for r in rows)}
out=ROOT/'docs/implementation/applicant/field-mapping/validation-probes.json';out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'probes':len(rows),'gaps':result['gaps']}))
