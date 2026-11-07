/* CTM council workspace module. Plenix stays on the pinned external CDN.
   The server enforces every permission; capability checks here only decide
   which controls to show and never stand in for authorization. */
(() => {
  "use strict";

  const ADMIN_ROLES = new Set(["admin", "secretary"]);
  const DATE = /^\d{4}-\d{2}-\d{2}$/;
  const OPEN_SESSION_STATES = new Set(["draft", "planned"]);

  // ---------- Pure logic (unit tested in tests/frontend/council.test.cjs) ----------

  // Unicode first-strong isolate: keeps names, case numbers, references and emails
  // in their own direction inside Arabic (RTL) sentences (F34). Invisible.
  function isolate(value) {
    const text = value === null || value === undefined ? "" : String(value);
    return text ? `\u2068${text}\u2069` : text;
  }

  // Unsaved report text, kept in page memory only (never browser storage), so moving to another
  // page inside CTM and back restores it instead of discarding it. A reload or sign-out clears it;
  // the editors warn before the page unloads.
  const unsavedDrafts = new Map();

  function canManage(user) {
    return Boolean(user && user.portal === "council" && ADMIN_ROLES.has(user.role));
  }

  function awaitingReview(items) {
    return (items || []).filter(
      // Closed-case first filings go to council consideration, not completeness review (F12).
      (row) => row && row.kind === "petition" && row.status === "submitted" && row.origin !== "closed_case_intake",
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

  function todayInLosAngeles(now = new Date()) {
    const p = Object.fromEntries(
      new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit" })
        .formatToParts(now)
        .map((x) => [x.type, x.value]),
    );
    return `${p.year}-${p.month}-${p.day}`;
  }

  // Upcoming = open sessions from today (Los Angeles), soonest first. Everything
  // else (closed, or open sessions in the past and not yet closed) is listed after.
  function splitSessions(rows, today) {
    const upcoming = (rows || []).filter((s) => OPEN_SESSION_STATES.has(s.state) && s.date >= today).sort((a, b) => a.date.localeCompare(b.date));
    const ids = new Set(upcoming.map((s) => s.id));
    const past = (rows || []).filter((s) => !ids.has(s.id)).sort((a, b) => b.date.localeCompare(a.date));
    return { upcoming, past };
  }

  function sessionBuckets(rows, today) {
    const records = rows || [];
    return {
      current: records
        .filter((session) => OPEN_SESSION_STATES.has(session.state) && session.date <= today)
        .sort((a, b) => b.date.localeCompare(a.date)),
      upcoming: records
        .filter((session) => OPEN_SESSION_STATES.has(session.state) && session.date > today)
        .sort((a, b) => a.date.localeCompare(b.date)),
      // Adjournment completes the session and immediately archives its record.
      archived: records
        .filter((session) => session.state === "closed")
        .sort((a, b) => b.date.localeCompare(a.date)),
    };
  }

  function sessionStatusKey(state) {
    if (state === "closed") return "sessionStatusAdjourned";
    if (state === "planned") return "sessionStatusInProgress";
    return "sessionStatusPlanned";
  }

  function sessionStatusTone(state) {
    if (state === "planned") return "active";
    if (state === "closed") return "neutral";
    return "waiting";
  }

  // Issue 116 (D-0039): who may press Send reminder now; the server checks the same roles.
  const REMINDER_ROLES = new Set(["secretary", "president", "admin"]);
  function canSendReminders(user) {
    return Boolean(user && user.portal === "council" && REMINDER_ROLES.has(user.role));
  }

  // Answers are open on an in-progress (planned) session until its start time.
  function sessionAnswerable(session, now = Date.now()) {
    if (!session || session.state !== "planned" || !session.starts_at) return false;
    const start = new Date(session.starts_at).getTime();
    return !Number.isNaN(start) && start > now;
  }

  // The signed-in member's latest answer: "mine" for members, their row in "members" for the secretary.
  function ownAnswer(data, user) {
    if (!data) return null;
    if ("mine" in data) return data.mine || null;
    const row = (data.members || []).find((item) => item.member_id === String(user?.id ?? ""));
    return row && row.answer ? { answer: row.answer, answered_at: row.answered_at } : null;
  }

  function answerKey(answer) {
    if (answer === "attend") return "answerAttending";
    if (answer === "not_attend") return "answerNotAttending";
    return "answerNone";
  }

  function answerTone(answer) {
    if (answer === "attend") return "success";
    if (answer === "not_attend") return "negative";
    return "neutral";
  }

  // "Confirmed n of m" only when the server sent both counts (secretary, president, admin).
  function confirmedText(data, t, key = "confirmedOf") {
    return data && Number.isInteger(data.confirmed) && Number.isInteger(data.total)
      ? t(key, { n: data.confirmed, m: data.total }) : null;
  }

  // The reminder endpoints answer in English; known refusals get their EN/AR words.
  const REMINDER_REFUSALS = {
    "Email is not set up, so reminders cannot be sent.": "emailNotSetUp",
    "A reminder was already sent in the last hour.": "reminderHourLimit",
    "Answers close when the session starts.": "answersClosed",
    "Reminders can be sent only before a planned session starts.": "remindersClosed",
    "Choose I will attend or I will not attend.": "answerChoose",
  };
  function reminderProblem(error, t) {
    const messages = error && error.data && Array.isArray(error.data.messages) ? error.data.messages : [];
    const key = messages.length === 1 ? REMINDER_REFUSALS[messages[0]] : null;
    return key ? t(key) : serverMessage(error, t);
  }

  function agendaDisplayStatus(row) {
    if (row?.state === "heard") return "closed";
    if (row?.part === 1 && !row?.assigned_member_id) return "toBeAssigned";
    return "inProgress";
  }

  function archivedAgendaRows(items) {
    const rows = (items || []).map((row) => ({
      ...row,
      applicant: {
        name: row.applicant_name || "—",
        gender: row.applicant_gender === "M" || row.applicant_gender === "male" ? "male"
          : row.applicant_gender === "F" || row.applicant_gender === "female" ? "female" : undefined,
      },
      respondent: {
        name: row.respondent_name || "—",
        gender: row.respondent_gender === "M" || row.respondent_gender === "male" ? "male"
          : row.respondent_gender === "F" || row.respondent_gender === "female" ? "female" : undefined,
      },
      status: agendaDisplayStatus(row),
    }));
    return {
      assigned: rows.filter((row) => row.part === 1),
      presented: rows.filter((row) => row.part === 2),
    };
  }

  function sessionDateProblem(value, existing, ignoreId = null) {
    if (!DATE.test(value || "")) return "dateRequired";
    const parsed = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value)
      return "dateRequired";
    if ((existing || []).some((row) => row.id !== ignoreId && row.date === value)) return "dateTaken";
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
    return `${prefix} ${isolate(first)} ${vs} ${isolate(second)} ${on} ${sessionLabel(date, t)}`;
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

  function casePlacementLabel(row) {
    const names = (row?.party_names || []).filter((name) => String(name || "").trim());
    return names.join(" | ") || row?.number || "";
  }

  function presidents(members) {
    return (members || []).filter((row) => row.role === "president");
  }

  // Assignment authority (F15): newer servers flag who may authorize and who may
  // record an assignment; one person may hold both. Older servers: President role
  // authorizes, admin/secretary record. President approval and decree signing keep
  // using presidents() (the role flag), unchanged.
  // When the server also lists assignment_authorities (holders of F15 authority,
  // which may include an admin outside the council roster), those rows are used.
  function assignmentAuthorizers(members, authorities) {
    if (Array.isArray(authorities)) return authorities.filter((m) => m.can_authorize_assignment);
    const rows = members || [];
    return rows.some((m) => typeof m.can_authorize_assignment === "boolean")
      ? rows.filter((m) => m.can_authorize_assignment)
      : presidents(rows);
  }

  function canRecordAssignment(user, members, authorities) {
    const me = (Array.isArray(authorities) ? authorities : []).find((m) => m.id === user?.id)
      || (members || []).find((m) => m.id === user?.id);
    if (me && typeof me.can_record_assignment === "boolean") return me.can_record_assignment;
    return canManage(user);
  }

  function assignableMembers(members) {
    return (members || []).filter((row) => ["president", "secretary", "member"].includes(row.role));
  }

  function assignmentProblem(memberId, presidentId, members, authorities) {
    if (!memberId) return "chooseMember";
    if (!presidentId) return "choosePresident";
    if (!assignmentAuthorizers(members, authorities).some((row) => row.id === presidentId))
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
  function agendaActions(row, session, user, caseRow, options = {}) {
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
      assign:
        planned &&
        scheduled &&
        row.part === 1 &&
        (typeof options.canRecordAssignment === "boolean" ? options.canRecordAssignment : manage),
      present,
      presentNeedsAttendance: !present && planned && scheduled && row.part === 2 && mine && typeof row.can_present === "boolean",
      outcome: row.can_record_outcome === true && Boolean(row.hearing_id),
      testimony: planned && scheduled && row.part === 2 && writerOf(user, row, caseRow),
      cancelTestimony: planned && writerOf(user, row, caseRow),
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

  function pendingAssignmentCount(items) {
    return (items || []).filter((row) => row.part === 1 && row.state !== "assigned").length;
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

  function formatSessionStart(value, lang) {
    if (!value) return null;
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return new Intl.DateTimeFormat(lang === "ar" ? "ar-EG" : "en-US", {
      dateStyle: "full",
      timeStyle: "short",
      timeZone: "America/Los_Angeles",
    }).format(d);
  }

  function formatDate(value, lang) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value || "");
    return new Intl.DateTimeFormat(lang === "ar" ? "ar-EG" : "en-US", {
      dateStyle: "medium",
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
      councilMember: "Council member",
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
      sessions: "Tribunal Sessions - Current",
      sessionsUpcoming: "Tribunal Sessions - Upcoming",
      sessionsArchived: "Tribunal Sessions - Archived",
      tribunalSession: "Tribunal Session",
      noSessions: "No current council sessions are available.",
      noUpcomingSessions: "No upcoming council sessions are scheduled.",
      noArchivedSessions: "No archived council sessions are available.",
      newSession: "New council session",
      sessionDate: "Session date",
      sessionTime: "Session time",
      presiding: "Presiding",
      location: "Location",
      timeNotRecorded: "Time not recorded",
      presidingNotRecorded: "Presiding member not recorded",
      locationNotRecorded: "Location not recorded",
      hearingAdjourned: "Hearing Adjourned",
      resumeHearing: "Resume Hearing",
      hearingAdjournedNotice: "The hearing has been adjourned.",
      hearingResumedNotice: "The hearing has resumed.",
      sessionStatusPlanned: "Draft",
      sessionStatusInProgress: "In progress",
      sessionAnswers: "Attendance answers",
      sessionAnswersHelp: "Who has said they will attend. Recorded attendance on the day is separate.",
      yourAnswer: "Your answer",
      willAttend: "I will attend",
      willNotAttend: "I will not attend",
      answerAttending: "Attending",
      answerNotAttending: "Not attending",
      answerNone: "No answer",
      answerColumn: "Answer",
      answeredAt: "Answered",
      answeredOn: "Answered {when}",
      answerSaved: "Your answer is saved.",
      answerChoose: "Choose I will attend or I will not attend.",
      answersClosed: "Answers close when the session starts.",
      answersNotOpen: "Members can answer once the session is In progress.",
      confirmedColumn: "Confirmed",
      confirmedOf: "Confirmed {n} of {m}",
      confirmedCount: "{n} of {m}",
      sendReminderNow: "Send reminder now",
      reminderHelp: "Goes to members who have not answered, at most once an hour.",
      reminderQueued: "A reminder is queued for {n} members who have not answered.",
      reminderHourLimit: "A reminder was already sent in the last hour.",
      remindersClosed: "Reminders can be sent only before a planned session starts.",
      emailNotSetUp: "Email is not set up, so reminders cannot be sent.",
      noMembers: "No active council members.",
      sessionStatusAdjourned: "Adjourned",
      sessionActivated: "The tribunal session is now in session.",
      sessionReturnedToPlanned: "The tribunal session is planned.",
      moveCase: "Move",
      transferCaseTitle: "Move case to another session",
      transferCaseHelp: "This authorized override keeps the original agenda item and records why it moved.",
      moveToSession: "Move to session",
      chooseSession: "Choose a session",
      transferReason: "Reason for move",
      transferReasonRequired: "Enter a reason for this move.",
      transferRecorded: "The case was moved and the override was recorded.",
      noTransferSessions: "No other draft or in-session sessions are available.",
      adjournSessionTitle: "Adjourn this tribunal session",
      adjournedSessionMessage: "Record the time the session ended. It remains in Current view until midnight Los Angeles time.",
      adjournEndTime: "Session end time",
      assignedCases: "Cases assigned",
      caseHearings: "Case hearings",
      casesPresented: "Cases presented",
      archivedSessionDetails: "Archived session details",
      adjournSessionAction: "Adjourn session",
      addAssignmentCase: "Case to be Assigned",
      addHearingCase: "Case to Hearings",
      attendance: "Attendance",
      scheduledCasesForHearing: "Hearings",
      collapse: "Collapse {title}",
      expand: "Expand {title}",
      respondent: "Respondent",
      yearsMarried: "Years married",
      reason: "Reason",
      married: "Married",
      submitted: "Submitted",
      assignedTo: "Assigned to",
      previousRecommendation: "Previous recommendation",
      actions: "Actions",
      years: "{n} years",
      createSession: "Create session",
      dateRequired: "Enter a valid session date.",
      timeRequired: "Enter the session start time.",
      presidingRequired: "Select the presiding member.",
      locationRequired: "Enter the session location.",
      dateTaken: "A council session already exists on that date.",
      sessionCreated: "The council session was created.",
      sessionUpdated: "The council session was updated.",
      editSession: "Edit council session",
      saveSession: "Save changes",
      planned: "Planned",
      closed: "Closed",
      reference: "Reference",
      statusLabel: "Status",
      backSessions: "Back to sessions",
      sessionHeaderDescription: "Manage attendance, case assignments, and hearings for this session.",
      sessionSummary: "Session summary",
      casesToAssign: "To assign",
      scheduledHearings: "Scheduled hearings",
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
      toBeAssigned: "To be assigned",
      inProgress: "In Progress",
      heard: "Heard",
      presented: "Presented",
      presenter_absent: "Presenter absent — awaiting manual placement",
      unpresented: "Not presented",
      time_exhausted: "Time exhausted",
      deferred: "Deferred — awaiting manual placement",
      assigned: "Assigned case manager",
      unassigned: "Not yet assigned",
      notRecorded: "Not Recorded",
      readRecommendation: "Read Recommendation",
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
      deleteSession: "Delete",
      deleteSessionTitle: "Delete this draft session?",
      deleteSessionMessage: "This removes the unassigned draft session. Sessions with agenda items or retained history cannot be deleted.",
      deleteCase: "Delete",
      deleteCaseTitle: "Delete this case?",
      deleteCaseMessage: "This permanently removes the case and all of its related records. This cannot be undone.",
      sessionDeleted: "The draft session was deleted.",
      closeTitle: "Close this council session?",
      closeMessage:
        "Unpresented cases carry over to the next already scheduled session, or await manual placement if none exists. Deferred and presenter-absent cases always await manual placement. Messages set to “Send after council session” are released.",
      sessionClosed: "The council session was closed.",
      closedReadOnly: "This session is closed and read-only.",
      unknownParty: "Unknown spouse",
      pageFailed: "This page could not be shown. Your saved work is unchanged.",
      emailDelivery: "Email delivery of this update",
      sendImmediately: "Send Immediately",
      sendAfterSession: "Send after council session",
      chooseSessionForUpdate: "Select the council session",
      hearingAttendance: "Attendance at this hearing",
      hearingAttendanceHelp: "Taken from the session attendance when the case was presented. Correct an individual member's presence here.",
      presentLabel: "Present",
      absentLabel: "Absent",
      noHearingAttendance: "No attendance is recorded for this hearing.",
      upcomingSessions: "Upcoming sessions",
      pastSessions: "Past sessions",
      awaitingClose: "Planned date has passed — not yet closed",
      rescheduleAction: "Reschedule session",
      rescheduleTitle: "Reschedule this council session",
      rescheduleHelp: "Moves this planned session and its agenda to a new date. Each testimony invitation needs a new time; applicants receive a new invitation version to confirm or reject. The original session is removed from the list; its history is kept with each case.",
      newSessionDate: "New session date",
      sameDate: "Choose a different date.",
      rescheduleReason: "Reason for rescheduling",
      reasonRequired: "Record the reason for rescheduling.",
      replacementTimesLegend: "New testimony times (Pacific time)",
      replacementTimesHelp: "Enter a new time on the new date for every active invitation.",
      replacementTimes: "Enter new start and end times for every invitation.",
      replacementOverlap: "Two testimony times overlap. Applicants testify separately.",
      cancelInvitation: "Cancel invitation",
      cancelInvitationTitle: "Cancel this testimony invitation?",
      cancelInvitationMessage: "The applicant is notified privately. The case stays on the agenda.",
      keepInvitation: "Keep invitation",
      invitationCancelled: "The testimony invitation was cancelled.",
      statsTitle: "Statistics and Reports",
      statsPartial: "Counts cover the most recent 100 cases or sessions returned to this view. Complete figures need a server summary.",
      statsCases: "Cases",
      statsOpen: "Open cases",
      statsUnassigned: "Open cases awaiting a case manager",
      statsClosed: "Closed cases",
      statsByManager: "Open cases by case manager",
      statsSessions: "Council sessions",
      statsNoAssigned: "No open case has a case manager yet.",
      casesTitle: "Cases",
      newApplications: "New Applications",
      applicationSubmitted: "Submitted",
      archivedTitle: "Archived",
      searchCases: "Find a case by number or case manager",
      caseNumber: "Case number",
      noOpenCases: "No open cases.",
      noArchived: "No closed cases.",
      showClosedCases: "Show closed cases",
      caseApplicant: "Applicant",
      caseRespondent: "Respondent",
      caseReason: "Reason for divorce",
      ground_infidelity: "Infidelity",
      ground_abandonment: "Abandonment",
      ground_abuse: "Abuse",
      ground_faith: "Leaving or changing the faith",
      ground_addiction: "Addiction",
      ground_concealment: "Misrepresentation or concealment before marriage",
      groundsSeparator: "; ",
      caseAssignee: "Assigned council member",
      caseClosedDate: "Closed date",
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
      considerationCount: "{n} appeals or later petitions await council consideration (place them on a session agenda from the case).",
      upcomingSession: "Upcoming council session",
      openSession: "Open session",
      sessionWhen: "Date and time",
      agendaItems: "Agenda items",
      scheduleSession: "Schedule session",
      tileUnread: "Unread",
      tileNewApplications: "New applications",
      tileForCouncil: "For council",
      spouses: "Spouses",
      homeNextStep: "Next step",
      allCases: "All cases",
      noUpcoming: "No council session is scheduled.",
      needsAttention: "Needs attention",
      unreadNotifications: "{n} unread notifications",
      openNotifications: "Open notifications",
      nothingNeedsAttention: "You’re all caught up for now.",
      myCases: "My cases",
      myCasesCount: "{n} open cases assigned to you",
      noMyCases: "No open cases are assigned to you.",
      myCasesUnavailable: "The assigned-case list is unavailable. Open Cases to browse the cases returned by the server.",
      open: "Open",
      searchTitle: "Search",
      searchLabel: "Search documents",
      searchLength: "Use a search phrase of 2 to 200 characters.",
      searchAction: "Search",
      searchHistory: "Include earlier file versions",
      searchResults: "Results",
      searchCount: "{n} results",
      searchNone: "No permitted documents match this search.",
      // CDN page templates (#97 slice 2): dashboard metrics, listings, search and read-only notes.
      unreadTitle: "Unread notifications",
      considerationTitle: "Awaiting council consideration",
      considerationHelp: "Appeals and later petitions. Place them on a session agenda from the case.",
      metricMore: "More for {title}",
      archivedReadOnly: "Closed cases are read-only.",
      archivedSessionsReadOnly: "Archived sessions are read-only.",
      sessionNotSaved: "The council session was not saved.",
      searchStart: "Enter a search phrase, then choose Search.",
      searchNoun: "document",
      searchNouns: "documents",
      searchField: "Search {nouns}",
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
      councilMember: "عضو المجلس",
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
      sessions: "جلسات المجلس - الحالية",
      sessionsUpcoming: "جلسات المجلس - القادمة",
      sessionsArchived: "جلسات المجلس - المؤرشفة",
      tribunalSession: "جلسة المجلس",
      noSessions: "لا توجد جلسات مجلس حالية.",
      noUpcomingSessions: "لا توجد جلسات مجلس قادمة مجدولة.",
      noArchivedSessions: "لا توجد جلسات مجلس مؤرشفة.",
      newSession: "جلسة مجلس جديدة",
      sessionDate: "تاريخ الجلسة",
      sessionTime: "وقت الجلسة",
      presiding: "برئاسة",
      location: "الموقع",
      timeNotRecorded: "لم يُسجّل الوقت",
      presidingNotRecorded: "لم يُسجّل العضو المترئس",
      locationNotRecorded: "لم يُسجّل الموقع",
      hearingAdjourned: "تأجيل الجلسة",
      resumeHearing: "استئناف الجلسة",
      hearingAdjournedNotice: "تم تأجيل الجلسة.",
      hearingResumedNotice: "تم استئناف الجلسة.",
      sessionStatusPlanned: "مسودة",
      sessionStatusInProgress: "قيد التنفيذ",
      sessionAnswers: "تأكيدات الحضور",
      sessionAnswersHelp: "من أكّد أنه سيحضر. الحضور المسجَّل يوم الجلسة منفصل.",
      yourAnswer: "إجابتك",
      willAttend: "سأحضر",
      willNotAttend: "لن أحضر",
      answerAttending: "سيحضر",
      answerNotAttending: "لن يحضر",
      answerNone: "لا توجد إجابة",
      answerColumn: "الإجابة",
      answeredAt: "وقت الإجابة",
      answeredOn: "أُجيب في {when}",
      answerSaved: "تم حفظ إجابتك.",
      answerChoose: "اختر سأحضر أو لن أحضر.",
      answersClosed: "تُغلق الإجابات عند بدء الجلسة.",
      answersNotOpen: "يمكن للأعضاء الإجابة عندما تصبح الجلسة قيد التنفيذ.",
      confirmedColumn: "التأكيدات",
      confirmedOf: "أكّد {n} من {m}",
      confirmedCount: "{n} من {m}",
      sendReminderNow: "أرسل تذكيرًا الآن",
      reminderHelp: "يُرسل إلى الأعضاء الذين لم يجيبوا، مرة واحدة في الساعة على الأكثر.",
      reminderQueued: "التذكير في قائمة الإرسال إلى {n} من الأعضاء الذين لم يجيبوا.",
      reminderHourLimit: "أُرسل تذكير خلال الساعة الماضية.",
      remindersClosed: "لا يمكن إرسال التذكيرات إلا قبل بدء جلسة قيد التنفيذ.",
      emailNotSetUp: "البريد الإلكتروني غير مُعدّ، لذلك لا يمكن إرسال التذكيرات.",
      noMembers: "لا يوجد أعضاء نشطون في المجلس.",
      sessionStatusAdjourned: "مؤجلة",
      sessionActivated: "جلسة المجلس الآن قيد الانعقاد.",
      sessionReturnedToPlanned: "جلسة المجلس مخططة.",
      moveCase: "نقل",
      transferCaseTitle: "نقل القضية إلى جلسة أخرى",
      transferCaseHelp: "يحفظ هذا التجاوز المصرح به بند جدول الأعمال الأصلي ويسجل سبب نقله.",
      moveToSession: "نقل إلى جلسة",
      chooseSession: "اختر جلسة",
      transferReason: "سبب النقل",
      transferReasonRequired: "أدخل سببًا لهذا النقل.",
      transferRecorded: "تم نقل القضية وتسجيل التجاوز.",
      noTransferSessions: "لا تتوفر جلسات مسودة أو قيد الانعقاد أخرى.",
      adjournSessionTitle: "تأجيل جلسة المجلس",
      adjournedSessionMessage: "سجّل وقت انتهاء الجلسة. ستظل في العرض «الحالي» حتى منتصف الليل في لوس أنجلوس.",
      adjournEndTime: "وقت انتهاء الجلسة",
      assignedCases: "القضايا المُعيَّنة",
      caseHearings: "جلسات القضايا",
      casesPresented: "القضايا المعروضة",
      archivedSessionDetails: "تفاصيل الجلسة المؤرشفة",
      adjournSessionAction: "تأجيل الجلسة",
      addAssignmentCase: "قضية للتعيين",
      addHearingCase: "قضية لجلسات النظر",
      attendance: "الحضور",
      scheduledCasesForHearing: "مناقشات القضية",
      collapse: "طي {title}",
      expand: "توسيع {title}",
      respondent: "الطرف الآخر",
      yearsMarried: "سنوات الزواج",
      reason: "السبب",
      married: "مدة الزواج",
      submitted: "تاريخ التقديم",
      assignedTo: "مُعيَّنة إلى",
      previousRecommendation: "التوصية السابقة",
      actions: "إجراءات",
      years: "{n} سنة",
      createSession: "إنشاء الجلسة",
      dateRequired: "أدخل تاريخًا صحيحًا للجلسة.",
      timeRequired: "أدخل وقت بدء الجلسة.",
      presidingRequired: "اختر العضو المترئس.",
      locationRequired: "أدخل موقع الجلسة.",
      dateTaken: "توجد جلسة مجلس بالفعل في هذا التاريخ.",
      sessionCreated: "تم إنشاء جلسة المجلس.",
      sessionUpdated: "تم تحديث جلسة المجلس.",
      editSession: "تحرير جلسة المجلس",
      saveSession: "حفظ التغييرات",
      planned: "مجدولة",
      closed: "مغلقة",
      reference: "المرجع",
      statusLabel: "الحالة",
      backSessions: "العودة إلى الجلسات",
      sessionHeaderDescription: "إدارة الحضور وتعيين القضايا وجلسات النظر لهذه الجلسة.",
      sessionSummary: "ملخص الجلسة",
      casesToAssign: "قضايا للتعيين",
      scheduledHearings: "جلسات النظر المجدولة",
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
      toBeAssigned: "بانتظار التعيين",
      inProgress: "قيد الإجراء",
      heard: "تم نظرها",
      presented: "عُرضت",
      presenter_absent: "المقدِّم غائب — في انتظار الجدولة اليدوية",
      unpresented: "لم تُعرض",
      time_exhausted: "انتهى الوقت",
      deferred: "مؤجلة — في انتظار الجدولة اليدوية",
      assigned: "مسؤول القضية",
      unassigned: "لم يُعيَّن بعد",
      notRecorded: "غير مسجل",
      readRecommendation: "قراءة التوصية",
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
      deleteSession: "حذف",
      deleteSessionTitle: "حذف جلسة المسودة؟",
      deleteSessionMessage: "يُحذف فقط مشروع الجلسة غير المعيّن. لا يمكن حذف الجلسات التي تحتوي على بنود جدول أعمال أو سجل محفوظ.",
      deleteCase: "حذف",
      deleteCaseTitle: "حذف هذه القضية؟",
      deleteCaseMessage: "يؤدي هذا إلى حذف القضية وجميع سجلاتها المرتبطة نهائياً. لا يمكن التراجع عن ذلك.",
      sessionDeleted: "تم حذف مشروع الجلسة.",
      closeTitle: "هل تريد إغلاق جلسة المجلس هذه؟",
      closeMessage:
        "تنتقل القضايا التي لم تُعرض إلى الجلسة المجدولة التالية، أو تنتظر الجدولة اليدوية إن لم توجد جلسة. أما القضايا المؤجلة أو التي غاب مقدِّمها فتنتظر دائمًا الجدولة اليدوية. ويتم إرسال الرسائل المحددة بخيار «الإرسال بعد جلسة المجلس».",
      sessionClosed: "تم إغلاق جلسة المجلس.",
      closedReadOnly: "هذه الجلسة مغلقة ومتاحة للقراءة فقط.",
      unknownParty: "زوج غير معروف",
      pageFailed: "تعذر عرض هذه الصفحة. لم يتغير عملك المحفوظ.",
      emailDelivery: "إرسال هذا التحديث بالبريد الإلكتروني",
      sendImmediately: "إرسال فوري",
      sendAfterSession: "الإرسال بعد جلسة المجلس",
      chooseSessionForUpdate: "اختر جلسة المجلس",
      hearingAttendance: "الحضور في هذه الجلسة",
      hearingAttendanceHelp: "مأخوذ من حضور جلسة المجلس عند عرض القضية. صحّح حضور أي عضو هنا.",
      presentLabel: "حاضر",
      absentLabel: "غائب",
      noHearingAttendance: "لا يوجد حضور مسجَّل لهذه الجلسة.",
      upcomingSessions: "الجلسات القادمة",
      pastSessions: "الجلسات السابقة",
      awaitingClose: "انقضى الموعد المحدد — لم تُغلق بعد",
      rescheduleAction: "إعادة جدولة الجلسة",
      rescheduleTitle: "إعادة جدولة جلسة المجلس هذه",
      rescheduleHelp: "تنقل هذه الجلسة المجدولة وجدول أعمالها إلى تاريخ جديد. وتحتاج كل دعوة للإدلاء بالشهادة إلى موعد جديد؛ ويتلقى مقدمو الطلبات إصدارًا جديدًا من الدعوة لتأكيده أو رفضه. وتُحذف الجلسة الأصلية من القائمة مع الاحتفاظ بسجلها في كل قضية.",
      newSessionDate: "تاريخ الجلسة الجديد",
      sameDate: "اختر تاريخًا مختلفًا.",
      rescheduleReason: "سبب إعادة الجدولة",
      reasonRequired: "سجّل سبب إعادة الجدولة.",
      replacementTimesLegend: "المواعيد الجديدة للشهادة (توقيت المحيط الهادئ)",
      replacementTimesHelp: "أدخل موعدًا جديدًا في التاريخ الجديد لكل دعوة سارية.",
      replacementTimes: "أدخل وقتَي البدء والانتهاء الجديدين لكل دعوة.",
      replacementOverlap: "يتداخل موعدان للشهادة. يدلي مقدمو الطلبات بشهاداتهم بشكل منفصل.",
      cancelInvitation: "إلغاء الدعوة",
      cancelInvitationTitle: "هل تريد إلغاء دعوة الإدلاء بالشهادة هذه؟",
      cancelInvitationMessage: "يُخطَر مقدم الطلب بشكل خاص. وتبقى القضية في جدول الأعمال.",
      keepInvitation: "الإبقاء على الدعوة",
      invitationCancelled: "تم إلغاء دعوة الإدلاء بالشهادة.",
      statsTitle: "الإحصاءات والتقارير",
      statsPartial: "تشمل الأعداد أحدث ١٠٠ قضية أو جلسة معروضة في هذه الصفحة. وتحتاج الأرقام الكاملة إلى ملخص من الخادم.",
      statsCases: "القضايا",
      statsOpen: "القضايا المفتوحة",
      statsUnassigned: "قضايا مفتوحة في انتظار تعيين مسؤول",
      statsClosed: "القضايا المغلقة",
      statsByManager: "القضايا المفتوحة حسب مسؤول القضية",
      statsSessions: "جلسات المجلس",
      statsNoAssigned: "لا توجد قضية مفتوحة معيَّن لها مسؤول بعد.",
      casesTitle: "القضايا",
      newApplications: "الطلبات الجديدة",
      applicationSubmitted: "مُقدَّم",
      archivedTitle: "الأرشيف",
      searchCases: "ابحث عن قضية برقمها أو بمسؤولها",
      caseNumber: "رقم القضية",
      noOpenCases: "لا توجد قضايا مفتوحة.",
      noArchived: "لا توجد قضايا مغلقة.",
      showClosedCases: "إظهار القضايا المغلقة",
      caseApplicant: "الطالب",
      caseRespondent: "المدعى عليه",
      caseReason: "سبب الطلاق",
      ground_infidelity: "الخيانة الزوجية",
      ground_abandonment: "الهجر",
      ground_abuse: "الإساءة",
      ground_faith: "ترك الإيمان أو تغييره",
      ground_addiction: "الإدمان",
      ground_concealment: "التحريف أو الإخفاء قبل الزواج",
      groundsSeparator: "؛ ",
      caseAssignee: "عضو المجلس المعيَّن",
      caseClosedDate: "تاريخ الإغلاق",
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
      considerationCount: "{n} من الاستئنافات أو الطلبات اللاحقة في انتظار نظر المجلس (أدرجها في جدول أعمال جلسة من القضية).",
      upcomingSession: "جلسة المجلس القادمة",
      openSession: "فتح الجلسة",
      sessionWhen: "التاريخ والوقت",
      agendaItems: "بنود جدول الأعمال",
      scheduleSession: "جدولة جلسة",
      tileUnread: "غير مقروءة",
      tileNewApplications: "طلبات جديدة",
      tileForCouncil: "أمام المجلس",
      spouses: "الزوجان",
      homeNextStep: "الخطوة التالية",
      allCases: "كل القضايا",
      noUpcoming: "لا توجد جلسة مجلس مجدولة.",
      needsAttention: "يحتاج إلى متابعة",
      unreadNotifications: "{n} إشعارات غير مقروءة",
      openNotifications: "فتح الإشعارات",
      nothingNeedsAttention: "لا يوجد ما يحتاج إلى متابعتك الآن.",
      myCases: "قضاياي",
      myCasesCount: "{n} قضايا مفتوحة معيَّنة لك",
      noMyCases: "لا توجد قضايا مفتوحة معيَّنة لك.",
      myCasesUnavailable: "قائمة القضايا المعيّنة غير متاحة. افتح القضايا لاستعراض السجلات التي أعادها الخادم.",
      open: "مفتوحة",
      searchTitle: "البحث",
      searchLabel: "البحث في المستندات",
      searchLength: "استخدم عبارة بحث من حرفين إلى ٢٠٠ حرف.",
      searchAction: "بحث",
      searchHistory: "تضمين الإصدارات السابقة من الملفات",
      searchResults: "النتائج",
      searchCount: "{n} نتيجة",
      searchNone: "لا توجد مستندات مسموح بها تطابق هذا البحث.",
      // CDN page templates (#97 slice 2): dashboard metrics, listings, search and read-only notes.
      unreadTitle: "إشعارات غير مقروءة",
      considerationTitle: "في انتظار نظر المجلس",
      considerationHelp: "الاستئنافات والطلبات اللاحقة. أدرجها في جدول أعمال جلسة من القضية.",
      metricMore: "المزيد عن {title}",
      archivedReadOnly: "القضايا المغلقة للاطلاع فقط.",
      archivedSessionsReadOnly: "الجلسات المؤرشفة للاطلاع فقط.",
      sessionNotSaved: "لم تُحفظ جلسة المجلس.",
      searchStart: "أدخل عبارة البحث، ثم اختر «بحث».",
      searchNoun: "مستند",
      searchNouns: "مستندات",
      searchField: "البحث في {nouns}",
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

  // Plural messages for the DataGrid card counts (strings.cardCount): English one/other, the six Arabic forms.
  const counts = {
    en: {
      casesCount: { one: "{n} case", other: "{n} cases" },
      sessionsCount: { one: "{n} session", other: "{n} sessions" },
      applicationsCount: { one: "{n} application", other: "{n} applications" },
      resultsCount: { one: "{n} document", other: "{n} documents" },
    },
    ar: {
      casesCount: { zero: "لا توجد قضايا", one: "قضية واحدة", two: "قضيتان", few: "{n} قضايا", many: "{n} قضية", other: "{n} قضية" },
      sessionsCount: { zero: "لا توجد جلسات", one: "جلسة واحدة", two: "جلستان", few: "{n} جلسات", many: "{n} جلسة", other: "{n} جلسة" },
      applicationsCount: { zero: "لا توجد طلبات", one: "طلب واحد", two: "طلبان", few: "{n} طلبات", many: "{n} طلبًا", other: "{n} طلب" },
      resultsCount: { zero: "لا توجد مستندات", one: "مستند واحد", two: "مستندان", few: "{n} مستندات", many: "{n} مستندًا", other: "{n} مستند" },
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

  // The plural message a DataGrid card count takes ({ one, other } in English; the six Arabic forms).
  function plural(lang, key) {
    return counts[lang === "ar" ? "ar" : "en"][key] || counts.en[key];
  }

  // Loading: Skeleton rows hold the page's place (skeleton.md, DESIGN.md §3), announced as busy.
  function loadingView(P, h, t) {
    return h(P.Stack, { gap: "sm", role: "status", "aria-busy": "true", "aria-label": t("loading") },
      h(P.Skeleton, { width: "240px", height: "24px" }),
      ...[0, 1, 2, 3].map((key) => h(P.Skeleton, { key, height: "36px" })));
  }

  // Error boundary: a failure inside one council page shows a recoverable message
  // instead of blanking the whole application.
  let BoundaryClass = null;
  function boundaryClass() {
    if (BoundaryClass) return BoundaryClass;
    const R = window.React;
    BoundaryClass = class CouncilBoundary extends R.Component {
      constructor(props) {
        super(props);
        this.state = { error: null };
      }
      static getDerivedStateFromError(error) {
        return { error };
      }
      render() {
        if (!this.state.error) return this.props.children;
        const P = window.Plenix,
          h = R.createElement,
          t = translator(this.props.lang);
        return h(P.EmptyState, {
          tone: "error",
          title: t("pageFailed"),
          action: h(P.Button, { onClick: () => this.setState({ error: null }) }, t("retry")),
        });
      }
    };
    return BoundaryClass;
  }

  function guarded(Component) {
    const Guarded = (props) => window.React.createElement(boundaryClass(), { lang: props.lang }, window.React.createElement(Component, props));
    Guarded.displayName = `Guarded(${Component.name})`;
    return Guarded;
  }

  function loadFailure(P, h, t, retry, error) {
    return h(P.EmptyState, {
      tone: "error",
      title: error && error.status === 401 ? t("expired") : t("loadFailed"),
      action: h(P.Button, { onClick: retry }, t("retry")),
    });
  }

  function PreviousRecommendationCell({ value, lang }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [open, setOpen] = R.useState(false);
    const recommendation = String(value || "").trim();
    if (!recommendation) return t("notRecorded");
    return h(
      R.Fragment,
      null,
      h(P.Button, { size: "xs", icon: "document", onClick: () => setOpen(true) }, t("readRecommendation")),
      h(
        P.Dialog,
        { open: open, size: "lg", title: t("previousRecommendation"), closeLabel: t("cancel"), onClose: () => setOpen(false) },
        h(P.Text, { as: "p" }, recommendation),
      ),
    );
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
    [isolate(row.applicant_name), row.submitted_at ? formatWhen(row.submitted_at, lang) : null, `${t("fee")}: ${feeLabel(row, t)}`]
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
      { icon: "doc-text",
        title: t("reviewQueue"),
        actions: rows.length
          ? h(P.Button, { size: "sm", onClick: onOpen }, t("reviewOpen"))
          : null,
      },
      state.pending
        ? loadingView(P, h, t)
        : state.error
          ? loadFailure(P, h, t, retry, state.error)
          : rows.length
            ? h(
                P.Stack,
                { gap: "sm" },
                h(P.Badge, { tone: "action-required" }, t("reviewCount", { n: rows.length })),
                ...rows.slice(0, 5).map((row) =>
                  h(P.Card, { icon: "doc-text",
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
        row.case_number ? h(P.PropertyList.Item, { label: t("reference"), data: true }, h("bdi", { dir: "ltr" }, row.case_number)) : h(P.PropertyList.Item, { label: t("reference") }, t("unnumbered")),
        row.applicant_name ? h(P.PropertyList.Item, { label: t("applicant") }, row.applicant_name) : null,
        row.submitted_at ? h(P.PropertyList.Item, { label: t("submittedAt"), data: true }, formatWhen(row.submitted_at, lang)) : null,
        h(P.PropertyList.Item, { label: t("version"), data: true }, String(row.submitted_version ?? row.version)),
        h(P.PropertyList.Item, { label: t("fee") }, feeLabel(row, t)),
      ),
      returns.length
        ? h(
            P.Panel,
            { icon: "progress", title: t("previousReturns") },
            h(P.List, {
              variant: "bullets",
              items: returns.map((r) => ({ children: `${formatWhen(r.timestamp, lang)} · ${r.actor}: ${r.instructions}` })),
            }),
          )
        : null,
      row.manifest
        ? h(
            P.Panel,
            { icon: "attachment", title: t("manifest") },
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
        { icon: "doc-text", title: t("answers") },
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
        onConfirm: () => !pending && submit("accept"),
        onCancel: () => !pending && setMode(null),
      },
        failure && mode === "accept" ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
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

  // Completeness review: the queue and the chosen application side by side (SplitWorkspace through
  // CTMShell.Workspace, master-detail-workspace.md); Back sits in the command bar.
  function ReviewWorkspace({ api, lang, user, onCase, onBack }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(() => api(REVIEW_URL), [user?.id]);
    const [done, setDone] = R.useState({});
    const [notice, setNotice] = R.useState(null);
    const [selected, select] = R.useState(null);
    const rows = awaitingReview(state.data?.items).filter((row) => !done[row.id]).map((row) => ({
      ...row,
      title: row.case_number || t("unnumbered"),
      submitted: row.submitted_at ? formatWhen(row.submitted_at, lang) : t("notRecorded"),
      fee_status: feeLabel(row, t),
    }));
    if (state.pending && !state.data) return loadingView(P, h, t);
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    return h(
      P.Stack,
      { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t("review")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      h(window.CTMShell.Workspace, {
        label: t("reviewQueue"), rows, selected, empty: t("reviewQueueEmpty"), selectionPrompt: t("chooseApplication"),
        onSelect: (id) => { setNotice(null); select(id); },
        commandBar: { actions: onBack ? [{ id: "back", label: t("back"), icon: "arrow-left", onSelect: onBack }] : [] },
        cardCount: plural(lang, "applicationsCount"),
        template: { title: "title", subtitle: "applicant_name", date: "submitted", primary: "fee_status" },
        columns: [
          { title: t("caseNumber"), field: "title", kind: "name", minWidth: "9rem" },
          { title: t("applicant"), field: "applicant_name", type: "person", minWidth: "11rem" },
          { title: t("submitted"), field: "submitted", minWidth: "11rem" },
          { title: t("fee"), field: "fee_status", minWidth: "7rem" },
        ],
      }, (chosen) => h(ReviewDetail, {
        key: chosen.id, row: chosen, api, lang, user, onCase,
        onDone: (id, outcome) => {
          setDone((old) => ({ ...old, [id]: outcome }));
          select(null);
          setNotice(outcome);
        },
      })),
    );
  }

  const SESSION_LOCATION = "St. George Coptic Orthodox Church, Bellflower, California";

  // Tribunal sessions. Current: the session record itself. Upcoming: a listing with its command bar
  // (listing-page.md, command-bar.md), Open, Edit and Delete in each row's menu, and the create/edit form as a
  // FormFlow dialog (form-flow.md). Archived: a SplitWorkspace whose reading pane holds the session's record,
  // read-only (read-only-state.md).
  function SessionList({ api, lang, user, mode = "current", onOpen, onCase, renderAttendance }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(
      () => Promise.all([api("/api/sessions/"), api("/api/council/members/")]).then(([sessions, members]) => ({ sessions, members })),
      [user?.id],
    );
    const [selected, select] = R.useState("");
    const [archiveAgendaState] = useLoad(
      () => selected && mode === "archived" ? api(`/api/sessions/${encodeURIComponent(selected)}/agenda/`) : Promise.resolve({ items: [] }),
      [selected, mode],
    );
    const [initial, setInitial] = R.useState({ date: "", time: "", presiding: "", location: SESSION_LOCATION });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [created, setCreated] = R.useState(false);
    const [formOpen, setFormOpen] = R.useState(false);
    const [deleteTarget, setDeleteTarget] = R.useState(null);
    const loaded = state.data?.sessions?.items || [];
    const presidingMembers = assignmentAuthorizers(state.data?.members?.items || []);
    const defaultPresiding = presidingMembers.find((row) => row.name === "H.E. Metropolitan Serapion")
      || presidingMembers.find((row) => row.name?.includes("Metropolitan Serapion"))
      || presidingMembers.find((row) => row.president)
      || presidingMembers[0];
    const presiding = initial.presiding || defaultPresiding?.id || "";
    const today = todayInLosAngeles();
    const buckets = sessionBuckets(loaded, today);
    const rows = buckets[mode] || [];
    // Issue 116: the answer counts come from each session's answers (secretary, president, admin only).
    const showConfirmed = mode === "upcoming" && canSendReminders(user);
    const [answerState] = useLoad(
      () => showConfirmed && rows.length
        ? Promise.all(rows.map((row) => api(`/api/sessions/${encodeURIComponent(row.id)}/answers/`).then((data) => [row.id, data], () => [row.id, null])))
            .then((pairs) => Object.fromEntries(pairs))
        : Promise.resolve({}),
      [showConfirmed, rows.map((row) => row.id).join(",")],
    );
    const tableRows = rows.map((row) => ({
      ...row,
      confirmed: confirmedText(answerState.data?.[row.id], t, "confirmedCount") || "—",
      title: sessionLabel(row.date, t),
      session_time: formatTime(row.starts_at, lang) || t("timeNotRecorded"),
      adjourned_time: formatTime(row.adjourned_at, lang) || t("timeNotRecorded"),
    }));
    const titleKey = mode === "upcoming" ? "sessionsUpcoming" : mode === "archived" ? "sessionsArchived" : "sessions";
    const emptyKey = mode === "upcoming" ? "noUpcomingSessions" : mode === "archived" ? "noArchivedSessions" : "noSessions";

    const selectedSession = loaded.find((row) => row.id === selected) || null;
    const archivedItems = archivedAgendaRows(archiveAgendaState.data?.items);
    const editing = Boolean(selectedSession) && mode === "upcoming";
    // Loads the chosen session (or a blank one with the default presiding member and location) into the form.
    function openForm(row) {
      select(row ? row.id : "");
      setInitial(row
        ? { date: row.date || "", time: row.starts_at ? row.starts_at.slice(11, 16) : "", presiding: row.presiding_member_id || defaultPresiding?.id || "", location: row.location || "" }
        : { date: "", time: "", presiding: defaultPresiding?.id || "", location: SESSION_LOCATION });
      setProblem(null);
      setFailure(null);
      setCreated(false);
      setFormOpen(true);
    }
    function editSession(row) {
      openForm(row);
    }
    function startCreate() {
      openForm(null);
    }
    function cancelSessionForm() {
      select("");
      setProblem(null);
      setFailure(null);
      setFormOpen(false);
    }

    async function deleteSession() {
      if (!deleteTarget) return;
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/sessions/${encodeURIComponent(deleteTarget.id)}/`, { method: "DELETE" });
        if (selected === deleteTarget.id) cancelSessionForm();
        setDeleteTarget(null);
        setCreated("sessionDeleted");
        retry();
      } catch (error) {
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    // FormFlow runs validate, then onSubmit; the field's own error shows beside it as well.
    function validateSession(value) {
      const issue = sessionDateProblem(value.date, loaded, selectedSession?.id);
      const validation = issue || (!value.time ? "timeRequired" : !presiding ? "presidingRequired" : !value.location.trim() ? "locationRequired" : null);
      setProblem(validation);
      return validation ? t(validation) : "";
    }
    // A server refusal keeps its reason under the fields; FormFlow adds "not saved" and keeps the input.
    async function create(value) {
      setPending(true);
      setFailure(null);
      try {
        return await api(editing ? `/api/sessions/${encodeURIComponent(selectedSession.id)}/` : "/api/sessions/", {
          method: editing ? "PATCH" : "POST",
          body: JSON.stringify({ date: value.date, starts_at: laIso(value.date, value.time), location: value.location.trim() }),
        });
      } catch (error) {
        setFailure(error && error.status === 409 ? t("dateTaken") : serverMessage(error, t));
        throw error;
      } finally {
        setPending(false);
      }
    }
    function saved() {
      setFormOpen(false);
      select("");
      setCreated(editing ? "sessionUpdated" : "sessionCreated");
      retry();
    }

    if (state.pending && !state.data) return loadingView(P, h, t);
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    if (mode === "current")
      return rows.length
        ? h(SessionWorkspace, { key: rows[0].id, api, lang, user, sessionId: rows[0].id, current: true,
            onCase, onSession: select, onChanged: retry, renderAttendance })
        : h(P.Stack, { gap: "lg" }, h(P.Text, { as: "h1", variant: "title" }, t(titleKey)), h(P.EmptyState, { title: t(emptyKey) }));

    const manage = mode === "upcoming" && canManage(user);
    const columns = [
      { title: t("sessionDate"), field: "date", kind: "name", width: "8rem" },
      { title: t("sessionTime"), field: "session_time", width: "8rem" },
      ...(mode === "archived" ? [
        { title: t("adjournEndTime"), field: "adjourned_time", width: "10rem" },
        { title: t("assignedCases"), field: "assigned_case_count", width: "9rem" },
        { title: t("caseHearings"), field: "hearing_case_count", width: "9rem" },
      ] : []),
      ...(showConfirmed ? [{ title: t("confirmedColumn"), field: "confirmed", width: "11rem" }] : []),
      { title: t("statusLabel"), field: "state", pill: false, render: (row) => h(P.Badge, { tone: sessionStatusTone(row.state) }, t(sessionStatusKey(row.state))) },
    ];
    const listProps = {
      label: t(titleKey), rows: tableRows, empty: t(emptyKey), columns,
      cardCount: plural(lang, "sessionsCount"),
      template: { title: "date", subtitle: "session_time", primary: "state" },
    };
    const open = (row) => onOpen && onOpen(row.id);
    const caseColumns = (extra) => [
      { title: t("caseNumber"), field: "case_number", kind: "name", minWidth: "8rem" },
      { title: t("applicant"), field: "applicant", type: "person", minWidth: "10rem" },
      { title: t("respondent"), field: "respondent", type: "person", minWidth: "10rem" },
      ...extra,
    ];
    // An archived agenda part: each row opens its case (row click or the row menu).
    const archiveTable = (label, items, empty, columns) => h(window.CTMShell.Table, {
      label, rows: items, empty, isStatic: true, columns,
      rowMenu: [{ label: t("open"), icon: "open", onSelect: (row) => onCase(row.case_id) }],
      onSelect: (id) => { const row = items.find((item) => item.id === id); if (row) onCase(row.case_id); },
      // In the reading pane the grid sizes to its rows (pages) instead of filling a room it does not have.
      grid: { mode: "pages", pageSize: 10, strings: { cardCount: plural(lang, "casesCount"), perPage: t("tablePerPage"),
        range: t("tableRange"), count: t("tableCount"), pages: t("tablePages") } },
    });
    const archivedDetail = () => h(P.ReadOnly, { reason: t("archivedSessionsReadOnly") },
      h(P.Stack, { gap: "md" },
        archiveAgendaState.pending ? loadingView(P, h, t) : null,
        archiveAgendaState.error ? h(P.Notice, { tone: "danger" }, serverMessage(archiveAgendaState.error, t)) : null,
        !archiveAgendaState.pending && !archiveAgendaState.error ? h(P.Panel, { title: t("assignedCases") },
          archiveTable(t("assignedCases"), archivedItems.assigned, t("part1Empty"), caseColumns([
            { title: t("reason"), field: "reason", minWidth: "9rem", pill: false, render: (row) => groundsText(row.grounds, row.reason, t) || t("notRecorded") },
            { title: t("assignedTo"), field: "assigned_member_name", minWidth: "12rem", pill: false, render: (row) => row.assigned_member_name || t("unassigned") },
            { title: t("statusLabel"), field: "status", minWidth: "9rem", pill: false, render: (row) => t(row.status) },
          ])),
        ) : null,
        !archiveAgendaState.pending && !archiveAgendaState.error ? h(P.Panel, { title: t("casesPresented") },
          archiveTable(t("casesPresented"), archivedItems.presented, t("part2Empty"), caseColumns([
            { title: t("assignedTo"), field: "assigned_member_name", minWidth: "12rem", pill: false, render: (row) => row.assigned_member_name || t("unassigned") },
            { title: t("statusLabel"), field: "status", minWidth: "9rem", pill: false, render: (row) => t(row.status) },
            { title: t("previousRecommendation"), field: "previous_recommendation", minWidth: "14rem", pill: false, render: (row) => h(PreviousRecommendationCell, { value: row.previous_recommendation, lang }) },
          ])),
        ) : null,
      ));

    return h(
      P.Stack,
      { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t(titleKey)),
      created && !formOpen ? h(P.Notice, { tone: "success", onDismiss: () => setCreated(false) }, t(created)) : null,
      mode === "archived"
        ? h(window.CTMShell.Workspace, { ...listProps, selected: selected || null, onSelect: select,
            selectionPrompt: t("archivedSessionDetails") }, archivedDetail)
        : h(window.CTMShell.Listing, {
            ...listProps, onOpen: open,
            commandBar: manage ? { actions: [{ id: "create", label: t("createSession"), icon: "add", primary: true, disabled: pending, onSelect: startCreate }] } : undefined,
            rowMenu: manage
              ? (row) => [
                  { label: t("open"), icon: "open", onSelect: () => open(row) },
                  { label: t("editSession"), icon: "pencil", disabled: pending, onSelect: () => editSession(row) },
                  { separator: true },
                  { label: t("deleteSession"), icon: "trash", danger: true, disabled: pending || row.state !== "draft", onSelect: () => setDeleteTarget(row) },
                ]
              : [{ label: t("open"), icon: "open", onSelect: open }],
          }),
      // FormFlow needs a ToastProvider that AppShell does not give through 0.88.0 (plenix-requests.md PLX-021).
      manage
        ? h(P.ToastProvider, null, h(P.FormFlow, {
            open: formOpen, surface: "dialog", mode: editing ? "edit" : "create",
            title: t(editing ? "editSession" : "newSession"), initialValue: initial, sessionKey: selected || "new",
            validate: validateSession, onSubmit: create, onSuccess: saved, onCancel: cancelSessionForm,
            strings: { create: t("createSession"), save: t("saveSession"), cancel: t("cancel"), close: t("cancel"),
              failed: t("sessionNotSaved"), saved: t(editing ? "sessionUpdated" : "sessionCreated") },
          // Issue 117: rows 24px apart (Stack gap xl), the Plenix form-section gap at compact density.
          }, ({ value, setValue, busy }) => h(R.Fragment, null, h(P.Stack, { gap: "xl" },
            h(P.Columns, { count: 2, collapseBelow: "wide" },
            h(P.Field, { label: t("sessionDate"), required: true, error: problem === "dateRequired" || problem === "dateTaken" ? t(problem) : undefined },
              h(P.Input, { type: "date", value: value.date, disabled: busy,
                onChange: (event) => { const date = event.target.value; setValue((old) => ({ ...old, date })); setProblem(null); } })),
            h(P.Field, { label: t("sessionTime"), required: true, error: problem === "timeRequired" ? t(problem) : undefined },
              h(P.Input, { type: "time", value: value.time, disabled: busy,
                onChange: (event) => { const time = event.target.value; setValue((old) => ({ ...old, time })); setProblem(null); } }))),
            h(P.Columns, { count: 2, collapseBelow: "wide" },
            h(P.Field, { label: t("presiding"), required: true, error: problem === "presidingRequired" ? t(problem) : undefined },
              h(P.Select, { value: presiding, disabled: true,
                options: [{ value: "", label: t("presidingRequired") }, ...presidingMembers.map((row) => ({ value: row.id, label: row.name || row.id }))] })),
            h(P.Field, { label: t("location"), required: true, error: problem === "locationRequired" ? t(problem) : undefined },
              h(P.Input, { value: value.location, maxLength: 300, disabled: busy,
                onChange: (event) => { const location = event.target.value; setValue((old) => ({ ...old, location })); setProblem(null); } })))),
            failure && !deleteTarget ? h(P.Notice, { tone: "danger" }, failure) : null,
          )))
        : null,
      h(P.ConfirmDialog, {
        open: Boolean(deleteTarget), title: t("deleteSessionTitle"), message: t("deleteSessionMessage"),
        confirmLabel: t("deleteSession"), cancelLabel: t("cancel"), onConfirm: deleteSession,
        onCancel: () => !pending && setDeleteTarget(null),
      }, failure && deleteTarget ? h(P.Notice, { tone: "danger" }, failure) : null),
    );
  }

  function AgendaItemCard({ row, session, caseRow, user, lang, onAssign, onPresent, onTransfer, onCase, onOutcome, onTestimony, onCancelTestimony, canAssign, compact = false }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const flags = agendaActions(row, session, user, caseRow, { canRecordAssignment: canAssign });
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
    if (row.can_transfer && onTransfer)
      actions.push(h(P.Button, { key: "transfer", size: "xs", onClick: () => onTransfer(row) }, t("moveCase")));
    actions.push(
      h(P.Button, { key: "case", size: "xs", variant: "ghost", onClick: () => onCase(row.case_id) }, t("openCase")),
    );
    const titled = row.part === 2 && Array.isArray(row.party_names) && row.party_names.length;
    return h(
      compact ? P.Stack : P.Card,
      compact ? { gap: "xs" } : {
        icon: "calendar",
        title: titled ? hearingTitle(row.party_names, session.date, t) : row.case_number,
        meta: [titled ? isolate(row.case_number) : null, `${t("assigned")}: ${assignedName ? isolate(assignedName) : t("unassigned")}`].filter(Boolean).join(" · "),
        actions: h(P.Inline, { gap: "xs", wrap: true }, ...actions),
      },
      compact ? h(P.Text, { variant: "secondary" }, [titled ? hearingTitle(row.party_names, session.date, t) : null, `${t("assigned")}: ${assignedName ? isolate(assignedName) : t("unassigned")}`].filter(Boolean).join(" · ")) : null,
      compact ? h(P.Inline, { gap: "xs", wrap: true }, ...actions) : null,
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
            P.Inline,
            { key: a.id, wrap: true, gap: "xs" },
            h(
              P.Text,
              { variant: "secondary" },
              `${t("testimony")}: ${a.party_name} · ${formatTime(a.starts_at, lang)}–${formatTime(a.ends_at, lang)} · ${t(a.state === "cancelled" ? "cancelled" : a.response ? "response_" + a.response : "awaitingResponse")}`,
            ),
            flags.cancelTestimony && a.state !== "cancelled" && onCancelTestimony
              ? h(P.Button, { size: "2xs", onClick: () => onCancelTestimony(a) }, t("cancelInvitation"))
              : null,
          ),
        ),
      ),
    );
  }

  // Hearing outcome: internal text and recommendations are revised silently; only the
  // first record sends the default pending update (plus any message) to applicants.
  function HearingOutcomeDialog({ api, lang, user, hearingId, sessionId, title, onClose, onSaved }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(
      () =>
        Promise.all([
          api(`/api/hearings/${encodeURIComponent(hearingId)}/`),
          api("/api/sessions/"),
          sessionId
            ? api(`/api/sessions/${encodeURIComponent(sessionId)}/attendance/?hearing_id=${encodeURIComponent(hearingId)}`).catch(() => ({ items: null }))
            : Promise.resolve({ items: null }),
        ]).then(([hearing, sessions, attendance]) => ({
          ...hearing,
          plannedSessions: (sessions.items || []).filter((s) => s.state === "planned"),
          hearingAttendance: attendance.items,
        })),
      [hearingId],
    );
    const [timing, setTiming] = R.useState("immediate");
    const [deferSession, setDeferSession] = R.useState(sessionId || "");
    const [attendanceFailure, setAttendanceFailure] = R.useState(null);
    const [attendanceSaving, setAttendanceSaving] = R.useState(false);
    const [attendanceOpen, setAttendanceOpen] = R.useState(false);
    async function recordPresence(memberId, present) {
      setAttendanceSaving(true);
      setAttendanceFailure(null);
      try {
        await api(`/api/sessions/${encodeURIComponent(sessionId)}/attendance/`, {
          method: "POST",
          body: JSON.stringify({ member_id: memberId, present, hearing_id: hearingId }),
        });
        retry();
      } catch (error) {
        setAttendanceFailure(serverMessage(error, t));
      } finally {
        setAttendanceSaving(false);
      }
    }
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
        if (first) {
          if (timing === "after_session" && !deferSession) throw { data: { detail: t("chooseSessionForUpdate") } };
          payload.email_timing = timing;
          if (timing === "after_session") payload.session_id = deferSession;
        }
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
        ? loadingView(P, h, t)
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
                first
                  ? h(P.RadioGroup, {
                      label: t("emailDelivery"),
                      value: timing,
                      onChange: setTiming,
                      options: [
                        { value: "immediate", label: t("sendImmediately"), disabled: pending },
                        { value: "after_session", label: t("sendAfterSession"), disabled: pending },
                      ],
                    })
                  : null,
                first && timing === "after_session"
                  ? h(
                      P.Field,
                      { label: t("chooseSessionForUpdate"), required: true },
                      h(P.Select, {
                        value: deferSession,
                        disabled: pending,
                        onChange: (e) => setDeferSession(e.target.value),
                        options: [
                          { value: "", label: t("chooseSessionForUpdate") },
                          ...(state.data.plannedSessions || []).map((s) => ({ value: s.id, label: sessionLabel(s.date, t) })),
                        ],
                      }),
                    )
                  : null,
                Array.isArray(state.data.hearingAttendance)
                  ? h(P.Button, { size: "sm", icon: "settings-users", onClick: () => setAttendanceOpen(true) }, t("hearingAttendance"))
                  : null,
                attendanceOpen
                  ? h(P.Dialog, { open: true, size: "lg", title: t("hearingAttendance"), description: t("hearingAttendanceHelp"), closeLabel: t("cancel"), onClose: () => !attendanceSaving && setAttendanceOpen(false) },
                      h(P.Stack, { gap: "md" },
                        h(P.Table, { label: t("hearingAttendance"), index: "member_id", data: state.data.hearingAttendance, columns: [
        { title: t("councilMember"), field: "member_name", rowLabel: true, kind: "wrap", render: (row) => h(P.Stack, { gap: "none" }, h(P.Text, { as: "div", variant: "strong" }, row.member_name), h(P.Text, { as: "div", variant: "secondary" }, row.member_role === "president" ? "Presiding" : row.member_role === "secretary" ? "Secretary" : "Member")) },
        { title: t("hearingAttendance"), field: "present", render: (row) => h(P.SegmentedControl, { size: "sm", label: `${t("hearingAttendance")}: ${row.member_name}`, value: row.present === true ? "present" : row.present === false ? "absent" : undefined, readOnly: attendanceSaving || !canManage(user) || !writable,
          options: [{ value: "present", label: t("presentLabel"), icon: "check" }, { value: "absent", label: t("absentLabel"), icon: "close" }],
          onChange: (choice) => recordPresence(row.member_id, choice === "present") }) },
      ] }),
                        !state.data.hearingAttendance.length ? h(P.EmptyState, { title: t("noHearingAttendance") }) : null,
                        attendanceFailure ? h(P.Notice, { tone: "danger" }, attendanceFailure) : null,
                      ),
                    )
                  : null,
                outcomes.length
                  ? h(
                      P.Panel,
                      { icon: "progress", title: t("outcomeHistory"), collapsible: true, defaultExpanded: false },
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
            starts_at: laIso(sessionDate, form.start),
            ends_at: laIso(sessionDate, form.end),
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
        ? loadingView(P, h, t)
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

  // The current Los Angeles wall-clock time as HH:MM (24-hour, a time input's value), for the Adjourn end time (issue 112).
  function laNowTime(now = new Date()) {
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", hourCycle: "h23", hour: "2-digit", minute: "2-digit" })
        .formatToParts(now).map((part) => [part.type, part.value]),
    );
    return `${parts.hour}:${parts.minute}`;
  }

  // Los Angeles wall-clock time on a date as an ISO timestamp with its UTC offset
  // (daylight saving aware), e.g. laIso("2026-11-05", "10:30") -> "2026-11-05T10:30:00-08:00".
  function laIso(date, time) {
    if (!DATE.test(date || "") || !/^\d{2}:\d{2}$/.test(time || "")) return null;
    const [y, mo, d] = date.split("-").map(Number);
    const [hh, mm] = time.split(":").map(Number);
    const wall = Date.UTC(y, mo - 1, d, hh, mm);
    const offsetAt = (instant) => {
      const parts = Object.fromEntries(
        new Intl.DateTimeFormat("en-US", {
          timeZone: "America/Los_Angeles",
          hourCycle: "h23",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })
          .formatToParts(new Date(instant))
          .map((p) => [p.type, p.value]),
      );
      const seen = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour % 24, +parts.minute);
      return (seen - instant) / 60000;
    };
    let offset = offsetAt(wall - offsetAt(wall) * 60000);
    const sign = offset <= 0 ? "-" : "+";
    const abs = Math.abs(offset);
    const pad = (n) => String(n).padStart(2, "0");
    return `${date}T${time}:00${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
  }

  function activeAppointments(items) {
    return (items || []).flatMap((item) => (item.testimony || []).filter((a) => a.state !== "cancelled").map((a) => ({ ...a, agenda_id: item.id })));
  }

  function rescheduleProblem(form, appointments, existing, currentDate) {
    const dateIssue = sessionDateProblem(form.date, (existing || []).filter((s) => s.date !== currentDate));
    if (dateIssue) return dateIssue;
    if (form.date === currentDate) return "sameDate";
    if (!String(form.reason || "").trim()) return "reasonRequired";
    for (const a of appointments || []) {
      const slot = form.times?.[a.id] || {};
      if (!/^\d{2}:\d{2}$/.test(slot.start || "") || !/^\d{2}:\d{2}$/.test(slot.end || "")) return "replacementTimes";
      if (slot.end <= slot.start) return "endAfterStart";
    }
    const slots = (appointments || []).map((a) => form.times[a.id]).sort((x, y) => x.start.localeCompare(y.start));
    for (let i = 1; i < slots.length; i++) if (slots[i].start < slots[i - 1].end) return "replacementOverlap";
    return null;
  }

  function reschedulePayload(form, appointments) {
    const out = {};
    for (const a of appointments || []) {
      const slot = form.times[a.id];
      out[a.id] = { starts_at: laIso(form.date, slot.start), ends_at: laIso(form.date, slot.end) };
    }
    return { date: form.date, reason: form.reason.trim(), appointments: out };
  }

  function RescheduleDialog({ api, lang, session, items, sessions, onClose, onDone }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const appointments = activeAppointments(items);
    const [form, setForm] = R.useState({ date: "", reason: "", times: {} });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const update = (patch) => {
      setForm((old) => ({ ...old, ...patch }));
      setProblem(null);
    };
    const setTime = (id, key, value) => update({ times: { ...form.times, [id]: { ...(form.times[id] || {}), [key]: value } } });
    async function save() {
      const issue = rescheduleProblem(form, appointments, sessions, session.date);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      try {
        const target = await api(`/api/sessions/${encodeURIComponent(session.id)}/reschedule/`, {
          method: "POST",
          body: JSON.stringify(reschedulePayload(form, appointments)),
        });
        onDone(target.id);
      } catch (error) {
        setFailure(serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    return h(
      P.Dialog,
      {
        open: true,
        size: "lg",
        title: t("rescheduleTitle"),
        description: t("rescheduleHelp"),
        closeLabel: t("cancel"),
        onClose: () => !pending && onClose(),
        footer: h(
          P.Inline,
          null,
          h(P.Button, { disabled: pending, onClick: onClose }, t("cancel")),
          h(P.Button, { variant: "primary", loading: pending, disabled: pending, onClick: save }, t("rescheduleAction")),
        ),
      },
      h(
        P.Stack,
        { gap: "md" },
        h(
          P.Field,
          {
            label: t("newSessionDate"),
            required: true,
            error: ["dateRequired", "dateTaken", "sameDate"].includes(problem) ? t(problem) : undefined,
          },
          h(P.Input, { type: "date", width: "sm", value: form.date, disabled: pending, onChange: (e) => update({ date: e.target.value }) }),
        ),
        h(
          P.Field,
          { label: t("rescheduleReason"), required: true, error: problem === "reasonRequired" ? t("reasonRequired") : undefined },
          h(P.Textarea, { rows: 3, value: form.reason, maxLength: 2000, disabled: pending, onChange: (e) => update({ reason: e.target.value }) }),
        ),
        appointments.length
          ? h(
              P.Fieldset,
              { legend: t("replacementTimesLegend") },
              h(P.Text, { variant: "secondary" }, t("replacementTimesHelp")),
              ...appointments.map((a) =>
                h(
                  P.Inline,
                  { key: a.id, wrap: true, align: "end" },
                  h(P.Text, { variant: "strong" }, `${a.party_name} · ${formatTime(a.starts_at, lang)}–${formatTime(a.ends_at, lang)}`),
                  h(P.Field, { label: `${t("startTime")} · ${a.party_name}` }, h(P.Input, { type: "time", width: "sm", value: form.times[a.id]?.start || "", disabled: pending, onChange: (e) => setTime(a.id, "start", e.target.value) })),
                  h(P.Field, { label: `${t("endTime")} · ${a.party_name}` }, h(P.Input, { type: "time", width: "sm", value: form.times[a.id]?.end || "", disabled: pending, onChange: (e) => setTime(a.id, "end", e.target.value) })),
                ),
              ),
              ["replacementTimes", "endAfterStart", "replacementOverlap"].includes(problem) ? h(P.Notice, { tone: "danger" }, t(problem)) : null,
            )
          : null,
        failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  // renderAttendance({ session, members, attendance, key }) lets the shell keep its
  // existing attendance component while this module supplies fresh data after each action.
  // Issue 116 AC-6: the member's own answer, and for the secretary, president and admin every
  // member's latest answer with its time, "Confirmed n of m" and Send reminder now (D-0039).
  function SessionAnswers({ api, lang, user, session }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const url = (part) => `/api/sessions/${encodeURIComponent(session.id)}/${part}/`;
    const [state, retry] = useLoad(() => api(url("answers")), [session.id]);
    const [saved, setSaved] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [problem, setProblem] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    const [reminded, setReminded] = R.useState(false);
    const data = saved || state.data;
    if (state.pending && !data) return loadingView(P, h, t);
    if (state.error && !data) return loadFailure(P, h, t, retry, state.error);
    const open = sessionAnswerable(session);
    const mine = ownAnswer(data, user);
    const sender = canSendReminders(user) && Array.isArray(data.members);
    async function act(work) {
      setPending(true);
      setProblem(null);
      setNotice(null);
      try {
        await work();
      } catch (error) {
        setProblem(reminderProblem(error, t));
      } finally {
        setPending(false);
      }
    }
    const answer = (value) => act(async () => {
      setSaved(await api(url("answer"), { method: "POST", body: JSON.stringify({ answer: value }) }));
      setNotice(t("answerSaved"));
    });
    const remind = () => act(async () => {
      const result = await api(url("reminders"), { method: "POST", body: "{}" });
      setReminded(true);
      setNotice(t("reminderQueued", { n: result?.queued ?? 0 }));
    });
    const byName = new Intl.Collator(lang === "ar" ? "ar" : "en");
    const rows = sender ? data.members.map((row) => ({ ...row, id: row.member_id,
      answered: row.answered_at ? formatWhen(row.answered_at, lang) : "—" })).sort((a, b) => byName.compare(a.name || "", b.name || "")) : [];
    return h(P.Panel, {
      title: t("sessionAnswers"), icon: "event_available", description: t("sessionAnswersHelp"),
      actions: sender ? h(P.Button, { icon: "notifications", disabled: pending || reminded || !data.email_ready || !open, onClick: remind }, t("sendReminderNow")) : undefined,
    },
      h(P.Stack, { gap: "md" },
        sender && !data.email_ready ? h(P.Notice, { tone: "warning" }, t("emailNotSetUp")) : null,
        notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, notice) : null,
        problem ? h(P.Notice, { tone: "danger", onDismiss: () => setProblem(null) }, problem) : null,
        h(P.Field, { label: t("yourAnswer"),
          description: !open ? t(session.state === "planned" ? "answersClosed" : "answersNotOpen")
            : mine ? t("answeredOn", { when: formatWhen(mine.answered_at, lang) }) : t("answerNone") },
          h(P.SegmentedControl, { label: t("yourAnswer"), value: mine?.answer, readOnly: pending || !open,
            onChange: (value) => value !== mine?.answer && answer(value),
            options: [{ value: "attend", label: t("willAttend"), icon: "check" }, { value: "not_attend", label: t("willNotAttend"), icon: "close" }] })),
        sender ? h(P.Stack, { gap: "sm" },
          h(P.Inline, { gap: "sm", align: "center" },
            h(P.Text, { as: "h3", variant: "heading" }, confirmedText(data, t)),
            h(P.Text, { variant: "secondary" }, t("reminderHelp"))),
          h(window.CTMShell.Table, { label: t("sessionAnswers"), rows, isStatic: true, empty: t("noMembers"),
            columns: [
              { title: t("councilMember"), field: "name", kind: "name", rowLabel: true },
              { title: t("answerColumn"), field: "answer", minWidth: "9rem", pill: false, render: (row) => h(P.Badge, { tone: answerTone(row.answer) }, t(answerKey(row.answer))) },
              { title: t("answeredAt"), field: "answered", minWidth: "12rem" },
            ] })) : null,
      ));
  }

  function SessionWorkspace({ api, lang, user, sessionId, renderAttendance, onCase, onBack, onSession, onChanged, compact = false, current = false }) {
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
          authorities: members.assignment_authorities,
          sessions: sessions.items,
        })),
      [sessionId],
    );
    const [dialog, setDialog] = R.useState(null); // {kind, row}
    const [choice, setChoice] = R.useState({ part1: "", part2: "", member: "", president: "", targetSession: "", transferReason: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    const [adjournEnd, setAdjournEnd] = R.useState("");

    if (state.pending && !state.data) return loadingView(P, h, t);
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    const data = state.data;
    const session = data.session;
    const planned = session.state === "planned";
    const editable = session.state === "draft" || planned;
    const manage = canManage(user);
    const caseById = Object.fromEntries((data.cases || []).map((row) => [row.id, row]));
    const groups = groupAgenda(data.items);
    const c1 = part1Candidates(data.cases, data.items);
    const c2 = part2Candidates(data.cases, data.items, user);
    const pendingAssignments = pendingAssignmentCount(data.items);
    const scheduledHearings = groups[2].filter((row) => row.state === "scheduled").length;
    const presidentRows = assignmentAuthorizers(data.members, data.authorities);
    const recorder = canRecordAssignment(user, data.members, data.authorities);
    const memberRows = assignableMembers(data.members);
    const transferSessions = data.sessions.filter((candidate) => candidate.id !== session.id && candidate.date > session.date && ["draft", "planned"].includes(candidate.state));
    // The session header is Plenix EntityHeader, header style 2 "facts with actions" (owner 2026-10-23;
    // CDN record-page docs): each count carries its own button, and the session's state is the status
    // box among the facts. Buttons appear only on the current session and only for those allowed.
    const presentCount = Array.isArray(data.attendance) ? data.attendance.filter((row) => row.present === true).length : null;
    const sessionFacts = [
      { icon: "person", label: t("presiding"), value: session.presiding_member_name || t("presidingNotRecorded") },
      {
        icon: "settings-users", label: t("attendance"), value: presentCount === null ? "—" : String(presentCount), data: true,
        action: current ? { label: t("attendance"), icon: "edit", name: t("attendance"), disabled: pending, onClick: () => setDialog({ kind: "attendance" }) } : undefined,
      },
      {
        icon: "folder", label: t("casesToAssign"), value: String(pendingAssignments), data: true,
        action: current && editable && manage ? { label: t("addAssignmentCase"), icon: "folder-add", name: t("addAssignmentCase"), disabled: pending, onClick: () => setDialog({ kind: "place", part: 1 }) } : undefined,
      },
      {
        icon: "event_available", label: t("scheduledCasesForHearing"), value: String(scheduledHearings), data: true,
        action: current && editable ? { label: t("addHearingCase"), icon: "event_available", name: t("addHearingCase"), disabled: pending, onClick: () => setDialog({ kind: "place", part: 2 }) } : undefined,
      },
    ];
    const sessionStatus = session.state === "closed" ? "adjourned" : session.state === "draft" ? "draft" : "in-session";
    // The status box: Draft (yellow), In progress (green), Adjourned (red), each with its icon (owner 2026-10-25).
    const sessionStates = {
      label: t("statusLabel"),
      value: sessionStatus,
      disabled: !current || pending,
      options: [
        { value: "draft", label: t("sessionStatusPlanned"), icon: "pencil", tone: "waiting" },
        { value: "in-session", label: t("sessionStatusInProgress"), icon: "clock", tone: "success" },
        { value: "adjourned", label: t("sessionStatusAdjourned"), icon: "do-not-disturb", tone: "negative" },
      ],
      onChange: (value) => {
        if (value === "draft" && session.state === "planned" && manage)
          run(() => api(`/api/sessions/${encodeURIComponent(sessionId)}/plan/`, { method: "POST", body: "{}" }), "sessionReturnedToPlanned", onChanged);
        if (value === "in-session" && session.state === "draft" && session.can_activate)
          run(() => api(`/api/sessions/${encodeURIComponent(sessionId)}/activate/`, { method: "POST", body: "{}" }), "sessionActivated", onChanged);
        if (value === "adjourned" && planned && manage) {
          setFailure(null);
          setAdjournEnd(laNowTime());
          setDialog({ kind: "adjourn" });
        }
      },
    };

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
      const issue = assignmentProblem(choice.member, choice.president, data.members, data.authorities);
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

    const addControl = (part, candidates) =>
      editable && (part === 1 ? manage : true)
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
                  ...candidates.map((row) => ({ value: row.id, label: casePlacementLabel(row) })),
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
        P.Stack,
        { key: n, gap: "sm" },
        h(P.Text, { as: "h2", variant: "heading" }, t(`part${n}`)),
        h(
          P.Stack,
          { gap: "sm" },
          h(P.DataGrid, {
            density: "compact", cells: "pill", typeIcons: false, wrapHeaders: false,
            label: t(`part${n}`), data: groups[n], index: "id", narrow: "table", mode: "fill", isStatic: true,
            empty: t(`part${n}Empty`),
            columns: [
              { title: t("caseNumber"), field: "case_number", kind: ["name", "data"] },
              { title: t("statusLabel"), field: "state", pill: false, render: (row) => t(row.state === "assigned" ? "assigned_state" : row.state) },
              { title: t("agenda"), field: "id", pill: false, render: (row) => h(AgendaItemCard, {
              compact: true,
              key: row.id,
              row,
              session,
              caseRow: caseById[row.case_id],
              user,
              lang,
              canAssign: recorder,
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
              onTransfer: (item) => {
                setFailure(null);
                setChoice((old) => ({ ...old, targetSession: "", transferReason: "" }));
                setDialog({ kind: "transfer", row: item });
              },
              onOutcome: (item) => {
                setFailure(null);
                setDialog({ kind: "outcome", row: item });
              },
              onTestimony: (item) => {
                setFailure(null);
                setDialog({ kind: "testimony", row: item });
              },
              onCancelTestimony: (appointment) => {
                setFailure(null);
                setDialog({ kind: "cancelTestimony", appointment });
              },
              }) },
            ],
          }),
          addControl(n, n === 1 ? c1 : c2),
        ),
      );

    const agendaCallbacks = {
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
      onTransfer: (item) => {
        setFailure(null);
        setChoice((old) => ({ ...old, targetSession: "", transferReason: "" }));
        setDialog({ kind: "transfer", row: item });
      },
      onOutcome: (item) => {
        setFailure(null);
        setDialog({ kind: "outcome", row: item });
      },
      onTestimony: (item) => {
        setFailure(null);
        setDialog({ kind: "testimony", row: item });
      },
      onCancelTestimony: (appointment) => {
        setFailure(null);
        setDialog({ kind: "cancelTestimony", appointment });
      },
    };

    const personPill = (value, kind, gender) => {
      if (!value) return t(kind === "clergy" ? "unassigned" : "notRecorded");
      const normalizedGender = gender === "M" || gender === "male" ? "male" : gender === "F" || gender === "female" ? "female" : undefined;
      return normalizedGender
        ? h(P.DataPill, { size: "md", gender: normalizedGender }, value)
        : h(P.DataPill, { size: "md", person: true }, value);
    };
    const agendaTable = (n) => {
      const first = n === 1;
      // DataTable supplies renderers with its declared row fields. Keep a person's
      // name and gender in the same declared value so the CDN DataPill receives both.
      const rows = groups[n].map((row, index) => ({
        ...row,
        // Hearing numbers are scoped to the cases presented in this session.
        hearing_number: first ? null : index + 1,
        reason: groundsText(row.grounds, row.reason, t),
        applicant: { name: row.applicant_name, gender: row.applicant_gender === "M" ? "male" : row.applicant_gender === "F" ? "female" : undefined },
        respondent: { name: row.respondent_name, gender: row.respondent_gender === "M" ? "male" : row.respondent_gender === "F" ? "female" : undefined },
      }));
      const title = first ? t("casesToAssign") : t("scheduledCasesForHearing");
      const columns = first
        ? [
            { title: t("applicant"), field: "applicant", kind: "name", width: "10.5rem", pill: false, render: (row) => personPill(row.applicant?.name, "applicant", row.applicant?.gender) },
            { title: t("respondent"), field: "respondent", width: "10.5rem", pill: false, render: (row) => personPill(row.respondent?.name, "respondent", row.respondent?.gender) },
            { title: t("reason"), field: "reason", minWidth: "6.5rem" },
            { title: t("yearsMarried"), field: "married_years", minWidth: "7.5rem", pill: false, render: (row) => row.married_years === null || row.married_years === undefined ? t("notRecorded") : t("years", { n: row.married_years }) },
            { title: t("assignedTo"), field: "assigned_member_name", width: "12rem", pill: false, render: (row) => personPill(row.assigned_member_name, "clergy") },
            { title: t("actions"), field: "open_action", minWidth: "9rem", pill: false, render: (row) => h(P.Inline, { gap: "xs" },
              h(P.Button, { size: "xs", icon: "open", onClick: () => onCase(row.case_id) }, t("open")),
              h(P.Button, { size: "xs", onClick: () => agendaCallbacks.onTransfer(row) }, t("moveCase"))) },
          ]
        : [
            { title: "#", field: "hearing_number", kind: "name", width: "5rem" },
            { title: t("applicant"), field: "applicant", width: "10.5rem", pill: false, render: (row) => personPill(row.applicant?.name, "applicant", row.applicant?.gender) },
            { title: t("respondent"), field: "respondent", width: "10.5rem", pill: false, render: (row) => personPill(row.respondent?.name, "respondent", row.respondent?.gender) },
            { title: t("assignedTo"), field: "assigned_member_name", width: "12rem", pill: false, render: (row) => personPill(row.assigned_member_name, "clergy") },
            { title: t("previousRecommendation"), field: "previous_recommendation", width: "12rem", pill: false, render: (row) => h(PreviousRecommendationCell, { value: row.previous_recommendation, lang }) },
            { title: t("actions"), field: "open_action", minWidth: "9rem", pill: false, render: (row) => h(P.Inline, { gap: "xs" },
              h(P.Button, { size: "xs", icon: "open", onClick: () => onCase(row.case_id) }, t("open")),
              h(P.Button, { size: "xs", onClick: () => agendaCallbacks.onTransfer(row) }, t("moveCase"))) },
          ];
      return h(window.CTMShell.Table, { className: "ctm-session-agenda-grid", label: title, rows, columns, empty: t(`part${n}Empty`), isStatic: true });
    };

    return h(
      P.Stack,
      { gap: "lg" },
      !current && onBack ? h(P.Inline, null, h(P.Button, { variant: "ghost", onClick: onBack }, t("backSessions"))) : null,
      h(P.EntityHeader, {
        media: { icon: "calendar", hue: "blue" },
        title: sessionLabel(session.date, t),
        subtitle: formatSessionStart(session.starts_at, lang) || t("timeNotRecorded"),
        facts: sessionFacts,
        states: sessionStates,
      }),
      !editable ? h(P.Notice, { tone: "info" }, t("closedReadOnly")) : null,
      notice ? h(P.Notice, { tone: notice === "absentNotice" ? "warning" : "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !dialog ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      editable && session.starts_at && new Date(session.starts_at).getTime() > Date.now()
        ? h(SessionAnswers, { key: session.id, api, lang, user, session }) : null,
      // D-0042 (owner, issue 171): no agenda tabs. Two full-width sections, one below the other, each with
      // its heading and its own table: Hearings, then To assign (peer sections, stack.md gap "section").
      current ? h(P.Stack, { gap: "section" },
        h(P.Stack, { gap: "sm" }, h(P.Text, { as: "h2", variant: "heading" }, t("scheduledCasesForHearing")), agendaTable(2)),
        h(P.Stack, { gap: "sm" }, h(P.Text, { as: "h2", variant: "heading" }, t("casesToAssign")), agendaTable(1)),
      ) : h(P.Text, { as: "h2", variant: "heading" }, t("agenda")),
      current ? null : part(1),
      current ? null : part(2),
      data.items.length && !data.items.some((row) => "hearing_id" in row) ? h(P.Notice, { tone: "info" }, t("outcomeDependency")) : null,
      dialog?.kind === "outcome"
        ? h(HearingOutcomeDialog, {
            api,
            lang,
            user,
            sessionId,
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
      dialog?.kind === "reschedule"
        ? h(RescheduleDialog, {
            api,
            lang,
            session,
            items: data.items,
            sessions: data.sessions,
            onClose: () => setDialog(null),
            onDone: (targetId) => {
              setDialog(null);
              if (onChanged) onChanged();
              if (onSession) onSession(targetId);
            },
          })
        : null,
      dialog?.kind === "transfer"
        ? h(P.Dialog, { open: true, size: "sm", title: t("transferCaseTitle"), onClose: () => !pending && setDialog(null) },
            h(P.Stack, { gap: "md" },
              h(P.Text, { variant: "secondary" }, t("transferCaseHelp")),
              h(P.Field, { label: t("moveToSession") }, h(P.Select, {
                value: choice.targetSession,
                onChange: (event) => setChoice((old) => ({ ...old, targetSession: event.target.value })),
                options: [{ value: "", label: transferSessions.length ? t("chooseSession") : t("noTransferSessions") }, ...transferSessions.map((candidate) => ({ value: candidate.id, label: sessionLabel(candidate.date, t) }))],
              })),
              h(P.Field, { label: t("transferReason") }, h(P.Textarea, { value: choice.transferReason, onChange: (event) => setChoice((old) => ({ ...old, transferReason: event.target.value })) })),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
              h(P.Inline, { justify: "end", gap: "sm" },
                h(P.Button, { variant: "secondary", disabled: pending, onClick: () => setDialog(null) }, t("cancel")),
                h(P.Button, { variant: "primary", disabled: pending || !choice.targetSession || !choice.transferReason.trim(), onClick: () => run(
                  () => api(`/api/agenda/${encodeURIComponent(dialog.row.id)}/transfer/`, { method: "POST", body: JSON.stringify({ target_session_id: choice.targetSession, reason: choice.transferReason }) }),
                  "transferRecorded", onChanged,
                ) }, t("moveCase")),
              ),
            ),
          )
        : null,
      dialog?.kind === "attendance" && renderAttendance
        ? h(
            P.Dialog,
            { open: true, size: "lg", title: t("attendance"), onClose: () => !pending && setDialog(null) },
            renderAttendance({
              session,
              members: data.members,
              attendance: data.attendance,
              key: `${sessionId}-${data.loadedAt}`,
              onSaved: retry,
            }),
          )
        : null,
      dialog?.kind === "adjourn"
        ? h(P.Dialog, { open: true, size: "sm", title: t("adjournSessionTitle"), onClose: () => !pending && setDialog(null) },
            h(P.Stack, { gap: "md" },
              h(P.Text, { variant: "secondary" }, t("adjournedSessionMessage")),
              h(P.Field, { label: t("adjournEndTime"), required: true },
                h(P.Input, { type: "time", value: adjournEnd, disabled: pending, onChange: (event) => setAdjournEnd(event.target.value) }),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
              h(P.Inline, { justify: "end", gap: "sm" },
                h(P.Button, { variant: "secondary", disabled: pending, onClick: () => setDialog(null) }, t("cancel")),
                h(P.Button, { variant: "primary", disabled: pending || !adjournEnd, onClick: () => run(
                  () => api(`/api/sessions/${encodeURIComponent(sessionId)}/adjourn/`, { method: "POST", body: JSON.stringify({ adjourned: true, ended_at: laIso(session.date, adjournEnd) }) }),
                  "hearingAdjournedNotice",
                  onChanged,
                ) }, t("adjournSessionAction")),
              ),
            ),
          )
        : null,
      dialog?.kind === "place"
        ? h(
            P.Dialog,
            {
              open: true,
              title: t(dialog.part === 1 ? "addAssignmentCase" : "addHearingCase"),
              closeLabel: t("cancel"),
              onClose: () => !pending && setDialog(null),
              footer: h(P.Inline, null,
                h(P.Button, { disabled: pending, onClick: () => setDialog(null) }, t("cancel")),
                h(P.Button, {
                  variant: "primary",
                  loading: pending,
                  disabled: pending || !choice[`part${dialog.part}`],
                  onClick: () => place(dialog.part),
                }, t("addCase")),
              ),
            },
            h(P.Stack, { gap: "md" },
              h(P.Field, { label: t(dialog.part === 1 ? "addToPart1" : "addToPart2") },
                h(P.Select, {
                  value: choice[`part${dialog.part}`],
                  disabled: pending,
                  onChange: (event) => setChoice((old) => ({ ...old, [`part${dialog.part}`]: event.target.value })),
                  options: [
                    { value: "", label: (dialog.part === 1 ? c1 : c2).length ? t("chooseCase") : t("noCandidates") },
                    ...(dialog.part === 1 ? c1 : c2).map((row) => ({ value: row.id, label: casePlacementLabel(row) })),
                  ],
                }),
              ),
              failure ? h(P.Notice, { tone: "danger" }, failure) : null,
            ),
          )
        : null,
      h(
        P.ConfirmDialog,
        {
          open: dialog?.kind === "cancelTestimony",
          title: t("cancelInvitationTitle"),
          message: t("cancelInvitationMessage"),
          confirmLabel: t("cancelInvitation"),
          cancelLabel: t("keepInvitation"),
          destructive: true,
          onConfirm: () =>
            run(
              () =>
                api(`/api/appointments/${encodeURIComponent(dialog.appointment.id)}/cancel/`, {
                  method: "POST",
                  body: JSON.stringify({ expected_version: dialog.appointment.version }),
                }),
              "invitationCancelled",
            ),
          onCancel: () => !pending && setDialog(null),
        },
        dialog?.kind === "cancelTestimony" ? h(P.Text, { as: "p", variant: "strong" }, dialog.appointment.party_name) : null,
        failure && dialog?.kind === "cancelTestimony" ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
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
    );
  }

  // Council search: the server reauthorizes every hit before returning names or snippets.
  function searchProblem(query) {
    const q = String(query || "").trim();
    if (q.length < 2 || q.length > 200) return "searchLength";
    return null;
  }

  // Search phrases go in a POST body so names never land in URLs or access logs.
  // Older servers only accept GET; fall back only on 405.
  async function runSearch(api, q, history) {
    try {
      return await api("/api/search/", { method: "POST", body: JSON.stringify({ q, history }) });
    } catch (error) {
      if (error.status !== 405) throw error;
      return api(`/api/search/?q=${encodeURIComponent(q)}&history=${history ? "true" : "false"}`);
    }
  }

  // Document search on the SearchWorkspace template (search-workspace.md): the query, the result count and the
  // results. The phrase still goes to the server only when Search is chosen (or Enter), never per keystroke
  // (plenix-requests.md PLX-022).
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
    async function run(event) {
      event.preventDefault();
      const issue = searchProblem(query);
      setProblem(issue);
      if (issue) return;
      setPending(true);
      setFailure(null);
      setResult(null);
      try {
        const [data, caseList] = await Promise.all([
          runSearch(api, query.trim(), history),
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
    const rows = (result || []).map((row) => ({
      ...row,
      id: row.file_id,
      case_number: cases[row.case_id] || "—",
    }));
    // Before a search runs, the template's "nothing matches" line asks for a phrase instead.
    const nothing = t(pending ? "loading" : failure ? "loadFailed" : result === null ? "searchStart" : "searchNone");
    return h(
      P.Stack,
      { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t("searchTitle")),
      h(
        P.Form,
        { onSubmit: run, label: t("searchTitle"), noValidate: true },
        // Outside the workspace body, which draws its results only when there are some.
        problem ? h(P.Notice, { tone: "warning" }, t(problem)) : null,
        failure ? h(P.Notice, { tone: "warning" }, failure) : null,
        h(P.SearchWorkspace, {
          title: t("searchResults"),
          query,
          onQueryChange: (next) => { setQuery(String(next).slice(0, 200)); setProblem(null); },
          placeholder: t("searchAction"),
          count: rows.length,
          noun: t("searchNoun"),
          plural: t("searchNouns"),
          locale: lang === "ar" ? "ar-EG" : "en-US",
          strings: { title: t("searchTitle"), searchField: t("searchField"), noMatchQuery: nothing, noMatchFilters: nothing, noMatchQueryFilters: nothing },
          headEnd: h(P.Inline, { gap: "md", align: "center", wrap: true },
            h(P.Checkbox, { label: t("searchHistory"), checked: history, disabled: pending, onChange: (e) => setHistory(e.target.checked) }),
            h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("searchAction"))),
        },
        h(window.CTMShell.Table, {
          label: t("searchResults"),
          rows,
          empty: nothing,
          onSelect: (id) => { const row = rows.find((item) => item.id === id); if (row) onCase(row.case_id); },
          rowMenu: [{ label: t("open"), icon: "open", onSelect: (row) => onCase(row.case_id) }],
          cardCount: plural(lang, "resultsCount"),
          template: { title: "name", subtitle: "case_number" },
          columns: [
            { title: t("searchResults"), field: "name", kind: "name", minWidth: "16rem" },
            { title: t("caseNumber"), field: "case_number", kind: "data", minWidth: "10rem" },
          ],
        })),
      ),
    );
  }

  // Council Home: upcoming session, own cases and what needs attention.
  // Larger analytics belong to Statistics and Reports, not here.
  // Pending appeals and closed-case later petitions (F12); older servers ignore the
  // state filter, so the same rule is applied here.
  function considerationQueue(items) {
    return (items || []).filter(
      (row) => row && row.status === "submitted" && (row.kind === "appeal" || (row.kind === "petition" && row.origin === "closed_case_intake")),
    );
  }

  function myCases(cases, user) {
    return (cases || []).filter((row) => row.status === "open" && user?.id && row.assigned_member_id === user.id);
  }

  // Spouses as one line, husband first when the genders are known (issue 170: "husband · wife").
  function spousesText(row) {
    const people = [
      { name: row.applicant_name, gender: row.applicant_gender },
      { name: row.respondent_name, gender: row.respondent_gender },
    ].filter((person) => person.name);
    const male = (g) => g === "M" || g === "male";
    if (people.length === 2 && !male(people[0].gender) && male(people[1].gender)) people.reverse();
    return people.map((person) => isolate(person.name)).join(" · ");
  }

  // The tiles of Home's one row (issue 170, design §2): short labels, each opens its list; a count the server
  // did not send is "–" (value left out), never 0. "For council" has no list page yet, so it has no link.
  function homeTiles({ dashboard, unread, consideration }, user, t, n) {
    const route = (id, path) => window.CTMRoutes?.routeFor(id) || path;
    return [
      { id: "mine", icon: "folder-open", title: t("myCases"), value: n(dashboard?.my_cases), href: route("myCases", "/cases/mine") },
      { id: "unread", icon: "hdr-bell", title: t("tileUnread"), value: n(unread), href: route("notifications", "/notifications") },
      ...(canManage(user) ? [
        { id: "review", icon: "doc-text", title: t("tileNewApplications"), value: n(dashboard?.review_queue), href: route("newApplications", "/applications/new") },
        { id: "consideration", icon: "doc-text", title: t("tileForCouncil"), value: n(consideration) },
      ] : []),
    ];
  }

  // Council Home (issue 170, D-0046; design docs/implementation/slices/ctm3-170-home/design.md). Top to bottom:
  // the next council session leads, then one row of equal tiles, then My cases as a DataGrid. Each region loads
  // on its own, so one failure shows its own Notice and Retry while the others still show (design §3).
  // Council members and the statistics summary follow when their aggregate endpoints exist.
  function CouncilHome({ api, lang, user, onCase, onSession, onNavigate }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const n = (value) => typeof value === "number" ? new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US").format(value) : undefined;
    const [dash, retryDash] = useLoad(() => api("/api/dashboard/"), [user?.id]);
    const [counts, retryCounts] = useLoad(
      () => Promise.all([
        api("/api/notifications/"),
        canManage(user) ? api("/api/applications/?state=council_consideration") : Promise.resolve({ items: [] }),
      ]).then(([notes, consideration]) => ({ unread: notes.unread_count || 0, consideration: considerationQueue(consideration.items).length })),
      [user?.id],
    );
    const leadId = dash.data?.upcoming_sessions?.[0]?.id || null;
    // The lead session's time, place and agenda come from the session endpoints until /api/dashboard/ sends them.
    const [lead, retryLead] = useLoad(
      () => leadId
        ? Promise.all([
            api("/api/sessions/"),
            api(`/api/sessions/${encodeURIComponent(leadId)}/agenda/`),
            api(`/api/sessions/${encodeURIComponent(leadId)}/answers/`).catch(() => null),
          ]).then(([sessions, agenda, answers]) => ({
            session: (sessions.items || []).find((row) => row.id === leadId) || agenda.session || { id: leadId },
            agendaCount: (agenda.items || []).length,
            answers,
          }))
        : Promise.resolve(null),
      [leadId],
    );
    const [cases, retryCases] = useLoad(() => api("/api/cases/"), [user?.id]);

    // A same-origin tile link opens its page inside the app (no reload); other clicks behave as links.
    const follow = (event) => {
      const link = event.target.closest && event.target.closest("a[href]");
      if (!link || !onNavigate || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || !window.CTMRoutes?.parse(url.pathname)) return;
      event.preventDefault();
      onNavigate(url.pathname);
    };
    const regionFailure = (retry, error) => h(P.Notice, { tone: "danger" }, serverMessage(error, t), " ",
      h(P.Button, { size: "sm", onClick: retry }, t("retry")));

    // 1. The next council session leads the page.
    const leadRegion = () => {
      if (dash.pending && !dash.data) return h(P.Skeleton, { height: "160px" });
      if (dash.error) return regionFailure(retryDash, dash.error);
      if (!leadId)
        return h(P.Panel, { icon: "calendar", title: t("upcomingSession") },
          h(P.EmptyState, { title: t("noUpcoming"),
            action: canManage(user) && onNavigate ? h(P.Button, { onClick: () => onNavigate(window.CTMRoutes?.routeFor("sessionsUpcoming") || "/sessions/upcoming") }, t("scheduleSession")) : undefined }));
      if (lead.error) return regionFailure(retryLead, lead.error);
      if (!lead.data) return h(P.Skeleton, { height: "160px" });
      const session = lead.data.session;
      const answers = lead.data.answers;
      const mine = answers ? ownAnswer(answers, user) : null;
      const confirmed = confirmedText(answers, t, "confirmedCount");
      const date = session.date || dash.data.upcoming_sessions[0].date;
      // Today's session opens Tribunal Sessions, Current (owner, 2026-10-22); a later one opens its own page,
      // because Current lists only sessions dated today or earlier.
      const openLead = () => date <= todayInLosAngeles() || !onNavigate
        ? onSession && onSession(leadId)
        : onNavigate(window.CTMRoutes?.routeFor("session", leadId) || "/sessions/" + leadId);
      return h(P.Panel, { icon: "calendar", title: sessionLabel(date, t), description: t("upcomingSession"),
        actions: h(P.Button, { variant: "primary", icon: "open", onClick: openLead }, t("openSession")) },
        h(P.Columns, { count: 3, collapseBelow: "wide" },
          h(P.PropertyList, null,
            h(P.PropertyList.Item, { label: t("sessionWhen") }, formatSessionStart(session.starts_at, lang) || t("timeNotRecorded"))),
          h(P.PropertyList, null,
            h(P.PropertyList.Item, { label: t("location") }, session.location || t("notRecorded"))),
          h(P.PropertyList, null,
            h(P.PropertyList.Item, { label: t("agendaItems"), data: true }, n(lead.data.agendaCount))),
          answers ? h(P.PropertyList, null,
            h(P.PropertyList.Item, { label: t("yourAnswer") },
              h(P.Badge, { tone: answerTone(mine?.answer), icon: mine?.answer === "attend" ? "check" : mine?.answer === "not_attend" ? "close" : undefined }, t(answerKey(mine?.answer))))) : null,
          confirmed ? h(P.PropertyList, null,
            h(P.PropertyList.Item, { label: t("confirmedColumn") }, confirmed)) : null,
        ));
    };

    // 2. One row of equal tiles.
    const tilesRegion = () => {
      const loading = (dash.pending && !dash.data) || (counts.pending && !counts.data);
      const tiles = homeTiles({ dashboard: dash.data, unread: counts.data?.unread, consideration: counts.data?.consideration }, user, t, n);
      return h(P.Stack, { gap: "sm" },
        counts.error ? regionFailure(retryCounts, counts.error) : null,
        h(P.WidgetGrid, { label: t("needsAttention"), columns: tiles.length, items: tiles,
          renderItem: (item) => h(P.MetricCard, { key: item.id, layout: "tile", size: "lg", icon: item.icon, title: item.title,
            value: item.value, href: item.href, headingLevel: 2, state: loading ? "loading" : "ready" }) }));
    };

    // 3. My cases, once, as a grid: case, spouses, status, next step; a row opens the case.
    const casesRegion = () => {
      const allCases = onNavigate ? h(P.Button, { variant: "ghost", onClick: () => onNavigate(window.CTMRoutes?.routeFor("myCases") || "/cases/mine") }, t("allCases")) : null;
      let body;
      if (cases.pending && !cases.data) body = h(P.Skeleton, { height: "120px" });
      else if (cases.error) body = regionFailure(retryCases, cases.error);
      else {
        const rows = myCases(cases.data.items, user).map((row) => ({
          id: row.id, case_id: row.id, number: row.number, spouses: spousesText(row) || "—",
          status: t(row.status === "closed" ? "closed" : "open"),
          next_step: row.next_step ? t(row.next_step) : "—",
        }));
        body = rows.length
          ? h(window.CTMShell.Table, {
              label: t("myCases"), rows, isStatic: true, empty: t("noMyCases"),
              onSelect: (id) => onCase(id),
              columns: [
                { title: t("caseNumber"), field: "number", kind: "data", width: "10rem" },
                { title: t("spouses"), field: "spouses", kind: "name" },
                { title: t("statusLabel"), field: "status", width: "8rem" },
                { title: t("homeNextStep"), field: "next_step", kind: "wrap" },
              ],
              grid: { mode: "pages", pageSize: 10, pageSizes: [10, 25, 50], strings: { cardCount: plural(lang, "casesCount"), perPage: t("tablePerPage"),
                range: t("tableRange"), count: t("tableCount"), pages: t("tablePages") } },
            })
          : h(P.EmptyState, { title: t("noMyCases"), action: allCases || undefined });
      }
      return h(P.Panel, { icon: "folder-open", title: t("myCases"), actions: allCases || undefined }, body);
    };

    return h(P.Stack, { gap: "lg", onClickCapture: follow },
      h(P.Text, { as: "h1", variant: "title" }, t("homeTitle")),
      leadRegion(),
      tilesRegion(),
      casesRegion(),
    );
  }

  // Separation grounds (issue 120, D-0035): a filing stores codes; screens show the EN/AR label. Earlier filings
  // stored "desertion", read as "abandonment". A value that is not a ground code (older free text) is shown as is.
  const GROUND_CODES = ["infidelity", "abandonment", "abuse", "faith", "addiction", "concealment"];
  const LEGACY_GROUNDS = { desertion: "abandonment" };
  function groundsText(grounds, fallback, t) {
    const list = Array.isArray(grounds) ? grounds : [];
    if (!list.length) return fallback || "";
    return list
      .map((value) => {
        const code = LEGACY_GROUNDS[value] || value;
        return GROUND_CODES.includes(code) ? t(`ground_${code}`) : String(value);
      })
      .join(t("groundsSeparator"));
  }

  // Cases workspace table (open or archived). Built-in header/row menus are off so
  // no untranslated table chrome appears in the Arabic interface.
  function caseRows(cases, archived, query, includeClosed = false) {
    const q = String(query || "").trim().toLowerCase();
    return (cases || [])
      .filter((row) => archived ? row.status === "closed" : row.status === "open" || includeClosed)
      .filter((row) => !q || [row.number, row.applicant_name || "", row.respondent_name || "", row.reason || "", row.assigned_member || ""]
        .some((value) => String(value).toLowerCase().includes(q)));
  }

  // The words a case row is found by: the same fields caseRows searches.
  const caseSearchText = (row) => [row.number, row.applicant?.name, row.respondent?.name, row.reason, row.manager].filter(Boolean).join(" ");

  // My / all active / archived cases on the ListingPage template (CTMShell.Listing): the command bar holds the
  // search (kept per list between visits, view-state.md) and the "show closed" toggle; Open and Delete are in
  // each row's menu, so phones get row cards. Archived cases are read-only (read-only-state.md).
  function CasesTable({ api, user, cases, archived, view, title, lang, onOpen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [includeClosed, setIncludeClosed] = R.useState(false);
    const [deleteTarget, setDeleteTarget] = R.useState(null);
    const [deleting, setDeleting] = R.useState(false);
    const [deleteFailure, setDeleteFailure] = R.useState(null);
    const canDelete = user?.role === "admin";
    async function deleteCase() {
      if (!deleteTarget) return;
      setDeleting(true);
      setDeleteFailure(null);
      try {
        await api(`/api/cases/${encodeURIComponent(deleteTarget.id)}/`, { method: "DELETE" });
        setDeleteTarget(null);
        window.location.reload();
      } catch (error) {
        setDeleteFailure(serverMessage(error, t));
      } finally {
        setDeleting(false);
      }
    }
    const rows = caseRows(cases, archived, "", includeClosed).map((row) => ({
      id: row.id,
      number: row.number,
      applicant: { name: row.applicant_name || "—", gender: row.applicant_gender === "M" ? "male" : row.applicant_gender === "F" ? "female" : undefined },
      respondent: { name: row.respondent_name || "—", gender: row.respondent_gender === "M" ? "male" : row.respondent_gender === "F" ? "female" : undefined },
      reason: groundsText(row.grounds, row.reason, t) || "—",
      manager: row.assigned_member || t("unassigned"),
      status: t(row.status === "closed" ? "closed" : "open"),
      closedAt: row.closed_at ? row.closed_at.slice(0, 10) : "—",
    }));
    const columns = archived
      ? [
          { title: t("caseNumber"), field: "number", kind: "data", sorter: "string" },
          { title: t("caseApplicant"), field: "applicant", type: "person", kind: "name", sorter: "string" },
          { title: t("caseRespondent"), field: "respondent", type: "person", kind: "name", sorter: "string" },
          { title: t("caseAssignee"), field: "manager", type: "person", kind: "name", sorter: "string" },
          { title: t("caseClosedDate"), field: "closedAt", type: "date", sorter: "string" },
          { title: t("statusLabel"), field: "status", maxWidth: "--plx-ref-size-240px", sorter: "string" },
        ]
      : [
          { title: t("caseNumber"), field: "number", kind: "data", sorter: "string" },
          { title: t("caseApplicant"), field: "applicant", type: "person", kind: "name", sorter: "string" },
          { title: t("caseRespondent"), field: "respondent", type: "person", kind: "name", sorter: "string" },
          { title: t("caseReason"), field: "reason", sorter: "string" },
          ...(view === "active" ? [{ title: t("caseAssignee"), field: "manager", type: "person", kind: "name", sorter: "string" }] : []),
          { title: t("statusLabel"), field: "status", maxWidth: "--plx-ref-size-240px", sorter: "string" },
        ];
    const label = title || t(archived ? "archivedTitle" : "casesTitle");
    const rowMenu = [
      { label: t("open"), icon: "open", onSelect: (row) => onOpen(row.id) },
      ...(canDelete ? [{ separator: true }, { label: t("deleteCase"), icon: "trash", danger: true, onSelect: (row) => setDeleteTarget(row) }] : []),
    ];
    const listing = h(window.CTMShell.Listing, {
      label, rows, columns, rowMenu,
      onOpen: (row) => onOpen(row.id),
      empty: t(archived ? "noArchived" : "noOpenCases"),
      search: { text: caseSearchText, placeholder: t("searchCases"), storageKey: `ctm.council.cases.${view || (archived ? "archived" : "active")}` },
      commandBar: archived ? undefined : {
        actions: [{ id: "closed", label: t("showClosedCases"), icon: "archive", toggle: true, pressed: includeClosed, onSelect: (next) => setIncludeClosed(next) }],
      },
      cardCount: plural(lang, "casesCount"),
      template: archived
        ? { title: "number", subtitle: "applicant", date: "closedAt", primary: "status", secondary: "respondent", tertiary: "manager" }
        : { title: "number", subtitle: "applicant", primary: "status", secondary: "respondent", tertiary: view === "active" ? "manager" : "reason" },
    });
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, label),
      archived ? h(P.ReadOnly, { reason: t("archivedReadOnly"), className: "plx-u-flex-1 plx-u-min-h-0" }, listing) : listing,
      h(P.ConfirmDialog, {
        open: Boolean(deleteTarget), title: t("deleteCaseTitle"), message: t("deleteCaseMessage"),
        confirmLabel: t("deleteCase"), cancelLabel: t("cancel"), onConfirm: deleteCase,
        onCancel: () => !deleting && setDeleteTarget(null),
      }, deleteFailure && deleteTarget ? h(P.Notice, { tone: "danger" }, deleteFailure) : null),
    );
  }

  // New applications awaiting completeness review, on the ListingPage template; a row opens the standard case view.
  function NewApplicationsTable({ api, lang, user, onOpen }) {
    const R = window.React, P = window.Plenix, h = R.createElement, t = translator(lang);
    const [state, retry] = useLoad(() => api(REVIEW_URL), [user?.id]);
    if (!canManage(user)) return h(P.EmptyState, { title: t("reviewOnlyAdmin") });
    if (state.pending && !state.data) return loadingView(P, h, t);
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    const rows = awaitingReview(state.data?.items).map((row) => ({
      ...row,
      applicant: { name: row.applicant_name || "—", gender: row.applicant_gender === "M" ? "male" : row.applicant_gender === "F" ? "female" : undefined },
      respondent: { name: row.respondent_name || "—", gender: row.respondent_gender === "M" ? "male" : row.respondent_gender === "F" ? "female" : undefined },
      status: t("applicationSubmitted"),
      assigned_to: row.assigned_to || t("unassigned"),
      submitted: row.submitted_at ? formatWhen(row.submitted_at, lang) : t("notRecorded"),
    }));
    const open = (row) => onOpen(row.case_id, row.id);
    return h(P.Stack, { gap: "md", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t("newApplications")),
      h(window.CTMShell.Listing, {
        label: t("newApplications"), rows, empty: t("reviewQueueEmpty"), isStatic: true,
        onOpen: open,
        rowMenu: [{ label: t("open"), icon: "open", onSelect: open }],
        cardCount: plural(lang, "applicationsCount"),
        template: { title: "case_number", subtitle: "applicant", date: "submitted", primary: "status", secondary: "respondent", tertiary: "assigned_to" },
        columns: [
          { title: t("caseNumber"), field: "case_number", kind: "data", minWidth: "9rem" },
          { title: t("applicant"), field: "applicant", type: "person", minWidth: "11rem" },
          { title: t("respondent"), field: "respondent", type: "person", minWidth: "11rem" },
          { title: t("statusLabel"), field: "status", minWidth: "9rem" },
          { title: t("assignedTo"), field: "assigned_to", type: "person", minWidth: "12rem" },
          { title: t("submitted"), field: "submitted", minWidth: "12rem" },
        ],
      }),
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
    // A dashboard of MetricCards (metric-card.md) in a WidgetGrid (dashboard-grid.md); the per-manager counts
    // are one ranked list card.
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = useLoad(
      () => Promise.all([api("/api/cases/"), api("/api/sessions/")]).then(([cases, sessions]) => caseStatistics(cases.items, sessions.items)),
      [],
    );
    if (state.pending && !state.data) return loadingView(P, h, t);
    if (state.error) return loadFailure(P, h, t, retry, state.error);
    const s = state.data;
    const n = (value) => new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US").format(value);
    const strings = { more: t("metricMore") };
    const card = (id, icon, title, context, value) => ({ id, render: () => h(P.MetricCard, { icon, title, context, value: n(value), headingLevel: 2, strings }) });
    const items = [
      card("open", "folder-open", t("statsOpen"), t("statsCases"), s.open),
      card("unassigned", "folder-open", t("statsUnassigned"), t("statsCases"), s.unassigned),
      card("closed", "folder-open", t("statsClosed"), t("statsCases"), s.closed),
      card("planned", "calendar", t("planned"), t("statsSessions"), s.plannedSessions),
      card("closedSessions", "calendar", t("closed"), t("statsSessions"), s.closedSessions),
      { id: "byManager", span: "2", render: () => s.byManager.length
        ? h(P.MetricCard, { type: "list", icon: "settings-users", title: t("statsByManager"), headingLevel: 2, strings,
            items: s.byManager.map(([name, count]) => ({ id: name, label: name, value: n(count), amount: count })) })
        : h(P.MetricCard, { icon: "settings-users", title: t("statsByManager"), state: "empty", emptyText: t("statsNoAssigned"), headingLevel: 2, strings }) },
    ];
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("statsTitle")),
      s.partial ? h(P.Notice, { tone: "warning" }, t("statsPartial")) : null,
      h(P.WidgetGrid, { label: t("statsTitle"), items, renderItem: (item) => item.render() }),
    );
  }

  window.CTMCouncil = {
    laNowTime,
    words,
    translator,
    groundsText,
    canManage,
    isolate,
    unsavedDrafts,
    awaitingReview,
    reviewProblem,
    sessionLabel,
    sessionReference,
    sessionStatusKey,
    archivedAgendaRows,
    agendaDisplayStatus,
    sessionDateProblem,
    todayInLosAngeles,
    splitSessions,
    sessionBuckets,
    hearingTitle,
    part1Candidates,
    part2Candidates,
        casePlacementLabel,
    presidents,
    assignmentAuthorizers,
    canRecordAssignment,
    assignableMembers,
    assignmentProblem,
    groupAgenda,
    pendingAssignmentCount,
    agendaActions,
    testimonyProblem,
    laIso,
    activeAppointments,
    rescheduleProblem,
    reschedulePayload,
    writerOf,
    serverMessage,
    answerText,
    fieldLabel,
    formatWhen,
        formatSessionStart,
    useLoad,
    loadFailure,
    loadingView,
    plural,
    guarded,
    ReviewQueuePanel: guarded(ReviewQueuePanel),
    ReviewWorkspace: guarded(ReviewWorkspace),
    SessionList: guarded(SessionList),
    SessionWorkspace: guarded(SessionWorkspace),
    SessionAnswers: guarded(SessionAnswers),
    canSendReminders,
    sessionAnswerable,
    ownAnswer,
    answerKey,
    answerTone,
    confirmedText,
    reminderProblem,
    searchProblem,
    runSearch,
    SearchWorkspace: guarded(SearchWorkspace),
    myCases,
    considerationQueue,
    CouncilHome: guarded(CouncilHome),
    homeTiles,
    spousesText,
    caseRows,
    CasesTable: guarded(CasesTable),
    NewApplicationsTable: guarded(NewApplicationsTable),
    caseStatistics,
    StatisticsWorkspace: guarded(StatisticsWorkspace),
  };
})();
