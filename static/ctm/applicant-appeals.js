/* Appeal entry delegates eligibility/reuse to the server; never reopens a case. */
(() => {
  "use strict";
  const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const hasAppealContext=record=>record?.status==="closed"||
    (Array.isArray(record?.proceedings)&&record.proceedings.some(row=>row?.status==="closed"));
  function createAppealStarter(caseId,api,changed=()=>{}) {
    const state={busy:false,locked:false,error:null};
    return {state,async start(){
      if(state.busy||state.locked||!uuid.test(caseId))return null;
      state.busy=true;state.error=null;changed();
      try {
        const result=await api("/api/applications/",{method:"POST",body:JSON.stringify({kind:"appeal",case_id:caseId})});
        if(!uuid.test(result?.id)||result.case_id!==caseId||result.kind!=="appeal")throw new Error("Invalid appeal acknowledgement");
        return result.id;
      } catch(error){
        state.error=error?.status===401?"expired":[403,404].includes(error?.status)?"denied":"failed";
        state.locked=[401,403,404].includes(error?.status);
        return null;
      } finally {state.busy=false;changed();}
    }};
  }
  function createPetitionStarter(record,api,changed=()=>{}) {
    const caseId=record?.id;
    const state={busy:false,locked:false,error:null};
    return {state,async start(){
      if(record?.can_start_petition!==true||state.busy||state.locked||!uuid.test(caseId))return null;
      state.busy=true;state.error=null;changed();
      try {
        const result=await api("/api/applications/",{method:"POST",body:JSON.stringify({kind:"petition",case_id:caseId})});
        if(!uuid.test(result?.id)||result.case_id!==caseId||result.kind!=="petition")throw new Error("Invalid petition acknowledgement");
        return result.id;
      } catch(error){
        state.error=error?.status===401?"expired":[403,404].includes(error?.status)?"denied":"failed";
        state.locked=[401,403,404].includes(error?.status);
        return null;
      } finally {state.busy=false;changed();}
    }};
  }
  const words={
    en:{title:"Appeal or new information",start:"Start or resume appeal",busy:"Opening appeal…",
      help:"Provide new information or evidence for council consideration. Starting or submitting an appeal does not reopen the case; council must accept it first.",
      fee:"The USD 250 filing fee is nonrefundable. The tribunal must verify payment or authorize a waiver before submission.",
      expired:"Your session has expired. Sign in again to continue.",denied:"This case is no longer available for starting an appeal.",
      failed:"Unable to open an appeal. This action has not changed the case status. Refresh the case or contact the tribunal."},
    ar:{title:"استئناف أو معلومات جديدة",start:"بدء الاستئناف أو متابعته",busy:"جارٍ فتح الاستئناف…",
      help:"قدّم معلومات أو أدلة جديدة لينظر فيها المجلس. بدء الاستئناف أو تقديمه لا يعيد فتح القضية؛ يجب أن يقبله المجلس أولاً.",
      fee:"رسوم التقديم البالغة ٢٥٠ دولاراً أمريكياً غير قابلة للاسترداد. يجب أن يتحقق المجلس من الدفع أو يعتمد الإعفاء قبل التقديم.",
      expired:"انتهت جلستك. سجّل الدخول مجدداً للمتابعة.",denied:"لم تعد هذه القضية متاحة لبدء استئناف.",
      failed:"تعذر فتح استئناف. لم يغيّر هذا الإجراء حالة القضية. حدّث القضية أو تواصل مع المجلس."}
  };
  function StartAppeal({caseId,api,lang="en",onOpen}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [,render]=R.useReducer(n=>n+1,0);
    const starter=R.useMemo(()=>createAppealStarter(caseId,api,render),[caseId,api]);
    const generation=R.useRef(0);
    R.useEffect(()=>{generation.current++;return()=>{generation.current++;};},[starter]);
    const {state}=starter;
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      h(P.Text,null,t("help")),h(P.Notice,null,t("fee")),
      state.error?h(P.Notice,{tone:"danger",role:"alert"},t(state.error)):null,
      h(P.Button,{disabled:state.busy||state.locked,onClick:async()=>{
        const ticket=generation.current,id=await starter.start();
        if(id&&generation.current===ticket)onOpen(id);
      }},t(state.busy?"busy":"start"))));
  }
  const petitionWords={
    en:{title:"Your first petition for this case",start:"Start or resume my petition",busy:"Opening petition…",
      help:"Complete your own application and declaration. Your spouse’s answers remain private. For a closed case, provide new information for council consideration; submission does not reopen the case.",
      fee:words.en.fee,expired:words.en.expired,denied:"This case is no longer available for starting your petition.",failed:"Unable to open your petition. Refresh the case or contact the tribunal."},
    ar:{title:"طلبك الأول لهذه القضية",start:"بدء طلبي أو متابعته",busy:"جارٍ فتح الطلب…",
      help:"أكمل طلبك وإقرارك الخاصين. تبقى إجابات الطرف الآخر خاصة به. للقضية المغلقة، قدّم معلومات جديدة لينظر فيها المجلس؛ تقديم الطلب لا يعيد فتح القضية.",
      fee:words.ar.fee,expired:words.ar.expired,denied:"لم تعد هذه القضية متاحة لبدء طلبك.",failed:"تعذر فتح طلبك. حدّث القضية أو تواصل مع المجلس."}
  };
  function StartPetition({record,api,lang="en",onOpen}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>petitionWords[lang==="ar"?"ar":"en"][key];
    const [,render]=R.useReducer(n=>n+1,0);
    const starter=R.useMemo(()=>createPetitionStarter(record,api,render),[record?.id,record?.can_start_petition,api]);
    const generation=R.useRef(0);
    R.useEffect(()=>{generation.current++;return()=>{generation.current++;};},[starter]);
    const {state}=starter;
    if(record?.can_start_petition!==true)return null;
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      h(P.Text,null,t("help")),h(P.Notice,null,t("fee")),
      state.error?h(P.Notice,{tone:"danger",role:"alert"},t(state.error)):null,
      h(P.Button,{disabled:state.busy||state.locked,onClick:async()=>{
        const ticket=generation.current,id=await starter.start();
        if(id&&generation.current===ticket)onOpen(id);
      }},t(state.busy?"busy":"start"))));
  }
  window.CTMApplicantAppeals={hasAppealContext,createAppealStarter,StartAppeal,createPetitionStarter,StartPetition};
})();
