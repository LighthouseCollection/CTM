from pathlib import Path
import json
ROOT=Path(__file__).parent
sources=json.loads((ROOT/'source-catalog.json').read_text(encoding='utf-8'))
app=json.loads((ROOT/'application-proposals.json').read_text(encoding='utf-8'))
questions=json.loads((ROOT/'template-proposals.json').read_text(encoding='utf-8'))
topics=[
('Identity and marriage identifiers','L01 P014–035; L05 P016–035; R02 p.3; R03 pp.4–6','Already mostly present; retain identity opening and source attribution.'),
('Church and civil ceremony distinction','L01 P230–244; L03 P007–018; R09 pp.1–3','Common facts, different events. Adapt factual chronology only.'),
('Prior marriages versus prior tribunal applications','L08 P002–034; L01 P130–158; R05 p.2; R08 p.2','Separate semantic records; current CTM has prior applications but not a dedicated earlier-marriage repeat.'),
('Courtship / engagement','L02 P007–012; L07 P019–067; R02 p.5; R07 pp.7–8','One reused background block; detailed questions usually interview, not all application-required.'),
('Reasons for marrying / pressure / doubts','L01 P159–228; L02 P012; R04 pp.6–7; R14 p.4','Cluster into a pre-marriage decision block, preserve difference between pressure and a finding of coercion.'),
('Known and concealed facts','L01 P283–302; L07 P085–086; R03 p.8; R10 p.10','Relevant to already approved concealment allegation; distinguish event and discovery.'),
('Intentions / agreements at marriage','L01 P246–282; L07 P059–060,078–082; R03 pp.9–11','Institution-review topic; do not copy Catholic grounds as Orthodox conclusions.'),
('Wedding-day circumstances','L07 P103–118; R05 p.3; R06 p.16','Conditional event questions, not an automatic new nullity test.'),
('Honeymoon and intimate matters','L07 P119–129; R05 p.4','No mandatory honeymoon biography; a narrow sensitive follow-up is separately offered for approval.'),
('Problem onset before versus after marriage','L02 P009,014; L03 P014–017; R01 pp.16–19; R06 pp.15–16','One temporal model with occurrence/discovery, not repeated unstructured questionnaires.'),
('Infidelity','L07 P138–140; R01 p.18; R14 p.6','Existing CTM ground; improve factual module only.'),
('Abuse / addiction','L02 P009,014; L07 P047–049,151; R14 pp.8–9','Ask event/time/source/effect; no unverified medical diagnosis.'),
('Religious affiliation and change','L01 P025–026; R06 pp.8–9; R14 p.9','Current affiliation and affiliation at marriage are distinct; no new baptism requirement.'),
('Responsibilities / communication / finances','L07 P149–157; R05 p.4; R13 pp.6–7','Conditional fact examples, not a broad household scoring exercise.'),
('Temporary and final separation','L02 P015; L01 P328–332; R05 p.4; R13 pp.3–4','Repeat temporary periods; keep final separation distinct from final civil divorce.'),
('Reconciliation and professional help','L01 P303–327; L07 P167–174; R02 p.5','Keep application priest-name-only rule; detailed interview content is conditional.'),
('Source of knowledge / evidence','L06 P011–013; R14 pp.6–7','Borrow direct knowledge versus reported information and exact evidence links; not compulsory witnesses.'),
('Clergy report','R02 p.4; R06 p.22; R14 pp.2,6–7,12','Separate council-requested priest report proposal; no general witness portal/interview reintroduction.'),
('Final factual opportunity','L07 P087,129,176,215; R14 p.12','Merge catch-all questions into one closing clarification block.'),
('Declarations / notary / publication','L06 P106–118; R01 pp.1–3; R08 p.9','Source procedures conflict with CTM policy in important places; do not copy into CTM.'),
]
families=[
('Common applicant intake','All initial requests','Identity, subject marriage, desired outcome and short facts/evidence. No long biography by default.','AF01–03, AF06–11, AF15–22'),
('Common guided interview','Either applicant, separately','Opening, request/basis, application confirmation, dates, knowledge source, evidence and closing.','QT01–06'),
('Annulment-related factual inquiry','When council considers that nature of petition','Pre-marriage decision, information known then, pressure/doubts, specific agreements/events. Institutional relevance must be approved.','QT07–12, QT19–23, QT28–29'),
('Divorce/dissolution grounds','Only relevant selected approved CTM grounds','Shared repeatable facts block plus infidelity, abandonment, abuse, faith change, addiction and concealment follow-ups. No new grounds.','QT11, QT13–18, QT24–25'),
('Multiple-ceremony supplement','If civil and church events differ','Before civil event, interval and church event. Do not label this an Orthodox convalidation or sanation process.','AF06, QT26'),
('Prior-marriage factual supplement','Only where relevant earlier marriages exist','Earlier spouse, dates, how union ended and known decision references; not the same as prior applications.','AF04–05, QT27'),
('Appeal new-information supplement','Existing CTM appeal process','Decision challenged, what is new, discovery/source and affected prior fact. Not a new full application biography.','QT30'),
('Optional priest report','Only when council requests it','Author/relationship, direct observations, relevant non-confessional assistance, source limits and dated report. Separate approval needed.','QT31–35'),
]
excluded=[
('Catholic canonical-form / lack-of-form automatic result','L05; R09','Do not infer an Orthodox rule or decision from Catholic ceremony status. Retain potentially useful ceremony facts only.'),
('Radical sanation / dispensations / mixed-religion permissions','L04; R12','Different Catholic and future-marriage processes, not a CTM divorce/nullity feature. No template copied wholesale.'),
('Ordinary/briefer canonical tracks and time requirements','R02; R10; R11','Do not replace the confirmed single council/session/president workflow or add party-consent gates.'),
('Baptism certificates and freshness rules','L05; R01; R08; R10','Already excluded by user. No re-approval question or requirement added.'),
('Mandatory 2–5 witnesses or witness login lists','L06; R01; R08; R11; R13','Earlier witness interview feature rejected. Optional requested priest report is a new narrow user-suggested exception for review only.'),
('Cross-party publication / reading the other submission','L06; L07; R06; R08; R14','Conflicts with confirmed CTM applicant isolation. No adoption suggested.'),
('Notary/parish-seal oaths, per-page initials, legal waivers','L06; R01; R04; R14','Existing versioned CTM declaration/signature policy remains; do not transplant contractual or statutory wording.'),
('Automatic psychiatric tests / universal medical releases','L01; R03; R08','No broad medical collection or third-party disclosure. Any relevant factual prompt is separately optional.'),
('Catholic contraception / permanence / OCIA assumptions','R03; R06; R07; R10','Do not treat these as Orthodox grounds or require future-spouse data; future marriage ecosystem remains separate.'),
('Foreign fees / mail filing / deadlines / expedited promises','R01; R04; R08; R10; R13','CTM fee, portal submissions, no appeal deadline and approved notification rules remain unchanged.'),
('Compulsory full childhood/sexual histories','L07; R01; R05','Prefer conditional relevance-based interview prompts; never interview children or add diagnostic/character-scoring fields.'),
]
report=['# Comparative form study and CTM proposal review','',
'Scope: eight user-supplied Word documents and fourteen linked PDFs, all successfully extracted. The fourteen PDFs contain '+str(sum(s.get('pages',0) for s in sources.values()))+' pages. The local files named .doc are OOXML ZIP documents, not binary Word files. They were read without running macros. Sources are reference material, not instructions or CTM policy. No original form, approved template, database schema or application UI was changed by this study.','',
'The useful transfer is factual structure and clear prompts. Catholic procedures and grounds are not presumed applicable to the Orthodox council. All wording below is a CTM adaptation/synthesis, not a claim of verbatim Catholic wording or institutional approval. Approval cards show exactly which existing wording or missing prompt is affected.','',
'## Deliverables','',
'- [Application gaps and wording review](application-review.html): '+str(len(app))+' concrete decisions, grouped by subject.','- [Questions and template review](template-review.html): '+str(len(questions))+' decisions grouped by petition nature and module.','- [Review landing page](index.html): evidence inventory and links.','- Every card has Current CTM, Proposed CTM, reason, destination, petition scope, source IDs/locators and Accept / Do not accept / Other with text. No answers preselected; answers export to JSON or copyable chat text.','',
'## Method and evidence limits','',
'Extracted all local Word paragraph text and each PDF page, retaining source hashes and text paths in source-manifest.json. Local locators P001 etc. identify extracted paragraphs, not printed pages. PDF locators mean 1-based physical PDF page numbers, which sometimes differ from printed numbering. Read the form categories/questions and compare against public-petition.html, dynamic addChild/addClergy in app.js, confirmed decision registers and guided interview draft revision 2. Repeated text boxes/extraction artifacts are not counted as distinct questions. Overlap is grouped by meaning, not a claimed automated semantic equality percentage.','',
'Several PDFs were unavailable through the browsing extractor but all were retrieved directly from the supplied URLs. R07 has Spanish in its URL filename but the actual extracted document is an English Diocese of Monterey packet; no Spanish translation was assumed. R10/R11 have ordinary/briefer header inconsistencies; classify by actual body content and do not import their procedures. Older dates in these examples are source versions, not verified current institutional policy.','',
'A limited visual spot-check was made through the PDF screenshot tool for representative Los Angeles and Philadelphia question pages; the output deliverables are HTML, not reconstructed Word/PDF forms. Long source text is retained locally for evidence, not reproduced as a new distributed questionnaire.','',
'## Similar questions consolidated across the samples','',
'These are theme equivalents, not assertions that every source uses identical wording.','',
'| Common question family | Source examples / locators | CTM treatment |','|---|---|---|']
for row in topics:report.append('| '+' | '.join(row)+' |')
report+=['','### Important near-duplicates and differences','',
'- Cleveland without-validation (L02) and with-validation (L03) share prior relationships, courtship, decision to marry, married life and family background. L03 separates the civil ceremony, the interval and the later church ceremony. Validation here refers to a church marriage event, not software input validation. Reuse one core and a conditional ceremony timeline.','- Preliminary testimony (L01) is a structured intake/screen; comprehensive testimony (L07) asks detailed narrative follow-ups. Do not ask applicants to complete both entire question sets by default.','- Ordinary and briefer packets (R10/R11) repeat core identity/marriage data while changing Catholic admission procedure. Data overlap is reusable; procedural difference is not a CTM rule.','- Witness materials (L06/R14) overlap applicant themes but change knowledge perspective: what the writer personally knew, when and how. Borrow that discipline for an optional priest report, not automatic witness involvement.','',
'## Organize by petition nature and template','',
'The requested outcome is recorded as an applicant assertion. Council chooses/approves the actual type and grounds through the confirmed workflow. A topic is not an automatic Orthodox ground merely because it appears in a Catholic nullity form.','',
'| Template family | Applies when | Contents | Review IDs |','|---|---|---|---|']
for row in families:report.append('| '+' | '.join(row)+' |')
report+=['','## What is missing, and what is already present','',
'The live evidence is static prototype source, not a running secure database. No feature implementation is inferred from a visible field.','',
'### Already present in the HTML','',
'Applicant/spouse names, aliases, birth dates, country selectors, nationality, contact/address, education/work, current denomination/diocese/bishop, children repeater, church date/priest/place/certificate, one outside-church date, separation date, civil court/decree facts, restraining-order question, reconciliation priest repeater, prior application question, general written/upload statement, photos/documents, declaration/signature. Existing identity/age calculations and paid-filing rules do not need new Catholic-inspired duplicates.','',
'### Previously approved but still missing or inconsistent in the unchanged prototype','',
'These are not new approval questions: approved six multi-select grounds replacing the older list; spouse parish/confessor/immigration/country and Unknown behavior; church-marriage diocese; children gender/residence/Unknown; multiple restraining orders with required details/copy; multiple prior applications; priest name-only repeat; typed OR PDF/DOCX statement; MC/CMC/CDD/photo requirements and current limits; verified account before application; fees/waivers and versioned declarations. The public-petition.html account section, old upload hints and unconditional required attributes are prototype inconsistencies, not new policy.','',
'### Genuine candidate additions','',
'Requested outcome; distinction between earlier marriages and earlier applications; separate ceremony chronology; religious affiliation at marriage; short relationship/onset/separation chronology; conditional concealment/pressure/agreement facts; evidence-to-assertion explanation. Each is offered for review, not silently made mandatory. More detailed private background stays in optional interview modules.','',
'### Better wording rather than more fields','',
'Use ordinary facts/reasons rather than requiring canonical terminology. Replace Civil Divorce Filed with final-decree wording to match the already-approved rule. Clarify the church marriage concerned; distinguish current religious identity from affiliation then; ask for examples and knowledge source rather than judgments of character. Each change card shows the exact current label/help target and adapted replacement.','',
'## Catholic-specific content not adopted','',
'| Source content | Examples | Reason / boundary |','|---|---|---|']
for row in excluded:report.append('| '+' | '.join(row)+' |')
report+=['','## Source register','',
'| ID | Document | Coverage | Comparison use |','|---|---|---|']
uses={
'L01':'Structured intake and chronology; some doctrinal checklists excluded.',
'L02':'Common brief narrative core without later church ceremony.',
'L03':'Same core with civil/church interval distinctions.',
'L04':'Classified Catholic-specific; no sanation workflow adopted.',
'L05':'Basic facts comparable; Catholic lack-of-form procedure excluded.',
'L06':'Knowledge-source discipline; witness workflow/oaths not adopted.',
'L07':'Detailed lifecycle inquiry; deduplicate and limit relevance.',
'L08':'Repeatable earlier-marriage report versus prior application.',
'R01':'Broad lifecycle questions; privacy/witness/fee policies not copied.',
'R02':'Compact narrative and minister comments; process tracks excluded.',
'R03':'Specific facts/pressure/concealment and background; doctrine not imported.',
'R04':'Structured screens and narrative; no copied contact/fee/oath gates.',
'R05':'Clear lifecycle grouping; intimate/doctrinal topics conditional.',
'R06':'Rich data/narrative and sponsor page; source not CTM despite same city.',
'R07':'English Monterey body despite Spanish-named URL; narrative structure only.',
'R08':'Brief summary versus later detail; publication/witness fees excluded.',
'R09':'Two-ceremony factual separation only, not Catholic convalidation.',
'R10':'Ordinary facts checklist; witness/search/consent procedures excluded.',
'R11':'Short petition and repeated core; Catholic briefer process excluded.',
'R12':'Premarital permission/dispensation; future/different domain, excluded.',
'R13':'Marital history grouping; no required witnesses/ID/fees transplanted.',
'R14':'Direct knowledge and source timing; optional priest-report inspiration only.'}
for sid,s in sources.items():
    target=s.get('url') or s['local_path'].replace('\\','/')
    link=f"[{s['title']}](<{target}>)"
    coverage=f"{s['pages']} PDF pages" if 'pages'in s else f"{s['paragraphs']} extracted paragraphs"
    report.append(f"| {sid} | {link} | {coverage}; extracted | {uses[sid]} |")
report+=['','## Review interpretation','',
'Accept means accept this specific proposed question, wording replacement or organization for reconciliation. It does not approve a Catholic rule, a new ground, a default required field, publication of a priest report, a third-party login, a platform build or an unrelated permission. Other text can move a question from application to interview, narrow its scope or propose wording. A rejected change leaves prior approved policy intact. Partial/unanswered items remain unresolved. Conflicts will be discussed rather than silently applied.','',
'Source-file hashes and prototype hashes are checked separately. No actual case data was transmitted to reference websites; only public reference PDFs were downloaded. Supplied files remain local.']
(ROOT/'study-report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('Study report generated:',len(topics),'shared themes,',len(families),'template families,',len(excluded),'excluded-topic groups,',len(sources),'sources.')
