/* CTM uses documented Plenix 0.58.0 CDN exports. No component assets are bundled. */
(() => {
  "use strict";
  const root = document.getElementById("ctm-root");
  if (!window.React || !window.ReactDOM || !window.Plenix) {
    root.textContent =
      "CTM could not load. Please check your connection and reload. تعذر تحميل النظام. يرجى التحقق من الاتصال وإعادة المحاولة.";
    return;
  }
  const R = window.React,
    P = window.Plenix,
    h = R.createElement;
  const config = JSON.parse(document.getElementById("ctm-config").textContent);
  const words = {
    en: {
      tribunal: "Church Tribunal",
      signIn: "Sign in to CTM",
      welcome: "Access your application or council workspace securely.",
      microsoft: "Continue with Microsoft",
      google: "Continue with Google",
      apple: "Continue with Apple",
      councilLogin: "Council members use their authorized Microsoft account.",
      noProviders:
        "Sign-in is temporarily unavailable. Please contact the tribunal.",
      language: "العربية",
      home: "Home",
      cases: "Cases",
      sessions: "Tribunal Sessions",
      archived: "Archived",
      search: "Q Search",
      statistics: "Statistics and Reports",
      applications: "My application",
      past: "Past cases",
      loading: "Loading…",
      retry: "Try again",
      error: "Unable to load this information",
      expired: "Please sign in again to continue.",
      empty: "Nothing to show",
      noCases: "No cases are available.",
      noFiles: "No technically cleared files are available in this section.",
      chooseFile: "Select a file to preview",
      download: "Download",
      version: "Version",
      olderVersions: "Include older versions",
      more: "Load more",
      previous: "Previous",
      next: "Next",
      preview: "Preview",
      closePreview: "Close preview",
      rate: "Playback speed",
      transcript: "Transcript",
      hideTranscript: "Hide transcript",
      pip: "Picture in picture",
      exitPip: "Exit picture in picture",
      unsupported: "This media format is not supported.",
      mediaFailed: "Unable to play this recording.",
      pipFailed: "Picture in picture is unavailable.",
      seek: "Seek",
      fallback: "Open media",
      audioFailed: "Unable to load audio.",
      volume: "Volume",
      mute: "Mute",
      counter: "{index} of {total}",
      downloadOnly:
        "Download this document to open it in a compatible application.",
      noSessions: "No council sessions are scheduled.",
      current: "Your current application or case",
      noCurrent: "You have no current application or open case.",
      fee: "The filing fee is USD 250. Drafts can be saved before payment.",
      open: "Open",
      closed: "Closed",
      draft: "Draft",
      submitted: "Submitted",
      accepted: "Accepted",
      returned: "Returned for correction",
      withdrawn: "Withdrawn",
      declined: "Declined",
      petition: "Petition",
      appeal: "Appeal",
      paid: "Paid",
      due: "Payment due",
      waived: "Fee waived",
      reference: "Case number",
      assigned: "Assigned case manager",
      unassigned: "Not yet assigned",
      summary: "Summary",
      overview: "Case Overview",
      communications: "Communications",
      assessment: "Case Review",
      decision: "Decision",
      timeline: "Timeline",
      parties: "Parties",
      marriage: "Marriage",
      separation: "Separation",
      reports: "Reports",
      hearings: "Hearings",
      evidence: "Evidence",
      documents: "Documents",
      medical: "Medical & Psychological Reports",
      decree: "Decree",
      appeals: "Appeals",
      audit: "Case Audit",
      backCases: "Back to cases",
      backSessions: "Back to sessions",
      account: "My Profile",
      settings: "Account Settings",
      system: "CTM Settings",
      unavailable: "This view is not available yet.",
      signOut: "Sign out",
      agenda: "Agenda",
      assignment: "New case assignments",
      hearing: "Case hearings",
      scheduled: "Scheduled",
      heard: "Heard",
      presenter_absent: "Presenter absent — awaiting manual placement",
      unpresented: "Not presented",
      planned: "Planned",
      status: "Status",
      members: "Parties",
      view: "Open",
      profile: "Profile",
      council: "Council portal",
      applicant: "Applicant portal",
      skip: "Skip to main content",
      answers: "Your answers",
      payment: "Payment",
      version: "Version",
      unknown: "Unknown",
      notificationLanguage: "Email and notification language",
      interfaceLanguage: "Interface language",
      english: "English",
      arabic: "العربية",
      newMessage: "New message",
      message: "Message",
      recipients: "Recipients",
      send: "Send",
      immediate: "Send Immediately",
      afterSession: "Send after council session",
      chooseSession: "Select a council session",
      sent: "Message sent",
      sendFailed: "The message could not be sent. Your text has been kept.",
      noMessages: "No messages yet",
    },
    ar: {
      noFiles: "لا توجد ملفات اجتازت الفحص في هذا القسم.",
      chooseFile: "اختر ملفًا لعرضه",
      download: "تنزيل",
      version: "الإصدار",
      olderVersions: "تضمين الإصدارات السابقة",
      more: "تحميل المزيد",
      previous: "السابق",
      next: "التالي",
      preview: "معاينة",
      closePreview: "إغلاق المعاينة",
      rate: "سرعة التشغيل",
      transcript: "النص المكتوب",
      hideTranscript: "إخفاء النص",
      pip: "صورة داخل صورة",
      exitPip: "إغلاق صورة داخل صورة",
      unsupported: "صيغة الوسائط غير مدعومة.",
      mediaFailed: "تعذر تشغيل التسجيل.",
      pipFailed: "ميزة صورة داخل صورة غير متاحة.",
      seek: "الانتقال",
      fallback: "فتح الوسائط",
      audioFailed: "تعذر تحميل الصوت.",
      volume: "مستوى الصوت",
      mute: "كتم الصوت",
      counter: "{index} من {total}",
      downloadOnly: "نزّل هذا المستند لفتحه باستخدام تطبيق مناسب.",
      tribunal: "المجلس الإكليريكي",
      signIn: "تسجيل الدخول",
      welcome: "ادخل بأمان لمتابعة طلبك أو للوصول إلى مساحة عمل المجلس.",
      microsoft: "المتابعة باستخدام Microsoft",
      google: "المتابعة باستخدام Google",
      apple: "المتابعة باستخدام Apple",
      councilLogin: "يستخدم أعضاء المجلس حساب Microsoft المعتمد لهم.",
      noProviders: "تسجيل الدخول غير متاح مؤقتًا. يرجى التواصل مع المجلس.",
      language: "English",
      home: "الرئيسية",
      cases: "القضايا",
      sessions: "جلسات المجلس",
      archived: "الأرشيف",
      search: "البحث",
      statistics: "الإحصاءات والتقارير",
      applications: "طلبي",
      past: "القضايا السابقة",
      loading: "جارٍ التحميل…",
      retry: "إعادة المحاولة",
      error: "تعذر تحميل هذه المعلومات",
      expired: "يرجى تسجيل الدخول مرة أخرى للمتابعة.",
      empty: "لا توجد بيانات للعرض",
      noCases: "لا توجد قضايا متاحة.",
      noSessions: "لا توجد جلسات مجلس محددة.",
      current: "طلبك أو قضيتك الحالية",
      noCurrent: "ليس لديك طلب حالي أو قضية مفتوحة.",
      fee: "رسوم تقديم الطلب ٢٥٠ دولارًا أمريكيًا. يمكنك حفظ المسودة قبل السداد.",
      open: "مفتوحة",
      closed: "مغلقة",
      draft: "مسودة",
      submitted: "تم التقديم",
      accepted: "مقبول",
      returned: "أُعيد للتصحيح",
      withdrawn: "تم سحبه",
      declined: "مرفوض",
      petition: "طلب",
      appeal: "التماس إعادة نظر",
      paid: "تم السداد",
      due: "الرسوم مستحقة",
      waived: "تم الإعفاء من الرسوم",
      reference: "رقم القضية",
      assigned: "مسؤول القضية",
      unassigned: "لم يُعيّن بعد",
      summary: "الملخص",
      overview: "نظرة عامة على القضية",
      communications: "المراسلات",
      assessment: "دراسة القضية",
      decision: "القرار",
      timeline: "التسلسل الزمني",
      parties: "أطراف القضية",
      marriage: "الزواج",
      separation: "الانفصال",
      reports: "التقارير",
      hearings: "مناقشات القضية",
      evidence: "الأدلة",
      documents: "المستندات",
      medical: "التقارير الطبية والنفسية",
      decree: "الشهادة",
      appeals: "التماسات إعادة النظر",
      audit: "سجل القضية",
      backCases: "العودة إلى القضايا",
      backSessions: "العودة إلى الجلسات",
      account: "ملفي الشخصي",
      settings: "إعدادات الحساب",
      system: "إعدادات النظام",
      unavailable: "هذا القسم غير متاح حاليًا.",
      signOut: "تسجيل الخروج",
      agenda: "جدول الأعمال",
      assignment: "إسناد القضايا الجديدة",
      hearing: "مناقشة القضايا",
      scheduled: "مدرجة بالجدول",
      heard: "تمت المناقشة",
      presenter_absent: "مسؤول القضية غائب — بانتظار إدراجها يدويًا",
      unpresented: "لم تُناقش",
      planned: "محددة",
      status: "الحالة",
      members: "أطراف القضية",
      view: "فتح",
      profile: "الملف الشخصي",
      council: "بوابة المجلس",
      applicant: "بوابة مقدم الطلب",
      skip: "الانتقال إلى المحتوى الرئيسي",
      answers: "إجاباتك",
      payment: "الرسوم",
      version: "الإصدار",
      unknown: "غير معروف",
      notificationLanguage: "لغة البريد الإلكتروني والإشعارات",
      interfaceLanguage: "لغة الواجهة",
      english: "English",
      arabic: "العربية",
      newMessage: "رسالة جديدة",
      message: "الرسالة",
      recipients: "المستلمون",
      send: "إرسال",
      immediate: "إرسال فورًا",
      afterSession: "إرسال بعد جلسة المجلس",
      chooseSession: "اختر جلسة المجلس",
      sent: "تم إرسال الرسالة",
      sendFailed: "تعذر إرسال الرسالة. تم الاحتفاظ بالنص.",
      noMessages: "لا توجد رسائل بعد",
    },
  };
  function csrf() {
    return decodeURIComponent(
      document.cookie
        .split("; ")
        .find((v) => v.startsWith("csrftoken="))
        ?.slice(10) || "",
    );
  }
  function postForm(url) {
    const form = document.createElement("form");
    form.method = "post";
    form.action = url;
    const token = document.createElement("input");
    token.type = "hidden";
    token.name = "csrfmiddlewaretoken";
    token.value = csrf();
    form.appendChild(token);
    document.body.appendChild(form);
    form.submit();
  }
  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
      },
      cache: "no-store",
    });
    if (response.status === 401) {
      const error = new Error("unauthorized");
      error.status = 401;
      throw error;
    }
    if (!response.ok) throw new Error("request_failed");
    return response.json();
  }
  function MessageComposer({ record, sessions, council, t, onSent }) {
    const [body, setBody] = R.useState(""),
      [recipients, setRecipients] = R.useState([]);
    const [timing, setTiming] = R.useState("immediate"),
      [session, setSession] = R.useState("");
    const [pending, setPending] = R.useState(false),
      [status, setStatus] = R.useState(null);
    const ids = council
      ? recipients
      : record.parties.filter((p) => p.is_self).map((p) => p.id);
    async function submit(event) {
      event.preventDefault();
      setPending(true);
      setStatus(null);
      try {
        await api(`/api/cases/${record.id}/messages/`, {
          method: "POST",
          body: JSON.stringify({
            body,
            party_ids: ids,
            email_timing: timing,
            session_id: session || null,
          }),
        });
        setBody("");
        setStatus("sent");
        onSent();
      } catch {
        setStatus("sendFailed");
      } finally {
        setPending(false);
      }
    }
    return h(
      P.Panel,
      { title: t("newMessage") },
      h(
        P.Stack,
        { as: "form", onSubmit: submit },
        council
          ? h(
              P.Stack,
              { gap: "sm" },
              h(P.Text, { variant: "label" }, t("recipients")),
              ...record.parties
                .filter((p) => p.can_receive)
                .map((p) =>
                  h(P.Checkbox, {
                    key: p.id,
                    label: p.name,
                    checked: recipients.includes(p.id),
                    disabled: pending,
                    onChange: (event) =>
                      setRecipients((old) =>
                        event.target.checked
                          ? [...old, p.id]
                          : old.filter((id) => id !== p.id),
                      ),
                  }),
                ),
            )
          : null,
        h(P.Textarea, {
          "aria-label": t("message"),
          value: body,
          rows: 5,
          maxLength: 100000,
          required: true,
          disabled: pending,
          onChange: (event) => setBody(event.target.value),
        }),
        council
          ? h(P.RadioGroup, {
              label: t("send"),
              value: timing,
              onChange: setTiming,
              options: [
                { value: "immediate", label: t("immediate") },
                { value: "after_session", label: t("afterSession") },
              ],
            })
          : null,
        timing === "after_session"
          ? h(P.Select, {
              "aria-label": t("chooseSession"),
              value: session,
              onChange: (event) => setSession(event.target.value),
              options: [
                { value: "", label: t("chooseSession") },
                ...sessions
                  .filter((s) => s.state === "planned")
                  .map((s) => ({ value: s.id, label: s.date })),
              ],
            })
          : null,
        status
          ? h(
              P.Notice,
              { tone: status === "sent" ? "success" : "danger" },
              t(status),
            )
          : null,
        h(
          P.Button,
          {
            type: "submit",
            variant: "primary",
            loading: pending,
            disabled:
              pending ||
              !body.trim() ||
              !ids.length ||
              (timing === "after_session" && !session),
          },
          t("send"),
        ),
      ),
    );
  }
  const text = (value, props = {}) => h(P.Text, { as: "p", ...props }, value);
  const heading = (value) => text(value, { as: "h1", variant: "title" });
  function CaseFiles({ caseId, section, council, t }) {
    const [rows, setRows] = R.useState([]),
      [selected, select] = R.useState(null);
    const [history, setHistory] = R.useState(false),
      [next, setNext] = R.useState(null);
    const [pending, setPending] = R.useState(true),
      [failed, setFailed] = R.useState(false);
    const [revision, refresh] = R.useState(0);
    const generation = R.useRef(0);
    R.useEffect(() => {
      let active = true;
      generation.current += 1;
      setRows([]);
      setNext(null);
      select(null);
      setPending(true);
      setFailed(false);
      api(`/api/cases/${caseId}/files/?history=${history ? 1 : 0}`)
        .then((data) => {
          if (active) {
            setRows(data.items);
            setNext(data.next_offset);
          }
        })
        .catch(() => {
          if (active) setFailed(true);
        })
        .finally(() => {
          if (active) setPending(false);
        });
      return () => {
        active = false;
        generation.current += 1;
      };
    }, [caseId, history, revision]);
    async function more() {
      if (pending || next === null) return;
      const requestedGeneration = generation.current;
      setPending(true);
      setFailed(false);
      try {
        const data = await api(
          `/api/cases/${caseId}/files/?history=${history ? 1 : 0}&offset=${next}`,
        );
        if (requestedGeneration !== generation.current) return;
        setRows((old) => [
          ...old,
          ...data.items.filter((row) => !old.some((x) => x.id === row.id)),
        ]);
        setNext(data.next_offset);
      } catch {
        if (requestedGeneration === generation.current) setFailed(true);
      } finally {
        if (requestedGeneration === generation.current) setPending(false);
      }
    }
    // File purpose determines its section; MIME only chooses its viewer.
    const applicationDocumentCodes = new Set([
      "PHOTO",
      "SPOUSE_PHOTO",
      "MC",
      "CMC",
      "CDD",
      "RO",
      "PET",
    ]);
    const visible = rows.filter((row) =>
      section === "documents"
        ? applicationDocumentCodes.has(row.category)
        : !applicationDocumentCodes.has(row.category),
    );
    const chosen = visible.find((row) => row.id === selected);
    const list = h(
      P.Stack,
      null,
      council
        ? h(P.Checkbox, {
            label: t("olderVersions"),
            checked: history,
            onChange: (event) => setHistory(event.target.checked),
          })
        : null,
      ...visible.map((row) =>
        h(P.Card, {
          key: row.id,
          title: row.name,
          meta: `${row.category} · ${t("version")} ${row.version}`,
          onOpen: () => select(row.id),
        }),
      ),
      !visible.length && !pending
        ? h(P.EmptyState, { title: t("noFiles") })
        : null,
      pending ? text(t("loading")) : null,
      failed
        ? h(
            P.Notice,
            { tone: "danger" },
            t("error"),
            h(P.Button, { onClick: () => refresh((n) => n + 1) }, t("retry")),
          )
        : null,
      next !== null
        ? h(P.Button, { onClick: more, disabled: pending }, t("more"))
        : null,
    );
    const preview = !chosen
      ? h(P.EmptyState, { title: t("chooseFile") })
      : h(
          P.Stack,
          null,
          text(chosen.name),
          h(
            P.Button,
            { onClick: () => window.location.assign(chosen.download_url) },
            t("download"),
          ),
          chosen.preview_url && chosen.mime_type.startsWith("image/")
            ? h(P.DocumentViewer, {
                key: chosen.id,
                kind: "images",
                pages: [
                  { id: chosen.id, src: chosen.preview_url, alt: chosen.name },
                ],
                label: chosen.name,
                strings: {
                  previous: t("previous"),
                  next: t("next"),
                  loading: t("loading"),
                  failed: t("error"),
                  empty: t("empty"),
                  retry: t("retry"),
                },
              })
            : chosen.preview_url && /^(audio|video)\//.test(chosen.mime_type)
              ? h(P.MediaPlayer, {
                  key: chosen.id,
                  src: chosen.preview_url,
                  kind: chosen.mime_type.startsWith("audio/")
                    ? "audio"
                    : "video",
                  label: chosen.name,
                  strings: Object.fromEntries(
                    [
                      "rate",
                      "transcript",
                      "hideTranscript",
                      "pip",
                      "exitPip",
                      "unsupported",
                      "pipFailed",
                      "seek",
                      "fallback",
                      "audioFailed",
                      "volume",
                      "mute",
                    ]
                      .map((key) => [key, t(key)])
                      .concat([["failed", t("mediaFailed")]]),
                  ),
                })
              : chosen.preview_url
                ? h(
                    P.Button,
                    {
                      onClick: () =>
                        window.open(
                          chosen.preview_url,
                          "_blank",
                          "noopener,noreferrer",
                        ),
                    },
                    t("preview"),
                  )
                : text(t("downloadOnly")),
        );
    return h(
      P.Stack,
      null,
      heading(t(section)),
      h(P.SplitView, {
        label: t(section),
        firstLabel: t(section),
        first: list,
        second: h(
          P.ReadingPane,
          { label: chosen?.name || t("preview") },
          preview,
        ),
      }),
    );
  }
  function App() {
    const [lang, setLang] = R.useState(() => {
      try {
        return localStorage.getItem("ctm-language") === "ar" ? "ar" : "en";
      } catch {
        return "en";
      }
    });
    const [user, setUser] = R.useState(undefined),
      [page, setPage] = R.useState("home");
    const [selection, setSelection] = R.useState(null),
      [data, setData] = R.useState(null);
    const [failure, setFailure] = R.useState(false),
      [revision, reload] = R.useState(0);
    const [saving, setSaving] = R.useState(false);
    const t = (key) => words[lang][key] || words[lang].unknown;
    R.useEffect(() => {
      document.documentElement.lang = lang;
      document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
      try {
        localStorage.setItem("ctm-language", lang);
      } catch {
        /* Storage is optional. */
      }
    }, [lang]);
    R.useEffect(() => {
      let active = true;
      api("/api/session/")
        .then((value) => {
          if (active) {
            setUser(value);
            setLang(value.ui_language === "ar" ? "ar" : "en");
          }
        })
        .catch((error) => {
          if (active) {
            if (error.status === 401) setUser(null);
            else setFailure(true);
          }
        });
      return () => {
        active = false;
      };
    }, [revision]);
    R.useEffect(() => {
      let active = true;
      setData(null);
      setFailure(false);
      if (!user)
        return () => {
          active = false;
        };
      let request;
      if (["documents", "evidence"].includes(page) && selection)
        request = Promise.resolve({});
      else if (page === "case" && selection)
        request = api(`/api/cases/${selection}/`);
      else if (page === "communications" && selection)
        request = Promise.all([
          api(`/api/cases/${selection}/`),
          api(`/api/cases/${selection}/messages/`),
          user.portal === "council"
            ? api("/api/sessions/")
            : Promise.resolve({ items: [] }),
        ]).then(([record, messages, sessions]) => ({
          record,
          messages: messages.items,
          sessions: sessions.items,
        }));
      else if (page === "session" && selection)
        request = api(`/api/sessions/${selection}/agenda/`);
      else if (page === "sessions") request = api("/api/sessions/");
      else if (page === "applications") request = api("/api/applications/");
      else if (["home", "cases", "archived", "past"].includes(page)) {
        request =
          user.portal === "applicant" && page === "home"
            ? Promise.all([api("/api/cases/"), api("/api/applications/")]).then(
                ([cases, applications]) => ({
                  cases: cases.items,
                  applications: applications.items,
                }),
              )
            : api("/api/cases/");
      } else {
        setData({});
        return () => {
          active = false;
        };
      }
      request
        .then((value) => {
          if (active) setData(value);
        })
        .catch((error) => {
          if (active) {
            if (error.status === 401) setUser(null);
            else setFailure(true);
          }
        });
      return () => {
        active = false;
      };
    }, [user?.id, user?.portal, page, selection, revision]);
    const go = (id, selected = null) => {
      if (id === page && selected === selection) return;
      setData(null);
      setFailure(false);
      setPage(id);
      setSelection(selected);
    };
    const savePreference = async (field, value) => {
      if (!user) {
        setLang(value);
        return;
      }
      setSaving(true);
      try {
        const updated = await api("/api/account/settings/", {
          method: "POST",
          body: JSON.stringify({ [field]: value }),
        });
        setUser((previous) => ({ ...previous, ...updated }));
        if (field === "ui_language") setLang(value);
      } catch (error) {
        if (error.status === 401) setUser(null);
        else setFailure(true);
      } finally {
        setSaving(false);
      }
    };
    const language = h(
      P.Button,
      {
        variant: "ghost",
        disabled: saving,
        onClick: () =>
          savePreference("ui_language", lang === "en" ? "ar" : "en"),
      },
      t("language"),
    );
    const errorView = () =>
      h(P.EmptyState, {
        tone: "error",
        title: t("error"),
        action: h(
          P.Button,
          { onClick: () => reload((n) => n + 1) },
          t("retry"),
        ),
      });
    if (user === undefined)
      return h(
        P.Center,
        { vertical: true },
        failure ? errorView() : text(t("loading")),
      );
    if (user === null)
      return h(
        P.AppShell,
        { page: "form", strings: { skip: t("skip") } },
        h(
          P.PageContent,
          null,
          h(
            P.Center,
            { maxWidth: "sm", vertical: true },
            h(
              P.Stack,
              { gap: "lg", inset: "lg" },
              h(
                P.Inline,
                { justify: "between" },
                text("CTM", { variant: "eyebrow" }),
                language,
              ),
              text(t("signIn"), { as: "h1", variant: "display" }),
              text(t("welcome"), { variant: "lead" }),
              ...config.providers.map((name) =>
                h(
                  P.Button,
                  {
                    key: name,
                    variant: name === "microsoft" ? "primary" : "secondary",
                    onClick: () => postForm(`/accounts/${name}/login/`),
                  },
                  t(name),
                ),
              ),
              config.providers.length
                ? text(t("councilLogin"), { variant: "secondary" })
                : h(P.Notice, { tone: "warning" }, t("noProviders")),
            ),
          ),
        ),
      );
    const council = user.portal === "council";
    const navItems = council
      ? ["home", "sessions", "cases", "search", "archived", "statistics"]
      : ["home", "applications", "past"];
    const unavailable = new Set(["search", "statistics"]);
    const caseContext =
      ["case", "communications", "documents", "evidence"].includes(page) &&
      selection;
    const caseGroups = [
      {
        heading: t("overview"),
        items: ["case", "timeline", "parties", "marriage", "separation"].map(
          (id) => ({
            id,
            label: t(id === "case" ? "summary" : id),
            disabled: id !== "case",
          }),
        ),
      },
    ];
    const reviewGroups = [
      {
        heading: t("assessment"),
        items: [
          "petition",
          "reports",
          "hearings",
          "evidence",
          "documents",
          "medical",
        ].map((id) => ({
          id,
          label: t(id),
          disabled: !["documents", "evidence"].includes(id),
        })),
      },
      {
        heading: t("decision"),
        items: ["decree", "appeals"].map((id) => ({
          id,
          label: t(id),
          disabled: true,
        })),
      },
    ];
    const nav = caseContext
      ? h(
          P.NavPane,
          {
            title: t("overview"),
            label: t("overview"),
            header: h(
              P.Button,
              {
                variant: "ghost",
                onClick: () => go(council ? "cases" : "past"),
              },
              t("backCases"),
            ),
          },
          h(P.NavList, {
            label: t("overview"),
            value: page,
            onSelect: (id) => go(id, selection),
            groups: caseGroups,
          }),
          h(P.NavList, {
            label: t("communications"),
            value: page,
            onSelect: (id) => go(id, selection),
            items: [{ id: "communications", label: t("communications") }],
          }),
          council
            ? h(P.NavList, {
                label: t("assessment"),
                value: page,
                onSelect: (id) => go(id, selection),
                groups: reviewGroups,
              })
            : null,
        )
      : h(
          P.NavPane,
          { title: t(council ? "council" : "applicant"), label: t("tribunal") },
          h(P.NavList, {
            label: t("tribunal"),
            value: page,
            onSelect: (id) => go(id),
            items: navItems.map((id) => ({
              id,
              label: t(id),
              disabled: unavailable.has(id),
            })),
          }),
        );
    const account = h(
      P.Menu,
      {
        label: t("account"),
        placement: "bottom-end",
        trigger: h(
          P.Button,
          {
            variant: "ghost",
            caret: true,
            icon: h(P.Avatar, { name: user.name, size: "xs" }),
          },
          user.name,
        ),
      },
      h(P.MenuItem, { onSelect: () => go("profile") }, t("account")),
      h(P.MenuItem, { onSelect: () => go("settings") }, t("settings")),
      h(P.MenuDivider),
      h(
        P.MenuItem,
        { onSelect: () => postForm("/accounts/logout/") },
        t("signOut"),
      ),
    );
    const header = h(P.AppHeader, {
      appName: "CTM",
      brand: "CTM",
      switcher: false,
      nav: null,
      account,
      actions: language,
    });
    const caseCard = (row) =>
      h(
        P.Card,
        {
          key: row.id,
          title: row.number,
          meta: t(row.status),
          onOpen: () => go("case", row.id),
        },
        text(`${t("assigned")}: ${row.assigned_member || t("unassigned")}`, {
          variant: "secondary",
        }),
      );
    const caseList = (rows) =>
      rows.length
        ? h(P.Stack, null, ...rows.map(caseCard))
        : h(P.EmptyState, { title: t("noCases") });
    const applicationCard = (row) =>
      h(
        P.Panel,
        { key: row.id, title: t(row.kind), description: t(row.status) },
        h(
          P.Stack,
          null,
          text(`${t("payment")}: ${t(row.fee?.status || "unknown")}`),
          h(P.Notice, null, t("fee")),
        ),
      );
    function content() {
      if (failure) return errorView();
      if (!data) return text(t("loading"));
      if (["documents", "evidence"].includes(page))
        return h(CaseFiles, {
          key: `${selection}-${page}`,
          caseId: selection,
          section: page,
          council,
          t,
        });
      if (page === "profile")
        return h(
          P.Stack,
          null,
          heading(t("profile")),
          text(user.name),
          text(t(user.portal)),
        );
      if (page === "settings")
        return h(
          P.Stack,
          null,
          heading(t("settings")),
          h(P.Panel, { title: t("interfaceLanguage") }, language),
          h(
            P.Panel,
            { title: t("notificationLanguage") },
            h(
              P.Inline,
              null,
              h(
                P.Button,
                {
                  disabled: saving,
                  selected: user.notification_language === "en",
                  onClick: () => savePreference("notification_language", "en"),
                },
                t("english"),
              ),
              h(
                P.Button,
                {
                  disabled: saving,
                  selected: user.notification_language === "ar",
                  onClick: () => savePreference("notification_language", "ar"),
                },
                t("arabic"),
              ),
            ),
          ),
        );
      if (page === "communications")
        return h(
          P.Stack,
          { gap: "lg" },
          heading(t("communications")),
          ...data.messages.map((row) =>
            h(
              P.Panel,
              {
                key: row.id,
                title: row.sender,
                description: new Intl.DateTimeFormat(
                  lang === "ar" ? "ar-EG" : "en-US",
                  { dateStyle: "medium", timeStyle: "short" },
                ).format(new Date(row.timestamp)),
              },
              text(row.body),
            ),
          ),
          !data.messages.length
            ? h(P.EmptyState, { title: t("noMessages") })
            : null,
          data.record.can_message
            ? h(MessageComposer, {
                key: selection,
                record: data.record,
                sessions: data.sessions,
                council,
                t,
                onSent: () => reload((n) => n + 1),
              })
            : null,
        );
      if (page === "case")
        return h(
          P.Stack,
          { gap: "lg" },
          h(
            P.Button,
            { variant: "ghost", onClick: () => go(council ? "cases" : "past") },
            t("backCases"),
          ),
          heading(data.number),
          text(`${t("status")}: ${t(data.status)}`),
          h(
            P.Panel,
            { title: t("parties") },
            h(P.List, {
              variant: "bullets",
              items: data.parties.map((p) => ({ children: p.name })),
            }),
          ),
          h(
            P.Panel,
            { title: t("timeline") },
            h(P.List, {
              variant: "bullets",
              items: data.proceedings.map((p) => ({
                children: `${t(p.kind === "initial" ? "petition" : p.kind)} · ${t(p.status)}`,
              })),
            }),
          ),
        );
      if (page === "session")
        return h(
          P.Stack,
          null,
          h(
            P.Button,
            { variant: "ghost", onClick: () => go("sessions") },
            t("backSessions"),
          ),
          heading(t("agenda")),
          ...[1, 2].map((part) =>
            h(
              P.Panel,
              { key: part, title: t(part === 1 ? "assignment" : "hearing") },
              ...data.items
                .filter((row) => row.part === part)
                .map((row) =>
                  h(P.Card, {
                    key: row.id,
                    title: row.case_number,
                    meta: t(row.state),
                    onOpen: () => go("case", row.case_id),
                  }),
                ),
            ),
          ),
        );
      if (page === "sessions")
        return h(
          P.Stack,
          null,
          heading(t(page)),
          data.items.length
            ? data.items.map((row) =>
                h(P.Card, {
                  key: row.id,
                  title: `${t("sessions")} ${row.date}`,
                  meta: t(row.state),
                  onOpen: () => go("session", row.id),
                }),
              )
            : h(P.EmptyState, { title: t("noSessions") }),
        );
      if (page === "applications")
        return h(
          P.Stack,
          null,
          heading(t(page)),
          ...data.items.map(applicationCard),
        );
      if (page === "home" && !council) {
        const filing =
          data.applications.find(
            (row) =>
              row.kind === "appeal" &&
              ["draft", "submitted", "returned"].includes(row.status),
          ) ||
          data.applications.find((row) =>
            ["draft", "returned"].includes(row.status),
          );
        const currentCase = data.cases.find((row) => row.status === "open");
        return h(
          P.Stack,
          null,
          heading(t("home")),
          text(t("current")),
          filing
            ? applicationCard(filing)
            : currentCase
              ? caseCard(currentCase)
              : h(P.EmptyState, { title: t("noCurrent") }),
        );
      }
      if (["home", "cases", "archived", "past"].includes(page))
        return h(
          P.Stack,
          null,
          heading(t(page)),
          caseList(
            data.items.filter((row) =>
              ["archived", "past"].includes(page)
                ? row.status === "closed"
                : row.status === "open",
            ),
          ),
        );
      return h(P.EmptyState, { title: t("unavailable") });
    }
    return h(
      P.AppShell,
      { header, sideNav: nav, page: "workspace", strings: { skip: t("skip") } },
      h(P.PageContent, null, content()),
    );
  }
  window.ReactDOM.createRoot(root).render(h(P.ThemeProvider, null, h(App)));
})();
