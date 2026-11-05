/* Own active releases from the case read. Server authorization is required on every file request. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const text=value=>typeof value==="string"&&!!value.trim();
  const timestamp=value=>typeof value==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&Number.isFinite(Date.parse(value));
  function downloadURL(file) {
    return uuid(file?.id)&&text(file.name)&&file.scan_state==="clean"&&file.download_url===`/api/files/${file.id}/`?file.download_url:null;
  }
  function validProjection(data,caseId) {
    return uuid(caseId)&&data?.id===caseId&&Array.isArray(data.released_decrees)&&
      data.released_decrees.every(row=>uuid(row?.id)&&text(row.reference)&&["en","ar","bilingual"].includes(row.language)&&
        timestamp(row.released_at)&&!!downloadURL(row.signed_file))&&
      new Set(data.released_decrees.map(row=>row.id)).size===data.released_decrees.length;
  }
  const words={
    en:{title:"Released decree certificates",refresh:"Refresh released certificates",loading:"Loading released certificates…",
      unavailable:"Released certificates are unavailable. Refresh or contact the tribunal.",empty:"No certificate is currently released to your account.",
      help:"Only certificates explicitly released to your account appear here. Access may be withdrawn by the tribunal.",
      released:"Released",en:"English",ar:"Arabic",bilingual:"English and Arabic",open:"View or download signed PDF",reference:"Certificate",language:"Language"},
    ar:{title:"شهادات القرار المتاحة",refresh:"تحديث الشهادات المتاحة",loading:"جارٍ تحميل الشهادات المتاحة…",
      unavailable:"الشهادات المتاحة غير متوفرة حاليًا. حدّث الصفحة أو تواصل مع المجلس.",empty:"لا توجد شهادة متاحة لحسابك حاليًا.",
      help:"تظهر هنا فقط الشهادات التي أتاحها المجلس لحسابك صراحةً. يمكن للمجلس سحب صلاحية الوصول.",
      released:"تاريخ الإتاحة",en:"الإنجليزية",ar:"العربية",bilingual:"الإنجليزية والعربية",open:"عرض أو تنزيل ملف PDF الموقّع",reference:"الشهادة",language:"اللغة"}
  };
  function ReleasedDecrees({caseId,api,lang="en"}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [data,setData]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false),[revision,reload]=R.useState(0);
    R.useEffect(()=>{
      let active=true;setData(null);setError(false);setLoading(true);
      api(`/api/cases/${encodeURIComponent(caseId)}/`).then(result=>{
        if(!validProjection(result,caseId))throw new Error("Invalid released decree projection");
        if(active)setData(result);
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[caseId,api,revision]);
    return h(P.Panel,{ icon: "doc-text",title:t("title")},h(P.Stack,null,
      h(P.Text,null,t("help")),h(P.Inline,{wrap:true},h(P.Button,{disabled:loading,onClick:()=>reload(n=>n+1)},t("refresh"))),
      loading?h(P.Text,{role:"status"},t("loading")):null,
      error?h(P.Notice,{tone:"danger",role:"alert"},t("unavailable")):null,
      data&&!data.released_decrees.length?h(P.Text,null,t("empty")):null,
      // Released certificates are a Plenix FileList (file-list.md): the reference names the file and links to the
      // signed original only when the server marks it clean; no size is invented.
      data&&data.released_decrees.length?h(P.FileList,{label:t("title"),view:"table",columns:["modified","status"],
        files:data.released_decrees.map(row=>({id:row.id,name:row.reference,kind:"file",type:"application/pdf",
          modified:new Date(row.released_at),status:{tone:"neutral",label:t(row.language)},href:downloadURL(row.signed_file)})),
        // Opens the signed original in a new tab, as before (the reading stays on the case page).
        onOpen:file=>{if(file.href)window.open(file.href,"_blank","noopener,noreferrer");},
        strings:{name:t("reference"),modified:t("released"),status:t("language"),open:t("open"),empty:t("empty")}}):null
    ));
  }
  window.CTMApplicantDecrees={validProjection,downloadURL,ReleasedDecrees};
})();
