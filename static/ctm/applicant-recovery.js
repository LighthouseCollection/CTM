/* Existing payment candidates block new attempts. Resume needs an authoritative original snapshot. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const states=["pending","processing","paid","needs_review","finalized","expired","failed"];
  const timestamp=value=>typeof value==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&Number.isFinite(Date.parse(value));
  function validHistory(data){return Array.isArray(data?.checkouts)&&data.checkouts.every(row=>uuid(row?.id)&&
    typeof row.state==="string"&&Number.isSafeInteger(row.version)&&row.version>=0&&timestamp(row.timestamp))&&
    new Set(data.checkouts.map(row=>row.id)).size===data.checkouts.length;}
  function blocksNewCheckout(data){return !validHistory(data)||data.checkouts.some(row=>
    !states.includes(row.state)||["pending","processing","paid","needs_review"].includes(row.state));}
  function resumeURL(app,history){
    const p=app?.pending_checkout;
    if(app?.can_resume_checkout!==true||app.status!=="draft"||!uuid(app.id)||!uuid(p?.id)||
      !Number.isSafeInteger(app.version)||app.version<0||p.version!==app.version||!validHistory(history)||history.checkouts.some(row=>!states.includes(row.state))||
      history.checkouts.filter(row=>["pending","processing","paid","needs_review"].includes(row.state)).length!==1||
      !history.checkouts.some(row=>row.id===p.id&&row.state==="pending"&&row.version===p.version)||
      p.attestation?.accepted!==true||typeof p.attestation.name!=="string"||!p.attestation.name.trim()||
      ![p.declaration_en,p.declaration_ar].every(s=>typeof s==="string"&&!!s.trim()))return null;
    try{const url=new URL(p.checkout_url);return url.protocol==="https:"&&url.hostname==="checkout.stripe.com"&&
      !url.username&&!url.password&&!url.port?url.href:null;}catch{return null;}
  }
  const words={en:{title:"Existing checkout recovery",refresh:"Refresh existing checkout",loading:"Checking existing payment attempts…",
    unavailable:"Existing payment attempts cannot be checked. A new checkout is blocked until you refresh successfully.",
    hold:"An existing payment attempt must be resolved before starting another. Do not sign or pay again. Refresh or contact the tribunal.",
    clear:"No unresolved checkout is recorded.",original:"Original checkout declaration",signer:"Original signer",resume:"Resume existing secure checkout"},
    ar:{title:"استعادة محاولة الدفع القائمة",refresh:"تحديث محاولة الدفع القائمة",loading:"جارٍ التحقق من محاولات الدفع القائمة…",
      unavailable:"تعذر التحقق من محاولات الدفع القائمة. لن تتاح محاولة جديدة حتى يتم التحديث بنجاح.",
      hold:"يجب حسم محاولة الدفع القائمة قبل بدء محاولة أخرى. لا توقّع أو تدفع مجددًا. حدّث الصفحة أو تواصل مع المجلس.",
      clear:"لا توجد محاولة دفع غير محسومة مسجّلة.",original:"الإقرار الأصلي لمحاولة الدفع",signer:"صاحب التوقيع الأصلي",resume:"استئناف محاولة الدفع الآمنة القائمة"}};
  function Recovery({application,api,lang="en",disabled=false,onBlockChange,onCheckout=url=>window.location.assign(url)}){
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [data,setData]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false),[revision,reload]=R.useState(0);
    const blocked=!data||blocksNewCheckout(data.history);
    R.useEffect(()=>{onBlockChange?.(blocked);},[blocked,onBlockChange]);
    R.useEffect(()=>{
      let active=true;setData(null);setLoading(true);setError(false);onBlockChange?.(true);
      Promise.all([api(`/api/applications/${encodeURIComponent(application.id)}/payments/`),
        api(`/api/applications/${encodeURIComponent(application.id)}/`)]).then(([history,app])=>{
        if(!validHistory(history)||app?.id!==application.id||app.version!==application.version)throw Error("Invalid recovery projection");
        if(active)setData({history,app});
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[application.id,application.version,api,revision,onBlockChange]);
    const url=data?resumeURL(data.app,data.history):null,p=data?.app.pending_checkout;
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      h(P.Button,{disabled:loading,onClick:()=>reload(n=>n+1)},t("refresh")),
      loading?h(P.Text,{role:"status"},t("loading")):null,
      error?h(P.Notice,{tone:"warning",role:"alert"},t("unavailable")):null,
      data?h(P.Notice,null,t(blocked?"hold":"clear")):null,
      url?h(P.Stack,null,h(P.Panel,{title:t("original")},h(P.Text,null,p[lang==="ar"?"declaration_ar":"declaration_en"])),
        h(P.Text,null,t("signer"),": ",p.attestation.name),
        h(P.Button,{disabled:disabled,onClick:()=>onCheckout(url)},t("resume"))):null
    ));
  }
  window.CTMApplicantRecovery={validHistory,blocksNewCheckout,resumeURL,Recovery};
})();
