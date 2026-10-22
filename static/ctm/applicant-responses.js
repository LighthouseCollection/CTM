/* Prepared bound intake response. Missing authoritative capability/version leaves it unavailable. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const text=value=>typeof value==="string"&&!!value.trim();
  function canRespond(row){return uuid(row?.id)&&row.kind==="intake"&&row.state==="sent"&&row.can_respond===true&&
    Number.isSafeInteger(row.response_version)&&row.response_version>0&&["en","ar","both"].includes(row.language)&&
    Array.isArray(row.questions)&&row.questions.length>0&&row.questions.every(q=>text(q?.code)&&
      !["__proto__","prototype","constructor"].includes(q.code)&&Number.isSafeInteger(q.version)&&q.version>0&&
      (row.language==="ar"||text(q.en))&&(row.language==="en"||text(q.ar)))&&
    new Set(row.questions.map(q=>q.code)).size===row.questions.length;}
  function createResponseSession(row,api,changed=()=>{}){
    const state={busy:false,locked:false,received:false,error:null};
    return {state,async send(answers){
      if(!canRespond(row)||state.busy||state.locked||!answers||Array.isArray(answers)||typeof answers!=="object"||
        Object.keys(answers).some(code=>!row.questions.some(q=>q.code===code)||typeof answers[code]!=="string")||
        !Object.values(answers).some(text))return false;
      const frozen=structuredClone({answers,expected_version:row.response_version});
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
    denied:"This request is no longer available for response. Your local response is preserved.",empty:"No response entered",busy:"Submitting…"},
    ar:{respond:"الإجابة عن الطلب",back:"العودة إلى الطلبات",review:"مراجعة الإجابة",edit:"تعديل الإجابة",submit:"تقديم الإجابة",
      discard:"تجاهل الإجابة المحلية",keep:"متابعة التحرير",unsaved:"لم تُقدّم إجابتك المحلية. هل تريد تجاهلها قبل المغادرة؟",
      received:"أقرّ الخادم باستلام التقرير. حدّث قائمة الطلبات للتحقق من حالته الحالية.",
      uncertain:"نتيجة التقديم غير مؤكدة. حُفظت إجابتك محليًا. حدّث قائمة الطلبات قبل محاولة تقديم أخرى.",
      denied:"لم يعد هذا الطلب متاحًا للإجابة. حُفظت إجابتك محليًا.",empty:"لم تُدخل إجابة",busy:"جارٍ التقديم…"}};
  function ResponseEditor({request,api,lang="en",onBack,onNavigationGuard}){
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [answers,setAnswers]=R.useState({}),[review,setReview]=R.useState(false),[pending,setPending]=R.useState(null),[,render]=R.useReducer(n=>n+1,0);
    const session=R.useMemo(()=>createResponseSession(request,api,render),[request,api]),state=session.state;
    const dirty=Object.values(answers).some(text)&&!state.received;
    const navigate=action=>{if(state.busy)return;if(dirty)setPending(()=>action);else action();};
    R.useEffect(()=>{onNavigationGuard?.(navigate);return()=>onNavigationGuard?.(null);},[onNavigationGuard,dirty,state.busy]);
    R.useEffect(()=>{if(!dirty&&!state.busy)return;const warn=e=>{e.preventDefault();e.returnValue="";};
      window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[dirty,state.busy]);
    if(!canRespond(request))return null;
    return h(P.Panel,{title:request.title},h(P.Stack,null,
      h(P.Button,{disabled:state.busy,onClick:()=>navigate(onBack)},t("back")),
      pending?h(P.Notice,{tone:"warning",role:"alert"},h(P.Stack,null,t("unsaved"),h(P.Inline,{wrap:true},
        h(P.Button,{onClick:()=>{const action=pending;setPending(null);action();}},t("discard")),
        h(P.Button,{onClick:()=>setPending(null)},t("keep"))))):null,
      ...request.questions.map(q=>{const language=request.language==="both"?(lang==="ar"?"ar":"en"):request.language,label=q[language];
        return h(P.Field,{key:q.code,label},review||state.locked?h(P.Text,{dir:"auto"},answers[q.code]||t("empty")):
          h(P.Textarea,{value:answers[q.code]||"",dir:"auto",onChange:e=>setAnswers({...answers,[q.code]:e.target.value})}));}),
      state.error?h(P.Notice,{tone:"warning",role:"alert"},t(state.error)):null,
      state.received?h(P.Notice,{role:"status"},t("received")):null,
      h(P.Inline,{wrap:true},h(P.Button,{disabled:state.locked||!dirty,onClick:()=>setReview(!review)},t(review?"edit":"review")),
        review?h(P.Button,{disabled:state.locked||!dirty,onClick:()=>session.send(answers)},t(state.busy?"busy":"submit")):null)
    ));
  }
  window.CTMApplicantResponses={canRespond,createResponseSession,ResponseEditor};
})();
