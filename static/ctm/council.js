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
    const unknown = t ? t("unknownParty") : "Unknown spouse";
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

  function writerOf(user, row, caseRow) {
    if (canManage(user)) return true;
    if (row && row.assigned_member_id !== undefined) return Boolean(user && row.assigned_member_id === user.id);
    return Boolean(caseRow?.assigned_member && caseRow.assigned_member === user?.name);
  }

  // Which controls an agenda row shows. Server capability flags win when present;
  // the role/name fallback only applies to servers without them.
  function agendaActions(row, session, user, caseRow) {
    const planned = session.state === "planned";
    const scheduled = row.state === "scheduled";
    const manage = typeof session.can_manage === "boolean" ? session.can_manage : canManage(user) && planned;
    const assignedName = row.assigned_member_name ?? caseRow?.assigned_member ?? null;
    const mine =
      row.assigned_member_id !== undefined
        ? Boolean(user && row.assigned_member_id === user.id)
        : Boolean(assignedName && assignedName === user?.name);
    const present =
      typeof row.can_present === "boolean" ? row.can_present : planned && scheduled && row.part === 2 && mine;
    return {
      assign: planned && scheduled && row.part === 1 && manage,
      present,
      presentNeedsAttendance: !present && planned && scheduled && row.part === 2 && mine && typeof row.can_present === "boolean",
      outcome: row.can_record_outcome === true && Boolean(row.hearing_id),
      testimony: planned && scheduled && row.part === 2 && writerOf(user, row, caseRow),
    };
  }

  function testimonyProblem(form, sessionDate) {
    if (!form.party) return "chooseParty";
    if (!/^\d{2}:\d{2}$/.test(form.start || "") || !/^\d{2}:\d{2}$/.test(form.end || "")) return "timesRequired";
    if (form.end <= form.start) return "endAfterStart";
    if (!String(form.instructions || "").trim()) return "instructionsRequired";
    if (!DATE.test(sessionDate || "")) return "timesRequired";
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

  // Label from the submission's bound questionnaire; null when none is approved.
  function fieldLabel(row, code, lang) {
    const fields = row?.questionnaire?.definition?.fields;
    if (!Array.isArray(fields)) return null;
    const field = fields.find((f) => f && f.code === code);
    if (!field) return null;
    const ar = String(field.label_ar || "").trim();
    const en = String(field.label_en || "").trim();
    return (lang === "ar" ? ar || null : en || null) || null;
  }

  function formatTime(value, lang) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value || "");
    return new Intl.DateTimeFormat(lang === "ar" ? "ar-EG" : "en-US", {
      timeStyle: "short",
      timeZone: "America/Los_Angeles",
    }).format(d);
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
        "Approved question wording is not yet available here, so answer codes are shown exactly as stored.",
      noAnswers: "No answers are stored for this version.",
      applicant: "Applicant",
      submittedAt: "Submitted",
      previousReturns: "Previous returns for correction",
      manifest: "Submitted documents",
      noManifest: "No documents are recorded in this submission.",
      download: "Download",
      scanPending: "Safety check not complete",
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
      recordReassignment: "Record reassignment",
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
      unknownParty: "Unknown spouse",
      statsTitle: "Statistics and Reports",
      statsScope: "Operational counts for council planning. These are not rates: tribunal cases have no population denominator, so no divorce or approval rate is implied.",
      statsPartial: "Counts cover the most recent 100 cases or sessions returned to this view. Complete figures need a server summary.",
      statsCases: "Cases",
      statsOpen: "Open cases",
      statsUnassigned: "Open cases awaiting a case manager",
      statsClosed: "Closed cases",
      statsByManager: "Open cases by case manager",
      statsSessions: "Council sessions",
      casesTitle: "Cases",
      archivedTitle: "Archived",
      searchCases: "Find a case by number or case manager",
      caseNumber: "Case number",
      noOpenCases: "No open cases.",
      noArchived: "No closed cases.",
      noMatchingCases: "No cases match.",
      tablePerPage: "Rows per page",
      tableRange: "{first}–{last} of {total}",
      tableCount: "{shown} of {total}",
      tablePages: "{label} pages",
      state_submitted: "Submitted",
      state_accepted: "Accepted",
      state_returned: "Returned for correction",
      state_withdrawn: "Withdrawn",
      homeTitle: "Home",
      upcomingSession: "Upcoming council session",
      noUpcoming: "No council session is scheduled.",
      needsAttention: "Needs attention",
      unreadNotifications: "{n} unread notifications",
      openNotifications: "Open notifications",
      nothingNeedsAttention: "Nothing needs your attention right now.",
      myCases: "My cases",
      myCasesCount: "{n} open cases assigned to you",
      noMyCases: "No open cases are assigned to you.",
      open: "Open",
      searchTitle: "Search",
      searchLabel: "Search documents",
      searchHelp: "Searches the text of open and closed case documents you are permitted to see. Latest versions by default.",
      searchLength: "Use a search phrase of 2 to 200 characters.",
      searchAction: "Search",
      searchHistory: "Include earlier file versions",
      searchResults: "Results",
      searchCount: "{n} results",
      searchNone: "No permitted documents match this search.",
      searchChoose: "Select a result",
      searchExcerpt: "Excerpt",
      searchNoExcerpt: "No text excerpt is available for this document.",
      assigned_state: "Assigned",
      presentNeedsAttendance: "Your attendance must be recorded as present before you can present this case.",
      recordOutcome: "Recommendations and update",
      hearingOutcome: "Hearing recommendations and applicant update",
      outcomeFirstNotice: "Saving the first record sends each registered applicant a private update that the case was presented on this date and is still pending, followed by your message if you write one.",
      outcomeRevisionNotice: "Revisions are kept in history and are not sent to applicants. The update already sent is not changed or resent.",
      internalDiscussion: "Internal discussion (council only)",
      recommendations: "Recommendations (council only)",
      applicantMessage: "Message to applicants (optional)",
      applicantMessageHelp: "Added after the standard pending-case update. Each applicant receives a private copy.",
      saveAndSend: "Save and send update",
      saveRevision: "Save revision",
      outcomeHistory: "Revision history",
      outcomeSentNotice: "The hearing record was saved and the applicant update was sent.",
      outcomeRevisedNotice: "The revision was saved. No message was sent.",
      scheduleTestimony: "Schedule testimony",
      testimonyHelp: "Applicants attend only their own testimony, never the deliberation. The applicant receives a private invitation and can confirm or reject it.",
      testifyingApplicant: "Applicant",
      chooseParty: "Select the applicant.",
      startTime: "Start time",
      endTime: "End time",
      timesRequired: "Enter the start and end times.",
      endAfterStart: "The end time must be after the start time.",
      testimonyInstructions: "Location or remote instructions",
      testimonyInstructionsHelp: "Shown privately to this applicant only.",
      instructionsRequired: "Enter the location or remote instructions.",
      sendInvitation: "Send invitation",
      testimonyScheduled: "The testimony invitation was sent.",
      pacificTime: "Pacific time (Los Angeles)",
      testimony: "Testimony",
      awaitingResponse: "Awaiting response",
      response_confirm: "Confirmed",
      response_reject: "Rejected",
      cancelled: "Cancelled",
      caseHearingOf: "Case Hearing of",
      versus: "vs.",
      onSession: "on",
      outcomeDependency:
        "Hearing recommendations and the applicant update are not yet available from this view.",
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
      applicant: "مقدم الطلب",
      submittedAt: "تاريخ التقديم",
      previousReturns: "مرات الإعادة للتصحيح السابقة",
      manifest: "المستندات المقدَّمة",
      noManifest: "لا توجد مستندات مسجلة في هذا التقديم.",
      download: "تنزيل",
      scanPending: "لم يكتمل فحص الأمان",
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
      recordReassignment: "تسجيل إعادة التعيين",
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
      unknownParty: "زوج غير معروف",
      statsTitle: "الإحصاءات والتقارير",
      statsScope: "أعداد تشغيلية لتخطيط عمل المجلس. وهي ليست نسبًا: فقضايا المجلس ليس لها مقام سكاني، لذلك لا يُستنتج منها أي معدل للطلاق أو للموافقة.",
      statsPartial: "تشمل الأعداد أحدث ١٠٠ قضية أو جلسة معروضة في هذه الصفحة. وتحتاج الأرقام الكاملة إلى ملخص من الخادم.",
      statsCases: "القضايا",
      statsOpen: "القضايا المفتوحة",
      statsUnassigned: "قضايا مفتوحة في انتظار تعيين مسؤول",
      statsClosed: "القضايا المغلقة",
      statsByManager: "القضايا المفتوحة حسب مسؤول القضية",
      statsSessions: "جلسات المجلس",
      casesTitle: "القضايا",
      archivedTitle: "الأرشيف",
      searchCases: "ابحث عن قضية برقمها أو بمسؤولها",
      caseNumber: "رقم القضية",
      noOpenCases: "لا توجد قضايا مفتوحة.",
      noArchived: "لا توجد قضايا مغلقة.",
      noMatchingCases: "لا توجد قضايا مطابقة.",
      tablePerPage: "عدد الصفوف في الصفحة",
      tableRange: "{first}–{last} من {total}",
      tableCount: "{shown} من {total}",
      tablePages: "صفحات {label}",
      state_submitted: "مُقدَّم",
      state_accepted: "مقبول",
      state_returned: "أُعيد للتصحيح",
      state_withdrawn: "مسحوب",
      homeTitle: "الرئيسية",
      upcomingSession: "جلسة المجلس القادمة",
      noUpcoming: "لا توجد جلسة مجلس مجدولة.",
      needsAttention: "يحتاج إلى متابعة",
      unreadNotifications: "{n} إشعارات غير مقروءة",
      openNotifications: "فتح الإشعارات",
      nothingNeedsAttention: "لا يوجد ما يحتاج إلى متابعتك الآن.",
      myCases: "قضاياي",
      myCasesCount: "{n} قضايا مفتوحة معيَّنة لك",
      noMyCases: "لا توجد قضايا مفتوحة معيَّنة لك.",
      open: "مفتوحة",
      searchTitle: "البحث",
      searchLabel: "البحث في المستندات",
      searchHelp: "يبحث في نصوص مستندات القضايا المفتوحة والمغلقة المسموح لك برؤيتها. أحدث الإصدارات افتراضيًا.",
      searchLength: "استخدم عبارة بحث من حرفين إلى ٢٠٠ حرف.",
      searchAction: "بحث",
      searchHistory: "تضمين الإصدارات السابقة من الملفات",
      searchResults: "النتائج",
      searchCount: "{n} نتيجة",
      searchNone: "لا توجد مستندات مسموح بها تطابق هذا البحث.",
      searchChoose: "اختر نتيجة",
      searchExcerpt: "مقتطف",
      searchNoExcerpt: "لا يتوفر مقتطف نصي لهذا المستند.",
      assigned_state: "تم التعيين",
      presentNeedsAttendance: "يجب تسجيل حضورك قبل أن تتمكن من عرض هذه القضية.",
      recordOutcome: "التوصيات والتحديث",
      hearingOutcome: "توصيات الجلسة والتحديث الموجَّه لمقدمي الطلب",
      outcomeFirstNotice: "يؤدي حفظ السجل الأول إلى إرسال تحديث خاص لكل مقدم طلب مسجَّل يفيد بأن القضية عُرضت في هذا التاريخ وما زالت قيد النظر، تليه رسالتك إن كتبتها.",
      outcomeRevisionNotice: "تُحفظ التعديلات في السجل ولا تُرسل إلى مقدمي الطلب. ولا يتغير التحديث المُرسل سابقًا ولا يُعاد إرساله.",
      internalDiscussion: "المداولة الداخلية (للمجلس فقط)",
      recommendations: "التوصيات (للمجلس فقط)",
      applicantMessage: "رسالة إلى مقدمي الطلب (اختياري)",
      applicantMessageHelp: "تُضاف بعد التحديث المعتاد بأن القضية ما زالت قيد النظر. ويتلقى كل مقدم طلب نسخة خاصة.",
      saveAndSend: "حفظ وإرسال التحديث",
      saveRevision: "حفظ التعديل",
      outcomeHistory: "سجل التعديلات",
      outcomeSentNotice: "تم حفظ سجل الجلسة وإرسال التحديث إلى مقدمي الطلب.",
      outcomeRevisedNotice: "تم حفظ التعديل. لم تُرسل أي رسالة.",
      scheduleTestimony: "جدولة الإدلاء بالشهادة",
      testimonyHelp: "يحضر مقدم الطلب جلسة إدلائه بشهادته فقط، ولا يحضر المداولة. ويتلقى دعوة خاصة يمكنه تأكيدها أو رفضها.",
      testifyingApplicant: "مقدم الطلب",
      chooseParty: "اختر مقدم الطلب.",
      startTime: "وقت البدء",
      endTime: "وقت الانتهاء",
      timesRequired: "أدخل وقتَي البدء والانتهاء.",
      endAfterStart: "يجب أن يكون وقت الانتهاء بعد وقت البدء.",
      testimonyInstructions: "المكان أو تعليمات الحضور عن بُعد",
      testimonyInstructionsHelp: "تظهر لمقدم الطلب هذا فقط بشكل خاص.",
      instructionsRequired: "أدخل المكان أو تعليمات الحضور عن بُعد.",
      sendInvitation: "إرسال الدعوة",
      testimonyScheduled: "تم إرسال دعوة الإدلاء بالشهادة.",
      pacificTime: "توقيت المحيط الهادئ (لوس أنجلوس)",
      testimony: "الشهادة",
      awaitingResponse: "في انتظار الرد",
      response_confirm: "تم التأكيد",
      response_reject: "تم الرفض",
      cancelled: "ملغاة",
      caseHearingOf: "جلسة نظر قضية",
      versus: "ضد",
      onSession: "في",
      outcomeDependency:
        "توصيات الجلسة والتحديث الموجَّه لمقدم الطلب غير متاحة بعد من هذه الصفحة.",
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
  const REVIEW_URL = "/api/applications/?state=awaiting_review";
  function formatWhen(value, lang) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return new Intl.DateTimeFormat(lang === "ar" ? "ar-EG" : "en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "America/Los_Angeles",
    }).format(d);
  }
  const reviewMeta = (row, t, lang) =>
    [row.applicant_name, row.submitted_at ? formatWhen(row.submitted_at, lang) : null, `${t("fee")}: ${feeLabel(row, t)}`]
      .filter(Boolean)
      .join(" · ");

  // Home panel for admin/secretary. Members never see this queue.
  function ReviewQueuePanel({ api, lang, user, onOpen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api(REVIEW_URL), [user?.id]);
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
                    meta: reviewMeta(row, t, lang),
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
    // Server capability when provided; role check only as a display fallback.
    const manage = typeof row.can_review === "boolean" ? row.can_review : canManage(user);

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
    const labelled = answers.map(([code, value]) => [code, fieldLabel(row, code, lang), value]);
    const allLabelled = labelled.every(([, label]) => Boolean(label));
    const manifest = row.manifest || [];
    const returns = (row.reviews || []).filter((r) => r.result === "reject");
    return h(
      P.Stack,
      { gap: "lg" },
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: t("reference"), data: true }, row.case_number || t("unnumbered")),
        row.applicant_name ? h(P.PropertyList.Item, { label: t("applicant") }, row.applicant_name) : null,
        row.submitted_at ? h(P.PropertyList.Item, { label: t("submittedAt"), data: true }, formatWhen(row.submitted_at, lang)) : null,
        h(P.PropertyList.Item, { label: t("version"), data: true }, String(row.submitted_version ?? row.version)),
        h(P.PropertyList.Item, { label: t("fee") }, feeLabel(row, t)),
      ),
      returns.length
        ? h(
            P.Panel,
            { title: t("previousReturns") },
            h(P.List, {
              variant: "bullets",
              items: returns.map((r) => ({ children: `${formatWhen(r.timestamp, lang)} · ${r.actor}: ${r.instructions}` })),
            }),
          )
        : null,
      row.manifest
        ? h(
            P.Panel,
            { title: t("manifest") },
            manifest.length
              ? h(
                  P.Stack,
                  { gap: "sm" },
                  ...manifest.map((file) =>
                    h(
                      P.Inline,
                      { key: file.file_id, wrap: true, justify: "between" },
                      h(P.Text, { variant: "data" }, `${file.category} · ${file.name || file.file_id}`),
                      file.scan_state === "clean"
                        ? h(P.Button, { size: "xs", href: `/api/files/${encodeURIComponent(file.file_id)}/` }, t("download"))
                        : h(P.Badge, { tone: "waiting" }, t("scanPending")),
                    ),
                  ),
                )
              : h(P.EmptyState, { title: t("noManifest") }),
          )
        : null,
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
          !allLabelled ? h(P.Notice, { tone: "info" }, t("codesNotice")) : null,
          answers.length
            ? h(
                P.PropertyList,
                { layout: "stacked" },
                ...labelled.map(([code, label, value]) =>
                  h(P.PropertyList.Item, { key: code, label: label || code }, answerText(value, t)),
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
    const [state, retry] = useLoad(() => api(REVIEW_URL), [user?.id]);
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
                  meta: reviewMeta(row, t, lang),
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
              { onSubmit: create, label: t("newSession"), noValidate: true },
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

  function AgendaItemCard({ row, session, caseRow, user, lang, onAssign, onPresent, onCase, onOutcome, onTestimony }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const flags = agendaActions(row, session, user, caseRow);
    const assignedName = row.assigned_member_name ?? caseRow?.assigned_member ?? null;
    const actions = [];
    if (flags.assign)
      actions.push(
        h(P.Button, { key: "assign", size: "xs", onClick: () => onAssign(row) }, t(assignedName ? "recordReassignment" : "recordAssignment")),
      );
    if (flags.present)
      actions.push(
        h(P.Button, { key: "present", size: "xs", variant: "primary", onClick: () => onPresent(row) }, t("present")),
      );
    if (flags.outcome)
      actions.push(h(P.Button, { key: "outcome", size: "xs", onClick: () => onOutcome(row) }, t("recordOutcome")));
    if (flags.testimony)
      actions.push(h(P.Button, { key: "testimony", size: "xs", onClick: () => onTestimony(row) }, t("scheduleTestimony")));
    actions.push(
      h(P.Button, { key: "case", size: "xs", variant: "ghost", onClick: () => onCase(row.case_id) }, t("openCase")),
    );
    const titled = row.part === 2 && Array.isArray(row.party_names) && row.party_names.length;
    return h(
      P.Card,
      {
        title: titled ? hearingTitle(row.party_names, session.date, t) : row.case_number,
        meta: [titled ? row.case_number : null, `${t("assigned")}: ${assignedName || t("unassigned")}`].filter(Boolean).join(" · "),
        actions: h(P.Inline, { gap: "xs", wrap: true }, ...actions),
      },
      h(
        P.Stack,
        { gap: "xs" },
        h(
          P.Badge,
          {
            tone:
              row.state === "heard" || row.state === "assigned"
                ? "success"
                : row.state === "scheduled"
                  ? "active"
                  : "action-required",
          },
          t(row.state === "assigned" ? "assigned_state" : row.state),
        ),
        flags.presentNeedsAttendance ? h(P.Text, { variant: "secondary" }, t("presentNeedsAttendance")) : null,
        ...(row.testimony || []).map((a) =>
          h(
            P.Text,
            { key: a.id, variant: "secondary" },
            `${t("testimony")}: ${a.party_name} · ${formatTime(a.starts_at, lang)}–${formatTime(a.ends_at, lang)} · ${t(a.state === "cancelled" ? "cancelled" : a.response ? "response_" + a.response : "awaitingResponse")}`,
          ),
        ),
      ),
    );
  }

  // Hearing outcome: internal text and recommendations are revised silently; only the
  // first record sends the default pending update (plus any message) to applicants.
  function HearingOutcomeDialog({ api, lang, hearingId, title, onClose, onSaved }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api(`/api/hearings/${encodeURIComponent(hearingId)}/`), [hearingId]);
    const [form, setForm] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const outcomes = state.data?.outcomes || [];
    const latest = outcomes[outcomes.length - 1];
    const first = !outcomes.length;
    R.useEffect(() => {
      if (state.data && !form)
        setForm({
          internal_text: latest?.internal_text || "",
          recommendations: latest?.recommendations || "",
          applicant_message: "",
        });
    }, [state.data]);
    async function save() {
      setPending(true);
      setFailure(null);
      try {
        const payload = { internal_text: form.internal_text, recommendations: form.recommendations };
        if (first && form.applicant_message.trim()) payload.applicant_message = form.applicant_message.trim();
        await api(`/api/hearings/${encodeURIComponent(hearingId)}/outcome/`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        onSaved(first ? "outcomeSentNotice" : "outcomeRevisedNotice");
      } catch (error) {
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const writable = state.data?.can_record_outcome !== false;
    const area = (key, rows, max) =>
      h(P.Textarea, {
        rows,
        autoGrow: true,
        value: form[key],
        maxLength: max,
        disabled: pending || !writable,
        onChange: (e) => setForm({ ...form, [key]: e.target.value }),
      });
    return h(
      P.Dialog,
      {
        open: true,
        size: "lg",
        title: t("hearingOutcome"),
        description: title,
        closeLabel: t("cancel"),
        onClose: () => !pending && onClose(),
        footer: h(
          P.Inline,
          null,
          h(P.Button, { disabled: pending, onClick: onClose }, t("cancel")),
          writable && form
            ? h(
                P.Button,
                { variant: "primary", loading: pending, disabled: pending, onClick: save },
                t(first ? "saveAndSend" : "saveRevision"),
              )
            : null,
        ),
      },
      state.pending && !state.data
        ? h(P.Text, { as: "p" }, t("loading"))
        : state.error
          ? loadFailure(P, h, t, retry, state.error)
          : form
            ? h(
                P.Stack,
                { gap: "md" },
                h(P.Notice, { tone: first ? "warning" : "info" }, t(first ? "outcomeFirstNotice" : "outcomeRevisionNotice")),
                h(P.Field, { label: t("internalDiscussion") }, area("internal_text", 5, 50000)),
                h(P.Field, { label: t("recommendations") }, area("recommendations", 5, 50000)),
                first
                  ? h(
                      P.Field,
                      { label: t("applicantMessage"), description: t("applicantMessageHelp") },
                      area("applicant_message", 4, 20000),
                    )
                  : null,
                outcomes.length
                  ? h(
                      P.Panel,
                      { title: t("outcomeHistory"), collapsible: true, defaultExpanded: false },
                      h(P.List, {
                        variant: "bullets",
                        items: [...outcomes]
                          .reverse()
                          .map((o) => ({ children: `${formatWhen(o.timestamp, lang)} · ${o.actor}` })),
                      }),
                    )
                  : null,
                failure ? h(P.Notice, { tone: "danger" }, failure) : null,
              )
            : null,
    );
  }

  // Testimony is a separately scheduled, private applicant appointment on the session date.
  function TestimonyDialog({ api, lang, row, sessionDate, onClose, onSaved }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api(`/api/cases/${encodeURIComponent(row.case_id)}/`), [row.case_id]);
    const [form, setForm] = R.useState({ party: "", start: "", end: "", instructions: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const parties = (state.data?.parties || []).filter((p) => p.can_receive);
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    async function save() {
      const issue = testimonyProblem(form, sessionDate);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/agenda/${encodeURIComponent(row.id)}/testimony/`, {
          method: "POST",
          // Los Angeles wall-clock times on the session date (the server's time zone).
          body: JSON.stringify({
            party_id: form.party,
            starts_at: `${sessionDate}T${form.start}`,
            ends_at: `${sessionDate}T${form.end}`,
            instructions: form.instructions.trim(),
          }),
        });
        onSaved("testimonyScheduled");
      } catch (error) {
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    return h(
      P.Dialog,
      {
        open: true,
        title: t("scheduleTestimony"),
        description: t("testimonyHelp"),
        closeLabel: t("cancel"),
        onClose: () => !pending && onClose(),
        footer: h(
          P.Inline,
          null,
          h(P.Button, { disabled: pending, onClick: onClose }, t("cancel")),
          h(
            P.Button,
            { variant: "primary", loading: pending, disabled: pending || !parties.length, onClick: save },
            t("sendInvitation"),
          ),
        ),
      },
      state.pending && !state.data
        ? h(P.Text, { as: "p" }, t("loading"))
        : state.error
          ? loadFailure(P, h, t, retry, state.error)
          : h(
              P.Stack,
              { gap: "md" },
              h(P.Text, { as: "p", variant: "strong" }, `${sessionLabel(sessionDate, t)} · ${t("pacificTime")}`),
              h(
                P.Field,
                { label: t("testifyingApplicant"), required: true, error: err("chooseParty") },
                h(P.Select, {
                  value: form.party,
                  disabled: pending,
                  onChange: (e) => update({ party: e.target.value }),
                  options: [{ value: "", label: t("chooseParty") }, ...parties.map((p) => ({ value: p.id, label: p.name }))],
                }),
              ),
              h(
                P.Inline,
                { wrap: true },
                h(
                  P.Field,
                  { label: t("startTime"), required: true, error: err("timesRequired") },
                  h(P.Input, { type: "time", width: "sm", value: form.start, disabled: pending, onChange: (e) => update({ start: e.target.value }) }),
                ),
                h(
                  P.Field,
                  { label: t("endTime"), required: true, error: err("endAfterStart") },
                  h(P.Input, { type: "time", width: "sm", value: form.end, disabled: pending, onChange: (e) => update({ end: e.target.value }) }),
                ),
              ),
              h(
                P.Field,
                {
                  label: t("testimonyInstructions"),
                  description: t("testimonyInstructionsHelp"),
                  required: true,
                  error: err("instructionsRequired"),
                },
                h(P.Textarea, {
                  rows: 4,
                  value: form.instructions,
                  disabled: pending,
                  maxLength: 5000,
                  onChange: (e) => update({ instructions: e.target.value }),
                }),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
            ),
    );
  }

  // renderAttendance({ session, members, attendance, key }) lets the shell keep its
  // existing attendance component while this module supplies fresh data after each action.
  function SessionWorkspace({ api, lang, user, sessionId, renderAttendance, onCase, onBack }) {
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
          api(`/api/sessions/${encodeURIComponent(sessionId)}/attendance/`),
        ]).then(([agenda, cases, members, sessions, attendance]) => ({
          loadedAt: Date.now(),
          attendance: attendance.items,
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
              onOutcome: (item) => {
                setFailure(null);
                setDialog({ kind: "outcome", row: item });
              },
              onTestimony: (item) => {
                setFailure(null);
                setDialog({ kind: "testimony", row: item });
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
        (typeof session.can_close === "boolean" ? session.can_close : manage && planned)
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
      renderAttendance
        ? renderAttendance({
            session,
            members: data.members,
            attendance: data.attendance,
            key: `${sessionId}-${data.loadedAt}`,
          })
        : null,
      h(P.Text, { as: "h2", variant: "heading" }, t("agenda")),
      part(1),
      part(2),
      !data.items.some((row) => "hearing_id" in row) ? h(P.Notice, { tone: "info" }, t("outcomeDependency")) : null,
      dialog?.kind === "outcome"
        ? h(HearingOutcomeDialog, {
            api,
            lang,
            hearingId: dialog.row.hearing_id,
            title: hearingTitle(dialog.row.party_names, session.date, t),
            onClose: () => setDialog(null),
            onSaved: (key) => {
              setDialog(null);
              setNotice(key);
              retry();
            },
          })
        : null,
      dialog?.kind === "testimony"
        ? h(TestimonyDialog, {
            api,
            lang,
            row: dialog.row,
            sessionDate: session.date,
            onClose: () => setDialog(null),
            onSaved: (key) => {
              setDialog(null);
              setNotice(key);
              retry();
            },
          })
        : null,
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

  // Council search: the server reauthorizes every hit before returning names or snippets.
  function searchProblem(query) {
    const q = String(query || "").trim();
    if (q.length < 2 || q.length > 200) return "searchLength";
    return null;
  }

  function SearchWorkspace({ api, lang, user, onCase }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [query, setQuery] = R.useState("");
    const [history, setHistory] = R.useState(false);
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [result, setResult] = R.useState(null);
    const [cases, setCases] = R.useState({});
    const [selected, select] = R.useState(null);
    async function run(event) {
      event.preventDefault();
      const issue = searchProblem(query);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      select(null);
      try {
        const [data, caseList] = await Promise.all([
          api(`/api/search/?q=${encodeURIComponent(query.trim())}&history=${history ? "true" : "false"}`),
          api("/api/cases/"),
        ]);
        setCases(Object.fromEntries((caseList.items || []).map((c) => [c.id, c.number])));
        setResult(data.items || []);
      } catch (error) {
        setResult(null);
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const rows = result || [];
    const chosen = rows.find((row) => row.file_id === selected);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("searchTitle")),
      h(
        P.Form,
        { onSubmit: run, label: t("searchTitle"), noValidate: true },
        h(
          P.Inline,
          { wrap: true, align: "end" },
          h(
            P.Field,
            { label: t("searchLabel"), description: t("searchHelp"), error: problem ? t(problem) : undefined },
            h(P.Input, { type: "search", width: "lg", value: query, maxLength: 200, disabled: pending, onChange: (e) => { setQuery(e.target.value); setProblem(null); } }),
          ),
          h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("searchAction")),
        ),
        h(P.Checkbox, { label: t("searchHistory"), checked: history, disabled: pending, onChange: (e) => setHistory(e.target.checked) }),
      ),
      failure ? h(P.Notice, { tone: "warning" }, failure) : null,
      result
        ? h(P.SplitView, {
            label: t("searchResults"),
            firstLabel: t("searchResults"),
            first: rows.length
              ? h(
                  P.Stack,
                  { gap: "sm" },
                  h(P.Text, { variant: "secondary" }, t("searchCount", { n: rows.length })),
                  ...rows.map((row) =>
                    h(P.Card, {
                      key: row.file_id,
                      title: row.name,
                      meta: cases[row.case_id] || "",
                      selected: row.file_id === selected,
                      onOpen: () => select(row.file_id),
                    }),
                  ),
                )
              : h(P.EmptyState, { title: t("searchNone") }),
            second: h(
              P.ReadingPane,
              { label: chosen ? chosen.name : t("searchChoose"), empty: h(P.EmptyState, { title: t("searchChoose") }) },
              chosen
                ? h(
                    P.Stack,
                    { gap: "md" },
                    h(P.Text, { variant: "data" }, chosen.name),
                    cases[chosen.case_id] ? h(P.Text, { variant: "secondary" }, cases[chosen.case_id]) : null,
                    chosen.snippet ? h(P.Panel, { title: t("searchExcerpt") }, h(P.Text, { as: "p" }, chosen.snippet)) : h(P.Text, { variant: "secondary" }, t("searchNoExcerpt")),
                    h(
                      P.Inline,
                      { wrap: true },
                      h(P.Button, { onClick: () => onCase(chosen.case_id) }, t("openCase")),
                      h(P.Button, { href: `/api/files/${encodeURIComponent(chosen.file_id)}/` }, t("download")),
                    ),
                  )
                : null,
            ),
          })
        : null,
    );
  }

  // Council Home: upcoming session, own cases and what needs attention.
  // Larger analytics belong to Statistics and Reports, not here.
  function myCases(cases, user) {
    return (cases || []).filter((row) => row.status === "open" && row.assigned_member && row.assigned_member === user?.name);
  }

  function CouncilHome({ api, lang, user, onCase, onSession, onReview, onNotifications }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(
      () =>
        Promise.all([api("/api/dashboard/"), api("/api/cases/"), api("/api/notifications/")]).then(([dashboard, cases, notes]) => ({
          dashboard,
          cases: cases.items,
          unread: notes.unread_count || 0,
        })),
      [user?.id],
    );
    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    const { dashboard, cases, unread } = state.data;
    const upcoming = dashboard.upcoming_sessions || [];
    const mine = myCases(cases, user);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("homeTitle")),
      h(
        P.Panel,
        { title: t("upcomingSession") },
        upcoming.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...upcoming.slice(0, 3).map((s) =>
                h(P.Card, { key: s.id, title: sessionLabel(s.date, t), meta: sessionReference(s.date), onOpen: () => onSession(s.id) }),
              ),
            )
          : h(P.EmptyState, { title: t("noUpcoming") }),
      ),
      h(
        P.Panel,
        { title: t("needsAttention") },
        h(
          P.Stack,
          { gap: "sm" },
          unread
            ? h(
                P.Inline,
                { justify: "between", wrap: true },
                h(P.Text, null, t("unreadNotifications", { n: unread })),
                h(P.Button, { size: "xs", onClick: onNotifications }, t("openNotifications")),
              )
            : null,
          typeof dashboard.review_queue === "number" && dashboard.review_queue > 0
            ? h(
                P.Inline,
                { justify: "between", wrap: true },
                h(P.Text, null, t("reviewCount", { n: dashboard.review_queue })),
                h(P.Button, { size: "xs", onClick: onReview }, t("reviewOpen")),
              )
            : null,
          !unread && !(dashboard.review_queue > 0) ? h(P.EmptyState, { title: t("nothingNeedsAttention") }) : null,
        ),
      ),
      h(
        P.Panel,
        { title: t("myCases"), description: typeof dashboard.my_cases === "number" ? t("myCasesCount", { n: dashboard.my_cases }) : undefined },
        mine.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...mine.map((row) => h(P.Card, { key: row.id, title: row.number, meta: t("open"), onOpen: () => onCase(row.id) })),
            )
          : h(P.EmptyState, { title: t("noMyCases") }),
      ),
    );
  }

  // Cases workspace table (open or archived). Built-in header/row menus are off so
  // no untranslated table chrome appears in the Arabic interface.
  function caseRows(cases, archived, query) {
    const q = String(query || "").trim().toLowerCase();
    return (cases || [])
      .filter((row) => (archived ? row.status === "closed" : row.status === "open"))
      .filter((row) => !q || [row.number, row.assigned_member || ""].some((v) => String(v).toLowerCase().includes(q)));
  }

  function CasesTable({ cases, archived, lang, onOpen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [query, setQuery] = R.useState("");
    const rows = caseRows(cases, archived, query).map((row) => ({
      id: row.id,
      number: row.number,
      status: t(row.status === "closed" ? "closed" : "open"),
      manager: row.assigned_member || t("unassigned"),
    }));
    return h(
      P.Stack,
      { gap: "md" },
      h(P.Text, { as: "h1", variant: "title" }, t(archived ? "archivedTitle" : "casesTitle")),
      h(P.Field, { label: t("searchCases") }, h(P.Input, { type: "search", width: "md", value: query, onChange: (e) => setQuery(e.target.value) })),
      rows.length
        ? h(P.DataTable, {
            label: t(archived ? "archivedTitle" : "casesTitle"),
            data: rows,
            index: "id",
            mode: "pages",
            pageSize: 25,
            headerMenu: false,
            rowMenuButton: false,
            narrow: "list",
            keyColumns: ["number", "manager", "status"],
            columns: [
              { title: t("caseNumber"), field: "number", kind: "data", sorter: "string" },
              { title: t("assigned"), field: "manager", kind: "name", sorter: "string" },
              { title: t("statusLabel"), field: "status", sorter: "string" },
            ],
            strings: {
              perPage: t("tablePerPage"),
              range: t("tableRange"),
              count: t("tableCount"),
              pages: t("tablePages"),
              empty: t("noMatchingCases"),
              failed: t("loadFailed"),
              retry: t("retry"),
            },
            onRowClick: (row) => onOpen(row.id),
          })
        : h(P.EmptyState, { title: t(query ? "noMatchingCases" : archived ? "noArchived" : "noOpenCases") }),
    );
  }

  // Operational counts only. No rates: tribunal cases have no valid population
  // denominator, so nothing here implies a divorce or approval rate.
  const LIST_LIMIT = 100;

  function caseStatistics(cases, sessions) {
    const rows = cases || [];
    const byManager = {};
    for (const row of rows)
      if (row.status === "open" && row.assigned_member) byManager[row.assigned_member] = (byManager[row.assigned_member] || 0) + 1;
    return {
      open: rows.filter((r) => r.status === "open").length,
      closed: rows.filter((r) => r.status === "closed").length,
      unassigned: rows.filter((r) => r.status === "open" && !r.assigned_member).length,
      byManager: Object.entries(byManager).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
      plannedSessions: (sessions || []).filter((s) => s.state === "planned").length,
      closedSessions: (sessions || []).filter((s) => s.state === "closed").length,
      partial: rows.length >= LIST_LIMIT || (sessions || []).length >= LIST_LIMIT,
    };
  }

  function StatisticsWorkspace({ api, lang }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(
      () => Promise.all([api("/api/cases/"), api("/api/sessions/")]).then(([cases, sessions]) => caseStatistics(cases.items, sessions.items)),
      [],
    );
    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    const s = state.data;
    const n = (value) => new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US").format(value);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("statsTitle")),
      h(P.Notice, { tone: "info" }, t("statsScope")),
      s.partial ? h(P.Notice, { tone: "warning" }, t("statsPartial")) : null,
      h(
        P.Panel,
        { title: t("statsCases") },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("statsOpen") }, n(s.open)),
          h(P.PropertyList.Item, { label: t("statsUnassigned") }, n(s.unassigned)),
          h(P.PropertyList.Item, { label: t("statsClosed") }, n(s.closed)),
        ),
      ),
      h(
        P.Panel,
        { title: t("statsByManager") },
        s.byManager.length
          ? h(P.PropertyList, null, ...s.byManager.map(([name, count]) => h(P.PropertyList.Item, { key: name, label: name }, n(count))))
          : h(P.EmptyState, { title: t("noMyCases") }),
      ),
      h(
        P.Panel,
        { title: t("statsSessions") },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("planned") }, n(s.plannedSessions)),
          h(P.PropertyList.Item, { label: t("closed") }, n(s.closedSessions)),
        ),
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
    agendaActions,
    testimonyProblem,
    writerOf,
    serverMessage,
    answerText,
    fieldLabel,
    formatWhen,
    useLoad,
    loadFailure,
    ReviewQueuePanel,
    ReviewWorkspace,
    SessionList,
    SessionWorkspace,
    searchProblem,
    SearchWorkspace,
    myCases,
    CouncilHome,
    caseRows,
    CasesTable,
    caseStatistics,
    StatisticsWorkspace,
  };
})();
