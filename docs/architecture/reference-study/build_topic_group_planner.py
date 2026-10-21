from pathlib import Path
import json
R=Path(__file__).parent
bank=json.loads((R/'interview-category-bank.json').read_text(encoding='utf-8'))
guidance=json.loads((R/'interview-question-guidance.json').read_text(encoding='utf-8'))
names=['Identity and marriage identifiers','Church and civil ceremony distinction','Prior marriages versus prior tribunal applications','Courtship / engagement','Reasons for marrying / pressure / doubts','Known and concealed facts','Intentions / agreements at marriage','Wedding-day circumstances','Intimate matters','Problem onset before versus after marriage','Infidelity','Abuse / addiction','Religious affiliation and change','Responsibilities / communication / finances','Temporary and final separation','Reconciliation and professional help','Source of knowledge / evidence']
# Reuse stable question definitions. Empty categories retain the requested organization without inventing rejected questions.
family_map={'BKG':3,'DEC':4,'PRS':4,'DBT':4,'CON':5,'CHD':6,'WED':7,'INT':8,'TIM':9,'INF':10,'ABU':11,'ADD':11,'FTH':12,'MON':13,'ABD':14,'SEP':14,'REC':15,'MED':15,'EVD':16}
categories=[{'id':f'QC{i+1:02}','title':n,'questions':[]} for i,n in enumerate(names)]
for family in bank['categories']:
 for q in family['questions']:
  categories[family_map[family['id']]]['questions'].append({**q,'subtopic':family['title'],'pending':family['pending']})
fixed=[{'id':f'{b["id"]}-{i:02}','text':q} for b in bank['fixedBlocks'] for i,q in enumerate(b['questions'],1)]
groupnames=['Common applicant intake','Common guided interview','Annulment-related factual inquiry','Divorce/dissolution grounds','Multiple-ceremony supplement','Prior-marriage factual supplement','Appeal new-information supplement','Optional priest report']
suggested=[[0,1,2,16],list(range(17)),[3,4,5,6,7,8,9,16],[9,10,11,12,14,16],[1],[2],[16],[]]
notes=['Organization preview only; this does not add interview questions to the applicant application.','','An organizational grouping; questions do not determine a canonical outcome.','','The separate multiple-ceremony question supplement was not adopted. Use existing application confirmation where relevant.','The full prior-marriage interview supplement was not adopted. Use existing application confirmation where relevant.','The existing appeal process applies. No separate appeal question module has been added.','Council-requested priest testimony remains a separate free-form written or recorded report identifying the marriage and person concerned. It is not a mandatory guided interview.']
model={'version':'ctm-topic-group-planner-v2','hierarchy':['Topic group','Question categories','Questions'],'topicGroups':[{'id':f'TG{i+1:02}','title':n,'categories':[categories[j]['id'] for j in suggested[i]],'note':notes[i]} for i,n in enumerate(groupnames)],'categories':categories,'fixed':fixed,'guidance':guidance,'wordingProposals':json.loads((R/'interview-wording-proposals.json').read_text(encoding='utf-8')),'wordingFlags':json.loads((R/'interview-wording-review.json').read_text(encoding='utf-8'))}
# Apply only the user's returned decisions. Preserve the prior bank and proposal versions as review provenance.
review_items=[{**q,'category':'Foundational questions'} for q in fixed]+[{**q,'category':c['title']} for c in categories for q in c['questions']]
returned=json.loads((R/'interview-wording-user-decisions-2026-10-20.json').read_text(encoding='utf-8'))['decisions']
model['reviewItems']=review_items
model['returnedDecisions']={k:{'choice':'other' if v['decision'] in ['remove','custom','replace_with_contextual_dates'] else v['decision'],'text':('Remove this question.' if v['decision']=='remove' else v['note'])} for k,v in returned.items()}
def reconcile(q):
 decision=returned[q['id']]['decision']
 if decision in ['remove','replace_with_contextual_dates']:return None
 if decision=='accept':q['text']=model['wordingProposals'].get(q['id']) or guidance[q['id']].get('recommended') or q['text']
 if q['id']=='ADD-02':q['text']='When did the addiction begin, if known, and how did it develop?'
 if q['id']=='MON-01':q['text']='Before marriage, what did you discuss about work, income, debts and financial responsibilities?'
 q['reviewDecision']=decision
 if q['id'].startswith('ADD-'):
  q['text']=q['text'].replace('the behavior','the addiction')
 # Date precision belongs with the relevant event, rather than a blanket chronology question.
 import re
 if re.search(r'\b(when|date|dates|began|begin|time|period)\b',q['text'],re.I):
  prompts=guidance[q['id']]['prompts']
  note='For each date mentioned here, say whether it is exact, approximate or unknown.'
  if note not in prompts:prompts.append(note)
 return q
fixed[:]=[r for q in fixed if (r:=reconcile(q)) is not None]
for c in categories:c['questions']=[r for q in c['questions'] if (r:=reconcile(q)) is not None]
# Group already existing discussion questions by topic without creating additional questions.
discussions={'id':'QC18','title':'Discussions before marriage','questions':[]}
for c in categories:
 for q in list(c['questions']):
  if q['id'] in ['MON-01','CHD-01','INT-02']:
   c['questions'].remove(q);discussions['questions'].append(q)
categories.append(discussions)
for group in model['topicGroups']:
 if group['id'] in ['TG02','TG03']:group['categories'].append('QC18')
# User's category terminology and contextual evidence organization.
renames={'QC05':'Decision to marry','QC06':'Misrepresentation or concealment','QC10':'When problems began','QC14':'Finances','QC16':'Reconciliation efforts'}
for c in categories:
 if c['id'] in renames:c['title']=renames[c['id']]
discussions['questions']+=next(c for c in categories if c['id']=='QC07')['questions']
model['evidenceQuestions']=next(c for c in categories if c['id']=='QC17')['questions']
categories[:]=[c for c in categories if c['id'] not in ['QC07','QC17']]
# No general communication module is added; retain a separate organizational heading only.
categories.append({'id':'QC19','title':'Communication','questions':[]})
for group in model['topicGroups']:
 group['categories']=['QC18' if x=='QC07' else x for x in group['categories'] if x!='QC17']
 group['categories']=list(dict.fromkeys(group['categories']))
model['contextualEvidenceCategoryIds']=[]
model['removedEvidenceQuestions']=model['evidenceQuestions']
model['evidenceQuestions']=[]
# Integrate relevant follow-ups into readable main questions; do not repeat already covered prompts.
integrated=json.loads((R/'interview-integrated-question-wording.json').read_text(encoding='utf-8'))
import re
for q in fixed+[q for c in categories for q in c['questions']]+model['evidenceQuestions']:
 q['text']=integrated.get(q['id'],q['text']).replace('\ufffd',"'")
 if q['id']!='OPEN-01' and re.search(r'\b(when|date|dates|began|begin)\b',q['text'],re.I):
  q['text']+=' Give exact dates where known; otherwise, say whether the date is approximate or unknown.'
 guidance[q['id']]['prompts']=[]
model['followupPresentation']='Integrated into main question wording; no separate helper placeholders.'
# Latest user-supplied complete revision supersedes prior wording overlays.
revision=json.loads((R/'interview-revised-bank-2026-10-20.json').read_text(encoding='utf-8'))
old_categories={c['title']:c['id'] for c in categories}
new_categories=[]
for section in revision['sections']:
 if not section['questions']:continue
 questions=[{**q,'pending':False,'reviewDecision':'user-supplied-revision'} for q in section['questions']]
 for q in questions:
  if q['id'] not in guidance:guidance[q['id']]={'prompts':[]}
  guidance[q['id']]['prompts']=[]
 if section['title']=='Foundational questions':fixed[:]=questions;continue
 category_id=old_categories.get(section['title']) or ('QC18' if section['title'].startswith('Discussions before marriage') else 'QC20')
 new_categories.append({'id':category_id,'title':section['title'],'intro':section['intro'],'questions':questions})
categories[:]=new_categories
valid_ids={c['id'] for c in categories}
for group in model['topicGroups']:group['categories']=[cid for cid in group['categories'] if cid in valid_ids]
model['version']=revision['version']
model['administrativeSections']=[s for s in revision['sections'] if s['title'] in ['Interviewer instructions','Administrative record']]
model['contextPrompts']=json.loads((R/'interview-adopted-context-prompts.json').read_text(encoding='utf-8'))['questions']
model['questionCount']=len(fixed)+sum(len(c['questions']) for c in categories)+len(model['evidenceQuestions'])
model['version']='ctm-topic-group-planner-v3-reconciled'
(R/'interview-current-question-bank.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'interview-topic-group-model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CTM Interview Planner</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f5f0;color:#24332e;font:16px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:32px}h1{font-size:30px}h2{font-size:22px}h3{font-size:18px}button,select{font:inherit;padding:9px 12px;margin:5px;border:1px solid #82998e;border-radius:5px;background:white;color:inherit}button{cursor:pointer}button:focus-visible,select:focus-visible,summary:focus-visible,input:focus-visible{outline:3px solid #bd8228}label{display:block;margin:8px 0}.layout{display:grid;grid-template-columns:320px 1fr;gap:24px}.panel,.block{background:white;border:1px solid #d2d9d2;padding:20px;margin:16px 0;border-radius:7px}.question{border-top:1px solid #dce2dc;padding:16px 0}.muted{color:#52665b;font-size:14px}.wording-review{border-left:3px solid #b78324}details{background:#f1f4ed;padding:12px;margin-top:12px}summary{cursor:pointer;font-weight:600}.answer{display:block;width:100%;resize:vertical;border:1px solid #a7b9ae;border-radius:4px;padding:12px;color:#24332e;background:white;font:15px/1.6 system-ui,sans-serif}.answer::placeholder{color:#737373;opacity:1}.answer:focus-visible{outline:3px solid #bd8228}.notice{background:#fff4d8;padding:12px}.choices label{border-bottom:1px solid #e5e8e2;padding:7px 0}.choices input{margin-right:9px}select{max-width:100%}@media(max-width:800px){.layout{grid-template-columns:1fr}main{padding:16px}}</style>
<main><h1>Case Investigation and Factual Discovery</h1><p>Topic group → Question categories → Questions</p><p class="muted">Planning preview. Select reusable categories, the accepted conditional follow-up prompts are available under their linked questions. Use only when needed; do not repeat an existing answer. Preview text is temporary and is not saved.</p><p class="muted">Your returned wording decisions are applied below. Removed questions remain in the review record only; the current bank excludes them. Ask who, what, where, when, why and how where relevant; skip details already answered and accept unknown information.</p><div class="layout"><aside class="panel"><label for="view">Organize by</label><select id="view"><option value="group">Topic group</option><option value="category">Question categories</option></select><div id="groupControls"><label for="group">Topic group</label><select id="group"></select><p id="groupNote" class="muted"></p><button id="suggested">Add this group’s categories</button></div><p class="muted">Changing the view or group preserves selected categories.</p><div id="choices" class="choices"></div><button id="all">Review full question bank</button><button id="clear">Clear optional categories</button><p id="count" aria-live="polite"></p></aside><article><section class="panel"><h2>Report identification — always present</h2><p><strong>Report for:</strong> [first name and last name]<br><strong>Marriage:</strong> [first name last name] and [first name last name]<br><strong>Case number:</strong> [case number]<br><strong>Interviewer:</strong> [actual interviewer]<br><strong>Interview date/time:</strong> [date/time]</p><p class="muted">Repeat the spoken identification at the start of every interview and every new recording.</p></section><div id="foundations"></div><section class="panel"><h2>Submitted information and evidence</h2><p>Confirm application details using their exact submitted versions. Link relevant statements and evidence to the appropriate questions, identifying the supplier and version. An allegation remains attributed to its source.</p><p class="muted">Interview answers, original application answers, transcripts and council findings remain separate. Applicant privacy and medical release restrictions apply to linked material.</p></section><div id="priest" class="panel" hidden><h2>Priest report — free-form</h2><p>Identify the priest, the marriage, the person this report concerns and the report date. Invite a written or recorded account of personally known marriage circumstances. Recorded testimony follows the agreed transcription and translation process.</p><p class="muted">The foundational questions below remain part of the interview planner; they are not imposed on the separate priest report.</p></div><div id="outline"></div></article></div></main><script>const MODEL=__MODEL__;
const el=id=>document.getElementById(id), selected=new Set(), answers=new Map(), fields=new Map();let showPrompts=true;
function make(tag,text){const e=document.createElement(tag);if(text)e.textContent=text;return e;}
function question(q){const w=make('div');w.className='question';const guide=MODEL.guidance[q.id];const main=q.text;const label=make('label',q.id+' · '+main);label.htmlFor='answer-'+q.id;w.append(label);if(!q.reviewDecision&&MODEL.wordingFlags[q.id]){const review=make('details');review.className='wording-review';review.append(make('summary','Wording review — proposed changes only'),make('p','Original: '+q.text),make('p','Review note: '+MODEL.wordingFlags[q.id]));const proposed=MODEL.wordingProposals[q.id]||guide.recommended;if(proposed&&proposed!==q.text)review.append(make('p','Suggested wording — not applied: '+proposed));w.append(review);}if(q.pending)w.append(make('p','Medical wording remains a review draft. Signed disclosure release requirements apply separately.'));const a=make('textarea');a.id='answer-'+q.id;a.className='answer';a.rows=Math.max(4,guide.prompts.length*2);a.value=answers.get(q.id)||'';a.placeholder='';a.addEventListener('input',()=>answers.set(q.id,a.value));fields.set(q.id,{field:a,prompts:guide.prompts});w.append(a);const context=MODEL.contextPrompts[q.id];if(context&&context.prompts.length){const help=make('details');help.append(make('summary','Conditional follow-up prompts'),make('p','Use only for an unanswered detail: '+context.trigger));const list=make('ul');for(const prompt of context.prompts)list.append(make('li',prompt));help.append(list);w.append(help);}if(q.interviewerNote){const note=make('p','Interviewer note: '+q.interviewerNote);note.className='muted';w.append(note);}return w;}
function block(title,questions){const s=make('section');s.className='block';s.append(make('h2',title));for(const q of questions)s.append(question(q));return s;}
for(const g of MODEL.topicGroups){const o=make('option',g.title);o.value=g.id;el('group').append(o);}el('group').value=MODEL.topicGroups[0].id;
for(const section of MODEL.administrativeSections){const box=make('details');box.className='panel';box.append(make('summary',section.title),make('p',section.intro));el('foundations').append(box);}el('foundations').append(block('Foundational questions',MODEL.fixed));
function render(){const group=MODEL.topicGroups.find(g=>g.id===el('group').value);el('groupControls').hidden=el('view').value==='category';el('groupNote').textContent=group.note;el('priest').hidden=group.id!=='TG08'||el('view').value==='category';el('choices').replaceChildren();el('outline').replaceChildren();const seen=new Set(MODEL.fixed.map(q=>q.id));for(const c of MODEL.categories){const label=make('label');const input=make('input');input.type='checkbox';input.checked=selected.has(c.id);input.addEventListener('change',()=>{if(input.checked)selected.add(c.id);else selected.delete(c.id);render();});label.append(input,make('span',c.title));el('choices').append(label);if(selected.has(c.id)){const questions=c.questions.filter(q=>{if(seen.has(q.id))return false;seen.add(q.id);return true;});const s=block(c.title,questions);if(c.intro){const intro=make('p',c.intro);intro.className='muted';s.children[0].after(intro);}if(!questions.length)s.append(make('p',c.id==='QC01'?'Covered by the always-present report identification and foundational confirmation.':'Use the existing application-confirmation question where relevant. No separate approved question block has been added.'));el('outline').append(s);}}el('count').textContent=selected.size+' selected categories · '+seen.size+' main questions shown · '+MODEL.questionCount+' retained question definitions, including contextual evidence prompts';}
el('view').addEventListener('change',render);el('group').addEventListener('change',render);el('suggested').addEventListener('click',()=>{const g=MODEL.topicGroups.find(g=>g.id===el('group').value);for(const id of g.categories)selected.add(id);render();});el('all').addEventListener('click',()=>{for(const c of MODEL.categories)selected.add(c.id);render();});el('clear').addEventListener('click',()=>{selected.clear();render();});render();</script></html>'''

page=page.replace('<div class="layout"><aside', '<section class="panel" id="wording-grid"><h2>Question wording review</h2><p>Accept the proposed wording, reject it to keep the original, or enter your own. Your returned decisions are shown. Further selections are saved for review and do not automatically change the current bank.</p><button id="downloadReview">Download decisions</button><button id="copyReview">Copy decisions for chat</button><p id="reviewStatus" aria-live="polite"></p><textarea id="reviewOutput" class="answer" rows="5" aria-label="Decisions to copy" hidden></textarea><div class="grid-scroll"><table><thead><tr><th scope="col">Reference / category</th><th scope="col">Original question</th><th scope="col">Proposed wording / reason</th><th scope="col">Your decision / wording</th></tr></thead><tbody id="reviewRows"></tbody></table></div></section><div class="layout"><aside')
page=page.replace('</style>', '.prompt-toolbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;flex-wrap:wrap;gap:8px 20px;padding:12px 18px;background:#e5eee4;border:2px solid #657e68;border-radius:6px;box-shadow:0 2px 6px #0001}.prompt-toolbar label{font-weight:700;margin:0}.prompt-toolbar input{width:20px;height:20px;vertical-align:middle;margin-right:8px}.prompt-toolbar span{font-size:14px;color:#4d5e50}.grid-scroll{overflow:auto;max-height:75vh}table{border-collapse:collapse;width:100%;min-width:980px}th,td{border:1px solid #ccd4cd;padding:14px;text-align:left;vertical-align:top}th{background:#e9efe7;position:sticky;top:0}td{min-width:200px}td:first-child{min-width:120px}td textarea{min-height:110px}td fieldset{border:0;padding:0;margin:0 0 10px}td legend{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}td fieldset label{display:inline-flex;align-items:center;gap:5px;margin:4px 12px 4px 0;white-space:nowrap}tbody tr:nth-child(even){background:#f8f9f5}</style>')
reviewjs=r"""
const reviewKey='ctm-wording-review-v3-reconciled', reviewItems=MODEL.reviewItems;
let decisions={...MODEL.returnedDecisions};try{const raw=JSON.parse(localStorage.getItem(reviewKey)||'{}');for(const q of reviewItems){const d=raw[q.id];if(d&&['accept','reject','other'].includes(d.choice)&&typeof d.text==='string')decisions[q.id]={choice:d.choice,text:d.text};}}catch(e){}
function proposal(q){return MODEL.wordingProposals[q.id]||MODEL.guidance[q.id].recommended||q.text;}
function reviewPayload(){return {version:reviewKey,items:reviewItems.map(q=>({id:q.id,category:q.category,original:q.text,proposed:proposal(q),decision:decisions[q.id]?.choice||'unanswered',ownWording:decisions[q.id]?.text||''}))};}
function saveReview(){try{localStorage.setItem(reviewKey,JSON.stringify(decisions));el('reviewStatus').textContent=Object.values(decisions).filter(d=>d.choice).length+'/78 decisions saved in this browser. Download a copy to send back.';}catch(e){el('reviewStatus').textContent='Browser saving unavailable. Download or copy your decisions before leaving.';}}
for(const q of reviewItems){const tr=make('tr'),ref=make('td',q.id+' · '+q.category),original=make('td',q.text),proposed=make('td'),control=make('td');const wording=proposal(q);proposed.append(make('p',wording));if(MODEL.wordingFlags[q.id])proposed.append(make('p','Reason: '+MODEL.wordingFlags[q.id]));const radioGroup=make('fieldset');const legend=make('legend','Decision for '+q.id);radioGroup.append(legend);const own=make('textarea');own.className='answer';own.setAttribute('aria-label','My wording or clarification for '+q.id);own.placeholder='Type your wording or clarification';own.value=decisions[q.id]?.text||'';let choice=decisions[q.id]?.choice||'';function record(){decisions[q.id]={choice,text:own.value};saveReview();}for(const [v,t] of [['accept','Accept'],['reject','Reject'],['other','My wording']]){const label=make('label'),radio=make('input');radio.type='radio';radio.name='decision-'+q.id;radio.value=v;radio.checked=choice===v;radio.addEventListener('change',()=>{if(radio.checked){choice=v;record();}});label.append(radio,make('span',t));radioGroup.append(label);}own.addEventListener('input',record);control.append(radioGroup,own);tr.append(ref,original,proposed,control);el('reviewRows').append(tr);}
el('downloadReview').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(reviewPayload(),null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=make('a');a.href=url;a.download='CTM-question-wording-decisions.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
el('copyReview').addEventListener('click',async()=>{const t='CTM question wording review'+String.fromCharCode(10)+reviewPayload().items.map(q=>q.id+' — '+q.decision.toUpperCase()+(q.ownWording?' | '+q.ownWording:'')).join(String.fromCharCode(10));el('reviewOutput').hidden=false;el('reviewOutput').value=t;try{await navigator.clipboard.writeText(t);el('reviewStatus').textContent='Decisions copied. Paste them into this chat.';}catch(e){el('reviewStatus').textContent='Select and copy the text below, then paste it into this chat.';}});
saveReview();
"""
page=page.replace('</script>',reviewjs+'</script>')
# The completed review is history; open the reconciled bank by default.
page=page.replace('<section class="panel" id="wording-grid"><h2>Question wording review</h2>', '<details class="panel" id="wording-grid"><summary>Completed wording review — history</summary>')
page=page.replace('</tbody></table></div></section><div class="layout">', '</tbody></table></div></details><div class="layout">')
page=page.replace('Accept the proposed wording, reject it to keep the original, or enter your own.', 'Your completed review is retained here for reference. The current bank below already reflects your decisions.')
page=page.replace("});render();</script>", "});render();</script>")
page=page.replace("});render();", "});for(const c of MODEL.categories)selected.add(c.id);el('view').value='category';render();")
# Remove completed review UI and its handlers; keep decision files as source provenance only.
start=page.index('<details class="panel" id="wording-grid">')
end=page.index('</details><div class="layout">',start)+len('</details>')
page=page[:start]+page[end:]
start=page.index("const reviewKey=")
end=page.index('</script>',start)
page=page[:start]+page[end:]
lines=['# CTM Question Bank','','Current question wording, grouped by category.','','Total: '+str(model['questionCount'])+' questions.','','## Foundational questions','']
for q in fixed:lines.extend(['### '+q['id'],'',q['text'],''])
for c in categories:
 if not c['questions']:continue
 lines.extend(['## '+c['title'],''])
 for q in c['questions']:lines.extend(['### '+q['id'],'',q['text'],''])
(R.parent/'CTM-current-question-bank.md').write_text(revision['markdown'],encoding='utf-8')
(R/'interview-category-planner.html').write_text(page.replace('__MODEL__',json.dumps(model,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
print('Generated reconciled planner:',model['questionCount'],'active questions; 78 original references retained for review.')
