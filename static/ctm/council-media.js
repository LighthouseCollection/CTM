/* CTM council media: whole-report audio recording, completed report reader with
   recording/transcript tabs, and evidence viewers. Loads after council.js and
   council-case.js. Every file is read through authorized /api/files/{id}/ routes;
   no storage URL is ever built here. The server enforces all permissions. */
(() => {
  "use strict";
  const base = window.CTMCouncil;
  if (!base || !base.caseTranslator) return;

  // ---------- Pure logic (unit tested) ----------

  // Formats the server accepts by signature: WebM (stored as video/webm, 500 MB),
  // MP4 (Safari/iOS, video/mp4, 500 MB) and Ogg (audio/ogg, 100 MB).
  const RECORDER_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];

  function chooseMimeType(isSupported) {
    if (typeof isSupported !== "function") return "";
    return RECORDER_TYPES.find((type) => {
      try {
        return isSupported(type);
      } catch {
        return false;
      }
    }) || "";
  }

  function extensionFor(mimeType) {
    const type = String(mimeType || "");
    if (type.startsWith("audio/mp4") || type.startsWith("video/mp4")) return "m4a";
    if (type.startsWith("audio/ogg")) return "ogg";
    return "webm";
  }

  function sizeLimitBytes(mimeType) {
    return String(mimeType || "").startsWith("audio/ogg") ? 100 * 1024 * 1024 : 500 * 1024 * 1024;
  }

  // Maps getUserMedia/MediaRecorder failures to user-facing message keys.
  function microphoneProblem(error, context) {
    if (context && context.secure === false) return "micInsecure";
    if (context && context.supported === false) return "micUnsupported";
    const name = error && error.name;
    if (name === "NotAllowedError" || name === "PermissionDeniedError") return "micDenied";
    if (name === "NotFoundError" || name === "DevicesNotFoundError" || name === "OverconstrainedError") return "micMissing";
    if (name === "NotReadableError" || name === "TrackStartError" || name === "AbortError") return "micBusy";
    if (name === "SecurityError") return "micInsecure";
    return "micFailed";
  }

  function formatDuration(ms) {
    const total = Math.max(0, Math.floor((ms || 0) / 1000));
    const h = Math.floor(total / 3600),
      m = Math.floor((total % 3600) / 60),
      s = total % 60;
    const pad = (n) => String(n).padStart(2, "0");
    return h ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
  }

  // Elapsed recording time excluding paused periods.
  function elapsedMs(segments, now) {
    return (segments || []).reduce((sum, seg) => sum + Math.max(0, (seg.end ?? now) - seg.start), 0);
  }

  // Which viewer an evidence file uses, by MIME type only (purpose decides section).
  function viewerKind(file) {
    const type = String(file?.mime_type || "");
    if (type.startsWith("image/")) return "image";
    if (type.startsWith("audio/")) return "audio";
    if (type.startsWith("video/")) return "video";
    if (type === "application/pdf") return "pdf";
    return "download";
  }

  // Authorized routes only: the listing's own URLs, else the file id route.
  function fileUrls(file) {
    const id = encodeURIComponent(file.id);
    return {
      download: file.download_url && file.download_url.startsWith("/api/files/") ? file.download_url : `/api/files/${id}/`,
      inline: file.preview_url && file.preview_url.startsWith("/api/files/") ? file.preview_url : null,
    };
  }

  const APPLICATION_CODES = new Set(["PHOTO", "SPOUSE_PHOTO", "MC", "CMC", "CDD", "RO", "PET"]);
  function sectionFiles(rows, section) {
    return (rows || []).filter((row) =>
      section === "documents" ? APPLICATION_CODES.has(row.category) : !APPLICATION_CODES.has(row.category),
    );
  }

  function formatBytes(n, lang) {
    const value = Number(n) || 0;
    const fmt = (v, unit) => `${new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US", { maximumFractionDigits: 1 }).format(v)} ${unit}`;
    if (value >= 1024 * 1024) return fmt(value / (1024 * 1024), "MB");
    if (value >= 1024) return fmt(value / 1024, "KB");
    return fmt(value, "B");
  }

  // ---------- Local recording store (IndexedDB) ----------
  // Chunks are written every few seconds while recording so an interrupted tab
  // keeps what was captured. Entries are removed after a successful submission.

  const DB_NAME = "ctm-council-recordings";
  function openStore(indexedDB) {
    return new Promise((resolve, reject) => {
      if (!indexedDB) return reject(new Error("no-indexeddb"));
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("chunks")) db.createObjectStore("chunks", { autoIncrement: true }).createIndex("key", "key");
        if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta", { keyPath: "key" });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  function recordingStore(indexedDB = window.indexedDB) {
    const tx = async (stores, mode, fn) => {
      const db = await openStore(indexedDB);
      return new Promise((resolve, reject) => {
        const t = db.transaction(stores, mode);
        let result;
        Promise.resolve(fn(t)).then((value) => (result = value));
        t.oncomplete = () => {
          db.close();
          resolve(result);
        };
        t.onerror = () => {
          db.close();
          reject(t.error);
        };
      });
    };
    const all = (request) => new Promise((resolve) => (request.onsuccess = () => resolve(request.result)));
    return {
      async putMeta(meta) {
        return tx(["meta"], "readwrite", (t) => t.objectStore("meta").put(meta));
      },
      async getMeta(key) {
        return tx(["meta"], "readonly", (t) => all(t.objectStore("meta").get(key)));
      },
      async addChunk(key, blob) {
        return tx(["chunks"], "readwrite", (t) => t.objectStore("chunks").add({ key, blob, at: Date.now() }));
      },
      async chunks(key) {
        return tx(["chunks"], "readonly", (t) => all(t.objectStore("chunks").index("key").getAll(key)));
      },
      async clear(key) {
        return tx(["chunks", "meta"], "readwrite", (t) => {
          t.objectStore("meta").delete(key);
          const index = t.objectStore("chunks").index("key");
          const cursor = index.openCursor(key);
          cursor.onsuccess = () => {
            if (cursor.result) {
              cursor.result.delete();
              cursor.result.continue();
            }
          };
        });
      },
      async move(fromKey, toKey) {
        const meta = await this.getMeta(fromKey);
        const rows = await this.chunks(fromKey);
        if (!meta && !rows.length) return false;
        await tx(["chunks", "meta"], "readwrite", (t) => {
          if (meta) t.objectStore("meta").put({ ...meta, key: toKey });
          for (const row of rows) t.objectStore("chunks").add({ ...row, key: toKey });
        });
        await this.clear(fromKey);
        return true;
      },
    };
  }

  // ---------- Words ----------

  const words = {
    en: {
      recordingTab: "Recording",
      transcriptsTab: "Transcripts",
      answersTab: "Report",
      recordingTitle: "Interview recording",
      recordingHelp:
        "One recording covers the whole interview (not individual questions). Audio is kept on this device until you submit it. Submitting stores the original and queues transcription.",
      noticeLabel: "I told the person that this interview is being recorded, and they understood.",
      noticeRequired: "Confirm that the person was told about the recording before you start.",
      start: "Start recording",
      pause: "Pause",
      resume: "Resume",
      stop: "Stop",
      discard: "Discard recording",
      discardTitle: "Discard this recording?",
      discardMessage: "The captured audio on this device is deleted. Nothing has been submitted.",
      submit: "Submit recording",
      submitTitle: "Submit this recording?",
      submitMessage:
        "The original audio is stored with this report and transcription is queued. The recording cannot be changed after submission.",
      recordingState: "Recording",
      pausedState: "Paused",
      stoppedState: "Ready to review",
      recoveredState: "Recovered after an interruption",
      elapsed: "Length",
      playbackLabel: "Recorded interview audio",
      captureOnly: "Record now; submit it from the saved report after you save the interview answers.",
      recovered:
        "A recording from an earlier session on this device was recovered. Review it, then submit or discard it.",
      interrupted:
        "Recording stopped unexpectedly (the microphone or device was interrupted). The audio captured up to that point is kept.",
      micDenied: "Microphone access was blocked. Allow the microphone for this site in the browser settings, then try again.",
      micMissing: "No microphone was found on this device.",
      micBusy: "The microphone is being used by another application or could not be started.",
      micInsecure: "Recording needs a secure (HTTPS) connection.",
      micUnsupported: "This browser cannot record audio. Use a current version of Chrome, Edge, Firefox or Safari.",
      micFailed: "The recording could not start.",
      storageUnavailable:
        "This browser is not keeping a local copy (private browsing or storage blocked). Keep this page open until you submit.",
      tooLarge: "This recording is larger than the server accepts for this format.",
      uploading: "Uploading the original recording…",
      scanning: "Waiting for the automatic safety check…",
      associating: "Linking the recording to this report…",
      queueing: "Queuing transcription…",
      submitted: "The recording was submitted and transcription was queued.",
      uploadFailed: "The recording could not be submitted. It is still kept on this device; try again.",
      scanRejected: "The automatic safety check rejected this recording. It is kept on this device.",
      checkAgain: "Check again",
      retrySubmit: "Try again",
      writerOnlyRecording: "Only the assigned case manager, or the administrator or secretary, records while the proceeding is open.",
      notInterview: "Recordings are used for interviews conducted by the case manager.",
      beforeUnload: "A recording is in progress.",
      reportsList: "Completed reports",
      completedBy: "Report completed by",
      completedDate: "Completed date",
      intakeBy: "Intake by",
      noReports: "No completed reports are available.",
      chooseReport: "Select a report",
      reportFor: "Report for",
      followUpOf: "Follow-up to an earlier report",
      openOriginal: "Open original report",
      observations: "Council observations",
      history: "Revision history",
      loadHistory: "Show revision history",
      version: "Version",
      response: "Response",
      revisionPending: "Revising a report is available to its original author once the server identifies report authorship.",
      revisionNotAllowed: "Only the report's original council author can revise it, while the case and proceeding are open.",
      revise: "Revise report",
      reviseTitle: "Revise report narrative",
      reviseHelp:
        "Saving creates a new version. Earlier versions are kept and stay in the revision history. To investigate further, request a follow-up report instead.",
      saveRevision: "Save as new version",
      revisionSaved: "Saved as version {version}.",
      revisionNoChange: "Nothing has changed from the current version.",
      revisionConflict:
        "Version {version} was saved by {actor} after you started editing. Your text is kept below and has not been saved. Look at version {version}, then save your text as version {next} or discard it.",
      showVersion: "Show version {version}",
      hideVersion: "Hide version {version}",
      latestVersionTitle: "Version {version} · {when} · {actor}",
      overwriteTitle: "Save your text as version {next}?",
      overwriteMessage:
        "Version {version} stays in the revision history unchanged. Your text becomes version {next}. Attachments and other non-text answers are taken from version {version}.",
      overwriteConfirm: "Save as version {next}",
      previousSaveReceived: "Your earlier save was received as version {version}. Changes you made after it are not saved yet.",
      saveUncertain:
        "The server did not confirm this save. Your text is kept. It may already be saved: “Try again” sends exactly the same version, which the server never saves twice.",
      retrySave: "Try again",
      revisionFixAndSave: "Correct the text and save again. Your text is kept.",
      sessionExpiredKept: "Your session has ended. Sign in again in a new tab, then save here. Your text stays on this page while it is open.",
      reportMissing: "This report is no longer available to you. Your text is still shown so you can copy it.",
      discardUncertainMessage:
        "The text you typed will be removed from this page. Your last save was not confirmed by the server and may already be stored as a new version.",
      saveAnyway: "Save my text as a new version",
      discardChanges: "Discard my changes",
      revisionDenied: "This revision was not allowed. Your text is still shown so you can copy it.",
      revisionKept: "Your text is kept; try again.",
      nonTextKept: "Attached files and other non-text answers are kept unchanged.",
      unsavedRevision: "A report revision has not been saved.",
      revisionRestored: "Your unsaved revision was restored. Save it as a new version or discard it.",
      discardRevisionTitle: "Discard unsaved changes?",
      discardRevisionMessage: "The text you typed in this revision will be removed. Nothing has been saved.",
      keepEditing: "Keep editing",
      priestTestimony: "Written testimony",
      recordingsTitle: "Submitted recordings",
      noRecordings: "No recording has been submitted for this report.",
      recordingItem: "Recording {n}",
      submittedOn: "Submitted",
      recDuration: "Length",
      durationUnknown: "Not recorded",
      noticeState: "Recording notice",
      noticeGiven: "Confirmed",
      noticeMissing: "Not confirmed",
      originalUnavailable: "The original audio is not available here: it has not passed the automatic safety check.",
      statusNotQueued: "Transcription has not been requested for this recording.",
      statusNotQueuedNoAuthority: "Transcription has not been requested. The case manager can request it.",
      queueTranscription: "Request transcription",
      queuedDone: "Transcription requested. The original audio is kept.",
      statusMissing: "Transcription was requested, but no processing record exists. The original audio is kept.",
      statusQueued: "Waiting for transcription (attempt {attempt}). The transcription service may not be configured on this server yet, so nothing may have been processed. The original audio is kept.",
      statusRunning: "Transcription in progress (attempt {attempt}).",
      statusSucceeded: "Transcription finished (attempt {attempt}). Generated text is shown to other council members only after the case manager reviews it.",
      statusFailed: "Transcription failed (attempt {attempt}). {error} You can retry; earlier attempts are kept.",
      statusFailedNoRetry: "Transcription failed (attempt {attempt}). {error} Only the case manager can retry, while the case is open.",
      statusOther: "Transcription state: {state} (attempt {attempt}).",
      retryTranscription: "Retry transcription",
      retryDone: "Attempt {attempt} is queued. Earlier attempts and any earlier text are kept.",
      noTranscriptReleased: "No transcript is available to you yet. Generated text is shown to other council members only after the case manager reviews it.",
      transcriptLanguage: "Language",
      transcriptKind: "Version type",
      transcriptState: "Review",
      transcriptSaved: "Saved",
      transcriptText: "Transcript text",
      lang_en: "English",
      lang_ar: "Arabic",
      lang_mixed: "Mixed English and Arabic",
      kind_original: "Original",
      kind_translation: "Translation",
      versionOption: "Version {version} · {when} · {state}",
      stateReviewed: "Reviewed",
      stateUnreviewed: "Not reviewed",
      unreviewedNotice: "Generated text, not yet reviewed. Until this exact version is reviewed, only the case manager and administrators can read it.",
      olderVersionNotice: "This is an earlier version. The latest version is {version}.",
      markReviewed: "Mark as reviewed",
      reviewTitle: "Mark version {version} as reviewed?",
      reviewMessage: "Other council members will be able to read this exact version. Later corrections need their own review.",
      reviewDone: "Version {version} is reviewed.",
      correctText: "Correct text",
      correctTitle: "Correct transcript text",
      correctHelp: "Saving creates version {next}. Earlier versions are kept. The new version needs its own review. Timings from the generated text are not carried into corrected text.",
      saveCorrection: "Save as version {next}",
      correctionSaved: "Saved as version {version}. It needs review.",
      correctionStale: "A newer version of this transcript was saved. Your text is kept below. Load the latest version, then correct it again.",
      reloadLatest: "Load latest version",
      correctionEmpty: "Enter the corrected text.",
      correctionUncertain: "The server did not confirm this correction. Your text is kept. Saving the same text again will not create a duplicate.",
      correctionRestored: "Your unsaved correction was restored. Save it or discard it.",
      discardCorrectionTitle: "Discard your correction?",
      discardCorrectionMessage: "The corrected text you typed will be removed. Nothing has been saved.",
      unsavedCorrection: "A transcript correction has not been saved.",
      segmentsTitle: "Timed segments",
      reportAuthor: "Author",
      reportSubmitted: "Submitted",
      reportMethod: "Method",
      method_written: "Entered in CTM",
      method_external: "External source link",
      method_paper: "Paper original recorded by the council",
      method_recording: "Recording made by the council",
      recordedOn: "Recorded on",
      recordedOriginal: "Recording",
      recordedOriginalHelp: "The council's recording of the priest's report. Its transcript appears under Transcripts once one is produced; until then none exists.",
      recordedOriginalName: "Recording — {title}",
      recordedNotRevisable: "A recorded response is kept as recorded and cannot be revised. A transcript correction or a follow-up request is separate.",
      paperRecordedBy: "Recorded by",
      paperReceivedOn: "Paper received",
      paperOriginal: "Paper original",
      paperOriginalHelp: "The scanned paper as the priest returned it. It has not been transcribed.",
      paperOriginalName: "Paper original — {title}",
      paperNotRevisable: "A paper response is kept as received and cannot be revised. Use a follow-up request for anything further.",
      evidenceTitle: "Evidence",
      demoEvidenceTitle: "Demo evidence images",
      demoEvidenceHint: "Demo-only images supplied for the case review walkthrough.",
      demoEvidenceImage: "Open demo evidence image {number}",
      documentsTitle: "Documents",
      demoDocumentsTitle: "Demo documents",
      demoDocumentsHint: "Demo-only documents supplied for the case review walkthrough.",
      openDocument: "Open document",
      downloadDocument: "Download document",
      olderVersions: "Include older versions",
      noFiles: "No technically cleared files are available in this section.",
      chooseFile: "Select a file",
      download: "Download",
      openPdf: "Open in browser",
      failedEngine: "The document viewer could not start. Open the PDF in the browser instead.",
      failedAccess: "This document can't be opened: it is missing, or your access to it was withdrawn.",
      failedParse: "This file is not a readable PDF. Download it or open it in the browser instead.",
      failedRender: "A page could not be drawn. Try again, or open the PDF in the browser.",
      pdfFallbackHint: "The browser's own PDF viewer uses the same protected link.",
      pdfAccessHint: "Opening it in the browser uses the same protected link and will be refused too if access was withdrawn.",
      wordDownload: "Word documents open in a compatible application after download.",
      fullScreen: "Full screen",
      imageAlt: "Evidence image",
      size: "Size",
      uploadedOn: "Uploaded",
      category: "Category",
      more: "Load more",
      cancel: "Cancel",
      loading: "Loading…",
      previous: "Previous",
      next: "Next",
      zoom: "Zoom",
      page: "Page",
      thumbnails: "Thumbnails",
      failed: "Unable to load this file.",
      empty: "Nothing to show",
      retry: "Try again",
      rate: "Playback speed",
      transcript: "Transcript",
      hideTranscript: "Hide transcript",
      pip: "Picture in picture",
      exitPip: "Exit picture in picture",
      unsupported: "This media format cannot be played in this browser. Download it instead.",
      pipFailed: "Picture in picture is unavailable.",
      seek: "Seek",
      fallback: "Open media",
      audioFailed: "Unable to load audio.",
      volume: "Volume",
      mute: "Mute",
      viewerLabel: "Preview",
      closePreview: "Close preview",
      counter: "{index} of {total}",
    },
    ar: {
      recordingTab: "التسجيل",
      transcriptsTab: "النصوص المفرغة",
      answersTab: "التقرير",
      recordingTitle: "تسجيل المقابلة",
      recordingHelp:
        "يغطي التسجيل الواحد المقابلة كاملة (وليس كل سؤال على حدة). ويبقى الصوت على هذا الجهاز حتى تقدّمه. ويؤدي التقديم إلى حفظ الأصل ووضع التفريغ في قائمة الانتظار.",
      noticeLabel: "أبلغتُ الشخص بأن هذه المقابلة مسجَّلة، وقد فهم ذلك.",
      noticeRequired: "أكِّد أن الشخص أُبلغ بالتسجيل قبل البدء.",
      start: "بدء التسجيل",
      pause: "إيقاف مؤقت",
      resume: "استئناف",
      stop: "إيقاف",
      discard: "تجاهل التسجيل",
      discardTitle: "هل تريد تجاهل هذا التسجيل؟",
      discardMessage: "يُحذف الصوت المسجَّل على هذا الجهاز. لم يُقدَّم أي شيء.",
      submit: "تقديم التسجيل",
      submitTitle: "هل تريد تقديم هذا التسجيل؟",
      submitMessage: "يُحفظ الصوت الأصلي مع هذا التقرير ويوضع التفريغ في قائمة الانتظار. ولا يمكن تغيير التسجيل بعد تقديمه.",
      recordingState: "جارٍ التسجيل",
      pausedState: "متوقف مؤقتًا",
      stoppedState: "جاهز للمراجعة",
      recoveredState: "تم استرداده بعد انقطاع",
      elapsed: "المدة",
      playbackLabel: "صوت المقابلة المسجَّل",
      captureOnly: "سجّل الآن؛ ثم قدّم التسجيل من التقرير المحفوظ بعد حفظ إجابات المقابلة.",
      recovered: "تم استرداد تسجيل من جلسة سابقة على هذا الجهاز. راجعه ثم قدّمه أو تجاهله.",
      interrupted: "توقف التسجيل بشكل غير متوقع (انقطع الميكروفون أو الجهاز). ويُحتفظ بالصوت المسجَّل حتى تلك اللحظة.",
      micDenied: "تم حظر الوصول إلى الميكروفون. اسمح بالميكروفون لهذا الموقع من إعدادات المتصفح ثم حاول مجددًا.",
      micMissing: "لم يُعثر على ميكروفون في هذا الجهاز.",
      micBusy: "الميكروفون مستخدم من تطبيق آخر أو تعذر تشغيله.",
      micInsecure: "يتطلب التسجيل اتصالًا آمنًا (HTTPS).",
      micUnsupported: "هذا المتصفح لا يستطيع تسجيل الصوت. استخدم إصدارًا حديثًا من Chrome أو Edge أو Firefox أو Safari.",
      micFailed: "تعذر بدء التسجيل.",
      storageUnavailable: "لا يحتفظ هذا المتصفح بنسخة محلية (تصفح خاص أو تخزين محظور). أبقِ هذه الصفحة مفتوحة حتى تقدّم التسجيل.",
      tooLarge: "حجم هذا التسجيل أكبر مما يقبله الخادم لهذا الصيغة.",
      uploading: "جارٍ رفع التسجيل الأصلي…",
      scanning: "في انتظار فحص الأمان التلقائي…",
      associating: "جارٍ ربط التسجيل بهذا التقرير…",
      queueing: "جارٍ وضع التفريغ في قائمة الانتظار…",
      submitted: "تم تقديم التسجيل ووضع التفريغ في قائمة الانتظار.",
      uploadFailed: "تعذر تقديم التسجيل. وما زال محفوظًا على هذا الجهاز؛ حاول مجددًا.",
      scanRejected: "رفض فحص الأمان التلقائي هذا التسجيل. وما زال محفوظًا على هذا الجهاز.",
      checkAgain: "التحقق مرة أخرى",
      retrySubmit: "إعادة المحاولة",
      writerOnlyRecording: "يسجّل مسؤول القضية المعيَّن أو مسؤول المجلس أو السكرتير فقط ما دام الإجراء مفتوحًا.",
      notInterview: "تُستخدم التسجيلات للمقابلات التي يجريها مسؤول القضية.",
      beforeUnload: "يوجد تسجيل قيد التنفيذ.",
      reportsList: "التقارير المكتملة",
      completedBy: "أكمل التقرير",
      completedDate: "تاريخ الإكمال",
      intakeBy: "استلام بواسطة",
      noReports: "لا توجد تقارير مكتملة.",
      chooseReport: "اختر تقريرًا",
      reportFor: "التقرير بخصوص",
      followUpOf: "متابعة لتقرير سابق",
      openOriginal: "فتح التقرير الأصلي",
      observations: "ملاحظات المجلس",
      history: "سجل التعديلات",
      loadHistory: "عرض سجل التعديلات",
      version: "الإصدار",
      response: "الرد",
      revisionPending: "يتاح تعديل التقرير لكاتبه الأصلي بمجرد أن يحدد الخادم كاتب التقرير.",
      revisionNotAllowed: "لا يعدّل التقرير إلا كاتبه الأصلي من المجلس، ما دامت القضية والإجراء مفتوحين.",
      revise: "تعديل التقرير",
      reviseTitle: "تعديل نص التقرير",
      reviseHelp:
        "يُنشئ الحفظ إصدارًا جديدًا. وتُحفظ الإصدارات السابقة وتبقى في سجل التعديلات. ولإجراء تحقيق إضافي، اطلب تقرير متابعة بدلًا من ذلك.",
      saveRevision: "الحفظ كإصدار جديد",
      revisionSaved: "تم الحفظ كالإصدار {version}.",
      revisionNoChange: "لا يوجد أي تغيير عن الإصدار الحالي.",
      revisionConflict:
        "حفظ {actor} الإصدار {version} بعد أن بدأت التعديل. وما زال نصك معروضًا أدناه ولم يُحفظ. اطّلع على الإصدار {version}، ثم احفظ نصك كإصدار {next} أو تجاهله.",
      showVersion: "عرض الإصدار {version}",
      hideVersion: "إخفاء الإصدار {version}",
      latestVersionTitle: "الإصدار {version} · {when} · {actor}",
      overwriteTitle: "هل تريد حفظ نصك كإصدار {next}؟",
      overwriteMessage:
        "يبقى الإصدار {version} في سجل التعديلات دون تغيير. ويصبح نصك الإصدار {next}. وتؤخذ المرفقات والإجابات غير النصية من الإصدار {version}.",
      overwriteConfirm: "الحفظ كإصدار {next}",
      previousSaveReceived: "استُلم حفظك السابق كإصدار {version}. والتغييرات التي أجريتها بعده لم تُحفظ بعد.",
      saveUncertain:
        "لم يؤكد الخادم هذا الحفظ. وما زال نصك محفوظًا هنا. وقد يكون حُفظ بالفعل: يرسل زر «إعادة المحاولة» الإصدار نفسه تمامًا، ولا يحفظه الخادم مرتين.",
      retrySave: "إعادة المحاولة",
      revisionFixAndSave: "صحّح النص ثم احفظ مجددًا. وما زال نصك محفوظًا هنا.",
      sessionExpiredKept: "انتهت جلستك. سجّل الدخول مجددًا في علامة تبويب جديدة، ثم احفظ هنا. ويبقى نصك في هذه الصفحة ما دامت مفتوحة.",
      reportMissing: "لم يعد هذا التقرير متاحًا لك. وما زال نصك معروضًا لتتمكن من نسخه.",
      discardUncertainMessage:
        "سيُحذف النص الذي كتبته من هذه الصفحة. ولم يؤكد الخادم حفظك الأخير، وقد يكون مخزنًا بالفعل كإصدار جديد.",
      saveAnyway: "حفظ نصي كإصدار جديد",
      discardChanges: "تجاهل تغييراتي",
      revisionDenied: "لم يُسمح بهذا التعديل. وما زال نصك معروضًا لتتمكن من نسخه.",
      revisionKept: "نصك محفوظ؛ حاول مجددًا.",
      nonTextKept: "تبقى الملفات المرفقة والإجابات غير النصية دون تغيير.",
      unsavedRevision: "يوجد تعديل على التقرير لم يُحفظ.",
      revisionRestored: "تمت استعادة تعديلك غير المحفوظ. احفظه كإصدار جديد أو تجاهله.",
      discardRevisionTitle: "هل تريد تجاهل التغييرات غير المحفوظة؟",
      discardRevisionMessage: "سيُحذف النص الذي كتبته في هذا التعديل. لم يُحفظ أي شيء.",
      keepEditing: "متابعة التعديل",
      priestTestimony: "الشهادة المكتوبة",
      recordingsTitle: "التسجيلات المقدَّمة",
      noRecordings: "لم يُقدَّم أي تسجيل لهذا التقرير.",
      recordingItem: "التسجيل {n}",
      submittedOn: "تاريخ التقديم",
      recDuration: "المدة",
      durationUnknown: "غير مسجَّلة",
      noticeState: "إشعار التسجيل",
      noticeGiven: "مؤكَّد",
      noticeMissing: "غير مؤكَّد",
      originalUnavailable: "الصوت الأصلي غير متاح هنا: لم يجتز فحص الأمان التلقائي.",
      statusNotQueued: "لم يُطلب تفريغ هذا التسجيل.",
      statusNotQueuedNoAuthority: "لم يُطلب التفريغ. ويمكن لمسؤول القضية طلبه.",
      queueTranscription: "طلب التفريغ",
      queuedDone: "طُلب التفريغ. والصوت الأصلي محفوظ.",
      statusMissing: "طُلب التفريغ، لكن لا يوجد سجل معالجة. والصوت الأصلي محفوظ.",
      statusQueued: "في انتظار التفريغ (المحاولة {attempt}). قد لا تكون خدمة التفريغ مهيأة على هذا الخادم بعد، لذا ربما لم يُعالَج شيء. والصوت الأصلي محفوظ.",
      statusRunning: "التفريغ جارٍ (المحاولة {attempt}).",
      statusSucceeded: "اكتمل التفريغ (المحاولة {attempt}). ولا يُعرض النص المولَّد على باقي أعضاء المجلس إلا بعد أن يراجعه مسؤول القضية.",
      statusFailed: "فشل التفريغ (المحاولة {attempt}). {error} يمكنك إعادة المحاولة؛ وتُحفظ المحاولات السابقة.",
      statusFailedNoRetry: "فشل التفريغ (المحاولة {attempt}). {error} لا يعيد المحاولة إلا مسؤول القضية ما دامت القضية مفتوحة.",
      statusOther: "حالة التفريغ: {state} (المحاولة {attempt}).",
      retryTranscription: "إعادة محاولة التفريغ",
      retryDone: "المحاولة {attempt} في قائمة الانتظار. وتُحفظ المحاولات السابقة وأي نص سابق.",
      noTranscriptReleased: "لا يوجد نص مفرغ متاح لك بعد. ولا يُعرض النص المولَّد على باقي أعضاء المجلس إلا بعد أن يراجعه مسؤول القضية.",
      transcriptLanguage: "اللغة",
      transcriptKind: "نوع الإصدار",
      transcriptState: "المراجعة",
      transcriptSaved: "تاريخ الحفظ",
      transcriptText: "نص التفريغ",
      lang_en: "الإنجليزية",
      lang_ar: "العربية",
      lang_mixed: "مزيج من الإنجليزية والعربية",
      kind_original: "الأصلي",
      kind_translation: "ترجمة",
      versionOption: "الإصدار {version} · {when} · {state}",
      stateReviewed: "تمت مراجعته",
      stateUnreviewed: "لم تتم مراجعته",
      unreviewedNotice: "نص مولَّد لم تتم مراجعته بعد. وحتى تتم مراجعة هذا الإصدار بعينه، لا يطّلع عليه إلا مسؤول القضية والمسؤولون الإداريون.",
      olderVersionNotice: "هذا إصدار سابق. وأحدث إصدار هو {version}.",
      markReviewed: "اعتماد المراجعة",
      reviewTitle: "هل تريد اعتماد مراجعة الإصدار {version}؟",
      reviewMessage: "سيتمكن باقي أعضاء المجلس من قراءة هذا الإصدار بعينه. وتحتاج التصحيحات اللاحقة إلى مراجعة خاصة بها.",
      reviewDone: "تمت مراجعة الإصدار {version}.",
      correctText: "تصحيح النص",
      correctTitle: "تصحيح نص التفريغ",
      correctHelp: "يُنشئ الحفظ الإصدار {next}. وتُحفظ الإصدارات السابقة. ويحتاج الإصدار الجديد إلى مراجعة خاصة به. ولا تُنقل توقيتات النص المولَّد إلى النص المصحَّح.",
      saveCorrection: "الحفظ كإصدار {next}",
      correctionSaved: "تم الحفظ كالإصدار {version}. ويحتاج إلى مراجعة.",
      correctionStale: "حُفظ إصدار أحدث من هذا التفريغ. وما زال نصك محفوظًا أدناه. حمّل أحدث إصدار ثم صحّحه مجددًا.",
      reloadLatest: "تحميل أحدث إصدار",
      correctionEmpty: "أدخل النص المصحَّح.",
      correctionUncertain: "لم يؤكد الخادم هذا التصحيح. وما زال نصك محفوظًا هنا. ولن يؤدي حفظ النص نفسه مجددًا إلى إنشاء نسخة مكررة.",
      correctionRestored: "تمت استعادة تصحيحك غير المحفوظ. احفظه أو تجاهله.",
      discardCorrectionTitle: "هل تريد تجاهل تصحيحك؟",
      discardCorrectionMessage: "سيُحذف النص المصحَّح الذي كتبته. لم يُحفظ أي شيء.",
      unsavedCorrection: "يوجد تصحيح على نص التفريغ لم يُحفظ.",
      segmentsTitle: "المقاطع الموقَّتة",
      reportAuthor: "الكاتب",
      reportSubmitted: "تاريخ التقديم",
      reportMethod: "الطريقة",
      method_written: "أُدخل في النظام",
      method_external: "رابط مصدر خارجي",
      method_paper: "أصل ورقي سجّله المجلس",
      method_recording: "تسجيل أجراه المجلس",
      recordedOn: "تاريخ التسجيل",
      recordedOriginal: "التسجيل",
      recordedOriginalHelp: "تسجيل المجلس لتقرير الكاهن. ويظهر نصه تحت النصوص بعد إنتاجه؛ ولا يوجد نص قبل ذلك.",
      recordedOriginalName: "التسجيل — {title}",
      recordedNotRevisable: "يُحفظ الرد المسجَّل كما سُجّل ولا يمكن تعديله. وتصحيح النص أو طلب المتابعة أمر منفصل.",
      paperRecordedBy: "سجّله",
      paperReceivedOn: "تاريخ استلام الورقة",
      paperOriginal: "الأصل الورقي",
      paperOriginalHelp: "النسخة الممسوحة ضوئيًا من الورقة كما أعادها الكاهن. ولم يُنسخ نصها.",
      paperOriginalName: "الأصل الورقي — {title}",
      paperNotRevisable: "يُحفظ الرد الورقي كما استُلم ولا يمكن تعديله. استخدم طلب متابعة لأي إضافة.",
      evidenceTitle: "الأدلة",
      demoEvidenceTitle: "صور أدلة تجريبية",
      demoEvidenceHint: "صور تجريبية مضافة لشرح مراجعة القضية فقط.",
      demoEvidenceImage: "فتح صورة الدليل التجريبي {number}",
      documentsTitle: "المستندات",
      demoDocumentsTitle: "مستندات تجريبية",
      demoDocumentsHint: "مستندات تجريبية مضافة لشرح مراجعة القضية فقط.",
      openDocument: "فتح المستند",
      downloadDocument: "تنزيل المستند",
      olderVersions: "تضمين الإصدارات السابقة",
      noFiles: "لا توجد ملفات اجتازت فحص الأمان في هذا القسم.",
      chooseFile: "اختر ملفًا",
      download: "تنزيل",
      openPdf: "فتح في المتصفح",
      failedEngine: "تعذر تشغيل عارض المستندات. افتح ملف PDF في المتصفح بدلًا من ذلك.",
      failedAccess: "لا يمكن فتح هذا المستند: إما أنه غير موجود أو سُحب حق اطلاعك عليه.",
      failedParse: "هذا الملف ليس ملف PDF قابلًا للقراءة. نزّله أو افتحه في المتصفح بدلًا من ذلك.",
      failedRender: "تعذر عرض إحدى الصفحات. حاول مجددًا أو افتح ملف PDF في المتصفح.",
      pdfFallbackHint: "يستخدم عارض PDF الخاص بالمتصفح الرابط المحمي نفسه.",
      pdfAccessHint: "يستخدم الفتح في المتصفح الرابط المحمي نفسه، وسيُرفض كذلك إذا سُحب حق الاطلاع.",
      wordDownload: "تُفتح مستندات Word في تطبيق متوافق بعد تنزيلها.",
      fullScreen: "ملء الشاشة",
      imageAlt: "صورة دليل",
      size: "الحجم",
      uploadedOn: "تاريخ الرفع",
      category: "الفئة",
      more: "عرض المزيد",
      cancel: "إلغاء",
      loading: "جارٍ التحميل…",
      previous: "السابق",
      next: "التالي",
      zoom: "التكبير",
      page: "الصفحة",
      thumbnails: "الصور المصغرة",
      failed: "تعذر تحميل هذا الملف.",
      empty: "لا يوجد ما يُعرض",
      retry: "إعادة المحاولة",
      rate: "سرعة التشغيل",
      transcript: "النص",
      hideTranscript: "إخفاء النص",
      pip: "صورة داخل صورة",
      exitPip: "الخروج من صورة داخل صورة",
      unsupported: "لا يمكن تشغيل صيغة هذا الملف في هذا المتصفح. نزّله بدلًا من ذلك.",
      pipFailed: "خاصية صورة داخل صورة غير متاحة.",
      seek: "الانتقال",
      fallback: "فتح الوسائط",
      audioFailed: "تعذر تحميل الصوت.",
      volume: "مستوى الصوت",
      mute: "كتم الصوت",
      viewerLabel: "معاينة",
      closePreview: "إغلاق المعاينة",
      counter: "{index} من {total}",
    },
  };

  function translator(lang) {
    const own = words[lang === "ar" ? "ar" : "en"];
    const fallback = base.caseTranslator(lang);
    return (key, vars) => {
      let value = own[key] ?? words.en[key];
      if (value === undefined) return fallback(key, vars);
      if (vars) for (const [k, v] of Object.entries(vars)) value = value.split(`{${k}}`).join(v); // every occurrence
      return value;
    };
  }

  const mediaStrings = (t) =>
    Object.fromEntries(
      ["rate", "transcript", "hideTranscript", "pip", "exitPip", "unsupported", "pipFailed", "seek", "fallback", "audioFailed", "volume", "mute"]
        .map((k) => [k, t(k)])
        .concat([["failed", t("failed")]]),
    );
  const PDF_FAILURES = ["failedEngine", "failedAccess", "failedParse", "failedRender"];
  const pdfStrings = (t) =>
    Object.fromEntries(["previous", "next", "page", "zoom", "thumbnails", "loading", "empty", "retry", ...PDF_FAILURES].map((k) => [k, t(k)]));
  const documentStrings = (t) =>
    Object.fromEntries(["previous", "next", "page", "zoom", "thumbnails", "loading", "failed", "empty", "retry"].map((k) => [k, t(k)]));

  // ---------- Recorder ----------

  function ReportRecorder({ api, lang, storageKey, reportId, caseId, canSubmit, captureOnly, onSubmitted }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const store = R.useMemo(() => recordingStore(), []);
    const [status, setStatus] = R.useState("idle"); // idle | recording | paused | stopped | recovered | submitting | submitted
    const [notice, setNotice] = R.useState(false);
    const [problem, setProblem] = R.useState(null);
    const [message, setMessage] = R.useState(null);
    const [progress, setProgress] = R.useState(null);
    const [blobUrl, setBlobUrl] = R.useState(null);
    const [mimeType, setMimeType] = R.useState("");
    const [persisted, setPersisted] = R.useState(true);
    const [confirm, setConfirm] = R.useState(null);
    const [, tick] = R.useReducer((n) => n + 1, 0);
    const refs = R.useRef({ recorder: null, stream: null, segments: [], chunks: [], wakeLock: null, fileId: null, recordingId: null });

    // Recover chunks left by an interrupted session on this device.
    R.useEffect(() => {
      let live = true;
      (async () => {
        try {
          const meta = await store.getMeta(storageKey);
          const rows = await store.chunks(storageKey);
          if (!live || !rows.length) return;
          refs.current.chunks = rows.map((row) => row.blob);
          refs.current.segments = meta?.segments || [];
          refs.current.fileId = meta?.fileId || null;
          refs.current.recordingId = meta?.recordingId || null;
          setMimeType(meta?.mimeType || rows[0].blob.type || "");
          setNotice(Boolean(meta?.notice));
          buildPlayback(meta?.mimeType || rows[0].blob.type);
          setStatus("recovered");
          setMessage("recovered");
        } catch {
          if (live) setPersisted(false);
        }
      })();
      return () => {
        live = false;
        stopTracks();
      };
    }, [storageKey]);

    // Timer while recording; warn before leaving with an active recording.
    R.useEffect(() => {
      if (status !== "recording" && status !== "paused") return undefined;
      const timer = status === "recording" ? setInterval(tick, 500) : null;
      const guard = (event) => {
        event.preventDefault();
        event.returnValue = t("beforeUnload");
        return t("beforeUnload");
      };
      const flush = () => {
        try {
          if (refs.current.recorder && refs.current.recorder.state === "recording") refs.current.recorder.requestData();
        } catch {
          /* best effort */
        }
      };
      window.addEventListener("beforeunload", guard);
      document.addEventListener("visibilitychange", flush);
      window.addEventListener("pagehide", flush);
      return () => {
        if (timer) clearInterval(timer);
        window.removeEventListener("beforeunload", guard);
        document.removeEventListener("visibilitychange", flush);
        window.removeEventListener("pagehide", flush);
      };
    }, [status]);

    function stopTracks() {
      const r = refs.current;
      if (r.stream) r.stream.getTracks().forEach((track) => track.stop());
      r.stream = null;
      if (r.wakeLock) r.wakeLock.release().catch(() => {});
      r.wakeLock = null;
    }

    function buildPlayback(type) {
      const blob = new Blob(refs.current.chunks, { type: type || mimeType || "audio/webm" });
      setBlobUrl((old) => {
        if (old) URL.revokeObjectURL(old);
        return refs.current.chunks.length ? URL.createObjectURL(blob) : null;
      });
      return blob;
    }

    async function saveMeta(extra = {}) {
      try {
        await store.putMeta({
          key: storageKey,
          mimeType: refs.current.recorder?.mimeType || mimeType,
          notice: true,
          segments: refs.current.segments,
          fileId: refs.current.fileId,
          recordingId: refs.current.recordingId,
          updatedAt: Date.now(),
          ...extra,
        });
      } catch {
        setPersisted(false);
      }
    }

    async function start() {
      setProblem(null);
      setMessage(null);
      if (!notice) {
        setProblem("noticeRequired");
        return;
      }
      const secure = window.isSecureContext !== false;
      const supported = Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
      if (!secure || !supported) {
        setProblem(microphoneProblem(null, { secure, supported }));
        return;
      }
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      } catch (error) {
        setProblem(microphoneProblem(error, {}));
        return;
      }
      const type = chooseMimeType((value) => window.MediaRecorder.isTypeSupported(value));
      let recorder;
      try {
        recorder = new window.MediaRecorder(stream, type ? { mimeType: type } : undefined);
      } catch (error) {
        stream.getTracks().forEach((track) => track.stop());
        setProblem(microphoneProblem(error, {}));
        return;
      }
      const r = refs.current;
      r.stream = stream;
      r.recorder = recorder;
      r.chunks = [];
      r.segments = [{ start: Date.now(), end: null }];
      r.fileId = null;
      r.recordingId = null;
      setMimeType(recorder.mimeType || type);
      recorder.ondataavailable = (event) => {
        if (!event.data || !event.data.size) return;
        r.chunks.push(event.data);
        store.addChunk(storageKey, event.data).catch(() => setPersisted(false));
      };
      recorder.onstop = () => {
        const open = r.segments[r.segments.length - 1];
        if (open && open.end === null) open.end = Date.now();
        stopTracks();
        buildPlayback(recorder.mimeType || type);
        saveMeta();
        setStatus((old) => (old === "interrupted" ? "recovered" : "stopped"));
      };
      // A device change or OS interruption ends the track: keep what was captured.
      stream.getTracks().forEach((track) => {
        track.onended = () => {
          if (recorder.state !== "inactive") {
            setMessage("interrupted");
            setStatus("interrupted");
            try {
              recorder.stop();
            } catch {
              /* already stopped */
            }
          }
        };
      });
      await saveMeta({ startedAt: Date.now() });
      try {
        recorder.start(5000);
      } catch (error) {
        stopTracks();
        setProblem(microphoneProblem(error, {}));
        return;
      }
      if (navigator.wakeLock && navigator.wakeLock.request) {
        navigator.wakeLock
          .request("screen")
          .then((lock) => (r.wakeLock = lock))
          .catch(() => {});
      }
      setStatus("recording");
    }

    function pause() {
      const r = refs.current;
      if (r.recorder && r.recorder.state === "recording") {
        r.recorder.pause();
        r.recorder.requestData();
        r.segments[r.segments.length - 1].end = Date.now();
        saveMeta();
        setStatus("paused");
      }
    }

    function resume() {
      const r = refs.current;
      if (r.recorder && r.recorder.state === "paused") {
        r.recorder.resume();
        r.segments.push({ start: Date.now(), end: null });
        setStatus("recording");
      }
    }

    function stop() {
      const r = refs.current;
      if (r.recorder && r.recorder.state !== "inactive") r.recorder.stop();
    }

    async function discard() {
      stopTracks();
      refs.current = { recorder: null, stream: null, segments: [], chunks: [], wakeLock: null, fileId: null, recordingId: null };
      setBlobUrl((old) => {
        if (old) URL.revokeObjectURL(old);
        return null;
      });
      try {
        await store.clear(storageKey);
      } catch {
        /* nothing stored */
      }
      setConfirm(null);
      setMessage(null);
      setStatus("idle");
    }

    async function waitForScan(fileId) {
      for (let attempt = 0; attempt < 10; attempt++) {
        try {
          const state = await api(`/api/files/${encodeURIComponent(fileId)}/status/`);
          if (state.scan_state === "clean") return "clean";
          if (state.scan_state === "rejected") return "rejected";
        } catch (error) {
          if (error.status === 404 || error.status === 405) return "unknown";
          throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      return "pending";
    }

    async function submit() {
      setConfirm(null);
      setProblem(null);
      setMessage(null);
      const r = refs.current;
      const type = mimeType || r.chunks[0]?.type || "audio/webm";
      const blob = new Blob(r.chunks, { type: type.split(";")[0] });
      if (blob.size > sizeLimitBytes(type)) {
        setProblem("tooLarge");
        return;
      }
      setStatus("submitting");
      try {
        if (!r.fileId) {
          setProgress("uploading");
          const form = new FormData();
          form.append("file", new File([blob], `recording.${extensionFor(type)}`, { type: blob.type }));
          form.append("category", "REC");
          form.append("case_id", caseId);
          form.append("visibility", "council");
          form.append("context", `report:${reportId}`);
          const stored = await api("/api/files/", { method: "POST", body: form });
          r.fileId = stored.id;
          await saveMeta();
          if (stored.scan_state !== "clean") {
            setProgress("scanning");
            const scan = await waitForScan(stored.id);
            if (scan === "rejected") throw { scan: "rejected" };
            if (scan === "pending") throw { scan: "pending" };
          }
        }
        if (!r.recordingId) {
          setProgress("associating");
          const recording = await api("/api/recordings/", {
            method: "POST",
            body: JSON.stringify({
              file_id: r.fileId,
              report_id: reportId,
              notice_recorded: true,
              recording_notice: { acknowledged: true },
              ...(r.segments.length && r.segments.every((x) => x.end) ? { duration_ms: Math.round(elapsedMs(r.segments, Date.now())) } : {}),
            }),
          });
          r.recordingId = recording.id;
          await saveMeta();
        }
        setProgress("queueing");
        await api(`/api/recordings/${encodeURIComponent(r.recordingId)}/finalize/`, { method: "POST", body: "{}" });
        await store.clear(storageKey).catch(() => {});
        setProgress(null);
        setStatus("submitted");
        setMessage("submitted");
        if (onSubmitted) onSubmitted();
      } catch (error) {
        setProgress(null);
        setStatus(r.chunks.length ? "stopped" : "idle");
        if (error && error.scan === "rejected") setProblem("scanRejected");
        else if (error && error.scan === "pending") setMessage("scanning");
        else setProblem(error && (error.data?.detail || error.data?.messages) ? base.serverMessage(error, t) : "uploadFailed");
      }
    }

    const r = refs.current;
    const now = Date.now();
    const length = elapsedMs(r.segments, now);
    const stateLabel = {
      recording: "recordingState",
      paused: "pausedState",
      stopped: "stoppedState",
      recovered: "recoveredState",
      interrupted: "recoveredState",
    }[status];
    const problemText = problem ? (words.en[problem] ? t(problem) : problem) : null;
    return h(
      P.Panel,
      { icon: "doc-text", title: t("recordingTitle"), description: t("recordingHelp") },
      h(
        P.Stack,
        { gap: "md" },
        !persisted ? h(P.Notice, { tone: "warning" }, t("storageUnavailable")) : null,
        captureOnly ? h(P.Notice, { tone: "info" }, t("captureOnly")) : null,
        message ? h(P.Notice, { tone: message === "submitted" ? "success" : message === "interrupted" ? "warning" : "info" }, t(message)) : null,
        problemText ? h(P.Notice, { tone: "danger" }, problemText) : null,
        status === "idle"
          ? h(P.Checkbox, {
              label: t("noticeLabel"),
              checked: notice,
              onChange: (e) => {
                setNotice(e.target.checked);
                setProblem(null);
              },
            })
          : null,
        stateLabel
          ? h(
              P.Inline,
              { gap: "sm", wrap: true },
              h(P.Badge, { tone: status === "recording" ? "negative" : status === "paused" ? "waiting" : "active" }, t(stateLabel)),
              h(P.Text, { variant: "data", "aria-live": "polite" }, `${t("elapsed")}: ${formatDuration(length)}`),
            )
          : null,
        progress ? h(P.Inline, { gap: "sm" }, h(P.Spinner, { size: "sm", label: t(progress) }), h(P.Text, null, t(progress))) : null,
        blobUrl && ["stopped", "recovered", "interrupted"].includes(status)
          ? h(P.MediaPlayer, { key: blobUrl, src: blobUrl, kind: "audio", label: t("playbackLabel"), strings: mediaStrings(t) })
          : null,
        h(
          P.Inline,
          { wrap: true },
          status === "idle" ? h(P.Button, { variant: "primary", onClick: start }, t("start")) : null,
          status === "recording" ? h(P.Button, { onClick: pause }, t("pause")) : null,
          status === "paused" ? h(P.Button, { variant: "primary", onClick: resume }, t("resume")) : null,
          status === "recording" || status === "paused" ? h(P.Button, { variant: "danger-secondary", onClick: stop }, t("stop")) : null,
          ["stopped", "recovered", "interrupted"].includes(status) && canSubmit && !captureOnly
            ? h(P.Button, { variant: "primary", onClick: () => setConfirm("submit") }, t(problem === "uploadFailed" ? "retrySubmit" : "submit"))
            : null,
          message === "scanning" && status === "stopped" && canSubmit ? h(P.Button, { onClick: submit }, t("checkAgain")) : null,
          ["stopped", "recovered", "interrupted"].includes(status) ? h(P.Button, { variant: "danger-secondary", onClick: () => setConfirm("discard") }, t("discard")) : null,
        ),
      ),
      h(P.ConfirmDialog, {
        open: confirm === "submit",
        title: t("submitTitle"),
        message: t("submitMessage"),
        confirmLabel: t("submit"),
        cancelLabel: t("cancel"),
        onConfirm: submit,
        onCancel: () => setConfirm(null),
      }),
      h(P.ConfirmDialog, {
        open: confirm === "discard",
        title: t("discardTitle"),
        message: t("discardMessage"),
        confirmLabel: t("discard"),
        cancelLabel: t("cancel"),
        destructive: true,
        onConfirm: discard,
        onCancel: () => setConfirm(null),
      }),
    );
  }

  // ---------- Report revisions (D19) ----------

  // The server's can_revise flag is the only source of revise authority; no role or name inference.
  function revisionAccess(report) {
    if (!report || !Object.prototype.hasOwnProperty.call(report, "can_revise")) return "unknown";
    return report.can_revise === true ? "allowed" : "denied";
  }

  // Editable text fields: every question of the request plus any other text answer. Files and other
  // structured answers are not editable and are carried into the new version unchanged.
  function revisionFields(report, latest) {
    const answers = (latest && latest.answers) || {};
    const codes = (report.questions || []).map((q) => q.code);
    for (const [code, value] of Object.entries(answers)) if (typeof value === "string" && !codes.includes(code)) codes.push(code);
    return codes.filter((code) => answers[code] === undefined || typeof answers[code] === "string");
  }

  // Answers in the request's question order (PostgreSQL JSON does not keep key order), then any others.
  function answerEntries(report, answers) {
    const order = (report.questions || []).map((q) => q.code);
    const rank = (code) => (order.includes(code) ? order.indexOf(code) : order.length);
    return Object.entries(answers || {}).sort((a, b) => rank(a[0]) - rank(b[0]));
  }

  const revisionDraftKey = (report) => `revision:${report.id}`;

  function revisionDraft(report, latest) {
    const answers = (latest && latest.answers) || {};
    return {
      answers: Object.fromEntries(revisionFields(report, latest).map((code) => [code, answers[code] || ""])),
      observations: (latest && latest.observations) || "",
    };
  }

  function revisionPayload(latest, draft) {
    const answers = { ...((latest && latest.answers) || {}) };
    for (const [code, value] of Object.entries(draft.answers || {})) {
      if (answers[code] !== undefined && typeof answers[code] !== "string") continue;
      if (answers[code] === undefined && !value) continue;
      answers[code] = value;
    }
    return { expected_version: latest?.version, answers, observations: draft.observations || "" };
  }

  function revisionChanged(latest, draft) {
    const before = { answers: (latest && latest.answers) || {}, observations: (latest && latest.observations) || "" };
    const after = revisionPayload(latest, draft);
    const keys = new Set([...Object.keys(before.answers), ...Object.keys(after.answers)]);
    for (const key of keys) if (JSON.stringify(before.answers[key] ?? "") !== JSON.stringify(after.answers[key] ?? "")) return true;
    return before.observations !== after.observations;
  }

  // Classifies a failed save by the backend's published contract (backend #7 tribunal/api.py endpoint()):
  // 409 {error:"version_conflict", current_version} or {error:"conflict", detail}; 403 {detail}; 422 {messages};
  // 401; 404. No status (network failure) or 5xx means the outcome is unknown: the server may have saved it.
  function saveFailure(error) {
    const status = error && error.status;
    if (!status || status >= 500) return "uncertain";
    if (status === 409) return "conflict";
    if (status === 403) return "denied";
    if (status === 401) return "expired";
    if (status === 404) return "missing";
    if (status === 422) return "invalid";
    return "failed";
  }

  // Key-order-independent JSON (PostgreSQL jsonb does not keep key order).
  function stableJson(value) {
    if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
    if (value && typeof value === "object")
      return `{${Object.keys(value)
        .sort()
        .map((k) => `${JSON.stringify(k)}:${stableJson(value[k])}`)
        .join(",")}}`;
    return JSON.stringify(value === undefined ? null : value);
  }

  // The server's replay rule: the stored version right after expected_version holds exactly this content.
  function isSameSave(row, payload) {
    return Boolean(
      row &&
        payload &&
        row.version === payload.expected_version + 1 &&
        stableJson(row.answers || {}) === stableJson(payload.answers || {}) &&
        (row.observations || "") === (payload.observations || ""),
    );
  }

  function ReportRevisionEditor({ api, lang, report, latest, restored, onCancel, onSaved, onHistory, onDenied }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const draftKey = revisionDraftKey(report);
    const [stored] = R.useState(() => base.unsavedDrafts.get(draftKey) || null);
    const [draft, setDraft] = R.useState(() => (stored ? stored.draft : revisionDraft(report, latest)));
    const [base0, setBase0] = R.useState(() => (stored ? stored.base : latest)); // version the edit is based on
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null); // { kind, message }
    const [conflict, setConflict] = R.useState(null); // newest saved version when it is not base0
    const [showLatest, setShowLatest] = R.useState(false);
    const [attempt, setAttempt] = R.useState(null); // exact request whose outcome is unknown
    const [info, setInfo] = R.useState(null); // { key, vars }
    const [confirm, setConfirm] = R.useState(null); // "discard" | "overwrite"
    const [done, setDone] = R.useState(false); // a save was confirmed by the server
    const dirty = revisionChanged(base0, draft) && !done;
    // Keep unsaved text across in-app navigation (the editor unmounts when another page opens).
    R.useEffect(() => {
      if (dirty) base.unsavedDrafts.set(draftKey, { base: base0, draft });
      else base.unsavedDrafts.delete(draftKey);
    }, [draft, base0]);
    R.useEffect(() => {
      if (!dirty) return undefined;
      const guard = (event) => {
        event.preventDefault();
        event.returnValue = t("unsavedRevision");
        return event.returnValue;
      };
      window.addEventListener("beforeunload", guard);
      return () => window.removeEventListener("beforeunload", guard);
    }, [dirty]);
    const url = `/api/reports/${encodeURIComponent(report.id)}/revisions/`;
    const payload = revisionPayload(base0, draft);
    // Unchanged text after an unconfirmed save: resend the identical request; the server replays it.
    const retrying = Boolean(attempt) && stableJson(attempt) === stableJson(payload);
    const blocked = failure && (failure.kind === "denied" || failure.kind === "missing");

    async function readHistory() {
      const data = await api(url);
      const items = data.items || [];
      onHistory(items);
      return items;
    }
    function finish(version) {
      setDone(true);
      base.unsavedDrafts.delete(draftKey);
      setAttempt(null);
      onSaved(version);
    }
    // After a 409, learn what the server holds. Our own identical earlier save is a confirmation, not a conflict.
    async function settleConflict(sent) {
      const newest = (await readHistory())[0] || null;
      if (isSameSave(newest, sent)) return finish(newest.version);
      if (attempt && isSameSave(newest, attempt)) {
        setAttempt(null);
        setBase0(newest);
        setInfo({ key: "previousSaveReceived", vars: { version: String(newest.version) } });
        return undefined;
      }
      setConflict(newest);
      setShowLatest(false);
      return undefined;
    }
    async function submit(body) {
      setPending(true);
      setFailure(null);
      setInfo(null);
      try {
        const saved = await api(url, { method: "POST", body: JSON.stringify(body) });
        // The contract returns {id, version} for a new save and for a replay; older servers may omit version.
        const version = saved && saved.version != null ? saved.version : ((await readHistory().catch(() => []))[0] || {}).version;
        finish(version ?? null);
      } catch (error) {
        const kind = saveFailure(error);
        if (kind === "conflict") {
          try {
            await settleConflict(body);
          } catch {
            setAttempt(body);
            setFailure({ kind: "uncertain", message: "" });
          }
          return;
        }
        if (kind === "uncertain") setAttempt(body);
        if (kind === "denied" && onDenied) onDenied(); // refresh rows so can_revise reflects withdrawn authority
        setFailure({ kind, message: base.serverMessage(error, t) });
      } finally {
        setPending(false);
      }
    }
    async function save(event) {
      if (event && event.preventDefault) event.preventDefault();
      setFailure(null);
      setInfo(null);
      if (retrying) return submit(attempt);
      if (!dirty) return setInfo({ key: "revisionNoChange" });
      setPending(true);
      try {
        // Early, friendly check; the server's expected_version check remains the authority.
        const newest = (await readHistory())[0] || null;
        if (attempt && isSameSave(newest, attempt)) {
          setAttempt(null);
          setBase0(newest);
          setInfo({ key: "previousSaveReceived", vars: { version: String(newest.version) } });
          return undefined;
        }
        if (newest && base0 && newest.version !== base0.version) {
          setConflict(newest);
          setShowLatest(false);
          return undefined;
        }
      } catch {
        /* history unreadable: still safe to send, a stale version is refused with 409 */
      } finally {
        setPending(false);
      }
      return submit(payload);
    }
    // Deliberate choice after reviewing the newer version: the text becomes the next version.
    function overwrite() {
      const next = conflict;
      setConfirm(null);
      setConflict(null);
      setBase0(next);
      if (!revisionChanged(next, draft)) return setInfo({ key: "revisionNoChange" });
      return submit(revisionPayload(next, draft));
    }
    function discard() {
      base.unsavedDrafts.delete(draftKey);
      setConfirm(null);
      onCancel();
    }
    const questions = report.questions || [];
    const label = (code) => {
      const q = questions.find((x) => x.code === code);
      return q ? `${code} — ${base.isolate((lang === "ar" && q.ar) || q.en || code)}` : code;
    };
    const kept = Object.entries((base0 && base0.answers) || {}).some(([, v]) => typeof v !== "string");
    const failureText = failure
      ? {
          uncertain: t("saveUncertain"),
          denied: `${failure.message} ${t("revisionDenied")}`,
          invalid: `${failure.message} ${t("revisionFixAndSave")}`,
          expired: t("sessionExpiredKept"),
          missing: `${failure.message} ${t("reportMissing")}`,
          failed: `${failure.message} ${t("revisionKept")}`,
        }[failure.kind]
      : null;
    const conflictVars = conflict
      ? { version: String(conflict.version), next: String(conflict.version + 1), actor: conflict.actor ? base.isolate(conflict.actor) : "—" }
      : null;
    return h(
      P.Form,
      { onSubmit: save, label: t("reviseTitle"), noValidate: true },
      restored && stored ? h(P.Notice, { tone: "info" }, t("revisionRestored")) : null,
      h(
        P.FormSection,
        { title: t("reviseTitle"), description: t("reviseHelp") },
        ...revisionFields(report, base0).map((code) =>
          h(
            P.Field,
            { key: code, label: label(code) },
            h(P.Textarea, {
              dir: "auto",
              rows: 3,
              autoGrow: true,
              value: draft.answers[code] || "",
              maxLength: 50000,
              disabled: pending,
              onChange: (e) => {
                const value = e.target.value;
                setDraft((old) => ({ ...old, answers: { ...old.answers, [code]: value } }));
                setInfo(null);
              },
            }),
          ),
        ),
        h(
          P.Field,
          { label: t("observations") },
          h(P.Textarea, {
            dir: "auto",
            rows: 4,
            autoGrow: true,
            value: draft.observations,
            maxLength: 50000,
            disabled: pending,
            onChange: (e) => {
              const value = e.target.value;
              setDraft((old) => ({ ...old, observations: value }));
              setInfo(null);
            },
          }),
        ),
        kept ? h(P.Text, { variant: "secondary" }, t("nonTextKept")) : null,
      ),
      conflict
        ? h(
            P.Notice,
            { tone: "warning" },
            h(
              P.Stack,
              { gap: "sm" },
              h(P.Text, { as: "p" }, t("revisionConflict", conflictVars)),
              h(
                P.Inline,
                { wrap: true },
                h(P.Button, { size: "sm", disabled: pending, onClick: () => setShowLatest(!showLatest) }, t(showLatest ? "hideVersion" : "showVersion", conflictVars)),
                h(P.Button, { size: "sm", disabled: pending, onClick: () => setConfirm("overwrite") }, t("saveAnyway")),
                h(P.Button, { size: "sm", disabled: pending, onClick: () => setConfirm("discard") }, t("discardChanges")),
              ),
            ),
          )
        : null,
      conflict && showLatest
        ? h(
            P.Panel,
            {
              icon: "document",
              title: t("latestVersionTitle", { ...conflictVars, when: conflict.timestamp ? base.formatWhen(conflict.timestamp, lang) : "—" }),
            },
            h(
              P.Stack,
              { gap: "sm" },
              ...answerEntries(report, conflict.answers).map(([code, answer]) =>
                h(
                  P.Stack,
                  { key: code, gap: "xs" },
                  h(P.Text, { variant: "secondary" }, label(code)),
                  h(P.Text, { as: "p", dir: "auto" }, typeof answer === "string" ? answer : JSON.stringify(answer)),
                ),
              ),
              conflict.observations
                ? h(P.Stack, { gap: "xs" }, h(P.Text, { variant: "secondary" }, t("observations")), h(P.Text, { as: "p", dir: "auto" }, conflict.observations))
                : null,
            ),
          )
        : null,
      info ? h(P.Notice, { tone: "info" }, t(info.key, info.vars)) : null,
      failureText ? h(P.Notice, { tone: failure.kind === "uncertain" ? "warning" : "danger" }, failureText) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { disabled: pending, onClick: () => (dirty || attempt ? setConfirm("discard") : discard()) }, t("cancel")),
        blocked || conflict
          ? null
          : h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t(retrying ? "retrySave" : "saveRevision")),
      ),
      h(P.ConfirmDialog, {
        open: confirm === "discard",
        title: t("discardRevisionTitle"),
        message: t(attempt ? "discardUncertainMessage" : "discardRevisionMessage"),
        confirmLabel: t("discardChanges"),
        cancelLabel: t("keepEditing"),
        destructive: true,
        onConfirm: discard,
        onCancel: () => setConfirm(null),
      }),
      h(P.ConfirmDialog, {
        open: confirm === "overwrite",
        title: t("overwriteTitle", conflictVars || {}),
        message: t("overwriteMessage", conflictVars || {}),
        confirmLabel: t("overwriteConfirm", conflictVars || {}),
        cancelLabel: t("keepEditing"),
        onConfirm: overwrite,
        onCancel: () => setConfirm(null),
      }),
    );
  }

  // ---------- Recording status and transcripts (D20) ----------
  // Contract: backend #7 docs/implementation/media-read-and-review.md and twenty-batch-continuation.md.
  // GET /api/reports/{id}/recordings/ · GET /api/transcripts/{id}/ · POST .../review/ {} ·
  // POST .../correct/ {expected_version,text,segments} · POST /api/processing/{run}/retry/ {} ·
  // POST /api/recordings/{id}/finalize/. No provider success is ever inferred: "queued" means waiting.

  function processingView(recording) {
    const p = recording.processing;
    const attempt = String((p && p.attempt) || 1);
    if (!recording.download_url) return { key: "originalUnavailable", tone: "danger" };
    if (!recording.finalized_at)
      return recording.can_finalize ? { key: "statusNotQueued", tone: "info", finalize: true } : { key: "statusNotQueuedNoAuthority", tone: "info" };
    if (!p) return { key: "statusMissing", tone: "warning" };
    if (p.state === "queued") return { key: "statusQueued", tone: "info", attempt };
    if (p.state === "running") return { key: "statusRunning", tone: "info", attempt };
    if (p.state === "succeeded") return { key: "statusSucceeded", tone: "success", attempt };
    if (p.state === "failed") return { key: p.can_retry ? "statusFailed" : "statusFailedNoRetry", tone: "danger", attempt, retry: Boolean(p.can_retry) };
    return { key: "statusOther", tone: "info", attempt, state: String(p.state) };
  }

  // Versions grouped by language and kind, newest version first in each group.
  function transcriptGroups(transcripts) {
    const groups = new Map();
    for (const row of transcripts || []) {
      const key = `${row.language}|${row.kind}`;
      if (!groups.has(key)) groups.set(key, { key, language: row.language, kind: row.kind, versions: [] });
      groups.get(key).versions.push(row);
    }
    return [...groups.values()]
      .map((g) => ({ ...g, versions: g.versions.sort((a, b) => b.version - a.version) }))
      .sort((a, b) => (a.language + a.kind).localeCompare(b.language + b.kind));
  }

  // Only well-formed timed segments are shown; anything else is left to the text.
  function timedSegments(segments) {
    if (!Array.isArray(segments)) return [];
    return segments.filter(
      (s) => s && typeof s.text === "string" && s.text.trim() && Number.isFinite(s.start) && Number.isFinite(s.end) && s.end >= s.start,
    );
  }

  const codeLabel = (t, prefix, value) => {
    const label = t(`${prefix}_${value}`);
    return label === `${prefix}_${value}` || !label ? String(value || "—") : label;
  };

  function RecordingStatusList({ api, lang, report, refreshKey }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/reports/${encodeURIComponent(report.id)}/recordings/`), [report.id, refreshKey]);
    const [busy, setBusy] = R.useState(null);
    const [notes, setNotes] = R.useState({}); // recording id -> { tone, text }
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const items = (state.data && state.data.items) || [];
    async function act(recording, kind) {
      setBusy(recording.id);
      try {
        if (kind === "retry") {
          const run = await api(`/api/processing/${encodeURIComponent(recording.processing.run_id)}/retry/`, { method: "POST", body: "{}" });
          setNotes((n) => ({ ...n, [recording.id]: { tone: "success", text: t("retryDone", { attempt: String(run.attempt) }) } }));
        } else {
          await api(`/api/recordings/${encodeURIComponent(recording.id)}/finalize/`, { method: "POST", body: "{}" });
          setNotes((n) => ({ ...n, [recording.id]: { tone: "success", text: t("queuedDone") } }));
        }
        retry();
      } catch (error) {
        setNotes((n) => ({ ...n, [recording.id]: { tone: "danger", text: base.serverMessage(error, t) } }));
      } finally {
        setBusy(null);
      }
    }
    return h(
      P.Stack,
      { gap: "md" },
      h(P.Text, { as: "h3", variant: "heading" }, t("recordingsTitle")),
      items.length
        ? h(
            P.Stack,
            { gap: "md" },
            ...items.map((recording, i) => {
              const view = processingView(recording);
              const note = notes[recording.id];
              return h(
                P.Panel,
                { key: recording.id, icon: "triangle-right", title: t("recordingItem", { n: String(i + 1) }) },
                h(
                  P.Stack,
                  { gap: "sm" },
                  h(
                    P.PropertyList,
                    null,
                    h(P.PropertyList.Item, { label: t("submittedOn"), data: true }, base.formatWhen(recording.created_at, lang)),
                    h(P.PropertyList.Item, { label: t("recDuration"), data: true }, recording.duration_ms != null ? formatDuration(recording.duration_ms) : t("durationUnknown")),
                    recording.byte_count ? h(P.PropertyList.Item, { label: t("size"), data: true }, formatBytes(recording.byte_count, lang)) : null,
                    h(P.PropertyList.Item, { label: t("noticeState") }, t(recording.notice_recorded ? "noticeGiven" : "noticeMissing")),
                  ),
                  recording.download_url
                    ? h(P.MediaPlayer, { src: recording.download_url, kind: "audio", label: t("recordingItem", { n: String(i + 1) }), strings: mediaStrings(t) })
                    : null,
                  h(P.Notice, { tone: view.tone }, t(view.key, { attempt: view.attempt || "1", error: (recording.processing && recording.processing.safe_error) || "", state: view.state || "" })),
                  note ? h(P.Notice, { tone: note.tone }, note.text) : null,
                  view.finalize || view.retry
                    ? h(
                        P.Inline,
                        { wrap: true },
                        h(
                          P.Button,
                          { size: "sm", variant: "primary", loading: busy === recording.id, disabled: Boolean(busy), onClick: () => act(recording, view.retry ? "retry" : "finalize") },
                          t(view.retry ? "retryTranscription" : "queueTranscription"),
                        ),
                      )
                    : null,
                ),
              );
            }),
          )
        : h(P.EmptyState, { title: t("noRecordings") }),
    );
  }

  function TranscriptCorrection({ api, lang, data, draftKey, onSaved, onCancel, onStale }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [stored] = R.useState(() => base.unsavedDrafts.get(draftKey) || null);
    const [text, setText] = R.useState(() => (stored ? stored.text : data.text || ""));
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [stale, setStale] = R.useState(false);
    const [confirm, setConfirm] = R.useState(false);
    const [done, setDone] = R.useState(false);
    const dirty = !done && text !== (data.text || "");
    R.useEffect(() => {
      if (dirty) base.unsavedDrafts.set(draftKey, { version: data.version, text });
      else base.unsavedDrafts.delete(draftKey);
      if (!dirty) return undefined;
      const guard = (event) => {
        event.preventDefault();
        event.returnValue = t("unsavedCorrection");
        return event.returnValue;
      };
      window.addEventListener("beforeunload", guard);
      return () => window.removeEventListener("beforeunload", guard);
    }, [text]);
    const next = String(data.version + 1);
    async function save(event) {
      if (event && event.preventDefault) event.preventDefault();
      setFailure(null);
      if (!text.trim()) return setFailure(t("correctionEmpty"));
      if (!dirty) return setFailure(t("revisionNoChange"));
      setPending(true);
      try {
        // Corrected text does not carry the generated timings (they would no longer match the words).
        const row = await api(`/api/transcripts/${encodeURIComponent(data.id)}/correct/`, {
          method: "POST",
          body: JSON.stringify({ expected_version: data.version, text, segments: [] }),
        });
        setDone(true);
        base.unsavedDrafts.delete(draftKey);
        onSaved(row);
      } catch (error) {
        const kind = saveFailure(error);
        if (kind === "invalid" && /newer transcript version/i.test(base.serverMessage(error, t))) setStale(true);
        else setFailure(kind === "uncertain" ? t("correctionUncertain") : `${base.serverMessage(error, t)} ${t("revisionKept")}`);
      } finally {
        setPending(false);
      }
    }
    function discard() {
      base.unsavedDrafts.delete(draftKey);
      setConfirm(false);
      onCancel();
    }
    return h(
      P.Form,
      { onSubmit: save, label: t("correctTitle"), noValidate: true },
      stored ? h(P.Notice, { tone: "info" }, t("correctionRestored")) : null,
      h(
        P.FormSection,
        { title: t("correctTitle"), description: t("correctHelp", { next }) },
        h(P.Field, { label: t("transcriptText") }, h(P.Textarea, { dir: "auto", rows: 10, autoGrow: true, value: text, maxLength: 5000000, disabled: pending, onChange: (e) => setText(e.target.value) })),
      ),
      stale
        ? h(
            P.Notice,
            { tone: "warning" },
            h(P.Stack, { gap: "sm" }, h(P.Text, { as: "p" }, t("correctionStale")), h(P.Inline, { wrap: true }, h(P.Button, { size: "sm", onClick: onStale }, t("reloadLatest")))),
          )
        : null,
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { disabled: pending, onClick: () => (dirty ? setConfirm(true) : discard()) }, t("cancel")),
        stale ? null : h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveCorrection", { next })),
      ),
      h(P.ConfirmDialog, {
        open: confirm,
        title: t("discardCorrectionTitle"),
        message: t("discardCorrectionMessage"),
        confirmLabel: t("discardChanges"),
        cancelLabel: t("keepEditing"),
        destructive: true,
        onConfirm: discard,
        onCancel: () => setConfirm(false),
      }),
    );
  }

  function TranscriptViewer({ api, lang, revisionId, latestVersion, initialNote, onChanged }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/transcripts/${encodeURIComponent(revisionId)}/`), [revisionId]);
    const data = state.data;
    const draftKey = data ? `transcript:${data.recording_id}:${data.language}:${data.kind}` : null;
    const [editing, setEditing] = R.useState(null);
    const [confirm, setConfirm] = R.useState(false);
    const [busy, setBusy] = R.useState(false);
    const [note, setNote] = R.useState(initialNote || null); // a message carried over from the version that was replaced
    if (state.pending && !data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const isEditing = editing === revisionId || (draftKey && base.unsavedDrafts.has(draftKey) && editing !== false);
    async function review() {
      setConfirm(false);
      setBusy(true);
      setNote(null);
      try {
        await api(`/api/transcripts/${encodeURIComponent(data.id)}/review/`, { method: "POST", body: "{}" });
        setNote({ tone: "success", text: t("reviewDone", { version: String(data.version) }) });
        retry();
        if (onChanged) onChanged(null);
      } catch (error) {
        setNote({ tone: "danger", text: base.serverMessage(error, t) });
      } finally {
        setBusy(false);
      }
    }
    const segments = timedSegments(data.segments);
    const meta = h(
      P.PropertyList,
      null,
      h(P.PropertyList.Item, { label: t("transcriptLanguage") }, codeLabel(t, "lang", data.language)),
      h(P.PropertyList.Item, { label: t("transcriptKind") }, codeLabel(t, "kind", data.kind)),
      h(P.PropertyList.Item, { label: t("version") }, String(data.version)),
      h(P.PropertyList.Item, { label: t("transcriptState") }, h(P.Badge, { tone: data.reviewed ? "success" : "warning" }, t(data.reviewed ? "stateReviewed" : "stateUnreviewed"))),
      data.timestamp ? h(P.PropertyList.Item, { label: t("transcriptSaved"), data: true }, base.formatWhen(data.timestamp, lang)) : null,
    );
    if (isEditing)
      return h(
        P.Stack,
        { gap: "md" },
        meta,
        h(TranscriptCorrection, {
          api,
          lang,
          data,
          draftKey,
          onCancel: () => setEditing(false),
          onStale: () => {
            base.unsavedDrafts.delete(draftKey);
            setEditing(false);
            if (onChanged) onChanged(null);
          },
          onSaved: (row) => {
            setEditing(false);
            const saved = { tone: "success", text: t("correctionSaved", { version: String(row.version) }) };
            setNote(saved);
            if (onChanged) onChanged(row.id, saved);
          },
        }),
      );
    const latest = latestVersion == null || data.version === latestVersion;
    return h(
      P.Stack,
      { gap: "md" },
      meta,
      !data.reviewed ? h(P.Notice, { tone: "warning" }, t("unreviewedNotice")) : null,
      !latest ? h(P.Notice, { tone: "info" }, t("olderVersionNotice", { version: String(latestVersion) })) : null,
      note ? h(P.Notice, { tone: note.tone }, note.text) : null,
      h(P.Panel, { icon: "document", title: t("transcriptText") }, ...String(data.text || "").split(/\n{2,}/).map((para, i) => h(P.Text, { key: i, as: "p", dir: "auto" }, para))),
      segments.length
        ? h(
            P.Panel,
            { icon: "clock", title: t("segmentsTitle") },
            h(
              P.Stack,
              { gap: "xs" },
              ...segments.map((s, i) =>
                h(P.Text, { key: i, as: "p", dir: "auto" }, `${base.isolate(`${formatDuration(s.start * 1000)}–${formatDuration(s.end * 1000)}`)} ${s.text}`),
              ),
            ),
          )
        : null,
      data.can_review && latest
        ? h(
            P.Inline,
            { wrap: true },
            !data.reviewed ? h(P.Button, { variant: "primary", loading: busy, disabled: busy, onClick: () => setConfirm(true) }, t("markReviewed")) : null,
            h(P.Button, { disabled: busy, onClick: () => setEditing(revisionId) }, t("correctText")),
          )
        : null,
      h(P.ConfirmDialog, {
        open: confirm,
        title: t("reviewTitle", { version: String(data.version) }),
        message: t("reviewMessage"),
        confirmLabel: t("markReviewed"),
        cancelLabel: t("cancel"),
        onConfirm: review,
        onCancel: () => setConfirm(false),
      }),
    );
  }

  function TranscriptsPanel({ api, lang, report, refreshKey }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [bump, setBump] = R.useState(0);
    const [state, retry] = base.useLoad(() => api(`/api/reports/${encodeURIComponent(report.id)}/recordings/`), [report.id, refreshKey, bump]);
    const [chosen, setChosen] = R.useState({}); // group key -> revision id
    const [flash, setFlash] = R.useState({}); // group key -> message shown once on the newly selected version
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const items = (state.data && state.data.items) || [];
    if (!items.length) return h(P.EmptyState, { title: t("noRecordings") });
    return h(
      P.Stack,
      { gap: "lg" },
      ...items.map((recording, i) => {
        const groups = transcriptGroups(recording.transcripts);
        const view = processingView(recording);
        return h(
          P.Stack,
          { key: recording.id, gap: "md" },
          h(P.Text, { as: "h3", variant: "heading" }, t("recordingItem", { n: String(i + 1) })),
          groups.length
            ? h(
                P.Stack,
                { gap: "md" },
                ...groups.map((group) => {
                  const key = `${recording.id}|${group.key}`;
                  const selected = chosen[key] && group.versions.some((v) => v.id === chosen[key]) ? chosen[key] : group.versions[0].id;
                  return h(
                    P.Panel,
                    { key, icon: "document", title: `${codeLabel(t, "lang", group.language)} · ${codeLabel(t, "kind", group.kind)}` },
                    h(
                      P.Stack,
                      { gap: "md" },
                      h(
                        P.Field,
                        { label: t("history") },
                        h(P.Select, {
                          value: selected,
                          onChange: (e) => {
                            setFlash((x) => ({ ...x, [key]: null }));
                            setChosen((c) => ({ ...c, [key]: e.target.value }));
                          },
                          options: group.versions.map((v) => ({
                            value: v.id,
                            label: t("versionOption", { version: String(v.version), when: base.formatWhen(v.timestamp, lang), state: t(v.reviewed ? "stateReviewed" : "stateUnreviewed") }),
                          })),
                        }),
                      ),
                      h(TranscriptViewer, {
                        key: selected,
                        api,
                        lang,
                        revisionId: selected,
                        latestVersion: group.versions[0].version,
                        initialNote: flash[key] || null,
                        onChanged: (newId, message) => {
                          if (newId) setChosen((c) => ({ ...c, [key]: newId }));
                          if (message) setFlash((x) => ({ ...x, [key]: message }));
                          setBump((b) => b + 1);
                        },
                      }),
                    ),
                  );
                }),
              )
            : h(P.Notice, { tone: view.key === "statusSucceeded" ? "info" : view.tone }, view.key === "statusSucceeded" ? t("noTranscriptReleased") : t(view.key, { attempt: view.attempt || "1", error: (recording.processing && recording.processing.safe_error) || "", state: view.state || "" })),
        );
      }),
    );
  }

  // ---------- Completed reports reader ----------

  function ReportDetailTabs({ api, lang, user, report, record, onOriginal, onRevised }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [tab, setTab] = R.useState("answers");
    const [history, setHistory] = R.useState(null);
    const [version, setVersion] = R.useState(null);
    const [failure, setFailure] = R.useState(null);
    // Unsaved text left by in-app navigation reopens the editor where the author stopped.
    const [restored] = R.useState(() => base.unsavedDrafts.get(revisionDraftKey(report)) || null);
    const [editing, setEditing] = R.useState(() => (restored ? restored.base : null)); // version the edit started from
    const [opening, setOpening] = R.useState(false);
    const [saved, setSaved] = R.useState(null);
    const [submittedCount, setSubmittedCount] = R.useState(0); // reloads recording status after a submission
    const historyUrl = `/api/reports/${encodeURIComponent(report.id)}/revisions/`;
    function showHistory(items) {
      setHistory(items);
      setVersion(items[0]?.version ?? null);
    }
    async function loadHistory() {
      setFailure(null);
      try {
        const data = await api(historyUrl);
        showHistory(data.items || []);
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      }
    }
    async function startRevision() {
      setFailure(null);
      setSaved(null);
      setOpening(true);
      try {
        // Always edit from the newest stored version, never from a possibly stale list row.
        const data = await api(historyUrl);
        const items = data.items || [];
        showHistory(items);
        setEditing(items[0] || { version: report.version, answers: report.answers, observations: report.observations });
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setOpening(false);
      }
    }
    const shown = history?.find((row) => row.version === version) || report;
    const proceeding = base.openProceeding(record);
    const writer = base.writerFor(user, null, record) && Boolean(proceeding);
    const access = revisionAccess(report);
    const latestShown = !history || version === history[0]?.version;
    const methodLabel = report.method ? t(`method_${report.method}`) : null;
    const paper = report.method === "paper";
    const recorded = report.method === "recording"; // council-recorded priest response (backend fcf03a2)
    const councilSource = paper || recorded;
    const answers = editing
      ? h(ReportRevisionEditor, {
          api,
          lang,
          report,
          latest: editing,
          restored: Boolean(restored),
          onCancel: () => setEditing(null),
          onHistory: showHistory,
          onDenied: onRevised,
          onSaved: (newVersion) => {
            setEditing(null);
            setSaved(newVersion);
            if (onRevised) onRevised();
          },
        })
      : h(
      P.Stack,
      { gap: "md" },
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: t("reportFor") }, report.subject || ""),
        h(P.PropertyList.Item, { label: t("version") }, String(shown.version ?? report.version ?? "")),
        report.author ? h(P.PropertyList.Item, { label: t(councilSource ? "paperRecordedBy" : "reportAuthor") }, base.isolate(report.author)) : null,
        councilSource && report.date ? h(P.PropertyList.Item, { label: t(paper ? "paperReceivedOn" : "recordedOn"), data: true }, report.date) : null,
        report.submitted_at ? h(P.PropertyList.Item, { label: t("reportSubmitted"), data: true }, base.formatWhen(report.submitted_at, lang)) : null,
        methodLabel ? h(P.PropertyList.Item, { label: t("reportMethod") }, methodLabel.startsWith("method_") ? report.method : methodLabel) : null,
      ),
      saved !== null && saved !== undefined ? h(P.Notice, { tone: "success" }, t("revisionSaved", { version: String(saved) })) : null,
      report.parent_report_id ? h(P.Inline, null, h(P.Button, { size: "sm", onClick: onOriginal }, t("openOriginal"))) : null,
      access === "allowed" && latestShown
        ? h(P.Inline, null, h(P.Button, { size: "sm", variant: "primary", loading: opening, disabled: opening, onClick: startRevision }, t("revise")))
        : null,
      history
        ? h(
            P.Field,
            { label: t("history") },
            h(P.Select, {
              value: String(version),
              onChange: (e) => setVersion(Number(e.target.value)),
              options: history.map((row) => ({
                value: String(row.version),
                label: `${t("version")} ${row.version} · ${base.formatWhen(row.timestamp, lang)}${row.actor ? " · " + row.actor : ""}`,
              })),
            }),
          )
        : h(P.Inline, null, h(P.Button, { size: "sm", onClick: loadHistory }, t("loadHistory"))),
      failure ? h(P.Notice, { tone: "danger" }, failure) : null,
      ...answerEntries(report, shown.answers).map(([code, answer]) => {
        if (paper && code === "files" && Array.isArray(answer))
          return h(
            P.Panel,
            { icon: "document", key: code, title: t("paperOriginal") },
            h(P.Stack, { gap: "md" }, h(P.Text, { variant: "secondary" }, t("paperOriginalHelp")), ...answer.map((id) => paperOriginal(String(id), report, lang))),
          );
        if (recorded && code === "files" && Array.isArray(answer))
          return h(
            P.Panel,
            { icon: "document", key: code, title: t("recordedOriginal") },
            h(P.Stack, { gap: "md" }, h(P.Text, { variant: "secondary" }, t("recordedOriginalHelp")), ...answer.map((id) => recordedOriginal(String(id), report, lang))),
          );
        const question = (report.questions || []).find((q) => q.code === code);
        const label = question ? `${code} — ${base.isolate((lang === "ar" && question.ar) || question.en || code)}` : code === "files" ? t("response") : code === "testimony" ? t("priestTestimony") : code;
        return h(P.Panel, { icon: "document", key: code, title: label }, h(P.Text, { as: "p", dir: "auto" }, typeof answer === "string" ? answer : JSON.stringify(answer)));
      }),
      shown.observations ? h(P.Panel, { icon: "document", title: t("observations") }, h(P.Text, { as: "p", dir: "auto" }, shown.observations)) : null,
      access === "unknown" ? h(P.Text, { variant: "secondary" }, t("revisionPending")) : null,
      access === "denied" ? h(P.Text, { variant: "secondary" }, t(paper ? "paperNotRevisable" : recorded ? "recordedNotRevisable" : "revisionNotAllowed")) : null,
    );
    const interview = report.kind === "interview";
    const hasMedia = interview || recorded;
    const recording = recorded
      ? h(RecordingStatusList, { api, lang, report, refreshKey: submittedCount })
      : interview
      ? h(
          P.Stack,
          { gap: "lg" },
          h(RecordingStatusList, { api, lang, report, refreshKey: submittedCount }),
          h(ReportRecorder, {
            key: report.id,
            api,
            lang,
            storageKey: `report:${report.id}`,
            reportId: report.id,
            caseId: record.id,
            canSubmit: writer,
            onSubmitted: () => setSubmittedCount((n) => n + 1),
          }),
        )
      : h(P.EmptyState, { title: t("notInterview") });
    return h(P.Tabs, {
      variant: "contained",
      label: report.title,
      value: tab,
      onChange: setTab,
      items: [
        { value: "answers", label: t("answersTab"), content: answers },
        { value: "recording", label: t("recordingTab"), content: interview && !writer ? h(P.Stack, { gap: "md" }, h(P.Notice, { tone: "info" }, t("writerOnlyRecording")), recording) : recording },
        { value: "transcripts", label: t("transcriptsTab"), content: hasMedia ? h(TranscriptsPanel, { api, lang, report, refreshKey: submittedCount }) : h(P.EmptyState, { title: t("notInterview") }) },
      ],
    });
  }

  function ReportsReader({ api, lang, user, caseId, reports, refreshKey }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(() => api(`/api/cases/${encodeURIComponent(caseId)}/`).then((r) => base.withAssignee(api, r)), [caseId]);
    const [selected, select] = R.useState(null);
    const [fresh, setFresh] = R.useState(null); // reloaded after a revision so rows carry the new version
    const rows = base.ordinaryReports(fresh || reports);
    function reloadReports() {
      api(`/api/cases/${encodeURIComponent(caseId)}/reports/`)
        .then((data) => setFresh(data.items || []))
        .catch(() => {});
    }
    R.useEffect(() => {
      if (refreshKey) reloadReports();
    }, [refreshKey]);
    const chosen = rows.find((row) => row.id === selected);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    return h(P.SplitView, {
      label: t("reportsList"),
      firstLabel: t("reportsList"),
      first: h(window.CTMShell.Table, {
        label: t("reportsList"), rows, selected, onSelect: select, empty: t("noReports"),
        columns: [
          { title: t("completedBy"), field: "completed_by", type: "person", render: row => row.completed_by || row.author || "—" },
          { title: t("completedDate"), field: "date", type: "date" },
          { title: t("intakeBy"), field: "intake_by", type: "person", render: row => row.intake_by || "—" },
        ],
      }),
      second: h(
        P.ReadingPane,
        { label: chosen ? chosen.title : t("chooseReport"), empty: h(P.EmptyState, { title: t("chooseReport") }) },
        chosen
          ? h(ReportDetailTabs, {
              key: chosen.id,
              api,
              lang,
              user,
              report: chosen,
              record: state.data,
              onOriginal: () => select(chosen.parent_report_id),
              onRevised: reloadReports,
            })
          : null,
      ),
    });
  }

  // ---------- Evidence and documents ----------

  // Embedded PDF (Plenix 0.61.0 DocumentViewer; PDF.js from the CDN vendor folder via vendorBase()). The document is
  // fetched from the protected /api/files/{id}/?view=1 route with the session; the server sends private, no-store.
  // Nothing is written to browser storage. A page already drawn stays on screen until the viewer closes: withdrawing
  // access stops later loads, it cannot erase what was already shown or downloaded.
  // A paper report's answers carry only the retained original's file id (backend 746e5a4): view it inline through the
  // protected file route and offer the authorized download. Nothing is cached in browser storage.
  function paperOriginal(id, report, lang) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const url = `/api/files/${encodeURIComponent(id)}/`;
    const file = { id, name: t("paperOriginalName", { title: report.title || "" }) };
    return h(
      P.Stack,
      { gap: "sm", key: id },
      h(PdfPreview, { key: id, file, lang, inline: `${url}?view=1` }),
      h(P.Inline, null, h(P.Button, { size: "sm", href: url }, t("download"))),
    );
  }

  // A council-recorded priest response keeps only the recording's file id in its answers: play it through the
  // authorized file route (byte ranges) and offer the download. No transcript is implied.
  function recordedOriginal(id, report, lang) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const url = `/api/files/${encodeURIComponent(id)}/`;
    return h(
      P.Stack,
      { gap: "sm", key: id },
      h(P.MediaPlayer, { key: id, src: url, kind: "audio", label: t("recordedOriginalName", { title: report.title || "" }), strings: mediaStrings(t) }),
      h(P.Inline, null, h(P.Button, { size: "sm", href: url }, t("download"))),
    );
  }

  function PdfPreview({ file, lang, inline }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [reason, setReason] = R.useState(null);
    const override = window.CTM_PDF_VIEWER || null; // optional { moduleUrl, workerUrl } when served separately
    // Phones start at 50% so a typical page fits its frame (documented initialZoom steps: 50…200).
    const narrow = typeof window.matchMedia === "function" && window.matchMedia("(max-width: 600px)").matches;
    return h(
      P.Stack,
      { gap: "sm" },
      h(P.DocumentViewer, {
        key: file.id,
        kind: "pdf",
        src: inline,
        label: file.name,
        initialZoom: narrow ? 50 : 100,
        strings: pdfStrings(t),
        onError: (e) => setReason((e && e.reason) || "engine"),
        ...(override && override.moduleUrl ? { pdfModuleUrl: override.moduleUrl, pdfWorkerUrl: override.workerUrl } : {}),
      }),
      reason && reason !== "access" ? h(P.Text, { variant: "secondary" }, t("pdfFallbackHint")) : null,
      reason === "access" ? h(P.Text, { variant: "secondary" }, t("pdfAccessHint")) : null,
      h(P.Inline, { wrap: true }, h(P.Button, { size: "sm", href: inline, target: "_blank", rel: "noopener noreferrer" }, t("openPdf"))),
    );
  }

  function FilePreview({ file, lang, images, onFullScreen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const kind = viewerKind(file);
    const urls = fileUrls(file);
    let viewer;
    if (kind === "image" && urls.inline)
      viewer = h(
        P.Stack,
        { gap: "sm" },
        h(P.DocumentViewer, {
          key: file.id,
          kind: "images",
          pages: [{ id: file.id, src: urls.inline, alt: file.name || t("imageAlt") }],
          label: file.name,
          strings: documentStrings(t),
        }),
        images.length ? h(P.Inline, null, h(P.Button, { size: "sm", onClick: onFullScreen }, t("fullScreen"))) : null,
      );
    else if (kind === "audio" || kind === "video")
      // Authorized download route; media elements stream it with byte ranges.
      viewer = h(P.MediaPlayer, { key: file.id, src: urls.download, kind, label: file.name, strings: mediaStrings(t) });
    else if (kind === "pdf" && urls.inline) viewer = h(PdfPreview, { key: file.id, file, lang, inline: urls.inline });
    else viewer = h(P.Text, { variant: "secondary" }, t("wordDownload"));
    return h(
      P.Stack,
      { gap: "md" },
      h(
        P.PropertyList,
        null,
        h(P.PropertyList.Item, { label: t("category"), data: true }, file.category),
        h(P.PropertyList.Item, { label: t("version") }, String(file.version)),
        file.byte_count ? h(P.PropertyList.Item, { label: t("size"), data: true }, formatBytes(file.byte_count, lang)) : null,
        file.created_at ? h(P.PropertyList.Item, { label: t("uploadedOn"), data: true }, base.formatWhen(file.created_at, lang)) : null,
      ),
      viewer,
      h(P.Inline, null, h(P.Button, { href: urls.download }, t("download"))),
    );
  }

  function CaseFilesWorkspace({ api, lang, caseId, section }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [history, setHistory] = R.useState(false);
    const [rows, setRows] = R.useState([]);
    const [next, setNext] = R.useState(null);
    const [pending, setPending] = R.useState(true);
    const [failure, setFailure] = R.useState(null);
    const [selected, select] = R.useState(null);
    const [viewerIndex, setViewerIndex] = R.useState(null);
    const [reload, setReload] = R.useState(0);
    R.useEffect(() => {
      let live = true;
      setPending(true);
      setFailure(null);
      setRows([]);
      select(null);
      api(`/api/cases/${encodeURIComponent(caseId)}/files/?history=${history ? 1 : 0}`)
        .then((data) => {
          if (!live) return;
          setRows(data.items || []);
          setNext(data.next_offset ?? null);
        })
        .catch((error) => live && setFailure(error))
        .finally(() => live && setPending(false));
      return () => {
        live = false;
      };
    }, [caseId, history, reload]);
    async function more() {
      if (next === null) return;
      setPending(true);
      try {
        const data = await api(`/api/cases/${encodeURIComponent(caseId)}/files/?history=${history ? 1 : 0}&offset=${next}`);
        setRows((old) => [...old, ...(data.items || []).filter((row) => !old.some((x) => x.id === row.id))]);
        setNext(data.next_offset ?? null);
      } catch (error) {
        setFailure(error);
      } finally {
        setPending(false);
      }
    }
    const visible = sectionFiles(rows, section);
    const demoRows = section === "evidence"
      ? [
          { id: "demo-evidence-01", name: "demo-evidence-01.png", version: "—", demoSrc: "/static/ctm/demo-evidence/demo-evidence-01.png", demoType: "image" },
          { id: "demo-evidence-02", name: "demo-evidence-02.png", version: "—", demoSrc: "/static/ctm/demo-evidence/demo-evidence-02.png", demoType: "image" },
          { id: "demo-evidence-03", name: "demo-evidence-03.png", version: "—", demoSrc: "/static/ctm/demo-evidence/demo-evidence-03.png", demoType: "image" },
          { id: "demo-evidence-04", name: "demo-evidence-04.png", version: "—", demoSrc: "/static/ctm/demo-evidence/demo-evidence-04.png", demoType: "image" },
        ]
      : [
          { id: "demo-document-pdf", name: "PDF Test.pdf", version: "—", demoSrc: "/static/ctm/demo-documents/PDF-Test.pdf", demoType: "document" },
          { id: "demo-document-word", name: "MSWORD TEST.docx", version: "—", demoSrc: "/static/ctm/demo-documents/MSWORD-TEST.docx", demoType: "document" },
        ];
    const tableRows = [...demoRows, ...visible];
    const chosen = tableRows.find((row) => row.id === selected);
    const images = visible.filter((row) => viewerKind(row) === "image" && fileUrls(row).inline);
    const viewerItems = images.map((row) => ({ src: fileUrls(row).inline, alt: row.name, title: row.name, meta: [row.category, formatBytes(row.byte_count, lang)] }));
    const demoPreview = chosen?.demoSrc
      ? h(P.Stack, { gap: "md" },
          chosen.demoType === "image" ? h("img", { className: "ctm-demo-file-preview", src: chosen.demoSrc, alt: chosen.name }) : h(P.Text, null, chosen.name),
          h(P.Inline, null,
            h(P.Button, { href: chosen.demoSrc, target: "_blank", rel: "noreferrer" }, t("openDocument")),
            h("a", { className: "plx-button plx-button--secondary", href: chosen.demoSrc, download: chosen.name }, t("downloadDocument")),
          ),
        )
      : null;
    return h(
      P.Stack,
      { gap: "lg", className: "plx-u-flex-1 plx-u-min-h-0" },
      h(P.Text, { as: "h1", variant: "title" }, t(section === "documents" ? "documentsTitle" : "evidenceTitle")),
      h(P.SplitView, {
        label: t(section === "documents" ? "documentsTitle" : "evidenceTitle"),
        firstLabel: t(section === "documents" ? "documentsTitle" : "evidenceTitle"),
        first: h(
          P.Stack,
          { gap: "sm", className: "plx-u-flex-1 plx-u-min-h-0" },
          h(P.Checkbox, { label: t("olderVersions"), checked: history, onChange: (e) => setHistory(e.target.checked) }),
          h(window.CTMShell.Table, {
            label: t(section === "documents" ? "documentsTitle" : "evidenceTitle"),
            rows: tableRows, selected, onSelect: select, empty: t("noFiles"),
            columns: [{ title: t(section === "documents" ? "documentsTitle" : "evidenceTitle"), field: "name", kind: "name" }, { title: t("version"), field: "version" }],
          }),
          pending ? base.loadingView(P, h, t) : null,
          failure ? base.loadFailure(P, h, t, () => setReload((n) => n + 1), failure) : null,
          next !== null ? h(P.Button, { size: "sm", disabled: pending, onClick: more }, t("more")) : null,
        ),
        second: h(
          P.ReadingPane,
          { label: chosen ? chosen.name : t("chooseFile"), empty: h(P.EmptyState, { title: t("chooseFile") }) },
          chosen ? (demoPreview || h(FilePreview, { key: chosen.id, file: chosen, lang, images, onFullScreen: () => setViewerIndex(Math.max(0, images.findIndex((row) => row.id === chosen.id))) })) : null,
        ),
      }),
      viewerIndex !== null ? h(P.MediaViewer, { open: true, items: viewerItems, index: viewerIndex, onIndexChange: setViewerIndex, onClose: () => setViewerIndex(null), label: t("viewerLabel"), strings: { label: t("viewerLabel"), close: t("closePreview"), previous: t("previous"), next: t("next"), counter: t("counter") } }) : null,
    );

  }

  Object.assign(window.CTMCouncil, {
    mediaWords: words,
    mediaTranslator: translator,
    ReportRevisionEditor, // exported for the unsaved-text regression test
    ReportDetailTabs,
    chooseMimeType,
    revisionAccess,
    revisionFields,
    revisionDraft,
    revisionPayload,
    revisionChanged,
    saveFailure,
    stableJson,
    isSameSave,
    processingView,
    transcriptGroups,
    timedSegments,
    RecordingStatusList,
    TranscriptsPanel,
    TranscriptViewer,
    PdfPreview,
    paperOriginal,
    recordedOriginal,
    FilePreview,
    pdfStrings,
    answerEntries,
    extensionFor,
    sizeLimitBytes,
    microphoneProblem,
    formatDuration,
    elapsedMs,
    viewerKind,
    fileUrls,
    sectionFiles,
    formatBytes,
    recordingStore,
    ReportRecorder,
    ReportsReader: base.guarded(ReportsReader),
    CaseFilesWorkspace: base.guarded(CaseFilesWorkspace),
  });
})();
