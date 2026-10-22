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
    { code: "denied", label: "Petition Denied — No Permission to Remarry" },
  ];
  // "Decision Deferred" is a hearing outcome in the approved catalog
  // (hearing_pending_no_decree): it is labelled for display but never offered
  // for a vote or approval (acceptance review F27).
  const DISPLAY_ONLY_TYPES = [{ code: "deferred", label: "Decision Deferred — Further Investigation Required" }];
  const ENTITLEMENTS = ["certificate", "notice_only"];
  const VOTES = ["approve", "deny", "abstain"];
  const LANGUAGES = ["en", "ar", "both"];

  // ---------- Pure logic ----------

  function typeLabel(code) {
    return [...DECISION_TYPES, ...DISPLAY_ONLY_TYPES].find((row) => row.code === code)?.label || code;
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
    // Votes already recorded by a member who is no longer active stay counted and
    // visible (F19): the roster lists current members, history keeps every vote.
    const listed = new Set((roster || []).map((member) => member.id));
    for (const [memberId, vote] of Object.entries(latest))
      if (!listed.has(memberId)) rows.push({ member: { id: memberId, name: null, former: true }, vote });
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
      if (!group) groups.push((group = { category: q.category, category_ar: q.category_ar, questions: [] }));
      group.questions.push(q);
    }
    for (const group of groups) group.questions.sort((a, b) => a.code.localeCompare(b.code));
    return groups;
  }

  // Topic groups are an alternate view over the same questions; a question may sit
  // in several groups and keeps one shared selection.
  function topicGroupView(questions) {
    const latest = questionGroups(questions).flatMap((group) => group.questions);
    const groups = [];
    for (const q of latest) {
      for (const tg of q.topic_groups || []) {
        let group = groups.find((row) => row.id === tg.id);
        if (!group) groups.push((group = { id: tg.id, title: tg.title, title_ar: tg.title_ar, questions: [] }));
        group.questions.push(q);
      }
    }
    groups.sort((a, b) => String(a.id).localeCompare(String(b.id)));
    return groups;
  }

  function hasTaxonomy(questions) {
    return (questions || []).some((q) => Array.isArray(q.topic_groups));
  }

  function groupTitle(group, lang) {
    const ar = String(group.title_ar || group.category_ar || "").trim();
    return lang === "ar" && ar ? ar : group.title || group.category;
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

  // Templates usable to pre-fill a request: active, with question codes (newer servers).
  function usableTemplates(templates) {
    return (templates || []).filter((tpl) => !tpl.retired && Array.isArray(tpl.questions) && tpl.questions.length);
  }

  // Selected codes from a template, excluding foundational questions (always included)
  // and codes no longer published.
  function templateSelection(template, questions) {
    const published = new Set((questions || []).map((q) => q.code));
    const foundational = new Set(foundationalCodes(questions));
    return [...new Set((template?.questions || []).map((q) => q.code))].filter((code) => published.has(code) && !foundational.has(code));
  }

  function requestProblem(form, questions) {
    if (!form.party) return "chooseSubject";
    if (form.kind && !["intake", "interview"].includes(form.kind)) return "chooseMethod";
    if (!String(form.title || "").trim()) return "titleRequired";
    if (!LANGUAGES.includes(form.language)) return "chooseLanguage";
    if (missingArabic(form.selected, questions, form.language).length) return "arabicMissing";
    return null;
  }

  function requestPayload(form, proceedingId) {
    return {
      proceeding_id: proceedingId,
      party_id: form.party,
      kind: form.kind === "interview" ? "interview" : "intake",
      title: form.title.trim(),
      language: form.language,
      instructions: form.kind === "interview" ? "" : String(form.instructions || "").trim(),
      questions: [...form.selected],
      parent_id: form.parent || null,
    };
  }

  function interviewProblem(answers, questions) {
    const filled = (questions || []).filter((q) => String(answers?.[q.code] || "").trim());
    return filled.length ? null : "answerRequired";
  }

  function interviewPayload(answers, observations, questions) {
    const out = {};
    for (const q of questions || []) {
      const value = String(answers?.[q.code] || "").trim();
      if (value) out[q.code] = value;
    }
    return { answers: out, observations: String(observations || "").trim() };
  }

  // Ordinary reports only: Professional Assessments never join the ordinary chain,
  // even when their release makes them readable to the council.
  function ordinaryReports(reports) {
    return (reports || []).filter((r) => !r.restricted && !["medical", "psychological"].includes(r.kind));
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
      draftSaved: "The draft request was saved. Review the questions before continuing.",
      frozenNotice:
        "These are the exact questions saved with this request. Sending or starting it freezes their wording and order.",
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
      entitlements: "Spouses' entitlements",
      certificate: "Decree certificate (after explicit release)",
      notice_only: "Official decision notice only",
      entitlementRequired: "Choose an entitlement for each spouse.",
      nullityBoth: "A Declaration of Nullity entitles both spouses to the certificate.",
      conditions: "Spouses concerned and conditions",
      conditionsRequired: "State which spouse is concerned and the conditions explicitly.",
      recordDecision: "Record decision version",
      reviseDecision: "Record a revised version",
      revisionNotice:
        "A revised type or grounds creates a new version. Earlier votes and approval stay with the earlier version and are not carried over.",
      decisionRecorded: "The decision version was recorded.",
      typeLabelNotice: "Approved Arabic decision-type labels are not yet supplied; the approved English label is shown.",
      deferralNotice: "To defer for further investigation, record it in the hearing recommendations. Deferral is not voted on or approved as a decision.",
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
      currentProceeding: "Current proceeding",
      proceedingInitial: "Initial proceeding",
      proceedingReconsideration: "Appeal or reconsideration proceeding",
      whereThingsStand: "Where the case stands",
      pendingRequests: "Requests awaiting a response",
      draftRequests: "Draft requests not yet sent",
      decreeIssuedState: "Decree issued",
      communicationsLink: "Communications",
      formerMember: "Former council member",
      managerHistory: "Case manager history",
      authorizedBy: "authorized by",
      recordedByInline: "recorded by",
      noManagerHistory: "No case manager has been assigned yet.",
      templates: "Question templates",
      templatesHelp: "Reusable selections of published questions. Templates never contain applicant answers.",
      startFromTemplate: "Start from a template",
      chooseTemplate: "Select a template",
      useTemplate: "Use template",
      templateApplied: "The template's questions were selected. Foundational questions stay included.",
      templateTitle: "Name for a new personal template",
      templateTitleRequired: "Enter a name for the template.",
      saveAsTemplate: "Save selection as my template",
      templateSaved: "Your personal template was saved.",
      sharedTemplate: "Shared",
      personalTemplate: "Personal",
      publishTemplate: "Publish as shared",
      templatePublished: "A shared copy was published. The personal template is unchanged.",
      retireTemplate: "Retire",
      templateRetired: "The template was retired. Its history is kept.",
      release_none: "No signed release",
      release_signed: "Release covers council",
      release_out_of_scope: "Release out of scope",
      editNote: "Edit",
      editingNote: "Edit your note",
      editNoteHelp: "Saving keeps the earlier text in the note's history.",
      saveRevision: "Save revision",
      findingsTitle: "Council findings",
      findingsHelp: "The council's own findings. They never change what either spouse submitted.",
      noFindings: "No findings have been recorded.",
      timelineTitle: "Timeline",
      timelineHelp: "Key case events, oldest first. Every recorded action is listed in Case Audit.",
      noTimeline: "No key events are recorded yet.",
      petitionTitle: "Petition",
      petitionReadOnly: "Each spouse's formal submission is shown as submitted. Council notes below are separate and never change it.",
      petition: "Petition",
      noPetitions: "No submitted petition is available for this case.",
      internalNotes: "Internal notes",
      internalNotesHelp: "Council only. Never shown to applicants.",
      note: "Note",
      noNotes: "No internal notes yet.",
      addNote: "Add an internal note",
      saveNote: "Save note",
      noteSaved: "The note was saved.",
      noteRequired: "Write the note before saving.",
      partiesTitle: "Spouses",
      ctmReference: "CTM reference",
      portalAccount: "Portal account",
      registered: "Registered",
      notRegistered: "Not registered",
      noParties: "No spouses are recorded.",
      addParty: "Add the other spouse",
      addPartyHelp: "Record the other spouse by name and email. They are linked automatically after registering with a matching verified email. No account is created for them and no invitation acceptance is needed.",
      firstName: "First name",
      lastName: "Last name",
      email: "Email",
      firstRequired: "Enter the first name.",
      lastRequired: "Enter the last name.",
      emailInvalid: "Enter a valid email address.",
      partyAdded: "The other spouse was recorded. They are linked once they register with this verified email.",
      hearingsTitle: "Hearings",
      hearingsScope: "Agenda appearances of this case in recent council sessions.",
      noHearings: "This case has not been placed on a council session agenda.",
      assessments: "Professional Assessments",
      assessmentPrivacy: "Medical and psychological reports are kept separate from ordinary documents. Their contents are shown only when the person's signed release covers the council, and they are never sent to external AI processing.",
      releaseTextPending: "The institution's signed-release wording has not been approved yet, so applicants cannot sign releases and report contents stay hidden.",
      assessmentRequests: "Assessment requests",
      newAssessment: "New assessment request",
      assessmentKind: "Assessment type",
      chooseAssessmentKind: "Choose medical or psychological.",
      assessmentInstructions: "Instructions to the person, including any recommended doctors (optional)",
      assessmentInstructionsHelp: "Recommended doctors are optional; the person may choose another qualified provider.",
      assessmentDraftSaved: "The assessment request was saved as a draft.",
      assessmentSent: "The assessment request was sent.",
      noAssessments: "No assessment requests yet.",
      assessmentReports: "Submitted assessments",
      noAssessmentReports: "No assessments have been submitted.",
      restrictedAssessment: "Submitted assessment — contents hidden",
      restrictedAssessmentHelp: "A signed release covering the council is missing or out of scope.",
      sendAssessmentTitle: "Send this assessment request?",
      sendAssessmentMessage: "The person is notified privately. A signed release is required before any report contents become visible to the council.",
      caseAudit: "Case Audit",
      searchAudit: "Search audit events",
      auditCount: "{n} events",
      noAudit: "No audit events match.",
      systemActor: "System",
      otherAccount: "Applicant or former council account",
      callLog: "Call records",
      callLogHelp: "Manual records of phone calls. CTM does not place or record calls.",
      noCalls: "No calls have been recorded.",
      recordCall: "Record a call",
      callParty: "Person called",
      chooseCallParty: "Select who was called.",
      callTime: "When the call took place",
      callTimeRequired: "Enter when the call took place.",
      callTimeFuture: "The call time cannot be in the future.",
      callOutcome: "Outcome",
      callOutcomeRequired: "Enter the outcome of the call.",
      callNotes: "Notes (optional)",
      callRecorded: "The call was recorded.",
      recordedAt: "Recorded",
      interviewHelp: "Record the applicant's answers yourself. The applicant is not notified and cannot see this interview.",
      chooseMethod: "Choose how the questions are answered.",
      questionView: "Show questions",
      byCategory: "By question category",
      byTopicGroup: "By topic group",
      startInterview: "Start interview",
      startInterviewTitle: "Start this interview?",
      startInterviewMessage: "The question list is frozen. The applicant is not notified.",
      interviewStarted: "The interview was started. Record the answers when ready.",
      recordInterview: "Record interview answers",
      interviewRecordHelp: "Enter what the applicant said for each question. Leave a question empty if it was not asked.",
      internalObservations: "Internal observations (council only)",
      internalObservationsHelp: "Kept separate from the applicant's answers and never shown to applicants.",
      saveInterview: "Save interview report",
      answerRequired: "Enter at least one answer before saving.",
      interviewRecorded: "The interview report was saved under Completed reports.",
      preparedBy: "Prepared by",
      createdAt: "Created",
      sentAt: "Sent",
      startedAt: "Started",
      followUpYes: "Yes",
      recordedBy: "Recorded by",
      earlierVersions: "Earlier versions",
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
      draftSaved: "تم حفظ مسودة الطلب. راجع الأسئلة قبل المتابعة.",
      frozenNotice: "هذه هي الأسئلة المحفوظة بالضبط مع هذا الطلب. يؤدي إرساله أو بدؤه إلى تثبيت صياغتها وترتيبها.",
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
      entitlements: "استحقاقات الزوجين",
      certificate: "شهادة القرار (بعد الإتاحة الصريحة)",
      notice_only: "إخطار رسمي بالقرار فقط",
      entitlementRequired: "اختر الاستحقاق لكل من الزوجين.",
      nullityBoth: "إعلان البطلان يمنح الشهادة للزوجين كليهما.",
      conditions: "الزوج المعني والشروط",
      conditionsRequired: "اذكر الزوج المعني والشروط صراحةً.",
      recordDecision: "تسجيل إصدار القرار",
      reviseDecision: "تسجيل إصدار معدَّل",
      revisionNotice:
        "تعديل النوع أو الأسباب يُنشئ إصدارًا جديدًا. تبقى الأصوات والاعتماد السابقة مرتبطة بالإصدار السابق ولا تنتقل إلى الجديد.",
      decisionRecorded: "تم تسجيل إصدار القرار.",
      typeLabelNotice: "لم تُتَح بعد التسميات العربية المعتمدة لأنواع القرار؛ تُعرض التسمية الإنجليزية المعتمدة.",
      deferralNotice: "لتأجيل القرار لمزيد من التحقيق، سجّل ذلك في توصيات الجلسة. لا يُصوَّت على التأجيل ولا يُعتمد كقرار.",
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
      currentProceeding: "الإجراء الحالي",
      proceedingInitial: "الإجراء الأول",
      proceedingReconsideration: "إجراء استئناف أو إعادة نظر",
      whereThingsStand: "وضع القضية الحالي",
      pendingRequests: "طلبات في انتظار الرد",
      draftRequests: "مسودات طلبات لم تُرسل",
      decreeIssuedState: "صدرت الشهادة",
      communicationsLink: "المراسلات",
      formerMember: "عضو سابق في المجلس",
      managerHistory: "سجل مسؤولي القضية",
      authorizedBy: "باعتماد",
      recordedByInline: "وسجّله",
      noManagerHistory: "لم يُعيَّن مسؤول للقضية بعد.",
      templates: "نماذج الأسئلة",
      templatesHelp: "مجموعات قابلة لإعادة الاستخدام من الأسئلة المنشورة. ولا تحتوي النماذج أبدًا على إجابات مقدمي الطلبات.",
      startFromTemplate: "البدء من نموذج",
      chooseTemplate: "اختر نموذجًا",
      useTemplate: "استخدام النموذج",
      templateApplied: "تم تحديد أسئلة النموذج. وتبقى الأسئلة الأساسية مُدرجة.",
      templateTitle: "اسم نموذج شخصي جديد",
      templateTitleRequired: "أدخل اسمًا للنموذج.",
      saveAsTemplate: "حفظ التحديد كنموذج خاص بي",
      templateSaved: "تم حفظ نموذجك الشخصي.",
      sharedTemplate: "مشترك",
      personalTemplate: "شخصي",
      publishTemplate: "نشر كنموذج مشترك",
      templatePublished: "نُشرت نسخة مشتركة. ولم يتغير النموذج الشخصي.",
      retireTemplate: "إيقاف",
      templateRetired: "تم إيقاف النموذج مع الاحتفاظ بسجله.",
      release_none: "لا يوجد إذن موقَّع",
      release_signed: "الإذن يشمل المجلس",
      release_out_of_scope: "الإذن خارج النطاق",
      editNote: "تعديل",
      editingNote: "تعديل ملاحظتك",
      editNoteHelp: "يُحتفظ بالنص السابق في سجل الملاحظة عند الحفظ.",
      saveRevision: "حفظ التعديل",
      findingsTitle: "نتائج المجلس",
      findingsHelp: "نتائج المجلس الخاصة به. ولا تغيّر أبدًا ما قدّمه أي من الزوجين.",
      noFindings: "لم تُسجَّل أي نتائج.",
      timelineTitle: "التسلسل الزمني",
      timelineHelp: "الأحداث الرئيسية للقضية من الأقدم إلى الأحدث. وتُعرض جميع الإجراءات المسجلة في سجل تدقيق القضية.",
      noTimeline: "لم تُسجَّل أحداث رئيسية بعد.",
      petitionTitle: "الطلب",
      petitionReadOnly: "يُعرض ما قدّمه كل من الزوجين كما قُدِّم. وملاحظات المجلس أدناه منفصلة ولا تغيّره أبدًا.",
      petition: "الطلب",
      noPetitions: "لا يوجد طلب مقدَّم متاح لهذه القضية.",
      internalNotes: "ملاحظات داخلية",
      internalNotesHelp: "للمجلس فقط. لا تُعرض أبدًا على مقدمي الطلبات.",
      note: "ملاحظة",
      noNotes: "لا توجد ملاحظات داخلية بعد.",
      addNote: "إضافة ملاحظة داخلية",
      saveNote: "حفظ الملاحظة",
      noteSaved: "تم حفظ الملاحظة.",
      noteRequired: "اكتب الملاحظة قبل الحفظ.",
      partiesTitle: "الزوجان",
      ctmReference: "مرجع النظام",
      portalAccount: "حساب البوابة",
      registered: "مسجَّل",
      notRegistered: "غير مسجَّل",
      noParties: "لا يوجد زوجان مسجلان.",
      addParty: "إضافة الزوج الآخر",
      addPartyHelp: "سجّل الزوج الآخر بالاسم والبريد الإلكتروني. ويُربط تلقائيًا بعد تسجيله ببريد إلكتروني مطابق ومُتحقَّق منه. لا يُنشأ له حساب ولا يلزم قبول دعوة.",
      firstName: "الاسم الأول",
      lastName: "اسم العائلة",
      email: "البريد الإلكتروني",
      firstRequired: "أدخل الاسم الأول.",
      lastRequired: "أدخل اسم العائلة.",
      emailInvalid: "أدخل بريدًا إلكترونيًا صحيحًا.",
      partyAdded: "تم تسجيل الزوج الآخر. ويُربط بمجرد تسجيله بهذا البريد المُتحقَّق منه.",
      hearingsTitle: "الجلسات",
      hearingsScope: "ظهور هذه القضية في جداول أعمال جلسات المجلس الأخيرة.",
      noHearings: "لم تُدرج هذه القضية في جدول أعمال أي جلسة مجلس.",
      assessments: "التقييمات المهنية",
      assessmentPrivacy: "تُحفظ التقارير الطبية والنفسية منفصلة عن المستندات العادية. ولا تُعرض محتوياتها إلا إذا شمل الإذن الموقَّع من صاحبها المجلس، ولا تُرسل أبدًا إلى معالجة خارجية بالذكاء الاصطناعي.",
      releaseTextPending: "لم تُعتمد بعد صياغة الإذن الموقَّع من الجهة، لذلك لا يمكن لمقدمي الطلبات توقيع الإذن وتبقى محتويات التقارير مخفية.",
      assessmentRequests: "طلبات التقييم",
      newAssessment: "طلب تقييم جديد",
      assessmentKind: "نوع التقييم",
      chooseAssessmentKind: "اختر طبيًا أو نفسيًا.",
      assessmentInstructions: "تعليمات للشخص، بما في ذلك الأطباء المقترحون (اختياري)",
      assessmentInstructionsHelp: "اقتراح الأطباء اختياري؛ ويجوز للشخص اختيار مقدِّم خدمة مؤهل آخر.",
      assessmentDraftSaved: "تم حفظ طلب التقييم كمسودة.",
      assessmentSent: "تم إرسال طلب التقييم.",
      noAssessments: "لا توجد طلبات تقييم بعد.",
      assessmentReports: "التقييمات المقدَّمة",
      noAssessmentReports: "لم تُقدَّم أي تقييمات.",
      restrictedAssessment: "تقييم مقدَّم — المحتويات مخفية",
      restrictedAssessmentHelp: "الإذن الموقَّع الذي يشمل المجلس غير موجود أو خارج النطاق.",
      sendAssessmentTitle: "هل تريد إرسال طلب التقييم هذا؟",
      sendAssessmentMessage: "يُخطَر الشخص بشكل خاص. ويلزم إذن موقَّع قبل أن تظهر أي محتويات للتقرير للمجلس.",
      caseAudit: "سجل تدقيق القضية",
      searchAudit: "البحث في أحداث التدقيق",
      auditCount: "{n} حدث",
      noAudit: "لا توجد أحداث تدقيق مطابقة.",
      systemActor: "النظام",
      otherAccount: "مقدم طلب أو عضو مجلس سابق",
      callLog: "سجل المكالمات",
      callLogHelp: "سجلات يدوية للمكالمات الهاتفية. لا يُجري النظام المكالمات ولا يسجّلها.",
      noCalls: "لم تُسجَّل أي مكالمات.",
      recordCall: "تسجيل مكالمة",
      callParty: "الشخص الذي تم الاتصال به",
      chooseCallParty: "اختر من تم الاتصال به.",
      callTime: "وقت إجراء المكالمة",
      callTimeRequired: "أدخل وقت إجراء المكالمة.",
      callTimeFuture: "لا يمكن أن يكون وقت المكالمة في المستقبل.",
      callOutcome: "النتيجة",
      callOutcomeRequired: "أدخل نتيجة المكالمة.",
      callNotes: "ملاحظات (اختياري)",
      callRecorded: "تم تسجيل المكالمة.",
      recordedAt: "تاريخ التسجيل",
      interviewHelp: "سجّل إجابات مقدم الطلب بنفسك. لا يتم إخطار مقدم الطلب ولا يمكنه رؤية هذه المقابلة.",
      chooseMethod: "اختر طريقة الإجابة عن الأسئلة.",
      questionView: "عرض الأسئلة",
      byCategory: "حسب فئة الأسئلة",
      byTopicGroup: "حسب مجموعة الموضوعات",
      startInterview: "بدء المقابلة",
      startInterviewTitle: "هل تريد بدء هذه المقابلة؟",
      startInterviewMessage: "يتم تثبيت قائمة الأسئلة. ولا يتم إخطار مقدم الطلب.",
      interviewStarted: "بدأت المقابلة. سجّل الإجابات عندما تكون جاهزًا.",
      recordInterview: "تسجيل إجابات المقابلة",
      interviewRecordHelp: "أدخل ما قاله مقدم الطلب عن كل سؤال. اترك السؤال فارغًا إذا لم يُطرح.",
      internalObservations: "ملاحظات داخلية (للمجلس فقط)",
      internalObservationsHelp: "تُحفظ منفصلة عن إجابات مقدم الطلب ولا تُعرض على مقدمي الطلبات أبدًا.",
      saveInterview: "حفظ تقرير المقابلة",
      answerRequired: "أدخل إجابة واحدة على الأقل قبل الحفظ.",
      interviewRecorded: "تم حفظ تقرير المقابلة ضمن التقارير المكتملة.",
      preparedBy: "أعدّه",
      createdAt: "تاريخ الإنشاء",
      sentAt: "تاريخ الإرسال",
      startedAt: "تاريخ البدء",
      followUpYes: "نعم",
      recordedBy: "سجّله",
      earlierVersions: "الإصدارات السابقة",
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

  function writerFor(user, caseRow, record) {
    if (base.canManage(user)) return true;
    if (record && record.assigned_member_id !== undefined)
      return Boolean(user && record.assigned_member_id === user.id);
    // Older servers: display-only fallback on the shown manager name; the server decides.
    const shown = caseRow?.assigned_member ?? record?.assigned_member ?? null;
    return Boolean(shown && shown === user?.name);
  }

  // Older servers omit assigned_member_id from case detail; add the shown manager
  // name from the case list so the display fallback above can work.
  async function withAssignee(api, record) {
    if (!record || record.assigned_member_id !== undefined || record.assigned_member !== undefined) return record;
    const list = await api("/api/cases/");
    const row = (list.items || []).find((c) => c.id === record.id);
    return { ...record, assigned_member: row ? row.assigned_member : null };
  }

  // ---------- Report requests ----------

  function TemplateTools({ api, lang, templates, questions, selected, onUse, onChanged }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const usable = usableTemplates(templates);
    const [choice, setChoice] = R.useState("");
    const [title, setTitle] = R.useState("");
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    async function act(fn, key) {
      setPending(true);
      setFailure(null);
      setNotice(null);
      try {
        await fn();
        setNotice(key);
        onChanged();
        return true;
      } catch (error) {
        setFailure(base.serverMessage(error, t));
        return false;
      } finally {
        setPending(false);
      }
    }
    const save = () => {
      if (!title.trim()) {
        setFailure(t("templateTitleRequired"));
        return;
      }
      act(() => api("/api/templates/", { method: "POST", body: JSON.stringify({ title: title.trim(), questions: selected }) }), "templateSaved").then((ok) => ok && setTitle(""));
    };
    const supportsQuestions = (templates || []).every((tpl) => Array.isArray(tpl.questions));
    return h(
      P.Panel,
      { icon: "doc-text", title: t("templates"), description: t("templatesHelp"), collapsible: true, defaultExpanded: false },
      h(
        P.Stack,
        { gap: "md" },
        supportsQuestions && usable.length
          ? h(
              P.Inline,
              { wrap: true, align: "end" },
              h(
                P.Field,
                { label: t("startFromTemplate") },
                h(P.Select, {
                  value: choice,
                  disabled: pending,
                  onChange: (e) => setChoice(e.target.value),
                  options: [
                    { value: "", label: t("chooseTemplate") },
                    ...usable.map((tpl) => ({ value: tpl.id, label: `${tpl.title}${tpl.shared ? " · " + t("sharedTemplate") : ""}` })),
                  ],
                }),
              ),
              h(
                P.Button,
                {
                  disabled: pending || !choice,
                  onClick: () => {
                    onUse(templateSelection(usable.find((tpl) => tpl.id === choice), questions));
                    setNotice("templateApplied");
                  },
                },
                t("useTemplate"),
              ),
            )
          : null,
        h(
          P.Inline,
          { wrap: true, align: "end" },
          h(P.Field, { label: t("templateTitle") }, h(P.Input, { value: title, maxLength: 200, disabled: pending, onChange: (e) => setTitle(e.target.value) })),
          h(P.Button, { disabled: pending || !selected.length, onClick: save }, t("saveAsTemplate")),
        ),
        ...(templates || [])
          .filter((tpl) => !tpl.retired && (tpl.can_publish || tpl.can_retire))
          .map((tpl) =>
            h(
              P.Inline,
              { key: tpl.id, justify: "between", wrap: true },
              h(P.Text, null, `${tpl.title}${tpl.shared ? " · " + t("sharedTemplate") : " · " + t("personalTemplate")}`),
              h(
                P.Inline,
                { gap: "xs" },
                tpl.can_publish
                  ? h(P.Button, { size: "xs", disabled: pending, onClick: () => act(() => api(`/api/templates/${encodeURIComponent(tpl.id)}/publish/`, { method: "POST", body: "{}" }), "templatePublished") }, t("publishTemplate"))
                  : null,
                tpl.can_retire
                  ? h(P.Button, { size: "xs", variant: "danger-secondary", disabled: pending, onClick: () => act(() => api(`/api/templates/${encodeURIComponent(tpl.id)}/retire/`, { method: "POST", body: "{}" }), "templateRetired") }, t("retireTemplate"))
                  : null,
              ),
            ),
          ),
        notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function RequestComposer({ api, lang, record, questions, reports, templates, onTemplatesChanged, onSaved, onCancel }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const proceeding = openProceeding(record);
    const [form, setForm] = R.useState({
      kind: "intake",
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
    const taxonomy = hasTaxonomy(questions);
    const [view, setView] = R.useState("category");
    const groups = view === "topic" && taxonomy ? topicGroupView(questions) : questionGroups(questions);
    // The in-person interview path is offered only by servers that no longer notify
    // the applicant when an interview starts (shipped with the question taxonomy).
    const interviewReady = taxonomy;
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
              ...record.parties
                .filter((p) => p.can_receive || (form.kind === "interview" && interviewReady))
                .map((p) => ({ value: p.id, label: p.name })),
            ],
          }),
        ),
        h(P.RadioGroup, {
          label: t("method"),
          value: form.kind,
          onChange: (value) => update({ kind: value }),
          options: [
            { value: "intake", label: t("methodApplicant"), disabled: pending },
            interviewReady
              ? { value: "interview", label: t("methodInterview"), description: t("interviewHelp"), disabled: pending }
              : { value: "interview", label: t("methodInterview"), description: t("interviewBlocked"), disabled: true },
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
        ordinaryReports(reports).length
          ? h(
              P.Field,
              { label: t("parent") },
              h(P.Select, {
                value: form.parent,
                disabled: pending,
                onChange: (e) => update({ parent: e.target.value }),
                options: [
                  { value: "", label: t("noParent") },
                  ...ordinaryReports(reports).map((r) => ({ value: r.id, label: `${r.title} · ${r.date}` })),
                ],
              }),
            )
          : null,
      ),
      h(
        P.FormSection,
        { title: t("questions"), description: t("selectedCount", { n: form.selected.length }) },
        h(TemplateTools, {
          api,
          lang,
          templates,
          questions,
          selected: form.selected,
          onUse: (codes) => update({ selected: codes }),
          onChanged: onTemplatesChanged || (() => {}),
        }),
        taxonomy
          ? h(P.RadioGroup, {
              label: t("questionView"),
              layout: "row",
              value: view,
              onChange: setView,
              options: [
                { value: "category", label: t("byCategory") },
                { value: "topic", label: t("byTopicGroup") },
              ],
            })
          : null,
        ...groups.map((group) =>
          h(
            P.Fieldset,
            { key: group.id || group.category, legend: groupTitle(group, lang) },
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
        form.kind === "interview"
          ? null
          : h(
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

  function InterviewForm({ api, lang, request, onRecorded, onCancel }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [answers, setAnswers] = R.useState({});
    const [observations, setObservations] = R.useState("");
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    async function save(event) {
      event.preventDefault();
      const issue = interviewProblem(answers, request.questions);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        const report = await api(`/api/requests/${encodeURIComponent(request.id)}/complete/`, {
          method: "POST",
          body: JSON.stringify(interviewPayload(answers, observations, request.questions)),
        });
        // Audio captured during the interview moves to the saved report, where it is submitted.
        if (report && report.id && base.recordingStore) {
          try {
            await base.recordingStore().move(`request:${request.id}`, `report:${report.id}`);
          } catch {
            /* no local recording */
          }
        }
        onRecorded();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    return h(
      P.Form,
      { onSubmit: save, label: t("recordInterview"), noValidate: true },
      base.ReportRecorder
        ? h(base.ReportRecorder, { api, lang, storageKey: `request:${request.id}`, reportId: null, caseId: null, canSubmit: false, captureOnly: true })
        : null,
      h(
        P.FormSection,
        { title: t("recordInterview"), description: t("interviewRecordHelp") },
        ...(request.questions || []).map((q) =>
          h(
            P.Field,
            { key: q.code, label: `${q.code} — ${wording(q, lang)}` },
            h(P.Textarea, {
              rows: 3,
              autoGrow: true,
              value: answers[q.code] || "",
              maxLength: 50000,
              disabled: pending,
              onChange: (e) => {
                setAnswers((old) => ({ ...old, [q.code]: e.target.value }));
                setProblem(null);
              },
            }),
          ),
        ),
        h(
          P.Field,
          { label: t("internalObservations"), description: t("internalObservationsHelp") },
          h(P.Textarea, { rows: 4, autoGrow: true, value: observations, maxLength: 50000, disabled: pending, onChange: (e) => setObservations(e.target.value) }),
        ),
      ),
      problem ? h(P.Notice, { tone: "danger" }, t(problem)) : null,
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { disabled: pending, onClick: onCancel }, t("cancel")),
        h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveInterview")),
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
    const [recording, setRecording] = R.useState(false);
    const interview = request.kind === "interview";
    async function send() {
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/requests/${encodeURIComponent(request.id)}/send/`, { method: "POST", body: "{}" });
        setConfirm(false);
        onSent(interview ? "interviewStarted" : "sentNotice");
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
        request.subject_name ? h(P.PropertyList.Item, { label: t("subject") }, request.subject_name) : null,
        request.language ? h(P.PropertyList.Item, { label: t("language") }, t(request.language)) : null,
        request.author ? h(P.PropertyList.Item, { label: t("preparedBy") }, request.author) : null,
        request.created_at ? h(P.PropertyList.Item, { label: t("createdAt"), data: true }, base.formatWhen(request.created_at, lang)) : null,
        request.sent_at ? h(P.PropertyList.Item, { label: t(interview ? "startedAt" : "sentAt"), data: true }, base.formatWhen(request.sent_at, lang)) : null,
        request.parent_report_id ? h(P.PropertyList.Item, { label: t("parent") }, t("followUpYes")) : null,
      ),
      h(P.Notice, { tone: "info" }, t(request.state === "draft" ? "frozenNotice" : "answerReadOnly")),
      h(
        P.Panel,
        { icon: "doc-text", title: t("questions") },
        h(P.List, {
          ordered: "decimal",
          items: (request.questions || []).map((q) => ({ children: `${q.code} — ${wording(q, lang)}` })),
        }),
      ),
      request.instructions ? h(P.Panel, { icon: "doc-text", title: t("instructions") }, h(P.Text, { as: "p" }, request.instructions)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      request.state === "draft" && canWrite && (request.kind === "intake" || interview)
        ? h(P.Inline, null, h(P.Button, { variant: "primary", onClick: () => setConfirm(true) }, t(interview ? "startInterview" : "send")))
        : null,
      request.state === "sent" && interview && canWrite && !recording
        ? h(P.Inline, null, h(P.Button, { variant: "primary", onClick: () => setRecording(true) }, t("recordInterview")))
        : null,
      recording
        ? h(InterviewForm, {
            api,
            lang,
            request,
            onCancel: () => setRecording(false),
            onRecorded: () => {
              setRecording(false);
              onSent("interviewRecorded");
            },
          })
        : null,
      h(
        P.ConfirmDialog,
        {
          open: confirm,
          title: t(interview ? "startInterviewTitle" : "sendTitle"),
          message: t(interview ? "startInterviewMessage" : "sendMessage"),
          confirmLabel: t(interview ? "startInterview" : "send"),
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
          api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)),
          api(`/api/cases/${encodeURIComponent(caseId)}/requests/`),
          api("/api/report-questions/"),
          api("/api/cases/"),
          api("/api/templates/"),
        ]).then(([record, requests, questions, cases, templates]) => ({
          record,
          templates: templates.items || [],
          // Professional Assessments have their own section; never list them with ordinary reports.
          requests: requests.items.filter((row) => !["medical", "psychological"].includes(row.kind)),
          questions: questions.items,
          caseRow: cases.items.find((row) => row.id === caseId),
        })),
      [caseId],
    );
    const [selected, select] = R.useState(null);
    const [composing, setComposing] = R.useState(false);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, requests, questions, caseRow } = state.data;
    const proceeding = openProceeding(record);
    const canWrite = writerFor(user, caseRow, record) && Boolean(proceeding);
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
          meta: [t(row.kind), base.isolate(row.subject_name), t(row.state)].filter(Boolean).join(" · "),
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
          templates: state.data.templates,
          onTemplatesChanged: retry,
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
            onSent: (key) => {
              setNotice(key || "sentNotice");
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
        {
          value: "reports",
          label: t("completedReports"),
          content: base.ReportsReader ? h(base.ReportsReader, { api, lang, user, caseId, reports }) : renderReports(),
        },
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
        h(P.Text, { variant: "secondary" }, t("deferralNotice")),
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
    const canVote = decision.can_vote !== false;
    const canApprove = typeof decision.can_approve === "boolean" ? decision.can_approve : isPresident || manage;
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
        onChange(
          {
            ...decision,
            votes: [...(decision.votes || []).filter((v) => v.member_id !== memberId), { member_id: memberId, choice: vote, actor_id: user.id }],
          },
          true,
        );
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
        onChange({ ...decision, approval: { president: name, actor: user.name } }, true);
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
        { icon: "doc-text", title: t("votedOn"), description: decision.number ? `${t("version")} ${decision.number}` : undefined },
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
          decision.actor ? h(P.PropertyList.Item, { label: t("recordedBy") }, `${decision.actor} · ${base.formatWhen(decision.timestamp, lang)}`) : null,
        ),
      ),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      h(
        P.Panel,
        { icon: "doc-text", title: t("votes"), description: t("rosterNotice") },
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
                { key: row.member.id, label: row.member.former ? t("formerMember") : row.member.name || row.member.id },
                row.vote
                  ? h(P.Badge, { tone: row.vote.choice === "approve" ? "success" : row.vote.choice === "deny" ? "negative" : "neutral" }, t(row.vote.choice))
                  : h(P.Text, { variant: "secondary" }, t("notVoted")),
              ),
            ),
          ),
          !canVote
            ? null
            : h(
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
        { icon: "doc-text", title: t("approval") },
        decision.approval
          ? h(
              P.Stack,
              { gap: "sm" },
              h(P.Badge, { tone: "success" }, t("approved")),
              h(P.Text, { as: "p" }, `${t("president")}: ${decision.approval.president || ""}`),
              decision.approval.actor && decision.approval.actor !== decision.approval.president
                ? h(P.Text, { as: "p", variant: "secondary" }, `${t("recordedBy")}: ${decision.approval.actor}${decision.approval.timestamp ? " · " + base.formatWhen(decision.approval.timestamp, lang) : ""}`)
                : null,
            )
          : canApprove
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
          api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)),
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
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, members, caseRow, proceeding, versions } = state.data;
    const readAvailable = versions !== null;
    const noticeKey = readAvailable ? null : "readUnavailable";
    const latestSaved = readAvailable && versions.length
      ? [...versions].sort((a, b) => b.number - a.number)[0]
      : null;
    const current = local || (latestSaved ? { votes: [], approval: null, ...latestSaved } : null);
    const earlier = readAvailable ? [...versions].sort((a, b) => b.number - a.number).slice(1) : [];
    const canWrite = writerFor(user, caseRow, record) && Boolean(proceeding);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("decisionVoting")),
      noticeKey ? h(P.Notice, { tone: "info" }, t(noticeKey)) : null,
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
            // With the server read available, reload the saved record after each action.
            onChange: (next, saved) => (readAvailable && saved ? retry() : setLocal(next)),
          })
        : h(P.EmptyState, { title: t("noDecision") }),
      earlier.length
        ? h(
            P.Panel,
            { icon: "doc-text", title: t("earlierVersions"), collapsible: true, defaultExpanded: false },
            h(P.List, {
              variant: "bullets",
              items: earlier.map((v) => ({
                children: `${t("version")} ${v.number} · ${typeLabel(v.type)} · ${v.actor || ""} · ${base.formatWhen(v.timestamp, lang)}${v.approval ? " · " + t("approved") : ""}`,
              })),
            }),
          )
        : null,
      proceeding
        ? canWrite
          ? h(DecisionForm, {
              api,
              lang,
              record,
              proceeding,
              revising: Boolean(current),
              onRecorded: (decision) => {
                setNotice("decisionRecorded");
                if (readAvailable) {
                  setLocal(null);
                  retry();
                } else setLocal(decision);
              },
            })
          : h(P.Notice, { tone: "info" }, t("writerDecision"))
        : null,
    );
  }

  // ---------- Case audit and manual call records ----------

  const AUDIT_LABELS = {
    en: {
      agenda_placed: "Placed on a council session agenda",
      session_created: "Council session created",
      session_closed: "Council session closed",
      agenda_carryover_already_placed: "Carryover skipped: already on the next agenda",
      answers_saved: "Application answers saved",
      appeal_accept: "Appeal accepted",
      appeal_decline: "Appeal declined",
      appeal_added: "Appeal information added",
      application_submitted: "Application submitted",
      attendance_recorded: "Attendance recorded",
      call_recorded: "Call recorded",
      case_assigned: "Case manager assigned",
      case_heard: "Case presented at hearing",
      completeness_accept: "Application accepted for review",
      completeness_reject: "Application returned for correction",
      decision_recorded: "Decision version recorded",
      decree_access_release: "Decree certificate released",
      decree_access_withdraw: "Decree certificate access withdrawn",
      decree_issued: "Decree issued",
      fee_waived: "Fee waived",
      file_uploaded: "File uploaded",
      filing_withdrawn: "Filing withdrawn",
      finding_saved: "Finding saved",
      hearing_deferred_presenter_absent: "Hearing deferred: presenter absent",
      hearing_outcome_saved: "Hearing recommendations saved",
      message_sent: "Message sent",
      note_saved: "Internal note saved",
      party_linked: "Spouse linked",
      pending_party_added: "Other spouse added",
      president_approved: "President's approval recorded",
      president_signature_recorded: "President's signature recorded",
      report_request_created: "Report request prepared",
      report_request_sent: "Report request sent or started",
      report_revised: "Report revised",
      report_submitted: "Report submitted",
      testimony_scheduled: "Testimony scheduled",
      vote_recorded: "Vote recorded",
      petition_denied: "Petition denied: case closed",
      petitions_withdrawn: "Petitions withdrawn: case closed",
      assignment_agenda_completed: "New-case assignment completed at session",
    },
    ar: {
      agenda_placed: "أُدرجت في جدول أعمال جلسة المجلس",
      session_created: "أُنشئت جلسة المجلس",
      session_closed: "أُغلقت جلسة المجلس",
      agenda_carryover_already_placed: "لم تُنقل: مُدرجة بالفعل في جدول الجلسة التالية",
      answers_saved: "حُفظت إجابات الطلب",
      appeal_accept: "قُبل الاستئناف",
      appeal_decline: "رُفض الاستئناف",
      appeal_added: "أُضيفت معلومات إلى الاستئناف",
      application_submitted: "قُدِّم الطلب",
      attendance_recorded: "سُجِّل الحضور",
      call_recorded: "سُجِّلت مكالمة",
      case_assigned: "عُيِّن مسؤول القضية",
      case_heard: "عُرضت القضية في الجلسة",
      completeness_accept: "قُبل الطلب بعد مراجعة الاستيفاء",
      completeness_reject: "أُعيد الطلب للتصحيح",
      decision_recorded: "سُجِّل إصدار القرار",
      decree_access_release: "أُتيحت شهادة القرار",
      decree_access_withdraw: "سُحبت إتاحة شهادة القرار",
      decree_issued: "صدرت الشهادة",
      fee_waived: "أُعفي من الرسوم",
      file_uploaded: "رُفع ملف",
      filing_withdrawn: "سُحب الطلب",
      finding_saved: "حُفظت نتيجة تحقيق",
      hearing_deferred_presenter_absent: "أُجِّلت الجلسة لغياب المقدِّم",
      hearing_outcome_saved: "حُفظت توصيات الجلسة",
      message_sent: "أُرسلت رسالة",
      note_saved: "حُفظت ملاحظة داخلية",
      party_linked: "رُبط أحد الزوجين",
      pending_party_added: "أُضيف الزوج الآخر",
      president_approved: "سُجِّل اعتماد الرئيس",
      president_signature_recorded: "سُجِّل توقيع الرئيس",
      report_request_created: "أُعِدّ طلب تقرير",
      report_request_sent: "أُرسل طلب التقرير أو بدأ",
      report_revised: "عُدِّل تقرير",
      report_submitted: "قُدِّم تقرير",
      testimony_scheduled: "جُدولت الشهادة",
      vote_recorded: "سُجِّل صوت",
      petition_denied: "رُفض الطلب وأُغلقت القضية",
      petitions_withdrawn: "سُحبت الطلبات وأُغلقت القضية",
      assignment_agenda_completed: "اكتمل تعيين القضية الجديدة في الجلسة",
    },
  };

  // Known codes get a readable label; unknown codes are shown exactly as stored.
  function auditLabel(action, lang) {
    const table = AUDIT_LABELS[lang === "ar" ? "ar" : "en"];
    return table[action] || action;
  }

  function auditRows(items, members, lang) {
    const names = Object.fromEntries((members || []).map((m) => [m.id, m.name]));
    return (items || []).map((row) => ({
      id: row.id,
      timestamp: row.timestamp,
      action: row.action,
      label: auditLabel(row.action, lang),
      actor: row.actor ? names[row.actor] || null : "system",
    }));
  }

  function filterAudit(rows, query) {
    const q = String(query || "").trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      [row.label, row.action, row.actor || ""].some((value) => String(value).toLowerCase().includes(q)),
    );
  }

  function callProblem(form) {
    if (!form.party) return "chooseCallParty";
    if (!form.occurred || Number.isNaN(new Date(form.occurred).getTime())) return "callTimeRequired";
    if (new Date(form.occurred).getTime() > Date.now() + 5 * 60 * 1000) return "callTimeFuture";
    if (!String(form.outcome || "").trim()) return "callOutcomeRequired";
    return null;
  }

  function CaseAudit({ api, lang, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([api(`/api/cases/${encodeURIComponent(caseId)}/audit/`), api("/api/council/members/")]).then(
          ([audit, members]) => ({ items: audit.items, members: members.items }),
        ),
      [caseId],
    );
    const [query, setQuery] = R.useState("");
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const rows = filterAudit(auditRows(state.data.items, state.data.members, lang), query);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("caseAudit")),
      h(P.Field, { label: t("searchAudit") }, h(P.Input, { type: "search", value: query, onChange: (e) => setQuery(e.target.value) })),
      h(P.Text, { variant: "secondary" }, t("auditCount", { n: rows.length })),
      rows.length
        ? h(
            P.Stack,
            { gap: "xs" },
            ...rows.map((row) =>
              h(
                P.Inline,
                { key: row.id, justify: "between", wrap: true },
                h(P.Text, { variant: "strong" }, row.label),
                h(
                  P.Text,
                  { variant: "secondary" },
                  `${row.actor === "system" ? t("systemActor") : row.actor || t("otherAccount")} · ${base.formatWhen(row.timestamp, lang)}`,
                ),
              ),
            ),
          )
        : h(P.EmptyState, { title: t("noAudit") }),
    );
  }

  function CallLog({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)), api(`/api/cases/${encodeURIComponent(caseId)}/calls/`)]).then(
          ([record, calls]) => ({ record, calls: calls.items }),
        ),
      [caseId],
    );
    const [form, setForm] = R.useState({ party: "", occurred: "", outcome: "", notes: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, calls } = state.data;
    const canWrite = writerFor(user, null, record) && record.status === "open";
    const partyName = (id) => record.parties.find((p) => p.id === id)?.name || "";
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    async function save(event) {
      event.preventDefault();
      const issue = callProblem(form);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/cases/${encodeURIComponent(caseId)}/calls/`, {
          method: "POST",
          body: JSON.stringify({
            party_id: form.party,
            // Browser-local wall time converted to an absolute instant with offset.
            occurred_at: new Date(form.occurred).toISOString(),
            outcome: form.outcome.trim(),
            notes: form.notes.trim(),
          }),
        });
        setForm({ party: "", occurred: "", outcome: "", notes: "" });
        setNotice("callRecorded");
        retry();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    return h(
      P.Panel,
      { icon: "doc-text", title: t("callLog"), description: t("callLogHelp") },
      h(
        P.Stack,
        { gap: "md" },
        notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
        calls.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...calls.map((call) =>
                h(
                  P.Card,
                  { key: call.id, title: `${base.isolate(partyName(call.party_id))} · ${base.formatWhen(call.occurred_at, lang)}`, meta: `${t("recordedAt")}: ${base.formatWhen(call.recorded_at, lang)}` },
                  h(P.Text, { as: "p", variant: "strong" }, call.outcome),
                  call.notes ? h(P.Text, { as: "p" }, call.notes) : null,
                ),
              ),
            )
          : h(P.EmptyState, { title: t("noCalls") }),
        canWrite
          ? h(
              P.Form,
              { onSubmit: save, label: t("recordCall"), noValidate: true },
              h(
                P.FormSection,
                { title: t("recordCall") },
                h(
                  P.Field,
                  { label: t("callParty"), required: true, error: err("chooseCallParty") },
                  h(P.Select, {
                    value: form.party,
                    disabled: pending,
                    onChange: (e) => update({ party: e.target.value }),
                    options: [{ value: "", label: t("chooseCallParty") }, ...record.parties.map((p) => ({ value: p.id, label: p.name }))],
                  }),
                ),
                h(
                  P.Field,
                  { label: t("callTime"), required: true, error: err("callTimeRequired") || err("callTimeFuture") },
                  h(P.Input, { type: "datetime-local", width: "md", value: form.occurred, disabled: pending, onChange: (e) => update({ occurred: e.target.value }) }),
                ),
                h(
                  P.Field,
                  { label: t("callOutcome"), required: true, error: err("callOutcomeRequired") },
                  h(P.Input, { value: form.outcome, maxLength: 500, disabled: pending, onChange: (e) => update({ outcome: e.target.value }) }),
                ),
                h(
                  P.Field,
                  { label: t("callNotes") },
                  h(P.Textarea, { rows: 3, value: form.notes, maxLength: 10000, disabled: pending, onChange: (e) => update({ notes: e.target.value }) }),
                ),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
              h(P.FormActions, { sticky: false }, h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("recordCall"))),
            )
          : null,
      ),
    );
  }

  // ---------- Professional Assessments ----------
  // Separate from ordinary reports. Contents stay hidden unless the subject's signed,
  // scoped release covers council; the server enforces this on every read.

  const ASSESSMENT_KINDS = ["medical", "psychological"];

  function assessmentRequests(requests) {
    return (requests || []).filter((row) => ASSESSMENT_KINDS.includes(row.kind));
  }

  function assessmentReports(reports) {
    return (reports || []).filter((row) => row.restricted || ASSESSMENT_KINDS.includes(row.kind));
  }

  function assessmentProblem(form) {
    if (!form.party) return "chooseSubject";
    if (!ASSESSMENT_KINDS.includes(form.kind)) return "chooseAssessmentKind";
    if (!String(form.title || "").trim()) return "titleRequired";
    return null;
  }

  function AssessmentsWorkspace({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([
          api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)),
          api(`/api/cases/${encodeURIComponent(caseId)}/requests/`),
          api(`/api/cases/${encodeURIComponent(caseId)}/reports/`),
        ]).then(([record, requests, reports]) => ({
          record,
          requests: assessmentRequests(requests.items),
          reports: assessmentReports(reports.items),
        })),
      [caseId],
    );
    const [composing, setComposing] = R.useState(false);
    const [form, setForm] = R.useState({ party: "", kind: "medical", title: "", instructions: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    const [confirm, setConfirm] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, requests, reports } = state.data;
    const proceeding = openProceeding(record);
    const canWrite = writerFor(user, null, record) && Boolean(proceeding);
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    async function create(event) {
      event.preventDefault();
      const issue = assessmentProblem(form);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/cases/${encodeURIComponent(caseId)}/requests/`, {
          method: "POST",
          body: JSON.stringify({
            proceeding_id: proceeding.id,
            party_id: form.party,
            kind: form.kind,
            title: form.title.trim(),
            instructions: form.instructions.trim(),
            language: "en",
            questions: [],
          }),
        });
        setComposing(false);
        setForm({ party: "", kind: "medical", title: "", instructions: "" });
        setNotice("assessmentDraftSaved");
        retry();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    async function send() {
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/requests/${encodeURIComponent(confirm.id)}/send/`, { method: "POST", body: "{}" });
        setConfirm(null);
        setNotice("assessmentSent");
        retry();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("assessments")),
      h(P.Notice, { tone: "info" }, t("assessmentPrivacy")),
      h(P.Notice, { tone: "warning" }, t("releaseTextPending")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      h(
        P.Panel,
        { icon: "lock",
          title: t("assessmentRequests"),
          actions: canWrite && !composing ? h(P.Button, { size: "sm", variant: "primary", onClick: () => setComposing(true) }, t("newAssessment")) : null,
        },
        h(
          P.Stack,
          { gap: "sm" },
          composing
            ? h(
                P.Form,
                { onSubmit: create, label: t("newAssessment"), noValidate: true },
                h(
                  P.FormSection,
                  { title: t("newAssessment") },
                  h(
                    P.Field,
                    { label: t("subject"), required: true, error: err("chooseSubject") },
                    h(P.Select, {
                      value: form.party,
                      disabled: pending,
                      onChange: (e) => update({ party: e.target.value }),
                      options: [{ value: "", label: t("chooseSubject") }, ...record.parties.filter((p) => p.can_receive).map((p) => ({ value: p.id, label: p.name }))],
                    }),
                  ),
                  h(P.RadioGroup, {
                    label: t("assessmentKind"),
                    layout: "row",
                    value: form.kind,
                    onChange: (value) => update({ kind: value }),
                    options: ASSESSMENT_KINDS.map((value) => ({ value, label: t(value), disabled: pending })),
                  }),
                  h(P.Field, { label: t("title"), required: true, error: err("titleRequired") }, h(P.Input, { value: form.title, maxLength: 200, disabled: pending, onChange: (e) => update({ title: e.target.value }) })),
                  h(
                    P.Field,
                    { label: t("assessmentInstructions"), description: t("assessmentInstructionsHelp") },
                    h(P.Textarea, { rows: 4, value: form.instructions, maxLength: 10000, disabled: pending, onChange: (e) => update({ instructions: e.target.value }) }),
                  ),
                ),
                h(
                  P.FormActions,
                  { sticky: false },
                  h(P.Button, { disabled: pending, onClick: () => setComposing(false) }, t("cancel")),
                  h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveDraft")),
                ),
              )
            : null,
          ...requests.map((row) =>
            h(
              P.Card,
              {
                key: row.id,
                title: row.title,
                meta: [t(row.kind), base.isolate(row.subject_name), t(row.state), row.release_status ? t("release_" + row.release_status) : null].filter(Boolean).join(" · "),
                actions:
                  canWrite && row.state === "draft"
                    ? h(P.Button, { size: "xs", variant: "primary", onClick: () => setConfirm(row) }, t("send"))
                    : null,
              },
              row.instructions ? h(P.Text, { as: "p", variant: "secondary" }, row.instructions) : null,
            ),
          ),
          !requests.length && !composing ? h(P.EmptyState, { title: t("noAssessments") }) : null,
          !canWrite ? h(P.Text, { variant: "secondary" }, t(proceeding ? "writerOnly" : "noOpenProceeding")) : null,
        ),
      ),
      h(
        P.Panel,
        { icon: "doc-text", title: t("assessmentReports") },
        reports.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...reports.map((row) =>
                row.restricted
                  ? h(P.Card, { key: row.id, title: t("restrictedAssessment"), meta: t("restrictedAssessmentHelp") })
                  : h(
                      P.Card,
                      { key: row.id, title: row.title, meta: [t(row.kind), row.subject, row.date].filter(Boolean).join(" · ") },
                      ...((row.answers && Array.isArray(row.answers.files) ? row.answers.files : []).map((id) =>
                        h(P.Button, { key: id, size: "xs", href: `/api/files/${encodeURIComponent(id)}/` }, t("download")),
                      )),
                    ),
              ),
            )
          : h(P.EmptyState, { title: t("noAssessmentReports") }),
      ),
      h(
        P.ConfirmDialog,
        {
          open: Boolean(confirm),
          title: t("sendAssessmentTitle"),
          message: t("sendAssessmentMessage"),
          confirmLabel: t("send"),
          cancelLabel: t("cancel"),
          onConfirm: send,
          onCancel: () => !pending && setConfirm(null),
        },
        failure && confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  // ---------- Parties and case hearings ----------

  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function partyProblem(form) {
    if (!String(form.first || "").trim()) return "firstRequired";
    if (!String(form.last || "").trim()) return "lastRequired";
    if (!EMAIL.test(String(form.email || "").trim())) return "emailInvalid";
    return null;
  }

  function CaseParties({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)), [caseId]);
    const [form, setForm] = R.useState({ first: "", last: "", email: "" });
    const [open, setOpen] = R.useState(false);
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const record = state.data;
    const manage = base.canManage(user);
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    async function save(event) {
      event.preventDefault();
      const issue = partyProblem(form);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/cases/${encodeURIComponent(caseId)}/parties/`, {
          method: "POST",
          body: JSON.stringify({ first_name: form.first.trim(), last_name: form.last.trim(), email: form.email.trim() }),
        });
        setForm({ first: "", last: "", email: "" });
        setOpen(false);
        setNotice("partyAdded");
        retry();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("partiesTitle")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      ...record.parties.map((party) =>
        h(
          P.Panel,
          { icon: "doc-text", key: party.id, title: party.name },
          h(
            P.PropertyList,
            null,
            party.reference ? h(P.PropertyList.Item, { label: t("ctmReference"), data: true }, party.reference) : null,
            h(
              P.PropertyList.Item,
              { label: t("portalAccount") },
              h(P.Badge, { tone: party.can_receive ? "success" : "waiting" }, t(party.can_receive ? "registered" : "notRegistered")),
            ),
          ),
        ),
      ),
      !record.parties.length ? h(P.EmptyState, { title: t("noParties") }) : null,
      manage && record.status === "open"
        ? open
          ? h(
              P.Form,
              { onSubmit: save, label: t("addParty"), noValidate: true },
              h(
                P.FormSection,
                { title: t("addParty"), description: t("addPartyHelp") },
                h(P.Field, { label: t("firstName"), required: true, error: err("firstRequired") }, h(P.Input, { value: form.first, maxLength: 150, disabled: pending, onChange: (e) => update({ first: e.target.value }) })),
                h(P.Field, { label: t("lastName"), required: true, error: err("lastRequired") }, h(P.Input, { value: form.last, maxLength: 150, disabled: pending, onChange: (e) => update({ last: e.target.value }) })),
                h(P.Field, { label: t("email"), required: true, error: err("emailInvalid") }, h(P.Input, { type: "email", value: form.email, maxLength: 254, disabled: pending, onChange: (e) => update({ email: e.target.value }) })),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
              h(
                P.FormActions,
                { sticky: false },
                h(P.Button, { disabled: pending, onClick: () => setOpen(false) }, t("cancel")),
                h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("addParty")),
              ),
            )
          : h(P.Inline, null, h(P.Button, { onClick: () => setOpen(true) }, t("addParty")))
        : null,
    );
  }

  function CaseHearings({ api, lang, caseId, onSession }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        api("/api/sessions/").then(async (sessions) => {
          const recent = (sessions.items || []).slice(0, 24);
          const agendas = await Promise.all(
            recent.map((session) =>
              api(`/api/sessions/${encodeURIComponent(session.id)}/agenda/`).then((data) => ({ session, items: data.items })),
            ),
          );
          const rows = [];
          for (const { session, items } of agendas)
            for (const item of items || []) if (item.case_id === caseId) rows.push({ session, item });
          return rows.sort((a, b) => b.session.date.localeCompare(a.session.date));
        }),
      [caseId],
    );
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const bt = base.translator(lang);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("hearingsTitle")),
      h(P.Text, { variant: "secondary" }, t("hearingsScope")),
      state.data.length
        ? h(
            P.Stack,
            { gap: "sm" },
            ...state.data.map(({ session, item }) =>
              h(
                P.Card,
                {
                  key: item.id,
                  title:
                    item.part === 2 && Array.isArray(item.party_names) && item.party_names.length
                      ? base.hearingTitle(item.party_names, session.date, bt)
                      : base.sessionLabel(session.date, bt),
                  meta: `${bt(item.part === 1 ? "part1" : "part2")} · ${bt(item.state === "assigned" ? "assigned_state" : item.state)}`,
                  onOpen: () => onSession(session.id),
                },
                (item.testimony || []).length
                  ? h(P.Text, { variant: "secondary" }, `${bt("testimony")}: ${item.testimony.length}`)
                  : null,
              ),
            ),
          )
        : h(P.EmptyState, { title: t("noHearings") }),
    );
  }

  // ---------- Petition and internal notes ----------
  // Each spouse's formal submission is shown read-only. Council notes are a separate,
  // council-only record and never change what either spouse submitted.

  function casePetitions(items, caseId) {
    return (items || []).filter((row) => row && row.kind === "petition" && row.case_id === caseId);
  }

  // Latest revision of each note, newest note first by first appearance order.
  function latestNotes(revisions) {
    const byNote = new Map();
    for (const row of revisions || []) {
      const prior = byNote.get(row.note_id);
      if (!prior || prior.version < row.version) byNote.set(row.note_id, row);
    }
    return [...byNote.values()].reverse();
  }

  function latestFindings(rows) {
    const byCode = new Map();
    for (const row of rows || []) {
      const prior = byCode.get(row.fact_code);
      if (!prior || prior.version < row.version) byCode.set(row.fact_code, row);
    }
    return [...byCode.values()].sort((a, b) => String(a.fact_code).localeCompare(String(b.fact_code)));
  }

  function PetitionWorkspace({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const bt = base.translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([api("/api/applications/"), api(`/api/cases/${encodeURIComponent(caseId)}/`)]).then(async ([apps, record]) => {
          const proceeding = openProceeding(record) || [...(record.proceedings || [])].sort((a, b) => (b.sequence || 0) - (a.sequence || 0))[0] || null;
          const notes = proceeding ? await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/notes/`) : { items: [] };
          let findings = null;
          if (proceeding) {
            try {
              findings = latestFindings((await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/findings/`)).items);
            } catch (error) {
              // Older servers have no findings read (405); findings are then not shown.
              if (error.status !== 405) throw error;
            }
          }
          return { petitions: casePetitions(apps.items, caseId), record, proceeding, notes: latestNotes(notes.items), findings };
        }),
      [caseId],
    );
    const [text, setText] = R.useState("");
    const [editing, setEditing] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { petitions, record, proceeding, notes, findings } = state.data;
    const canWrite = writerFor(user, null, record) && proceeding && proceeding.status === "open";
    async function save(event) {
      event.preventDefault();
      if (!text.trim()) {
        setFailure(t("noteRequired"));
        return;
      }
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/notes/`, {
          method: "POST",
          body: JSON.stringify(editing ? { text: text.trim(), note_id: editing } : { text: text.trim() }),
        });
        setText("");
        setEditing(null);
        setNotice("noteSaved");
        retry();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("petitionTitle")),
      h(P.Notice, { tone: "info" }, t("petitionReadOnly")),
      ...petitions.map((row) => {
        const answers = Object.entries(row.answers || {});
        const labelled = answers.every(([code]) => base.fieldLabel(row, code, lang));
        return h(
          P.Panel,
          { icon: "doc-text",
            key: row.id,
            title: row.applicant_name || t("petition"),
            description: [bt("state_" + row.status), row.submitted_at ? base.formatWhen(row.submitted_at, lang) : null].filter(Boolean).join(" · "),
            collapsible: true,
          },
          h(
            P.Stack,
            { gap: "sm" },
            !labelled ? h(P.Notice, { tone: "info" }, bt("codesNotice")) : null,
            answers.length
              ? h(
                  P.PropertyList,
                  { layout: "stacked" },
                  ...answers.map(([code, value]) =>
                    h(P.PropertyList.Item, { key: code, label: base.fieldLabel(row, code, lang) || code }, base.answerText(value, bt)),
                  ),
                )
              : h(P.EmptyState, { title: bt("noAnswers") }),
          ),
        );
      }),
      !petitions.length ? h(P.EmptyState, { title: t("noPetitions") }) : null,
      findings
        ? h(
            P.Panel,
            { icon: "doc-text", title: t("findingsTitle"), description: t("findingsHelp") },
            findings.length
              ? h(
                  P.PropertyList,
                  { layout: "stacked" },
                  ...findings.map((f) =>
                    h(
                      P.PropertyList.Item,
                      { key: f.fact_code, label: f.fact_code, description: `${f.actor} · ${base.formatWhen(f.timestamp, lang)} · ${t("version")} ${f.version}` },
                      typeof f.value === "string" ? f.value : JSON.stringify(f.value),
                    ),
                  ),
                )
              : h(P.EmptyState, { title: t("noFindings") }),
          )
        : null,
      h(
        P.Panel,
        { icon: "doc-text", title: t("internalNotes"), description: t("internalNotesHelp") },
        h(
          P.Stack,
          { gap: "md" },
          notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
          notes.length
            ? h(
                P.Stack,
                { gap: "sm" },
                ...notes.map((note) =>
                  h(
                    P.Card,
                    {
                      key: note.note_id,
                      title: note.author ? `${note.author} · ${base.formatWhen(note.timestamp, lang)}` : t("note"),
                      meta: `${t("version")} ${note.version}`,
                      actions: note.can_edit && canWrite
                        ? h(P.Button, { size: "xs", onClick: () => { setEditing(note.note_id); setText(note.text); setFailure(null); } }, t("editNote"))
                        : null,
                    },
                    h(P.Text, { as: "p" }, note.text),
                  ),
                ),
              )
            : h(P.EmptyState, { title: t("noNotes") }),
          canWrite
            ? h(
                P.Form,
                { onSubmit: save, label: t("addNote"), noValidate: true },
                h(P.Field, { label: t(editing ? "editingNote" : "addNote"), description: editing ? t("editNoteHelp") : undefined }, h(P.Textarea, { rows: 4, autoGrow: true, value: text, maxLength: 50000, disabled: pending, onChange: (e) => { setText(e.target.value); setFailure(null); } })),
                failure ? h(P.Notice, { tone: "danger" }, failure) : null,
                h(
                  P.FormActions,
                  { sticky: false },
                  editing ? h(P.Button, { disabled: pending, onClick: () => { setEditing(null); setText(""); } }, t("cancel")) : null,
                  h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t(editing ? "saveRevision" : "saveNote")),
                ),
              )
            : null,
        ),
      ),
    );
  }

  // Case timeline: milestone events from the case audit, oldest first. Routine edits
  // (answer saves, uploads, notes, votes) stay in Case Audit.
  const MILESTONES = new Set([
    "application_submitted",
    "completeness_accept",
    "completeness_reject",
    "case_assigned",
    "agenda_placed",
    "case_heard",
    "hearing_deferred_presenter_absent",
    "testimony_scheduled",
    "report_request_sent",
    "report_submitted",
    "decision_recorded",
    "president_approved",
    "decree_issued",
    "decree_access_release",
    "decree_access_withdraw",
    "petition_denied",
    "filing_withdrawn",
    "petitions_withdrawn",
    "appeal_accept",
    "appeal_decline",
  ]);

  function timelineRows(items, lang) {
    return (items || [])
      .filter((row) => MILESTONES.has(row.action))
      .sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)))
      .map((row) => ({ id: row.id, timestamp: row.timestamp, label: auditLabel(row.action, lang) }));
  }

  function CaseTimeline({ api, lang, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([api(`/api/cases/${encodeURIComponent(caseId)}/audit/`), api(`/api/cases/${encodeURIComponent(caseId)}/`)]).then(
          ([audit, record]) => ({ items: audit.items, history: record.assignment_history || null }),
        ),
      [caseId],
    );
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const rows = timelineRows(state.data.items, lang);
    const history = state.data.history;
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("timelineTitle")),
      h(P.Text, { variant: "secondary" }, t("timelineHelp")),
      rows.length
        ? h(P.List, {
            variant: "bullets",
            items: rows.map((row) => ({ children: `${base.formatWhen(row.timestamp, lang)} — ${row.label}` })),
          })
        : h(P.EmptyState, { title: t("noTimeline") }),
      history
        ? h(
            P.Panel,
            { icon: "doc-text", title: t("managerHistory") },
            history.length
              ? h(P.List, {
                  variant: "bullets",
                  items: history.map((row) => ({
                    children: `${base.formatWhen(row.timestamp, lang)} — ${base.isolate(row.member)} · ${t("authorizedBy")} ${base.isolate(row.president)} · ${t("recordedByInline")} ${base.isolate(row.actor)}`,
                  })),
                })
              : h(P.EmptyState, { title: t("noManagerHistory") }),
          )
        : null,
    );
  }

  // ---------- Case summary ----------
  function summaryFacts(record, requests, versions) {
    const latest = Array.isArray(versions) && versions.length ? [...versions].sort((a, b) => b.number - a.number)[0] : null;
    return {
      pendingRequests: (requests || []).filter((r) => r.state === "sent" && !["medical", "psychological"].includes(r.kind)).length,
      draftRequests: (requests || []).filter((r) => r.state === "draft" && !["medical", "psychological"].includes(r.kind)).length,
      decision: latest
        ? { type: latest.type, approved: Boolean(latest.approval), issued: Boolean(latest.decree && latest.decree.issued_at), number: latest.number }
        : null,
      openProceeding: openProceeding(record),
    };
  }

  function CaseSummary({ api, lang, user, caseId, onNavigate }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([
          api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)),
          api(`/api/cases/${encodeURIComponent(caseId)}/requests/`),
        ]).then(async ([record, requests]) => {
          const proceeding = openProceeding(record) || [...(record.proceedings || [])].sort((a, b) => (b.sequence || 0) - (a.sequence || 0))[0];
          let versions = null;
          if (proceeding) {
            try {
              versions = (await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/decision/`)).items || null;
            } catch (error) {
              if (error.status !== 405) throw error;
            }
          }
          return { record, facts: summaryFacts(record, requests.items, versions) };
        }),
      [caseId],
    );
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, facts } = state.data;
    const bt = base.translator(lang);
    const manager =
      record.assignment_history && record.assignment_history.length
        ? record.assignment_history[record.assignment_history.length - 1].member
        : record.assigned_member || null;
    const link = (page, label) => h(P.Button, { key: page, size: "sm", onClick: () => onNavigate(page) }, t(label));
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, record.number),
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: bt("statusLabel") }, h(P.Badge, { tone: record.status === "open" ? "active" : "neutral" }, bt(record.status === "open" ? "open" : "closed"))),
        h(P.PropertyList.Item, { label: bt("assigned") }, manager || bt("unassigned")),
        h(P.PropertyList.Item, { label: t("partiesTitle") }, record.parties.map((p) => p.name).join(" · ") || t("noParties")),
        facts.openProceeding
          ? h(P.PropertyList.Item, { label: t("currentProceeding") }, t(facts.openProceeding.kind === "initial" ? "proceedingInitial" : "proceedingReconsideration"))
          : null,
      ),
      h(
        P.Panel,
        { icon: "info", title: t("whereThingsStand") },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("pendingRequests") }, String(facts.pendingRequests)),
          h(P.PropertyList.Item, { label: t("draftRequests") }, String(facts.draftRequests)),
          h(
            P.PropertyList.Item,
            { label: t("decisionVoting") },
            facts.decision
              ? `${typeLabel(facts.decision.type)} · ${t("version")} ${facts.decision.number} · ${t(facts.decision.issued ? "decreeIssuedState" : facts.decision.approved ? "approved" : "notApproved")}`
              : t("noDecision"),
          ),
        ),
      ),
      h(
        P.Inline,
        { wrap: true },
        link("petition", "petitionTitle"),
        link("reports", "reports"),
        link("hearings", "hearingsTitle"),
        link("decision", "decisionVoting"),
        link("communications", "communicationsLink"),
      ),
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
    topicGroupView,
    hasTaxonomy,
    groupTitle,
    interviewProblem,
    interviewPayload,
    foundationalCodes,
    missingArabic,
    requestProblem,
    usableTemplates,
    templateSelection,
    requestPayload,
    openProceeding,
    ordinaryReports,
    writerFor,
    withAssignee,
    ReportsWorkspace: base.guarded(ReportsWorkspace),
    RequestsPanel: base.guarded(RequestsPanel),
    DecisionWorkspace: base.guarded(DecisionWorkspace),
    auditLabel,
    auditRows,
    filterAudit,
    callProblem,
    CaseAudit: base.guarded(CaseAudit),
    CallLog: base.guarded(CallLog),
    assessmentRequests,
    assessmentReports,
    assessmentProblem,
    AssessmentsWorkspace: base.guarded(AssessmentsWorkspace),
    partyProblem,
    CaseParties: base.guarded(CaseParties),
    CaseHearings: base.guarded(CaseHearings),
    casePetitions,
    latestNotes,
    latestFindings,
    PetitionWorkspace: base.guarded(PetitionWorkspace),
    timelineRows,
    summaryFacts,
    CaseSummary: base.guarded(CaseSummary),
    CaseTimeline: base.guarded(CaseTimeline),
  });
})();
