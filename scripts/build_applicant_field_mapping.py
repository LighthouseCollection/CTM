"""Reproduce applicant requirement mapping against a pinned source-only candidate.
No form publication or database mutation. Labels remain source evidence.
"""
import ast,csv,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/implementation/applicant/field-mapping'
REF='104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc'
def source(path):
    return subprocess.check_output(['git','show',f'{REF}:{path}'],cwd=ROOT).decode('utf-8')
def build():
    OUT.mkdir(exist_ok=True)
    schema=json.loads(source('docs/architecture/build-spec/schema.json'))
    tables={t['name']:t for t in schema['tables']}
    seed_tree=ast.parse(source('tribunal/management/commands/seed_reference.py'))
    seed_assignment=next(n for n in ast.walk(seed_tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fields' for t in n.targets))
    seed_fields=ast.literal_eval(seed_assignment.value.generators[0].iter)
    assert [x[0] for x in seed_fields]==['first_name','last_name','birth_date','gender','marriage_date','grounds']
    rows=[]
    def group(prefix,fields,table,line,policy):
        assert table in tables,table
        for field in fields.split():
            key=prefix+'.'+field if prefix else field
            binding={'self.first_name':'first_name','self.last_name':'last_name','self.dob':'birth_date','self.gender':'gender','marriage.church_date':'marriage_date','grounds':'grounds'}.get(key)
            rows.append({'semantic_field':key,'source':'docs/architecture/prototype-to-data-map.md','line':line,'target_table':table,'adapter':'AnswerRevision.answers (JSON); semantic table equivalence unverified','seed_binding':binding or '', 'seed_status':'unpublished minimal field' if binding else 'absent from reference petition seed','english_label':'not supplied in reference petition seed','arabic_label':'not supplied in reference petition seed','validation_and_unknown_policy':policy,'dependency':'backend versioned definition/binding plus institutional bilingual content review; normalized mapping backend-owned'})
    group('self','first_name middle_name last_name other_names','application_person_assertions',12,'English first/last required; retain source assertions, no live-profile rewrite')
    group('self','dob gender birth_country nationality','application_person_assertions',13,'DOB/date and gender; no town-of-birth addition; exact approved choices required')
    group('self','education graduation_year occupation','application_person_assertions',14,'Preserve current source types; graduation year four digits or approved Unknown')
    group('self.address','street city region postal country','application_person_assertions',15,'Structured international address; requiredness must be frozen by version')
    group('self','immigration_status residing_with','application_person_assertions',16,'Catalog and Other/Unknown only as approved, not a global Unknown fallback')
    group('self','email mobile','application_person_assertions',17,'Submitted contact is distinct from authenticated/verified account email')
    group('self','denomination bishop diocese parish confessor','application_person_assertions',18,'AF07 affiliation before knowing each other; Coptic skips denomination text')
    group('spouse','aware_of_application','application_person_assertions',19,'Yes/no/Unknown assertion; not notification or consent evidence')
    group('spouse','first_name middle_name last_name aliases dob gender birth_country nationality','application_person_assertions',20,'Independent applicant assertion; never silently update spouse identity')
    group('spouse.address','street city region postal','application_person_assertions',21,'Unknown permitted; preserve original source')
    group('spouse','residence_country','application_person_assertions',21,'Explicit Unknown permitted; no inferred residence')
    group('spouse','email mobile education graduation_year occupation','application_person_assertions',22,'Conditional availability; not verified spouse account/contact')
    group('spouse','denomination diocese bishop parish confessor immigration_status','application_person_assertions',23,'Unknown permitted for approved spouse fields; no spouse residing_with question')
    group('children[]','first_name last_name dob','application_children',24,'Stable entry UUID retained across edits/reordering; names/DOB kept as assertions')
    group('children[]','gender lives_with','application_children',25,'Required per reported child; explicit Unknown accepted')
    group('marriage','outside_coptic outside_denomination outside_date','application_marriage_assertions',26,'Conditional on outside-Coptic marriage; preserve approved branch wording')
    group('marriage','church_date officiating_priest church_name location','application_marriage_assertions',27,'Exact marriage date; directory only when verified, otherwise source text')
    group('marriage','certificate_number certificate_issued_date','application_marriage_assertions',28,'Certificate number/date separate from immutable document evidence')
    group('marriage','diocese','application_marriage_assertions',29,'Explicit Unknown allowed')
    group('separation','marital_status date','application_separation_assertions',31,'Keep separation distinct from final civil divorce')
    group('separation','initiated_by','application_separation_assertions',32,'Applicant/spouse/both/Unknown relative to filing author')
    group('civil_divorce','filed divorce_date court court_location case_number','application_separation_assertions',33,'Existing approved final divorce date/court/reference and CDD; do not add conflicting extra finality questions (build-spec80/AF11 reconciled)')
    group('restraining_orders[]','order_date expiry_date named_person','application_restraining_orders',35,'Repeating source orders with stable UUID and distinct dates')
    group('restraining_orders[]','court case_number status','application_restraining_orders',36,'Actual required values; no Unknown; each reported order requires its own copy')
    group('counseling','attempted','application_separation_assertions',37,'AF20 asks priest-assisted reconciliation and priest name')
    group('counseling_priests[]','priest_name','application_prior_records',37,'Priest name only; no role/parish/contact/date/outcome expansion')
    group('prior_application','applied','application_answers',39,'Conditional gate for repeated prior applications; retain each date/council/outcome')
    group('prior_applications[]','date council_or_diocese outcome','application_prior_records',39,'Repeatable approved prior applications; no replacement AF21 label')
    group('prior_marriages[]','spouse_name ecclesiastical_permit','application_prior_records',39,'AF04 narrow override, AF05 known spouse history with Unknown allowed; no full-history expansion')
    group('summary','narrative','application_answers',40,'Nonblank typed statement OR accepted PDF/Word; AF02/03/16 guidance, not compulsory duplicate narrative questions')
    group('','grounds','application_selected_grounds',41,'Multiple approved grounds, separate from findings; bilingual catalog publication required')
    group('marriage','blood_relationship','application_marriage_assertions',29,'AF23 blood relationship only, not adoption; factual answer not canonical determination')
    # Specific source authority for additions not fully enumerated by prototype map.
    for row in rows:
        if row['semantic_field'].startswith('prior_marriages[]') or row['semantic_field']=='marriage.blood_relationship':
            row['source']='docs/architecture/CTM-reference-review-decisions.md'
            row['line']=12 if row['semantic_field'].startswith('prior_marriages[]') else 31
    decisions=[]
    for n,line in enumerate(source('docs/architecture/CTM-reference-review-decisions.md').splitlines(),1):
        m=re.match(r'\| (AF\d+) \| (.*?) \| (.*?) \|',line)
        if m:decisions.append({'id':m[1],'disposition':m[2],'treatment':m[3],'source_line':n})
    repeaters=[]
    for prefix in ['children[]','restraining_orders[]','prior_applications[]','prior_marriages[]','counseling_priests[]']:
        repeaters.append({'collection':prefix,'fields':[r['semantic_field'] for r in rows if r['semantic_field'].startswith(prefix+'.')],'seed_status':'absent','frontend':'generic list/item_fields supports one-level records and generates UUID for new row; no approved bound section supplied','backend':'JSON snapshot retains supplied rows; validate_answers does not descend into item_fields; validate_petition checks only child gender/lives_with truthiness','dependency':'backend schema/validation owner and reviewed versioned question content; per-row document mapping for restraining orders/permits'})
    paths=['tribunal/management/commands/seed_reference.py','tribunal/validation.py','tribunal/services/applications.py','docs/architecture/prototype-to-data-map.md','docs/architecture/CTM-reference-review-decisions.md','docs/architecture/build-spec/schema.json','static/ctm/applicant.js','tribunal/services/configuration.py','docs/architecture/CTM-confirmed-decisions.md']
    result={'candidate_sha':REF,'scope':'source requirement mapping, not published form or normalized schema acceptance','fields':rows,'repeat_sections':repeaters,'AF_decisions':decisions,'excluded':['new requested-outcome control AF01','interview-only AF08/09/12/13/14','rejected AF06/10/15/18/19/24 expansions','spouse lives-with','town of birth','baptism certificate requirement','additional civil ceremony/finality questions without approval'],'separate_context':['account credentials: provider/account workflow, never questionnaire answers','contextual files and declarations: immutable file/attestation contracts, not text-field substitutes','59 accepted questions belong to interview/report library, not automatic applicant form population'],'counts':{'semantic_fields':len(rows),'reference_petition_fields':len(seed_fields),'mapped_seed_candidates':sum(bool(r['seed_binding']) for r in rows),'repeat_sections':len(repeaters),'AF_decisions':len(decisions)},'reference_seed':{'fields':[{'code':code,'type':kind,'published':False,'label_en':None,'label_ar':None} for code,kind in seed_fields],'scope':'six-field unpublished reference; not actual deployed configuration'},'contextual_requirements':[{'field':field,'source_line':line,'status':'contextual contract exists; full approved institution-bound acceptance pending','policy':policy} for field,line,policy in [('documents.applicant_photo',42,'PHOTO required; not government photo ID'),('documents.spouse_photo',42,'SPOUSE_PHOTO if available'),('documents.church_certificate',42,'Confirmed decisions98: MC church; backend labels MC generically and CMC church. Owner reconciliation required; do not silently relabel'),('documents.civil_certificate',42,'Confirmed decisions98: CMC civil. Backend labels CMC church; seed requires CMC in addition to base MC. Preserve both sources and resolve with backend/content owner'),('documents.civil_divorce_decree',42,'CDD finalized decree required'),('documents.restraining_order_copy',43,'RO linked to each reported stable order context'),('documents.ecclesiastical_permit',12,'AF04 per prior marriage permit; backend context/category mapping requires confirmation'),('documents.petition_statement',40,'Nonblank typed statement OR PET PDF/Word'),('consent.accepted',44,'Bound declaration text/version and final snapshot digest'),('signature.name_date_bytes',45,'Signed name/date and retained bytes; server receipt distinct')]],'source_sha256':{p:hashlib.sha256(source(p).encode()).hexdigest() for p in paths}}
    result['counts']['contextual_requirements']=len(result['contextual_requirements'])
    (OUT/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (OUT/'fields.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(result['counts']))
if __name__=='__main__':build()
