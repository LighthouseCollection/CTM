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
    return (members || []).filter((row) => ["president", "secretary", "member"].includes(row.role));
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
    const en = group.title || group.category;
    const ar = String(group.title_ar || group.category_ar || "").trim();
    if (lang === "ar") return ar || en;
    return lang === "en-ar" && ar ? `${en} / ${ar}` : en;
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
    if (form.kind && !["intake", "interview"].includes(form.kind)) return "chooseMethod";
    if (!String(form.title || "").trim()) return "titleRequired";
    if (!LANGUAGES.includes(form.language)) return "chooseLanguage";
    if (missingArabic(form.selected, questions, form.language).length) return "arabicMissing";
    return null;
  }

  function requestPayload(form, proceedingId, parties) {
    const partyIds = form.party === "both" ? parties.map((party) => party.id) : [];
    return {
      proceeding_id: proceedingId,
      ...(partyIds.length ? { party_ids: partyIds } : { party_id: form.party }),
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
    const en = question.en || question.wording_en;
    const ar = String(question.ar || question.wording_ar || "").trim();
    if (lang === "ar") return ar || en;
    return lang === "en-ar" && ar ? `${en}
${ar}` : en;
  }

  // ---------- Words ----------

  const words = {
    en: {
      reports: "Reports",
      completedReports: "Completed reports",
      interviewReports: "Reports for Interview",
      noInterviewReports: "No reports are waiting for an interview.",
      requests: "Requests",
      reportTemplates: "Report Maker",
      questionCategories: "Question categories",
      questionSelection: "Questions in this report",
      bothSpouses: "Both spouses",
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
      saveReport: "Save as a Report",
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
      councilVote: "Council vote",
      councilVoteDescription: "Record each council member's vote before proceeding to the decision.",
      voteRecord: "Vote record",
      councilMember: "Council member",
      recordVotesContinue: "Record votes & continue",
      saveVoteDraft: "Save draft",
      voteDraftSaved: "The current vote entries were saved.",
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
      caseSummary: "Case Summary",
      caseNumber: "Case Number",
      filingDate: "Filing Date",
      pending: "Pending",
      inProgress: "In progress",
      active: "Active",
      applicant: "Applicant",
      respondent: "Respondent",
      reasonForDivorce: "Reason for Divorce",
      assignedCouncilMember: "Assigned Council Member",
      lastHearingDate: "Last Hearing Date",
      children: "Children",
      noChildren: "No children recorded",
      keyDates: "Key Dates",
      decreeIssued: "Decree Issued",
      councilReviewDecision: "Council Review & Decision",
      recommendationPending: "Recommendation Pending",
      awaitingCouncilReview: "Awaiting council review and decision.",
      awaitingRecommendation: "Awaiting recommendation from {member}.",
      current: "Current",
      upcoming: "Upcoming",
      caseFiled: "Case Filed",
      caseFiledDescription: "Application received and logged.",
      caseAssigned: "Assigned to Council Member",
      hearing: "Hearing",
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
      petition: "Petition",
      noPetitions: "No submitted petition is available for this case.",
      marriageTitle: "Marriage",
      separation: "Separation",
      churchMarriage: "Church Marriage",
      marriedOutsideCoptic: "Were You Married Outside the Coptic Orthodox Church?",
      outsideDenomination: "Religious Denomination Officiating",
      outsideMarriageDate: "Date of Marriage Outside Coptic Church",
      churchMarriageDate: "Date of Church Marriage",
      dateOfSeparation: "Date of Separation",
      dateOfCivilDivorce: "Date of Civil Divorce",
      dateOfRestrainingOrder: "Date of Restraining Order",
      restrainingOrderExpirationDate: "Restraining Order Expiration Date",
      officiatingPriest: "Officiating Priest",
      marriageDuration: "Marriage Duration",
      churchName: "Church Name",
      churchLocation: "Church Address / Location",
      internalNotes: "Internal notes",
      internalNotesHelp: "Council only. Never shown to applicants.",
      note: "Note",
      noNotes: "No internal notes yet.",
      addNote: "Add an internal note",
      saveNote: "Save note",
      noteSaved: "The note was saved.",
      noteRequired: "Write the note before saving.",
      partiesTitle: "Spouses",
      ctmId: "CTM ID#",
      portalAccount: "Portal account",
      registered: "Registered",
      notRegistered: "Not registered",
      personalDetails: "Personal Details",
      contact: "Contact",
      career: "Career",
      churchAffiliation: "Church Affiliation",
      otherNamesKnownBy: "Other Names Known By",
      placeOfBirth: "Place of Birth",
      nationality: "Nationality",
      awarenessOfApplication: "Awareness of Application",
      address: "Address",
      mobileNumber: "Mobile Number",
      emailAddress: "Email Address",
      immigrationStatus: "Immigration Status",
      residingWith: "Residing With",
      education: "Education",
      yearOfGraduation: "Year of Graduation",
      occupation: "Occupation",
      denomination: "Denomination",
      nameOfBishop: "Name of Bishop",
      diocese: "Diocese",
      parishName: "Parish Name",
      fatherOfConfession: "Father of Confession",
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
      currentHearing: "Current Hearing: {date}",
      pastHearings: "Past hearings",
      rescheduleHearing: "Reschedule this hearing",
      councilAttendance: "Council attendance",
      councilAttendanceHelp: "Confirm the members who attended this particular hearing.",
      outcome: "Outcome",
      decisionMade: "Decision Made — Go to Decision tab",
      recommendationOnly: "Recommendation (no final decision yet)",
      decisionOutcomeHelp: "Go to the Decision tab to document the final outcome.",
      recommendationRequired: "Enter a recommendation before saving.",
      saveRecommendation: "Save Recommendation",
      recommendationSaved: "Recommendation saved.",
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
      interviewRestored: "Your unsaved interview answers were restored. Save them or discard them.",
      interviewUnsaved: "Interview answers have not been saved.",
      interviewDiscardTitle: "Discard unsaved interview answers?",
      interviewDiscardMessage: "The answers and observations you typed will be removed. Nothing has been saved.",
      interviewDiscard: "Discard answers",
      interviewKeepEditing: "Keep editing",
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
      interviewReports: "تقارير للمقابلة",
      noInterviewReports: "لا توجد تقارير بانتظار المقابلة.",
      requests: "الطلبات",
      reportTemplates: "منشئ التقارير",
      questionCategories: "فئات الأسئلة",
      questionSelection: "أسئلة هذا التقرير",
      bothSpouses: "كلا الزوجين",
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
      saveReport: "حفظ كتقرير",
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
      councilVote: "تصويت المجلس",
      councilVoteDescription: "سجّل صوت كل عضو في المجلس قبل متابعة القرار.",
      voteRecord: "سجل التصويت",
      councilMember: "عضو المجلس",
      recordVotesContinue: "سجّل الأصوات وتابع",
      saveVoteDraft: "حفظ المسودة",
      voteDraftSaved: "تم حفظ إدخالات التصويت الحالية.",
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
      caseSummary: "ملخص القضية",
      caseNumber: "رقم القضية",
      filingDate: "تاريخ التقديم",
      pending: "قيد الانتظار",
      inProgress: "قيد التنفيذ",
      active: "نشطة",
      applicant: "مقدم الطلب",
      respondent: "الطرف الآخر",
      reasonForDivorce: "سبب الطلاق",
      assignedCouncilMember: "عضو المجلس المكلّف",
      lastHearingDate: "تاريخ آخر جلسة",
      children: "الأبناء",
      noChildren: "لا يوجد أبناء مسجلون",
      keyDates: "التواريخ المهمة",
      decreeIssued: "صدور المرسوم",
      councilReviewDecision: "مراجعة المجلس والقرار",
      recommendationPending: "التوصية قيد الانتظار",
      awaitingCouncilReview: "بانتظار مراجعة المجلس والقرار.",
      awaitingRecommendation: "بانتظار توصية من {member}.",
      current: "الحالي",
      upcoming: "قادم",
      caseFiled: "تم تقديم القضية",
      caseFiledDescription: "تم استلام الطلب وتسجيله.",
      caseAssigned: "تم التعيين لعضو المجلس",
      hearing: "جلسة استماع",
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
      petition: "الطلب",
      noPetitions: "لا يوجد طلب مقدَّم متاح لهذه القضية.",
      marriageTitle: "الزواج",
      separation: "الانفصال",
      churchMarriage: "الزواج الكنسي",
      marriedOutsideCoptic: "هل تم الزواج خارج الكنيسة القبطية الأرثوذكسية؟",
      outsideDenomination: "الطائفة الدينية التي أجرت الزواج",
      outsideMarriageDate: "تاريخ الزواج خارج الكنيسة القبطية",
      churchMarriageDate: "تاريخ الزواج الكنسي",
      dateOfSeparation: "تاريخ الانفصال",
      dateOfCivilDivorce: "تاريخ الطلاق المدني",
      dateOfRestrainingOrder: "تاريخ أمر التقييد",
      restrainingOrderExpirationDate: "تاريخ انتهاء أمر التقييد",
      officiatingPriest: "الكاهن الذي أجرى الزواج",
      marriageDuration: "مدة الزواج",
      churchName: "اسم الكنيسة",
      churchLocation: "عنوان / موقع الكنيسة",
      internalNotes: "ملاحظات داخلية",
      internalNotesHelp: "للمجلس فقط. لا تُعرض أبدًا على مقدمي الطلبات.",
      note: "ملاحظة",
      noNotes: "لا توجد ملاحظات داخلية بعد.",
      addNote: "إضافة ملاحظة داخلية",
      saveNote: "حفظ الملاحظة",
      noteSaved: "تم حفظ الملاحظة.",
      noteRequired: "اكتب الملاحظة قبل الحفظ.",
      partiesTitle: "الزوجان",
      ctmId: "معرّف CTM#",
      portalAccount: "حساب البوابة",
      registered: "مسجَّل",
      notRegistered: "غير مسجَّل",
      personalDetails: "البيانات الشخصية",
      contact: "التواصل",
      career: "العمل والتعليم",
      churchAffiliation: "الانتماء الكنسي",
      otherNamesKnownBy: "أسماء أخرى معروفة بها",
      placeOfBirth: "مكان الميلاد",
      nationality: "الجنسية",
      awarenessOfApplication: "العلم بالطلب",
      address: "العنوان",
      mobileNumber: "رقم الجوال",
      emailAddress: "البريد الإلكتروني",
      immigrationStatus: "حالة الهجرة",
      residingWith: "الإقامة مع",
      education: "التعليم",
      yearOfGraduation: "سنة التخرج",
      occupation: "المهنة",
      denomination: "الطائفة",
      nameOfBishop: "اسم الأسقف",
      diocese: "الإيبارشية",
      parishName: "اسم الكنيسة",
      fatherOfConfession: "أب الاعتراف",
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
      currentHearing: "الجلسة الحالية: {date}",
      pastHearings: "الجلسات السابقة",
      rescheduleHearing: "إعادة جدولة هذه الجلسة",
      councilAttendance: "حضور المجلس",
      councilAttendanceHelp: "أكد الأعضاء الذين حضروا هذه الجلسة تحديدًا.",
      outcome: "النتيجة",
      decisionMade: "تم اتخاذ القرار — انتقل إلى علامة القرار",
      recommendationOnly: "توصية (لا يوجد قرار نهائي بعد)",
      decisionOutcomeHelp: "انتقل إلى علامة القرار لتوثيق النتيجة النهائية.",
      recommendationRequired: "أدخل توصية قبل الحفظ.",
      saveRecommendation: "حفظ التوصية",
      recommendationSaved: "تم حفظ التوصية.",
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
      interviewRestored: "تمت استعادة إجابات المقابلة غير المحفوظة. احفظها أو تجاهلها.",
      interviewUnsaved: "لم تُحفظ إجابات المقابلة.",
      interviewDiscardTitle: "هل تريد تجاهل إجابات المقابلة غير المحفوظة؟",
      interviewDiscardMessage: "ستُحذف الإجابات والملاحظات التي كتبتها. لم يُحفظ أي شيء.",
      interviewDiscard: "تجاهل الإجابات",
      interviewKeepEditing: "متابعة التعديل",
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

  function ReportPartySelector({ P, h, t, parties, kind, interviewReady, value, disabled, error, onChange }) {
    const eligible = (parties || []).filter((party) => party.can_receive || (kind === "interview" && interviewReady));
    const selected = value === "both" ? eligible.map((party) => party.id) : value ? [value] : [];
    const changeSelection = (partyId, checked) => {
      const next = checked ? [...new Set([...selected, partyId])] : selected.filter((id) => id !== partyId);
      onChange(next.length === eligible.length && eligible.length > 1 ? "both" : next[0] || "");
    };
    return h(
      P.Field,
      { label: t("subject"), required: true, error },
      h(
        "div",
        { className: "ctm-report-party-cards", role: "group", "aria-label": t("subject") },
        ...eligible.map((party) => {
          const checked = selected.includes(party.id);
          return h(
            "div",
            { key: party.id, className: `ctm-report-party-card${checked ? " is-selected" : ""}` },
            h(P.Checkbox, {
              checked,
              disabled,
              onChange: (event) => changeSelection(party.id, event.target.checked),
              label: h(
                P.Inline,
                { gap: "sm", align: "center" },
                h(P.Avatar, { src: party.photo_url || undefined, name: party.name, size: "lg", label: party.name }),
                h(P.Text, { as: "span", variant: "strong" }, party.name),
              ),
            }),
          );
        }),
      ),
    );
  }

  function RequestComposer({ api, lang, record, questions, reports, onSaved, onCancel }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const proceeding = openProceeding(record);
    const [form, setForm] = R.useState({
      // Applicant delivery is not available yet, so reports begin as an internal interview.
      kind: "interview",
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
    const categoryGroups = questionGroups(questions);
    const [activeCategory, setActiveCategory] = R.useState(() => categoryGroups[0]?.category || "");
    const activeQuestions = categoryGroups.find((group) => group.category === activeCategory)?.questions || [];
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
          body: JSON.stringify(requestPayload(form, proceeding.id, record.parties)),
        });
        onSaved(created.items ? created.items.map((item) => item.id) : created.id);
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
        h(ReportPartySelector, {
          P, h, t, parties: record.parties, kind: form.kind, interviewReady,
          value: form.party, disabled: pending, error: err("chooseSubject"),
          onChange: (party) => update({ party }),
        }),
        h(P.RadioGroup, {
          label: t("method"),
          value: form.kind,
          onChange: (value) => update({ kind: value, party: "" }),
          options: [
            // Applicant delivery is deliberately visible but unavailable until the
            // applicant delivery workflow is ready for release.
            { value: "intake", label: t("methodApplicant"), disabled: true },
            interviewReady
              ? { value: "interview", label: t("methodInterview"), disabled: pending }
              : { value: "interview", label: t("methodInterview"), disabled: true },
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
      h(P.SplitView, {
        label: t("reportTemplates"),
        firstLabel: t("questionCategories"),
        first: h(P.Panel, { title: t("questionCategories") }, h("div", {
          className: `ctm-report-question-language${form.language === "ar" ? " ctm-report-question-language--rtl" : ""}`,
          dir: form.language === "ar" ? "rtl" : undefined,
        }, h(P.NavList, {
          label: t("questionCategories"), value: activeCategory, onSelect: setActiveCategory,
          items: categoryGroups.map((group) => ({ id: group.category, label: groupTitle(group, form.language), count: group.questions.length })),
        }))),
        second: h(P.FormSection, { title: t("questionSelection"), description: t("selectedCount", { n: form.selected.length }) },
          h("div", {
            className: `ctm-report-question-language${form.language === "ar" ? " ctm-report-question-language--rtl" : ""}`,
            dir: form.language === "ar" ? "rtl" : undefined,
          }, h(P.Fieldset, { legend: groupTitle(categoryGroups.find((group) => group.category === activeCategory) || {}, form.language) },
            ...activeQuestions.map((q) => h(P.Checkbox, {
              key: q.code, label: wording(q, form.language),
              description: q.foundational ? t("foundational") : form.language === "ar" && !String(q.wording_ar || "").trim() ? t("arabicPending") : undefined,
              checked: q.foundational || form.selected.includes(q.code), disabled: pending || q.foundational,
              onChange: (e) => update({ selected: e.target.checked ? [...form.selected, q.code] : form.selected.filter((code) => code !== q.code) }),
            })),
          )),
        ),
      }),
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      problem === "chooseLanguage" ? h(P.Notice, { tone: "danger" }, t(problem)) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { disabled: pending, onClick: onCancel }, t("cancel")),
        h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveReport")),
      ),
    );
  }

  const interviewDraftKey = (request) => `interview:${request.id}`;

  function InterviewForm({ api, lang, request, onRecorded, onCancel }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const draftKey = interviewDraftKey(request);
    const [stored] = R.useState(() => base.unsavedDrafts.get(draftKey) || null);
    const [answers, setAnswers] = R.useState(() => (stored ? stored.answers : {}));
    const [observations, setObservations] = R.useState(() => (stored ? stored.observations : ""));
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [confirmDiscard, setConfirmDiscard] = R.useState(false);
    const dirty = Object.values(answers).some((v) => String(v || "").trim()) || Boolean(observations.trim());
    // Keep typed answers across in-app navigation; warn before the page itself unloads.
    R.useEffect(() => {
      if (dirty) base.unsavedDrafts.set(draftKey, { answers, observations });
      else base.unsavedDrafts.delete(draftKey);
      if (!dirty) return undefined;
      const guard = (event) => {
        event.preventDefault();
        event.returnValue = t("interviewUnsaved");
        return event.returnValue;
      };
      window.addEventListener("beforeunload", guard);
      return () => window.removeEventListener("beforeunload", guard);
    }, [answers, observations]);
    function discard() {
      base.unsavedDrafts.delete(draftKey);
      setConfirmDiscard(false);
      onCancel();
    }
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
        base.unsavedDrafts.delete(draftKey);
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
      stored ? h(P.Notice, { tone: "info" }, t("interviewRestored")) : null,
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
        h(P.Button, { disabled: pending, onClick: () => (dirty ? setConfirmDiscard(true) : discard()) }, t("cancel")),
        h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveInterview")),
      ),
      h(P.ConfirmDialog, {
        open: confirmDiscard,
        title: t("interviewDiscardTitle"),
        message: t("interviewDiscardMessage"),
        confirmLabel: t("interviewDiscard"),
        cancelLabel: t("interviewKeepEditing"),
        destructive: true,
        onConfirm: discard,
        onCancel: () => setConfirmDiscard(false),
      }),
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
    // Reopen the answer form when typed answers were left by in-app navigation.
    const [recording, setRecording] = R.useState(() => base.unsavedDrafts.has(interviewDraftKey(request)));
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

  function RequestsPanel({ api, lang, user, caseId, reports, mode = "templates", onCreated }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const interviewOnly = mode === "interviews";
    const panelTitle = interviewOnly ? t("interviewReports") : t("reportTemplates");
    const [state, retry] = base.useLoad(() => Promise.all([
      api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)),
      api(`/api/cases/${encodeURIComponent(caseId)}/requests/`), api("/api/report-questions/"),
      api("/api/cases/"),
    ]).then(([record, requests, questions, cases]) => ({
      record,
      requests: requests.items.filter((row) => !["medical", "psychological"].includes(row.kind)),
      questions: questions.items, caseRow: cases.items.find((row) => row.id === caseId),
    })), [caseId]);
    const [selected, select] = R.useState(null);
    const [editing, setEditing] = R.useState(!interviewOnly);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, questions, caseRow } = state.data;
    const requests = state.data.requests.filter((row) => interviewOnly ? row.kind === "interview" : row.kind !== "interview");
    const proceeding = openProceeding(record);
    const canWrite = writerFor(user, caseRow, record) && Boolean(proceeding);
    const chosen = requests.find((row) => row.id === selected);
    const drafts = h(P.Stack, { gap: "sm" }, ...requests.map((row) => h(P.Card, {
      icon: "doc-text", key: row.id, title: row.title,
      meta: [t(row.kind), base.isolate(row.subject_name), t(row.state)].filter(Boolean).join(" · "),
      selected: row.id === selected, onOpen: () => { setEditing(false); setNotice(null); select(row.id); },
    })), !requests.length ? h(P.EmptyState, { title: t(interviewOnly ? "noInterviewReports" : "noRequests") }) : null);
    const editor = h(RequestComposer, {
      api, lang, record, questions, reports: reports || [],
      onCancel: () => setEditing(false),
      onSaved: (result) => { const id = Array.isArray(result) ? result[0] : result; setEditing(false); setNotice("draftSaved"); select(id); retry(); onCreated?.(id); },
    });
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Toolbar, { label: panelTitle }, !interviewOnly && canWrite ? h(P.Button, { variant: "primary", icon: "add", onClick: () => { setEditing(true); setNotice(null); } }, t("newRequest")) : null),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      !interviewOnly && editing ? editor : h(P.SplitView, {
        label: panelTitle, firstLabel: t("requests"), first: drafts,
        second: h(P.ReadingPane, { label: chosen?.title || t("chooseRequest"), empty: h(P.EmptyState, { title: t("chooseRequest") }) },
          chosen ? h(RequestDetail, { key: chosen.id, api, lang, request: chosen, canWrite, onSent: (key) => { setNotice(key || "sentNotice"); retry(); } }) : null,
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
    const completedReports = base.ReportsReader ? h(base.ReportsReader, { api, lang, user, caseId, reports }) : renderReports();
    const requests = h(RequestsPanel, { api, lang, user, caseId, reports, onCreated: () => setTab("interviews") });
    const interviewReports = h(RequestsPanel, { api, lang, user, caseId, reports, mode: "interviews" });
    return h(P.Tabs, {
      variant: "contained", label: t("reports"), value: tab, onChange: setTab,
      items: [
        { value: "reports", label: t("completedReports"), content: completedReports },
        { value: "interviews", label: t("interviewReports"), content: interviewReports },
        { value: "requests", label: t("reportTemplates"), content: requests },
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

  function CouncilVoteRecord({ api, lang, user, decision, members, readAvailable, onChange }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const roster = councilRoster(members);
    const { rows, counts } = tally(decision.votes, roster);
    const manage = canRecordFor(user);
    const canVote = decision.can_vote !== false;
    const initialChoices = () => Object.fromEntries(rows.map((row) => [row.member.id, row.vote?.choice || ""]));
    const [choices, setChoices] = R.useState(initialChoices);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);

    R.useEffect(() => setChoices(initialChoices()), [decision.id, decision.votes]);
    const changes = rows.filter((row) => choices[row.member.id] && choices[row.member.id] !== (row.vote?.choice || ""));

    async function saveVotes(continueAfter) {
      if (!changes.length) return;
      setPending(true);
      setFailure(null);
      setNotice(null);
      try {
        let votes = [...(decision.votes || [])];
        for (const row of changes) {
          const body = manage ? { choice: choices[row.member.id], member_id: row.member.id } : { choice: choices[row.member.id] };
          await api(`/api/decisions/${encodeURIComponent(decision.id)}/vote/`, { method: "POST", body: JSON.stringify(body) });
          votes = [...votes.filter((vote) => vote.member_id !== row.member.id), { member_id: row.member.id, choice: choices[row.member.id], actor_id: user.id }];
        }
        onChange({ ...decision, votes }, true);
        setNotice(continueAfter ? "voteRecorded" : "voteDraftSaved");
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    return h(
      P.Panel,
      { icon: "check-square", title: t("councilVote"), description: t("councilVoteDescription") },
      h(
        "div",
        { className: "ctm-council-vote-table", role: "table", "aria-label": t("voteRecord") },
        h("div", { className: "ctm-council-vote-table__header", role: "row" },
          h("div", { role: "columnheader" }, t("councilMember")),
          ...VOTES.map((choice) => h("div", { key: choice, role: "columnheader" }, t(choice))),
        ),
        ...rows.map((row) => {
          const canEditRow = canVote && !pending && (manage || row.member.id === user.id);
          return h("div", { key: row.member.id, className: "ctm-council-vote-table__row", role: "row" },
            h("div", { className: "ctm-council-vote-member", role: "cell" },
              h(P.Avatar, { name: row.member.name || row.member.id, size: "md" }),
              h("div", null,
                h(P.Text, { as: "div", variant: "strong" }, row.member.name || row.member.id),
                h(P.Text, { as: "div", variant: "secondary" }, row.member.former ? t("formerMember") : t(row.member.role || "member")),
              ),
            ),
            ...VOTES.map((choice) => h("label", { key: choice, className: "ctm-council-vote-choice", role: "cell" },
              h("input", {
                type: "radio",
                name: `decision-${decision.id}-member-${row.member.id}`,
                value: choice,
                checked: choices[row.member.id] === choice,
                disabled: !canEditRow,
                "aria-label": `${t(choice)}: ${row.member.name || row.member.id}`,
                onChange: () => setChoices((old) => ({ ...old, [row.member.id]: choice })),
              }),
            )),
          );
        }),
        h("div", { className: "ctm-council-vote-table__summary", role: "row" },
          h("div", { role: "cell" }, h("span", { className: "ctm-vote-total ctm-vote-total--approve" }, `${t("approve")}: ${counts.approve}`)),
          h("div", { role: "cell" }, h("span", { className: "ctm-vote-total ctm-vote-total--deny" }, `${t("deny")}: ${counts.deny}`)),
          h("div", { role: "cell" }, h("span", { className: "ctm-vote-total ctm-vote-total--abstain" }, `${t("abstain")}: ${counts.abstain}`)),
        ),
      ),
      !readAvailable ? h(P.Notice, { tone: "warning" }, t("sessionVotesNotice")) : null,
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      canVote ? h(P.FormActions, { sticky: false },
        h(P.Button, { disabled: pending || !changes.length, onClick: () => saveVotes(false) }, t("saveVoteDraft")),
        h(P.Button, { variant: "primary", loading: pending, disabled: pending || !changes.length, onClick: () => saveVotes(true) }, t("recordVotesContinue")),
      ) : null,
    );
  }

  function DecisionVersion({ api, lang, user, record, decision, members, readAvailable, onChange, showVoting = true, showApproval = true }) {
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
      showVoting
        ? h(
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
      )
        : null,
      showApproval
        ? h(
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
      )
        : null,
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
    const updateDecision = (next, saved) => (readAvailable && saved ? retry() : setLocal(next));
    const detail = h(
      P.Stack,
      { gap: "lg" },
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
            showVoting: false,
            showApproval: false,
            onChange: updateDecision,
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
      proceeding && !current
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
    return h(
      P.Stack,
      { gap: "lg", className: "ctm-decision-voting-workspace" },
      h(P.Panel, { icon: "doc-text", title: t("decisionVoting") }, detail),
      current
        ? h(CouncilVoteRecord, {
            key: `vote-${current.id}`,
            api,
            lang,
            user,
            decision: current,
            members,
            readAvailable,
            onChange: updateDecision,
          })
        : null,
    );

  }

  // ---------- Case audit and manual call records ----------

  const AUDIT_LABELS = {
    en: {
      agenda_placed: "Placed on a council session agenda",
      session_created: "Council session created",
      session_closed: "Council session closed",
      session_returned_to_planned: "Council session returned to Planned",
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
      session_returned_to_planned: "أُعيدت جلسة المجلس إلى مخططة",
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
      actor_id: row.actor,
      source: row.source,
      source_id: row.source_id,
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
    const [filters, setFilters] = R.useState({});
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const loaded = auditRows(state.data.items, state.data.members, lang);
    const rows = window.CTMUI.filterAudit(loaded, filters);
    return h(
      P.Stack,
      { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t("caseAudit")),
      h(window.CTMUI.AuditFilters, { rows: loaded, filters, onChange: setFilters, lang }),
      h(P.Text, { variant: "secondary" }, t("auditCount", { n: rows.length })),
      h(window.CTMShell.Workspace, {
        label: t("caseAudit"), rows, empty: t("noAudit"),
        columns: [{ title: t("caseAudit"), field: "label", kind: "name" }, { title: t("recordedBy"), field: "actor" }],
      }, (row) => h(P.Stack, null,
        h(P.Text, { as: "h2", variant: "title" }, row.label),
        h(P.Text, null, row.actor === "system" ? t("systemActor") : row.actor || t("otherAccount")),
        h(P.Text, null, base.formatWhen(row.timestamp, lang)),
        h(P.Text, { variant: "data" }, row.action),
        row.source ? h(P.Text, null, row.source) : null,
        row.source_id ? h(P.Text, { variant: "data" }, row.source_id) : null,
      )),
    );
  }

  function CallLog({ api, lang, user, caseId }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [state, retry] = base.useLoad(() => Promise.all([api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)), api(`/api/cases/${encodeURIComponent(caseId)}/calls/`)]).then(([record, calls]) => ({ record, calls: calls.items })), [caseId]);
    const [selected, select] = R.useState(null), [tab, setTab] = R.useState("received"), [composing, setComposing] = R.useState(false);
    const [form, setForm] = R.useState({ party: "", occurred: "", direction: "sent", outcome: "", notes: "" });
    const [problem, setProblem] = R.useState(null), [pending, setPending] = R.useState(false), [failure, setFailure] = R.useState(null), [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, calls } = state.data;
    const canWrite = writerFor(user, null, record) && record.status === "open";
    const partyName = (id) => record.parties.find((p) => p.id === id)?.name || "";
    const rows = calls.filter((call) => (call.direction || "sent") === tab).map((call) => ({ ...call, id: call.id, person: partyName(call.party_id), occurred: base.formatWhen(call.occurred_at, lang) }));
    const update = (patch) => { setForm((old) => ({ ...old, ...patch })); setProblem(null); };
    async function save(event) {
      event.preventDefault(); const issue = callProblem(form); setProblem(issue); if (issue) return;
      setPending(true); setFailure(null);
      try {
        await api(`/api/cases/${encodeURIComponent(caseId)}/calls/`, { method: "POST", body: JSON.stringify({ party_id: form.party, occurred_at: new Date(form.occurred).toISOString(), direction: form.direction, outcome: form.outcome.trim(), notes: form.notes.trim() }) });
        setForm({ party: "", occurred: "", direction: "sent", outcome: "", notes: "" }); setComposing(false); setNotice("callRecorded"); retry();
      } catch (error) { setFailure(base.serverMessage(error, t)); } finally { setPending(false); }
    }
    const err = (key) => (problem === key ? t(key) : undefined);
    const callDialog = composing ? h(P.Dialog, { open: true, title: t("recordCall"), size: "lg", onClose: () => !pending && setComposing(false) },
      h(P.Form, { onSubmit: save, label: t("recordCall"), noValidate: true },
        h(P.FormSection, { title: t("recordCall") },
          h(P.Field, { label: t("callParty"), required: true, error: err("chooseCallParty") }, h(P.Select, { value: form.party, disabled: pending, onChange: (e) => update({ party: e.target.value }), options: [{ value: "", label: t("chooseCallParty") }, ...record.parties.map((p) => ({ value: p.id, label: p.name }))] })),
          h(P.RadioGroup, { label: "Direction", layout: "row", value: form.direction, onChange: (direction) => update({ direction }), options: [{ value: "received", label: "Received" }, { value: "sent", label: "Sent" }] }),
          h(P.Field, { label: t("callTime"), required: true, error: err("callTimeRequired") || err("callTimeFuture") }, h(P.Input, { type: "datetime-local", width: "md", value: form.occurred, disabled: pending, onChange: (e) => update({ occurred: e.target.value }) })),
          h(P.Field, { label: t("callOutcome"), required: true, error: err("callOutcomeRequired") }, h(P.Input, { value: form.outcome, maxLength: 500, disabled: pending, onChange: (e) => update({ outcome: e.target.value }) })),
          h(P.Field, { label: t("callNotes") }, h(P.Textarea, { rows: 4, value: form.notes, maxLength: 10000, disabled: pending, onChange: (e) => update({ notes: e.target.value }) })),
        ),
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
        h(P.FormActions, { sticky: false }, h(P.Button, { disabled: pending, onClick: () => setComposing(false) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("recordCall"))),
      ),
    ) : null;
    const workspace = h(window.CTMShell.Workspace, {
      label: t("callLog"), rows, selected, onSelect: select, empty: t("noCalls"), showDetailWhenEmpty: true,
      columns: [{ title: t("callParty"), field: "person", kind: "name" }, { title: t("callOutcome"), field: "outcome" }, { title: t("callTime"), field: "occurred" }],
    }, (call) => call ? h(P.Stack, { gap: "md" }, h(P.Text, { as: "h1", variant: "title" }, call.person), h(P.Text, { variant: "secondary" }, call.occurred), h(P.Text, { as: "p", variant: "strong" }, call.outcome), call.notes ? h(P.Text, { as: "p" }, call.notes) : null) : h(P.EmptyState, { title: t("noCalls") }));
    return h(R.Fragment, null, callDialog,
      h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
        h(P.Toolbar, { label: t("callLog") }, canWrite ? h(P.Button, { variant: "primary", icon: "add", onClick: () => setComposing(true) }, "New Call") : null),
        notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
        h(P.Tabs, {
          variant: "contained", label: t("callLog"), value: tab,
          onChange: (value) => { setTab(value); select(null); },
          items: [
            { value: "received", label: "Received", content: workspace },
            { value: "sent", label: "Sent", content: workspace },
          ],
        }),
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
    const [selected, select] = R.useState(null);
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
    const requestDialog = composing
      ? h(P.Dialog, { open: true, title: t("newAssessment"), size: "lg", onClose: () => !pending && setComposing(false) },
          h(P.Form, { onSubmit: create, label: t("newAssessment"), noValidate: true },
            h(P.FormSection, { title: t("newAssessment") },
              h(P.Field, { label: t("subject"), required: true, error: err("chooseSubject") }, h(P.Select, { value: form.party, disabled: pending, onChange: (e) => update({ party: e.target.value }), options: [{ value: "", label: t("chooseSubject") }, ...record.parties.filter((p) => p.can_receive).map((p) => ({ value: p.id, label: p.name }))] })),
              h(P.RadioGroup, { label: t("assessmentKind"), layout: "row", value: form.kind, onChange: (value) => update({ kind: value }), options: ASSESSMENT_KINDS.map((value) => ({ value, label: t(value), disabled: pending })) }),
              h(P.Field, { label: t("title"), required: true, error: err("titleRequired") }, h(P.Input, { value: form.title, maxLength: 200, disabled: pending, onChange: (e) => update({ title: e.target.value }) })),
              h(P.Field, { label: t("assessmentInstructions"), description: t("assessmentInstructionsHelp") }, h(P.Textarea, { rows: 4, value: form.instructions, maxLength: 10000, disabled: pending, onChange: (e) => update({ instructions: e.target.value }) })),
            ),
            h(P.FormActions, { sticky: false }, h(P.Button, { disabled: pending, onClick: () => setComposing(false) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveDraft"))),
          ),
        )
      : null;
    const detail = h(
      P.Stack,
      { gap: "lg" },
      h(P.Toolbar, { label: t("assessments") }, canWrite ? h(P.Button, { variant: "primary", icon: "add", onClick: () => setComposing(true) }, t("newAssessment")) : null),
      h(P.Text, { as: "h1", variant: "title" }, t("assessments")),
      h(P.Notice, { tone: "info" }, t("assessmentPrivacy")),
      h(P.Notice, { tone: "warning" }, t("releaseTextPending")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      h(
        P.Panel,
        { icon: "lock",
          title: t("assessmentRequests"),
          actions: null,
        },
        h(
          P.Stack,
          { gap: "sm" },
          ...requests.filter((row) => row.id === selected).map((row) =>
            h(
              P.Card,
              { icon: "doc-text",
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
          !requests.length ? h(P.EmptyState, { title: t("noAssessments") }) : null,
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
              ...reports.filter((row) => row.id === selected).map((row) =>
                row.restricted
                  ? h(P.Card, { icon: "lock", key: row.id, title: t("restrictedAssessment"), meta: t("restrictedAssessmentHelp") })
                  : h(
                      P.Card,
                      { icon: "doc-text", key: row.id, title: row.title, meta: [t(row.kind), row.subject, row.date].filter(Boolean).join(" · ") },
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
    return h(window.CTMShell.Workspace, {
      label: t("assessments"), selected, onSelect: select, showDetailWhenEmpty: true,
      rows: [...requests, ...reports].map((row) => ({ ...row, title: row.restricted ? t("restrictedAssessment") : row.title })),
      empty: t("noAssessmentReports"),
      columns: [{ title: t("assessments"), field: "title", kind: "name" }, { title: t("assessmentKind"), field: "kind", render: (row) => row.kind ? t(row.kind) : "" }],
    }, detail, requestDialog);

  }

  // ---------- Parties and case hearings ----------

  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function partyProblem(form) {
    if (!String(form.first || "").trim()) return "firstRequired";
    if (!String(form.last || "").trim()) return "lastRequired";
    if (!EMAIL.test(String(form.email || "").trim())) return "emailInvalid";
    return null;
  }

  function spouseProfileSection(P, h, t, title, icon, values, twoColumns = false) {
    const fields = values.filter(([, value]) => value);
    if (!fields.length) return null;
    return h(
      P.Stack,
      { gap: "sm", key: title, className: `ctm-spouse-profile-section${twoColumns ? " ctm-spouse-profile-section--two-columns" : ""}` },
      h(
        P.Inline,
        { gap: "sm", align: "center", className: "ctm-spouse-profile-section__heading" },
        h(P.Icon, { name: icon, label: title }),
        h(P.SectionHeading, { level: 2 }, title),
        h(P.Divider, { className: "ctm-spouse-profile-section__divider" }),
      ),
      h(
        P.PropertyList,
        { layout: "stacked" },
        ...fields.map(([label, value]) => h(P.PropertyList.Item, { key: label, label: t(label) }, value)),
      ),
    );
  }

  function spousePhoto(P, h, party) {
    // Avatar preserves the intended photograph and falls back to initials when a
    // submitted file is unavailable; it never renders an error message in the card.
    return h(P.Avatar, {
      src: party.photo_url || undefined,
      name: party.name,
      size: "xl",
      label: party.name,
      className: "ctm-spouse-photo",
    });
  }

  function spouseHeaderTitle(P, h, t, party) {
    const fact = (label, value, data) => h(
      "span",
      { className: "ctm-spouse-header__fact" },
      h(P.Text, { as: "span", variant: "caption" }, label),
      data ? h(P.Text, { as: "span", variant: "data" }, value) : value,
    );
    return h(
      "span",
      { className: "ctm-spouse-header" },
      h(P.Text, { as: "span", variant: "strong", className: "ctm-spouse-header__name" }, party.name),
      party.reference ? fact(t("ctmId"), party.reference, true) : null,
      fact(
        t("portalAccount"),
        h(P.Badge, { tone: party.can_receive ? "success" : "waiting" }, t(party.can_receive ? "registered" : "notRegistered")),
        false,
      ),
    );
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
          {
            icon: spousePhoto(P, h, party),
            key: party.id,
            title: spouseHeaderTitle(P, h, t, party),
            collapsible: true,
            defaultExpanded: false,
            strings: { collapse: t("collapse"), expand: t("expand") },
          },
          h(
            P.Stack,
            { gap: "lg" },
            h(
              P.Stack,
              { gap: "section", className: "ctm-spouse-profile-sections" },
              spouseProfileSection(P, h, t, t("personalDetails"), "person", [
                ["otherNamesKnownBy", party.profile?.personal?.other_names],
                ["placeOfBirth", party.profile?.personal?.place_of_birth],
                ["nationality", party.profile?.personal?.nationality],
                ["awarenessOfApplication", party.profile?.personal?.awareness_of_application],
              ]),
              spouseProfileSection(P, h, t, t("contact"), "message", [
                ["address", party.profile?.contact?.address],
                ["mobileNumber", party.profile?.contact?.mobile],
                ["emailAddress", party.profile?.contact?.email],
                ["immigrationStatus", party.profile?.contact?.immigration_status],
                ["residingWith", party.profile?.contact?.residing_with],
              ], true),
              spouseProfileSection(P, h, t, t("career"), "document", [
                ["education", party.profile?.career?.education],
                ["yearOfGraduation", party.profile?.career?.graduation_year],
                ["occupation", party.profile?.career?.occupation],
              ]),
              spouseProfileSection(P, h, t, t("churchAffiliation"), "settings-users", [
                ["denomination", party.profile?.church_affiliation?.denomination],
                ["nameOfBishop", party.profile?.church_affiliation?.bishop],
                ["diocese", party.profile?.church_affiliation?.diocese],
                ["parishName", party.profile?.church_affiliation?.parish],
                ["fatherOfConfession", party.profile?.church_affiliation?.confessor],
              ]),
            ),
          ),
        ),
      ),
      !record.parties.length ? h(P.EmptyState, { title: t("noParties") }) : null,
      manage && record.status === "open" && record.parties.length < 2
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

  function CaseHearings({ api, lang, user, caseId, onSession, onDecision }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang),
      bt = base.translator(lang);
    const [tab, setTab] = R.useState("current");
    const [attendanceOpen, setAttendanceOpen] = R.useState(false);
    const [outcomeKind, setOutcomeKind] = R.useState("recommendation");
    const [recommendation, setRecommendation] = R.useState("");
    const [saving, setSaving] = R.useState(false);
    const [notice, setNotice] = R.useState(null);
    const [failure, setFailure] = R.useState(null);
    const [state, retry] = base.useLoad(
      () =>
        api("/api/sessions/").then(async (sessions) => {
          const recent = (sessions.items || []).slice(0, 100);
          const agendas = await Promise.all(recent.map((session) =>
            api(`/api/sessions/${encodeURIComponent(session.id)}/agenda/`).then((data) => ({ session, items: data.items }))));
          const rows = [];
          for (const { session, items } of agendas)
            for (const item of items || []) if (item.case_id === caseId && item.part === 2) rows.push({ session, item });
          return rows.sort((a, b) => b.session.date.localeCompare(a.session.date));
        }),
      [caseId],
    );
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const rows = state.data || [];
    const current = rows.find(({ session, item }) => session.state !== "closed" && item.state !== "heard") || rows[0] || null;
    const past = rows.filter((row) => row !== current);
    const title = (row) => {
      const names = row.item.party_names || [];
      return names.length >= 2 ? `${base.isolate(names[0])} vs. ${base.isolate(names[1])}` : base.hearingTitle(names, row.session.date, bt);
    };
    const hearingId = current?.item?.hearing_id;
    const saveRecommendation = async () => {
      if (!String(recommendation).trim()) { setFailure(t("recommendationRequired")); return; }
      if (!hearingId) { setFailure(bt("outcomeDependency")); return; }
      setSaving(true); setFailure(null);
      try {
        await api(`/api/hearings/${encodeURIComponent(hearingId)}/outcome/`, { method: "POST", body: JSON.stringify({ internal_text: "", recommendations: recommendation.trim() }) });
        setNotice(t("recommendationSaved"));
      } catch (error) { setFailure(base.serverMessage(error, bt)); }
      finally { setSaving(false); }
    };
    const attendance = current && attendanceOpen
      ? h(HearingAttendance, { api, lang, user, sessionId: current.session.id, hearingId, onClose: () => setAttendanceOpen(false) })
      : null;
    const outcome = current ? h(P.Panel, { icon: "document", title: t("outcome") },
      h(P.RadioGroup, { label: t("outcome"), layout: "row", value: outcomeKind, onChange: setOutcomeKind,
        options: [{ value: "decision", label: t("decisionMade") }, { value: "recommendation", label: t("recommendationOnly") }] }),
      outcomeKind === "decision"
        ? h(P.Inline, { justify: "between" }, h(P.Text, { variant: "secondary" }, t("decisionOutcomeHelp")), h(P.Button, { icon: "open", onClick: onDecision }, t("decisionVoting")))
        : h(P.Stack, { gap: "md" }, h(P.Textarea, { rows: 6, autoGrow: true, value: recommendation, disabled: saving || !hearingId, onChange: (event) => setRecommendation(event.target.value) }), h(P.Inline, { justify: "end" }, h(P.Button, { variant: "primary", loading: saving, disabled: saving || !hearingId, onClick: saveRecommendation }, t("saveRecommendation")))),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, notice) : null,
      failure ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
    ) : h(P.EmptyState, { title: t("noHearings") });
    const currentContent = current ? h(P.Stack, { gap: "lg" },
      h("header", { className: "plx-entity-header ctm-hearing-header" }, h("div", { className: "plx-entity-header__layout" },
        h("div", { className: "plx-entity-header__main" }, h("div", { className: "plx-entity-header__lead" },
          h("div", { className: "plx-entity-header__heading" },
            h("span", { className: "plx-entity-header__media" }, h("span", { className: "plx-entity-header__tile", "data-plx-media-hue": "green", "aria-hidden": true }, h(P.Icon, { name: "calendar", size: "lg" }))),
            h("div", { className: "plx-entity-header__text" }, h("h1", { className: "plx-entity-header__title" }, title(current)), h("p", { className: "plx-entity-header__subtitle" }, `${bt("councilSession")} ${current.session.date}`)),
          ),
        )),
        h("div", { className: "plx-entity-header__aside" }, h(P.Stack, { gap: "xs", align: "end" },
          h(P.Button, { className: "ctm-session-header-action", size: "sm", icon: "calendar", disabled: !current.session.can_reschedule, onClick: () => onSession(current.session.id) }, t("rescheduleHearing")),
          h(P.Button, { className: "ctm-session-header-action", size: "sm", icon: "settings-users", onClick: () => setAttendanceOpen((open) => !open) }, t("councilAttendance")),
        )),
      )),
      attendance,
      outcome,
    ) : h(P.EmptyState, { title: t("noHearings") });
    const pastContent = past.length ? h(P.Stack, { gap: "md" }, ...past.map((row) => h(P.Panel, { key: row.item.id, icon: "calendar", title: title(row), description: `${bt("councilSession")} ${row.session.date}` }, h(P.Inline, { justify: "end" }, h(P.Button, { size: "sm", icon: "open", onClick: () => onSession(row.session.id) }, bt("open")))))) : h(P.EmptyState, { title: t("noHearings") });
    return h(P.Tabs, { variant: "contained", label: t("hearingsTitle"), value: tab, onChange: setTab,
      items: [{ value: "current", label: t("currentHearing", { date: current?.session?.date || "—" }), content: currentContent }, { value: "past", label: t("pastHearings"), content: pastContent }] });
  }

  function HearingAttendance({ api, lang, user, sessionId, hearingId, onClose }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang), bt = base.translator(lang);
    const [state, retry] = base.useLoad(() => hearingId ? api(`/api/sessions/${encodeURIComponent(sessionId)}/attendance/?hearing_id=${encodeURIComponent(hearingId)}`) : Promise.resolve({ items: [] }), [sessionId, hearingId]);
    const [saving, setSaving] = R.useState(false), [failure, setFailure] = R.useState(null);
    const record = async (memberId, present) => { setSaving(true); setFailure(null); try { await api(`/api/sessions/${encodeURIComponent(sessionId)}/attendance/`, { method: "POST", body: JSON.stringify({ member_id: memberId, present, hearing_id: hearingId }) }); retry(); } catch (error) { setFailure(base.serverMessage(error, bt)); } finally { setSaving(false); } };
    return h(P.Panel, { icon: "settings-users", title: t("councilAttendance"), description: t("councilAttendanceHelp"), actions: h(P.Button, { size: "sm", onClick: onClose }, t("cancel")) },
      state.pending ? base.loadingView(P, h, t) : state.error ? base.loadFailure(P, h, t, retry, state.error) : h(P.Stack, { gap: "sm" }, ...(state.data.items || []).map((row) => h(P.RadioGroup, { key: row.member_id, label: row.member_name, layout: "row", value: row.present ? "present" : "absent", onChange: (value) => record(row.member_id, value === "present"), options: [{ value: "present", label: bt("presentLabel"), disabled: saving || !hearingId || user?.role === "member" }, { value: "absent", label: bt("absentLabel"), disabled: saving || !hearingId || user?.role === "member" }] })), failure ? h(P.Notice, { tone: "danger" }, failure) : null));
  }

  // ---------- Petition and council notes ----------
  // Formal petitions preserve only petition material. Identity and application profile
  // details are presented in Spouses from the immutable case-detail projection.

  const PETITION_PROFILE_CODES = new Set([
    "first_name", "last_name", "birth_date", "gender", "marriage_date",
    "spouse_name", "spouse_birth_date", "spouse_gender",
    "other_names", "aliases", "birth_country", "place_of_birth", "nationality",
    "aware_of_application", "awareness_of_application", "address", "mobile", "mobile_number",
    "email", "email_address", "immigration_status", "residing_with", "education",
    "graduation_year", "year_of_graduation", "occupation", "denomination", "bishop",
    "name_of_bishop", "diocese", "parish", "parish_name", "confessor", "father_of_confession",
    "married_outside_coptic_church", "outside_coptic_church", "religious_denomination_officiating",
    "outside_denomination", "date_of_marriage_outside_coptic_church", "outside_marriage_date",
    "church_marriage_date", "officiating_priest", "marriage_officiant", "church_name",
    "marriage_church_name", "church_location", "church_address", "marriage_church_location",
    "marriage_diocese", "church_diocese",
  ]);

  function casePetitions(items, caseId) {
    return (items || []).filter((row) => row && row.kind === "petition" && row.case_id === caseId);
  }

  function petitionAnswers(answers) {
    return Object.entries(answers || {}).filter(([code]) => !PETITION_PROFILE_CODES.has(code) && !code.startsWith("spouse_"));
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

  function PetitionWorkspace({ api, lang, caseId }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang), bt = base.translator(lang);
    const [state, retry] = base.useLoad(() => api("/api/applications/").then((apps) => ({ petitions: casePetitions(apps.items, caseId) })), [caseId]);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { petitions } = state.data;
    return h(P.Stack, { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("petitionTitle")),
      ...petitions.map((row) => {
        const answers = petitionAnswers(row.answers);
        return h(P.Panel, { icon: "doc-text", key: row.id, title: t("petition"), description: [bt("state_" + row.status), row.submitted_at ? base.formatWhen(row.submitted_at, lang) : null].filter(Boolean).join(" · "), collapsible: true },
          h(P.Stack, { gap: "sm" },
            answers.length ? h(P.PropertyList, { layout: "stacked" }, ...answers.map(([code, value]) => h(P.PropertyList.Item, { key: code, label: base.fieldLabel(row, code, lang) || code }, base.answerText(value, bt)))) : h(P.EmptyState, { title: bt("noAnswers") }),
          ),
        );
      }),
      !petitions.length ? h(P.EmptyState, { title: t("noPetitions") }) : null,
    );
  }

  function CaseNotesWorkspace({ api, lang, user, caseId }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/cases/${encodeURIComponent(caseId)}/`).then(async (record) => {
      const proceeding = openProceeding(record) || [...(record.proceedings || [])].sort((a, b) => (b.sequence || 0) - (a.sequence || 0))[0] || null;
      const notes = proceeding ? await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/notes/`) : { items: [] };
      return { record, proceeding, notes: latestNotes(notes.items) };
    }), [caseId]);
    const [text, setText] = R.useState("");
    const [selected, select] = R.useState(null);
    const [editing, setEditing] = R.useState(null);
    const [composing, setComposing] = R.useState(false);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, proceeding, notes } = state.data;
    const canWrite = writerFor(user, null, record) && proceeding && proceeding.status === "open";
    async function save(event) {
      event.preventDefault();
      if (!text.trim()) { setFailure(t("noteRequired")); return; }
      setPending(true); setFailure(null);
      try {
        await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/notes/`, { method: "POST", body: JSON.stringify(editing ? { text: text.trim(), note_id: editing } : { text: text.trim() }) });
        setText(""); setEditing(null); setComposing(false); setNotice("noteSaved"); retry();
      } catch (error) { setFailure(base.serverMessage(error, t)); }
      finally { setPending(false); }
    }
    const noteDialog = composing ? h(P.Dialog, { open: true, title: t(editing ? "editingNote" : "addNote"), size: "lg", onClose: () => !pending && setComposing(false) },
      h(P.Form, { onSubmit: save, label: t(editing ? "editingNote" : "addNote"), noValidate: true },
        h(P.Field, { label: t(editing ? "editingNote" : "addNote"), description: editing ? t("editNoteHelp") : undefined }, h(P.Textarea, { rows: 5, autoGrow: true, value: text, maxLength: 50000, disabled: pending, onChange: (e) => { setText(e.target.value); setFailure(null); } })),
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
        h(P.FormActions, { sticky: false }, h(P.Button, { disabled: pending, onClick: () => setComposing(false) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t(editing ? "saveRevision" : "saveNote"))),
      ),
    ) : null;
    return h(R.Fragment, null, noteDialog,
      h(P.Stack, { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
        h(P.Toolbar, { label: t("internalNotes") }, canWrite ? h(P.Button, { variant: "primary", icon: "add", onClick: () => { setEditing(null); setText(""); setFailure(null); setComposing(true); } }, t("addNote")) : null),
        h(P.Text, { as: "p", variant: "secondary" }, t("internalNotesHelp")),
        notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
        h(window.CTMShell.Workspace, {
          label: t("internalNotes"), selected, onSelect: select,
          rows: notes.map((note) => ({ ...note, id: note.note_id, title: note.author || t("note"), preview: note.text, recorded: base.formatWhen(note.timestamp, lang) })), empty: t("noNotes"),
          columns: [{ title: t("note"), field: "title", kind: "name" }, { title: t("recordedAt"), field: "recorded" }, { title: t("note"), field: "preview", kind: "wrap" }],
        }, (note) => note ? h(P.Stack, { gap: "md" }, h(P.Text, { as: "h2", variant: "title" }, note.title), h(P.Text, { variant: "secondary" }, `${t("version")} ${note.version} · ${note.recorded}`), h(P.Text, { as: "p" }, note.text), note.can_edit && canWrite ? h(P.Button, { size: "sm", icon: "edit", onClick: () => { setEditing(note.note_id); setText(note.text); setFailure(null); setComposing(true); } }, t("editNote")) : null) : h(P.EmptyState, { title: t("noNotes") })),
      ),
    );
  }
  function marriageDuration(dateValue, lang) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(dateValue || ""))) return null;
    const start = new Date(`${dateValue}T00:00:00`), today = new Date();
    let months = (today.getFullYear() - start.getFullYear()) * 12 + today.getMonth() - start.getMonth();
    if (today.getDate() < start.getDate()) months -= 1;
    if (months < 0) return null;
    const years = Math.floor(months / 12), remainder = months % 12;
    return lang === "ar" ? `${years} سنة و${remainder} شهر` : `${years} years, ${remainder} months`;
  }

  function councilCardValues(record, scope, submitted) {
    const edit = record.council_edits?.[scope]?.value;
    return edit && typeof edit === "object" && !Array.isArray(edit) ? { ...submitted, ...edit } : submitted;
  }

  // Council cards use the same field grid in read and edit modes. Read controls
  // intentionally preserve the form layout while preventing direct changes.
  function CaseReadFields({ P, h, fields, values, className = "" }) {
    return h("div", { className: `ctm-case-edit-grid ctm-case-read-grid ${className}`.trim() },
      ...fields.map(([key, label, type = "text"]) => {
        const value = values[key];
        const validDate = type === "date" && /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
        return h(P.Field, { key, label }, h(P.Input, { type: validDate ? "date" : "text", value: value === undefined || value === null || value === "" ? "—" : String(value), readOnly: true, tabIndex: -1 }));
      }),
    );
  }

  function CaseMarriage({ api, lang, user, caseId }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/cases/${encodeURIComponent(caseId)}/`), [caseId]);
    const [editing, setEditing] = R.useState(false);
    const [form, setForm] = R.useState({});
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const record = state.data;
    const marriage = councilCardValues(record, "marriage", record.marriage || {}), value = (item) => item || "—";
    const proceeding = openProceeding(record);
    const canWrite = writerFor(user, null, record) && proceeding?.status === "open";
    const fields = [
      ["outside_coptic_church", t("marriedOutsideCoptic"), "text"],
      ["outside_denomination", t("outsideDenomination"), "text"],
      ["outside_marriage_date", t("outsideMarriageDate"), "date"],
      ["church_marriage_date", t("churchMarriageDate"), "date"],
      ["officiating_priest", t("officiatingPriest"), "text"],
      ["church_name", t("churchName"), "text"],
      ["church_location", t("churchLocation"), "text"],
      ["diocese", t("diocese"), "text"],
    ];
    const startEditing = () => { setForm(Object.fromEntries(fields.map(([key]) => [key, marriage[key] || ""]))); setFailure(null); setEditing(true); };
    const save = async (event) => {
      event.preventDefault();
      setPending(true); setFailure(null);
      try {
        await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/findings/`, {
          method: "POST", body: JSON.stringify({ fact_code: "case_card.marriage", value: form }),
        });
        setEditing(false); retry();
      } catch (error) { setFailure(base.serverMessage(error, t)); }
      finally { setPending(false); }
    };
    return h(P.Stack, { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("marriageTitle")),
      h(P.Panel, { icon: "settings-users", title: t("churchMarriage"), actions: canWrite && !editing ? h(P.Button, { size: "sm", onClick: startEditing }, "Edit") : null },
        h(P.Stack, { gap: "md" },
          editing ? h(P.Form, { onSubmit: save, label: t("churchMarriage"), noValidate: true },
            h("div", { className: "ctm-case-edit-grid" }, ...fields.map(([key, label, type]) => h(P.Field, { key, label }, h(P.Input, { type, value: form[key], disabled: pending, onChange: (event) => setForm((old) => ({ ...old, [key]: event.target.value })) })))),
            failure ? h(P.Notice, { tone: "danger" }, failure) : null,
            h(P.FormActions, { sticky: false }, h(P.Button, { disabled: pending, onClick: () => setEditing(false) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, "Save")),
          ) : h(CaseReadFields, { P, h, fields: [
            ["outside_coptic_church", t("marriedOutsideCoptic")], ["outside_denomination", t("outsideDenomination")], ["outside_marriage_date", t("outsideMarriageDate"), "date"],
            ["church_marriage_date", t("churchMarriageDate"), "date"], ["officiating_priest", t("officiatingPriest")], ["marriage_duration", t("marriageDuration")],
            ["church_name", t("churchName")], ["church_location", t("churchLocation")], ["diocese", t("diocese")],
          ], values: { ...marriage, marriage_duration: marriageDuration(marriage.church_marriage_date, lang) } }),
        ),
      ),
    );
  }

  function CouncilEditablePanel({ api, P, h, t, user, record, scope, title, icon, fields, values, onSaved }) {
    const R = window.React;
    const [editing, setEditing] = R.useState(false);
    const [form, setForm] = R.useState({});
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const proceeding = openProceeding(record);
    const canWrite = writerFor(user, null, record) && proceeding?.status === "open";
    const startEditing = () => { setForm(Object.fromEntries(fields.map(([key]) => [key, values[key] || ""]))); setFailure(null); setEditing(true); };
    const save = async (event) => {
      event.preventDefault();
      setPending(true); setFailure(null);
      try {
        await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/findings/`, {
          method: "POST", body: JSON.stringify({ fact_code: `case_card.${scope}`, value: form }),
        });
        setEditing(false); onSaved();
      } catch (error) { setFailure(base.serverMessage(error, t)); }
      finally { setPending(false); }
    };
    return h(P.Panel, { title, icon, actions: canWrite && !editing ? h(P.Button, { size: "sm", onClick: startEditing }, "Edit") : null }, h(P.Stack, { gap: "md" },
      editing ? h(P.Form, { onSubmit: save, label: title, noValidate: true },
        h("div", { className: "ctm-case-edit-grid" }, ...fields.map(([key, label, type = "text"]) => h(P.Field, { key, label }, h(P.Input, { type, value: form[key], disabled: pending, onChange: (event) => setForm((old) => ({ ...old, [key]: event.target.value })) })))),
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
        h(P.FormActions, { sticky: false }, h(P.Button, { disabled: pending, onClick: () => setEditing(false) }, t("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, "Save")),
      ) : h(CaseReadFields, { P, h, fields, values }),
    ));
  }

  function CaseSeparation({ api, lang, user, caseId }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/cases/${encodeURIComponent(caseId)}/`), [caseId]);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const record = state.data, separation = record.separation || {};
    const initiator = separation.initiated_by;
    const initiatorValue = initiator?.party ? `${initiator.party.name} (${initiator.party.slot === "A" ? "Applicant" : "Spouse"})` : initiator?.value;
    const details = councilCardValues(record, "separation_details", { marital_status: separation.marital_status, separation_date: separation.separation_date, initiated_by: initiatorValue, reason: separation.reason });
    const civil = councilCardValues(record, "civil_divorce", separation.civil_divorce || {});
    const reconciliation = councilCardValues(record, "reconciliation", separation.reconciliation || {});
    const order = councilCardValues(record, "restraining_order", separation.restraining_orders?.[0] || {});
    return h(P.Stack, { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("separation")),
      h(CouncilEditablePanel, { api, P, h, t, user, record, onSaved: retry, scope: "separation_details", title: "Separation Details", icon: "move", values: details, fields: [["marital_status", "Current Marital Status"], ["separation_date", "Date of Separation", "date"], ["initiated_by", "Initiated By"], ["reason", "Reason for Divorce"]] }),
      h(CouncilEditablePanel, { api, P, h, t, user, record, onSaved: retry, scope: "civil_divorce", title: "Civil Divorce", icon: "document", values: civil, fields: [["filed", "Civil Divorce Filed?"], ["date", "Date of Civil Divorce", "date"], ["court", "Name of Court"], ["location", "Court Street Address / Location"], ["case_number", "Civil Case Number"], ["status", "Civil Divorce Status"]] }),
      h(CouncilEditablePanel, { api, P, h, t, user, record, onSaved: retry, scope: "restraining_order", title: "Restraining Order", icon: "link", values: order, fields: [["filed", "Restraining Order Filed?"], ["date", "Date of Restraining Order", "date"], ["expiration_date", "Restraining Order Expiration Date", "date"], ["name_listed", "Name Listed on Order"], ["court", "Name of Court"], ["case_number", "Restraining Order Case Number"], ["status", "Restraining Order Status"]] }),
      h(CouncilEditablePanel, { api, P, h, t, user, record, onSaved: retry, scope: "reconciliation", title: "Reconciliation", icon: "settings-users", values: reconciliation, fields: [["attempted", "Clergy Counseling / Reconciliation Attempted?"], ["previously_applied", "Previously Applied for Ecclesiastical Marriage Permit?"], ["when", "When Did You Previously Apply?"], ["where", "Where Did You Previously Apply?"], ["outcome", "Decision Outcome"]] }),
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
  function isSubmittedDate(value) {
    return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
  }

  function summaryDate(value, lang) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(lang === "ar" ? "ar-EG" : "en-US", {
      dateStyle: "medium",
      ...(isSubmittedDate(value) ? { timeZone: "UTC" } : {}),
    }).format(date);
  }

  function summaryFacts(record, requests, versions, audit) {
    const latest = Array.isArray(versions) && versions.length ? [...versions].sort((a, b) => b.number - a.number)[0] : null;
    return {
      pendingRequests: (requests || []).filter((r) => r.state === "sent" && !["medical", "psychological"].includes(r.kind)).length,
      draftRequests: (requests || []).filter((r) => r.state === "draft" && !["medical", "psychological"].includes(r.kind)).length,
      audit: audit || [],
      decision: latest
        ? { type: latest.type, approved: Boolean(latest.approval), issued: Boolean(latest.decree && latest.decree.issued_at), issuedAt: latest.decree?.issued_at || null, number: latest.number }
        : null,
      openProceeding: openProceeding(record),
    };
  }

  function CaseSummary({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [summaryEditing, setSummaryEditing] = R.useState(false);
    const [summaryForm, setSummaryForm] = R.useState(null);
    const [summaryPending, setSummaryPending] = R.useState(false);
    const [summaryFailure, setSummaryFailure] = R.useState(null);
    const [state, retry] = base.useLoad(
      () =>
        api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => withAssignee(api, r)).then(async (record) => {
          const [requests, members, audit] = await Promise.all([
            api(`/api/cases/${encodeURIComponent(caseId)}/requests/`),
            record.can_assign ? api("/api/council/members/") : Promise.resolve({ items: [] }),
            api(`/api/cases/${encodeURIComponent(caseId)}/audit/`),
          ]);
          const proceeding = openProceeding(record) || [...(record.proceedings || [])].sort((a, b) => (b.sequence || 0) - (a.sequence || 0))[0];
          let versions = null;
          if (proceeding) {
            try {
              versions = (await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/decision/`)).items || null;
            } catch (error) {
              if (error.status !== 405) throw error;
            }
          }
          return { record, members: members.items, facts: summaryFacts(record, requests.items, versions, audit.items) };
        }),
      [caseId],
    );
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, members, facts } = state.data;
    const bt = base.translator(lang);
    const manager =
      record.assignment_history && record.assignment_history.length
        ? record.assignment_history[record.assignment_history.length - 1].member
        : record.assigned_member || null;
    const eligibleMembers = base.assignableMembers(members);
    const presidents = base.assignmentAuthorizers(members);
    const submittedSummary = record.summary || {};
    const summary = councilCardValues(record, "summary", submittedSummary);
    const applicant = record.parties.find((party) => party.slot === "A") || record.parties[0] || null;
    const respondent = record.parties.find((party) => party.slot === "B") || record.parties[1] || null;
    const personPill = (party) => {
      if (!party) return "—";
      const gender = party.gender === "M" ? "male" : party.gender === "F" ? "female" : undefined;
      return gender ? h(P.DataPill, { gender, className: "ctm-case-summary-person-pill" }, party.name) : h(P.DataPill, { person: true, className: "ctm-case-summary-person-pill" }, party.name);
    };
    const latestAudit = (action) => [...facts.audit].filter((row) => row.action === action).sort((a, b) => String(b.timestamp).localeCompare(String(a.timestamp)))[0];
    const summaryTimeline = [];
    const timelineBadge = (tone, label) => h(P.Badge, { tone, size: "sm" }, label);
    summaryTimeline.push({
      id: "decree", title: t("decreeIssued"), time: facts.decision?.issued ? summaryDate(facts.decision.issuedAt, lang) : t("pending"),
      badge: timelineBadge(facts.decision?.issued ? "success" : "neutral", facts.decision?.issued ? t("completed") : t("upcoming")),
    });
    summaryTimeline.push({
      id: "decision", title: t("councilReviewDecision"), time: facts.decision?.approved ? t("approved") : t("pending"),
      description: facts.decision?.approved ? null : t("awaitingCouncilReview"),
      badge: timelineBadge(facts.decision?.approved ? "success" : "neutral", facts.decision?.approved ? t("completed") : t("upcoming")),
    });
    if (record.status === "open") summaryTimeline.push({
      id: "recommendation", title: t("recommendationPending"), time: t("inProgress"),
      description: manager ? t("awaitingRecommendation", { member: manager }) : bt("unassigned"),
      badge: timelineBadge("success", t("current")),
    });
    const hearing = latestAudit("case_heard");
    if (hearing) summaryTimeline.push({
      id: `hearing-${hearing.id}`, title: t("hearing"), time: summaryDate(hearing.timestamp, lang), description: auditLabel(hearing.action, lang), badge: timelineBadge("active", t("completed")),
    });
    const assigned = latestAudit("case_assigned");
    if (assigned) summaryTimeline.push({
      id: `assigned-${assigned.id}`, title: t("caseAssigned"), time: summaryDate(assigned.timestamp, lang),
      description: manager || null,
      badge: timelineBadge("active", t("completed")),
    });
    const filed = latestAudit("application_submitted");
    if (summary.filing_date) summaryTimeline.push({
      id: "filed", title: t("caseFiled"), time: summaryDate(filed?.timestamp || summary.filing_date, lang), description: t("caseFiledDescription"), badge: timelineBadge("active", t("completed")),
    });
    const applicationDates = [
      { id: "church-marriage", title: t("churchMarriageDate"), date: record.marriage?.church_marriage_date },
      { id: "outside-marriage", title: t("outsideMarriageDate"), date: record.marriage?.outside_marriage_date },
      { id: "separation", title: t("dateOfSeparation"), date: record.separation?.separation_date },
      { id: "civil-divorce", title: t("dateOfCivilDivorce"), date: record.separation?.civil_divorce?.date },
      ...(record.separation?.restraining_orders || []).flatMap((order, index) => [
        { id: `restraining-order-${index}`, title: t("dateOfRestrainingOrder"), date: order.date },
        { id: `restraining-order-expiration-${index}`, title: t("restrainingOrderExpirationDate"), date: order.expiration_date },
      ]),
    ];
    for (const applicationDate of applicationDates.filter((item) => isSubmittedDate(item.date)))
      summaryTimeline.push({
        ...applicationDate,
        time: summaryDate(applicationDate.date, lang),
        badge: timelineBadge("active", t("completed")),
      });
    const canEditSummary = writerFor(user, null, record) && openProceeding(record)?.status === "open";
    const childLabel = (child) => typeof child === "string" ? child : child?.name || "—";
    const childrenText = (children) => (children || []).map(childLabel).filter((value) => value && value !== "—").join("\n");
    const startSummaryEdit = () => {
      setSummaryFailure(null);
      setSummaryForm({ reason: summary.reason || "", children: childrenText(summary.children), memberId: eligibleMembers.find((member) => member.name === manager)?.id || "", presidentId: "" });
      setSummaryEditing(true);
    };
    const saveSummary = async (event) => {
      event.preventDefault();
      const nextMemberId = summaryForm.memberId;
      const currentMemberId = eligibleMembers.find((member) => member.name === manager)?.id || "";
      if (nextMemberId && nextMemberId !== currentMemberId && !summaryForm.presidentId) { setSummaryFailure(bt("choosePresident")); return; }
      setSummaryPending(true); setSummaryFailure(null);
      try {
        if (nextMemberId && nextMemberId !== currentMemberId) await api(`/api/cases/${encodeURIComponent(caseId)}/assignment/`, { method: "POST", body: JSON.stringify({ member_id: nextMemberId, president_id: summaryForm.presidentId }) });
        await api(`/api/proceedings/${encodeURIComponent(openProceeding(record).id)}/findings/`, { method: "POST", body: JSON.stringify({ fact_code: "case_card.summary", value: { reason: summaryForm.reason.trim(), children: summaryForm.children.split(/\r?\n/).map((name) => name.trim()).filter(Boolean).map((name) => ({ name })) } }) });
        setSummaryEditing(false); retry();
      } catch (error) { setSummaryFailure(base.serverMessage(error, bt)); }
      finally { setSummaryPending(false); }
    };
    const summaryReadFields = [
      ["case_number", t("caseNumber")], ["filing_date", t("filingDate")], ["status", bt("statusLabel")], ["assigned_member", t("assignedCouncilMember")],
      ["applicant", t("applicant")], ["respondent", t("respondent")], ["reason", t("reasonForDivorce")], ["marriage_duration", t("marriageDuration")],
      ["children", t("children")], ["last_hearing_date", t("lastHearingDate")],
    ];
    const summaryReadValues = {
      case_number: record.number, filing_date: summaryDate(summary.filing_date, lang), status: record.status === "open" ? t("active") : bt("closed"), assigned_member: manager || bt("unassigned"),
      applicant: applicant?.name, respondent: respondent?.name, reason: summary.reason, marriage_duration: marriageDuration(record.marriage?.church_marriage_date, lang),
      children: summary.children?.length ? summary.children.map(childLabel).join(" · ") : t("noChildren"), last_hearing_date: summaryDate(summary.last_hearing_date, lang),
    };
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, record.number),
      h(
        P.Panel,
        { icon: "document", title: t("caseSummary"), actions: canEditSummary && !summaryEditing ? h(P.Button, { size: "sm", onClick: startSummaryEdit }, "Edit") : null },
        summaryEditing
          ? h(P.Form, { onSubmit: saveSummary, label: t("caseSummary"), noValidate: true },
              h("div", { className: "ctm-case-edit-grid" },
                h(P.Field, { label: t("reasonForDivorce") }, h(P.Input, { value: summaryForm.reason, disabled: summaryPending, onChange: (event) => setSummaryForm((old) => ({ ...old, reason: event.target.value })) })),
                h(P.Field, { label: t("assignedCouncilMember") }, h(P.Select, { value: summaryForm.memberId, disabled: summaryPending || !record.can_assign, onChange: (event) => setSummaryForm((old) => ({ ...old, memberId: event.target.value, presidentId: "" })), options: [{ value: "", label: bt("unassigned") }, ...eligibleMembers.map((member) => ({ value: member.id, label: member.name || member.id }))] })),
                summaryForm.memberId && summaryForm.memberId !== (eligibleMembers.find((member) => member.name === manager)?.id || "") ? h(P.Field, { label: bt("president"), required: true }, h(P.Select, { value: summaryForm.presidentId, disabled: summaryPending, onChange: (event) => setSummaryForm((old) => ({ ...old, presidentId: event.target.value })), options: [{ value: "", label: bt("choosePresident") }, ...presidents.map((member) => ({ value: member.id, label: member.name || member.id }))] })) : null,
              ),
              h(P.Field, { label: t("children"), description: "One child per line. Submitted child details remain with the application." }, h(P.Textarea, { rows: 4, value: summaryForm.children, disabled: summaryPending, onChange: (event) => setSummaryForm((old) => ({ ...old, children: event.target.value })) })),
              summaryFailure ? h(P.Notice, { tone: "danger" }, summaryFailure) : null,
              h(P.FormActions, { sticky: false }, h(P.Button, { disabled: summaryPending, onClick: () => setSummaryEditing(false) }, bt("cancel")), h(P.Button, { type: "submit", variant: "primary", loading: summaryPending, disabled: summaryPending }, "Save")),
            )
          : h(CaseReadFields, { P, h, fields: summaryReadFields, values: summaryReadValues, className: "ctm-case-summary-fields" }),
      ),
      h(
        P.Panel,
        { icon: "calendar", title: t("keyDates") },
        h(P.Timeline, { label: t("keyDates"), items: summaryTimeline }),
      ),
    );
  }

  Object.assign(window.CTMCouncil, {
    caseWords: words,
    caseTranslator: translator,
    InterviewForm, // exported for the unsaved-text regression test
    RequestDetail,
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
    petitionAnswers,
    latestNotes,
    latestFindings,
    PetitionWorkspace: base.guarded(PetitionWorkspace),
    CaseNotesWorkspace: base.guarded(CaseNotesWorkspace),
    marriageDuration,
    CaseMarriage: base.guarded(CaseMarriage),
    CaseSeparation: base.guarded(CaseSeparation),
    timelineRows,
    summaryFacts,
    CaseSummary: base.guarded(CaseSummary),
    CaseTimeline: base.guarded(CaseTimeline),
  });
})();
