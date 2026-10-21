/* CTM applicant workflow. Plenix stays on the pinned external CDN. */
(() => {
  "use strict";
  const types = new Set(["text", "textarea", "date", "choice", "list"]);
  const label = (item, lang) => item[`label_${lang === "ar" ? "ar" : "en"}`];
  const bilingual = (item) => ["label_en", "label_ar"].every(
    (key) => typeof item?.[key] === "string" && item[key].trim());

  function definitionProblem(app) {
    const q = app?.questionnaire;
    const fields = q?.definition?.fields;
    if (!q?.id || !Number.isInteger(q.version) || q.published !== true ||
        !Array.isArray(fields) || !fields.length) return "definitionUnavailable";
    const codes = new Set();
    for (const field of fields) {
      if (!field || typeof field.code !== "string" || !field.code.trim() ||
          ["__proto__", "constructor", "prototype"].includes(field.code) ||
          codes.has(field.code) || !bilingual(field) || !types.has(field.type) ||
          field.condition || field.visible_if) return "definitionUnavailable";
      codes.add(field.code);
      if (["choice", "list"].includes(field.type)) {
        if (!Array.isArray(field.choices) || !field.choices.length)
          return "definitionUnavailable";
        const values = new Set();
        for (const option of field.choices) {
          if (!bilingual(option) || typeof option.value !== "string" ||
              !option.value || values.has(option.value)) return "definitionUnavailable";
          values.add(option.value);
        }
      }
    }
    return null;
  }

  function createDraftSession(app, api, changed = () => {}) {
    const state = {
      answers: structuredClone(app.answers || {}), version: app.version,
      editable: app.can_edit === true && !definitionProblem(app) &&
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
      required: "Required", reviewNotice: "Review your answers. Submission and payment are separate steps.",
    },
    ar: {
      title: "طلبي", loading: "جارٍ تحميل الطلب…", back: "رجوع",
      loadFailed: "تعذر تحميل هذا الطلب.", retry: "إعادة المحاولة",
      definitionUnavailable: "نموذج الطلب المعتمد غير متاح. يرجى التواصل مع المجلس.",
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
      required: "مطلوب", reviewNotice: "راجع إجاباتك. الإرسال والدفع خطوتان منفصلتان.",
    },
  };

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
    const [, refresh] = R.useReducer(n => n + 1, 0);
    R.useEffect(() => {
      let active = true;
      setRecord(null); setSession(null); setFailure(null); setReview(false);
      api(`/api/applications/${encodeURIComponent(applicationId)}/`).then(app => {
        if (!active) return;
        setRecord(app); setSession(createDraftSession(app, api, () => { if (active) refresh(); }));
      }).catch(error => {
        if (active) setFailure(error.status === 401 ? "expired" : "loadFailed");
      });
      return () => { active = false; };
    }, [applicationId, api, reload]);
    const state = session?.state;
    R.useEffect(() => {
      if (!state?.dirty) return;
      const warn = event => { event.preventDefault(); event.returnValue = ""; };
      window.addEventListener("beforeunload", warn);
      return () => window.removeEventListener("beforeunload", warn);
    }, [state?.dirty]);
    const text = (value, props = {}) => h(P.Text, props, value);
    const button = (key, action, props = {}) => h(P.Button, {
      onClick: action, disabled: state?.saving, ...props,
    }, t(key));
    const navigate = (action) => {
      if (state?.saving) return;
      if (state?.dirty) setPending(() => action); else action();
    };
    R.useEffect(() => {
      onNavigationGuard?.(navigate);
      return () => onNavigationGuard?.(null);
    }, [onNavigationGuard, session, state?.dirty, state?.saving]);
    const reloadAnswers = () => navigate(() => setReload(n => n + 1));
    let body;
    if (failure) body = h(P.Notice, { tone: "danger", actions: button("retry", reloadAnswers) }, t(failure));
    else if (!record || !session) body = text(t("loading"), { role: "status" });
    else if (definitionProblem(record)) body = h(P.Notice, { tone: "warning" }, t("definitionUnavailable"));
    else {
      const fields = record.questionnaire.definition.fields;
      const renderField = (field) => {
        const value = state.answers[field.code];
        const fieldLabel = label(field, lang);
        const options = (field.choices || []).map(o => ({ value: o.value, label: label(o, lang) }));
        const display = value === undefined || value === "" || (Array.isArray(value) && !value.length)
          ? t("empty") : Array.isArray(value)
            ? value.map(v => options.find(o => o.value === v)?.label || v).join("، ")
            : options.find(o => o.value === value)?.label || String(value);
        if (review || !state.editable) return h(P.Panel, {
          key: field.code, title: fieldLabel,
          description: field.required ? t("required") : undefined,
        }, text(display));
        const shared = {
          value: value ?? "", disabled: state.saving,
          onChange: event => session.change(field.code, event.target.value),
        };
        if (field.type === "list") return h(P.Fieldset, { key: field.code,
          legend: fieldLabel + (field.required ? ` (${t("required")})` : "") },
          ...options.map(option => h(P.Checkbox, {
            key: option.value, label: option.label, disabled: state.saving,
            checked: Array.isArray(value) && value.includes(option.value),
            onChange: event => session.change(field.code, event.target.checked
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
        h(P.Notice, null, t("fee")),
        !state.editable ? h(P.Notice, null, t("readOnly")) : text(t("draftNotice")),
        state.error ? h(P.Notice, { tone: "danger", role: "alert",
          actions: button("reload", reloadAnswers) }, t(state.error)) : null,
        state.saved ? h(P.Notice, { tone: "success", role: "status" }, t("saved")) : null,
        state.dirty ? h(P.Notice, { tone: "warning", role: "status" }, t("unsaved")) : null,
        review ? h(P.Notice, null, t("reviewNotice")) : null,
        ...fields.map(renderField),
        h(P.Inline, { wrap: true },
          state.editable ? button(state.saving ? "saving" : "save", () => session.save(),
            { disabled: state.saving || !state.dirty }) : null,
          state.editable ? button(review ? "edit" : "review", () => setReview(!review), { variant: "secondary" }) : null,
        ));
    }
    return h(P.LocaleProvider, { locale: lang === "ar" ? "ar" : "en", dir: lang === "ar" ? "rtl" : "ltr" },
      h(P.Stack, { as: "section", gap: "lg", lang, dir: lang === "ar" ? "rtl" : "ltr" },
      button("back", () => navigate(onBack), { variant: "ghost" }),
      text(t("title"), { as: "h1", variant: "display" }),
      pending ? h(P.Notice, { tone: "warning", role: "alert", actions: h(P.Inline, { wrap: true },
        button("discard", () => { const action = pending; setPending(null); action(); }),
        button("keep", () => setPending(null), { variant: "secondary" }),
      ) }, t("discardNotice")) : null,
      body));
  }

  window.CTMApplicant = { ApplicationEditor, createDraftSession, definitionProblem };
})();
