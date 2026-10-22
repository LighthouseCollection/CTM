/* Append-only appeal information. Own history/capability projection is required. */
(() => {
  "use strict";
  const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const fileValid=row=>!!row&&uuid.test(row.id)&&typeof row.name==="string"&&typeof row.scan_state==="string";
  const downloadURL=row=>fileValid(row)&&row.scan_state==="clean"&&row.download_url===`/api/files/${row.id}/`?row.download_url:null;
  function validProjection(app) {
    return !!app&&uuid.test(app.id)&&app.kind==="appeal"&&typeof app.status==="string"&&
      typeof app.can_supplement==="boolean"&&Array.isArray(app.supplements)&&
      new Set(app.supplements.map(row=>row?.id)).size===app.supplements.length&&
      app.supplements.every(row=>row&&uuid.test(row.id)&&typeof row.text==="string"&&typeof row.actor==="string"&&
        typeof row.timestamp==="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(row.timestamp)&&Number.isFinite(Date.parse(row.timestamp))&&
        Array.isArray(row.manifest)&&row.manifest.every(fileValid));
  }
  function createSupplementSession(api,changed=()=>{}) {
    const state={busy:false,attempted:false,locked:false,acknowledged:false,error:null};
    return {state,async send(app,text,fileIds,files){
      if(state.busy||state.attempted||!validProjection(app)||app.status!=="submitted"||app.can_supplement!==true||
        typeof text!=="string"||!Array.isArray(fileIds)||new Set(fileIds).size!==fileIds.length||
        !Array.isArray(files)||(!text.trim()&&!fileIds.length)||
        !fileIds.every(id=>uuid.test(id)&&files.some(row=>row.id===id&&downloadURL(row))))return false;
      const payload={text,file_ids:[...fileIds]};
      state.busy=true;state.attempted=true;state.error=null;changed();
      try {
        const result=await api(`/api/appeals/${app.id}/additions/`,{method:"POST",body:JSON.stringify(payload)});
        if(!uuid.test(result?.id))throw new Error("Invalid supplement acknowledgement");
        state.acknowledged=true;return true;
      } catch(error){
        state.error=[401,403,404].includes(error?.status)?"denied":"uncertain";
        return false;
      } finally {state.busy=false;state.locked=true;changed();}
    }};
  }
  const words={
    en:{title:"Additional appeal information",refresh:"Refresh supplement history and evidence",loading:"Loading additional information…",
      unavailable:"Additional appeal information is unavailable. Refresh or contact the tribunal.",
      help:"Your submitted appeal stays unchanged. Add new information or select supporting originals already uploaded to this appeal.",
      uploadHelp:"Upload new originals in Application documents, then refresh this list before selecting them.",
      text:"New additional information",evidence:"Supporting originals",review:"Review supplement",edit:"Continue editing supplement",send:"Submit additional information",busy:"Submitting…",
      history:"Previously submitted supplements",none:"No supplements are recorded.",closed:"This appeal is not accepting additional information.",
      received:"The server received your supplement. Refresh the history before starting another.",
      uncertain:"Submission was not confirmed. Do not repeat it automatically. Refresh and review the history before starting another supplement.",
      denied:"Supplement access is unavailable. Refresh or sign in again.",
      fresh:"Clear local entry and start a new supplement",frozen:"This attempt keeps its text and selected originals unchanged. Refresh and review the history before clearing this entry.",
      empty:"No text entered",download:"Download supporting original"},
    ar:{title:"معلومات إضافية للاستئناف",refresh:"تحديث سجل الإضافات والأدلة",loading:"جارٍ تحميل المعلومات الإضافية…",
      unavailable:"المعلومات الإضافية للاستئناف غير متاحة. حدّث القائمة أو تواصل مع المجلس.",
      help:"يبقى الاستئناف المقدّم دون تغيير. أضف معلومات جديدة أو اختر الأصول الداعمة المرفوعة لهذا الاستئناف.",
      uploadHelp:"ارفع الأصول الجديدة في مستندات الطلب، ثم حدّث هذه القائمة قبل اختيارها.",
      text:"المعلومات الإضافية الجديدة",evidence:"الأصول الداعمة",review:"مراجعة الإضافة",edit:"متابعة تعديل الإضافة",send:"تقديم المعلومات الإضافية",busy:"جارٍ التقديم…",
      history:"الإضافات المقدّمة سابقاً",none:"لا توجد إضافات مسجلة.",closed:"هذا الاستئناف لا يقبل معلومات إضافية حالياً.",
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
          setData(app);setFiles(evidence.items);setChecked(session.state.attempted);
          if(!session.state.attempted){setReviewed(false);setSelected(ids=>ids.filter(id=>evidence.items.some(row=>row.id===id&&downloadURL(row))));}
        }
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[applicationId,api,revision,session]);
    const allowed=data?.can_supplement===true&&data.status==="submitted";
    const blocked=disabled||loading||!allowed||state.busy||state.attempted;
    const renderFiles=items=>items.map(file=>h(P.Stack,{key:file.id},h(P.Text,null,file.name),
      downloadURL(file)?h(P.Button,{href:downloadURL(file)},t("download")):null));
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      h(P.Button,{disabled:disabled||state.busy||loading,onClick:()=>reload(n=>n+1)},t("refresh")),
      loading?h(P.Text,{role:"status"},t("loading")):null,
      error?h(P.Notice,{tone:"warning",role:"alert"},t("unavailable")):null,
      data?h(P.Stack,null,
        h(P.Panel,{title:t("history")},h(P.Stack,null,
          !data.supplements.length?h(P.Text,null,t("none")):null,
          ...data.supplements.map(row=>h(P.Panel,{key:row.id,title:row.actor},h(P.Stack,null,
            h(P.Text,null,h("bdi",{dir:"ltr"},row.timestamp)),h(P.Text,null,row.text),...renderFiles(row.manifest)))))),
        !allowed?h(P.Notice,null,t("closed")):null,
        h(P.Text,null,t("help")),h(P.Text,null,t("uploadHelp")),
        state.error?h(P.Notice,{role:"alert",tone:"danger"},t(state.error)):null,
        state.acknowledged?h(P.Notice,{role:"status"},t("received")):null,
        state.attempted?h(P.Notice,null,t("frozen")):null,
        reviewed?h(P.Panel,{title:t("review")},h(P.Stack,null,h(P.Text,null,text||t("empty")),
          ...renderFiles(state.attempted?frozenEvidence:files.filter(file=>selected.includes(file.id)))))
          :h(P.Field,{label:t("text")},h(P.Textarea,{value:text,rows:5,disabled:blocked,onChange:event=>{setText(event.target.value);setReviewed(false);}})),
        !reviewed?h(P.Fieldset,{legend:t("evidence")},...files.filter(downloadURL).map(file=>h(P.Checkbox,{key:file.id,label:file.name,
          checked:selected.includes(file.id),disabled:blocked,onChange:event=>{setSelected(ids=>event.target.checked?[...ids,file.id]:ids.filter(id=>id!==file.id));setReviewed(false);}}))):null,
        h(P.Inline,{wrap:true},
          h(P.Button,{variant:"secondary",disabled:blocked||(!text.trim()&&!selected.length),onClick:()=>setReviewed(!reviewed)},t(reviewed?"edit":"review")),
          h(P.Button,{disabled:blocked||!reviewed,onClick:()=>{setChecked(false);setFrozenEvidence(files.filter(file=>selected.includes(file.id)));session.send(data,text,selected,files);}},t(state.busy?"busy":"send"))),
        state.attempted&&checked&&allowed?h(P.Button,{disabled:disabled||state.busy,onClick:()=>{
          setText("");setSelected([]);setFrozenEvidence([]);setReviewed(false);setChecked(false);newSession(n=>n+1);
        }},t("fresh")):null):null));
  }
  window.CTMApplicantSupplements={validProjection,downloadURL,createSupplementSession,Supplements};
})();
