/* Applicant private notifications. Payload internals are never rendered or used as access grants. */
(() => {
 "use strict";
 const uuid=x=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x);
 const time=x=>typeof x==='string'&&/(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x));
 const validRow=row=>!!row&&uuid(row.id)&&typeof row.kind==='string'&&typeof row.read==='boolean'&&time(row.timestamp)&&
  (row.case_id===null||uuid(row.case_id))&&(row.case_number===null||typeof row.case_number==='string');
 function validPage(page,offset){return Number.isSafeInteger(offset)&&offset>=0&&Array.isArray(page?.items)&&page.items.length<=50&&page.items.every(validRow)&&
  new Set(page.items.map(row=>row.id)).size===page.items.length&&Number.isSafeInteger(page.unread_count)&&page.unread_count>=0&&
  (page.next_offset===null||Number.isSafeInteger(page.next_offset)&&page.next_offset===offset+50&&page.items.length===50);}
 function createReadSession(api,changed=()=>{}){
  const state={busy:false,attempted:false,confirmed:false,error:null};
  return {state,async send(row,confirmed){
   if(confirmed!==true||state.busy||state.attempted||!validRow(row)||row.read)return false;
   state.busy=true;state.attempted=true;changed();
   try{const result=await api('/api/notifications/',{method:'POST',body:JSON.stringify({id:row.id})});
    if(result?.updated!==true){state.error='refreshRequired';return false;}state.confirmed=true;return true;
   }catch{state.error='uncertain';return false;}finally{state.busy=false;changed();}
  }};
 }
 const words={en:{title:'My notifications',refresh:'Refresh notifications',more:'Load more notifications',loading:'Loading private notifications…',empty:'No notifications are listed.',
  unread:'Unread',read:'Read',count:'Unread notifications',update:'Case update',mark:'Mark notification as read',open:'Open case',
  unavailable:'Notifications are unavailable or the list changed. Refresh to load the current private list.',
  refreshRequired:'Read status was not confirmed. Refresh notifications to check the current status.',uncertain:'Acknowledgement was not confirmed. Refresh before trying again.',
  help:'This acknowledges a portal notification. It does not confirm message reading or email delivery.'},
 ar:{title:'إشعاراتي',refresh:'تحديث الإشعارات',more:'تحميل المزيد من الإشعارات',loading:'جارٍ تحميل الإشعارات الخاصة…',empty:'لا توجد إشعارات مدرجة.',
  unread:'غير مقروء',read:'مقروء',count:'الإشعارات غير المقروءة',update:'تحديث القضية',mark:'تأكيد قراءة الإشعار',open:'فتح القضية',
  unavailable:'الإشعارات غير متاحة أو تغيّرت القائمة. حدّثها لتحميل القائمة الخاصة الحالية.',refreshRequired:'لم يتم تأكيد حالة القراءة. حدّث الإشعارات للتحقق من الحالة الحالية.',
  uncertain:'لم يتم تأكيد الاستلام. حدّث القائمة قبل إعادة المحاولة.',help:'يؤكد هذا الإجراء إشعار البوابة، ولا يؤكد قراءة الرسالة أو تسليم البريد الإلكتروني.'}};
 function NoticeRow({row,api,t,disabled,onStart,onEnd,onOpen}){
  const R=window.React,P=window.Plenix,h=R.createElement,[,render]=R.useReducer(n=>n+1,0);
  const session=R.useMemo(()=>createReadSession(api,render),[row.id,api]);
  return h(P.Panel,{title:row.case_number||t('update')},h(P.Stack,null,h(P.Text,null,t('update')),h(P.Text,null,h('bdi',{dir:'ltr'},row.timestamp)),
   h(P.Text,{role:'status'},t(row.read||session.state.confirmed?'read':'unread')),
   session.state.error?h(P.Notice,{tone:'warning',role:'alert'},t(session.state.error)):null,
   h(P.Inline,{wrap:true},row.case_id?h(P.Button,{disabled,onClick:()=>onOpen(row.case_id)},t('open')):null,
    !row.read&&!session.state.confirmed?h(P.Button,{disabled:disabled||session.state.attempted,onClick:async()=>{onStart();try{await session.send(row,true);}finally{onEnd();}}},t('mark')):null)));
 }
 function Inbox({api,lang='en',onCase,onNavigationGuard}){
  const R=window.React,P=window.Plenix,h=R.createElement,t=k=>words[lang==='ar'?'ar':'en'][k];
  const [rows,setRows]=R.useState([]),[next,setNext]=R.useState(null),[count,setCount]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false),[busy,setBusy]=R.useState(0);
  const ticket=R.useRef(0),current=R.useRef([]),[epoch,reset]=R.useState(0);
  async function load(offset=0){const request=++ticket.current;setLoading(true);setError(false);
   if(offset===0){current.current=[];setRows([]);setNext(null);setCount(null);reset(n=>n+1);}
   try{const page=await api(`/api/notifications/?offset=${offset}`);if(request!==ticket.current)return;
    if(!validPage(page,offset))throw Error('Invalid own notifications');const combined=offset===0?page.items:[...current.current,...page.items];
    if(new Set(combined.map(row=>row.id)).size!==combined.length)throw Error('Notification pages changed');
    current.current=combined;setRows(combined);setNext(page.next_offset);setCount(page.unread_count);
   }catch{if(request===ticket.current){current.current=[];setRows([]);setNext(null);setCount(null);setError(true);}}
   finally{if(request===ticket.current)setLoading(false);}}
  R.useEffect(()=>{load(0);return()=>{ticket.current++;};},[api]);
  R.useEffect(()=>{const guard=move=>{if(!busy)move();};onNavigationGuard?.(guard);return()=>onNavigationGuard?.(null);},[busy,onNavigationGuard]);
  R.useEffect(()=>{if(!busy)return;const warn=event=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[busy]);
  return h(P.LocaleProvider,{locale:lang==='ar'?'ar':'en',dir:lang==='ar'?'rtl':'ltr'},h(P.Stack,{as:'section',lang,dir:lang==='ar'?'rtl':'ltr'},
   h(P.Text,{as:'h1',variant:'display'},t('title')),h(P.Text,null,t('help')),
   h(P.Button,{disabled:loading||busy>0,onClick:()=>load(0)},t('refresh')),
   loading?h(P.Text,{role:'status'},t('loading')):null,error?h(P.Notice,{tone:'warning',role:'alert'},t('unavailable')):null,
   count!==null?h(P.Text,null,t('count'),': ',h('bdi',{dir:'ltr'},String(count))):null,
   !rows.length&&!loading&&!error?h(P.Text,null,t('empty')):null,
   ...rows.map(row=>h(NoticeRow,{key:row.id+':'+epoch,row,api,t,disabled:loading||busy>0,onStart:()=>setBusy(n=>n+1),onEnd:()=>{setBusy(n=>Math.max(0,n-1));setCount(null);},onOpen:id=>onCase?.(id)})),
   next!==null?h(P.Button,{disabled:loading||busy>0,onClick:()=>load(next)},t('more')):null));
 }
 window.CTMApplicantNotifications={validPage,createReadSession,Inbox};
})();
