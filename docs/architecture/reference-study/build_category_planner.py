from pathlib import Path
import json,html
ROOT=Path(__file__).parent
categories=[]
def cat(code,title,refs,scope,questions,pending=False):
    categories.append(dict(id=code,title=title,proposalRefs=refs,scope=scope,pending=pending,questions=[dict(id=f'{code}-{i:02}',text=q) for i,q in enumerate(questions,1)]))
cat('DEC','Decision to marry',['QT07','QT12'],'Facts surrounding the decision; no canonical conclusion',[
'How did the decision to marry arise, and what were your reasons at that time?',
'What did you understand your responsibilities would be, and what had you actually discussed together?',
'Was a specific promise, agreement or condition important to your decision? Identify what was said, by whom and when.',
'Did what you understood differ from what you later learned? Identify the fact, the discovery and supporting information.'])
cat('CHD','Children',['QT07','QT21','QT29'],'Relevant agreements and lived facts; children never interviewed',[
'Before marriage, what did you discuss or agree about having children?',
'Were there differences about whether or when to have children? What was actually communicated?',
'Did those expectations change or did you learn something different later? When and how?',
'If relevant to this petition, describe a specific parenting responsibility or disagreement and what happened.',
'What facts or documents support this account? Do not include unrelated private information about children.'])
cat('MON','Money',['QT07','QT12','QT21'],'Relevant financial facts, not a new ground or financial audit',[
'Before marriage, what did you discuss about work, income, debts and financial responsibilities?',
'Was there an important financial fact or agreement you say was not disclosed or was represented differently?',
'Describe a specific financial decision or disagreement relevant to this petition: when, who was involved and what happened.',
'What did you know then, what did you discover later and how did you discover it?',
'Which evidence supports the particular fact, and what is uncertain or disputed?'])
cat('INT','Intimacy',['QT07','QT28'],'Narrow private inquiry where relevant; no blanket sexual-history inventory',[
'Is there a specific intimate marital difficulty you wish to explain, including when it arose or became known?',
'If relevant, what had been discussed or understood before marriage, and what was different afterward?',
'How does this specific difficulty relate to your request? Include only the facts you wish to explain.'])
cat('PRS','Pressure or threats',['QT08','AF13'],'Relevant freedom-of-decision facts, not presumed coercion',[
'What pressure, threat or circumstance affected the decision to marry?',
'Who or what was the source, when did it occur and what specifically happened?',
'How did it affect your decision and what did you communicate at the time?',
'What do you know directly and what evidence or contemporaneous information supports it?'])
cat('DBT','Doubts before marriage',['QT09'],'Specific reservations and what followed',[
'What serious reservations, if any, did you have before the wedding?',
'Did you discuss them? Identify what you said, to whom and what response or action followed.',
'Why did you proceed at that time, and what relevant facts were known then?'])
cat('WED','Wedding circumstances',['QT10'],'Specific event at the ceremony; no separate civil/church supplement',[
'Did a specific event immediately before or at the ceremony affect willingness or ability to proceed?',
'Describe what happened, when and what you remember directly.',
'Was the event discussed at the time, and what other information supports your account?'])
cat('CON','Misrepresentation or concealment',['QT11','AF12','AF14'],'Already approved allegation type; assertions remain attributed',[
'What important fact do you say was represented differently or not disclosed before marriage?',
'What were you told, by whom and when?',
'What did you believe when deciding to marry, and why was that fact important to the decision?',
'When and how did you learn the difference?',
'What evidence supports each part of this sequence, and what remains uncertain?'])
cat('INF','Infidelity',['QT13'],'Selected approved ground; no presumed guilt',[
'Describe the alleged unfaithfulness relevant to the petition.',
'When did the conduct occur, and when did you first learn about it?',
'What did you observe directly and what information came from another source?',
'What specific evidence supports your account?'])
cat('ABD','Desertion or abandonment',['QT14'],'Known absence/contact facts, not assumed intention',[
'When did the separation or absence begin, and what circumstances do you know directly?',
'What relevant communication, contact or support continued, if any?',
'What attempts were made to communicate or reconcile, and what happened?',
'Which dates or reasons are known, estimated or unknown, and what supports them?'])
cat('ABU','Abuse',['QT15'],'Specific incidents/patterns; no child testimony or imposed diagnosis',[
'Describe the relevant incident or pattern you wish the council to consider.',
'When did it happen, was it repeated, and what did you experience or observe directly?',
'What relevant effect did it have on married life or the decision to separate?',
'Are there existing court orders, reports or other evidence you wish to identify?'])
cat('FTH','Leaving or changing the faith',['QT16','AF07'],'Affiliation, change and source of knowledge kept distinct',[
'What was each party’s religious affiliation before you knew each other, to your knowledge?',
'What later change in affiliation or practice is relevant to this request, and when did it occur?',
'What do you know directly and what were you told?',
'How did the stated change affect married life, and what information supports that account?'])
cat('ADD','Addiction',['QT17'],'Reported conduct and effect; no diagnosis from labels',[
'Describe the behavior relevant to this petition rather than only giving it a label.',
'When did it begin, when did you become aware of it and how?',
'How did the behavior affect married life?',
'What help was sought, if known, and what evidence or direct observations support your account?'])
cat('BKG','Relevant personal or family background',['QT19'],'Conditional relevance only, not a full biography',[
'Is there a specific earlier experience directly connected to an issue in this petition?',
'Explain the relevant event and connection, distinguishing your direct knowledge from what you were told.',
'What information supports the connection, and what is unknown?'])
cat('TIM','When problems began',['QT03','QT20','AF08','AF09'],'Occurrence versus discovery; exact versus approximate dates',[
'When did the relevant difficulties first appear, and were they evident before or after marriage?',
'What did you know at the time, and what became known later?',
'Which important dates are exact, approximate or unknown? Relate each date to a specific event.'])
cat('SEP','Separation history',['QT24'],'Interview only; rejected applicant separation-repeat proposal remains out',[
'Were there relevant temporary separations before the final one?',
'For each relevant period, describe approximate dates, reason and what led to resuming life together.',
'Describe the final separation separately: when, circumstances and what you know directly.',
'Identify supporting information and uncertain dates without treating separation as a new case.'])
cat('REC','Reconciliation efforts',['QT25'],'Detailed interview; application still priest name only',[
'What relevant attempts at reconciliation were made?',
'Who participated, approximately when, and what happened?',
'Distinguish the outcome you observed from information you received from someone else.',
'What information remains outstanding and what existing records are relevant?'])
cat('EVD','Evidence and factual clarification',['QT04','QT05','AF16'],'One fact/source structure reused across categories',[
'Which specific fact does each item support?',
'Who created it, when and how did you obtain it, if known?',
'What did you personally experience, observe or learn from another source?',
'What limitations, conflicting information or uncertainty should the council know? Do not disclose the other applicant’s private submission.'])
cat('MED','Medical or psychological professional help',['QT23'],'Revised wording awaiting confirmation, not an active question category',[
'Have you or your spouse received medical, psychological or psychiatric treatment relevant to the issue discussed?',
'If so, what treatment or professional help, when, and how does it relate to the marriage?',
'What do you know directly? No blanket medical-record release or unverified diagnosis is implied.'],pending=True)
fixed=[
dict(id='OPEN',title='Opening and subject identification — always retained',questions=['State the interviewee’s full name and the spouse’s full name; identify the case, actual interviewer and date. Repeat identity opening for every newly started recording.','Where audio is used, record that the interviewee was informed about recording.']),
dict(id='BASIS',title='Request and application confirmation — common core',questions=['What outcome are you seeking, and which specific facts do you want the council to consider in support of it?','Identify any submitted information needing clarification without rewriting the original application through the interview.']),
dict(id='CLOSE',title='Closing clarification — always retained',questions=['What relevant fact has not yet been covered, and is anything you said today in need of clarification?'])]
bank={'version':'ctm-interview-category-review-v1','status':'Structure confirmed by user; expanded detail wording is a review draft, not a published institutional questionnaire.','fixedBlocks':fixed,'categories':categories,'excludedProposals':['QT22','QT26','QT27','QT30'],'reportRule':'Assemble selected category questions and recorded answers/evidence; observations and transcript remain separate. No AI mapping into answers; no case export.'}
(ROOT/'interview-category-bank.json').write_text(json.dumps(bank,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# Interview common question families and category bank','',bank['status'],'',
'The assigned member selects relevant categories. Selected questions and their actual answers form report sections, in retained category/question order. Common opening/request and closing stay attached to each interview. There is no requirement to use every category. Original source, actual actor, exact question version, selected category, evidence links and timestamps remain identifiable.','',
'This English review bank supplies concrete detail to the approved bilingual versioning model; it is not a replacement for published English/Arabic text. Previously published text would never be mutated. No inference of new canonical grounds or case export.','',
'## Common blocks','']
for b in fixed:
 md+=['### '+b['title'],'']+[f'{b["id"]}-{i:02}. {text}'for i,text in enumerate(b['questions'],1)]+['']
for c in categories:
 md+=['## '+c['title']+(' — pending wording approval' if c['pending'] else ''),'',f'Category `{c["id"]}` · accepted source decisions: '+', '.join(c['proposalRefs'])+'.',c['scope'],'']
 md += [f'- **{q["id"]}** {q["text"]}'for q in c['questions']]+['']
md+=['## Assembly and boundaries','',bank['reportRule'],
'QT22 generic communication, QT26 multi-ceremony supplement, QT27 full prior-marriage interview and QT30 appeal-question template are excluded. Existing appeals/prior-application policies are not deleted. Money and Children categories may include relevant examples without opening a new communication or civil-law determination workflow.',
'An answer not supplied is not an affirmative or a finding. Once recorded, category removal/reordering must preserve prior answers/history. Investigator observations are a separate authored section. Audio, manual answers and reviewed AI transcript do not overwrite each other.',
'The priest report is a separate free-form template with explicit subject header; it does not require answering this bank.']
(ROOT.parent/'CTM-interview-category-bank.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
css=(ROOT.parent/'questionnaire/questionnaire.css').read_text(encoding='utf-8')
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CTM interview category planner</title><style>'''+css+'''
main{display:grid;grid-template-columns:minmax(250px,330px) minmax(0,1fr);gap:35px}.category-select{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid var(--line)}.category-select input{margin-top:5px;accent-color:var(--accent)}.category-select small{display:block;color:var(--muted)}.section{padding:18px 0;border-bottom:1px solid var(--line)}.section h2{margin:0 0 10px}.question{margin:9px 0}.code{font-size:12px;color:var(--accent);font-weight:700}.pending{opacity:.7}.notice{border-top:1px solid var(--line);padding-top:15px}aside{position:static}.report-note{font-size:13px;color:var(--muted)}@media(max-width:800px){main{grid-template-columns:1fr}}
</style></head><body><header><p class="eyebrow">CTM / interview planning preview</p><h1>Select the question families.</h1><p class="intro">Choose categories to see the detailed questions and resulting report structure. Children, Money and Intimacy are explicit categories.</p><p>This is a template-planning artifact, not CTM or a place to enter real case data. Expanded question wording is a review draft. No microphone, transcription, case storage or export is implemented here.</p><p><a href="../CTM-reference-review-decisions.md">Reconciled decisions</a> · <a href="../CTM-priest-testimony-template-draft.md">Free-form priest report</a></p></header><main><aside><h2>Common question families</h2><p class="small">Opening, request/context and closing remain in every interview. Select only relevant additional categories. Medical wording remains pending.</p><div id="categories"></div><p id="count" role="status"></p><button id="clear" type="button">Clear selections</button></aside><section><h2>Assembled interview report outline</h2><p class="report-note">Each selected section contains its numbered prompts, recorded answers and evidence references. The actual member’s observations remain separate. This preview shows the structure only.</p><div id="report"></div><div class="notice"><h2>Separate report material</h2><p>Interview metadata and subject · selected template/version · actual answers and linked evidence · member observations/recommendations · separate original audio and reviewed transcript references. Missing answers are not findings. No AI-generated questionnaire answers.</p></div></section></main><footer>Planning only · no case data collected · no approved questionnaire changed</footer><script>const BANK=__BANK__;
const selected=new Set();
const make=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
function block(title,questions){const section=document.createElement('section');section.className='section';section.append(make('h2',title));for(const q of questions){const p=make('p',q.id+' · '+q.text);p.className='question';section.append(p);}return section;}
function render(){const report=document.getElementById('report');report.replaceChildren();for(const b of BANK.fixedBlocks.slice(0,2))report.append(block(b.title,b.questions.map((text,i)=>({id:b.id+'-'+String(i+1).padStart(2,'0'),text}))));for(const c of BANK.categories)if(selected.has(c.id)&&!c.pending)report.append(block(c.title,c.questions));const b=BANK.fixedBlocks[2];report.append(block(b.title,b.questions.map((text,i)=>({id:b.id+'-'+String(i+1).padStart(2,'0'),text}))));document.getElementById('count').textContent=selected.size+' optional categories selected';}
for(const c of BANK.categories){const label=document.createElement('label');label.className='category-select'+(c.pending?' pending':'');const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.disabled=c.pending;checkbox.value=c.id;checkbox.addEventListener('change',()=>{if(checkbox.checked)selected.add(c.id);else selected.delete(c.id);render();});const content=document.createElement('span');content.append(make('strong',c.title),make('small',c.pending?'Wording pending — not included':c.questions.length+' detailed questions · '+c.proposalRefs.join(', ')));label.append(checkbox,content);document.getElementById('categories').append(label);}
document.getElementById('clear').addEventListener('click',()=>{selected.clear();document.querySelectorAll('input').forEach(x=>x.checked=false);render();});render();
</script></body></html>'''
(ROOT/'interview-category-planner.html').write_text(page.replace('__BANK__',json.dumps(bank,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
print('Built',len(categories),'categories,',sum(len(c['questions'])for c in categories if not c['pending']),'detailed selectable prompts, plus common opening/context/closing; medical category pending.')
