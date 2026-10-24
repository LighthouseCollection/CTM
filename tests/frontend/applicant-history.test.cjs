const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const c={window:{}};if(fs.existsSync('static/ctm/applicant-history.js'))vm.runInNewContext(fs.readFileSync('static/ctm/applicant-history.js','utf8'),c);
const H=c.window.CTMApplicantHistory||{},id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222';
const row=(version=1)=>({id,version,answers:{name:'Saved',active:false},actor:'Actual actor',timestamp:'2026-10-21T12:00:00Z'});
test('own answer history validates ordered immutable revision metadata and strict bounded JSON',()=>{
 assert.equal(typeof H.validHistory,'function');assert.equal(H.validHistory({items:[row()]},1),true);
 assert.equal(H.validHistory({items:[row(),{...row(2),id:other}]},1),false);
 assert.equal(H.validHistory({items:[row(),row()]},2),false);
 assert.equal(H.validHistory({items:[{...row(),answers:{bad:Infinity}}]},1),false);
});
test('answer comparison distinguishes absence, null, false, zero and changed original text',()=>{
 const changes=H.compare({nullable:null,active:false,number:0,text:'Original'},{nullable:false,text:'Changed'});
 const by=new Map(changes.map(x=>[x.path,x]));assert.equal(by.get('/active').after_present,false);
 assert.equal(by.get('/nullable').before,null);assert.equal(by.get('/nullable').after,false);
 assert.equal(by.get('/number').before,0);assert.equal(by.get('/text').after,'Changed');
});
test('repeat comparison uses retained UUID identity and captures order without fabricating entries',()=>{
 const before={children:[{id,name:'First'},{id:other,name:'Second'}]};
 const after={children:[{id:other,name:'Second changed'},{id,name:'First'}]};
 const changes=H.compare(before,after);
 assert.ok(changes.some(x=>x.path===`/children/@${other}/name`&&x.after==='Second changed'));
 assert.ok(changes.some(x=>x.path==='/children/$order'));assert.equal(changes.filter(x=>x.path.endsWith('/name')).length,1);
});
test('unknown field keys and nested originals are escaped as paths and retained, independent of current labels',()=>{
 const input=JSON.parse('{"a/b~c":{"__proto__":"retained","value":"<script>literal</script>"}}');
 const rows=H.flatten(input);assert.ok(rows.some(x=>x.path==='/a~1b~0c/__proto__'&&x.value==='retained'));
 assert.ok(rows.some(x=>x.value==='<script>literal</script>'));assert.equal({}.retained,undefined);
});

test('initial saved version does not invent a removed root field for an empty predecessor',()=>{
 assert.deepEqual(JSON.parse(JSON.stringify(H.compare({}, {name:'Saved'}).map(x=>x.path))),['/name']);
});

test('nested object key order inside an unknown array is not a historical answer change',()=>{
 assert.equal(H.compare({future:[{a:1,b:2}]},{future:[{b:2,a:1}]}).length,0);
});
