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
      submittedNoRead:
        "Submitted. Transcription status cannot be shown here yet; the original audio is stored with the report.",
      uploadFailed: "The recording could not be submitted. It is still kept on this device; try again.",
      scanRejected: "The automatic safety check rejected this recording. It is kept on this device.",
      checkAgain: "Check again",
      retrySubmit: "Try again",
      writerOnlyRecording: "Only the assigned case manager, or the administrator or secretary, records while the proceeding is open.",
      notInterview: "Recordings are used for interviews conducted by the case manager.",
      transcriptsPending:
        "Transcription status and transcripts are not available from this server yet. Submitted recordings keep their original audio.",
      beforeUnload: "A recording is in progress.",
      reportsList: "Completed reports",
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
      revisionStale:
        "Version {version} was saved by {actor} after you started editing. Your text is kept below. Review the latest version in the revision history, then save your text as a new version or discard it.",
      saveAnyway: "Save my text as a new version",
      discardChanges: "Discard my changes",
      revisionDenied: "This revision was not allowed. Your text is still shown so you can copy it.",
      revisionKept: "Your text is kept; try again.",
      nonTextKept: "Attached files and other non-text answers are kept unchanged.",
      unsavedRevision: "A report revision has not been saved.",
      reportAuthor: "Author",
      reportSubmitted: "Submitted",
      reportMethod: "Method",
      method_written: "Entered in CTM",
      method_external: "External source link",
      evidenceTitle: "Evidence",
      documentsTitle: "Documents",
      olderVersions: "Include older versions",
      noFiles: "No technically cleared files are available in this section.",
      chooseFile: "Select a file",
      download: "Download",
      openPdf: "Open PDF",
      pdfExternal: "The PDF opens in the browser's viewer through the protected file link. The embedded viewer becomes available once its viewer files are configured.",
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
      submittedNoRead: "تم التقديم. لا يمكن عرض حالة التفريغ هنا بعد؛ والصوت الأصلي محفوظ مع التقرير.",
      uploadFailed: "تعذر تقديم التسجيل. وما زال محفوظًا على هذا الجهاز؛ حاول مجددًا.",
      scanRejected: "رفض فحص الأمان التلقائي هذا التسجيل. وما زال محفوظًا على هذا الجهاز.",
      checkAgain: "التحقق مرة أخرى",
      retrySubmit: "إعادة المحاولة",
      writerOnlyRecording: "يسجّل مسؤول القضية المعيَّن أو مسؤول المجلس أو السكرتير فقط ما دام الإجراء مفتوحًا.",
      notInterview: "تُستخدم التسجيلات للمقابلات التي يجريها مسؤول القضية.",
      transcriptsPending: "حالة التفريغ والنصوص المفرغة غير متاحة من هذا الخادم بعد. وتحتفظ التسجيلات المقدَّمة بصوتها الأصلي.",
      beforeUnload: "يوجد تسجيل قيد التنفيذ.",
      reportsList: "التقارير المكتملة",
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
      revisionStale:
        "حفظ {actor} الإصدار {version} بعد أن بدأت التعديل. وما زال نصك محفوظًا أدناه. راجع أحدث إصدار في سجل التعديلات، ثم احفظ نصك كإصدار جديد أو تجاهله.",
      saveAnyway: "حفظ نصي كإصدار جديد",
      discardChanges: "تجاهل تغييراتي",
      revisionDenied: "لم يُسمح بهذا التعديل. وما زال نصك معروضًا لتتمكن من نسخه.",
      revisionKept: "نصك محفوظ؛ حاول مجددًا.",
      nonTextKept: "تبقى الملفات المرفقة والإجابات غير النصية دون تغيير.",
      unsavedRevision: "يوجد تعديل على التقرير لم يُحفظ.",
      reportAuthor: "الكاتب",
      reportSubmitted: "تاريخ التقديم",
      reportMethod: "الطريقة",
      method_written: "أُدخل في النظام",
      method_external: "رابط مصدر خارجي",
      evidenceTitle: "الأدلة",
      documentsTitle: "المستندات",
      olderVersions: "تضمين الإصدارات السابقة",
      noFiles: "لا توجد ملفات اجتازت فحص الأمان في هذا القسم.",
      chooseFile: "اختر ملفًا",
      download: "تنزيل",
      openPdf: "فتح ملف PDF",
      pdfExternal: "يُفتح ملف PDF في عارض المتصفح عبر رابط الملف المحمي. ويصبح العارض المضمَّن متاحًا بعد إعداد ملفاته.",
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
      if (vars) for (const [k, v] of Object.entries(vars)) value = value.replace(`{${k}}`, v);
      return value;
    };
  }

  const mediaStrings = (t) =>
    Object.fromEntries(
      ["rate", "transcript", "hideTranscript", "pip", "exitPip", "unsupported", "pipFailed", "seek", "fallback", "audioFailed", "volume", "mute"]
        .map((k) => [k, t(k)])
        .concat([["failed", t("failed")]]),
    );
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
            body: JSON.stringify({ file_id: r.fileId, report_id: reportId, notice_recorded: true }),
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

  function ReportRevisionEditor({ api, lang, report, latest, onCancel, onSaved, onHistory, onDenied }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [draft, setDraft] = R.useState(() => revisionDraft(report, latest));
    const [base0, setBase0] = R.useState(latest);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [denied, setDenied] = R.useState(false);
    const [stale, setStale] = R.useState(null);
    const [problem, setProblem] = R.useState(null);
    const dirty = revisionChanged(base0, draft);
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
    async function save(event, force) {
      if (event && event.preventDefault) event.preventDefault();
      setFailure(null);
      setProblem(null);
      if (!force && !revisionChanged(base0, draft)) return setProblem("revisionNoChange");
      setPending(true);
      try {
        // Preflight offers a helpful stale warning; the bound version also guards the write race.
        const current = await api(url);
        const newest = (current.items || [])[0] || null;
        onHistory(current.items || []);
        if (!force && newest && base0 && newest.version !== base0.version) {
          setStale(newest);
          return;
        }
        await api(url, { method: "POST", body: JSON.stringify(revisionPayload(newest || base0, draft)) });
        const after = await api(url).catch(() => null);
        if (after) onHistory(after.items || []);
        onSaved(after?.items?.[0]?.version ?? null);
      } catch (error) {
        setFailure(base.serverMessage(error, t));
        if (error && error.status === 403) {
          setDenied(true);
          if (onDenied) onDenied(); // refresh rows so can_revise reflects the withdrawn authority
        }
      } finally {
        setPending(false);
      }
    }
    function adoptLatest() {
      setBase0(stale);
      setStale(null);
      save(null, true);
    }
    const questions = report.questions || [];
    const kept = Object.entries((latest && latest.answers) || {}).some(([, v]) => typeof v !== "string");
    return h(
      P.Form,
      { onSubmit: (e) => save(e, false), label: t("reviseTitle"), noValidate: true },
      h(
        P.FormSection,
        { title: t("reviseTitle"), description: t("reviseHelp") },
        ...revisionFields(report, latest).map((code) => {
          const q = questions.find((x) => x.code === code);
          return h(
            P.Field,
            { key: code, label: q ? `${code} — ${base.isolate((lang === "ar" && q.ar) || q.en || code)}` : code },
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
                setProblem(null);
              },
            }),
          );
        }),
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
              setProblem(null);
            },
          }),
        ),
        kept ? h(P.Text, { variant: "secondary" }, t("nonTextKept")) : null,
      ),
      stale
        ? h(
            P.Notice,
            { tone: "warning" },
            h(
              P.Stack,
              { gap: "sm" },
              h(P.Text, { as: "p" }, t("revisionStale", { version: String(stale.version), actor: stale.actor ? base.isolate(stale.actor) : "—" })),
              h(
                P.Inline,
                null,
                h(P.Button, { size: "sm", disabled: pending, onClick: adoptLatest }, t("saveAnyway")),
                h(P.Button, { size: "sm", disabled: pending, onClick: onCancel }, t("discardChanges")),
              ),
            ),
          )
        : null,
      problem ? h(P.Notice, { tone: "info" }, t(problem)) : null,
      failure ? h(P.Notice, { tone: "danger" }, `${failure} ${t(denied ? "revisionDenied" : "revisionKept")}`) : null,
      h(
        P.FormActions,
        { sticky: false },
        h(P.Button, { disabled: pending, onClick: onCancel }, t("cancel")),
        denied || stale ? null : h(P.Button, { type: "submit", variant: "primary", loading: pending, disabled: pending }, t("saveRevision")),
      ),
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
    const [editing, setEditing] = R.useState(null); // latest revision the edit started from
    const [opening, setOpening] = R.useState(false);
    const [saved, setSaved] = R.useState(null);
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
    const answers = editing
      ? h(ReportRevisionEditor, {
          api,
          lang,
          report,
          latest: editing,
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
        report.author ? h(P.PropertyList.Item, { label: t("reportAuthor") }, base.isolate(report.author)) : null,
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
        const question = (report.questions || []).find((q) => q.code === code);
        const label = question ? `${code} — ${base.isolate((lang === "ar" && question.ar) || question.en || code)}` : code === "files" ? t("response") : code;
        return h(P.Panel, { icon: "document", key: code, title: label }, h(P.Text, { as: "p", dir: "auto" }, typeof answer === "string" ? answer : JSON.stringify(answer)));
      }),
      shown.observations ? h(P.Panel, { icon: "document", title: t("observations") }, h(P.Text, { as: "p", dir: "auto" }, shown.observations)) : null,
      access === "unknown" ? h(P.Text, { variant: "secondary" }, t("revisionPending")) : null,
      access === "denied" ? h(P.Text, { variant: "secondary" }, t("revisionNotAllowed")) : null,
    );
    const interview = report.kind === "interview";
    const recording = interview
      ? h(ReportRecorder, {
          key: report.id,
          api,
          lang,
          storageKey: `report:${report.id}`,
          reportId: report.id,
          caseId: record.id,
          canSubmit: writer,
        })
      : h(P.EmptyState, { title: t("notInterview") });
    return h(P.Tabs, {
      label: report.title,
      value: tab,
      onChange: setTab,
      items: [
        { value: "answers", label: t("answersTab"), content: answers },
        { value: "recording", label: t("recordingTab"), content: interview && !writer ? h(P.Stack, { gap: "md" }, h(P.Notice, { tone: "info" }, t("writerOnlyRecording")), recording) : recording },
        { value: "transcripts", label: t("transcriptsTab"), content: h(P.Notice, { tone: "info" }, t("transcriptsPending")) },
      ],
    });
  }

  function ReportsReader({ api, lang, user, caseId, reports }) {
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
    const chosen = rows.find((row) => row.id === selected);
    if (state.pending && !state.data) return base.loadingView(P, h, t);
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    return h(P.SplitView, {
      label: t("reportsList"),
      firstLabel: t("reportsList"),
      first: h(window.CTMShell.Table, {
        label: t("reportsList"), rows, selected, onSelect: select, empty: t("noReports"),
        columns: [{ title: t("reportsList"), field: "title", kind: "name" }, { title: t("version"), field: "version", type: "number" }],
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

  function FilePreview({ file, lang, images, onFullScreen }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const kind = viewerKind(file);
    const urls = fileUrls(file);
    const pdfConfig = window.CTM_PDF_VIEWER || null; // { moduleUrl, workerUrl } supplied by governance packaging
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
    else if (kind === "pdf" && urls.inline && pdfConfig && pdfConfig.moduleUrl)
      viewer = h(P.DocumentViewer, {
        key: file.id,
        kind: "pdf",
        src: urls.inline,
        label: file.name,
        pdfModuleUrl: pdfConfig.moduleUrl,
        pdfWorkerUrl: pdfConfig.workerUrl,
        strings: documentStrings(t),
      });
    else if (kind === "pdf" && urls.inline)
      viewer = h(
        P.Stack,
        { gap: "sm" },
        h(P.Text, { variant: "secondary" }, t("pdfExternal")),
        h(P.Inline, null, h(P.Button, { href: urls.inline, target: "_blank", rel: "noopener noreferrer" }, t("openPdf"))),
      );
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
    const chosen = visible.find((row) => row.id === selected);
    const images = visible.filter((row) => viewerKind(row) === "image" && fileUrls(row).inline);
    const viewerItems = images.map((row) => ({ src: fileUrls(row).inline, alt: row.name, title: row.name, meta: [row.category, formatBytes(row.byte_count, lang)] }));
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
            rows: visible, selected, onSelect: select, empty: t("noFiles"),
            columns: [{ title: t(section === "documents" ? "documentsTitle" : "evidenceTitle"), field: "name", kind: "name" }, { title: t("version"), field: "version", type: "number" }],
          }),
          pending ? base.loadingView(P, h, t) : null,
          !pending && !visible.length && !failure ? h(P.EmptyState, { title: t("noFiles") }) : null,
          failure ? base.loadFailure(P, h, t, () => setReload((n) => n + 1), failure) : null,
          next !== null ? h(P.Button, { size: "sm", disabled: pending, onClick: more }, t("more")) : null,
        ),
        second: h(
          P.ReadingPane,
          { label: chosen ? chosen.name : t("chooseFile"), empty: h(P.EmptyState, { title: t("chooseFile") }) },
          chosen
            ? h(FilePreview, {
                key: chosen.id,
                file: chosen,
                lang,
                images,
                onFullScreen: () => setViewerIndex(Math.max(0, images.findIndex((row) => row.id === chosen.id))),
              })
            : null,
        ),
      }),
      viewerIndex !== null
        ? h(P.MediaViewer, {
            open: true,
            items: viewerItems,
            index: viewerIndex,
            onIndexChange: setViewerIndex,
            onClose: () => setViewerIndex(null),
            label: t("viewerLabel"),
            strings: { label: t("viewerLabel"), close: t("closePreview"), previous: t("previous"), next: t("next"), counter: t("counter") },
          })
        : null,
    );
  }

  Object.assign(window.CTMCouncil, {
    mediaWords: words,
    mediaTranslator: translator,
    chooseMimeType,
    revisionAccess,
    revisionFields,
    revisionDraft,
    revisionPayload,
    revisionChanged,
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
