/* Own append-only reconsideration supplements with bound versions and retained receipts. */
(() => {
  "use strict";
  const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const fileValid=row=>!!row&&uuid.test(row.id)&&typeof row.name==="string"&&typeof row.scan_state==="string";
  const downloadURL=row=>fileValid(row)&&row.scan_state==="clean"&&row.download_url===`/api/files/${row.id}/`?row.download_url:null;
  const keyValid=value=>typeof value==="string"&&!!value.trim()&&value.length<=100;
  const receiptValid=row=>!!row&&uuid.test(row.id)&&typeof row.text==="string"&&
    (row.idempotency_key===null||keyValid(row.idempotency_key))&&
    typeof row.timestamp==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(row.timestamp)&&Number.isFinite(Date.parse(row.timestamp))&&
    Array.isArray(row.manifest)&&new Set(row.manifest.map(file=>file?.id)).size===row.manifest.length&&
    row.manifest.every(file=>file&&uuid.test(file.id)&&typeof file.sha256==="string"&&/^[0-9a-f]{64}$/.test(file.sha256));
  function validProjection(app) {
    return !!app&&uuid.test(app.id)&&(app.kind==="appeal"||app.kind==="petition"&&app.origin==="closed_case_intake")&&
      Number.isSafeInteger(app.version)&&app.version>=0&&typeof app.status==="string"&&
      typeof app.can_supplement==="boolean"&&Array.isArray(app.supplements)&&
      new Set(app.supplements.map(row=>row?.id)).size===app.supplements.length&&app.supplements.every(receiptValid)&&
      new Set(app.supplements.filter(row=>row.idempotency_key!==null).map(row=>row.idempotency_key)).size===app.supplements.filter(row=>row.idempotency_key!==null).length;
  }
  function createSupplementSession(api,changed=()=>{},newKey=()=>window.crypto.randomUUID()) {
    const state={busy:false,attempted:false,locked:false,acknowledged:false,error:null,receipt:null,attempt:null};
    async function transmit(){
      state.busy=true;state.locked=true;state.error=null;changed();
      try {
        const result=await api(`/api/appeals/${state.attempt.appId}/additions/`,{method:"POST",body:JSON.stringify(state.attempt.payload)});
        if(!uuid.test(result?.id))throw new Error("Invalid supplement acknowledgement");
        state.acknowledged=true;state.receipt=result.id;return true;
      } catch(error){state.error=[401,403,404].includes(error?.status)?"denied":"uncertain";return false;}
      finally{state.busy=false;changed();}
    }
    return {state,async send(app,text,fileIds,files){
      if(state.busy||state.attempted||!validProjection(app)||app.status!=="submitted"||app.can_supplement!==true||
        typeof text!=="string"||text.length>100000||!Array.isArray(fileIds)||new Set(fileIds).size!==fileIds.length||
        !Array.isArray(files)||(!text.trim()&&!fileIds.length)||
        !fileIds.every(id=>uuid.test(id)&&files.some(row=>row.id===id&&row.category!=="CONSENT"&&downloadURL(row))))return false;
      const key=newKey();if(!keyValid(key))return false;
      state.attempt=Object.freeze({appId:app.id,payload:Object.freeze({text,file_ids:Object.freeze([...fileIds]),expected_version:app.version,idempotency_key:key})});
      state.attempted=true;return transmit();
    },async retry(app){
      if(state.busy||!state.attempt||state.acknowledged||state.error!=="uncertain"||!validProjection(app)||
        app.id!==state.attempt.appId||app.version!==state.attempt.payload.expected_version)return false;
      return transmit();
    },reconcile(app){
      if(state.busy||!state.attempt||!validProjection(app)||app.id!==state.attempt.appId)return false;
      const payload=state.attempt.payload,row=app.supplements.find(r=>r.idempotency_key===payload.idempotency_key);
      if(!row||row.text!==payload.text||JSON.stringify(row.manifest.map(f=>f.id))!==JSON.stringify(payload.file_ids))return false;
      state.acknowledged=true;state.receipt=row.id;state.error=null;changed();return true;
    }};
  }
  const words={
    en:{localEvidence:"This original was selected for this attempt; no current download is available.",ownEntry:"Your submitted supplement",retainedEvidence:"Evidence is retained in this receipt; no current download is available.",retry:"Retry original supplement",unavailableEvidence:"Some selected originals are no longer available. Remove those selections and review again.",removeUnavailable:"Remove unavailable evidence selections",title:"Additional filing information",refresh:"Refresh supplement history and evidence",loading:"Loading additional information…",
      unavailable:"Additional filing information is unavailable. Refresh or contact the tribunal.",
      help:"Your submitted filing stays unchanged. Add new information or select supporting originals already uploaded to this filing.",
      uploadHelp:"Upload new originals in Application documents, then refresh this list before selecting them.",
      text:"New additional information",evidence:"Supporting originals",review:"Review supplement",edit:"Continue editing supplement",send:"Submit additional information",busy:"Submitting…",
      history:"Previously submitted supplements",none:"No supplements are recorded.",closed:"This filing is not accepting additional information.",
      received:"The server received your supplement. Refresh the history before starting another.",
      uncertain:"Submission was not confirmed. Do not repeat it automatically. Refresh and review the history before starting another supplement.",
      denied:"Supplement access is unavailable. Refresh or sign in again.",
      fresh:"Clear local entry and start a new supplement",frozen:"This attempt keeps its text and selected originals unchanged. Refresh and review the history before clearing this entry.",
      empty:"No text entered",download:"Download supporting original"},
    ar:{localEvidence:"تم اختيار هذا الأصل لهذه المحاولة؛ لا يتوفر تنزيل حالي.",ownEntry:"الإضافة التي قدّمتها",retainedEvidence:"الأدلة محفوظة في هذا الإيصال؛ لا يتوفر تنزيل حالي.",retry:"إعادة محاولة الإضافة الأصلية",unavailableEvidence:"بعض الأصول المحددة لم تعد متاحة. أزل تلك الاختيارات وراجع الإضافة مجددًا.",removeUnavailable:"إزالة اختيارات الأدلة غير المتاحة",title:"معلومات إضافية للطلب",refresh:"تحديث سجل الإضافات والأدلة",loading:"جارٍ تحميل المعلومات الإضافية…",
      unavailable:"المعلومات الإضافية للاستئناف غير متاحة. حدّث القائمة أو تواصل مع المجلس.",
      help:"يبقى الطلب المقدّم دون تغيير. أضف معلومات جديدة أو اختر الأصول الداعمة المرفوعة لهذا الطلب.",
      uploadHelp:"ارفع الأصول الجديدة في مستندات الطلب، ثم حدّث هذه القائمة قبل اختيارها.",
      text:"المعلومات الإضافية الجديدة",evidence:"الأصول الداعمة",review:"مراجعة الإضافة",edit:"متابعة تعديل الإضافة",send:"تقديم المعلومات الإضافية",busy:"جارٍ التقديم…",
      history:"الإضافات المقدّمة سابقاً",none:"لا توجد إضافات مسجلة.",closed:"هذا الطلب لا يقبل معلومات إضافية حالياً.",
      received:"استلم الخادم إضافتك. حدّث السجل قبل بدء إضافة أخرى.",
      uncertain:"لم يتم تأكيد التقديم. لا تكرر المحاولة تلقائياً. حدّث السجل وراجعه قبل بدء إضافة أخرى.",
      denied:"الوصول إلى الإضافات غير متاح. حدّث القائمة أو سجّل الدخول مجدداً.",
      fresh:"مسح الإدخال المحلي وبدء إضافة جديدة",frozen:"تحتفظ هذه المحاولة بالنص والأصول المختارة دون تغيير. حدّث السجل وراجعه قبل مسح هذا الإدخال.",
      empty:"لم يتم إدخال نص",download:"تنزيل الأصل الداعم"}
  };
  function Supplements({applicationId,api,lang="en",disabled=false,onDirtyChange,onBusyChange}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [data,setData]=R.useState(null),[files,setFiles]=R.useState([]),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false);
    const [revision,reload]=R.useState(0),[epoch,newSession]=R.useState(0),[checked,setChecked]=R.useState(false);
    const [text,setText]=R.useState(""),[selected,setSelected]=R.useState([]),[reviewed,setReviewed]=R.useState(false);
    const [frozenEvidence,setFrozenEvidence]=R.useState([]);
    const [,render]=R.useReducer(n=>n+1,0);
    const session=R.useMemo(()=>createSupplementSession(api,render),[applicationId,api,epoch]);
    const state=session.state,dirty=(!!text.trim()||!!selected.length)&&!state.acknowledged;
    R.useEffect(()=>{onDirtyChange?.(dirty);return()=>onDirtyChange?.(false);},[dirty,onDirtyChange]);
    R.useEffect(()=>{onBusyChange?.(state.busy);return()=>onBusyChange?.(false);},[state.busy,onBusyChange]);
    R.useEffect(()=>{
      let active=true;setLoading(true);setError(false);setData(null);setFiles([]);setChecked(false);
      Promise.all([api(`/api/applications/${encodeURIComponent(applicationId)}/`),api(`/api/applications/${encodeURIComponent(applicationId)}/files/`)]).then(([app,evidence])=>{
        if(app?.id!==applicationId||!validProjection(app)||!Array.isArray(evidence?.items)||!evidence.items.every(fileValid)||
          new Set(evidence.items.map(row=>row.id)).size!==evidence.items.length)throw new Error("Invalid own supplement projection");
        if(active){
          session.reconcile(app);setData(app);setFiles(evidence.items);setChecked(session.state.attempted);
          if(!session.state.attempted)setReviewed(false);
        }
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[applicationId,api,revision,session]);
    const allowed=data?.can_supplement===true&&data.status==="submitted";
    const safeEvidence=file=>file.category!=="CONSENT"&&downloadURL(file);
    const missingEvidence=selected.some(id=>!files.some(file=>file.id===id&&safeEvidence(file)));
    const blocked=disabled||loading||!allowed||state.busy||state.attempted;
    const renderFiles=items=>items.map(file=>h(P.Stack,{key:file.id},h(P.Text,null,file.name),
      downloadURL(file)?h(P.Button,{href:downloadURL(file)},t("download")):null));
    const renderFrozen=()=>frozenEvidence.map(original=>{
      const current=files.find(file=>file.id===original.id&&safeEvidence(file));
      return h(P.Stack,{key:original.id},h(P.Text,null,original.name),current
        ?h(P.Button,{href:downloadURL(current)},t("download")):h(P.Text,null,t("localEvidence")));
    });
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      h(P.Button,{disabled:disabled||state.busy||loading,onClick:()=>reload(n=>n+1)},t("refresh")),
      loading?h(P.Text,{role:"status"},t("loading")):null,
      error?h(P.Notice,{tone:"warning",role:"alert"},t("unavailable")):null,
      data?h(P.Stack,null,
        h(P.Panel,{title:t("history")},h(P.Stack,null,
          !data.supplements.length?h(P.Text,null,t("none")):null,
          ...data.supplements.map(row=>h(P.Panel,{key:row.id,title:t("ownEntry")},h(P.Stack,null,
            h(P.Text,null,h("bdi",{dir:"ltr"},row.timestamp)),h(P.Text,null,row.text),...row.manifest.map(file=>{const current=files.find(item=>item.id===file.id&&safeEvidence(item));return current?h(P.Stack,{key:file.id},...renderFiles([current])):h(P.Text,{key:file.id},t("retainedEvidence"));})))))),
        !allowed?h(P.Notice,null,t("closed")):null,
        h(P.Text,null,t("help")),h(P.Text,null,t("uploadHelp")),
        state.error?h(P.Notice,{role:"alert",tone:"danger"},t(state.error)):null,
        state.acknowledged?h(P.Notice,{role:"status"},t("received")):null,
        state.attempted?h(P.Notice,null,t("frozen")):null,
        reviewed?h(P.Panel,{title:t("review")},h(P.Stack,null,h(P.Text,null,text||t("empty")),
          ...(state.attempted?renderFrozen():renderFiles(files.filter(file=>selected.includes(file.id)&&safeEvidence(file))))))
          :h(P.Field,{label:t("text")},h(P.Textarea,{value:text,rows:5,disabled:blocked,onChange:event=>{setText(event.target.value);setReviewed(false);}})),
        !reviewed?h(P.Fieldset,{legend:t("evidence")},...files.filter(safeEvidence).map(file=>h(P.Checkbox,{key:file.id,label:file.name,
          checked:selected.includes(file.id),disabled:blocked,onChange:event=>{setSelected(ids=>event.target.checked?[...ids,file.id]:ids.filter(id=>id!==file.id));setReviewed(false);}}))):null,
        missingEvidence&&!state.attempted?h(P.Notice,{tone:"warning",role:"alert"},h(P.Stack,null,t("unavailableEvidence"),
          h(P.Button,{disabled:blocked,onClick:()=>{setSelected(ids=>ids.filter(id=>files.some(file=>file.id===id&&safeEvidence(file))));setReviewed(false);}},t("removeUnavailable")))):null,
        h(P.Inline,{wrap:true},
          h(P.Button,{variant:"secondary",disabled:blocked||missingEvidence||(!text.trim()&&!selected.length),onClick:()=>setReviewed(!reviewed)},t(reviewed?"edit":"review")),
          h(P.Button,{disabled:blocked||missingEvidence||!reviewed,onClick:()=>{setChecked(false);setFrozenEvidence(files.filter(file=>selected.includes(file.id)));session.send(data,text,selected,files);}},t(state.busy?"busy":"send"))),
        state.attempted&&checked&&!state.acknowledged&&state.error==="uncertain"&&data.version===state.attempt?.payload.expected_version
          ?h(P.Button,{disabled:disabled||state.busy||loading,onClick:()=>{setChecked(false);session.retry(data);}},t("retry")):null,
        state.acknowledged&&checked&&allowed?h(P.Button,{disabled:disabled||state.busy,onClick:()=>{
          setText("");setSelected([]);setFrozenEvidence([]);setReviewed(false);setChecked(false);newSession(n=>n+1);
        }},t("fresh")):null):null));
  }
  window.CTMApplicantSupplements={validProjection,downloadURL,createSupplementSession,Supplements};
})();
