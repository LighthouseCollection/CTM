/* Own request files and explicit bound professional disclosure. No inferred consent. */
(() => {
  "use strict";
  const uuid=value=>typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const fingerprint=value=>typeof value==="string"&&/^[0-9a-f]{64}$/.test(value);
  const text=value=>typeof value==="string"&&!!value.trim();
  const timestamp=value=>typeof value==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&Number.isFinite(Date.parse(value));
  const assessment=row=>["medical","psychological"].includes(row?.kind);
  const identity=row=>uuid(row?.id)&&uuid(row.proceeding_id)&&fingerprint(row.request_version);
  const same=(a,b)=>identity(a)&&identity(b)&&a.id===b.id&&a.proceeding_id===b.proceeding_id&&a.request_version===b.request_version;
  const validDefinition=d=>uuid(d?.id)&&Number.isSafeInteger(d.version)&&d.version>0&&
    text(d.declaration_en)&&text(d.declaration_ar)&&d.definition&&typeof d.definition==="object"&&!Array.isArray(d.definition);
  const validReceipt=r=>r===null||uuid(r?.id)&&timestamp(r.submitted_at)&&Number.isSafeInteger(r.version)&&r.version>0;
  function validOwnRequest(row){return identity(row)&&["can_respond","can_upload","can_sign_release"].every(key=>typeof row[key]==="boolean")&&
    ["none","signed","out_of_scope"].includes(row.release_status)&&validReceipt(row.response)&&
    (row.release_definition===null||validDefinition(row.release_definition))&&Array.isArray(row.signed_releases)&&
    row.signed_releases.every(s=>uuid(s?.id)&&uuid(s.declaration_id)&&uuid(s.signature_file_id)&&timestamp(s.signed_at)&&
      s.scope&&typeof s.scope==="object"&&!Array.isArray(s.scope))&&
    new Set(row.signed_releases.map(s=>s.id)).size===row.signed_releases.length;}
  function hasSignedScope(row){return identity(row)&&assessment(row)&&row.release_status==="signed"&&
    Array.isArray(row.signed_releases)&&row.signed_releases.some(s=>uuid(s?.id)&&uuid(s.declaration_id)&&uuid(s.signature_file_id)&&
      timestamp(s.signed_at)&&s.scope?.council===true&&s.scope.purpose===row.kind&&
      s.scope.request_id===row.id&&s.scope.proceeding_id===row.proceeding_id);}
  function safeURL(file){return uuid(file?.id)&&file.scan_state==="clean"&&file.download_url===`/api/files/${file.id}/`?file.download_url:null;}
  function validFiles(data,row){return identity(row)&&data?.request_id===row.id&&data.proceeding_id===row.proceeding_id&&
    data.request_version===row.request_version&&typeof data.can_upload==="boolean"&&Array.isArray(data.items)&&data.items.every(f=>
      uuid(f?.id)&&uuid(f.attachment_id)&&text(f.name)&&text(f.category)&&Number.isSafeInteger(f.version)&&f.version>0&&
      ["pending","clean","rejected"].includes(f.scan_state)&&f.purpose===(f.category==="CONSENT"?"consent":"report")&&
      (f.download_url===undefined||!!safeURL(f)))&&new Set(data.items.map(f=>f.id)).size===data.items.length&&
      new Set(data.items.map(f=>f.attachment_id)).size===data.items.length;}
  const signatureFile=f=>f?.purpose==="consent"&&!!safeURL(f)&&/\.(pdf|png|jpe?g)$/i.test(f.name);
  const canSign=row=>identity(row)&&assessment(row)&&row.state==="sent"&&row.can_sign_release===true&&
    validDefinition(row.release_definition)&&row.release_status==="none"&&Array.isArray(row.signed_releases)&&!row.signed_releases.length;
  function createConsentSession(row,api,changed=()=>{}){
    const state={busy:false,attempted:false,received:false,recovered:false,error:null,definition:null,fileId:null};
    return {state,reconcile(latest){
      if(!state.attempted||!same(row,latest)||!hasSignedScope(latest)||!latest.signed_releases.some(s=>
        s.declaration_id===state.definition?.id&&s.signature_file_id===state.fileId&&s.scope?.council===true&&
        s.scope.purpose===row.kind&&s.scope.request_id===row.id&&s.scope.proceeding_id===row.proceeding_id))return false;
      state.recovered=true;state.error=null;return true;
    },async sign(file,accepted,latest=row){
      if(state.attempted||state.busy||!same(row,latest)||!canSign(latest)||accepted!==true||!signatureFile(file))return false;
      state.definition=structuredClone(latest.release_definition);
      state.fileId=file.id;
      const payload={expected_version:latest.request_version,declaration_id:state.definition.id,accepted:true,file_id:file.id,scope:{council:true}};
      state.busy=true;state.attempted=true;state.error=null;changed();
      try{const result=await api(`/api/requests/${row.id}/release/`,{method:"POST",body:JSON.stringify(payload)});
        if(!uuid(result?.id))throw Error("Invalid release acknowledgement");state.received=true;return true;
      }catch(error){state.error=[401,403,404].includes(error?.status)?"denied":"uncertain";return false;}
      finally{state.busy=false;changed();}
    }};
  }
  async function uploadRequestFile(row,file,purpose,api){
    if(!identity(row)||row.state!=="sent"||row.can_upload!==true||!["consent","report"].includes(purpose)||
      purpose==="consent"&&(!assessment(row)||row.signed_releases?.length)||
      !file||!text(file.name)||!Number.isSafeInteger(file.size)||file.size<=0||file.size>25*1024*1024||
      !(purpose==="consent"?/\.(pdf|png|jpe?g)$/i:/\.(pdf|docx?|png|jpe?g)$/i).test(file.name))throw Error("Invalid request upload");
    const form=new FormData();form.append("request_id",row.id);form.append("expected_request_version",row.request_version);
    form.append("category",purpose==="consent"?"CONSENT":assessment(row)?"MED":"REPORT");form.append("file",file,file.name);
    const result=await api("/api/files/",{method:"POST",body:form});if(!uuid(result?.id))throw Error("Invalid upload acknowledgement");return result;
  }
  const words={en:{open:"Open request",back:"Back to requests",refresh:"Refresh request and files",loading:"Loading private request…",
    unavailable:"This request or its files cannot be verified. Refresh or contact the tribunal. Your local response is preserved.",
    changed:"This request has changed. Keep a copy of your local response, then return to the request list and reopen it.",
    files:"My request originals",consentFile:"Signed release original",reportFile:"Report or response evidence",upload:"Upload original",
    uploadNotice:"Up to 25 MB. Only technically clean originals can be used. Uploading does not sign a release or submit a response.",
    uploadReceived:"The server acknowledged the upload. Review the refreshed file status.",download:"View or download original",
    consent:"Professional disclosure release",accept:"I have read and accept this exact disclosure declaration for the council and this request.",
    choose:"Choose the signed release original",review:"Review disclosure consent",edit:"Edit consent selection",sign:"Confirm disclosure consent",
    declaration:"Bound release declaration",version:"Declaration version",scope:"Recipient: council. Purpose and request are bound by the tribunal.",
    none:"No signed release is recorded.",signed:"A signed release for this request and purpose is recorded.",
    outOfScope:"The retained release does not verify this request and purpose. Contact the tribunal; no broader consent is inferred.",
    receipt:"Own response receipt",received:"Server acknowledgement received. Refresh to verify the retained record.",
    recovered:"Your retained release matches this original and declaration.",retainedSignature:"Retained signature original",missingOriginal:"Original unavailable",
    uncertain:"The result is uncertain. Do not repeat the action. Refresh to check the retained record.",denied:"This action is no longer available. Refresh the request.",
    empty:"No originals are listed.",pending:"Safety check pending",clean:"Safety check passed",rejected:"Safety check rejected",signedAt:"Signed"},
    ar:{open:"فتح الطلب",back:"العودة إلى الطلبات",refresh:"تحديث الطلب والملفات",loading:"جارٍ تحميل الطلب الخاص…",
      unavailable:"تعذر التحقق من الطلب أو ملفاته. حدّث الصفحة أو تواصل مع المجلس. حُفظت إجابتك المحلية.",
      changed:"تغيّر هذا الطلب. احتفظ بنسخة من إجابتك المحلية، ثم عد إلى قائمة الطلبات وافتحه من جديد.",
      files:"أصول ملفاتي لهذا الطلب",consentFile:"أصل التفويض الموقّع",reportFile:"التقرير أو أدلة الإجابة",upload:"رفع الأصل",
      uploadNotice:"الحد الأقصى 25 ميغابايت. لا يمكن استخدام إلا الأصول التي اجتازت الفحص. رفع الملف لا يوقّع التفويض ولا يقدّم الإجابة.",
      uploadReceived:"أقرّ الخادم باستلام الملف. راجع حالة الملف بعد التحديث.",download:"عرض الأصل أو تنزيله",
      consent:"تفويض الإفصاح المهني",accept:"قرأت هذا الإقرار المحدد للإفصاح وأوافق عليه للمجلس ولهذا الطلب.",
      choose:"اختر أصل التفويض الموقّع",review:"مراجعة الموافقة على الإفصاح",edit:"تعديل اختيار التفويض",sign:"تأكيد الموافقة على الإفصاح",
      declaration:"إقرار التفويض المرتبط",version:"نسخة الإقرار",scope:"الجهة المستلمة: المجلس. يربط المجلس الغرض والطلب بالتفويض.",
      none:"لا يوجد تفويض موقّع مسجّل.",signed:"يوجد تفويض موقّع مسجّل لهذا الطلب والغرض.",
      outOfScope:"التفويض المحفوظ لا يثبت النطاق لهذا الطلب والغرض. تواصل مع المجلس؛ لا تُفترض موافقة أوسع.",
      receipt:"إيصال إجابتي",received:"أقرّ الخادم بالاستلام. حدّث الصفحة للتحقق من السجل المحفوظ.",
      recovered:"التفويض المحفوظ يطابق هذا الأصل وهذا الإقرار.",retainedSignature:"أصل التوقيع المحفوظ",missingOriginal:"الأصل غير متاح",
      uncertain:"نتيجة الإجراء غير مؤكدة. لا تكرره. حدّث الصفحة للتحقق من السجل المحفوظ.",denied:"لم يعد هذا الإجراء متاحًا. حدّث الطلب.",
      empty:"لا توجد أصول مدرجة.",pending:"الفحص قيد الانتظار",clean:"اجتاز فحص السلامة",rejected:"رُفض في فحص السلامة",signedAt:"تاريخ التوقيع"}}
  ;
  function Workspace({request,caseId,api,lang="en",onBack,onNavigationGuard}){
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [data,setData]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(null),[revision,reload]=R.useState(0);
    const [uploadBusy,setUploadBusy]=R.useState(false),[uploadLocked,setUploadLocked]=R.useState(false),[uploadReceived,setUploadReceived]=R.useState(false);
    const [responseBusy,setResponseBusy]=R.useState(false),[responseLocked,setResponseLocked]=R.useState(false);
    const [consentChecked,setConsentChecked]=R.useState(true);
    const [selected,setSelected]=R.useState({}),[fileEpoch,setFileEpoch]=R.useState(0),[signature,setSignature]=R.useState(""),[accepted,setAccepted]=R.useState(false),[review,setReview]=R.useState(false);
    const [,render]=R.useReducer(n=>n+1,0),childGuard=R.useRef(null);
    const register=R.useCallback(guard=>{childGuard.current=guard;},[]);
    const consent=R.useMemo(()=>createConsentSession(request,api,render),[request.id,request.request_version,api]);
    const busy=uploadBusy||consent.state.busy||responseBusy;
    const navigate=action=>{if(busy)return;if(childGuard.current)childGuard.current(action);else action();};
    R.useEffect(()=>{onNavigationGuard?.(navigate);return()=>onNavigationGuard?.(null);},[onNavigationGuard,busy]);
    R.useEffect(()=>{if(!busy)return;const warn=e=>{e.preventDefault();e.returnValue="";};window.addEventListener("beforeunload",warn);
      return()=>window.removeEventListener("beforeunload",warn);},[busy]);
    R.useEffect(()=>{
      let active=true;setLoading(true);setData(null);setError(null);
      Promise.all([api(`/api/cases/${encodeURIComponent(caseId)}/requests/`),api(`/api/requests/${request.id}/files/`)]).then(([list,files])=>{
        const latest=list?.items?.find(row=>row.id===request.id);
        if(!window.CTMApplicantRequests?.validProjection(list)||!validOwnRequest(latest)||!same(request,latest)||!validFiles(files,latest))
          throw Error("Invalid own request projection");
        if(active){consent.reconcile(latest);setData({request:latest,files});setUploadLocked(false);setConsentChecked(true);}
      }).catch(()=>{if(active)setError("unavailable");}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[caseId,request.id,request.request_version,api,revision]);
    const latest=data?.request,files=data?.files.items||[],blocked=busy||loading||!data||responseLocked||!consentChecked;
    const signatures=files.filter(signatureFile),definition=consent.state.definition||latest?.release_definition;
    R.useEffect(()=>{if(!consent.state.attempted){setAccepted(false);setReview(false);setSignature("");}},
      [latest?.release_definition?.id,latest?.release_definition?.version,revision]);
    async function upload(purpose){
      if(blocked||uploadLocked||latest?.can_upload!==true||data.files.can_upload!==true)return;
      setUploadBusy(true);setError(null);setUploadReceived(false);
      try{await uploadRequestFile(latest,selected[purpose],purpose,api);setSelected({});setFileEpoch(n=>n+1);setUploadReceived(true);reload(n=>n+1);}
      catch{setError("uncertain");setUploadLocked(true);}finally{setUploadBusy(false);}
    }
    const filePanel=h(P.Panel,{ icon: "lock",title:t("files")},h(P.Stack,null,
      h(P.Text,null,t("uploadNotice")),!files.length?h(P.Text,null,t("empty")):null,
      ...files.map(file=>h(P.Panel,{ icon: "lock",key:file.id,title:file.name},h(P.Stack,null,
        h(P.Text,null,t(file.purpose==="consent"?"consentFile":"reportFile")," · ",t(file.scan_state)),
        safeURL(file)?h(P.Button,{href:safeURL(file),target:"_blank",rel:"noopener noreferrer"},t("download")):null))),
      ...[...(assessment(request)&&!latest?.signed_releases.length?["consent"]:[]),"report"].map(purpose=>
        latest?.can_upload&&data.files.can_upload?h(P.Fieldset,{key:purpose,legend:t(purpose==="consent"?"consentFile":"reportFile")},
          h(P.Input,{key:`${purpose}:${fileEpoch}`,type:"file",disabled:blocked||uploadLocked,accept:purpose==="consent"?".pdf,.png,.jpg,.jpeg":".pdf,.doc,.docx,.png,.jpg,.jpeg",
            onChange:e=>setSelected({...selected,[purpose]:e.target.files?.[0]})}),
          h(P.Button,{disabled:blocked||uploadLocked||!selected[purpose],onClick:()=>upload(purpose)},t("upload"))):null)
    ));
    const consentPanel=assessment(request)?h(P.Panel,{ icon: "lock",title:t("consent")},h(P.Stack,null,
      latest?h(P.Notice,null,t(hasSignedScope(latest)?"signed":latest.release_status==="none"?"none":"outOfScope")):null,
      ...(latest?.signed_releases||[]).map(s=>h(P.Stack,{key:s.id},
        h(P.Text,null,t("signedAt"),": ",h("bdi",{dir:"ltr"},s.signed_at)),
        h(P.Text,null,t("retainedSignature"),": ",files.find(f=>f.id===s.signature_file_id)?.name||t("missingOriginal")))),
      (canSign(latest)||consent.state.attempted)&&validDefinition(definition)?h(P.Stack,null,
        h(P.Text,null,t("version"),": ",definition.version),h(P.Panel,{ icon: "lock",title:t("declaration")},h(P.Text,{dir:lang==="ar"?"rtl":"ltr"},definition[lang==="ar"?"declaration_ar":"declaration_en"])),
        h(P.Text,null,t("scope")),h(P.Field,{label:t("choose")},h(P.Select,{value:signature,disabled:blocked||consent.state.attempted,
          options:[{value:"",label:"—"},...signatures.map(f=>({value:f.id,label:f.name}))],onChange:e=>{setSignature(e.target.value);setReview(false);}})),
        h(P.Checkbox,{label:t("accept"),checked:accepted,disabled:blocked||consent.state.attempted,onChange:e=>{setAccepted(e.target.checked);setReview(false);}}),
        h(P.Inline,{wrap:true},h(P.Button,{disabled:blocked||consent.state.attempted||!accepted||!signature,
          onClick:()=>setReview(!review)},t(review?"edit":"review")),
          review?h(P.Button,{disabled:blocked||consent.state.attempted||!canSign(latest)||!accepted||!signatures.some(f=>f.id===signature),
            onClick:async()=>{if(blocked)return;setConsentChecked(false);
              if(await consent.sign(signatures.find(f=>f.id===signature),accepted,latest))reload(n=>n+1);}},t("sign")):null)
      ):null,
      consent.state.error?h(P.Notice,{tone:"warning",role:"alert"},t(consent.state.error)):null,
      consent.state.recovered||consent.state.received?h(P.Notice,{role:"status"},t(consent.state.recovered?"recovered":"received")):null
    )):null;
    return h(P.Stack,null,h(P.Panel,{ icon: "lock",title:request.title},h(P.Text,{dir:"auto"},request.instructions)),
      h(P.Inline,{wrap:true},h(P.Button,{disabled:busy,onClick:()=>navigate(onBack)},t("back")),
      h(P.Button,{disabled:busy||loading,onClick:()=>reload(n=>n+1)},t("refresh"))),
      loading?h(P.Text,{role:"status"},t("loading")):null,error?h(P.Notice,{tone:"warning",role:"alert"},t(error)):null,
      uploadReceived?h(P.Notice,{role:"status"},t("uploadReceived")):null,
      latest?.response?h(P.Panel,{ icon: "lock",title:t("receipt")},h(P.Text,null,h("bdi",{dir:"ltr"},latest.response.id)," · ",h("bdi",{dir:"ltr"},latest.response.submitted_at))):null,
      data?filePanel:null,consentPanel,
      window.CTMApplicantResponses?h(window.CTMApplicantResponses.ResponseEditor,{request:latest||request,api,lang,evidence:files,evidenceVerified:!!data,
        disabled:blocked||uploadLocked,navigationBusy:busy,onNavigationGuard:register,onBusyChange:setResponseBusy,onLockChange:setResponseLocked,
        onBack,onRefresh:()=>reload(n=>n+1),showBack:false}):null
    );
  }
  window.CTMApplicantAssessments={identity,same,validOwnRequest,validDefinition,hasSignedScope,safeURL,validFiles,canSign,createConsentSession,uploadRequestFile,Workspace};
})();
