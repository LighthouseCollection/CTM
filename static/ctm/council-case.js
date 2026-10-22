/* CTM council case workspace: report requests and Decision & Voting.
   Loads after council.js and extends window.CTMCouncil. The server enforces
   every permission; capability checks here only choose which controls show. */
(() => {
  "use strict";
  const base = window.CTMCouncil;
  if (!base) return;

  // Exact prototype catalog (docs/architecture/build-spec/prototype-decision-types.json)
  // restricted to the server's decision types. Withdrawal/reconciliation are the
  // withdrawal workflow, not decision types. Approved Arabic labels are not yet
  // supplied, so the approved English label is shown in both languages.
  const DECISION_TYPES = [
    { code: "diss-applicant", label: "Dissolution Granted — Permission to Remarry (Applicant)" },
    { code: "diss-respondent", label: "Dissolution Granted — Permission to Remarry (Respondent)" },
    { code: "diss-both", label: "Dissolution Granted — Permission to Remarry (Both Parties)" },
    { code: "diss-conditional", label: "Dissolution Granted — Conditional Permission to Remarry" },
    { code: "null-granted", label: "Declaration of Nullity — Permission to Remarry Granted" },
    { code: "null-conditional", label: "Declaration of Nullity — Conditional Permission to Remarry" },
    { code: "deferred", label: "Decision Deferred — Further Investigation Required" },
    { code: "denied", label: "Petition Denied — No Permission to Remarry" },
  ];
  const ENTITLEMENTS = ["certificate", "notice_only"];
  const VOTES = ["approve", "deny", "abstain"];
  const LANGUAGES = ["en", "ar", "both"];

  // ---------- Pure logic ----------

  function typeLabel(code) {
    return DECISION_TYPES.find((row) => row.code === code)?.label || code;
  }

  function needsEntitlements(type) {
    return /^(diss|null)-/.test(type || "");
  }

  function isConditional(type) {
    return /-conditional$/.test(type || "");
  }

  function decisionProblem(form, parties) {
    if (!DECISION_TYPES.some((row) => row.code === form.type)) return "chooseType";
    if (!String(form.grounds || "").trim()) return "groundsRequired";
    if (needsEntitlements(form.type)) {
      for (const party of parties || []) {
        if (!ENTITLEMENTS.includes(form.entitlements?.[party.id])) return "entitlementRequired";
      }
      if (
        form.type === "null-granted" &&
        (parties || []).some((party) => form.entitlements[party.id] !== "certificate")
      )
        return "nullityBoth";
    }
    if (isConditional(form.type) && !String(form.conditions || "").trim())
      return "conditionsRequired";
    return null;
  }

  function decisionPayload(form, parties) {
    const entitlements = {};
    if (needsEntitlements(form.type))
      for (const party of parties || []) entitlements[party.id] = form.entitlements[party.id];
    return {
      type: form.type,
      grounds: form.grounds.trim(),
      entitlements,
      conditions: isConditional(form.type) ? form.conditions.trim() : "",
    };
  }

  // Latest effective vote per member for one exact decision version. Every
  // council member stays listed regardless of attendance.
  function tally(votes, roster) {
    const latest = {};
    for (const vote of votes || []) latest[vote.member_id] = vote;
    const rows = (roster || []).map((member) => ({
      member,
      vote: latest[member.id] || null,
    }));
    const counts = { approve: 0, deny: 0, abstain: 0, none: 0 };
    for (const row of rows) counts[row.vote ? row.vote.choice : "none"] += 1;
    return { rows, counts };
  }

  function councilRoster(members) {
    return (members || []).filter((row) => row.role !== "applicant");
  }

  function canRecordFor(user) {
    return base.canManage(user);
  }

  // Latest version of each published question, grouped by its reusable category.
  function questionGroups(questions) {
    const latest = {};
    for (const q of questions || []) {
      if (!latest[q.code] || latest[q.code].version < q.version) latest[q.code] = q;
    }
    const groups = [];
    for (const q of Object.values(latest)) {
      let group = groups.find((row) => row.category === q.category);
      if (!group) groups.push((group = { category: q.category, questions: [] }));
      group.questions.push(q);
    }
    for (const group of groups) group.questions.sort((a, b) => a.code.localeCompare(b.code));
    return groups;
  }

  function foundationalCodes(questions) {
    return questionGroups(questions)
      .flatMap((group) => group.questions)
      .filter((q) => q.foundational)
      .map((q) => q.code);
  }

  // Arabic or bilingual requests need approved Arabic wording for every question sent.
  function missingArabic(selected, questions, language) {
    if (language === "en") return [];
    const all = questionGroups(questions).flatMap((group) => group.questions);
    const codes = new Set([...(selected || []), ...foundationalCodes(questions)]);
    return all.filter((q) => codes.has(q.code) && !String(q.wording_ar || "").trim()).map((q) => q.code);
  }

  function requestProblem(form, questions) {
    if (!form.party) return "chooseSubject";
    if (!String(form.title || "").trim()) return "titleRequired";
    if (!LANGUAGES.includes(form.language)) return "chooseLanguage";
    if (missingArabic(form.selected, questions, form.language).length) return "arabicMissing";
    return null;
  }

  function requestPayload(form, proceedingId) {
    return {
      proceeding_id: proceedingId,
      party_id: form.party,
      kind: "intake",
      title: form.title.trim(),
      language: form.language,
      instructions: String(form.instructions || "").trim(),
      questions: [...form.selected],
      parent_id: form.parent || null,
    };
  }

  function openProceeding(record) {
    return (record?.proceedings || []).find((row) => row.status === "open") || null;
  }

  function wording(question, lang) {
    return lang === "ar" && String(question.ar || question.wording_ar || "").trim()
      ? question.ar || question.wording_ar
      : question.en || question.wording_en;
  }

  // ---------- Words ----------

  const words = {
    en: {
      reports: "Reports",
      completedReports: "Completed reports",
      requests: "Requests",
      newRequest: "New request",
      noRequests: "No report requests yet.",
      chooseRequest: "Select a request",
      draft: "Draft",
      sent: "Sent",
      completed: "Completed",
      closed: "Closed",
      cancelled: "Cancelled",
      intake: "Applicant intake",
      interview: "Interview",
      external_priest: "External priest report",
      medical: "Medical assessment",
      psychological: "Psychological assessment",
      subject: "Report for",
      chooseSubject: "Select the applicant this request is for.",
      method: "How the questions are answered",
      methodApplicant: "Send the selected questions to the applicant",
      methodInterview: "I will conduct the interview myself",
      interviewBlocked:
        "Recording an interview you conduct yourself is not available yet.",
      title: "Title",
      titleRequired: "Enter a title for this request.",
      language: "Request language",
      en: "English",
      ar: "Arabic",
      both: "English and Arabic",
      chooseLanguage: "Choose the request language.",
      arabicMissing:
        "Approved Arabic wording is not available for every selected question. Send this request in English, or wait for the approved Arabic wording.",
      parent: "Follow-up to report (optional)",
      noParent: "Not a follow-up",
      questions: "Questions",
      foundational: "Always included",
      selectedCount: "{n} selected in addition to the foundational questions",
      instructions: "Instructions to the applicant (optional)",
      saveDraft: "Save draft request",
      draftSaved: "The draft request was saved. Review the questions, then send it.",
      frozenNotice:
        "These are the exact questions saved with this request. Sending freezes their wording and order.",
      send: "Send to applicant",
      sendTitle: "Send this request to the applicant?",
      sendMessage:
        "The applicant is notified in the portal and can answer the questions privately. Sent questions cannot be changed.",
      sentNotice: "The request was sent to the applicant.",
      cancel: "Cancel",
      noOpenProceeding: "This case has no open proceeding, so new requests cannot be prepared.",
      writerOnly:
        "Only the assigned case manager, or the administrator or secretary, prepares and sends requests.",
      arabicPending: "Approved Arabic wording pending",
      answerReadOnly: "Responses appear under Completed reports once submitted.",
      decisionVoting: "Decision & Voting",
      noDecision: "No decision has been recorded in this view yet.",
      readUnavailable:
        "Saved decision versions, votes and approvals cannot be displayed here yet. A version recorded on this page can be voted on and approved while the page stays open.",
      votedOn: "What is being voted on",
      version: "Version",
      decisionType: "Decision type",
      chooseType: "Choose the decision type.",
      grounds: "Grounds / reason",
      groundsRequired: "Enter the grounds or reason before votes are taken.",
      entitlements: "Party entitlements",
      certificate: "Decree certificate (after explicit release)",
      notice_only: "Official decision notice only",
      entitlementRequired: "Choose an entitlement for each party.",
      nullityBoth: "A Declaration of Nullity entitles both parties to the certificate.",
      conditions: "Parties and conditions",
      conditionsRequired: "State the parties and conditions explicitly.",
      recordDecision: "Record decision version",
      reviseDecision: "Record a revised version",
      revisionNotice:
        "A revised type or grounds creates a new version. Earlier votes and approval stay with the earlier version and are not carried over.",
      decisionRecorded: "The decision version was recorded.",
      typeLabelNotice: "Approved Arabic decision-type labels are not yet supplied; the approved English label is shown.",
      votes: "Council votes",
      rosterNotice: "Every council member is listed, regardless of attendance.",
      approve: "Approve",
      deny: "Deny",
      abstain: "Abstain",
      notVoted: "No vote recorded",
      yourVote: "Your vote",
      recordFor: "Record a vote on behalf of",
      chooseMember: "Select a council member",
      recordVote: "Record vote",
      voteRecorded: "The vote was recorded.",
      tallyLine: "Approve {approve} · Deny {deny} · Abstain {abstain} · Not voted {none}",
      sessionVotesNotice: "Only votes recorded on this page are shown. Votes recorded elsewhere are saved but not yet displayed here.",
      approval: "Presidential approval",
      approveDecision: "Approve decision",
      recordApproval: "Record President's approval",
      approvalTitle: "Record final approval of this version?",
      approvalMessage: "The approval is bound to this exact version. Approval may be given with or without votes.",
      deniedWarning:
        "Approving Petition Denied closes the case and sends the official decision notice. No decree certificate is issued.",
      president: "President",
      choosePresident: "Select the President",
      approved: "Approved",
      approvalRecorded: "The approval was recorded.",
      notApproved: "Not yet approved",
      writerDecision:
        "Only the assigned case manager, or the administrator or secretary, enters the decision type and grounds.",
      actionFailed: "The action could not be completed. Nothing was changed.",
      back: "Back",
    },
    ar: {
      reports: "التقارير",
      completedReports: "التقارير المكتملة",
      requests: "الطلبات",
      newRequest: "طلب جديد",
      noRequests: "لا توجد طلبات تقارير بعد.",
      chooseRequest: "اختر طلبًا",
      draft: "مسودة",
      sent: "مُرسل",
      completed: "مكتمل",
      closed: "مغلق",
      cancelled: "ملغى",
      intake: "استيفاء بيانات مقدم الطلب",
      interview: "مقابلة",
      external_priest: "تقرير كاهن خارجي",
      medical: "تقييم طبي",
      psychological: "تقييم نفسي",
      subject: "التقرير بخصوص",
      chooseSubject: "اختر مقدم الطلب المعني بهذا الطلب.",
      method: "طريقة الإجابة عن الأسئلة",
      methodApplicant: "إرسال الأسئلة المحددة إلى مقدم الطلب",
      methodInterview: "سأجري المقابلة بنفسي",
      interviewBlocked:
        "تسجيل مقابلة تجريها بنفسك غير متاح بعد.",
      title: "العنوان",
      titleRequired: "أدخل عنوانًا لهذا الطلب.",
      language: "لغة الطلب",
      en: "الإنجليزية",
      ar: "العربية",
      both: "الإنجليزية والعربية",
      chooseLanguage: "اختر لغة الطلب.",
      arabicMissing:
        "الصياغة العربية المعتمدة غير متاحة لكل الأسئلة المحددة. أرسل هذا الطلب بالإنجليزية، أو انتظر الصياغة العربية المعتمدة.",
      parent: "متابعة لتقرير سابق (اختياري)",
      noParent: "ليس متابعة",
      questions: "الأسئلة",
      foundational: "مُدرج دائمًا",
      selectedCount: "تم تحديد {n} بالإضافة إلى الأسئلة الأساسية",
      instructions: "تعليمات لمقدم الطلب (اختياري)",
      saveDraft: "حفظ مسودة الطلب",
      draftSaved: "تم حفظ مسودة الطلب. راجع الأسئلة ثم أرسله.",
      frozenNotice: "هذه هي الأسئلة المحفوظة بالضبط مع هذا الطلب. يؤدي الإرسال إلى تثبيت صياغتها وترتيبها.",
      send: "إرسال إلى مقدم الطلب",
      sendTitle: "هل تريد إرسال هذا الطلب إلى مقدم الطلب؟",
      sendMessage: "يتم إخطار مقدم الطلب في البوابة ويمكنه الإجابة عن الأسئلة بشكل خاص. لا يمكن تغيير الأسئلة بعد إرسالها.",
      sentNotice: "تم إرسال الطلب إلى مقدم الطلب.",
      cancel: "إلغاء",
      noOpenProceeding: "لا توجد إجراءات مفتوحة في هذه القضية، لذلك لا يمكن إعداد طلبات جديدة.",
      writerOnly: "يُعِدّ الطلبات ويرسلها مسؤول القضية المعيَّن أو مسؤول المجلس أو السكرتير فقط.",
      arabicPending: "الصياغة العربية المعتمدة قيد الانتظار",
      answerReadOnly: "تظهر الردود ضمن التقارير المكتملة بعد تقديمها.",
      decisionVoting: "القرار والتصويت",
      noDecision: "لم يُسجَّل قرار في هذه الصفحة بعد.",
      readUnavailable:
        "لا يمكن عرض إصدارات القرار المحفوظة والأصوات والاعتمادات هنا بعد. يمكن التصويت على الإصدار المسجَّل في هذه الصفحة واعتماده ما دامت الصفحة مفتوحة.",
      votedOn: "موضوع التصويت",
      version: "الإصدار",
      decisionType: "نوع القرار",
      chooseType: "اختر نوع القرار.",
      grounds: "الأسباب / المسوِّغات",
      groundsRequired: "أدخل الأسباب أو المسوِّغات قبل التصويت.",
      entitlements: "استحقاقات الأطراف",
      certificate: "شهادة القرار (بعد الإتاحة الصريحة)",
      notice_only: "إخطار رسمي بالقرار فقط",
      entitlementRequired: "اختر الاستحقاق لكل طرف.",
      nullityBoth: "إعلان البطلان يمنح الشهادة للطرفين كليهما.",
      conditions: "الأطراف والشروط",
      conditionsRequired: "اذكر الأطراف والشروط صراحةً.",
      recordDecision: "تسجيل إصدار القرار",
      reviseDecision: "تسجيل إصدار معدَّل",
      revisionNotice:
        "تعديل النوع أو الأسباب يُنشئ إصدارًا جديدًا. تبقى الأصوات والاعتماد السابقة مرتبطة بالإصدار السابق ولا تنتقل إلى الجديد.",
      decisionRecorded: "تم تسجيل إصدار القرار.",
      typeLabelNotice: "لم تُتَح بعد التسميات العربية المعتمدة لأنواع القرار؛ تُعرض التسمية الإنجليزية المعتمدة.",
      votes: "أصوات أعضاء المجلس",
      rosterNotice: "يُدرج جميع أعضاء المجلس بغض النظر عن الحضور.",
      approve: "موافقة",
      deny: "رفض",
      abstain: "امتناع",
      notVoted: "لم يُسجَّل صوت",
      yourVote: "صوتك",
      recordFor: "تسجيل صوت نيابةً عن",
      chooseMember: "اختر عضوًا من المجلس",
      recordVote: "تسجيل الصوت",
      voteRecorded: "تم تسجيل الصوت.",
      tallyLine: "موافقة {approve} · رفض {deny} · امتناع {abstain} · لم يصوِّت {none}",
      sessionVotesNotice: "تُعرض فقط الأصوات المسجَّلة في هذه الصفحة. الأصوات المسجَّلة في مكان آخر محفوظة لكنها لا تظهر هنا بعد.",
      approval: "اعتماد الرئيس",
      approveDecision: "اعتماد القرار",
      recordApproval: "تسجيل اعتماد الرئيس",
      approvalTitle: "هل تريد تسجيل الاعتماد النهائي لهذا الإصدار؟",
      approvalMessage: "يرتبط الاعتماد بهذا الإصدار تحديدًا. ويجوز الاعتماد مع التصويت أو بدونه.",
      deniedWarning: "اعتماد رفض الطلب يُغلق القضية ويُرسل الإخطار الرسمي بالقرار. ولا تصدر شهادة قرار.",
      president: "الرئيس",
      choosePresident: "اختر الرئيس",
      approved: "معتمد",
      approvalRecorded: "تم تسجيل الاعتماد.",
      notApproved: "لم يُعتمد بعد",
      writerDecision: "يُدخل نوع القرار وأسبابه مسؤول القضية المعيَّن أو مسؤول المجلس أو السكرتير فقط.",
      actionFailed: "تعذر إتمام الإجراء. لم يتم تغيير أي شيء.",
      back: "رجوع",
    },
  };

  function translator(lang) {
    const own = words[lang === "ar" ? "ar" : "en"];
    const shared = base.translator(lang);
    return (key, vars) => {
      let value = own[key] ?? words.en[key];
      if (value === undefined) return shared(key, vars);
      if (vars) for (const [k, v] of Object.entries(vars)) value = value.replace(`{${k}}`, v);
      return value;
    };
  }

  function writerFor(user, caseRow) {
    return base.canManage(user) || Boolean(caseRow?.assigned_member && caseRow.assigned_member === user?.name);
  }

  // ---------- Report requests ----------

  function RequestComposer({ api, lang, record, questions, reports, onSaved, onCancel }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const proceeding = openProceeding(record);
    const [form, setForm] = R.useState({
      party: "",
      title: "",
      language: "en",
      instructions: "",
      selected: [],
      parent: "",
    });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const groups = questionGroups(questions);
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    async function save(event) {
      event.preventDefault();
      const issue = requestProblem(form, questions);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        const created = await api(`/api/cases/${encodeURIComponent(record.id)}/requests/`, {
          method: "POST",
          body: JSON.stringify(requestPayload(form, proceeding.id)),
        });
        onSaved(created.id);
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    return h(
      P.Form,
      { onSubmit: save, label: t("newRequest"), noValidate: true },
      h(
        P.FormSection,
        { title: t("newRequest") },
        h(
          P.Field,
          { label: t("subject"), required: true, error: err("chooseSubject") },
          h(P.Select, {
            value: form.party,
            disabled: pending,
            onChange: (e) => update({ party: e.target.value }),
            options: [
              { value: "", label: t("chooseSubject") },
              ...record.parties.filter((p) => p.can_receive).map((p) => ({ value: p.id, label: p.name })),
            ],
          }),
        ),
        h(P.RadioGroup, {
          label: t("method"),
          value: "intake",
          onChange: () => {},
          options: [
            { value: "intake", label: t("methodApplicant") },
            { value: "interview", label: t("methodInterview"), description: t("interviewBlocked"), disabled: true },
          ],
        }),
        h(
          P.Field,
          { label: t("title"), required: true, error: err("titleRequired") },
          h(P.Input, {
            value: form.title,
            maxLength: 200,
            disabled: pending,
            onChange: (e) => update({ title: e.target.value }),
          }),
        ),
        h(P.RadioGroup, {
          label: t("language"),
          value: form.language,
          layout: "row",
          onChange: (value) => update({ language: value }),
          options: LANGUAGES.map((value) => ({ value, label: t(value), disabled: pending })),
        }),
        problem === "arabicMissing" ? h(P.Notice, { tone: "warning" }, t("arabicMissing")) : null,
        reports.length
          ? h(
              P.Field,
              { label: t("parent") },
              h(P.Select, {
                value: form.parent,
                disabled: pending,
                onChange: (e) => update({ parent: e.target.value }),
                options: [
                  { value: "", label: t("noParent") },
                  ...reports.filter((r) => !r.restricted).map((r) => ({ value: r.id, label: `${r.title} · ${r.date}` })),
                ],
              }),
            )
          : null,
      ),
      h(
        P.FormSection,
        { title: t("questions"), description: t("selectedCount", { n: form.selected.length }) },
        ...groups.map((group) =>
          h(
            P.Fieldset,
            { key: group.category, legend: group.category },
            ...group.questions.map((q) =>
              h(P.Checkbox, {
                key: q.code,
                label: `${q.code} — ${wording(q, lang)}`,
                description: q.foundational
                  ? t("foundational")
                  : lang === "ar" && !String(q.wording_ar || "").trim()
                    ? t("arabicPending")
                    : undefined,
                checked: q.foundational || form.selected.includes(q.code),
                disabled: pending || q.foundational,
                onChange: (e) =>
                  update({
                    selected: e.target.checked
                      ? [...form.selected, q.code]
                      : form.selected.filter((code) => code !== q.code),
                  }),
              }),
            ),
          ),
        ),
        h(
          P.Field,
          { label: t("instructions") },
          h(P.Textarea, {
            rows: 4,
            value: form.instructions,
            maxLength: 10000,
            disabled: pending,
            onChange: (e) => update({ instructions: e.target.value }),
          }),
        ),
      ),
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      problem === "chooseLanguage" ? h(P.Notice, { tone: "danger" }, t(problem)) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { disabled: pending, onClick: onCancel }, t("cancel")),
        h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveDraft")),
      ),
    );
  }

  function RequestDetail({ api, lang, request, canWrite, onSent }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [confirm, setConfirm] = R.useState(false);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    async function send() {
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/requests/${encodeURIComponent(request.id)}/send/`, { method: "POST", body: "{}" });
        setConfirm(false);
        onSent();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    return h(
      P.Stack,
      { gap: "md" },
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: t("title") }, request.title),
        h(P.PropertyList.Item, { label: base.translator(lang)("statusLabel") }, h(P.Badge, { tone: request.state === "draft" ? "neutral" : request.state === "sent" ? "active" : "success" }, t(request.state))),
        h(P.PropertyList.Item, { label: t("method") }, t(request.kind)),
      ),
      h(P.Notice, { tone: "info" }, t(request.state === "draft" ? "frozenNotice" : "answerReadOnly")),
      h(
        P.Panel,
        { title: t("questions") },
        h(P.List, {
          ordered: "decimal",
          items: (request.questions || []).map((q) => ({ children: `${q.code} — ${wording(q, lang)}` })),
        }),
      ),
      request.instructions ? h(P.Panel, { title: t("instructions") }, h(P.Text, { as: "p" }, request.instructions)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      request.state === "draft" && canWrite && request.kind === "intake"
        ? h(P.Inline, null, h(P.Button, { variant: "primary", onClick: () => setConfirm(true) }, t("send")))
        : null,
      h(
        P.ConfirmDialog,
        {
          open: confirm,
          title: t("sendTitle"),
          message: t("sendMessage"),
          confirmLabel: t("send"),
          cancelLabel: t("cancel"),
          onConfirm: send,
          onCancel: () => !pending && setConfirm(false),
        },
        failure && confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function RequestsPanel({ api, lang, user, caseId, reports }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([
          api(`/api/cases/${encodeURIComponent(caseId)}/`),
          api(`/api/cases/${encodeURIComponent(caseId)}/requests/`),
          api("/api/report-questions/"),
          api("/api/cases/"),
        ]).then(([record, requests, questions, cases]) => ({
          record,
          requests: requests.items,
          questions: questions.items,
          caseRow: cases.items.find((row) => row.id === caseId),
        })),
      [caseId],
    );
    const [selected, select] = R.useState(null);
    const [composing, setComposing] = R.useState(false);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, requests, questions, caseRow } = state.data;
    const proceeding = openProceeding(record);
    const canWrite = writerFor(user, caseRow) && Boolean(proceeding);
    const chosen = requests.find((row) => row.id === selected);
    const list = h(
      P.Stack,
      { gap: "sm" },
      canWrite
        ? h(P.Inline, null, h(P.Button, { variant: "primary", size: "sm", onClick: () => { setComposing(true); select(null); setNotice(null); } }, t("newRequest")))
        : h(P.Notice, { tone: "info" }, t(proceeding ? "writerOnly" : "noOpenProceeding")),
      ...requests.map((row) =>
        h(P.Card, {
          key: row.id,
          title: row.title,
          meta: `${t(row.kind)} · ${t(row.state)}`,
          selected: row.id === selected,
          onOpen: () => {
            setComposing(false);
            setNotice(null);
            select(row.id);
          },
        }),
      ),
      !requests.length ? h(P.EmptyState, { title: t("noRequests") }) : null,
    );
    const detail = composing
      ? h(RequestComposer, {
          api,
          lang,
          record,
          questions,
          reports: reports || [],
          onCancel: () => setComposing(false),
          onSaved: (id) => {
            setComposing(false);
            setNotice("draftSaved");
            select(id);
            retry();
          },
        })
      : chosen
        ? h(RequestDetail, {
            key: chosen.id,
            api,
            lang,
            request: chosen,
            canWrite,
            onSent: () => {
              setNotice("sentNotice");
              retry();
            },
          })
        : null;
    return h(
      P.Stack,
      { gap: "md" },
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      h(P.SplitView, {
        label: t("requests"),
        firstLabel: t("requests"),
        first: list,
        second: h(
          P.ReadingPane,
          {
            label: composing ? t("newRequest") : chosen?.title || t("chooseRequest"),
            empty: h(P.EmptyState, { title: t("chooseRequest") }),
          },
          detail,
        ),
      }),
    );
  }

  // Completed reports stay in the shell's existing reader; requests are separate.
  function ReportsWorkspace({ api, lang, user, caseId, reports, renderReports }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [tab, setTab] = R.useState("reports");
    return h(P.Tabs, {
      label: t("reports"),
      value: tab,
      onChange: setTab,
      items: [
        { value: "reports", label: t("completedReports"), content: renderReports() },
        {
          value: "requests",
          label: t("requests"),
          content: h(RequestsPanel, { api, lang, user, caseId, reports }),
        },
      ],
    });
  }

  // ---------- Decision & Voting ----------

  function DecisionForm({ api, lang, record, proceeding, onRecorded, revising }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const parties = record.parties;
    const [form, setForm] = R.useState({ type: "", grounds: "", entitlements: {}, conditions: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    async function save(event) {
      event.preventDefault();
      const issue = decisionProblem(form, parties);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      const payload = decisionPayload(form, parties);
      try {
        const created = await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/decision/`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        onRecorded({ id: created.id, ...payload, votes: [], approval: null });
        setForm({ type: "", grounds: "", entitlements: {}, conditions: "" });
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    return h(
      P.Form,
      { onSubmit: save, label: t(revising ? "reviseDecision" : "recordDecision"), noValidate: true },
      h(
        P.FormSection,
        { title: t(revising ? "reviseDecision" : "recordDecision"), description: revising ? t("revisionNotice") : undefined },
        h(
          P.Field,
          { label: t("decisionType"), required: true, error: err("chooseType") },
          h(P.Select, {
            value: form.type,
            disabled: pending,
            onChange: (e) => update({ type: e.target.value }),
            options: [{ value: "", label: t("chooseType") }, ...DECISION_TYPES.map((row) => ({ value: row.code, label: row.label }))],
          }),
        ),
        lang === "ar" ? h(P.Notice, { tone: "info" }, t("typeLabelNotice")) : null,
        h(
          P.Field,
          { label: t("grounds"), required: true, error: err("groundsRequired") },
          h(P.Textarea, {
            rows: 5,
            value: form.grounds,
            maxLength: 20000,
            disabled: pending,
            onChange: (e) => update({ grounds: e.target.value }),
          }),
        ),
        needsEntitlements(form.type)
          ? h(
              P.Fieldset,
              { legend: t("entitlements") },
              ...parties.map((party) =>
                h(P.RadioGroup, {
                  key: party.id,
                  label: party.name,
                  layout: "row",
                  value: form.entitlements[party.id] || "",
                  onChange: (value) => update({ entitlements: { ...form.entitlements, [party.id]: value } }),
                  options: ENTITLEMENTS.map((value) => ({ value, label: t(value), disabled: pending })),
                }),
              ),
              problem === "entitlementRequired" || problem === "nullityBoth"
                ? h(P.Notice, { tone: "danger" }, t(problem))
                : null,
            )
          : null,
        isConditional(form.type)
          ? h(
              P.Field,
              { label: t("conditions"), required: true, error: err("conditionsRequired") },
              h(P.Textarea, {
                rows: 4,
                value: form.conditions,
                maxLength: 20000,
                disabled: pending,
                onChange: (e) => update({ conditions: e.target.value }),
              }),
            )
          : null,
      ),
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t(revising ? "reviseDecision" : "recordDecision")),
      ),
    );
  }

  function DecisionVersion({ api, lang, user, record, decision, members, readAvailable, onChange }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const roster = councilRoster(members);
    const presidentRows = base.presidents(members);
    const [vote, setVote] = R.useState("");
    const [member, setMember] = R.useState("");
    const [president, setPresident] = R.useState("");
    const [confirm, setConfirm] = R.useState(false);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    const { rows, counts } = tally(decision.votes, roster);
    const manage = canRecordFor(user);
    const isPresident = user?.role === "president";
    const partyName = (id) => record.parties.find((p) => p.id === id)?.name || id;

    async function submitVote() {
      if (!vote) return;
      setPending(true);
      setFailure(null);
      setNotice(null);
      const memberId = manage && member ? member : user.id;
      try {
        await api(`/api/decisions/${encodeURIComponent(decision.id)}/vote/`, {
          method: "POST",
          body: JSON.stringify(manage && member ? { choice: vote, member_id: member } : { choice: vote }),
        });
        onChange({
          ...decision,
          votes: [...decision.votes, { member_id: memberId, choice: vote, actor_id: user.id }],
        });
        setVote("");
        setMember("");
        setNotice("voteRecorded");
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    async function approve() {
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/decisions/${encodeURIComponent(decision.id)}/approve/`, {
          method: "POST",
          body: JSON.stringify(isPresident ? {} : { president_id: president }),
        });
        const name = isPresident ? user.name : presidentRows.find((p) => p.id === president)?.name;
        onChange({ ...decision, approval: { president: name, actor: user.name } });
        setConfirm(false);
        setNotice("approvalRecorded");
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    return h(
      P.Stack,
      { gap: "lg" },
      h(
        P.Panel,
        { title: t("votedOn"), description: decision.number ? `${t("version")} ${decision.number}` : undefined },
        h(
          P.PropertyList,
          { layout: "stacked" },
          h(P.PropertyList.Item, { label: t("decisionType") }, typeLabel(decision.type)),
          h(P.PropertyList.Item, { label: t("grounds") }, decision.grounds),
          Object.keys(decision.entitlements || {}).length
            ? h(
                P.PropertyList.Item,
                { label: t("entitlements") },
                h(P.List, {
                  variant: "bullets",
                  items: Object.entries(decision.entitlements).map(([id, value]) => ({ children: `${partyName(id)}: ${t(value)}` })),
                }),
              )
            : null,
          decision.conditions ? h(P.PropertyList.Item, { label: t("conditions") }, decision.conditions) : null,
        ),
      ),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      h(
        P.Panel,
        { title: t("votes"), description: t("rosterNotice") },
        h(
          P.Stack,
          { gap: "md" },
          h(P.Text, { as: "p", variant: "strong" }, t("tallyLine", counts)),
          !readAvailable ? h(P.Notice, { tone: "warning" }, t("sessionVotesNotice")) : null,
          h(
            P.PropertyList,
            null,
            ...rows.map((row) =>
              h(
                P.PropertyList.Item,
                { key: row.member.id, label: row.member.name || row.member.id },
                row.vote
                  ? h(P.Badge, { tone: row.vote.choice === "approve" ? "success" : row.vote.choice === "deny" ? "negative" : "neutral" }, t(row.vote.choice))
                  : h(P.Text, { variant: "secondary" }, t("notVoted")),
              ),
            ),
          ),
          h(
                P.Inline,
                { wrap: true, align: "end" },
                manage
                  ? h(
                      P.Field,
                      { label: t("recordFor") },
                      h(P.Select, {
                        value: member,
                        disabled: pending,
                        onChange: (e) => setMember(e.target.value),
                        options: [
                          { value: "", label: `${t("yourVote")} (${user.name})` },
                          ...roster.filter((m) => m.id !== user.id).map((m) => ({ value: m.id, label: m.name || m.id })),
                        ],
                      }),
                    )
                  : null,
                h(P.RadioGroup, {
                  label: manage && member ? t("recordVote") : t("yourVote"),
                  layout: "row",
                  value: vote,
                  onChange: setVote,
                  options: VOTES.map((value) => ({ value, label: t(value), disabled: pending })),
                }),
                h(P.Button, { disabled: pending || !vote, loading: pending && Boolean(vote), onClick: submitVote }, t("recordVote")),
              ),
        ),
      ),
      h(
        P.Panel,
        { title: t("approval") },
        decision.approval
          ? h(
              P.Stack,
              { gap: "sm" },
              h(P.Badge, { tone: "success" }, t("approved")),
              h(P.Text, { as: "p" }, `${t("president")}: ${decision.approval.president || ""}`),
            )
          : isPresident || manage
            ? h(
                P.Stack,
                { gap: "sm" },
                h(P.Text, { as: "p", variant: "secondary" }, t("notApproved")),
                !isPresident
                  ? presidentRows.length
                    ? h(
                        P.Field,
                        { label: t("president"), required: true },
                        h(P.Select, {
                          value: president,
                          disabled: pending,
                          onChange: (e) => setPresident(e.target.value),
                          options: [{ value: "", label: t("choosePresident") }, ...presidentRows.map((p) => ({ value: p.id, label: p.name || p.id }))],
                        }),
                      )
                    : h(P.Notice, { tone: "warning" }, base.translator(lang)("noPresident"))
                  : null,
                h(
                  P.Inline,
                  null,
                  h(
                    P.Button,
                    { variant: "primary", disabled: pending || (!isPresident && !president), onClick: () => setConfirm(true) },
                    t(isPresident ? "approveDecision" : "recordApproval"),
                  ),
                ),
              )
            : h(P.Text, { as: "p", variant: "secondary" }, t("notApproved")),
      ),
      h(
        P.ConfirmDialog,
        {
          open: confirm,
          title: t("approvalTitle"),
          message: t("approvalMessage"),
          confirmLabel: t(isPresident ? "approveDecision" : "recordApproval"),
          cancelLabel: t("cancel"),
          destructive: decision.type === "denied",
          onConfirm: approve,
          onCancel: () => !pending && setConfirm(false),
        },
        decision.type === "denied" ? h(P.Notice, { tone: "warning" }, t("deniedWarning")) : null,
        failure && confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function DecisionWorkspace({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([
          api(`/api/cases/${encodeURIComponent(caseId)}/`),
          api("/api/council/members/"),
          api("/api/cases/"),
        ]).then(async ([record, members, cases]) => {
          const proceeding = openProceeding(record);
          let versions = null;
          if (proceeding) {
            try {
              const data = await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/decision/`);
              versions = Array.isArray(data?.items) ? data.items : null;
            } catch (error) {
              // 405: the endpoint is POST-only today (dependency D8). Other errors surface.
              if (error.status !== 405) throw error;
            }
          }
          return { record, members: members.items, caseRow: cases.items.find((row) => row.id === caseId), proceeding, versions };
        }),
      [caseId],
    );
    const [local, setLocal] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, members, caseRow, proceeding, versions } = state.data;
    const readAvailable = versions !== null;
    const latestSaved = readAvailable && versions.length
      ? [...versions].sort((a, b) => b.number - a.number)[0]
      : null;
    const current = local || (latestSaved ? { votes: [], approval: null, ...latestSaved } : null);
    const canWrite = writerFor(user, caseRow) && Boolean(proceeding);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("decisionVoting")),
      !readAvailable ? h(P.Notice, { tone: "info" }, t("readUnavailable")) : null,
      !proceeding ? h(P.Notice, { tone: "info" }, t("noOpenProceeding")) : null,
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      current
        ? h(DecisionVersion, {
            key: current.id,
            api,
            lang,
            user,
            record,
            decision: current,
            members,
            readAvailable,
            onChange: setLocal,
          })
        : h(P.EmptyState, { title: t("noDecision") }),
      proceeding
        ? canWrite
          ? h(DecisionForm, {
              api,
              lang,
              record,
              proceeding,
              revising: Boolean(current),
              onRecorded: (decision) => {
                setLocal(decision);
                setNotice("decisionRecorded");
              },
            })
          : h(P.Notice, { tone: "info" }, t("writerDecision"))
        : null,
    );
  }

  Object.assign(window.CTMCouncil, {
    caseWords: words,
    caseTranslator: translator,
    DECISION_TYPES,
    typeLabel,
    needsEntitlements,
    isConditional,
    decisionProblem,
    decisionPayload,
    tally,
    councilRoster,
    questionGroups,
    foundationalCodes,
    missingArabic,
    requestProblem,
    requestPayload,
    openProceeding,
    ReportsWorkspace,
    RequestsPanel,
    DecisionWorkspace,
  });
})();
