/* Applicant filing actions; only server capabilities enable writes. */
(() => {
  "use strict";
  const settled = new Set(["paid", "waived", "historical_exempt"]);
  const validAttestation = a => a?.accepted === true && typeof a.name === "string" && !!a.name.trim();
  function availability(app) {
    const q = app?.questionnaire;
    const declaration = q?.published === true && !!q.id && Number.isInteger(q.version) &&
      [q.declaration_en, q.declaration_ar].every(s => typeof s === "string" && !!s.trim());
    const eligible = !!app?.id && Number.isInteger(app.version) && app.version >= 0 &&
      app.duplicate_hold !== true;
    return {
      declaration,
      checkout: eligible && declaration && app.status === "draft" && app.can_checkout === true &&
        app.fee?.status === "due" && app.fee.currency === "USD" && app.fee.amount_minor === 25000,
      submit: eligible && declaration && app.status === "draft" && app.can_submit === true && settled.has(app.fee?.status),
      resubmit: eligible && app.status === "returned" && app.can_resubmit === true && settled.has(app.fee?.status),
    };
  }
  function checkoutURL(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === "checkout.stripe.com" &&
        !url.username && !url.password && !url.port ? url.href : null;
    } catch { return null; }
  }
  function createFilingSession(app, api, makeKey, changed = () => {}) {
    const state = { busy: false, locked: false, error: null, submitted: false, attempted: false };
    let key, frozenSubmission;
    const allowed = () => !state.busy && !state.locked && !state.submitted;
    const fail = (error, fallback) => {
      state.error = error?.status === 401 ? "expired" : [403,404].includes(error?.status) ? "accessDenied" : fallback;
      if ([401,403,404].includes(error?.status)) state.locked = true;
    };
    return {
      state,
      async checkout(attestation) {
        if (!allowed() || !availability(app).checkout || !validAttestation(attestation)) return null;
        state.busy = true; state.error = null; changed();
        try {
          const result = await api(`/api/applications/${encodeURIComponent(app.id)}/checkout/`, {
            method: "POST", body: JSON.stringify({ attestation, expected_version: app.version }),
          });
          const url = checkoutURL(result?.checkout_url);
          if (!result?.intent || !url) throw new Error("Invalid checkout response");
          return url;
        } catch (error) { fail(error, "checkoutFailed"); return null; }
        finally { state.busy = false; changed(); }
      },
      async submit(attestation) {
        const actions = availability(app);
        if (!allowed() || !(actions.submit || actions.resubmit) ||
            (!actions.resubmit && !validAttestation(attestation))) return false;
        state.busy = true; state.error = null; changed();
        try {
          key ||= makeKey();
          if (!frozenSubmission) {
            frozenSubmission = { idempotency_key: key, expected_version: app.version };
            if (!actions.resubmit) frozenSubmission.attestation = {accepted:true, name:attestation.name};
          }
          state.attempted = true;
          const result = await api(`/api/applications/${encodeURIComponent(app.id)}/submit/`, {
            method: "POST", body: JSON.stringify(frozenSubmission),
          });
          if (typeof result?.id !== "string" || !result.id) throw new Error("Invalid submission response");
          state.submitted = true;
          return true;
        } catch (error) { fail(error, "submitFailed"); return false; }
        finally { state.busy = false; changed(); }
      },
    };
  }
  const words = {
    en: {
      title: "Declaration and filing", fee: "Application fee", due: "Payment due",
      paid: "Payment verified by the tribunal", waived: "Authorized fee waiver",
      historical_exempt: "Historical filing exemption", unknown: "Payment status unavailable",
      declaration: "Declaration", accept: "I have read and accept this declaration.",
      name: "Your full name", checkout: "Continue to secure payment", submit: "Submit application",
      resubmit: "Resubmit corrections", busy: "Processing…", unavailable: "Filing actions are not available yet. Your saved answers remain available.",
      saveFirst: "Save and review your current answers before filing.",
      checkoutFailed: "Payment could not be started. No payment success has been recorded here. Check your application status before trying again.",
      submitFailed: "Submission was not confirmed. Keep this page open and retry or reload the application status before taking further action.",
      expired: "Your session has expired. Sign in again to continue.", accessDenied: "You no longer have permission to file this application.",
      received: "The server acknowledged your submission. Reload the application to see its current status.",
      returnNotice: "Corrections use your original declaration and fee. You do not need to sign or pay again.",
      returned: "Correction instructions", notRefundable: "The USD 250 application fee is nonrefundable.",
      reload: "Reload application status", frozen: "This filing attempt keeps the reviewed answers and signature unchanged. Reload the application status before editing again.",
    },
    ar: {
      title: "الإقرار وتقديم الطلب", fee: "رسوم الطلب", due: "الدفع مطلوب",
      paid: "تم التحقق من الدفع لدى المجلس", waived: "إعفاء معتمد من الرسوم",
      historical_exempt: "إعفاء لطلب تاريخي", unknown: "حالة الدفع غير متاحة",
      declaration: "الإقرار", accept: "قرأت هذا الإقرار وأوافق عليه.", name: "اسمك الكامل",
      checkout: "المتابعة إلى الدفع الآمن", submit: "إرسال الطلب", resubmit: "إعادة إرسال التصحيحات", busy: "جارٍ المعالجة…",
      unavailable: "إجراءات تقديم الطلب غير متاحة بعد. تظل إجاباتك المحفوظة متاحة.",
      saveFirst: "احفظ إجاباتك الحالية وراجعها قبل تقديم الطلب.",
      checkoutFailed: "تعذر بدء الدفع. لم يتم تسجيل نجاح الدفع هنا. تحقق من حالة طلبك قبل المحاولة مجددًا.",
      submitFailed: "لم يتم تأكيد إرسال الطلب. أبقِ هذه الصفحة مفتوحة وأعد المحاولة أو أعد تحميل حالة الطلب قبل اتخاذ أي إجراء آخر.",
      expired: "انتهت جلستك. سجّل الدخول مجددًا للمتابعة.", accessDenied: "لم يعد لديك إذن لتقديم هذا الطلب.",
      received: "أكد الخادم استلام طلبك. أعد تحميل الطلب لعرض حالته الحالية.",
      returnNotice: "تستخدم التصحيحات الإقرار والرسوم الأصليين. لا تحتاج إلى التوقيع أو الدفع مجددًا.",
      returned: "تعليمات التصحيح", notRefundable: "رسوم الطلب البالغة ٢٥٠ دولارًا أمريكيًا غير قابلة للاسترداد.",
      reload: "إعادة تحميل حالة الطلب", frozen: "تحتفظ محاولة التقديم هذه بالإجابات والتوقيع اللذين تمت مراجعتهما دون تغيير. أعد تحميل حالة الطلب قبل التعديل مجددًا.",
    },
  };
  function FilingActions({ application, api, lang = "en", dirty = false, reviewed = false,
    onBusyChange, onLockChange, onRefresh, onCheckout = url => window.location.assign(url) }) {
    const R = window.React, P = window.Plenix, h = R.createElement;
    const t = key => words[lang === "ar" ? "ar" : "en"][key];
    const [, refresh] = R.useReducer(n => n + 1, 0);
    const [accepted, setAccepted] = R.useState(false), [name, setName] = R.useState("");
    const session = R.useMemo(() => createFilingSession(application, api,
      () => window.crypto.randomUUID(), refresh), [application, api]);
    const actions = availability(application), state = session.state;
    R.useEffect(() => { onBusyChange?.(state.busy); return () => onBusyChange?.(false); }, [state.busy, onBusyChange]);
    R.useEffect(() => { onLockChange?.(state.attempted); return () => onLockChange?.(false); }, [state.attempted, onLockChange]);
    R.useEffect(() => { if (!reviewed) { setAccepted(false); setName(""); } }, [application, reviewed]);
    const blocked = dirty || !reviewed || state.busy || state.locked || state.submitted;
    const attestation = { accepted, name };
    const button = (key, action, extra = false) => h(P.Button, {
      disabled: blocked || extra, onClick: action,
    }, t(state.busy ? "busy" : key));
    const fee = application.fee;
    const amount = Number.isInteger(fee?.amount_minor) && fee.amount_minor >= 0 && fee.currency === "USD"
      ? new Intl.NumberFormat(lang === "ar" ? "ar" : "en", {style:"currency", currency:"USD"}).format(fee.amount_minor / 100) : null;
    return h(P.Panel, { title: t("title") }, h(P.Stack, null,
      h(P.Text, null, `${t("fee")}: ${amount || "—"} · ${t(["due","paid","waived","historical_exempt"].includes(fee?.status) ? fee.status : "unknown")}`),
      h(P.Text, {variant:"secondary"}, t("notRefundable")),
      application.status === "returned" ? h(P.Notice, null, t("returnNotice")) : null,
      typeof application.return_instructions === "string" && application.return_instructions.trim()
        ? h(P.Panel, {title:t("returned")}, h(P.Text, null, application.return_instructions)) : null,
      state.error ? h(P.Notice, {tone:"danger", role:"alert"}, t(state.error)) : null,
      state.submitted ? h(P.Notice, {tone:"success", role:"status"}, t("received")) : null,
      state.attempted ? h(P.Notice, {tone:"warning"}, t("frozen")) : null,
      (state.error || state.submitted) && onRefresh ? h(P.Button, {disabled:state.busy, onClick:onRefresh}, t("reload")) : null,
      dirty || !reviewed ? h(P.Notice, null, t("saveFirst")) : null,
      !actions.checkout && !actions.submit && !actions.resubmit ? h(P.Notice, null, t("unavailable")) : null,
      application.status === "draft" && actions.declaration && (actions.checkout || actions.submit)
        ? h(P.Stack, null,
          h(P.Panel, {title:t("declaration")}, h(P.Text, null, application.questionnaire[lang === "ar" ? "declaration_ar" : "declaration_en"])),
          h(P.Checkbox, {label:t("accept"), checked:accepted, disabled:blocked || state.attempted, onChange:e => setAccepted(e.target.checked)}),
          h(P.Field, {label:t("name"), required:true}, h(P.Input, {value:name, disabled:blocked || state.attempted, onChange:e => setName(e.target.value)}))) : null,
      h(P.Inline, {wrap:true},
        actions.checkout ? button("checkout", async () => {
          const url = await session.checkout(attestation); if (url) onCheckout(url);
        }, !validAttestation(attestation)) : null,
        actions.submit || actions.resubmit ? button(actions.resubmit ? "resubmit" : "submit",
          () => session.submit(attestation), !actions.resubmit && !validAttestation(attestation)) : null,
      )));
  }
  window.CTMApplicantFiling = { availability, createFilingSession, FilingActions };
})();
