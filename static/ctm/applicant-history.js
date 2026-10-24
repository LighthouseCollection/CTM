/* Own saved answer revisions. Historical wording is not inferred from the current form. */
(() => {
 "use strict";
 const uuid=x=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x);
 const time=x=>typeof x==='string'&&/(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x));
 function validJSON(value,depth=0,budget={left:20000}){
  if(depth>20||--budget.left<0)return false;
  if(value===null||typeof value==='boolean')return true;
  if(typeof value==='string')return value.length<=1000000;
  if(typeof value==='number')return Number.isFinite(value);
  if(Array.isArray(value))return value.every(v=>validJSON(v,depth+1,budget));
  return !!value&&typeof value==='object'&&Object.entries(value).every(([k,v])=>k.length<=1000&&validJSON(v,depth+1,budget));
 }
 function validHistory(data,version){return Number.isSafeInteger(version)&&version>=0&&Array.isArray(data?.items)&&data.items.length<=500&&
  new Set(data.items.map(row=>row?.id)).size===data.items.length&&data.items.every((row,i)=>row&&uuid(row.id)&&
   Number.isSafeInteger(row.version)&&row.version>0&&row.version<=version&&(!i||row.version>data.items[i-1].version)&&
   typeof row.actor==='string'&&time(row.timestamp)&&!!row.answers&&!Array.isArray(row.answers)&&typeof row.answers==='object'&&validJSON(row.answers));}
 const token=value=>value.replace(/~/g,'~0').replace(/\//g,'~1');
 function flatten(answers){
  const result=[];
  function visit(value,path){
   if(Array.isArray(value)&&value.length&&value.every(row=>row&&typeof row==='object'&&!Array.isArray(row)&&uuid(row.id))&&new Set(value.map(row=>row.id)).size===value.length){
    result.push({path:path+'/$order',value:value.map(row=>row.id)});for(const row of value)visit(row,path+'/@'+row.id);return;
   }
   if(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length){for(const k of Object.keys(value).sort())visit(value[k],path+'/'+token(k));return;}
   result.push({path,value});
  }
  if(!validJSON(answers))throw Error('Unsupported answer snapshot');if(Object.keys(answers).length)visit(answers,'');return result;
 }
 const canonical=value=>value&&typeof value==='object'?(Array.isArray(value)?'['+value.map(canonical).join(',')+']':'{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}'):JSON.stringify(value);
 function compare(before,after){
  const a=new Map(flatten(before).map(row=>[row.path,row.value])),b=new Map(flatten(after).map(row=>[row.path,row.value]));
  return [...new Set([...a.keys(),...b.keys()])].sort().filter(path=>a.has(path)!==b.has(path)||canonical(a.get(path))!==canonical(b.get(path))).map(path=>
   ({path,before_present:a.has(path),after_present:b.has(path),before:a.has(path)?a.get(path):null,after:b.has(path)?b.get(path):null}));
 }
 const words={en:{title:'My saved answer history',open:'View saved answer history',close:'Hide answer history',refresh:'Refresh answer history',loading:'Loading saved revisions…',
  unavailable:'Saved answer history is unavailable or has changed. Refresh the application and try again.',empty:'No saved revisions are listed.',version:'Saved version',actor:'Recorded by',unnamed:'Name not supplied',time:'Server time',
  wording:'Historical question wording is not supplied by this endpoint. Any question labels below come from your current form; the saved values and field paths are retained originals.',
  changes:'Changes from preceding saved version',before:'Previous saved value',after:'Selected saved value',absent:'Not present in this version',unchanged:'No value changes are listed.',field:'Saved field'},
 ar:{title:'سجل إجاباتي المحفوظة',open:'عرض سجل الإجابات المحفوظة',close:'إخفاء سجل الإجابات',refresh:'تحديث سجل الإجابات',loading:'جارٍ تحميل النسخ المحفوظة…',
  unavailable:'سجل الإجابات المحفوظة غير متاح أو تغيّر. حدّث الطلب وحاول مجددًا.',empty:'لا توجد نسخ محفوظة مدرجة.',version:'النسخة المحفوظة',actor:'سجّلها',unnamed:'الاسم غير متوفر',time:'وقت الخادم',
  wording:'لا توفّر هذه الخدمة صياغة الأسئلة التاريخية. عناوين الأسئلة أدناه من نموذجك الحالي؛ والقيم ومسارات الحقول هي الأصول المحفوظة.',
  changes:'التغييرات عن النسخة المحفوظة السابقة',before:'القيمة المحفوظة السابقة',after:'القيمة المحفوظة المحددة',absent:'غير موجودة في هذه النسخة',unchanged:'لا توجد تغييرات مدرجة في القيم.',field:'حقل محفوظ'}};
 function History({applicationId,currentVersion,currentFields=[],api,lang='en',disabled=false}){
  const R=window.React,P=window.Plenix,h=R.createElement,t=k=>words[lang==='ar'?'ar':'en'][k];
  const [open,setOpen]=R.useState(false),[data,setData]=R.useState(null),[selected,select]=R.useState(''),[error,setError]=R.useState(false),[loading,setLoading]=R.useState(false),[revision,reload]=R.useState(0),[fieldPath,setFieldPath]=R.useState(null);
  R.useEffect(()=>{
   let active=true;setData(null);setError(false);select('');setFieldPath(null);
   if(!uuid(applicationId))return()=>{active=false;};setLoading(true);
   api(`/api/applications/${applicationId}/history/`).then(result=>{
    if(!validHistory(result,currentVersion))throw Error('Invalid own history');
    if(active){setData(result);select(String(result.items.at(-1)?.version??''));}
   }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};
  },[applicationId,currentVersion,api,revision]);
  if(!uuid(applicationId))return null;
  const index=data?.items.findIndex(row=>String(row.version)===selected)??-1,row=index>=0?data.items[index]:null;
  const changes=row?compare(index>0?data.items[index-1].answers:{},row.answers):[];
  const label=path=>{const code=path.split('/')[1]?.replace(/~1/g,'/').replace(/~0/g,'~');const field=currentFields.find(f=>f.code===code);return field?.[lang==='ar'?'label_ar':'label_en']||t('field');};
  const value=(present,v)=>present?JSON.stringify(v):t('absent');
  return h(P.Panel,{title:t('title')},h(P.Stack,null,
   h(P.Button,{disabled,onClick:()=>{setFieldPath(null);setOpen(true);}},t('open')),
   ...changes.map(change=>h(P.Button,{key:'open-field'+change.path,disabled,onClick:()=>{setFieldPath(change.path);setOpen(true);}},label(change.path)+': '+change.path)),
   h(P.Dialog,{open,onClose:()=>setOpen(false),title:t('title'),closeLabel:t('close'),size:'lg'},h(P.Stack,null,h(P.Text,null,t('wording')),h(P.Button,{disabled:disabled||loading,onClick:()=>reload(n=>n+1)},t('refresh')),
    loading?h(P.Text,{role:'status'},t('loading')):null,error?h(P.Notice,{tone:'warning',role:'alert'},t('unavailable')):null,
    data?h(P.Stack,null,!data.items.length?h(P.Text,null,t('empty')):null,
     data.items.length?h(P.Field,{label:t('version')},h(P.Select,{value:selected,onChange:event=>{setFieldPath(null);select(event.target.value);},options:data.items.map(item=>({value:String(item.version),label:String(item.version)}))})):null,
     row?h(P.Stack,null,h(P.Text,null,t('actor'),': ',row.actor||t('unnamed')),h(P.Text,null,t('time'),': ',h('bdi',{dir:'ltr'},row.timestamp)),
      h(P.Text,{as:'h3'},t('changes')),!changes.length?h(P.Text,null,t('unchanged')):null,
      ...changes.map(change=>h(P.Button,{key:'indicator'+change.path,onClick:()=>setFieldPath(fieldPath===change.path?null:change.path),'aria-pressed':fieldPath===change.path},label(change.path)+': '+change.path)),
      ...changes.filter(change=>!fieldPath||change.path===fieldPath).map(change=>h(P.Panel,{key:change.path,title:label(change.path)},h(P.Stack,null,h(P.Text,null,h('bdi',{dir:'ltr'},change.path)),
       h(P.Text,null,t('before'),': ',value(change.before_present,change.before)),h(P.Text,null,t('after'),': ',value(change.after_present,change.after)))))):null,
     ):null))));
 }
 window.CTMApplicantHistory={validHistory,flatten,compare,History};
})();
