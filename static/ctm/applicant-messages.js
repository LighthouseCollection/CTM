/* Applicant-only private thread. Stable replay keys and portal read evidence are distinct from email delivery. */
(() => {
 "use strict";
 const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
 const time=value=>typeof value==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&Number.isFinite(Date.parse(value));
 const key=value=>typeof value==="string"&&!!value.trim()&&value.length<=100;
 function ownParty(record,caseId){
  if(!uuid(caseId)||record?.id!==caseId||!Array.isArray(record.parties))return null;
  const own=record.parties.filter(p=>p?.is_self===true);
  return own.length===1&&uuid(own[0].id)?own[0].id:null;
 }
 const canSend=(record,caseId)=>!!ownParty(record,caseId)&&record.can_message===true;
 function validRow(row,party){return !!row&&uuid(row.id)&&typeof row.body==="string"&&typeof row.sender==="string"&&
  ['portal','email','call'].includes(row.channel)&&time(row.timestamp)&&(row.idempotency_key===null||key(row.idempotency_key))&&
  Array.isArray(row.file_links)&&row.file_links.every(uuid)&&new Set(row.file_links).size===row.file_links.length&&
  Array.isArray(row.receipts)&&row.receipts.length===1&&row.receipts[0]?.party_id===party&&
  (row.receipts[0].read_at===null||time(row.receipts[0].read_at));}
 function validPage(page,offset,party){return Number.isSafeInteger(offset)&&offset>=0&&uuid(party)&&Array.isArray(page?.items)&&
  page.items.length<=50&&page.items.every(row=>validRow(row,party))&&new Set(page.items.map(row=>row.id)).size===page.items.length&&
  (page.next_offset===null||Number.isSafeInteger(page.next_offset)&&page.next_offset===offset+50&&page.items.length===50);}
 function createSendSession(caseId,api,changed=()=>{},newKey=()=>window.crypto.randomUUID()){
  const state={busy:false,attempted:false,acknowledged:false,error:null,receipt:null,attempt:null};
  async function transmit(){state.busy=true;state.error=null;changed();
   try{const result=await api(`/api/cases/${caseId}/messages/`,{method:'POST',body:JSON.stringify(state.attempt)});
    if(!uuid(result?.id))throw Error('Invalid message acknowledgement');state.receipt=result.id;state.acknowledged=true;return true;
   }catch(error){state.error=[401,403,404].includes(error?.status)?'denied':'uncertain';return false;}
   finally{state.busy=false;changed();}}
  return {state,async send(record,body){
   if(state.busy||state.attempted||!canSend(record,caseId)||typeof body!=='string'||!body.trim()||body.length>100000)return false;
   const idempotency_key=newKey();if(!key(idempotency_key))return false;
   state.attempt=Object.freeze({body,party_ids:Object.freeze([ownParty(record,caseId)]),channel:'portal',email_timing:'immediate',
    session_id:null,file_ids:Object.freeze([]),idempotency_key});state.attempted=true;return transmit();
  },async retry(record){
   if(state.busy||!state.attempted||state.acknowledged||state.error!=='uncertain'||!canSend(record,caseId)||ownParty(record,caseId)!==state.attempt.party_ids[0])return false;
   return transmit();
  },reconcile(rows){
   if(state.busy||!state.attempt||!Array.isArray(rows))return false;
   const match=rows.find(row=>validRow(row,state.attempt.party_ids[0])&&row.idempotency_key===state.attempt.idempotency_key&&
    row.body===state.attempt.body&&row.channel==='portal'&&row.file_links.length===0);
   if(!match)return false;state.acknowledged=true;state.receipt=match.id;state.error=null;changed();return true;
  }};
 }
 function createReadSession(api,changed=()=>{}){
  const state={busy:false,attempted:false,error:null,read_at:null};
  return {state,async send(row,party,confirmed){
   if(confirmed!==true||state.busy||state.attempted||!validRow(row,party)||row.receipts[0].read_at!==null)return false;
   state.busy=true;state.attempted=true;changed();
   try{const result=await api(`/api/messages/${row.id}/read/`,{method:'POST',body:'{}'});
    if(result?.id!==row.id||!time(result.read_at))throw Error('Invalid read acknowledgement');state.read_at=result.read_at;return true;
   }catch{state.error='readUncertain';return false;}finally{state.busy=false;changed();}
  }};
 }
 const words={en:{title:'Private case messages',refresh:'Refresh thread',more:'Load more messages',loading:'Loading private messages…',empty:'No messages are listed.',
  unavailable:'This private thread is unavailable. Refresh or sign in again.',message:'Your message',review:'Review message',edit:'Continue editing message',send:'Send private message',
  uncertain:'Sending was not confirmed. Refresh the thread to check for your original message before retrying.',denied:'Message access is unavailable. Refresh or sign in again.',
  sent:'The server received your message.',frozen:'This attempt keeps its original text, recipient and replay key.',retry:'Retry original message',fresh:'Start a new message',
  readonly:'This case is not accepting new messages.',read:'Mark my copy as read',readTitle:'Your portal copy',unread:'No portal read acknowledgement is recorded for your copy.',
  readAt:'Your copy was marked read at',readHelp:'This records your portal acknowledgement. It does not confirm email delivery.',readUncertain:'Read acknowledgement was not confirmed. Refresh the thread before trying again.',
  attachments:'This message references case documents. Use the authorized document workspace to access originals.',discardHelp:'Your local message has not been confirmed. Leaving will discard this local attempt.',
  discard:'Discard local message',keep:'Keep editing',working:'Processing…'},
 ar:{title:'رسائل القضية الخاصة',refresh:'تحديث المحادثة',more:'تحميل المزيد من الرسائل',loading:'جارٍ تحميل الرسائل الخاصة…',empty:'لا توجد رسائل مدرجة.',
  unavailable:'هذه المحادثة الخاصة غير متاحة. حدّث الصفحة أو سجّل الدخول مجددًا.',message:'رسالتك',review:'مراجعة الرسالة',edit:'متابعة تعديل الرسالة',send:'إرسال رسالة خاصة',
  uncertain:'لم يتم تأكيد الإرسال. حدّث المحادثة للتحقق من رسالتك الأصلية قبل إعادة المحاولة.',denied:'الوصول إلى الرسائل غير متاح. حدّث الصفحة أو سجّل الدخول مجددًا.',
  sent:'استلم الخادم رسالتك.',frozen:'تحتفظ هذه المحاولة بالنص الأصلي والمستلم ومفتاح إعادة المحاولة.',retry:'إعادة محاولة الرسالة الأصلية',fresh:'بدء رسالة جديدة',
  readonly:'هذه القضية لا تقبل رسائل جديدة.',read:'تأكيد قراءة نسختي',readTitle:'نسختك في البوابة',unread:'لا يوجد تأكيد قراءة مسجّل لنسختك في البوابة.',readAt:'تم تأكيد قراءة نسختك في',
  readHelp:'يسجّل هذا الإجراء تأكيدك في البوابة، ولا يؤكد تسليم البريد الإلكتروني.',readUncertain:'لم يتم تأكيد القراءة. حدّث المحادثة قبل إعادة المحاولة.',
  attachments:'تشير هذه الرسالة إلى مستندات القضية. استخدم مساحة المستندات المصرّح بها للوصول إلى الأصول.',discardHelp:'لم يتم تأكيد رسالتك المحلية. المغادرة ستتجاهل هذه المحاولة المحلية.',
  discard:'تجاهل الرسالة المحلية',keep:'متابعة التحرير',working:'جارٍ المعالجة…'}};
 function ReadCopy({row,party,api,t,disabled,onStart,onEnd}){
  const R=window.React,P=window.Plenix,h=R.createElement,[,render]=R.useReducer(n=>n+1,0);
  const session=R.useMemo(()=>createReadSession(api,render),[row.id,row.receipts[0].read_at,api]);
  const readAt=session.state.read_at||row.receipts[0].read_at;
  return h(P.Stack,null,h(P.Text,null,readAt?t('readAt'):t('unread')),
   readAt?h(P.Text,null,h('bdi',{dir:'ltr'},readAt)):null,
   session.state.error?h(P.Notice,{tone:'warning',role:'alert'},t(session.state.error)):null,
   !readAt?h(P.Button,{disabled:disabled||session.state.attempted,onClick:async()=>{onStart();try{await session.send(row,party,true);}finally{onEnd();}}},t('read')):null);
 }
 function Thread({caseId,api,lang='en',onNavigationGuard}){
  const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==='ar'?'ar':'en'][key];
  const [record,setRecord]=R.useState(null),[rows,setRows]=R.useState([]),[next,setNext]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false);
  const [body,setBody]=R.useState(''),[reviewed,setReview]=R.useState(false),[epoch,newAttempt]=R.useState(0),[checked,setChecked]=R.useState(false),[pending,setPending]=R.useState(null),[reading,setReading]=R.useState(0);
  const [,render]=R.useReducer(n=>n+1,0),ticket=R.useRef(0),current=R.useRef([]);
  const session=R.useMemo(()=>createSendSession(caseId,api,render),[caseId,api,epoch]),state=session.state;
  const busy=state.busy||reading>0,dirty=!!body.trim()&&!state.acknowledged;
  const load=async(offset=0)=>{
   const request=++ticket.current;setLoading(true);setError(false);setChecked(false);
   if(offset===0){setRecord(null);setRows([]);current.current=[];setNext(null);}
   try{const [own,page]=await Promise.all([api(`/api/cases/${caseId}/`),api(`/api/cases/${caseId}/messages/?offset=${offset}`)]);
    if(request!==ticket.current)return;
    const party=ownParty(own,caseId);if(!party||typeof own.can_message!=='boolean'||!validPage(page,offset,party))throw Error('Invalid own thread');
    const combined=offset===0?page.items:[...current.current,...page.items];
    if(new Set(combined.map(row=>row.id)).size!==combined.length)throw Error('Repeated message page');
    current.current=combined;setRows(combined);setRecord(own);setNext(page.next_offset);setChecked(true);session.reconcile(combined);
   }catch{if(request===ticket.current){current.current=[];setRecord(null);setRows([]);setNext(null);setError(true);}}
   finally{if(request===ticket.current)setLoading(false);}
  };
  R.useEffect(()=>{load(0);return()=>{ticket.current++;};},[caseId,api]);
  R.useEffect(()=>{if(!dirty&&!busy)return;const warn=event=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty,busy]);
  const navigate=action=>{if(busy)return;if(dirty)setPending(()=>action);else action();};
  R.useEffect(()=>{onNavigationGuard?.(navigate);return()=>onNavigationGuard?.(null);},[onNavigationGuard,dirty,busy]);
  const party=ownParty(record,caseId),blocked=loading||!canSend(record,caseId)||busy||state.attempted;
  return h(P.LocaleProvider,{locale:lang==='ar'?'ar':'en',dir:lang==='ar'?'rtl':'ltr'},h(P.Stack,{as:'section',lang,dir:lang==='ar'?'rtl':'ltr'},
   h(P.Text,{as:'h1',variant:'display'},t('title')),
   pending?h(P.Notice,{tone:'warning',role:'alert'},h(P.Stack,null,t('discardHelp'),h(P.Inline,null,
    h(P.Button,{disabled:busy,onClick:()=>{if(!busy){const move=pending;setPending(null);move();}}},t('discard')),
    h(P.Button,{disabled:busy,onClick:()=>setPending(null)},t('keep'))))):null,
   h(P.Button,{disabled:loading||busy,onClick:()=>load(0)},t('refresh')),
   loading?h(P.Text,{role:'status'},t('loading')):null,error?h(P.Notice,{tone:'warning',role:'alert'},t('unavailable')):null,
   record?h(P.Stack,null,h(P.Text,null,t('readHelp')),!rows.length&&!loading?h(P.Text,null,t('empty')):null,
    ...rows.map(row=>h(P.Panel,{key:row.id,title:row.sender},h(P.Stack,null,
     h(P.Text,null,h('bdi',{dir:'ltr'},row.timestamp)),h(P.Text,null,row.body),row.file_links.length?h(P.Text,null,t('attachments')):null,
     h(ReadCopy,{row,party,api,t,disabled:loading||busy,onStart:()=>setReading(n=>n+1),onEnd:()=>setReading(n=>Math.max(0,n-1))})))),
    next!==null?h(P.Button,{disabled:loading||busy,onClick:()=>load(next)},t('more')):null,
    !canSend(record,caseId)?h(P.Notice,null,t('readonly')):null,
    state.error?h(P.Notice,{tone:'warning',role:'alert'},t(state.error)):null,state.acknowledged?h(P.Notice,{role:'status'},t('sent')):null,
    state.attempted?h(P.Notice,null,t('frozen')):null,
    reviewed?h(P.Panel,{title:t('review')},h(P.Text,null,body)):h(P.Field,{label:t('message')},h(P.Textarea,{value:body,rows:5,maxLength:100000,disabled:blocked,onChange:event=>{setBody(event.target.value);setReview(false);}})),
    h(P.Inline,{wrap:true},h(P.Button,{disabled:blocked||!body.trim(),onClick:()=>setReview(!reviewed)},t(reviewed?'edit':'review')),
     h(P.Button,{disabled:blocked||!reviewed,onClick:()=>{setChecked(false);session.send(record,body);}},t(state.busy?'working':'send'))),
    checked&&state.error==='uncertain'&&!state.acknowledged?h(P.Button,{disabled:loading||busy||!canSend(record,caseId),onClick:()=>{setChecked(false);session.retry(record);}},t('retry')):null,
    checked&&state.acknowledged?h(P.Button,{disabled:loading||busy,onClick:()=>{setBody('');setReview(false);setChecked(false);newAttempt(n=>n+1);}},t('fresh')):null):null));
 }
 window.CTMApplicantMessages={ownParty,canSend,validPage,createSendSession,createReadSession,Thread};
})();
