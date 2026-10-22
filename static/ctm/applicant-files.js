/* Own application documents only. Server scanning and ownership remain authoritative. */
(() => {
  "use strict";
  const categories = new Set(["MC","CMC","CDD","PHOTO","SPOUSE_PHOTO","PET","RO"]);
  const validRequirement = r => !!r && categories.has(r.category) && typeof r.context === "string" &&
    (r.category !== "RO" || !!r.context.trim()) &&
    typeof r.required === "boolean" && [r.label_en,r.label_ar].every(s => typeof s === "string" && !!s.trim());
  function validListing(result) {
    if (typeof result?.can_upload !== "boolean" || !Array.isArray(result.items) ||
        !Array.isArray(result.requirements) || !result.requirements.every(validRequirement)) return false;
    const keys=result.requirements.map(r=>JSON.stringify([r.category,r.context]));
    if (new Set(keys).size !== keys.length) return false;
    const attachments=new Set(), ids=new Set();
    for (const row of result.items) {
      if (!row || typeof row.id !== "string" || !row.id || ids.has(row.id) ||
          typeof row.attachment_id !== "string" || !row.attachment_id || attachments.has(row.attachment_id) ||
          typeof row.name !== "string" || !categories.has(row.category) || typeof row.context !== "string") return false;
      ids.add(row.id); attachments.add(row.attachment_id);
    }
    return true;
  }
  function downloadURL(row) {
    const id = row?.id;
    return row?.scan_state === "clean" && /^[0-9a-f-]{36}$/i.test(id) &&
      row.download_url === `/api/files/${id}/` ? row.download_url : null;
  }
  async function uploadFile({applicationId, requirement, file, replacement, api}) {
    if (!applicationId || !validRequirement(requirement) || !file ||
        !Number.isFinite(file.size) || file.size <= 0 || file.size > 25 * 1024 * 1024)
      throw new Error("Invalid upload");
    if (replacement && (!replacement.attachment_id || replacement.category !== requirement.category ||
        replacement.context !== requirement.context)) throw new Error("Invalid replacement context");
    const body = new FormData();
    body.append("application_id", applicationId); body.append("category", requirement.category);
    body.append("context", requirement.context); body.append("visibility", "own");
    body.append("file", file);
    if (replacement) body.append("attachment_id", replacement.attachment_id);
    const result = await api("/api/files/", {method:"POST", body});
    if (!result?.id || !["clean","pending","rejected"].includes(result.scan_state))
      throw new Error("Invalid upload acknowledgement");
    return result;
  }
  const words = {
    en: {title:"Application documents", loading:"Loading documents…", unavailable:"Application documents are not available. Please try again or contact the tribunal.",
      refresh:"Refresh documents", required:"Required", optional:"Optional", missing:"Not uploaded",
      clean:"Safety checks passed", pending:"Safety checks pending", rejected:"File rejected", unknown:"Safety status unavailable",
      choose:"Choose file", none:"No file chosen", count:"{count} files", remove:"Remove {name}",
      upload:"Upload original", replace:"Upload corrected original", busy:"Uploading…", download:"Download original",
      failed:"The upload was not confirmed. Refresh the document list before trying again; your original file has not been removed.",
      received:"The file was received. Only files that pass safety checks can be used for filing.",
      expired:"Your session has expired. Sign in again to continue.", denied:"Document access is no longer available.",
      size:"Up to 25 MB. The server checks the file format and safety.",
      savedContext:"Uploads are paused while answers are being edited or a filing action is in progress.", additional:"Additional uploaded originals",
    },
    ar: {title:"مستندات الطلب", loading:"جارٍ تحميل المستندات…", unavailable:"مستندات الطلب غير متاحة. يرجى إعادة المحاولة أو التواصل مع المجلس.",
      refresh:"تحديث المستندات", required:"مطلوب", optional:"اختياري", missing:"لم يتم الرفع",
      clean:"اجتاز فحوص السلامة", pending:"فحوص السلامة قيد الانتظار", rejected:"تم رفض الملف", unknown:"حالة السلامة غير متاحة",
      choose:"اختيار ملف", none:"لم يتم اختيار ملف", count:"{count} ملفات", remove:"إزالة {name}",
      upload:"رفع الأصل", replace:"رفع الأصل المصحح", busy:"جارٍ الرفع…", download:"تنزيل الأصل",
      failed:"لم يتم تأكيد رفع الملف. حدّث قائمة المستندات قبل المحاولة مجددًا؛ لم يتم حذف ملفك الأصلي.",
      received:"تم استلام الملف. لا يمكن استخدامه لتقديم الطلب إلا بعد اجتياز فحوص السلامة.",
      expired:"انتهت جلستك. سجّل الدخول مجددًا للمتابعة.", denied:"لم يعد الوصول إلى المستندات متاحًا.",
      size:"حتى ٢٥ ميغابايت. يتحقق الخادم من صيغة الملف وسلامته.",
      savedContext:"رفع الملفات متوقف أثناء تعديل الإجابات أو تنفيذ إجراء لتقديم الطلب.", additional:"أصول إضافية مرفوعة",
    },
  };
  function ApplicationFiles({applicationId, answerVersion, api, lang="en", disabled=false, onBusyChange, onChanged, onReadyChange}) {
    const R=window.React, P=window.Plenix, h=R.createElement;
    const t=k=>words[lang === "ar" ? "ar" : "en"][k];
    const [data,setData]=R.useState(null), [error,setError]=R.useState(null);
    const [busy,setBusy]=R.useState(false), [locked,setLocked]=R.useState(false);
    const [revision,reload]=R.useState(0), [received,setReceived]=R.useState(false);
    const [selected,setSelected]=R.useState({}), [pickerRevision,resetPickers]=R.useState(0);
    const [needsRefresh,setNeedsRefresh]=R.useState(false);
    const ready=!!data&&!busy&&!needsRefresh&&!error&&data.requirements.every(r=>!r.required||
      data.items.some(row=>row.category===r.category&&row.context===r.context&&row.scan_state==="clean"));
    R.useEffect(()=>{onBusyChange?.(busy);return()=>onBusyChange?.(false);},[busy,onBusyChange]);
    R.useEffect(()=>{onReadyChange?.(ready);},[ready,onReadyChange]);
    R.useEffect(()=>{
      let active=true; setData(null); setError(null);
      api(`/api/applications/${encodeURIComponent(applicationId)}/files/`).then(result=>{
        if (!validListing(result)) throw new Error("Invalid file projection");
        if(active){setData(result);setNeedsRefresh(false);}
      }).catch(e=>{if(active){
        setError(e?.status===401?"expired":[403,404].includes(e?.status)?"denied":"unavailable");
        if([401,403].includes(e?.status))setLocked(true);
      }});
      return()=>{active=false;};
    },[applicationId,answerVersion,api,revision]);
    const send=async(requirement,replacement,key)=>{
      if(busy || disabled || locked || needsRefresh || data?.can_upload !== true || !selected[key])return;
      setBusy(true);setError(null);setReceived(false);
      onChanged?.();
      try {
        await uploadFile({applicationId,requirement,replacement,file:selected[key],api});
        setReceived(true);setSelected({});resetPickers(n=>n+1);reload(n=>n+1);
      } catch(e) {
        setError(e?.status===401?"expired":[403,404].includes(e?.status)?"denied":"failed");
        if([401,403,404].includes(e?.status))setLocked(true);
        setNeedsRefresh(true);
      } finally {setBusy(false);}
    };
    const accept=category=>["PHOTO","SPOUSE_PHOTO"].includes(category)?".jpg,.jpeg,.png,.gif,.webp":
      category==="PET"?".pdf,.doc,.docx":".pdf,.jpg,.jpeg,.png,.gif,.webp";
    const renderRow=row=>h(P.Stack,{key:row.id},
      h(P.Text,null,`${row.name} · ${t(["clean","pending","rejected"].includes(row.scan_state)?row.scan_state:"unknown")}`),
      downloadURL(row)?h(P.Button,{href:downloadURL(row)},t("download")):null);
    const additional=(data?.items||[]).filter(row=>!data.requirements.some(r=>r.category===row.category&&r.context===row.context));
    return h(P.Panel,{title:t("title")},h(P.Stack,null,
      error?h(P.Notice,{tone:"danger",role:"alert"},t(error)):null,
      received?h(P.Notice,{role:"status"},t("received")):null,
      disabled?h(P.Notice,null,t("savedContext")):null,
      !data&&!error?h(P.Text,{role:"status"},t("loading")):null,
      h(P.Button,{disabled:busy||disabled,onClick:()=>reload(n=>n+1)},t("refresh")),
      ...(data?.requirements||[]).map(requirement=>{
        const key=JSON.stringify([requirement.category,requirement.context]);
        const rows=data.items.filter(row=>row.category===requirement.category&&row.context===requirement.context);
        // Multiple current attachments are displayed individually; replacement is
        // offered only for an unambiguous same-context attachment.
        const replacement=rows.length===1?rows[0]:null;
        const controlsDisabled=busy||disabled||locked||needsRefresh||data.can_upload!==true;
        return h(P.Panel,{key,title:requirement[lang==="ar"?"label_ar":"label_en"],
          description:t(requirement.required?"required":"optional")},h(P.Stack,null,
          !rows.length?h(P.Text,null,t("missing")):null,
          ...rows.map(renderRow),
          data.can_upload===true?h(P.Stack,null,
            h(P.Field,{label:requirement[lang==="ar"?"label_ar":"label_en"],description:`${accept(requirement.category)}. ${t("size")}`},
              h(P.FileInput,{key:pickerRevision,accept:accept(requirement.category),disabled:controlsDisabled,
                strings:{choose:t("choose"),none:t("none"),count:t("count"),remove:t("remove")},
                onChange:files=>setSelected(previous=>({...previous,[key]:files[0]||null}))})),
            h(P.Button,{disabled:controlsDisabled||!selected[key],onClick:()=>send(requirement,replacement,key)},
              t(busy?"busy":replacement?"replace":"upload"))) : null));
      }),
      additional.length?h(P.Panel,{title:t("additional")},h(P.Stack,null,...additional.map(renderRow))):null));
  }
  window.CTMApplicantFiles={validRequirement,validListing,downloadURL,uploadFile,ApplicationFiles};
})();
