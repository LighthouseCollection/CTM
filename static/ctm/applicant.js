/* CTM applicant workflow. Plenix stays on the pinned external CDN. */
(() => {
  "use strict";
  const types = new Set(["text", "textarea", "date", "choice", "list", "boolean"]);
  const label = (item, lang) => item[`label_${lang === "ar" ? "ar" : "en"}`];
  const bilingual = (item) => ["label_en", "label_ar"].every(
    (key) => typeof item?.[key] === "string" && item[key].trim());
  const fieldChoices = field => (field.choices || []).map(option =>
    typeof option === "string" ? { ...field.choice_labels?.[option], value: option } : option);
  const isVisible = (field, answers) => !field.when ||
    answers[field.when.field] === field.when.equals;
  function updateRecord(rows,index,code,value) {
    if(!Array.isArray(rows)||!Number.isInteger(index)||index<0||index>=rows.length||
      ["id","__proto__","constructor","prototype"].includes(code))return rows;
    return rows.map((row,i)=>i===index?{...row,[code]:value}:row);
  }

  function definitionProblem(app) {
    const q = app?.questionnaire;
    const fields = q?.definition?.fields;
    if (!q?.id || !Number.isInteger(q.version) || q.published !== true ||
        !Array.isArray(fields) || !fields.length) return "definitionUnavailable";
    const codes = new Set();
    const allCodes = new Set(fields.map(field => field?.code));
    for (const field of fields) {
      if (!field || typeof field.code !== "string" || !field.code.trim() ||
          ["__proto__", "constructor", "prototype"].includes(field.code) ||
          codes.has(field.code) || !bilingual(field) || !types.has(field.type) ||
          field.condition || field.visible_if) return "definitionUnavailable";
      if(field.item_fields!==undefined && field.type!=="list")return "definitionUnavailable";
      if (field.when && (typeof field.when !== "object" ||
          !allCodes.has(field.when.field) || field.when.field === field.code ||
          !["string", "boolean"].includes(typeof field.when.equals)))
        return "definitionUnavailable";
      codes.add(field.code);
      if(field.type==="list" && field.item_fields!==undefined) {
        if(!Array.isArray(field.item_fields)||!field.item_fields.length||field.choices||
          field.item_fields.some(child=>!child||child.code==="id"||child.item_fields!==undefined||child.when)||
          definitionProblem({...app,questionnaire:{...q,definition:{fields:field.item_fields}}}))return "definitionUnavailable";
        continue;
      }
      if (["choice", "list"].includes(field.type)) {
        if (!Array.isArray(field.choices) || !field.choices.length)
          return "definitionUnavailable";
        const values = new Set();
        for (const option of fieldChoices(field)) {
          if (!bilingual(option) || typeof option.value !== "string" ||
              !option.value || values.has(option.value)) return "definitionUnavailable";
          values.add(option.value);
        }
      }
    }
    return null;
  }

  function answerProblem(app) {
    if (!Number.isInteger(app.version) || app.version < 0) return "answersUnavailable";
    if (!app.answers || Array.isArray(app.answers) || typeof app.answers !== "object")
      return "answersUnavailable";
    for (const field of app.questionnaire?.definition?.fields || []) {
      const value = app.answers[field.code];
      if (value === null || value === undefined || value === "") continue;
      if (field.type === "list") {
        if(!Array.isArray(value))return "answersUnavailable";
        if(field.item_fields) {
          const ids=value.filter(row=>row?.id).map(row=>row.id);
          if(new Set(ids).size!==ids.length)return "answersUnavailable";
          if(value.some(row=>!row||Array.isArray(row)||typeof row!=="object"||
            (row.id!==undefined&&typeof row.id!=="string")||
            answerProblem({...app,answers:row,questionnaire:{definition:{fields:field.item_fields}}})))
            return "answersUnavailable";
        } else if(value.some(v=>typeof v!=="string"))return "answersUnavailable";
      } else if (field.type === "boolean") {
        if (typeof value !== "boolean") return "answersUnavailable";
      } else if (typeof value !== "string") return "answersUnavailable";
    }
    return null;
  }

  async function startDraft(api) {
    const result = await api("/api/applications/", {
      method:"POST", body:JSON.stringify({kind:"petition"}),
    });
    if (typeof result?.id !== "string" || !result.id) throw new Error("Invalid draft response");
    return result.id;
  }

  function createDraftSession(app, api, changed = () => {}) {
    const state = {
      answers: structuredClone(app.answers || {}), version: app.version,
      editable: app.can_edit === true && !definitionProblem(app) && !answerProblem(app) &&
        !["withdrawn", "expired", "deleted"].includes(app.status),
      dirty: false, saving: false, saved: false, error: null,
    };
    const fields = app.questionnaire?.definition?.fields || [];
    return {
      state,
      change(code, value) {
        if (!state.editable || state.saving || !fields.some(f => f.code === code)) return;
        state.answers = { ...state.answers, [code]: value };
        state.dirty = true; state.saved = false; state.error = null; changed();
      },
      async save() {
        if (!state.editable || state.saving || !state.dirty) return false;
        state.saving = true; state.saved = false; state.error = null; changed();
        try {
          const result = await api(`/api/applications/${encodeURIComponent(app.id)}/`, {
            method: "POST", body: JSON.stringify({
              answers: state.answers, expected_version: state.version,
            }),
          });
          if (!Number.isInteger(result?.version) || result.version !== state.version + 1)
            throw new Error("Invalid save acknowledgement");
          state.version = result.version; state.dirty = false; state.saved = true;
          return true;
        } catch (error) {
          state.error = error.status === 401 ? "expired" :
            [403, 404].includes(error.status) ? "accessDenied" : "saveFailed";
          if ([401, 403, 404].includes(error.status)) state.editable = false;
          return false;
        } finally { state.saving = false; changed(); }
      },
    };
  }

  const words = {
    en: {
      title: "My application", loading: "Loading application…", back: "Back",
      loadFailed: "Unable to load this application.", retry: "Try again",
      definitionUnavailable: "The approved application form is not available. Please contact the tribunal.",
      answersUnavailable: "The saved answers cannot be displayed safely. Please contact the tribunal; your saved data has not been changed.",
      readOnly: "This application is read-only.", save: "Save draft", saving: "Saving…",
      saved: "Your answers have been saved.", unsaved: "You have unsaved changes.",
      saveFailed: "Your changes were not saved. Keep this page open. Another change may have been saved; reload to check before trying again.",
      expired: "Your session has expired. Sign in again before continuing.",
      accessDenied: "This application is no longer available for editing.",
      review: "Review answers", edit: "Continue editing", empty: "Not answered",
      select: "Select an answer", reload: "Reload saved answers",
      discard: "Discard unsaved changes", keep: "Keep editing",
      discardNotice: "Reloading or leaving will discard your unsaved changes.",
      fee: "The application fee is USD 250 and is nonrefundable. Saving a draft does not submit your application or complete payment.",
      draftNotice: "You may save an incomplete draft. Required answers and documents are checked before submission.",
      identityHold:"Your application is awaiting identity review. You can save your answers, but payment and submission remain unavailable until the tribunal completes this review.",
      identityHoldReadOnly:"Your application is awaiting identity review. Payment and submission remain unavailable until the tribunal completes this review.",
      required: "Required", reviewNotice: "Review your answers. Submission and payment are separate steps.",
      yes:"Yes", no:"No", start:"Start or resume application", starting:"Opening application…",
      startHelp:"Prepare your marriage certificates, finalized civil divorce decree and applicant photo. You may type your petition statement or upload a PDF or Word document. Any reported restraining order needs its own copy.",
      startFailed:"Unable to open an application. Try again to resume any existing draft, or contact the tribunal.",
      saveCorrections:"Save corrections",
      refreshFailed:"Your save was acknowledged, but the current application status could not be refreshed. Reload saved answers before filing.",
      status:"Application status", draft:"Draft", submitted:"Submitted", returned:"Returned for corrections", accepted:"Accepted for processing",
      withdrawn:"Withdrawn", expiredStatus:"Expired", deleted:"Deleted", declined:"Declined", statusUnknown:"Status unavailable", caseReference:"Case reference",
      addRecord:"Add another entry",removeRecord:"Remove this entry",noRecords:"No entries added",
      refreshApplication:"Refresh application status",
      correctionNotice:"Corrections preserve your previous submissions. Save your changes, review answers and documents, then resubmit if requested.",
    },
    ar: {
      title: "طلبي", loading: "جارٍ تحميل الطلب…", back: "رجوع",
      loadFailed: "تعذر تحميل هذا الطلب.", retry: "إعادة المحاولة",
      definitionUnavailable: "نموذج الطلب المعتمد غير متاح. يرجى التواصل مع المجلس.",
      answersUnavailable: "لا يمكن عرض الإجابات المحفوظة بأمان. يرجى التواصل مع المجلس؛ لم يتم تغيير بياناتك المحفوظة.",
      readOnly: "هذا الطلب متاح للقراءة فقط.", save: "حفظ المسودة", saving: "جارٍ الحفظ…",
      saved: "تم حفظ إجاباتك.", unsaved: "لديك تغييرات غير محفوظة.",
      saveFailed: "لم يتم حفظ تغييراتك. أبقِ هذه الصفحة مفتوحة. ربما تم حفظ تغيير آخر؛ أعد تحميل الإجابات للتحقق قبل المحاولة مجددًا.",
      expired: "انتهت جلستك. سجّل الدخول مجددًا للمتابعة.",
      accessDenied: "لم يعد هذا الطلب متاحًا للتعديل.",
      review: "مراجعة الإجابات", edit: "متابعة التعديل", empty: "لم تتم الإجابة",
      select: "اختر إجابة", reload: "إعادة تحميل الإجابات المحفوظة",
      discard: "تجاهل التغييرات غير المحفوظة", keep: "متابعة التعديل",
      discardNotice: "ستؤدي إعادة التحميل أو المغادرة إلى فقدان التغييرات غير المحفوظة.",
      fee: "رسوم الطلب ٢٥٠ دولارًا أمريكيًا وغير قابلة للاسترداد. حفظ المسودة لا يرسل الطلب ولا يُتم الدفع.",
      draftNotice: "يمكنك حفظ مسودة غير مكتملة. يتم التحقق من الإجابات والمستندات المطلوبة قبل الإرسال.",
      identityHold:"طلبك بانتظار مراجعة الهوية. يمكنك حفظ إجاباتك، لكن الدفع وتقديم الطلب غير متاحين حتى يكمل المجلس هذه المراجعة.",
      identityHoldReadOnly:"طلبك بانتظار مراجعة الهوية. الدفع وتقديم الطلب غير متاحين حتى يكمل المجلس هذه المراجعة.",
      required: "مطلوب", reviewNotice: "راجع إجاباتك. الإرسال والدفع خطوتان منفصلتان.",
      yes:"نعم", no:"لا", start:"بدء الطلب أو متابعته", starting:"جارٍ فتح الطلب…",
      startHelp:"جهّز شهادات الزواج وحكم الطلاق المدني النهائي وصورتك الشخصية. يمكنك كتابة بيان الطلب أو رفعه بصيغة PDF أو Word. يلزم إرفاق نسخة مستقلة من كل أمر تقييدي يتم الإبلاغ عنه.",
      startFailed:"تعذر فتح طلب. حاول مجددًا لمتابعة أي مسودة موجودة أو تواصل مع المجلس.",
      saveCorrections:"حفظ التصحيحات",
      refreshFailed:"تم تأكيد الحفظ، لكن تعذر تحديث حالة الطلب الحالية. أعد تحميل الإجابات المحفوظة قبل تقديم الطلب.",
      status:"حالة الطلب", draft:"مسودة", submitted:"تم الإرسال", returned:"أعيد للتصحيح", accepted:"مقبول للمعالجة",
      withdrawn:"مسحوب", expiredStatus:"منتهي الصلاحية", deleted:"محذوف", declined:"مرفوض", statusUnknown:"الحالة غير متاحة", caseReference:"رقم القضية",
      addRecord:"إضافة سجل آخر",removeRecord:"إزالة هذا السجل",noRecords:"لم تتم إضافة سجلات",
      refreshApplication:"تحديث حالة الطلب",
      correctionNotice:"تُحفظ طلباتك السابقة عند التصحيح. احفظ التغييرات وراجع الإجابات والمستندات، ثم أعد الإرسال إذا طُلب منك ذلك.",
    },
  };

  function StartApplication({api,lang="en",onOpen}) {
    const R=window.React,P=window.Plenix,h=R.createElement;
    const t=key=>words[lang==="ar"?"ar":"en"][key];
    const [busy,setBusy]=R.useState(false),[error,setError]=R.useState(null);
    const start=async()=>{
      if(busy)return;
      setBusy(true);setError(null);
      try { const id=await startDraft(api); onOpen(id); }
      catch(e){setError(e?.status===401?"expired":"startFailed");}
      finally{setBusy(false);}
    };
    return h(P.Panel,{title:t("start")},h(P.Stack,null,
      h(P.Notice,null,t("fee")),h(P.Text,null,t("startHelp")),
      error?h(P.Notice,{tone:"danger",role:"alert"},t(error)):null,
      h(P.Button,{disabled:busy,onClick:start},t(busy?"starting":"start"))));
  }

  function ApplicationEditor({ applicationId, api, lang = "en", onBack,
    onNavigationGuard }) {
    const R = window.React, P = window.Plenix, h = R.createElement;
    const t = (key) => words[lang === "ar" ? "ar" : "en"][key];
    const [record, setRecord] = R.useState(null);
    const [session, setSession] = R.useState(null);
    const [failure, setFailure] = R.useState(null);
    const [reload, setReload] = R.useState(0);
    const [review, setReview] = R.useState(false);
    const [pending, setPending] = R.useState(null);
    const [filingBusy, setFilingBusy] = R.useState(false);
    const [filingLocked, setFilingLocked] = R.useState(false);
    const [uploadBusy, setUploadBusy] = R.useState(false);
    const [documentRevision, setDocumentRevision] = R.useState(0);
    const [documentsReady, setDocumentsReady] = R.useState(false);
    const [projectionPending, setProjectionPending] = R.useState(false);
    const [projectionFailure, setProjectionFailure] = R.useState(false);
    const documentsReadinessChanged = R.useCallback(ready => {
      setDocumentsReady(ready); setReview(false);
    }, []);
    const documentsChanged = R.useCallback(() => {
      setReview(false); setDocumentRevision(n => n + 1);
    }, []);
    const [, refresh] = R.useReducer(n => n + 1, 0);
    const currentSession = R.useRef(session);
    const projectionRequest = R.useRef(0);
    currentSession.current = session;
    R.useEffect(() => () => { currentSession.current = null; }, []);
    const refreshProjection = R.useCallback(async () => {
      const target=currentSession.current;
      if(!target)return;
      const version=target.state.version, request=++projectionRequest.current;
      setProjectionPending(true);setProjectionFailure(false);
      try {
        const updated=await api(`/api/applications/${encodeURIComponent(applicationId)}/`);
        if(currentSession.current!==target || request!==projectionRequest.current || target.state.version!==version)return;
        if(updated?.id!==applicationId || updated.version!==version)throw new Error("Application changed after saving");
        target.state.editable=updated.can_edit===true&&!definitionProblem(updated)&&!answerProblem(updated)&&
          !["withdrawn","expired","deleted"].includes(updated.status);
        setRecord(updated);
      } catch {
        if(currentSession.current===target && request===projectionRequest.current)setProjectionFailure(true);
      } finally {
        if(currentSession.current===target && request===projectionRequest.current)setProjectionPending(false);
      }
    },[api,applicationId]);
    R.useEffect(() => {
      let active = true;
      setRecord(null); setSession(null); setFailure(null); setReview(false);
      setFilingBusy(false); setFilingLocked(false); setUploadBusy(false); setDocumentsReady(false);
      setProjectionPending(false); setProjectionFailure(false);
      api(`/api/applications/${encodeURIComponent(applicationId)}/`).then(app => {
        if (!active) return;
        setRecord(app); setSession(createDraftSession(app, api, () => { if (active) refresh(); }));
      }).catch(error => {
        if (active) setFailure(error.status === 401 ? "expired" : "loadFailed");
      });
      return () => { active = false; };
    }, [applicationId, api, reload]);
    const state = session?.state;
    const filingRecord = R.useMemo(() => record && ({ ...record,
      version: state?.version ?? record.version,
    }), [record, state?.version, documentRevision]);
    R.useEffect(() => {
      if (!state?.dirty) return;
      const warn = event => { event.preventDefault(); event.returnValue = ""; };
      window.addEventListener("beforeunload", warn);
      return () => window.removeEventListener("beforeunload", warn);
    }, [state?.dirty]);
    const text = (value, props = {}) => h(P.Text, props, value);
    const button = (key, action, props = {}) => h(P.Button, {
      onClick: action, disabled: state?.saving || filingBusy || uploadBusy || projectionPending, ...props,
    }, t(key));
    const navigate = (action) => {
      if (state?.saving || filingBusy || uploadBusy || projectionPending) return;
      if (state?.dirty) setPending(() => action); else action();
    };
    R.useEffect(() => {
      onNavigationGuard?.(navigate);
      return () => onNavigationGuard?.(null);
    }, [onNavigationGuard, session, state?.dirty, state?.saving, filingBusy, uploadBusy, projectionPending]);
    const reloadAnswers = () => navigate(() => setReload(n => n + 1));
    const saveAnswers = async () => {
      const target = session;
      setProjectionPending(true); setProjectionFailure(false);
      try {
        if (await target.save() && currentSession.current===target) await refreshProjection();
      } catch {
        if (currentSession.current === target) setProjectionFailure(true);
      } finally {
        if (currentSession.current === target) setProjectionPending(false);
      }
    };
    let body;
    if (failure) body = h(P.Notice, { tone: "danger", actions: button("retry", reloadAnswers) }, t(failure));
    else if (!record || !session) body = text(t("loading"), { role: "status" });
    else if (definitionProblem(record)) body = h(P.Notice, { tone: "warning" }, t("definitionUnavailable"));
    else if (answerProblem(record)) body = h(P.Notice, { tone: "warning" }, t("answersUnavailable"));
    else {
      const fields = record.questionnaire.definition.fields;
      const renderField = (field, answers=state.answers, change=session.change) => {
        const value = answers[field.code];
        const fieldLabel = label(field, lang);
        const controlsDisabled=state.saving||filingBusy||filingLocked||uploadBusy||projectionPending;
        if(field.item_fields) {
          const rows=Array.isArray(value)?value:[];
          return h(P.Panel,{key:field.code,title:fieldLabel,description:field.required?t("required"):undefined},
            h(P.Stack,null,
              !rows.length?text(t("noRecords")):null,
              ...rows.map((row,index)=>h(P.Panel,{key:row.id||index,title:`${fieldLabel} ${index+1}`},
                h(P.Stack,null,...field.item_fields.map(child=>renderField(child,row,
                  (code,next)=>change(field.code,updateRecord(rows,index,code,next)))),
                  state.editable&&!review?h(P.Button,{disabled:controlsDisabled,
                    onClick:()=>change(field.code,rows.filter((_,i)=>i!==index))},t("removeRecord")):null))),
              state.editable&&!review?h(P.Button,{disabled:controlsDisabled,
                onClick:()=>change(field.code,[...rows,{id:window.crypto.randomUUID()}])},t("addRecord")):null));
        }
        const options = fieldChoices(field).map(o => ({ value: o.value, label: label(o, lang) }));
        const display = value === undefined || value === "" || (Array.isArray(value) && !value.length)
          ? t("empty") : Array.isArray(value)
            ? value.map(v => options.find(o => o.value === v)?.label || v).join("، ")
            : typeof value === "boolean" ? t(value ? "yes" : "no")
            : options.find(o => o.value === value)?.label || String(value);
        if (review || !state.editable) return h(P.Panel, {
          key: field.code, title: fieldLabel,
          description: field.required ? t("required") : undefined,
        }, text(display));
        const shared = {
          value: value ?? "", disabled: state.saving || filingBusy || filingLocked || uploadBusy || projectionPending,
          onChange: event => change(field.code, event.target.value),
        };
        if (field.type === "boolean") return h(P.RadioGroup, {key:field.code,
          label:fieldLabel + (field.required ? ` (${t("required")})` : ""),
          value:typeof value === "boolean" ? String(value) : "",
          options:[{value:"true",label:t("yes"),disabled:shared.disabled},
            {value:"false",label:t("no"),disabled:shared.disabled}],
          onChange:next => change(field.code,next === "true"),
        });
        if (field.type === "list") return h(P.Fieldset, { key: field.code,
          legend: fieldLabel + (field.required ? ` (${t("required")})` : "") },
          ...options.map(option => h(P.Checkbox, {
            key: option.value, label: option.label, disabled: state.saving || filingBusy || filingLocked || uploadBusy || projectionPending,
            checked: Array.isArray(value) && value.includes(option.value),
            onChange: event => change(field.code, event.target.checked
              ? [...(Array.isArray(value) ? value : []), option.value]
              : (Array.isArray(value) ? value : []).filter(v => v !== option.value)),
          })));
        const control = field.type === "choice" ? h(P.Select, { ...shared,
          options: [{ value: "", label: t("select") }, ...options],
        }) : field.type === "textarea" ? h(P.Textarea, { ...shared, rows: 5 })
          : h(P.Input, { ...shared, type: field.type === "date" ? "date" : "text" });
        return h(P.Field, { key: field.code, label: fieldLabel, required: !!field.required }, control);
      };
      body = h(P.Stack, { gap: "lg" },
        text(`${t("status")}: ${t(record.status === "expired" ? "expiredStatus" :
          ["draft","submitted","returned","accepted","withdrawn","deleted","declined"].includes(record.status) ? record.status : "statusUnknown")}`),
        record.case_number ? h(P.Text,{variant:"secondary"},`${t("caseReference")}: `,
          h("bdi",{dir:"ltr"},record.case_number)) : null,
        record.status === "draft" ? h(P.Notice, null, t("fee")) : null,
        record.duplicate_hold===true && ["draft","returned"].includes(record.status)
          ? h(P.Notice,{tone:"warning",role:"status"},t(state.editable?"identityHold":"identityHoldReadOnly")) : null,
        !state.editable ? h(P.Notice, null, t("readOnly")) : text(t(record.status === "draft" ? "draftNotice" : "correctionNotice")),
        state.error ? h(P.Notice, { tone: "danger", role: "alert",
          actions: button("reload", reloadAnswers) }, t(state.error)) : null,
        projectionFailure ? h(P.Notice, {tone:"warning",actions:button("reload",reloadAnswers)},t("refreshFailed")) : null,
        state.saved ? h(P.Notice, { tone: "success", role: "status" }, t("saved")) : null,
        state.dirty ? h(P.Notice, { tone: "warning", role: "status" }, t("unsaved")) : null,
        review ? h(P.Notice, null, t("reviewNotice")) : null,
        ...fields.filter(field => isVisible(field, state.answers)).map(field=>renderField(field)),
        h(P.Inline, { wrap: true },
          state.editable ? button(state.saving || projectionPending ? "saving" : record.status === "draft" ? "save" : "saveCorrections", saveAnswers,
            { disabled: state.saving || filingBusy || filingLocked || uploadBusy || projectionPending || !state.dirty }) : null,
          state.editable ? button(review ? "edit" : "review", () => setReview(!review),
            { variant: "secondary", disabled:state.saving || filingBusy || filingLocked || uploadBusy || projectionPending })
            : button("review", () => setReview(true), {variant:"secondary", disabled:review || filingBusy || filingLocked || uploadBusy || projectionPending}),
        ),
        window.CTMApplicantFiles ? h(window.CTMApplicantFiles.ApplicationFiles, {
          key: "documents", applicationId, answerVersion:state.version, api, lang,
          savedApplication:record,
          disabled: state.dirty || state.saving || filingBusy || filingLocked || projectionPending,
          onBusyChange: setUploadBusy, onChanged: documentsChanged,
          onReadyChange: documentsReadinessChanged,
          onProjectionRefresh: refreshProjection,
        }) : null,
        window.CTMApplicantFiling ? h(window.CTMApplicantFiling.FilingActions, {
          key: "filing", application: filingRecord, api, lang,
          dirty: state.dirty || state.saving || uploadBusy || !documentsReady || projectionPending || projectionFailure || record.version !== state.version, reviewed: review,
          onBusyChange: setFilingBusy, onLockChange: setFilingLocked,
          onRefresh: reloadAnswers,
        }) : null,
        window.CTMApplicantPayments ? h(window.CTMApplicantPayments.PaymentHistory, {
          key:"payment-history",applicationId,api,lang,
          refreshKey:`${record.version}:${record.status}:${record.fee?.status}`,
        }) : null);
    }
    return h(P.LocaleProvider, { locale: lang === "ar" ? "ar" : "en", dir: lang === "ar" ? "rtl" : "ltr" },
      h(P.Stack, { as: "section", gap: "lg", lang, dir: lang === "ar" ? "rtl" : "ltr" },
      h(P.Inline,{wrap:true},
        button("back", () => navigate(onBack), { variant: "ghost" }),
        button("refreshApplication",reloadAnswers,{variant:"ghost"})),
      text(t("title"), { as: "h1", variant: "display" }),
      pending ? h(P.Notice, { tone: "warning", role: "alert", actions: h(P.Inline, { wrap: true },
        button("discard", () => { const action = pending; setPending(null); action(); }),
        button("keep", () => setPending(null), { variant: "secondary" }),
      ) }, t("discardNotice")) : null,
      body));
  }

  window.CTMApplicant = { ApplicationEditor, StartApplication, startDraft, updateRecord, createDraftSession, definitionProblem,
    answerProblem, fieldChoices, isVisible };
})();
