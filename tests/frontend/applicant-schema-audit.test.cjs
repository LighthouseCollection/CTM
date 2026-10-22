const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs');
let reconcile;
try{reconcile=require('../../scripts/audit_applicant_schema.cjs');}catch(e){if(e.code!=='MODULE_NOT_FOUND')throw e;}
const schema=()=>({version:'contract',tables:[{name:'applications',domain:'filings',columns:[
 {name:'id',type:'uuid',nullable:false,primary_key:true},
 {name:'owner_person_id',type:'uuid',nullable:false,references:'persons'},
 {name:'facts',type:'jsonb',nullable:false},
 {name:'received_at',type:'timestamptz',nullable:true}]}]});
const inventory=()=>({contract_table_count:1,implemented_domain_model_count:1,models:[{model:'tribunal.Application',table:'legacy_app',fields:[
 {name:'id',column:'id',type:'UUIDField',nullable:false,primary_key:true},
 {name:'owner',column:'owner_id',type:'ForeignKey',nullable:false,target:'tribunal.Account'},
 {name:'answers',column:'answers',type:'JSONField',nullable:false}]}]});
const config=()=>({batches:[{id:'filing',title:'Filing',tables:['applications']}],mappings:{applications:{model:'tribunal.Application',
 columns:{facts:{column:'answers',status:'json_candidate',reason:'Structured evidence needs exact mapping review'}}}}});
const run=(s=schema(),i=inventory(),c=config())=>reconcile(s,i,c);
test('schema reconciliation exposes absent owner person rather than treating account ownership as equivalent',()=>{
 assert.equal(typeof reconcile,'function');const r=run(),fields=r.tables[0].columns;
 assert.equal(fields.find(f=>f.name==='id').status,'column_candidate');
 assert.equal(fields.find(f=>f.name==='owner_person_id').status,'unmapped_column');
 assert.equal(fields.find(f=>f.name==='received_at').status,'unmapped_column');
 assert.equal(r.production_acceptance,'not_verified');assert.equal(r.tables[0].physical_table_match,false);
});
test('JSON storage candidates are not normalized schema parity',()=>{
 const r=run(),field=r.tables[0].columns.find(f=>f.name==='facts');
 assert.equal(field.status,'json_candidate');assert.equal(field.parity_verified,false);
 assert.equal(r.counts.json_candidate,1);assert.equal(r.counts.unmapped_column,2);
});
test('foreign key target and nullability differences stay visible',()=>{
 const s=schema(),i=inventory(),c=config();s.tables.push({name:'persons',domain:'identity',columns:[]});
 i.models.push({model:'tribunal.Person',table:'legacy_person',fields:[]});i.implemented_domain_model_count=2;i.contract_table_count=2;
 c.mappings.persons={model:'tribunal.Person'};c.mappings.applications.columns.owner_person_id={column:'owner_id',reason:'Candidate ownership relation'};
 i.models[0].fields[1].nullable=true;
 const f=run(s,i,c).tables[0].columns.find(x=>x.name==='owner_person_id');
 assert.ok(f.differences.includes('foreign_key_target'));assert.ok(f.differences.includes('nullability'));
 assert.equal(f.parity_verified,false);
});
test('unknown mapping targets and duplicated batch membership reject misleading reports',()=>{
 const c=config();c.mappings.applications.model='tribunal.Absent';assert.throws(()=>run(schema(),inventory(),c),/Unknown model/);
 const d=config();d.batches.push({id:'other',tables:['applications']});assert.throws(()=>run(schema(),inventory(),d),/multiple batches/);
 const e=config();e.mappings.applications.columns.facts.column='not_a_column';assert.throws(()=>run(schema(),inventory(),e),/Unknown column/);
});
test('inventory counters are checked and excluded catalog tables stay accounted for',()=>{
 const s=schema();s.tables.push({name:'council_votes',domain:'decisions',columns:[{name:'vote',type:'text',nullable:false}]});
 const i=inventory();i.contract_table_count=2;const r=run(s,i);
 assert.equal(r.counts.contract_tables,2);assert.equal(r.counts.in_scope_tables,1);assert.deepEqual(r.outside_scope,['council_votes']);
 const bad=inventory();bad.implemented_domain_model_count=63;assert.throws(()=>run(schema(),bad),/inventory count/);
});
test('cross-type and primary-key differences are reported without inferring runtime security',()=>{
 const i=inventory();i.models[0].fields[0].type='CharField';i.models[0].fields[0].primary_key=false;
 const r=run(schema(),i),field=r.tables[0].columns[0];
 assert.ok(field.differences.includes('type'));assert.ok(field.differences.includes('primary_key'));
 assert.equal(r.runtime_security,'not_verified');
});

test('shared adapter model mappings are surfaced as a reconciliation risk rather than counted as parity',()=>{
 const s=schema();s.tables.push({name:'filing_candidates',domain:'filings',columns:[{name:'id',type:'uuid',nullable:false,primary_key:true}]});
 const i=inventory();i.contract_table_count=2;const c=config();c.batches[0].tables.push('filing_candidates');
 c.mappings.filing_candidates={model:'tribunal.Application',reason:'Deliberately shared adapter candidate'};
 const r=run(s,i,c);
 assert.deepEqual(r.shared_adapter_models,[{model:'tribunal.Application',contract_tables:['applications','filing_candidates']}]);
 assert.equal(r.counts.mapped_tables,2);assert.equal(r.production_acceptance,'not_verified');
});
