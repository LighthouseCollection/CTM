/* Owner actions bound to current server capabilities and answer version. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  function available(app,action) {
    if(!uuid(app?.id)||!Number.isSafeInteger(app.version)||app.version<0)return false;
    if(action==="delete")return app.can_delete_draft===true&&app.status==="draft";
    return action==="withdraw"&&app.can_withdraw===true&&["petition","appeal"].includes(app.kind)&&
      ["submitted","returned","accepted"].includes(app.status);
  }
  const actionScope=app=>JSON.stringify([app?.id,app?.version,app?.status,
    app?.can_delete_draft===true,app?.can_withdraw===true]);
  function createActionSession(app,api,changed=()=>{}) {
    const state={busy:false,locked:false,error:null,received:false};
    return {state,async send(action,confirmed){
      if(confirmed!==true||!available(app,action)||state.busy||state.locked)return false;
      state.busy=true;state.locked=true;state.error=null;changed();
      try{
        const result=await api(`/api/applications/${app.id}/${action==="delete"?"delete-draft":"withdraw"}/`,{
          method:"POST",body:JSON.stringify({expected_version:app.version})});
        if(result?.id!==app.id)throw Error("Invalid action acknowledgement");
        state.received=true;return true;
      }catch(error){state.error=[401,403,404].includes(error?.status)?"denied":"uncertain";return false;}
      finally{state.busy=false;changed();}
    }};
  }
  const words={
    en:{title:"Application actions",delete:"Delete unsubmitted draft",withdraw:"Withdraw my filing",cancel:"Cancel",confirm:"Confirm action",
      deleteHelp:"This removes your unsubmitted draft. Submitted or returned filings cannot be deleted this way.",
      withdrawHelp:"This withdraws only your filing. The fee is retained. The tribunal determines any effect on participating spouses and case closure.",
      busy:"Processing…",received:"The server acknowledged your action. Refresh the application to check its current status.",
      denied:"This action is no longer available. Refresh the application.",uncertain:"The result is uncertain. Refresh the application before taking another action.",refresh:"Refresh application"},
    ar:{title:"إجراءات الطلب",delete:"حذف المسودة غير المقدّمة",withdraw:"سحب طلبي",cancel:"إلغاء",confirm:"تأكيد الإجراء",
      deleteHelp:"يحذف هذا الإجراء مسودتك غير المقدّمة. لا يمكن حذف الطلبات المقدّمة أو المعادة بهذه الطريقة.",
      withdrawHelp:"يسحب هذا الإجراء طلبك فقط. لا تُسترد الرسوم. يحدد المجلس الأثر على الزوجين المشاركين وإغلاق القضية.",
      busy:"جارٍ المعالجة…",received:"أقرّ الخادم باستلام الإجراء. حدّث الطلب للتحقق من حالته الحالية.",
      denied:"لم يعد هذا الإجراء متاحًا. حدّث الطلب.",uncertain:"نتيجة الإجراء غير مؤكدة. حدّث الطلب قبل اتخاذ إجراء آخر.",refresh:"تحديث الطلب"}
  };
  function Actions({application,api,lang="en",disabled=false,onBusyChange,onLockChange,onRefresh}){
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [,render]=R.useReducer(n=>n+1,0),[selected,select]=R.useState(null);
    const session=R.useMemo(()=>createActionSession(application,api,render),[application.id,application.version,
      application.status,application.can_delete_draft,application.can_withdraw,api]),state=session.state;
    const scope=actionScope(application);
    R.useEffect(()=>{select(null);},[scope,lang]);
    R.useEffect(()=>{onBusyChange?.(state.busy);return()=>onBusyChange?.(false);},[state.busy,onBusyChange]);
    R.useEffect(()=>{onLockChange?.(state.locked);return()=>onLockChange?.(false);},[state.locked,onLockChange]);
    if(!available(application,"delete")&&!available(application,"withdraw"))return null;
    return h(P.Panel,{ icon: "doc-text",title:t("title")},h(P.Stack,null,
      state.error?h(P.Notice,{tone:"warning",role:"alert"},t(state.error)):null,
      state.received?h(P.Notice,{role:"status"},t("received")):null,
      selected?h(P.Notice,{tone:"warning",role:"alert"},h(P.Stack,null,t(selected==="delete"?"deleteHelp":"withdrawHelp"),
        h(P.Inline,{wrap:true},h(P.Button,{variant:selected==="delete"?"danger-secondary":undefined,disabled:disabled||state.locked,onClick:()=>session.send(selected,true)},t(state.busy?"busy":"confirm")),
          h(P.Button,{variant:"secondary",disabled:state.busy,onClick:()=>select(null)},t("cancel"))))):null,
      !selected?h(P.Inline,{wrap:true},...["delete","withdraw"].filter(action=>available(application,action)).map(action=>
        h(P.Button,{key:action,variant:action==="delete"?"danger-secondary":undefined,disabled:disabled||state.locked,onClick:()=>select(action)},t(action)))):null,
      state.locked&&!state.busy?h(P.Button,{onClick:onRefresh,disabled:disabled},t("refresh")):null
    ));
  }
  window.CTMApplicantLifecycle={available,actionScope,createActionSession,Actions};
})();
