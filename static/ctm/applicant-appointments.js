/* Private applicant invitations; never use council agenda as fallback. */
(() => {
  "use strict";
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const date = value => typeof value === "string" &&
    /T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
  function validInvitation(row) {
    return !!row && uuid.test(row.id) && (uuid.test(row.case_id) ||
      (typeof row.case_number === "string" && !!row.case_number.trim())) &&
      date(row.starts_at) && date(row.ends_at) && Date.parse(row.ends_at) > Date.parse(row.starts_at) &&
      typeof row.instructions === "string" && Number.isSafeInteger(row.version) && row.version > 0 &&
      typeof row.state === "string" && !!row.state && typeof row.can_respond === "boolean" &&
      (!row.can_respond || row.state === "invited") &&
      [null,"confirm","reject"].includes(row.response);
  }
  function validListing(data) {
    return Array.isArray(data?.items) && data.items.every(validInvitation) &&
      new Set(data.items.map(row => row.id)).size === data.items.length;
  }
  function createResponseSession(invitation, api, changed = () => {}) {
    const row = {...invitation};
    const state = {busy:false,locked:false,acknowledged:false,error:null};
    return {state, async send(response, explanation = "") {
      if (!validInvitation(row) || !row.can_respond || state.busy || state.locked || state.acknowledged ||
          !["confirm","reject"].includes(response) || typeof explanation !== "string") return false;
      state.busy = true; state.error = null; changed();
      try {
        const result = await api(`/api/appointments/${row.id}/response/`, {method:"POST",
          body:JSON.stringify({version:row.version,response,explanation:response === "reject" ? explanation : ""})});
        if (!result?.id) throw new Error("Invalid response acknowledgement");
        state.acknowledged = true;
        return true;
      } catch (error) {
        state.locked = true;
        state.error = error?.status === 422 ? "stale" : [401,403,404].includes(error?.status) ? "denied" : "uncertain";
        return false;
      } finally { state.busy = false; changed(); }
    }};
  }
  const words = {
    en:{title:"My appointments",loading:"Loading your invitations…",empty:"You have no appointment invitations.",
      unavailable:"Your invitations are unavailable. Refresh or contact the tribunal.",refresh:"Refresh invitations",
      case:"Case reference",invitation:"Appointment invitation",start:"Starts",end:"Ends",instructions:"Instructions",version:"Invitation version",
      time:"Times below retain the invitation’s UTC offset.",confirm:"Confirm attendance",reject:"Reject invitation",
      explanation:"Reason for rejecting (optional)",busy:"Sending…",confirmResponse:"Your current response: Confirmed",
      rejectResponse:"Your current response: Rejected",noResponse:"You have not responded to this invitation version.",
      closed:"This invitation is not accepting responses.",ack:"Your response was received. Refresh invitations to see its current status.",
      stale:"This invitation has changed. Refresh and review the current invitation before responding.",
      denied:"Invitation access is unavailable. Refresh or sign in again.",
      uncertain:"Your response was not confirmed. Refresh invitations before responding again.",response:"Your response"},
    ar:{title:"مواعيدي",loading:"جارٍ تحميل دعواتك…",empty:"لا توجد لديك دعوات لمواعيد.",
      unavailable:"دعواتك غير متاحة. حدّث القائمة أو تواصل مع المجلس.",refresh:"تحديث الدعوات",
      case:"مرجع القضية",invitation:"دعوة لموعد",start:"البداية",end:"النهاية",instructions:"التعليمات",version:"نسخة الدعوة",
      time:"تحتفظ الأوقات أدناه بفارق التوقيت عن UTC الوارد في الدعوة.",confirm:"تأكيد الحضور",reject:"رفض الدعوة",
      explanation:"سبب الرفض (اختياري)",busy:"جارٍ الإرسال…",confirmResponse:"ردك الحالي: تأكيد الحضور",
      rejectResponse:"ردك الحالي: رفض الدعوة",noResponse:"لم ترد على هذه النسخة من الدعوة.",
      closed:"هذه الدعوة لا تقبل الردود حالياً.",ack:"تم استلام ردك. حدّث الدعوات للاطلاع على الحالة الحالية.",
      stale:"تغيّرت هذه الدعوة. حدّث الدعوات وراجع الدعوة الحالية قبل الرد.",
      denied:"الوصول إلى الدعوة غير متاح. حدّث الدعوات أو سجّل الدخول مجدداً.",
      uncertain:"لم يتم تأكيد ردك. حدّث الدعوات قبل الرد مجدداً.",response:"ردك"}
  };
  // The chosen invitation in the reading pane. Its response session and typed reason live in Appointments, so moving
  // between invitations never resets an acknowledged or locked response (a refresh starts new sessions, as before).
  function Invitation({row,session,explanation,setExplanation,lang}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang === "ar" ? "ar" : "en"][key];
    const s=session.state,disabled=!row.can_respond || s.busy || s.locked || s.acknowledged;
    return h(P.Stack,null,
      h(P.Text,null,`${t("version")}: ${row.version}`),h(P.Text,null,t("time")),
      h(P.Text,null,`${t("start")}: `,h("bdi",{dir:"ltr"},row.starts_at)),
      h(P.Text,null,`${t("end")}: `,h("bdi",{dir:"ltr"},row.ends_at)),
      h(P.Panel,{ icon: "doc-text",title:t("instructions")},h(P.Text,null,row.instructions)),
      h(P.Text,null,t(row.response === "confirm" ? "confirmResponse" : row.response === "reject" ? "rejectResponse" : "noResponse")),
      !row.can_respond ? h(P.Notice,null,t("closed")) : null,
      s.error ? h(P.Notice,{role:"alert",tone:"danger"},t(s.error)) : null,
      s.acknowledged ? h(P.Notice,{role:"status"},t("ack")) : null,
      row.can_respond ? h(P.Stack,null,
        h(P.Field,{label:t("explanation")},h(P.Textarea,{value:explanation,disabled,rows:3,
          onChange:e=>setExplanation(e.target.value)})),
        h(P.Inline,{wrap:true},
          h(P.Button,{disabled,variant:"primary",onClick:()=>session.send("confirm")},t(s.busy ? "busy" : "confirm")),
          h(P.Button,{disabled,variant:"secondary",onClick:()=>session.send("reject",explanation)},t(s.busy ? "busy" : "reject")))) : null);
  }
  function Appointments({api,lang="en"}) {
    const R=window.React,P=window.Plenix,Shell=window.CTMShell,h=R.createElement,t=key=>words[lang === "ar" ? "ar" : "en"][key];
    const [data,setData]=R.useState(null),[error,setError]=R.useState(false),[revision,reload]=R.useState(0);
    const [loading,setLoading]=R.useState(true),[selected,select]=R.useState(null),[reasons,setReasons]=R.useState({});
    const sessions=R.useRef(new Map()),[,rerender]=R.useReducer(n=>n+1,0);
    const sessionFor=row=>{const key=`${revision}:${row.id}`;if(!sessions.current.has(key))sessions.current.set(key,createResponseSession(row,api,rerender));return sessions.current.get(key);};
    const busy=(data?.items||[]).some(row=>sessionFor(row).state.busy);
    R.useEffect(()=>{
      let active=true;setLoading(true);setData(null);setError(false);sessions.current=new Map();setReasons({});
      api("/api/appointments/").then(result=>{
        if(!validListing(result))throw new Error("Invalid invitation projection");
        if(active)setData(result);
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[api,revision]);
    const rows=data?.items||[];
    const chosen=rows.find(row=>row.id===selected)||rows[0]||null;
    const caseLabel=row=>row.case_number||t("invitation");
    const answer=row=>t(row.response === "confirm" ? "confirmResponse" : row.response === "reject" ? "rejectResponse" : "noResponse");
    // My invitations as a CTMShell workspace (master-detail-workspace.md): the list, and the chosen invitation beside it.
    return h(P.Stack,{as:"section",gap:"md"},
      h(P.Text,{as:"h1",variant:"display"},t("title")),
      h(P.Inline,{wrap:true},h(P.Button,{disabled:busy || loading,onClick:()=>reload(n=>n+1)},t("refresh"))),
      error ? h(P.Notice,{role:"alert",tone:"danger"},t("unavailable")) : null,
      // Nothing listed: one EmptyState (empty-state.md) instead of an empty list beside an empty reading pane.
      !error && data && !rows.length ? h(P.EmptyState,{title:t("empty")}) : null,
      error || (data && !rows.length) ? null : h(Shell.Workspace,{label:t("title"),rows:rows.map(row=>({...row,title:caseLabel(row)})),loading,empty:t("empty"),
        selected:chosen?.id,onSelect:id=>{if(!busy)select(id);},
        columns:[{title:t("case"),field:"case_number",render:row=>caseLabel(row)},
          {title:t("start"),field:"starts_at",render:row=>row.starts_at},
          {title:t("response"),field:"response",render:row=>answer(row)}],
        actions:null},
        chosen?h(Invitation,{key:`${revision}:${chosen.id}`,row:chosen,lang,session:sessionFor(chosen),
          explanation:reasons[chosen.id]||"",setExplanation:value=>setReasons(old=>({...old,[chosen.id]:value}))}):null));
  }
  window.CTMApplicantAppointments={validListing,createResponseSession,Appointments};
})();
