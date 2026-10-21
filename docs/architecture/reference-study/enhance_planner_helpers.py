"""Enhance the planning artifact only; preserve original question wording/IDs."""
from pathlib import Path
import json,re
ROOT=Path(__file__).parent
src=Path('C:/Users/AdminMan/Downloads/CTM_Complete_Factual_Discovery_Question_Bank_and_Review.md')
text=src.read_text(encoding='utf-8-sig')
guidance={}
for m in re.finditer(r'^#{2,4} ([A-Z]+-\d{2})\s*\n([\s\S]*?)(?=^#{1,4} |\Z)',text,re.M):
 body=m[2]
 def part(label):
  x=re.search(re.escape(label)+r'\s*([^\n]+)',body)
  return x[1].strip() if x else ''
 guidance[m[1]]={'purpose':part('Concrete fact sought:'),'when':part('Trigger/skip:'),'prompts':re.findall(r'^- (.+)$',body,re.M),'source':'Perplexity review: optional editorial guidance; no external claims adopted.'}
 if not guidance[m[1]]['purpose']:
  guidance[m[1]]['purpose']='Keep identity, source attribution and the original record intact.'
  guidance[m[1]]['when']=part('Delivery and limit:')
bank=json.loads((ROOT/'interview-category-bank.json').read_text(encoding='utf-8'))
ids=[q['id']for c in bank['categories']for q in c['questions']]+[f'{b["id"]}-{i:02}'for b in bank['fixedBlocks']for i,_ in enumerate(b['questions'],1)]
assert set(ids)==set(guidance) and len(ids)==78
(ROOT/'interview-question-guidance.json').write_text(json.dumps(guidance,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'interview-category-planner.html';page=p.read_text(encoding='utf-8')
page=page.replace('General factual discovery','Start without a preset').replace('Annulment-related factual inquiry','Annulment').replace('Divorce / dissolution','Divorce').replace('Relevant petition / selected ground','Other relevant issue')
page=page.replace('Petition nature → template → reusable common question family → detailed questions → report.','Every report starts with identification and foundational questions. Then select the relevant topics; expand help only when needed.')
page=page.replace('<label for="nature">Petition nature</label>','<label for="nature">What is being investigated?</label>')
page=page.replace('<label for="template">Template</label>','<label for="template">Suggested topic group</label>')
page=page.replace('<button id="suggested" type="button">Add template’s suggested families</button>','<button id="suggested" type="button">Add suggested topics</button><button id="all" type="button">Review full question bank</button>')
page=page.replace('By petition / template','By investigation type').replace('By common question family','By topic / question family')
page=page.replace('<h2>Questionnaire and report outline</h2>','<h2>1. Report identification — always present</h2><div class="identity"><p><strong>Report for:</strong> [applicant first name and last name]</p><p><strong>Marriage:</strong> [first name last name] and [first name last name]</p><p><strong>Case number:</strong> [existing case number]</p><p><strong>Interviewer:</strong> [assigned council member] · <strong>Date/time:</strong> [interview date/time]</p><p>Identify the speaker again at the beginning of every new recording. These are report identifiers, separate from substantive answers.</p></div><h2>2. Foundational questions — every interview</h2>')
page=page.replace('<style>','<style>details{margin:12px 0 20px;padding:10px 13px;border:1px solid #b9c6bc;background:#eef1e9}summary{cursor:pointer;font-weight:600;color:#215952}details p,details li{font-size:14px}summary:focus-visible{outline:3px solid #a76713}.identity{padding:14px;border:1px solid #b9c6bc;background:#f0eee7}.question-wrap{margin:18px 0;padding-bottom:12px;border-bottom:1px solid #d3d6ce}.answer-preview{padding:10px;border:1px dashed #a9b8ae;color:#63716a;font-size:13px}.draft-label{font-size:13px;color:#855600}')
page=page.replace('<script>const MODEL=', '<script>const GUIDANCE='+json.dumps(guidance,ensure_ascii=False).replace('</','<\\/')+';const MODEL=')
start=page.index('function block(');end=page.index('function context(',start)
page=page[:start]+'''function block(title,questions){
 const s=make('section','');s.className='section';s.append(make('h2',title));
 for(const q of questions){const wrap=make('div','');wrap.className='question-wrap';wrap.append(make('p',q.id+' · '+q.text));
 const preview=make('div','Answer area — planning preview only');preview.className='answer-preview';wrap.append(preview);
 const d=make('details','');d.append(make('summary','Guidance and optional follow-up prompts'));const g=GUIDANCE[q.id];
 if(g){if(g.purpose)d.append(make('p','What this clarifies: '+g.purpose));if(g.when)d.append(make('p','When to use / skip: '+g.when));
 if(g.prompts.length){const list=document.createElement('ul');for(const t of g.prompts)list.append(make('li',t));d.append(list);}else d.append(make('p','No routine additional prompt. Clarify only an unanswered relevant fact; do not repeat existing timing or evidence answers.'));}
 d.append(make('p','Optional interviewer guidance only. This text is not an answer and is not included in the case report. No new required fields, grounds or automatic conclusions.'));wrap.append(d);s.append(wrap);}return s;
}
''' + page[end:]
page=page.replace('checkbox.disabled=c.pending;','checkbox.disabled=false;')
page=page.replace('box.disabled=c.pending;','box.disabled=false;')
page=page.replace("c.pending?'Exact question wording pending'", "c.pending?'Medical wording: review draft'")
page=page.replace("if(selected.has(c.id)&&!c.pending)","if(selected.has(c.id))")
page=page.replace("const s=block(c.title,c.questions);", "const s=block(c.title,c.questions);if(c.pending){const warning=make('p','Medical question wording is still a review draft. Signed test/disclosure release requirements remain separately confirmed.');warning.className='draft-label';s.append(warning);}")
page=page.replace("el('count').textContent=selected.size+' selected families · view changes preserve selection';", "el('count').textContent=selected.size+' selected topics · 78 original questions retained in the full library';")
page=page.replace("el('clear').addEventListener('click',", "el('all').addEventListener('click',()=>{for(const c of BANK.categories)selected.add(c.id);render();});el('clear').addEventListener('click',")
page=page.replace('3. Medical / psychiatric evaluations','Medical / psychiatric evaluations')
page=page.replace('The same family is reused across templates.','The same family is reused across templates. Full-bank review includes draft medical wording without approving it.')
page=page.replace('This preview shows the structure only.','This preview shows the structure only.')
p.write_text(page,encoding='utf-8')
print('Enhanced planning preview: 78 retained questions with collapsed helpers, plain group labels, fixed report identity and foundational blocks, full-bank review.')
