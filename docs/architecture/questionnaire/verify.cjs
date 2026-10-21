const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const dir = __dirname;
const source = fs.readFileSync(path.join(dir, 'questionnaire.js'), 'utf8');
// Exercise data and transfer logic without a browser, network or real stored answers.
const dataLogic = source.split('try{const stored=')[0];
const context = vm.createContext({setTimeout, clearTimeout, console});
vm.runInContext(dataLogic, context);
const run = code => vm.runInContext(code, context);
assert.equal(run('questions.length'), 39);
assert.equal(run('new Set(questions.map(q=>q.id)).size'), 39);
assert.equal(run('payload().answers.every(a=>a.answer===null&&a.clarification==="")'), true);
run('state.answers.L01={answer:"yes",clarification:"Keep both historical references."}; state.answers.D01={answer:"no",clarification:"Explain entitlement separately."}; state.answers.T01={answer:null,clarification:"Discuss size later. <script>plain text</script>"}; state.generalNotes="English / العربية";');
const original = run('JSON.stringify(payload())');
context.sample = original;
run('state=normalize(JSON.parse(sample));');
assert.equal(run('state.answers.L01.answer'), 'yes');
assert.equal(run('state.answers.D01.answer'), 'no');
assert.equal(run('state.answers.T01.answer'), null);
assert.match(run('state.answers.T01.clarification'), /<script>plain text<\/script>/);
assert.equal(run('state.generalNotes'), 'English / العربية');
assert.match(run('chatText()'), /T01 — UNDECIDED/);
assert.match(run('chatText()'), /Answered: 2\/39/);
assert.throws(()=>run('normalize({questionnaireVersion:"wrong",answers:[]})'));
assert.throws(()=>run('normalize({questionnaireVersion:VERSION,answers:[{id:"L01",answer:"maybe",clarification:""}]})'));
assert.throws(()=>run('normalize({questionnaireVersion:VERSION,answers:[{id:"L01",answer:null,clarification:""},{id:"L01",answer:null,clarification:""}]})'));
const rows = JSON.parse(run('JSON.stringify(questions)'));
let md = '# CTM architecture review questionnaire\n\n39 unresolved scenarios. All choices are proposals; no answer is preselected. Use the HTML worksheet, or write Yes/No and clarification under these stable question IDs. Applicant-portal design and infrastructure/provider choices remain for later.\n\n';
let previous = '';
for (const q of rows) {
 if (q.section !== previous) { md += `## ${q.section}\n\n`; previous=q.section; }
 md += `### ${q.id}. ${q.question}\n\n${q.context}\n\n- [ ] Yes\n- [ ] No\n\nClarification: \n\n`;
}
fs.writeFileSync(path.join(dir,'questions.md'),md);
const html = fs.readFileSync(path.join(dir,'index.html'),'utf8')
 .replace('<link rel="stylesheet" href="questionnaire.css">',()=>`<style>\n${fs.readFileSync(path.join(dir,'questionnaire.css'),'utf8')}\n</style>`)
 .replace('<script src="questionnaire.js" defer></script>','')
 .replace('</body>',()=>`<script>\n${source}\n</script>\n</body>`);
fs.writeFileSync(path.join(dir,'CTM-architecture-questionnaire.html'),html);
assert.equal(/(?:src|href)="https?:/i.test(html),false);
assert.equal(/<script src=/.test(html),false);
console.log('PASS: 39 unique questions; all unanswered initially; JSON round-trip, Unicode, clarification-only responses, copy text and invalid-import rejection checked. Generated standalone HTML and Markdown companion. Browser rendering was not tested.');
