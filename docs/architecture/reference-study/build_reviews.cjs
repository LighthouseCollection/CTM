const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=__dirname,shared=path.join(root,'../questionnaire');
const sources=JSON.parse(fs.readFileSync(path.join(root,'source-catalog.json'),'utf8'));
const specs=[
 {slug:'application-review',input:'application-proposals.json',version:'ctm-reference-application-review-v1',title:'Application gaps and wording',description:'Review concrete additions and wording changes against the current CTM application. Each card shows what exists now, what would change and where it belongs.'},
 {slug:'template-review',input:'template-proposals.json',version:'ctm-reference-template-review-v1',title:'Questions and petition templates',description:'Review a common factual core, petition-specific interview modules and a separate council-requested priest report. Accept only the topics and wording you want CTM to use.'}
];
let engine=fs.readFileSync(path.join(shared,'questionnaire.js'),'utf8');engine=engine.slice(engine.indexOf('const questions ='));
engine=engine.replace("value==='yes'||value==='no'||value===null","value==='accept'||value==='reject'||value==='other'||value===null");
engine=engine.replace("['yes','no']","['accept','reject','other']");
engine=engine.replace("value==='yes'?'Yes':'No'","value==='accept'?'Accept':value==='reject'?'Do not accept':'Other'");
engine=engine.replace("()=>changed(id,'answer',value)","()=>{changed(id,'answer',value);if(value==='other')document.getElementById(`note-${id}`).focus();}");
engine=engine.replace("'Clarification / preferred alternative'","'Other / preferred wording / placement clarification'");
engine=engine.replace("'Optional — explain a No, qualify a Yes, or leave a question for discussion.'","'For Other, describe your alternative. You can move this to the interview, narrow its scope, change the wording, or qualify Accept / Do not accept.'");
engine=engine.replace("const detail=textNode('p',context,'detail');detail.id=`context-${id}`;field.append(detail);field.setAttribute('aria-describedby',detail.id);","renderProposalDetails(field,id,context);");
engine=engine.replace("'CTM architecture questionnaire'",'REVIEW_TITLE');
engine=engine.replace('clarifications qualify Yes/No choices.','clarifications qualify Accept / Do not accept / Other. Reject means do not accept the change, not rejection of a case.');
engine=engine.replace('CTM-architecture-answers-${','CTM-${REVIEW_SLUG}-answers-${');
engine=engine.replace("'Proposed CTM architecture decisions for review; not applied automatically'","'Source-linked CTM wording/template proposals. Accept is a review response, not institutional approval of Catholic rules. Nothing applied automatically.'");
engine=engine.replace("answers:questions.map(q=>({...q,answer:","answers:questions.map(q=>({...q,proposal:PROPOSALS[q.id],answer:");
const detailScript=`
function renderProposalDetails(field,id,context){
 const p=PROPOSALS[id];
 const detail=textNode('p',p.status+' · '+p.nature,'detail');detail.id='context-'+id;field.append(detail);field.setAttribute('aria-describedby',detail.id);
 const dest=textNode('p','Placement: '+p.destination+' · Action: '+p.action,'placement');field.append(dest);
 const pair=document.createElement('div');pair.className='comparison';
 for(const [heading,value,style] of [['Current CTM / missing prompt',p.current,'current'],['Proposed CTM wording / structure',p.proposed,'proposed']]){
  const box=document.createElement('div');box.className=style;box.append(textNode('h3',heading),textNode('p',value));pair.append(box);
 }
 field.append(pair,textNode('p',p.reason,'reason'));
 const evidence=document.createElement('div');evidence.className='source-links';evidence.append(textNode('strong','Reference ideas (adapted, not quoted): '));
 for(const ref of p.sources){const s=SOURCES[ref.id];const link=textNode('a',ref.id+' · '+s.title+' · '+ref.locator);let href=s.url||('file:///'+s.local_path.replaceAll('\\\\','/'));const page=ref.locator.match(/PDF pp?\\.(\\d+)/);if(page&&s.url)href+='#page='+page[1];link.href=href;link.target='_blank';link.rel='noopener';evidence.append(link,document.createTextNode(' '));}
 field.append(evidence);
}
`;
const extraCss=`
.comparison{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:14px 0}.comparison>div{padding:16px;background:#ebe9e1;border:1px solid var(--line)}.comparison .proposed{background:#e6eee7;border-color:#9eb6a6}.comparison h3{font:700 12px/1.5 'Segoe UI',sans-serif;letter-spacing:.03em;text-transform:uppercase;margin:0 0 9px}.comparison p{margin:0;font-size:16px;line-height:1.6}.placement{font-size:13px;color:var(--muted);margin:0}.reason{font-size:14px;margin:12px 0}.source-links{font-size:12px;line-height:1.7;margin:12px 0 18px}.source-links a{display:block;color:#20554f;text-decoration:underline;text-underline-offset:2px}.choices{flex-wrap:wrap}.baseline{border-top:1px solid var(--line);padding:14px 0;font-size:14px}.review-links{display:flex;gap:18px;flex-wrap:wrap}.review-links a{color:var(--accent)}.choices .choice{min-width:110px}.status-note{color:var(--accent);font-size:13px}
@media(max-width:680px){.comparison{grid-template-columns:1fr}}@media print{.comparison{grid-template-columns:1fr 1fr}.review-links{display:none}}
`;
const css=fs.readFileSync(path.join(shared,'questionnaire.css'),'utf8')+extraCss;
const baseHtml=fs.readFileSync(path.join(shared,'index.html'),'utf8');
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
for(const spec of specs){
 const data=JSON.parse(fs.readFileSync(path.join(root,spec.input),'utf8'));
 const groups=new Map();for(const p of data){if(!groups.has(p.category))groups.set(p.category,[]);groups.get(p.category).push([p.id,`Accept this ${p.action.toLowerCase()}?`,p.status]);}
 const sections=Array.from(groups,([title,rows],i)=>['review-'+i,title,'Review each change individually; use Other to change its wording, scope or placement.',rows]);
 const proposals=Object.fromEntries(data.map(p=>[p.id,p]));
 const js=`'use strict';\nconst VERSION=${JSON.stringify(spec.version)};const STORAGE_KEY=VERSION;const REVIEW_TITLE=${JSON.stringify(spec.title)};const REVIEW_SLUG=${JSON.stringify(spec.slug)};\nconst PROPOSALS=${JSON.stringify(proposals)};\nconst SOURCES=${JSON.stringify(sources)};\nconst sections=${JSON.stringify(sections)};\n${detailScript}\n${engine}`;
 new vm.Script(js);
 const ctx=vm.createContext({setTimeout,clearTimeout});vm.runInContext(js.split('try{const stored=')[0],ctx);
 const run=c=>vm.runInContext(c,ctx);
 assert.equal(run('questions.length'),data.length);assert.equal(run('new Set(questions.map(q=>q.id)).size'),data.length);assert(run('payload().answers.every(a=>a.answer===null)'));
 run('state.answers[questions[0].id]={answer:"accept",clarification:"Keep optional."};state.answers[questions[1].id]={answer:"reject",clarification:"Keep existing wording."};state.answers[questions[2].id]={answer:"other",clarification:"Interview only — العربية <script>plain text</script>"};');
 ctx.saved=JSON.parse(run('JSON.stringify(payload())'));run('state=normalize(saved)');assert.equal(run('state.answers[questions[2].id].answer'),'other');assert.match(run('chatText()'),/REJECT/);assert(ctx.saved.answers[0].proposal.current);
 assert.throws(()=>run('normalize({questionnaireVersion:VERSION,answers:[{id:questions[0].id,answer:"yes",clarification:""}]})'));
 const title=esc(spec.title);
 let html=baseHtml.replace('<title>CTM · Architecture decisions</title>',`<title>CTM · ${title}</title>`)
 .replace('<link rel="stylesheet" href="questionnaire.css">',()=>`<style>${css}</style>`)
 .replace('<script src="questionnaire.js" defer></script>','')
 .replace('CTM / Architecture review / 20 October 2026','CTM / Catholic sample comparison / Proposal review')
 .replace('<h1>The remaining decisions.</h1>',`<h1>${title}.</h1>`)
 .replace(/<p class="intro">[\s\S]*?<\/p>/,()=>`<p class="intro">${esc(spec.description)}</p><p class="baseline"><strong>${data.length} proposals · No preselected answers.</strong> Choose Accept, Do not accept, or Other and explain. These are CTM adaptations—not verbatim Catholic questions or approved Orthodox rules. New fields are not automatically mandatory. Prior CTM decisions remain in force.</p><p class="review-links"><a href="index.html">Study and source overview</a><a href="${spec.slug==='application-review'?'template-review':'application-review'}.html">${spec.slug==='application-review'?'Question and template review':'Application review'}</a><a href="study-report.md">Detailed comparison report</a></p>`)
 .replace('Your confirmed decisions stay in place; applicant-portal design, infrastructure and provider selection are reserved for later.','Existing privacy, fees, grounds, document rules and history stay in place. No CTM application is being built.')
 .replace('For a No answer, use the clarification box to describe your preferred rule.','Use Other to enter your own wording or move a topic to another template. Do not accept leaves the existing rule unchanged.')
 .replace('I will reconcile your choices and clarifications before updating the architecture.','I will reconcile these choices and clarifications before changing CTM wording or requirements. Accept does not authorize unrelated Catholic procedures.')
 .replace('Enable it or use the companion questions.md file.','Enable it or use the JSON proposal catalog and the detailed comparison report.')
 .replace('</body>',()=>`<script>\n${js}\n</script>\n</body>`);
 fs.writeFileSync(path.join(root,spec.slug+'.html'),html);
 console.log(`PASS: ${spec.slug}: ${data.length} unanswered proposals; Accept/Reject/Other transfer round-trip; source/current/proposed metadata included.`);
}
const sourceRows=Object.values(sources).map(s=>{
 const href=s.url||('file:///'+s.local_path.replaceAll('\\','/'));const size=s.pages?`${s.pages} PDF pages`:`${s.paragraphs} extracted paragraphs`;
 return `<tr><td>${s.id}</td><td><a href="${esc(href)}" target="_blank" rel="noopener">${esc(s.title)}</a></td><td>${size}</td><td>${esc(s.status)}</td></tr>`;
}).join('\n');
const home=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CTM reference form study</title><style>${css}main{display:block}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}a{color:var(--accent)}.review-entry{padding:25px 0;border-bottom:1px solid var(--line)}.review-entry h2{margin-top:0}</style><header><p class="eyebrow">CTM / 22 reference documents / Architecture only</p><h1>Borrow the useful questions.</h1><p class="intro">Compare the Catholic samples with CTM. Keep the factual structure that helps your council; review every proposed addition or wording change.</p><p><strong>Eight supplied Word files and fourteen linked PDFs (${Object.values(sources).reduce((n,s)=>n+(s.pages||0),0)} pages) were extracted.</strong> None of their instructions has been adopted as CTM policy. All current prototype files remain unchanged.</p></header><main><section class="review-entry"><h2><a href="application-review.html">1. Application gaps and wording</a></h2><p>22 concrete proposals. Current CTM wording or missing field → suggested wording → placement → source evidence.</p></section><section class="review-entry"><h2><a href="template-review.html">2. Questions organized by petition and template</a></h2><p>36 proposals: common core, annulment-related factual inquiry, six approved divorce grounds, conditional context, ceremony/prior-marriage supplements, appeals and an optional requested priest report.</p></section><section class="review-entry"><h2><a href="study-report.md">3. Detailed comparison report</a></h2><p>20 shared question families, eight template families, actual application gaps, already-approved changes missing from the prototype, and eleven Catholic-specific topic groups not adopted.</p></section><h2>How to return decisions</h2><p>Each review offers <strong>Accept / Do not accept / Other</strong> with a text area. Use Download answers and attach the JSON here, or Copy for chat and paste. Progress is saved separately where local browser storage is available. No network submission or automatic architecture update occurs.</p><h2>Scope boundaries</h2><p>Priest-report ideas are a new, narrow request for review; they do not create a general witness interview or login feature. No baptism requirement, Catholic canonical procedure, disclosure of one applicant’s material to the other, new fee or new grounds are imported. Sensitive topics are optional institutional-review proposals, not automatic form requirements.</p><p>Language note: the URL labeled Spanish (R07) contains an English Monterey packet. “With validation” in the Cleveland samples concerns a later church ceremony, not software form validation. Source locators use physical PDF pages or extracted Word paragraph numbers.</p><h2>Source inventory</h2><div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>Document</th><th>Coverage</th><th>Read status</th></tr></thead><tbody>${sourceRows}</tbody></table></div><p class="small">Source bytes, SHA-256 hashes and extracted text are retained locally in the study folder. Actual private CTM case data was not transmitted to source websites. Word documents were read without running macros.</p></main><footer>Review artifacts only · No CTM application/database changes</footer></html>`;
fs.writeFileSync(path.join(root,'index.html'),home.replace('22 concrete proposals.',`${JSON.parse(fs.readFileSync(path.join(root,'application-proposals.json'),'utf8')).length} concrete proposals.`));
