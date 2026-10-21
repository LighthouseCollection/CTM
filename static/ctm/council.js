/* CTM council workspace module. Plenix stays on the pinned external CDN.
   The server enforces every permission; capability checks here only decide
   which controls to show and never stand in for authorization. */
(() => {
  "use strict";

  const ADMIN_ROLES = new Set(["admin", "secretary"]);
  const DATE = /^\d{4}-\d{2}-\d{2}$/;

  // ---------- Pure logic (unit tested in tests/frontend/council.test.cjs) ----------

  function canManage(user) {
    return Boolean(user && user.portal === "council" && ADMIN_ROLES.has(user.role));
  }

  function awaitingReview(items) {
    return (items || []).filter(
      (row) => row && row.kind === "petition" && row.status === "submitted",
    );
  }

  // Returning an application is not a denial; it always needs an explanation.
  function reviewProblem(result, instructions) {
    if (result !== "accept" && result !== "reject") return "reviewChoose";
    if (result === "reject" && !String(instructions || "").trim())
      return "returnRequired";
    return null;
  }

  function sessionLabel(date, t) {
    return `${t ? t("councilSession") : "Council Session"} ${date}`;
  }

  function sessionReference(date) {
    return DATE.test(date || "") ? `CS${date.replace(/-/g, "")}` : null;
  }

  function sessionDateProblem(value, existing) {
    if (!DATE.test(value || "")) return "dateRequired";
    const parsed = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value)
      return "dateRequired";
    if ((existing || []).some((row) => row.date === value)) return "dateTaken";
    return null;
  }

  // Formal hearing title from the contract. Missing names stay visibly unknown.
  function hearingTitle(partyNames, date, t) {
    const unknown = t ? t("unknownParty") : "Unknown party";
    const names = (partyNames || []).filter((n) => String(n || "").trim());
    const first = names[0] || unknown,
      second = names[1] || unknown;
    const prefix = t ? t("caseHearingOf") : "Case Hearing of";
    const vs = t ? t("versus") : "vs.";
    const on = t ? t("onSession") : "on";
    return `${prefix} ${first} ${vs} ${second} ${on} ${sessionLabel(date, t)}`;
  }

  // Part 1: accepted open cases still awaiting a case manager, not yet on this agenda.
  function part1Candidates(cases, agenda) {
    const placed = new Set((agenda || []).map((row) => row.case_id));
    return (cases || []).filter(
      (row) => row.status === "open" && !row.assigned_member && !placed.has(row.id),
    );
  }

  // Part 2: assigned open cases. Admin/secretary manage the whole agenda; a member
  // sees the cases shown as theirs (display filter only, the server decides).
  function part2Candidates(cases, agenda, user) {
    const placed = new Set((agenda || []).map((row) => row.case_id));
    return (cases || []).filter(
      (row) =>
        row.status === "open" &&
        row.assigned_member &&
        !placed.has(row.id) &&
        (canManage(user) || row.assigned_member === user?.name),
    );
  }

  function presidents(members) {
    return (members || []).filter((row) => row.role === "president");
  }

  function assignableMembers(members) {
    return (members || []).filter((row) => row.role !== "applicant");
  }

  function assignmentProblem(memberId, presidentId, members) {
    if (!memberId) return "chooseMember";
    if (!presidentId) return "choosePresident";
    if (!presidents(members).some((row) => row.id === presidentId))
      return "choosePresident";
    if (!assignableMembers(members).some((row) => row.id === memberId))
      return "chooseMember";
    return null;
  }

  function groupAgenda(items) {
    const sorted = [...(items || [])].sort(
      (a, b) => a.part - b.part || (a.position || 0) - (b.position || 0),
    );
    return {
      1: sorted.filter((row) => row.part === 1),
      2: sorted.filter((row) => row.part === 2),
    };
  }

  // Extract the server's own explanation, never a fabricated one.
  function serverMessage(error, t) {
    const data = error && error.data;
    if (error && error.status === 401) return t("expired");
    if (error && error.status === 403) return data?.detail || t("forbidden");
    if (error && error.status === 409) return data?.detail || t("conflict");
    if (data && Array.isArray(data.messages) && data.messages.length)
      return data.messages.join(" ");
    if (data && typeof data.detail === "string") return data.detail;
    return t("actionFailed");
  }

  function answerText(value, t) {
    if (value === null || value === undefined || value === "") return t("notAnswered");
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (Array.isArray(value) && value.every((v) => typeof v === "string"))
      return value.join(", ");
    return JSON.stringify(value);
  }

  // ---------- Words ----------

  const words = {
    en: {
      councilSession: "Council Session",
      reviewQueue: "Applications awaiting completeness review",
      reviewQueueEmpty: "No applications are awaiting completeness review.",
      reviewOpen: "Review applications",
      reviewCount: "{n} awaiting review",
      review: "Completeness review",
      back: "Back",
      chooseApplication: "Select an application to review",
      unnumbered: "Case number pending",
      version: "Version",
      fee: "Fee",
      paid: "Paid",
      waived: "Fee waived",
      historical_exempt: "Historical entry exemption",
      due: "Payment due",
      unknown: "Unknown",
      answers: "Submitted answers",
      notAnswered: "Not answered",
      codesNotice:
        "Approved question labels are not yet provided to this view, so answer codes are shown exactly as stored.",
      noAnswers: "No answers are stored for this version.",
      documents: "Open case documents",
      accept: "Accept application",
      acceptTitle: "Accept this application?",
      acceptMessage:
        "The application becomes available for council assignment. The applicant is notified.",
      returnAction: "Return for correction",
      returnTitle: "Return for correction",
      returnHelp:
        "Explain exactly what the applicant must correct. Returning is not a denial; the case number, fee and signature are kept.",
      returnLabel: "Correction instructions",
      returnRequired: "Correction instructions are required to return an application.",
      reviewChoose: "Choose Accept or Return for correction.",
      cancel: "Cancel",
      accepted: "The application was accepted.",
      returned: "The application was returned for correction.",
      actionFailed: "The action could not be completed. Nothing was changed.",
      forbidden: "You are not authorized to perform this action.",
      conflict: "This record changed or conflicts with another saved record. Reload and try again.",
      expired: "Your session has expired. Sign in again to continue.",
      loading: "Loading…",
      loadFailed: "Unable to load this information.",
      retry: "Try again",
      reviewOnlyAdmin:
        "Only the tribunal administrator or secretary can accept or return applications.",
      sessions: "Tribunal Sessions",
      noSessions: "No council sessions are scheduled.",
      newSession: "New council session",
      sessionDate: "Session date",
      createSession: "Create session",
      dateRequired: "Enter a valid session date.",
      dateTaken: "A council session already exists on that date.",
      sessionCreated: "The council session was created.",
      planned: "Planned",
      closed: "Closed",
      reference: "Reference",
      statusLabel: "Status",
      backSessions: "Back to sessions",
      agenda: "Agenda",
      part1: "Part 1 — New case assignments",
      part2: "Part 2 — Case hearings",
      part1Empty: "No new cases are on this part of the agenda.",
      part2Empty: "No case hearings are on this part of the agenda.",
      addCase: "Add case",
      addToPart1: "Add accepted case for assignment",
      addToPart2: "Add case for hearing",
      chooseCase: "Select a case",
      noCandidates: "No eligible cases are available.",
      placed: "The case was added to the agenda.",
      scheduled: "Scheduled",
      heard: "Heard",
      presenter_absent: "Presenter absent — awaiting manual placement",
      unpresented: "Not presented",
      time_exhausted: "Time exhausted",
      deferred: "Deferred — awaiting manual placement",
      assigned: "Assigned case manager",
      unassigned: "Not yet assigned",
      recordAssignment: "Record assignment",
      assignTitle: "Record case manager assignment",
      assignHelp:
        "The President authorizes the assignment; you record it. The previous and new case managers and each applicant are notified privately.",
      member: "Case manager",
      president: "Authorized by President",
      chooseMember: "Select a council member.",
      choosePresident: "Select the authorizing President.",
      noPresident:
        "No active President account is enrolled, so an assignment cannot be recorded.",
      assignmentRecorded: "The assignment was recorded.",
      present: "Present case",
      presentTitle: "Present this case now?",
      presentMessage:
        "Only the assigned case manager presents. Attendance for this hearing is taken from the session attendance.",
      heardNotice: "The case hearing was recorded.",
      absentNotice:
        "The assigned presenter is recorded absent. The hearing is deferred and awaits manual placement.",
      openCase: "Open case",
      closeSession: "Close session",
      closeTitle: "Close this council session?",
      closeMessage:
        "Unpresented cases carry over to the next already scheduled session, or await manual placement if none exists. Deferred and presenter-absent cases always await manual placement. Messages set to “Send after council session” are released.",
      sessionClosed: "The council session was closed.",
      closedReadOnly: "This session is closed and read-only.",
      unknownParty: "Unknown party",
      caseHearingOf: "Case Hearing of",
      versus: "vs.",
      onSession: "on",
      outcomeDependency:
        "Hearing recommendations and the applicant update open from the hearing record once the server exposes it.",
    },
    ar: {
      councilSession: "جلسة المجلس",
      reviewQueue: "طلبات في انتظار مراجعة الاستيفاء",
      reviewQueueEmpty: "لا توجد طلبات في انتظار مراجعة الاستيفاء.",
      reviewOpen: "مراجعة الطلبات",
      reviewCount: "{n} في انتظار المراجعة",
      review: "مراجعة استيفاء الطلب",
      back: "رجوع",
      chooseApplication: "اختر طلبًا لمراجعته",
      unnumbered: "رقم القضية لم يُحدَّد بعد",
      version: "الإصدار",
      fee: "الرسوم",
      paid: "مدفوعة",
      waived: "تم الإعفاء من الرسوم",
      historical_exempt: "إعفاء إدخال تاريخي",
      due: "الرسوم مستحقة",
      unknown: "غير معروف",
      answers: "الإجابات المقدَّمة",
      notAnswered: "لم تتم الإجابة",
      codesNotice:
        "لم تُتَح بعد عناوين الأسئلة المعتمدة لهذه الصفحة، لذلك تُعرض رموز الإجابات كما هي محفوظة.",
      noAnswers: "لا توجد إجابات محفوظة لهذا الإصدار.",
      documents: "فتح مستندات القضية",
      accept: "قبول الطلب",
      acceptTitle: "هل تريد قبول هذا الطلب؟",
      acceptMessage: "يصبح الطلب متاحًا لتعيين مسؤول القضية في المجلس، ويتم إخطار مقدم الطلب.",
      returnAction: "إعادة الطلب للتصحيح",
      returnTitle: "إعادة الطلب للتصحيح",
      returnHelp:
        "وضّح بدقة ما يجب على مقدم الطلب تصحيحه. الإعادة ليست رفضًا؛ ويُحتفظ برقم القضية والرسوم والتوقيع.",
      returnLabel: "تعليمات التصحيح",
      returnRequired: "يجب كتابة تعليمات التصحيح لإعادة الطلب.",
      reviewChoose: "اختر القبول أو الإعادة للتصحيح.",
      cancel: "إلغاء",
      accepted: "تم قبول الطلب.",
      returned: "تمت إعادة الطلب للتصحيح.",
      actionFailed: "تعذر إتمام الإجراء. لم يتم تغيير أي شيء.",
      forbidden: "غير مصرح لك بتنفيذ هذا الإجراء.",
      conflict: "تغيّر هذا السجل أو تعارض مع سجل محفوظ آخر. أعد التحميل وحاول مرة أخرى.",
      expired: "انتهت جلستك. سجّل الدخول مجددًا للمتابعة.",
      loading: "جارٍ التحميل…",
      loadFailed: "تعذر تحميل هذه المعلومات.",
      retry: "إعادة المحاولة",
      reviewOnlyAdmin: "يقتصر قبول الطلبات أو إعادتها على مسؤول المجلس أو السكرتير.",
      sessions: "جلسات المجلس",
      noSessions: "لا توجد جلسات مجلس مجدولة.",
      newSession: "جلسة مجلس جديدة",
      sessionDate: "تاريخ الجلسة",
      createSession: "إنشاء الجلسة",
      dateRequired: "أدخل تاريخًا صحيحًا للجلسة.",
      dateTaken: "توجد جلسة مجلس بالفعل في هذا التاريخ.",
      sessionCreated: "تم إنشاء جلسة المجلس.",
      planned: "مجدولة",
      closed: "مغلقة",
      reference: "المرجع",
      statusLabel: "الحالة",
      backSessions: "العودة إلى الجلسات",
      agenda: "جدول الأعمال",
      part1: "الجزء الأول — تعيين القضايا الجديدة",
      part2: "الجزء الثاني — جلسات نظر القضايا",
      part1Empty: "لا توجد قضايا جديدة في هذا الجزء من جدول الأعمال.",
      part2Empty: "لا توجد جلسات نظر قضايا في هذا الجزء من جدول الأعمال.",
      addCase: "إضافة قضية",
      addToPart1: "إضافة قضية مقبولة للتعيين",
      addToPart2: "إضافة قضية للنظر",
      chooseCase: "اختر قضية",
      noCandidates: "لا توجد قضايا مؤهلة متاحة.",
      placed: "تمت إضافة القضية إلى جدول الأعمال.",
      scheduled: "مجدولة",
      heard: "تم نظرها",
      presenter_absent: "المقدِّم غائب — في انتظار الجدولة اليدوية",
      unpresented: "لم تُعرض",
      time_exhausted: "انتهى الوقت",
      deferred: "مؤجلة — في انتظار الجدولة اليدوية",
      assigned: "مسؤول القضية",
      unassigned: "لم يُعيَّن بعد",
      recordAssignment: "تسجيل التعيين",
      assignTitle: "تسجيل تعيين مسؤول القضية",
      assignHelp:
        "يعتمد الرئيس التعيين وتقوم أنت بتسجيله. ويتم إخطار مسؤول القضية السابق والجديد وكل مقدم طلب بشكل خاص.",
      member: "مسؤول القضية",
      president: "بموافقة الرئيس",
      chooseMember: "اختر عضوًا من المجلس.",
      choosePresident: "اختر الرئيس الذي اعتمد التعيين.",
      noPresident: "لا يوجد حساب رئيس نشط مسجَّل، لذلك لا يمكن تسجيل التعيين.",
      assignmentRecorded: "تم تسجيل التعيين.",
      present: "عرض القضية",
      presentTitle: "هل تريد عرض هذه القضية الآن؟",
      presentMessage:
        "يعرض القضية مسؤولها المعيَّن فقط. ويؤخذ حضور هذه الجلسة من سجل حضور جلسة المجلس.",
      heardNotice: "تم تسجيل نظر القضية.",
      absentNotice: "سُجِّل المقدِّم المعيَّن غائبًا. تم تأجيل النظر وهو في انتظار الجدولة اليدوية.",
      openCase: "فتح القضية",
      closeSession: "إغلاق الجلسة",
      closeTitle: "هل تريد إغلاق جلسة المجلس هذه؟",
      closeMessage:
        "تنتقل القضايا التي لم تُعرض إلى الجلسة المجدولة التالية، أو تنتظر الجدولة اليدوية إن لم توجد جلسة. أما القضايا المؤجلة أو التي غاب مقدِّمها فتنتظر دائمًا الجدولة اليدوية. ويتم إرسال الرسائل المحددة بخيار «الإرسال بعد جلسة المجلس».",
      sessionClosed: "تم إغلاق جلسة المجلس.",
      closedReadOnly: "هذه الجلسة مغلقة ومتاحة للقراءة فقط.",
      unknownParty: "طرف غير معروف",
      caseHearingOf: "جلسة نظر قضية",
      versus: "ضد",
      onSession: "في",
      outcomeDependency:
        "تُفتح توصيات الجلسة والتحديث الموجَّه لمقدم الطلب من سجل الجلسة بمجرد أن يتيحه الخادم.",
    },
  };

  function translator(lang) {
    const table = words[lang === "ar" ? "ar" : "en"];
    return (key, vars) => {
      let value = table[key] ?? words.en[key] ?? key;
      if (vars) for (const [k, v] of Object.entries(vars)) value = value.replace(`{${k}}`, v);
      return value;
    };
  }

  // ---------- Views ----------

  function useLoad(loader, deps) {
    const R = window.React;
    const [state, setState] = R.useState({ data: null, error: null, pending: true });
    const [tick, setTick] = R.useState(0);
    R.useEffect(() => {
      let active = true;
      setState((old) => ({ ...old, pending: true, error: null }));
      loader()
        .then((data) => active && setState({ data, error: null, pending: false }))
        .catch((error) => active && setState({ data: null, error, pending: false }));
      return () => {
        active = false;
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [...deps, tick]);
    return [state, () => setTick((n) => n + 1)];
  }

  function loadFailure(P, h, t, retry, error) {
    return h(P.EmptyState, {
      tone: "error",
      title: error && error.status === 401 ? t("expired") : t("loadFailed"),
      action: h(P.Button, { onClick: retry }, t("retry")),
    });
  }

  const feeLabel = (row, t) => (row.fee ? t(row.fee.status) : t("unknown"));

  // Home panel for admin/secretary. Members never see this queue.
  function ReviewQueuePanel({ api, lang, user, onOpen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api("/api/applications/"), [user?.id]);
    if (!canManage(user)) return null;
    const rows = awaitingReview(state.data?.items);
    return h(
      P.Panel,
      {
        title: t("reviewQueue"),
        actions: rows.length
          ? h(P.Button, { size: "sm", onClick: onOpen }, t("reviewOpen"))
          : null,
      },
      state.pending
        ? h(P.Text, { as: "p" }, t("loading"))
        : state.error
          ? loadFailure(P, h, t, retry, state.error)
          : rows.length
            ? h(
                P.Stack,
                { gap: "sm" },
                h(P.Badge, { tone: "action-required" }, t("reviewCount", { n: rows.length })),
                ...rows.slice(0, 5).map((row) =>
                  h(P.Card, {
                    key: row.id,
                    title: row.case_number || t("unnumbered"),
                    meta: `${t("version")} ${row.version} · ${t("fee")}: ${feeLabel(row, t)}`,
                    onOpen,
                  }),
                ),
              )
            : h(P.EmptyState, { title: t("reviewQueueEmpty") }),
    );
  }

  function ReviewDetail({ row, api, lang, user, onDone, onCase }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [mode, setMode] = R.useState(null); // "accept" | "reject"
    const [instructions, setInstructions] = R.useState("");
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const manage = canManage(user);

    async function submit(result) {
      const issue = reviewProblem(result, instructions);
      if (issue) {
        setProblem(issue);
        return;
      }
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/applications/${encodeURIComponent(row.id)}/review/`, {
          method: "POST",
          body: JSON.stringify({
            result,
            instructions: result === "reject" ? instructions.trim() : "",
          }),
        });
        setMode(null);
        onDone(row.id, result === "accept" ? "accepted" : "returned");
      } catch (error) {
        // Keep the typed instructions so nothing is lost on failure.
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    const answers = Object.entries(row.answers || {});
    return h(
      P.Stack,
      { gap: "lg" },
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: t("reference"), data: true }, row.case_number || t("unnumbered")),
        h(P.PropertyList.Item, { label: t("version"), data: true }, String(row.version)),
        h(P.PropertyList.Item, { label: t("fee") }, feeLabel(row, t)),
      ),
      row.case_id
        ? h(
            P.Inline,
            null,
            h(P.Button, { onClick: () => onCase(row.case_id) }, t("documents")),
          )
        : null,
      h(
        P.Panel,
        { title: t("answers") },
        h(
          P.Stack,
          { gap: "sm" },
          h(P.Notice, { tone: "info" }, t("codesNotice")),
          answers.length
            ? h(
                P.PropertyList,
                { layout: "stacked" },
                ...answers.map(([code, value]) =>
                  h(P.PropertyList.Item, { key: code, label: code }, answerText(value, t)),
                ),
              )
            : h(P.EmptyState, { title: t("noAnswers") }),
        ),
      ),
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      manage
        ? h(
            P.Inline,
            { wrap: true },
            h(
              P.Button,
              {
                variant: "secondary",
                disabled: pending,
                onClick: () => {
                  setProblem(null);
                  setMode("reject");
                },
              },
              t("returnAction"),
            ),
            h(
              P.Button,
              { variant: "primary", disabled: pending, onClick: () => setMode("accept") },
              t("accept"),
            ),
          )
        : h(P.Notice, { tone: "info" }, t("reviewOnlyAdmin")),
      h(P.ConfirmDialog, {
        open: mode === "accept",
        title: t("acceptTitle"),
        message: t("acceptMessage"),
        confirmLabel: t("accept"),
        cancelLabel: t("cancel"),
        onConfirm: () => submit("accept"),
        onCancel: () => !pending && setMode(null),
      }),
      h(
        P.Dialog,
        {
          open: mode === "reject",
          title: t("returnTitle"),
          description: t("returnHelp"),
          closeLabel: t("cancel"),
          onClose: () => !pending && setMode(null),
          footer: h(
            P.Inline,
            null,
            h(P.Button, { disabled: pending, onClick: () => setMode(null) }, t("cancel")),
            h(
              P.Button,
              { variant: "primary", loading: pending, disabled: pending, onClick: () => submit("reject") },
              t("returnAction"),
            ),
          ),
        },
        h(
          P.Field,
          {
            label: t("returnLabel"),
            required: true,
            error: problem ? t(problem) : undefined,
          },
          h(P.Textarea, {
            rows: 6,
            value: instructions,
            maxLength: 10000,
            disabled: pending,
            onChange: (event) => {
              setInstructions(event.target.value);
              if (problem) setProblem(null);
            },
          }),
        ),
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function ReviewWorkspace({ api, lang, user, onCase, onBack }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api("/api/applications/"), [user?.id]);
    const [selected, select] = R.useState(null);
    const [done, setDone] = R.useState({});
    const [notice, setNotice] = R.useState(null);
    const rows = awaitingReview(state.data?.items).filter((row) => !done[row.id]);
    const chosen = rows.find((row) => row.id === selected);
    const list = state.pending
      ? h(P.Text, { as: "p" }, t("loading"))
      : state.error
        ? loadFailure(P, h, t, retry, state.error)
        : rows.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...rows.map((row) =>
                h(P.Card, {
                  key: row.id,
                  title: row.case_number || t("unnumbered"),
                  meta: `${t("version")} ${row.version} · ${t("fee")}: ${feeLabel(row, t)}`,
                  selected: row.id === selected,
                  onOpen: () => {
                    setNotice(null);
                    select(row.id);
                  },
                }),
              ),
            )
          : h(P.EmptyState, { title: t("reviewQueueEmpty") });
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Inline, null, h(P.Button, { variant: "ghost", onClick: onBack }, t("back"))),
      h(P.Text, { as: "h1", variant: "title" }, t("review")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      h(P.SplitView, {
        label: t("review"),
        firstLabel: t("reviewQueue"),
        first: list,
        second: h(
          P.ReadingPane,
          {
            label: chosen ? chosen.case_number || t("unnumbered") : t("chooseApplication"),
            empty: h(P.EmptyState, { title: t("chooseApplication") }),
          },
          chosen
            ? h(ReviewDetail, {
                key: chosen.id,
                row: chosen,
                api,
                lang,
                user,
                onCase,
                onDone: (id, outcome) => {
                  setDone((old) => ({ ...old, [id]: outcome }));
                  select(null);
                  setNotice(outcome);
                },
              })
            : null,
        ),
      }),
    );
  }

  function SessionList({ api, lang, user, onOpen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api("/api/sessions/"), [user?.id]);
    const [date, setDate] = R.useState("");
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [created, setCreated] = R.useState(false);
    const rows = state.data?.items || [];

    async function create(event) {
      event.preventDefault();
      const issue = sessionDateProblem(date, rows);
      setProblem(issue);
      setCreated(false);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        await api("/api/sessions/", { method: "POST", body: JSON.stringify({ date }) });
        setDate("");
        setCreated(true);
        retry();
      } catch (error) {
        setFailure(error && error.status === 409 ? t("dateTaken") : serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("sessions")),
      canManage(user)
        ? h(
            P.Panel,
            { title: t("newSession") },
            h(
              P.Form,
              { onSubmit: create, label: t("newSession") },
              h(
                P.Field,
                { label: t("sessionDate"), required: true, error: problem ? t(problem) : undefined },
                h(P.Input, {
                  type: "date",
                  value: date,
                  width: "sm",
                  disabled: pending,
                  onChange: (event) => {
                    setDate(event.target.value);
                    setProblem(null);
                  },
                }),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
              created ? h(P.Notice, { tone: "success" }, t("sessionCreated")) : null,
              h(
                P.FormActions,
                { sticky: false },
                h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("createSession")),
              ),
            ),
          )
        : null,
      state.pending && !state.data
        ? h(P.Text, { as: "p" }, t("loading"))
        : state.error
          ? loadFailure(P, h, t, retry, state.error)
          : rows.length
            ? h(
                P.Stack,
                { gap: "sm" },
                ...rows.map((row) =>
                  h(P.Card, {
                    key: row.id,
                    title: sessionLabel(row.date, t),
                    meta: `${t(row.state)} · ${row.reference || sessionReference(row.date) || ""}`,
                    onOpen: () => onOpen(row.id),
                  }),
                ),
              )
            : h(P.EmptyState, { title: t("noSessions") }),
    );
  }

  function AgendaItemCard({ row, session, caseRow, user, lang, onAssign, onPresent, onCase }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const planned = session.state === "planned";
    const assignedName = caseRow?.assigned_member || null;
    const mine = assignedName && assignedName === user?.name;
    const actions = [];
    if (planned && row.state === "scheduled" && row.part === 1 && canManage(user))
      actions.push(
        h(P.Button, { key: "assign", size: "xs", onClick: () => onAssign(row) }, t("recordAssignment")),
      );
    if (planned && row.state === "scheduled" && row.part === 2 && mine)
      actions.push(
        h(P.Button, { key: "present", size: "xs", variant: "primary", onClick: () => onPresent(row) }, t("present")),
      );
    actions.push(
      h(P.Button, { key: "case", size: "xs", variant: "ghost", onClick: () => onCase(row.case_id) }, t("openCase")),
    );
    return h(
      P.Card,
      {
        title: row.case_number,
        meta: `${t("assigned")}: ${assignedName || t("unassigned")}`,
        actions: h(P.Inline, { gap: "xs" }, ...actions),
      },
      h(
        P.Badge,
        {
          tone:
            row.state === "heard"
              ? "success"
              : row.state === "scheduled"
                ? "active"
                : "action-required",
        },
        t(row.state),
      ),
    );
  }

  function SessionWorkspace({ api, lang, user, sessionId, attendance, onCase, onBack }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(
      () =>
        Promise.all([
          api(`/api/sessions/${encodeURIComponent(sessionId)}/agenda/`),
          api("/api/cases/"),
          api("/api/council/members/"),
          api("/api/sessions/"),
        ]).then(([agenda, cases, members, sessions]) => ({
          session: agenda.session,
          items: agenda.items,
          cases: cases.items,
          members: members.items,
          sessions: sessions.items,
        })),
      [sessionId],
    );
    const [dialog, setDialog] = R.useState(null); // {kind, row}
    const [choice, setChoice] = R.useState({ part1: "", part2: "", member: "", president: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);

    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    const data = state.data;
    const session = data.session;
    const planned = session.state === "planned";
    const manage = canManage(user);
    const caseById = Object.fromEntries((data.cases || []).map((row) => [row.id, row]));
    const groups = groupAgenda(data.items);
    const c1 = part1Candidates(data.cases, data.items);
    const c2 = part2Candidates(data.cases, data.items, user);
    const presidentRows = presidents(data.members);
    const memberRows = assignableMembers(data.members);

    async function run(action, success, extra) {
      setPending(true);
      setFailure(null);
      setNotice(null);
      try {
        const result = await action();
        setDialog(null);
        setNotice(typeof success === "function" ? success(result) : success);
        if (extra) extra();
        retry();
      } catch (error) {
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    const place = (part) =>
      run(
        () =>
          api(`/api/sessions/${encodeURIComponent(sessionId)}/agenda/`, {
            method: "POST",
            body: JSON.stringify({ case_id: choice[`part${part}`], part }),
          }),
        "placed",
        () => setChoice((old) => ({ ...old, [`part${part}`]: "" })),
      );

    function assign() {
      const issue = assignmentProblem(choice.member, choice.president, data.members);
      setProblem(issue);
      if (issue) return;
      run(
        () =>
          api(`/api/cases/${encodeURIComponent(dialog.row.case_id)}/assignment/`, {
            method: "POST",
            body: JSON.stringify({ member_id: choice.member, president_id: choice.president }),
          }),
        "assignmentRecorded",
      );
    }

    const present = () =>
      run(
        () => api(`/api/agenda/${encodeURIComponent(dialog.row.id)}/hear/`, { method: "POST", body: "{}" }),
        (result) => (result && result.state === "presenter_absent" ? "absentNotice" : "heardNotice"),
      );

    const close = () =>
      run(
        () => api(`/api/sessions/${encodeURIComponent(sessionId)}/close/`, { method: "POST", body: "{}" }),
        "sessionClosed",
      );

    const addControl = (part, candidates) =>
      planned && (part === 1 ? manage : true)
        ? h(
            P.Inline,
            { wrap: true, align: "end" },
            h(
              P.Field,
              { label: t(part === 1 ? "addToPart1" : "addToPart2") },
              h(P.Select, {
                value: choice[`part${part}`],
                disabled: pending || !candidates.length,
                onChange: (event) => setChoice((old) => ({ ...old, [`part${part}`]: event.target.value })),
                options: [
                  { value: "", label: candidates.length ? t("chooseCase") : t("noCandidates") },
                  ...candidates.map((row) => ({ value: row.id, label: row.number })),
                ],
              }),
            ),
            h(
              P.Button,
              { disabled: pending || !choice[`part${part}`], onClick: () => place(part) },
              t("addCase"),
            ),
          )
        : null;

    const part = (n) =>
      h(
        P.Panel,
        { key: n, title: t(`part${n}`) },
        h(
          P.Stack,
          { gap: "sm" },
          ...groups[n].map((row) =>
            h(AgendaItemCard, {
              key: row.id,
              row,
              session,
              caseRow: caseById[row.case_id],
              user,
              lang,
              onCase,
              onAssign: (item) => {
                setProblem(null);
                setFailure(null);
                setChoice((old) => ({ ...old, member: "", president: "" }));
                setDialog({ kind: "assign", row: item });
              },
              onPresent: (item) => {
                setFailure(null);
                setDialog({ kind: "present", row: item });
              },
            }),
          ),
          !groups[n].length ? h(P.EmptyState, { title: t(`part${n}Empty`) }) : null,
          addControl(n, n === 1 ? c1 : c2),
        ),
      );

    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Inline, null, h(P.Button, { variant: "ghost", onClick: onBack }, t("backSessions"))),
      h(
        P.Inline,
        { justify: "between", wrap: true },
        h(P.Text, { as: "h1", variant: "title" }, sessionLabel(session.date, t)),
        manage && planned
          ? h(P.Button, { variant: "danger-secondary", disabled: pending, onClick: () => setDialog({ kind: "close" }) }, t("closeSession"))
          : null,
      ),
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: t("reference"), data: true }, sessionReference(session.date) || ""),
        h(P.PropertyList.Item, { label: t("statusLabel") }, h(P.Badge, { tone: planned ? "active" : "neutral" }, t(session.state))),
      ),
      !planned ? h(P.Notice, { tone: "info" }, t("closedReadOnly")) : null,
      notice ? h(P.Notice, { tone: notice === "absentNotice" ? "warning" : "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !dialog ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      attendance || null,
      h(P.Text, { as: "h2", variant: "heading" }, t("agenda")),
      part(1),
      part(2),
      h(P.Notice, { tone: "info" }, t("outcomeDependency")),
      h(
        P.Dialog,
        {
          open: dialog?.kind === "assign",
          title: t("assignTitle"),
          description: t("assignHelp"),
          closeLabel: t("cancel"),
          onClose: () => !pending && setDialog(null),
          footer: h(
            P.Inline,
            null,
            h(P.Button, { disabled: pending, onClick: () => setDialog(null) }, t("cancel")),
            h(
              P.Button,
              { variant: "primary", loading: pending, disabled: pending || !presidentRows.length, onClick: assign },
              t("recordAssignment"),
            ),
          ),
        },
        dialog?.kind === "assign"
          ? h(
              P.Stack,
              { gap: "md" },
              h(P.Text, { as: "p", variant: "strong" }, dialog.row.case_number),
              !presidentRows.length ? h(P.Notice, { tone: "warning" }, t("noPresident")) : null,
              h(
                P.Field,
                { label: t("member"), required: true, error: problem === "chooseMember" ? t(problem) : undefined },
                h(P.Select, {
                  value: choice.member,
                  disabled: pending,
                  onChange: (event) => setChoice((old) => ({ ...old, member: event.target.value })),
                  options: [
                    { value: "", label: t("chooseMember") },
                    ...memberRows.map((row) => ({ value: row.id, label: row.name || row.id })),
                  ],
                }),
              ),
              h(
                P.Field,
                { label: t("president"), required: true, error: problem === "choosePresident" ? t(problem) : undefined },
                h(P.Select, {
                  value: choice.president,
                  disabled: pending || !presidentRows.length,
                  onChange: (event) => setChoice((old) => ({ ...old, president: event.target.value })),
                  options: [
                    { value: "", label: t("choosePresident") },
                    ...presidentRows.map((row) => ({ value: row.id, label: row.name || row.id })),
                  ],
                }),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
            )
          : null,
      ),
      h(
        P.ConfirmDialog,
        {
          open: dialog?.kind === "present",
          title: t("presentTitle"),
          message: t("presentMessage"),
          confirmLabel: t("present"),
          cancelLabel: t("cancel"),
          onConfirm: present,
          onCancel: () => !pending && setDialog(null),
        },
        failure && dialog?.kind === "present" ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
      h(
        P.ConfirmDialog,
        {
          open: dialog?.kind === "close",
          title: t("closeTitle"),
          message: t("closeMessage"),
          confirmLabel: t("closeSession"),
          cancelLabel: t("cancel"),
          onConfirm: close,
          onCancel: () => !pending && setDialog(null),
        },
        failure && dialog?.kind === "close" ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  window.CTMCouncil = {
    words,
    translator,
    canManage,
    awaitingReview,
    reviewProblem,
    sessionLabel,
    sessionReference,
    sessionDateProblem,
    hearingTitle,
    part1Candidates,
    part2Candidates,
    presidents,
    assignableMembers,
    assignmentProblem,
    groupAgenda,
    serverMessage,
    answerText,
    ReviewQueuePanel,
    ReviewWorkspace,
    SessionList,
    SessionWorkspace,
  };
})();
