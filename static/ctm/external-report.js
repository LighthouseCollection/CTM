/* External priest report page (council C-05).
   Contract (backend #7 tribunal/api.py external_report, services/reports.py external_request/complete_external):
     GET  /external/reports/{id}/  Authorization: Bearer <token>
          -> {id,title,case_number,subject,instructions,language,draft}
     POST same {action:"save", answers}  -> {saved:true}          (server-side draft)
     POST same {answers}                 -> 201 {submitted:true, report_id}
     Any failure (expired, wrong, cancelled, reissued, completed, closed) -> 403 {error:"link_unavailable"}.
   The token arrives in the URL fragment (#r=<request>&t=<token>), is removed from the address bar at once and
   kept only in memory. Nothing is written to browser storage; no cookies are sent. */
(() => {
  const words = {
    en: {
      pageTitle: "Report request",
      loading: "Loading the request…",
      language: "العربية",
      requestFor: "Request",
      caseNumber: "Case number",
      regarding: "Regarding",
      instructions: "Instructions from the tribunal",
      requestedLanguage: "Requested language",
      lang_en: "English",
      lang_ar: "Arabic",
      lang_both: "English or Arabic",
      testimony: "Your written report",
      testimonyHelp: "Write freely in English or Arabic about what you know of the marriage. You can save a draft and return with the same link until it expires.",
      saveDraft: "Save draft",
      submit: "Submit report",
      draftSaved: "Draft saved on the tribunal's server.",
      submitTitle: "Submit your report?",
      submitMessage: "After submitting, the report can no longer be changed through this link, and the link stops working.",
      cancel: "Keep writing",
      empty: "Write your report before submitting.",
      thanks: "Thank you. Your report was received by the tribunal.",
      thanksDetail: "This link no longer works. You may close this page.",
      unavailable: "This link is not active.",
      unavailableDetail:
        "It may have expired (links last 30 days), been replaced by a newer link, been cancelled, or the report may already have been submitted. Please contact the tribunal office for a new link.",
      malformed: "This link is incomplete. Please open the full link you received, or contact the tribunal office.",
      uncertain:
        "The tribunal's server did not confirm your submission. Your text is still here. Try again; if this link has stopped working, your report may already have been received — please contact the office before writing it again.",
      closedAfterSubmit:
        "This link stopped working while submitting. Your report may already have been received. Your text is still shown so you can copy it; please contact the tribunal office.",
      closedWhileSaving: "This link is no longer active, so the draft was not saved. Your text is still shown so you can copy it.",
      failed: "Something went wrong. Your text is kept; please try again.",
      unsaved: "Your report has not been saved.",
      otherFormats: "To send a recording or a signed paper response instead, please contact the tribunal office.",
      retry: "Try again",
    },
    ar: {
      pageTitle: "طلب تقرير",
      loading: "جارٍ تحميل الطلب…",
      language: "English",
      requestFor: "الطلب",
      caseNumber: "رقم القضية",
      regarding: "بخصوص",
      instructions: "تعليمات المحكمة",
      requestedLanguage: "اللغة المطلوبة",
      lang_en: "الإنجليزية",
      lang_ar: "العربية",
      lang_both: "الإنجليزية أو العربية",
      testimony: "تقريرك المكتوب",
      testimonyHelp: "اكتب بحرية بالعربية أو الإنجليزية عمّا تعرفه عن الزواج. ويمكنك حفظ مسودة والعودة بالرابط نفسه حتى تنتهي صلاحيته.",
      saveDraft: "حفظ المسودة",
      submit: "تقديم التقرير",
      draftSaved: "حُفظت المسودة على خادم المحكمة.",
      submitTitle: "هل تريد تقديم تقريرك؟",
      submitMessage: "بعد التقديم لا يمكن تغيير التقرير عبر هذا الرابط، ويتوقف الرابط عن العمل.",
      cancel: "متابعة الكتابة",
      empty: "اكتب تقريرك قبل التقديم.",
      thanks: "شكرًا لك. استلمت المحكمة تقريرك.",
      thanksDetail: "لم يعد هذا الرابط يعمل. يمكنك إغلاق هذه الصفحة.",
      unavailable: "هذا الرابط غير نشط.",
      unavailableDetail:
        "ربما انتهت صلاحيته (تدوم الروابط 30 يومًا)، أو استُبدل برابط أحدث، أو أُلغي، أو ربما قُدّم التقرير بالفعل. يرجى التواصل مع مكتب المحكمة للحصول على رابط جديد.",
      malformed: "هذا الرابط ناقص. يرجى فتح الرابط الكامل الذي وصلك، أو التواصل مع مكتب المحكمة.",
      uncertain:
        "لم يؤكد خادم المحكمة تقديمك. وما زال نصك هنا. حاول مجددًا؛ وإذا توقف هذا الرابط عن العمل فربما استُلم تقريرك بالفعل — يرجى التواصل مع المكتب قبل كتابته من جديد.",
      closedAfterSubmit:
        "توقف هذا الرابط عن العمل أثناء التقديم. وربما استُلم تقريرك بالفعل. وما زال نصك معروضًا لتتمكن من نسخه؛ يرجى التواصل مع مكتب المحكمة.",
      closedWhileSaving: "لم يعد هذا الرابط نشطًا، لذا لم تُحفظ المسودة. وما زال نصك معروضًا لتتمكن من نسخه.",
      failed: "حدث خطأ. نصك محفوظ هنا؛ يرجى المحاولة مجددًا.",
      unsaved: "لم يُحفظ تقريرك.",
      otherFormats: "لإرسال تسجيل صوتي أو رد ورقي موقَّع بدلًا من ذلك، يرجى التواصل مع مكتب المحكمة.",
      retry: "إعادة المحاولة",
    },
  };
  // Unicode first-strong isolate: names and titles keep their own direction inside the other language.
  const isolate = (value) => (value ? `\u2068${value}\u2069` : "");
  const translator = (lang) => (key) => (words[lang] || words.en)[key] ?? words.en[key] ?? key;

  // "#r=<request>&t=<token>" -> { requestId, token } (null when incomplete).
  function parseFragment(hash) {
    const params = new URLSearchParams(String(hash || "").replace(/^#/, ""));
    const requestId = params.get("r");
    const token = params.get("t");
    return requestId && token && /^[A-Za-z0-9-]{1,64}$/.test(requestId) ? { requestId, token } : null;
  }

  // Outcome of a request by status: the server deliberately collapses every link failure into 403.
  function outcome(error) {
    const status = error && error.status;
    if (!status || status >= 500) return "uncertain";
    if (status === 403 || status === 404 || status === 410) return "unavailable";
    return "failed";
  }

  function client(requestId, token, fetchImpl) {
    const url = `/external/reports/${encodeURIComponent(requestId)}/`;
    return async (method, body) => {
      let response;
      try {
        response = await fetchImpl(url, {
          method,
          credentials: "omit",
          cache: "no-store",
          referrerPolicy: "no-referrer",
          headers: { Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
          body: body ? JSON.stringify(body) : undefined,
        });
      } catch (cause) {
        throw Object.assign(new Error("network"), { status: 0, cause });
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw Object.assign(new Error(`HTTP ${response.status}`), { status: response.status, data });
      return data;
    };
  }

  function ExternalReportPage({ link, fetchImpl, initialLang }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement;
    const [lang, setLang] = R.useState(initialLang || "en");
    const t = translator(lang);
    const call = R.useMemo(() => (link ? client(link.requestId, link.token, fetchImpl) : null), [link]);
    const [state, setState] = R.useState(link ? "loading" : "malformed");
    const [request, setRequest] = R.useState(null);
    const [text, setText] = R.useState("");
    const [savedText, setSavedText] = R.useState("");
    const [pending, setPending] = R.useState(null); // "save" | "submit"
    const [message, setMessage] = R.useState(null); // { tone, key }
    const [confirm, setConfirm] = R.useState(false);
    const dirty = state === "ready" && text !== savedText;

    R.useEffect(() => {
      document.documentElement.lang = lang;
      document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
      document.title = t("pageTitle");
    }, [lang]);
    R.useEffect(() => {
      if (!dirty) return undefined;
      const guard = (event) => {
        event.preventDefault();
        event.returnValue = t("unsaved");
        return event.returnValue;
      };
      window.addEventListener("beforeunload", guard);
      return () => window.removeEventListener("beforeunload", guard);
    }, [dirty]);
    async function load() {
      setState("loading");
      setMessage(null);
      try {
        const data = await call("GET");
        setRequest(data);
        const draft = data.draft && typeof data.draft.testimony === "string" ? data.draft.testimony : "";
        setText(draft);
        setSavedText(draft);
        if (!initialLang && data.language === "ar") setLang("ar");
        setState("ready");
      } catch (error) {
        setState(outcome(error) === "unavailable" ? "unavailable" : "loadFailed");
      }
    }
    R.useEffect(() => {
      if (call) load();
    }, [call]);

    async function save() {
      setPending("save");
      setMessage(null);
      try {
        await call("POST", { action: "save", answers: { testimony: text } });
        setSavedText(text);
        setMessage({ tone: "success", key: "draftSaved" });
      } catch (error) {
        const kind = outcome(error);
        setMessage({ tone: "danger", key: kind === "unavailable" ? "closedWhileSaving" : kind === "uncertain" ? "failed" : "failed" });
      } finally {
        setPending(null);
      }
    }
    async function submit() {
      setConfirm(false);
      if (!text.trim()) return setMessage({ tone: "danger", key: "empty" });
      setPending("submit");
      setMessage(null);
      try {
        await call("POST", { answers: { testimony: text } });
        setSavedText(text);
        setState("submitted");
      } catch (error) {
        const kind = outcome(error);
        setMessage({ tone: "danger", key: kind === "unavailable" ? "closedAfterSubmit" : kind === "uncertain" ? "uncertain" : "failed" });
      } finally {
        setPending(null);
      }
      return undefined;
    }

    const header = h(
      P.Inline,
      { wrap: true, justify: "between" },
      h(P.Text, { as: "h1", variant: "heading" }, t("pageTitle")),
      h(P.Button, { size: "sm", onClick: () => setLang(lang === "ar" ? "en" : "ar") }, t("language")),
    );
    let body;
    if (state === "loading") body = h(P.Inline, { gap: "sm" }, h(P.Spinner, { size: "sm", label: t("loading") }), h(P.Text, null, t("loading")));
    else if (state === "malformed") body = h(P.Notice, { tone: "warning" }, t("malformed"));
    else if (state === "unavailable")
      body = h(P.Notice, { tone: "warning" }, h(P.Stack, { gap: "xs" }, h(P.Text, { variant: "strong" }, t("unavailable")), h(P.Text, null, t("unavailableDetail"))));
    else if (state === "loadFailed")
      body = h(P.Stack, { gap: "sm" }, h(P.Notice, { tone: "danger" }, t("failed")), h(P.Inline, null, h(P.Button, { onClick: load }, t("retry"))));
    else if (state === "submitted")
      body = h(P.Notice, { tone: "success" }, h(P.Stack, { gap: "xs" }, h(P.Text, { variant: "strong" }, t("thanks")), h(P.Text, null, t("thanksDetail"))));
    else
      body = h(
        P.Stack,
        { gap: "md" },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("requestFor") }, isolate(request.title)),
          h(P.PropertyList.Item, { label: t("caseNumber"), data: true, kind: "id" }, request.case_number),
          request.subject ? h(P.PropertyList.Item, { label: t("regarding") }, isolate(request.subject)) : null,
          h(P.PropertyList.Item, { label: t("requestedLanguage") }, t(`lang_${request.language}`)),
        ),
        request.instructions ? h(P.Panel, { icon: "doc-text", title: t("instructions") }, h(P.Text, { as: "p", dir: "auto" }, request.instructions)) : null,
        h(
          P.Form,
          { label: t("testimony"), noValidate: true, onSubmit: (e) => { e.preventDefault(); setConfirm(true); } },
          h(
            P.Field,
            { label: t("testimony"), description: t("testimonyHelp") },
            h(P.Textarea, { dir: "auto", rows: 12, autoGrow: true, maxLength: 100000, value: text, disabled: Boolean(pending), onChange: (e) => { setText(e.target.value); setMessage(null); } }),
          ),
          message ? h(P.Notice, { tone: message.tone }, t(message.key)) : null,
          h(
            P.FormActions,
            { sticky: false },
            h(P.Button, { disabled: Boolean(pending) || !dirty, loading: pending === "save", onClick: save }, t("saveDraft")),
            h(P.Button, { type: "submit", variant: "primary", disabled: Boolean(pending), loading: pending === "submit" }, t("submit")),
          ),
        ),
        h(P.Text, { variant: "secondary" }, t("otherFormats")),
        h(P.ConfirmDialog, {
          open: confirm,
          title: t("submitTitle"),
          message: t("submitMessage"),
          confirmLabel: t("submit"),
          cancelLabel: t("cancel"),
          onConfirm: submit,
          onCancel: () => setConfirm(false),
        }),
      );
    return h(P.Center, { maxWidth: "md" }, h(P.Stack, { gap: "lg", inset: "md" }, header, body));
  }

  const api = { words, parseFragment, outcome, client, ExternalReportPage };
  window.CTMExternalReport = api;

  // Boot only on the real page (tests load this file without a root element).
  const root = typeof document !== "undefined" && document.getElementById && document.getElementById("external-report-root");
  if (root && window.ReactDOM) {
    const link = parseFragment(window.location.hash);
    // Drop the token from the address bar and history; it stays in memory for this page only.
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname + window.location.search);
    // Opening another link in the same tab only changes the fragment; start that link fresh.
    window.addEventListener("hashchange", () => window.location.reload());
    const initialLang = (navigator.language || "").toLowerCase().startsWith("ar") ? "ar" : null;
    window.ReactDOM.createRoot(root).render(
      window.React.createElement(ExternalReportPage, { link, fetchImpl: window.fetch.bind(window), initialLang }),
    );
  }
})();
