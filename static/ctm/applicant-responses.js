/* Bound own request response. No inferred capability, observations or blind replay. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const text=value=>typeof value==="string"&&!!value.trim();
  const fingerprint=value=>typeof value==="string"&&/^[0-9a-f]{64}$/.test(value);
  function canRespond(row){return uuid(row?.id)&&uuid(row.proceeding_id)&&["intake","medical","psychological"].includes(row.kind)&&row.state==="sent"&&row.can_respond===true&&
    fingerprint(row.request_version)&&["en","ar","both"].includes(row.language)&&
    (row.kind==="intake"||window.CTMApplicantAssessments?.hasSignedScope(row)===true)&&
    Array.isArray(row.questions)&&(row.kind!=="intake"||row.questions.length>0)&&row.questions.every(q=>text(q?.code)&&
      !["__proto__","prototype","constructor"].includes(q.code)&&Number.isSafeInteger(q.version)&&q.version>0&&
      (row.language==="ar"||text(q.en))&&(row.language==="en"||text(q.ar)))&&
    new Set(row.questions.map(q=>q.code)).size===row.questions.length;}
  function createResponseSession(row,api,changed=()=>{}){
    const state={busy:false,locked:false,received:false,error:null};
    return {state,async send(answers,latest=row,files=[]){
      const ids=answers?.files===undefined?[]:answers.files;
      if(!canRespond(latest)||latest.id!==row.id||latest.proceeding_id!==row.proceeding_id||latest.request_version!==row.request_version||
        state.busy||state.locked||!answers||Array.isArray(answers)||typeof answers!=="object"||
        Object.keys(answers).some(code=>code!=="files"&&(!row.questions.some(q=>q.code===code)||typeof answers[code]!=="string"))||
        row.questions.some(q=>!text(answers[q.code]))||!Array.isArray(ids)||new Set(ids).size!==ids.length||
        ids.some(id=>!files.some(f=>f.id===id&&f.purpose==="report"&&window.CTMApplicantAssessments?.safeURL(f)))||
        (row.kind!=="intake"&&!ids.length)||!Object.keys(answers).length)return false;
      const frozen=structuredClone({answers,expected_version:row.request_version});
      state.busy=true;state.locked=true;state.error=null;changed();
      try{
        const result=await api(`/api/requests/${row.id}/complete/`,{method:"POST",body:JSON.stringify(frozen)});
        if(!uuid(result?.id))throw Error("Invalid report acknowledgement");state.received=true;return true;
      }catch(error){state.error=[401,403,404].includes(error?.status)?"denied":"uncertain";return false;}
      finally{state.busy=false;changed();}
    }};
  }
  const words={en:{respond:"Respond to request",back:"Back to requests",review:"Review response",edit:"Edit response",submit:"Submit response",
    discard:"Discard local response",keep:"Keep editing",unsaved:"Your local response has not been submitted. Discard it before leaving?",
    received:"The server acknowledged your report. Refresh the request list to confirm its current state.",
    uncertain:"The result is uncertain. Your local response is preserved. Refresh the request list before another submission.",
    denied:"This request is no longer available for response. Your local response is preserved.",empty:"No response entered",busy:"Submitting…",evidence:"Select report evidence",
    evidenceChanged:"Some selected evidence is no longer eligible. Refresh or remove those local selections before review.",removeEvidence:"Remove unavailable evidence selections"},
    ar:{respond:"الإجابة عن الطلب",back:"العودة إلى الطلبات",review:"مراجعة الإجابة",edit:"تعديل الإجابة",submit:"تقديم الإجابة",
      discard:"تجاهل الإجابة المحلية",keep:"متابعة التحرير",unsaved:"لم تُقدّم إجابتك المحلية. هل تريد تجاهلها قبل المغادرة؟",
      received:"أقرّ الخادم باستلام التقرير. حدّث قائمة الطلبات للتحقق من حالته الحالية.",
      uncertain:"نتيجة التقديم غير مؤكدة. حُفظت إجابتك محليًا. حدّث قائمة الطلبات قبل محاولة تقديم أخرى.",
      denied:"لم يعد هذا الطلب متاحًا للإجابة. حُفظت إجابتك محليًا.",empty:"لم تُدخل إجابة",busy:"جارٍ التقديم…",evidence:"اختر أدلة التقرير",
      evidenceChanged:"لم تعد بعض الأدلة المختارة مؤهلة. حدّث الصفحة أو أزل هذه الاختيارات المحلية قبل المراجعة.",removeEvidence:"إزالة اختيارات الأدلة غير المتاحة"}};
  function ResponseEditor({request,api,lang="en",onBack,onNavigationGuard,evidence=[],evidenceVerified=true,disabled=false,navigationBusy=false,onBusyChange,onLockChange,onRefresh,showBack=true}){
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [answers,setAnswers]=R.useState({}),[review,setReview]=R.useState(false),[pending,setPending]=R.useState(null),[,render]=R.useReducer(n=>n+1,0);
    const [fileIds,setFileIds]=R.useState([]);
    const session=R.useMemo(()=>createResponseSession(request,api,render),[request.id,request.request_version,api]),state=session.state;
    const dirty=(Object.values(answers).some(text)||fileIds.length>0)&&!state.received;
    const reportFiles=evidence.filter(f=>f.purpose==="report"&&window.CTMApplicantAssessments?.safeURL(f));
    const evidenceKey=reportFiles.map(f=>f.id).join(":");
    R.useEffect(()=>{if(evidenceVerified&&!state.locked)setReview(false);},[evidenceKey,evidenceVerified]);
    R.useEffect(()=>{onBusyChange?.(state.busy);return()=>onBusyChange?.(false);},[state.busy,onBusyChange]);
    R.useEffect(()=>{onLockChange?.(state.locked);return()=>onLockChange?.(false);},[state.locked,onLockChange]);
    const navigate=action=>{if(state.busy||navigationBusy)return;if(dirty)setPending(()=>action);else action();};
    R.useEffect(()=>{onNavigationGuard?.(navigate);return()=>onNavigationGuard?.(null);},[onNavigationGuard,dirty,state.busy,navigationBusy]);
    R.useEffect(()=>{if(!dirty&&!state.busy)return;const warn=e=>{e.preventDefault();e.returnValue="";};
      window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[dirty,state.busy]);
    if(!canRespond(request)&&!state.locked&&!dirty)return null;
    const blocked=disabled||state.locked||!canRespond(request);
    const complete=request.questions.every(q=>text(answers[q.code]))&&(request.kind==="intake"||fileIds.length>0)&&
      fileIds.every(id=>reportFiles.some(f=>f.id===id));
    return h(P.Panel,{ icon: "doc-text",title:request.title},h(P.Stack,null,
      showBack?h(P.Button,{disabled:state.busy||navigationBusy,onClick:()=>navigate(onBack)},t("back")):null,
      pending?h(P.Notice,{tone:"warning",role:"alert"},h(P.Stack,null,t("unsaved"),h(P.Inline,{wrap:true},
        h(P.Button,{disabled:state.busy||navigationBusy,onClick:()=>{if(state.busy||navigationBusy)return;const action=pending;setPending(null);action();}},t("discard")),
        h(P.Button,{disabled:state.busy||navigationBusy,onClick:()=>{if(!state.busy&&!navigationBusy)setPending(null);}},t("keep"))))):null,
      ...request.questions.map(q=>{const language=request.language==="both"?(lang==="ar"?"ar":"en"):request.language,label=q[language];
        return h(P.Field,{key:q.code,label},review||state.locked?h(P.Text,{dir:"auto"},answers[q.code]||t("empty")):
          h(P.Textarea,{value:answers[q.code]||"",dir:"auto",disabled:blocked,onChange:e=>setAnswers({...answers,[q.code]:e.target.value})}));}),
      reportFiles.length?h(P.Fieldset,{legend:t("evidence")},...reportFiles.map(file=>h(P.Checkbox,{key:file.id,label:file.name,
        checked:fileIds.includes(file.id),disabled:blocked||review,onChange:e=>setFileIds(ids=>e.target.checked?[...ids,file.id]:ids.filter(id=>id!==file.id))}))):null,
      evidenceVerified&&fileIds.some(id=>!reportFiles.some(f=>f.id===id))?h(P.Notice,{tone:"warning"},h(P.Stack,null,t("evidenceChanged"),
        h(P.Button,{disabled:blocked,onClick:()=>setFileIds(ids=>ids.filter(id=>reportFiles.some(f=>f.id===id)))},t("removeEvidence")))):null,
      state.error?h(P.Notice,{tone:"warning",role:"alert"},t(state.error)):null,
      state.received?h(P.Notice,{role:"status"},t("received")):null,
      h(P.Inline,{wrap:true},h(P.Button,{disabled:blocked||!dirty||!complete,onClick:()=>setReview(!review)},t(review?"edit":"review")),
        review?h(P.Button,{disabled:blocked||!dirty||!complete,onClick:async()=>{if(blocked)return;
          if(await session.send({...answers,...(fileIds.length?{files:fileIds}:{})},request,evidence))onRefresh?.();}},t(state.busy?"busy":"submit")):null)
    ));
  }
  window.CTMApplicantResponses={canRespond,createResponseSession,ResponseEditor};
})();
