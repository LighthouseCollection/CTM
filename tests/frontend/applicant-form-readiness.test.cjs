const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path='scripts/audit_applicant_forms.cjs';
const audit=fs.existsSync(path)?require('../../scripts/audit_applicant_forms.cjs'):()=>null;
const fixture=()=>({questionnaire:{id:'bound-form',version:1,published:true,declaration_en:'Declaration',declaration_ar:'الإقرار',
 definition:{fields:[{code:'children',type:'list',label_en:'Children',label_ar:'الأطفال',item_fields:[
 {code:'name',type:'text',label_en:'Name',label_ar:'الاسم'}]}]}}});
test('form readiness reports missing repeat/choice translations with exact source pointers',()=>{
 const d=fixture();d.questionnaire.definition.fields[0].item_fields[0].label_ar='';
 const report=audit(d);assert.equal(report.technical_complete,false);
 assert.ok(report.findings.some(f=>f.path==='/questionnaire/definition/fields/0/item_fields/0/label_ar'));
 assert.equal(report.institutional_approval,'not_verified');
});
test('technical readiness does not claim institutional approval and rejects nested repeats',()=>{
 const d=fixture();assert.equal(audit(d).technical_complete,true);
 d.questionnaire.definition.fields[0].item_fields[0].item_fields=[];
 assert.equal(audit(d).technical_complete,false);
 d.questionnaire.declaration_ar='';assert.ok(audit(d).findings.some(f=>f.path==='/questionnaire/declaration_ar'));
});
