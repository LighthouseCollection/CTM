/* Source reconciliation only: column candidates never establish schema or runtime parity. */
"use strict";
function reconcile(schema,inventory,config){
 const tables=new Map(schema.tables.map(t=>[t.name,t]));
 const models=new Map(inventory.models.map(m=>[m.model,m]));
 if(tables.size!==schema.tables.length||models.size!==inventory.models.length)throw Error("Duplicate catalog identity");
 if(inventory.implemented_domain_model_count!==models.size||inventory.contract_table_count!==tables.size)
  throw Error("Catalog inventory count mismatch");
 const membership=new Map(),batches=[];
 for(const batch of config.batches){
  if(batches.some(b=>b.id===batch.id))throw Error("Duplicate batch identity");
  batches.push({id:batch.id,title:batch.title,tables:[...batch.tables]});
  for(const name of batch.tables){
   if(!tables.has(name))throw Error(`Unknown contract table ${name}`);
   if(membership.has(name))throw Error(`Table belongs to multiple batches: ${name}`);
   membership.set(name,batch.id);
  }
 }
 for(const [name,mapping] of Object.entries(config.mappings)){
  const table=tables.get(name);if(!table)throw Error(`Unknown contract table ${name}`);
  const model=mapping.model?models.get(mapping.model):null;
  if(mapping.model&&!model)throw Error(`Unknown model ${mapping.model}`);
  for(const [column,link] of Object.entries(mapping.columns||{})){
   if(!table.columns.some(c=>c.name===column))throw Error(`Unknown contract column ${name}.${column}`);
   if(!model?.fields.some(f=>f.column===link.column))throw Error(`Unknown column ${mapping.model}.${link.column}`);
   if(link.status&&!['json_candidate','column_candidate'].includes(link.status))throw Error('Unknown mapping status');
   if((link.status==='json_candidate'||link.column!==column)&&!link.reason)throw Error('Explicit mapping needs a reason');
  }
  for(const candidate of mapping.storage_candidates||[]){
   const field=models.get(candidate.model)?.fields.find(f=>f.column===candidate.column);
   if(!field)throw Error(`Unknown column ${candidate.model}.${candidate.column}`);
   if(!candidate.reason)throw Error('Storage candidate needs a reason');
  }
 }
 const counts={contract_tables:tables.size,inventory_models:models.size,in_scope_tables:membership.size,
  mapped_tables:0,no_standalone_model_mapping:0,column_candidate:0,json_candidate:0,unmapped_column:0,
  candidate_columns_with_differences:0,contract_columns:0};
 const normalizedType={UUIDField:'uuid',DateTimeField:'timestamptz',DateField:'date',JSONField:'jsonb',
  CharField:'text',TextField:'text',EmailField:'text',BooleanField:'boolean',IntegerField:'integer',
  PositiveIntegerField:'integer',BigIntegerField:'bigint',PositiveBigIntegerField:'bigint',ForeignKey:'uuid',OneToOneField:'uuid'};
 const rows=[];
 for(const [name,batch] of membership){
  const table=tables.get(name),mapping=config.mappings[name]||{},model=models.get(mapping.model);
  counts[model?'mapped_tables':'no_standalone_model_mapping']++;
  const columns=table.columns.map(column=>{
   const explicit=mapping.columns?.[column.name],field=model?.fields.find(f=>f.column===(explicit?.column||column.name));
   const status=field?(explicit?.status||'column_candidate'):'unmapped_column',differences=[];
   counts[status]++;counts.contract_columns++;
   if(field&&status!=='json_candidate'){
    if(normalizedType[field.type]!==column.type)differences.push('type');
    if(field.nullable!==column.nullable)differences.push('nullability');
    if(!!field.primary_key!==!!column.primary_key)differences.push('primary_key');
    if(column.references){
     const target=config.mappings[column.references]?.model;
     if(!target||field.target!==target)differences.push('foreign_key_target');
    }else if(field.target)differences.push('unexpected_foreign_key');
   }
   if(differences.length)counts.candidate_columns_with_differences++;
   return {name:column.name,contract_type:column.type,contract_nullable:column.nullable,
    contract_references:column.references||null,status,model:model?.model||null,
    backend_column:field?.column||null,backend_type:field?.type||null,backend_nullable:field?.nullable??null,
    backend_target:field?.target||null,reason:explicit?.reason||null,differences,parity_verified:false};
  });
  rows.push({name,batch,domain:table.domain,purpose:table.purpose||null,
   model:model?.model||null,backend_table:model?.table||null,physical_table_match:model?.table===name,
   mapping_reason:mapping.reason||null,storage_candidates:mapping.storage_candidates||[],columns});
 }
 const usage=new Map();
 for(const row of rows)if(row.model){const names=usage.get(row.model)||[];names.push(row.name);usage.set(row.model,names);}
 const shared_adapter_models=[...usage].filter(([,names])=>names.length>1).map(([model,contract_tables])=>({model,contract_tables}));
 return {schema_version:1,contract_version:schema.version,shared_adapter_models,scope:'Applicant schema source reconciliation; explicit candidate mappings only',
  production_acceptance:'not_verified',runtime_security:'not_verified',constraints_and_policies:'not_compared',
  counts,batches,tables:rows,outside_scope:[...tables.keys()].filter(name=>!membership.has(name))};
}
module.exports=reconcile;
if(require.main===module){
 const fs=require('node:fs');
 const [contract,inventory,config,output]=process.argv.slice(2);
 if(!output)throw Error('Usage: node scripts/audit_applicant_schema.cjs schema.json inventory.json mapping.json output.json');
 const read=path=>JSON.parse(fs.readFileSync(path,'utf8'));
 fs.writeFileSync(output,JSON.stringify(reconcile(read(contract),read(inventory),read(config)),null,2)+'\n');
}
