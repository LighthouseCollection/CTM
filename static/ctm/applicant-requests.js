/* Own sent requests and bound workspaces. Server capabilities govern every mutation. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const text=value=>typeof value==="string"&&!!value.trim();
  const timestamp=value=>typeof value==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&Number.isFinite(Date.parse(value));
  function validProjection(data) {
    return Array.isArray(data?.items)&&data.items.every(row=>uuid(row?.id)&&text(row.title)&&
      ["intake","medical","psychological"].includes(row.kind)&&["sent","completed","cancelled","closed"].includes(row.state)&&
      ["en","ar","both"].includes(row.language)&&typeof row.instructions==="string"&&timestamp(row.sent_at)&&
      Array.isArray(row.questions)&&row.questions.every(q=>text(q?.code)&&Number.isSafeInteger(q.version)&&q.version>0&&
        (row.language==="ar"||text(q.en))&&(row.language==="en"||text(q.ar)))&&
      new Set(row.questions.map(q=>q.code)).size===row.questions.length)&&
      new Set(data.items.map(row=>row.id)).size===data.items.length;
  }
  function questionText(question,row,lang) {
    return question[row.language==="both"?(lang==="ar"?"ar":"en"):row.language];
  }
  const words={
    en:{title:"My tribunal requests",refresh:"Refresh my requests",loading:"Loading your requests…",
      unavailable:"Your requests are unavailable. Refresh or contact the tribunal.",empty:"No requests are currently listed for you.",
      intake:"Written response request",medical:"Medical assessment request",psychological:"Psychological assessment request",
      sent:"Awaiting response",completed:"Completed",cancelled:"Cancelled",closed:"Closed",instructions:"Instructions",questions:"Requested questions",sentAt:"Sent",
      open:"Open request",respond:"Respond to request",response:"Online response submission is not available here yet. Contact the tribunal about responding to this request.",
      release:"An assessment report and its signed, scoped release are separate requirements. Uploading a report does not grant disclosure consent. Contact the tribunal for the approved release and submission process."},
    ar:{title:"طلباتي من المجلس",refresh:"تحديث طلباتي",loading:"جارٍ تحميل طلباتك…",
      unavailable:"طلباتك غير متاحة حاليًا. حدّث الصفحة أو تواصل مع المجلس.",empty:"لا توجد طلبات مدرجة لك حاليًا.",
      intake:"طلب إجابة مكتوبة",medical:"طلب تقييم طبي",psychological:"طلب تقييم نفسي",
      sent:"بانتظار الإجابة",completed:"مكتمل",cancelled:"ملغى",closed:"مغلق",instructions:"التعليمات",questions:"الأسئلة المطلوبة",sentAt:"تاريخ الإرسال",
      open:"فتح الطلب",respond:"الإجابة عن الطلب",response:"تقديم الإجابات عبر هذه الصفحة غير متاح بعد. تواصل مع المجلس لمعرفة كيفية الإجابة عن هذا الطلب.",
      release:"تقرير التقييم والتفويض الموقّع المحدد النطاق متطلبان منفصلان. رفع التقرير لا يعني الموافقة على الإفصاح. تواصل مع المجلس للحصول على التفويض المعتمد وطريقة التقديم."}
  };
  function Requests({caseId,api,lang="en",onNavigationGuard}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [data,setData]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false),[revision,reload]=R.useState(0);
    const [selected,select]=R.useState(null);
    R.useEffect(()=>{
      let active=true;setData(null);setLoading(true);setError(false);
      api(`/api/cases/${encodeURIComponent(caseId)}/requests/`).then(result=>{
        if(!validProjection(result))throw new Error("Invalid own request projection");
        if(active)setData(result);
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[caseId,api,revision]);
    if(selected&&window.CTMApplicantAssessments?.validOwnRequest(selected))return h(window.CTMApplicantAssessments.Workspace,{
      key:selected.id,request:selected,caseId,api,lang,onNavigationGuard,onBack:()=>{select(null);reload(n=>n+1);}});
    if(selected&&window.CTMApplicantResponses)return h(window.CTMApplicantResponses.ResponseEditor,{
      key:selected.id,request:selected,api,lang,onNavigationGuard,onBack:()=>{select(null);reload(n=>n+1);}});
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      h(P.Button,{disabled:loading,onClick:()=>reload(n=>n+1)},t("refresh")),
      loading?h(P.Text,{role:"status"},t("loading")):null,
      error?h(P.Notice,{tone:"danger",role:"alert"},t("unavailable")):null,
      data&&!data.items.length?h(P.Text,null,t("empty")):null,
      ...(data?.items||[]).map(row=>h(P.Panel,{key:row.id,title:row.title},h(P.Stack,null,
        h(P.Text,null,t(row.kind)," · ",t(row.state)),
        h(P.Text,null,t("sentAt"),": ",h("bdi",{dir:"ltr"},row.sent_at)),
        row.instructions?h(P.Panel,{title:t("instructions")},h(P.Text,{dir:"auto"},row.instructions)):null,
        row.questions.length?h(P.Panel,{title:t("questions")},h(P.List,{variant:"bullets",items:row.questions.map(q=>({
          children:h("span",{lang:row.language==="both"?lang:row.language,dir:row.language==="ar"||row.language==="both"&&lang==="ar"?"rtl":"ltr"},questionText(q,row,lang))
        }))})):null,
        window.CTMApplicantAssessments?.validOwnRequest(row)?h(P.Button,{onClick:()=>select(row)},t("open")):
        window.CTMApplicantResponses?.canRespond(row)
          ?h(P.Button,{onClick:()=>select(row)},t("respond"))
          :row.state==="sent"?h(P.Notice,null,t(row.kind==="intake"?"response":"release")):null
      )))
    ));
  }
  window.CTMApplicantRequests={validProjection,questionText,Requests};
})();
