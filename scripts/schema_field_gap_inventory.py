"""Regenerate unaccepted field-level evidence against protected schema; no schema edits."""
import json,ast
from pathlib import Path
approved=json.loads(Path('docs/architecture/build-spec/schema.json').read_text())
prior=json.loads(Path('docs/implementation/schema-reconciliation.json').read_text())
source=ast.parse(Path('tribunal/models.py').read_text())
classes={c.name:c for c in source.body if isinstance(c,ast.ClassDef)}
def fields(name):
 c=classes.get(name); result={}
 if not c:return result
 for b in c.bases:
  if isinstance(b,ast.Name):result.update(fields(b.id))
 for n in c.body:
  if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call):
   for t in n.targets:
    if isinstance(t,ast.Name):result[t.id]=ast.unparse(n.value)
 return result
rows=[]
for table,old in zip(approved['tables'],prior['tables']):
 assert table['name']==old['approved_table']
 adapters={m:fields(m) for m in old['candidate_adapters']}
 columns=[]
 for col in table['columns']:
  candidates=[]
  for model,fs in adapters.items():
   for name,definition in fs.items():
    if name==col['name'] or name+'_id'==col['name']:
     candidates.append({'model':model,'field':name,'definition':definition})
  columns.append({'approved':col,'same_named_candidates':candidates,'assessment':'manual_semantic_review_required' if candidates else 'no_same_named_candidate; inspect adapter or add guarded migration'})
 rows.append({'approved_table':table['name'],'domain':table['domain'],'purpose':table['purpose'],'retention':table.get('retention'),'candidate_adapters':list(adapters),'columns':columns,'constraints':table.get('constraints',[]),'indexes':table.get('indexes',[]),'accepted_equivalence':False})
Path('docs/implementation/schema-field-gap-inventory.json').write_text(json.dumps({'status':'field/type/relationship evidence inventory, not accepted equivalence','source':'docs/architecture/build-spec/schema.json','tables':rows},indent=2)+'\n')
