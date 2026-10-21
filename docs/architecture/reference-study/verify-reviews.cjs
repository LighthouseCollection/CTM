// Lightweight DOM contract check, not browser rendering or a replacement for visual QA.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
for(const slug of ['application-review','template-review']){
 const html=fs.readFileSync(path.join(__dirname,slug+'.html'),'utf8');
 const script=html.match(/<script>\n([\s\S]*)\n<\/script>/)[1];
 const ids=new Map();
 class Element{
  constructor(tag){this.tagName=tag;this.children=[];this.listeners={};this.value='';this.checked=false;this.hidden=false;this._id='';}
  set id(value){this._id=value;ids.set(value,this);}get id(){return this._id;}
  append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}
  setAttribute(key,value){this[key]=value;}addEventListener(type,handler){this.listeners[type]=handler;}
  querySelectorAll(tag){return this.children.flatMap(c=>c instanceof Element?[...(c.tagName===tag?[c]:[]),...c.querySelectorAll(tag)]:[]);}
  focus(){this.focused=true;}select(){}click(){this.listeners.click?.();}remove(){}
 }
 const document={createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text}),getElementById:id=>ids.get(id),body:new Element('body')};
 for(const m of html.matchAll(/id="([^"]+)"/g)){const e=new Element('static');e.id=m[1];}
 const saved=new Map();
 const ctx=vm.createContext({document,localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)},window:{addEventListener(){},confirm:()=>true,print(){}},navigator:{clipboard:{writeText:async()=>{}}},setTimeout:()=>1,clearTimeout(){},Blob,URL,console});
 vm.runInContext(script,ctx);
 const run=code=>vm.runInContext(code,ctx);
 const count=run('questions.length');
 const inputs=ids.get('questions').querySelectorAll('input');
 assert.equal(inputs.length,count*3);
 assert(inputs.every(input=>input.checked===false));
 const other=inputs.find(input=>input.value==='other');other.checked=true;other.listeners.change();
 const note=ids.get('note-'+other.name);assert.equal(note.focused,true);
 note.value='My preferred process العربية';note.listeners.input();
 assert.equal(run('payload().answers[0].answer'),'other');
 assert.equal(run('payload().answers[0].clarification'),'My preferred process العربية');
 run('save()');assert.equal(saved.size,1);
 const clear=ids.get('question-'+other.name).querySelectorAll('button')[0];clear.click();
 assert.equal(run('payload().answers[0].answer'),null);
 assert.equal(run('payload().answers[0].clarification'),'My preferred process العربية');
 run('el("transfer-text").value=chatText()');
 assert.match(ids.get('transfer-text').value,/UNDECIDED/);
 console.log(`PASS: ${slug}: rendered ${count*3} radio controls; no defaults; Other focuses textarea; notes/export/local save/clear preserve correct state. Browser visuals not tested.`);
}

