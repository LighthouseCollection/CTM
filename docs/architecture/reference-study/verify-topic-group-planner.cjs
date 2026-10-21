const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=__dirname;
const model=JSON.parse(fs.readFileSync(root+'/interview-topic-group-model.json','utf8'));
const bank=JSON.parse(fs.readFileSync(root+'/interview-category-bank.json','utf8'));
assert.equal(model.topicGroups.length,8);assert.equal(model.categories.length,17);
const original=bank.categories.flatMap(c=>c.questions).concat(bank.fixedBlocks.flatMap(b=>b.questions.map((text,i)=>({id:b.id+'-'+String(i+1).padStart(2,'0'),text}))));
const current=model.fixed.concat(model.categories.flatMap(c=>c.questions));assert.equal(current.length,78);assert.equal(new Set(current.map(q=>q.id)).size,78);
for(const q of original){assert.equal(current.find(x=>x.id===q.id).text,q.text);assert(model.guidance[q.id]);}
class E{constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.value='';}setAttribute(k,v){this[k]=v}append(...c){this.children.push(...c)}replaceChildren(...c){this.children=c}addEventListener(t,f){this.listeners[t]=f}}
const nodes=new Map();const document={createElement:t=>new E(t),getElementById:id=>{if(!nodes.has(id))nodes.set(id,new E('div'));return nodes.get(id)}};
nodes.set('view',Object.assign(new E('select'),{value:'group'}));
const saved={};const localStorage={getItem:k=>saved[k]||null,setItem:(k,v)=>saved[k]=v};
const html=fs.readFileSync(root+'/interview-category-planner.html','utf8');new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]).runInNewContext({document,Set,localStorage});
function descendants(e){return [e,...e.children.flatMap(descendants)]}
function textareas(){return ['foundations','outline'].flatMap(id=>descendants(nodes.get(id))).filter(e=>e.tag==='textarea')}
assert.equal(textareas().length,5);nodes.get('all').listeners.click();assert.equal(textareas().length,78);
const target=textareas().find(e=>e.id==='answer-ADD-02');assert(target.placeholder.includes('When did you first become aware of it?'));target.value='Temporary answer';target.listeners.input();
nodes.get('showPrompts').checked=false;nodes.get('showPrompts').listeners.change();assert(textareas().every(e=>e.placeholder===''));assert.equal(target.value,'Temporary answer');
nodes.get('view').value='category';nodes.get('view').listeners.change();assert.equal(textareas().length,78);assert.equal(textareas().find(e=>e.id==='answer-ADD-02').value,'Temporary answer');
nodes.get('showPrompts').checked=true;nodes.get('showPrompts').listeners.change();assert(textareas().find(e=>e.id==='answer-ADD-02').placeholder.includes('How did you become aware of it?'));
assert.equal(textareas().find(e=>e.id==='answer-ADD-01').placeholder,'');assert(!html.includes('Case manager notes — not questions'));assert(!html.includes('No additional helper question is proposed'));
nodes.get('clear').listeners.click();assert.equal(textareas().length,5);console.log('PASS: 78 question fields, prompt toggle, blank prompts omitted, temporary answers preserved, fixed questions retained.');

assert.equal(nodes.get('reviewRows').children.length,78);const row=nodes.get('reviewRows').children[0];const controls=row.children[3].children;const radios=controls[0].children.slice(1).map(label=>label.children[0]);assert.equal(radios.length,3);assert(radios.every(r=>!r.checked));radios[2].checked=true;radios[2].listeners.change();controls[1].value='My clear question';controls[1].listeners.input();assert.equal(JSON.parse(saved['ctm-wording-review-v2'])['OPEN-01'].text,'My clear question');console.log('PASS: 78 grid rows, no preselected choices, custom wording and local saving.');

for(const [id,reason] of Object.entries(model.wordingFlags)){assert(model.wordingProposals[id]);const q=current.find(q=>q.id===id);assert.notEqual(model.wordingProposals[id],q.text);}assert(!html.includes('Keep original wording (no replacement proposed).'));console.log('PASS: all flagged questions have complete distinct proposed wording.');
