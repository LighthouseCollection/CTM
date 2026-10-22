/* Typed UI for the existing administrator-owned historical workspace contract. */
(() => {
  "use strict";
  const words = {
    en: { title:"Historical case entry", number:"Original case reference", status:"Case status", choose:"Choose status", open:"Open", closed:"Closed", closed_at:"Known closure timestamp", timestampHelp:"Optional. Include the original time-zone offset, for example 2020-01-15T14:30:00-08:00. Leave unknown dates blank.", parties:"Parties", linkedAccount:"Existing linked account reference", partyA:"Party A", partyB:"Party B", name:"Name, if known", legacy_reference:"Original party reference, if known", help:"Retain original references. Leave unknown details blank. New entries do not create or link applicant accounts. Saved account associations in resumed entries are retained.", save:"Save entry", saved:"Entry saved.", reference:"Entry reference", resume:"Resume saved entry", load:"Open entry", publish:"Publish historical case", confirm:"Publish this saved historical record?", confirmHelp:"This creates the historical case using the saved reference, status and parties. Review these details before continuing.", cancel:"Cancel", newEntry:"New entry", published:"Historical case published.", numberRequired:"Enter the original case reference.", statusRequired:"Choose open or closed explicitly.", timestampRequired:"Enter a valid timestamp including its time zone, or leave it blank.", referenceRequired:"Enter a valid saved entry reference.", invalidResponse:"Unable to confirm the saved entry. Your input has been retained.", loading:"Working…" },
    ar: { title:"إدخال قضية تاريخية", number:"رقم القضية الأصلي", status:"حالة القضية", choose:"اختر الحالة", open:"مفتوحة", closed:"مغلقة", closed_at:"وقت الإغلاق المعروف", timestampHelp:"اختياري. أدرج فرق التوقيت الأصلي، مثل ‎2020-01-15T14:30:00-08:00. اترك التاريخ المجهول فارغًا.", parties:"الأطراف", linkedAccount:"رقم الحساب المرتبط الموجود", partyA:"الطرف أ", partyB:"الطرف ب", name:"الاسم إن كان معروفًا", legacy_reference:"رقم الطرف الأصلي إن كان معروفًا", help:"احتفظ بالأرقام الأصلية واترك التفاصيل المجهولة فارغة. لا تنشئ الإدخالات الجديدة حسابات لمقدمي الطلبات ولا تربطها. تُحفظ ارتباطات الحسابات الموجودة في الإدخالات المستأنفة.", save:"حفظ الإدخال", saved:"تم حفظ الإدخال.", reference:"رقم الإدخال", resume:"استئناف إدخال محفوظ", load:"فتح الإدخال", publish:"نشر القضية التاريخية", confirm:"هل تريد نشر السجل التاريخي المحفوظ؟", confirmHelp:"سيتم إنشاء القضية التاريخية بالرقم والحالة والأطراف المحفوظة. راجع التفاصيل قبل المتابعة.", cancel:"إلغاء", newEntry:"إدخال جديد", published:"تم نشر القضية التاريخية.", numberRequired:"أدخل رقم القضية الأصلي.", statusRequired:"اختر مفتوحة أو مغلقة صراحةً.", timestampRequired:"أدخل وقتًا صالحًا مع المنطقة الزمنية أو اتركه فارغًا.", referenceRequired:"أدخل رقمًا صالحًا لإدخال محفوظ.", invalidResponse:"تعذر تأكيد الإدخال المحفوظ. تم الاحتفاظ ببياناتك.", loading:"جارٍ التنفيذ…" },
  };
  function formFrom(payload = {}) {
    return { number:payload.number || "", status:payload.status || "", closed_at:payload.closed_at || "", parties:["A","B"].map((slot) => {
      const row=(payload.parties || []).find((party) => party.slot === slot) || {};
      return { slot, name:row.name || "", legacy_reference:row.legacy_reference || "" };
    }) };
  }
  function payloadFrom(form, previous = {}) {
    return { ...previous, number:form.number, status:form.status, closed_at:form.status === "closed" ? form.closed_at : null,
      parties:form.parties.map((party) => ({ ...(previous.parties || []).find((row) => row.slot === party.slot), ...party })).filter((party) => party.name || party.legacy_reference || party.account_id || (previous.parties || []).some((row) => row.slot === party.slot)) };
  }
  function problem(form) {
    if (!form.number.trim() || form.number.length > 100) return "numberRequired";
    if (!["open","closed"].includes(form.status)) return "statusRequired";
    if (form.status === "closed" && form.closed_at && (!/(Z|[+-]\d\d:\d\d)$/.test(form.closed_at) || !Number.isFinite(Date.parse(form.closed_at)))) return "timestampRequired";
    return null;
  }
  const validId = (value) => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  function validPayload(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    if (["number", "status"].some((key) => value[key] !== undefined && typeof value[key] !== "string")) return false;
    if (value.closed_at !== undefined && value.closed_at !== null && typeof value.closed_at !== "string") return false;
    const parties = value.parties || [];
    return Array.isArray(parties) && parties.length <= 2 && new Set(parties.map((row) => row?.slot)).size === parties.length && parties.every((row) => row && ["A", "B"].includes(row.slot) && ["name", "legacy_reference"].every((key) => row[key] === undefined || typeof row[key] === "string"));
  }
  function Workspace({ api, user, lang, onNavigationGuard, onCase }) {
    const R=window.React, P=window.Plenix, h=R.createElement, U=window.CTMUI, base=window.CTMCouncil;
    const t=(key)=>words[lang === "ar" ? "ar" : "en"][key] || U.translator(lang)(key);
    const [form,setForm]=R.useState(()=>formFrom()), [saved,setSaved]=R.useState(null), [entry,setEntry]=R.useState(""), [pending,setPending]=R.useState(false), [failure,setFailure]=R.useState(null), [notice,setNotice]=R.useState(null), [confirm,setConfirm]=R.useState(false);
    const dirty=JSON.stringify(form)!==JSON.stringify(formFrom(saved?.payload));
    const guard=U.useDraftGuard({dirty,pending,onNavigationGuard,lang});
    const published=Boolean(saved?.finalized_case_id);
    if (!U.canEnroll(user)) return h(P.Notice,{tone:"danger"},U.translator(lang)("unavailable"));
    const update=(patch)=>{setForm({...form,...patch});setFailure(null);setNotice(null);};
    async function save(event) {
      event.preventDefault();
      if (pending || published) return;
      const issue=problem(form);
      if (issue) return setFailure(t(issue));
      setPending(true);setFailure(null);setNotice(null);
      const payload=payloadFrom(form,saved?.payload);
      try {
        const row=await api("/api/historical/",{method:"POST",body:JSON.stringify({payload,...(saved ? {workspace_id:saved.id,expected_version:saved.version} : {})})});
        if (!validId(row.id) || !Number.isInteger(row.version) || row.version < 1) throw Error(t("invalidResponse"));
        setSaved({...row,payload});setForm(formFrom(payload));setEntry(row.id);setNotice("saved");
      } catch(error) {setFailure(error.message===t("invalidResponse") ? error.message : base.serverMessage(error,t));}
      finally {setPending(false);}
    }
    async function resume() {
      if (pending) return;
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(entry.trim())) return setFailure(t("referenceRequired"));
      setPending(true);setFailure(null);setNotice(null);
      try {
        const row=await api(`/api/historical/${encodeURIComponent(entry.trim())}/`);
        if (!validId(row.id) || !validPayload(row.payload) || !Number.isInteger(row.version) || row.version < 1) throw Error(t("invalidResponse"));
        setSaved(row);setForm(formFrom(row.payload));
      } catch(error) {setFailure(base.serverMessage(error,t));}
      finally {setPending(false);}
    }
    async function publish() {
      if (!saved || pending || dirty || published) return;
      setPending(true);setFailure(null);
      try {
        const row=await api(`/api/historical/${encodeURIComponent(saved.id)}/publish/`,{method:"POST",body:JSON.stringify({expected_version:saved.version})});
        if (!validId(row.id)) throw Error(t("invalidResponse"));
        setSaved({...saved,finalized_case_id:row.id});setNotice("published");setConfirm(false);
      } catch(error) {setFailure(base.serverMessage(error,t));}
      finally {setPending(false);}
    }
    return h(P.Stack,{gap:"lg"},
      h(P.Text,{as:"h2",variant:"heading"},t("title")),h(P.Notice,{tone:"info"},t("help")),
      h(P.Inline,{wrap:true,align:"end"},h(P.Field,{label:t("resume")},h(P.Input,{value:entry,disabled:pending,onChange:(e)=>setEntry(e.target.value)})),h(P.Button,{disabled:pending,onClick:()=>guard.navigate(resume)},t("load")),h(P.Button,{disabled:pending,onClick:()=>guard.navigate(()=>{setForm(formFrom());setSaved(null);setEntry("");setNotice(null);setFailure(null);})},t("newEntry"))),
      notice ? h(P.Notice,{tone:"success"},t(notice)) : null,
      failure ? h(P.Notice,{tone:"danger"},failure) : null,
      saved?.payload?.parties?.some((party) => party.account_id) ? h(P.PropertyList, { layout: "stacked" }, ...saved.payload.parties.filter((party) => party.account_id).map((party) => h(P.PropertyList.Item, { key: party.slot, label: `${t(party.slot === "A" ? "partyA" : "partyB")} — ${t("linkedAccount")}`, data: true }, party.account_id))) : null,
      saved ? h(P.PropertyList,null,h(P.PropertyList.Item,{label:t("reference"),data:true},saved.id),h(P.PropertyList.Item,{label:t("version")},saved.version)) : null,
      published ? h(P.Stack, { gap: "md" },
        h(P.PropertyList, { layout: "stacked" },
          ...["number", "status", "closed_at"].filter((key) => form[key]).map((key) => h(P.PropertyList.Item, { key, label: t(key) }, key === "status" ? t(form[key]) : form[key])),
        ),
        ...form.parties.filter((party) => party.name || party.legacy_reference).map((party) => h(P.FormSection, { key: party.slot, title: t(party.slot === "A" ? "partyA" : "partyB") },
          h(P.PropertyList, { layout: "stacked" }, ...["name", "legacy_reference"].filter((key) => party[key]).map((key) => h(P.PropertyList.Item, { key, label: t(key) }, party[key]))),
        )),
        onCase ? h(P.Button, { onClick: () => onCase(saved.finalized_case_id) }, lang === "ar" ? "فتح القضية" : "Open case") : null,
      ) : h(P.Form,{label:t("title"),onSubmit:save,noValidate:true},
        h(P.Inline,{wrap:true},h(P.Field,{label:t("number"),required:true},h(P.Input,{value:form.number,maxLength:100,disabled:pending||published,onChange:(e)=>update({number:e.target.value})})),h(P.Field,{label:t("status"),required:true},h(P.Select,{value:form.status,disabled:pending||published,onChange:(e)=>update({status:e.target.value}),options:[{value:"",label:t("choose")},...['open','closed'].map(value=>({value,label:t(value)}))]}))),
        form.status === "closed" ? h(P.Field,{label:t("closed_at"),description:t("timestampHelp")},h(P.Input,{value:form.closed_at,disabled:pending||published,onChange:(e)=>update({closed_at:e.target.value})})) : null,
        ...form.parties.map((party, index) => h(P.FormSection,
          { key: party.slot, title: t(index === 0 ? "partyA" : "partyB") },
          h(P.Inline, { wrap: true }, ...["name", "legacy_reference"].map((key) =>
            h(P.Field, { key, label: t(key) }, h(P.Input, {
              value: party[key], maxLength: key === "name" ? 300 : 150, disabled: pending || published,
              onChange: (event) => update({ parties: form.parties.map((row, i) => i === index ? { ...row, [key]: event.target.value } : row) }),
            })),
          )),
        )),
        !published ? h(P.FormActions,{sticky:false},h(P.Button,{type:"submit",variant:"primary",disabled:pending,loading:pending},t("save")),h(P.Button,{disabled:pending||!saved||dirty,onClick:()=>setConfirm(true)},t("publish"))) : null),
      h(P.ConfirmDialog,{open:confirm,title:t("confirm"),message:t("confirmHelp"),confirmLabel:t("publish"),cancelLabel:t("cancel"),onConfirm:publish,onCancel:()=>!pending&&setConfirm(false)},failure ? h(P.Notice,{tone:"danger"},failure):null),guard.dialog);
  }
  window.CTMHistorical=Object.freeze({formFrom,payloadFrom,problem,validPayload,Workspace});
})();
