/* Technical candidate audit only. Never publishes or approves institutional text. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function audit(application){
 const findings=[],q=application?.questionnaire;
 const missing=(value,p)=>{if(typeof value!=='string'||!value.trim())findings.push({path:p,code:'missing_bilingual_text',severity:'error'});};
 for(const lang of ['en','ar'])missing(q?.[`declaration_${lang}`],`/questionnaire/declaration_${lang}`);
 const walk=(fields,p,depth=0)=>{
  if(!Array.isArray(fields))return;
  fields.forEach((field,index)=>{
   const at=`${p}/${index}`;
   for(const lang of ['en','ar'])missing(field?.[`label_${lang}`],`${at}/label_${lang}`);
   if(field?.item_fields!==undefined){
    if(depth>0)findings.push({path:`${at}/item_fields`,code:'unsupported_nested_repeat',severity:'error'});
    walk(field.item_fields,`${at}/item_fields`,depth+1);
   }
   if(Array.isArray(field?.choices))field.choices.forEach((choice,i)=>{
    const item=typeof choice==='string'?field.choice_labels?.[choice]:choice;
    const pointer=typeof choice==='string'?`${at}/choice_labels/${choice.replace(/~/g,'~0').replace(/\//g,'~1')}`:`${at}/choices/${i}`;
    for(const lang of ['en','ar'])missing(item?.[`label_${lang}`],`${pointer}/label_${lang}`);
   });
  });
 };
 walk(q?.definition?.fields,'/questionnaire/definition/fields');
 const context={window:{},structuredClone};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/ctm/applicant.js'),'utf8'),context);
 if(context.window.CTMApplicant.definitionProblem(application))findings.push({path:'/questionnaire',code:'unsupported_or_unpublished_definition',severity:'error'});
 return {schema_version:1,scope:'Bound applicant questionnaire technical readiness only',
  questionnaire_id:typeof q?.id==='string'?q.id:null,questionnaire_version:q?.version??null,
  institutional_approval:'not_verified',technical_complete:findings.length===0,findings};
}
module.exports=audit;
if(require.main===module){
 const [input,output]=process.argv.slice(2);
 if(!input)throw Error('Usage: node scripts/audit_applicant_forms.cjs application-projection.json [report.json]');
 const report=audit(JSON.parse(fs.readFileSync(input,'utf8'))),json=JSON.stringify(report,null,2)+'\n';
 if(output)fs.writeFileSync(output,json);else process.stdout.write(json);
 process.exitCode=report.technical_complete?0:1;
}
