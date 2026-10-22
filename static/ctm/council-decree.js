/* CTM council decree workspace. Loads after council.js and council-case.js.
   Only the administrator or secretary prepare, issue and release a decree; the
   server enforces this and every lifecycle rule. No replacement/clerical
   correction workflow is offered (removed by the build contract). */
(() => {
  "use strict";
  const base = window.CTMCouncil;
  if (!base || !base.caseTranslator) return;

  const LANGS = ["en", "ar", "both"];
  const METHODS = ["digital", "signed_scan"];
  const NO_CERTIFICATE = new Set(["denied", "deferred"]);

  // ---------- Pure logic ----------

  function decreeEligibility(decision) {
    if (!decision) return "noDecision";
    if (decision.current === false) return "notCurrent";
    if (NO_CERTIFICATE.has(decision.type)) return decision.type === "denied" ? "deniedNoCertificate" : "deferredNoCertificate";
    if (!decision.approval) return "needsApproval";
    return null;
  }

  function decreeReference(caseNumber, proceeding) {
    if (!caseNumber) return null;
    return proceeding && proceeding.kind === "appeal" ? `DCR-${caseNumber}-A${proceeding.sequence}` : `DCR-${caseNumber}`;
  }

  function entitledParties(decision, parties) {
    const ents = decision?.entitlements || {};
    return (parties || []).filter((p) => ents[p.id] === "certificate");
  }

  function releaseStatus(releases, partyId) {
    const rows = (releases || []).filter((r) => r.party_id === partyId);
    const last = rows[rows.length - 1];
    return last ? (last.action === "release" ? "released" : "withdrawn") : "notReleased";
  }

  // Current step: 0 upload, 1 safety check, 2 signature, 3 issue.
  function decreeStep(work) {
    if (!work.file) return 0;
    if (work.file.scan_state !== "clean") return 1;
    if (!work.attested) return 2;
    return 3;
  }

  function uploadProblem(file, language) {
    if (!LANGS.includes(language)) return "chooseLanguage";
    if (!file) return "chooseFile";
    const pdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name || "");
    if (!pdf) return "pdfOnly";
    if (file.size > 25 * 1024 * 1024) return "tooLarge";
    return null;
  }

  function attestationProblem(form) {
    if (!METHODS.includes(form.method)) return "chooseMethod";
    if (form.confirmed !== true) return "confirmSigned";
    return null;
  }

  function latestProceeding(record) {
    const rows = [...(record?.proceedings || [])];
    const open = rows.find((p) => p.status === "open");
    if (open) return open;
    return rows.sort((a, b) => (b.sequence || 0) - (a.sequence || 0))[0] || null;
  }

  // ---------- Words ----------

  const words = {
    en: {
      decree: "Decree",
      adminOnly: "Only the administrator or secretary prepares, issues and releases the decree. You can follow its status here.",
      readMissing: "The decision record cannot be read from this server yet, so the decree cannot be prepared here.",
      noDecision: "No decision has been recorded yet.",
      notCurrent: "The decision shown is not the current version.",
      needsApproval: "The current decision version needs presidential approval before a decree can be prepared.",
      deniedNoCertificate: "Petition Denied closes the case with an official decision notice. No decree certificate is issued.",
      deferredNoCertificate: "A deferred decision does not issue a decree certificate.",
      templateNotice:
        "Certificate generation from the approved templates is not available yet. Upload the signed PDF prepared from the approved template for this decision type.",
      approvedDecision: "Approved decision",
      steps: "Decree steps",
      stepUpload: "Signed PDF",
      stepScan: "Safety check",
      stepSignature: "Signature record",
      stepIssue: "Issue",
      decreeId: "Decree ID",
      certificateLanguage: "Certificate language",
      en: "English",
      ar: "Arabic",
      both: "English and Arabic (one bilingual certificate)",
      signedPdf: "Signed certificate (PDF, up to 25 MB)",
      chooseFile: "Choose the signed PDF.",
      chooseLanguage: "Choose the certificate language.",
      pdfOnly: "Only a PDF file can be stored as the signed certificate.",
      tooLarge: "The file is larger than 25 MB.",
      upload: "Store signed PDF",
      uploaded: "The signed PDF was stored. It is visible to the council only.",
      scanWaiting: "The automatic safety check for this file is not complete. The decree cannot be issued until it passes.",
      checkAgain: "Check again",
      stillWaiting: "The safety check is still not complete.",
      storedFile: "Stored file",
      download: "Download",
      signer: "Signing President",
      method: "Signing method",
      digital: "Digital signature by the President",
      signed_scan: "Printed, signed by the President and scanned",
      confirmSignedLabel: "I confirm this exact PDF bears the President's signature.",
      confirmSigned: "Confirm that the stored PDF is signed by the President.",
      chooseMethod: "Choose the signing method.",
      evidenceNote: "Signature note (optional)",
      recordSignature: "Record signature",
      signatureRecorded: "The President's signature was recorded for this PDF.",
      issueSummary: "Ready to issue",
      issue: "Issue decree",
      issueTitle: "Issue this decree?",
      issueMessage:
        "Issuing closes the case. Each spouse is notified privately according to their entitlement. The certificate stays hidden from applicants until you release it.",
      issued: "The decree was issued and the case is closed.",
      issuedTitle: "Issued decree",
      issuedAt: "Issued",
      unknownIssued:
        "This case is closed. The issued decree's details and release controls cannot be displayed from this server yet.",
      recipients: "Certificate recipients",
      noRecipients: "Neither spouse is entitled to the certificate under this decision.",
      notReleased: "Not released",
      released: "Released",
      withdrawn: "Access withdrawn",
      release: "Release certificate",
      withdrawAccess: "Withdraw access",
      releaseTitle: "Release the certificate to this recipient?",
      releaseMessage: "The recipient is notified privately and can view and download the signed certificate.",
      withdrawTitle: "Withdraw this recipient's access?",
      withdrawMessage:
        "Use this only when the certificate was released in error. Later views and downloads are blocked; copies already downloaded cannot be recalled. The decree and closed case are unchanged.",
      releaseDone: "The certificate was released.",
      withdrawDone: "Access was withdrawn.",
      noticeOnly: "Official decision notice only",
      cancel: "Cancel",
      appeals: "Appeals",
      appeal: "Appeal",
      noAppeals: "No appeals have been filed for this case.",
      chooseAppeal: "Select an appeal",
      appellant: "Appellant",
      appeal_draft: "Draft",
      appeal_submitted: "Pending",
      appeal_accepted: "Accepted",
      appeal_declined: "Declined",
      appeal_withdrawn: "Withdrawn",
      appealStatement: "Appeal statement and new information",
      supplementsPending: "Additional information added by the appellant after submission is not yet shown here.",
      recordAppealResult: "Record council result",
      appealResultHelp: "Record the result the council reached at the case hearing. Each appeal has its own result.",
      hearingsUnavailable: "Case hearings cannot be listed from this server yet, so a result cannot be recorded here.",
      noHeardHearing: "This appeal has not been heard yet. Place the case on a council session agenda and present it first.",
      caseHearing: "Case hearing",
      chooseHearing: "Select the case hearing.",
      appealResult: "Result",
      acceptAppeal: "Accept appeal",
      declineAppeal: "Decline appeal",
      chooseResult: "Choose Accept or Decline.",
      appealExplanation: "Additional explanation to the appellant (optional)",
      appealExplanationHelp: "Added to the official notice. Do not include council deliberations.",
      appealWriterOnly: "Only the assigned case manager, or the administrator or secretary, records the appeal result.",
      acceptAppealTitle: "Accept this appeal?",
      acceptAppealMessage: "The original case reopens under the same case number as a new appeal proceeding, unless it is already reopened. Both applicants are notified privately. Earlier proceedings stay read-only.",
      declineAppealTitle: "Decline this appeal?",
      declineAppealMessage: "The appellant receives the official decline notice privately. If no other appeal has reopened the case, it stays closed. The existing decree and access are unchanged.",
      appealAccepted: "The appeal was accepted.",
      appealDeclined: "The appeal was declined and the official notice was sent.",
    },
    ar: {
      decree: "الشهادة",
      adminOnly: "يُعِدّ مسؤول المجلس أو السكرتير الشهادة ويُصدرها ويتيحها فقط. يمكنك متابعة حالتها هنا.",
      readMissing: "لا يمكن قراءة سجل القرار من هذا الخادم بعد، لذلك لا يمكن إعداد الشهادة هنا.",
      noDecision: "لم يُسجَّل قرار بعد.",
      notCurrent: "القرار المعروض ليس الإصدار الحالي.",
      needsApproval: "يحتاج الإصدار الحالي من القرار إلى اعتماد الرئيس قبل إعداد الشهادة.",
      deniedNoCertificate: "رفض الطلب يُغلق القضية بإخطار رسمي بالقرار. ولا تصدر شهادة.",
      deferredNoCertificate: "القرار المؤجل لا تصدر عنه شهادة.",
      templateNotice:
        "إنشاء الشهادة من النماذج المعتمدة غير متاح بعد. ارفع ملف PDF الموقَّع المُعَدّ من النموذج المعتمد لنوع هذا القرار.",
      approvedDecision: "القرار المعتمد",
      steps: "خطوات الشهادة",
      stepUpload: "ملف PDF الموقَّع",
      stepScan: "فحص الأمان",
      stepSignature: "تسجيل التوقيع",
      stepIssue: "الإصدار",
      decreeId: "رقم الشهادة",
      certificateLanguage: "لغة الشهادة",
      en: "الإنجليزية",
      ar: "العربية",
      both: "الإنجليزية والعربية (شهادة واحدة ثنائية اللغة)",
      signedPdf: "الشهادة الموقَّعة (PDF حتى ٢٥ ميجابايت)",
      chooseFile: "اختر ملف PDF الموقَّع.",
      chooseLanguage: "اختر لغة الشهادة.",
      pdfOnly: "لا يمكن حفظ الشهادة الموقَّعة إلا كملف PDF.",
      tooLarge: "حجم الملف أكبر من ٢٥ ميجابايت.",
      upload: "حفظ ملف PDF الموقَّع",
      uploaded: "تم حفظ ملف PDF الموقَّع. ولا يراه إلا أعضاء المجلس.",
      scanWaiting: "لم يكتمل فحص الأمان التلقائي لهذا الملف. لا يمكن إصدار الشهادة حتى يجتازه.",
      checkAgain: "التحقق مرة أخرى",
      stillWaiting: "لم يكتمل فحص الأمان بعد.",
      storedFile: "الملف المحفوظ",
      download: "تنزيل",
      signer: "الرئيس الموقِّع",
      method: "طريقة التوقيع",
      digital: "توقيع رقمي من الرئيس",
      signed_scan: "طُبعت ووقَّعها الرئيس ثم مُسحت ضوئيًا",
      confirmSignedLabel: "أؤكد أن ملف PDF هذا بعينه يحمل توقيع الرئيس.",
      confirmSigned: "أكِّد أن ملف PDF المحفوظ موقَّع من الرئيس.",
      chooseMethod: "اختر طريقة التوقيع.",
      evidenceNote: "ملاحظة عن التوقيع (اختياري)",
      recordSignature: "تسجيل التوقيع",
      signatureRecorded: "تم تسجيل توقيع الرئيس لهذا الملف.",
      issueSummary: "جاهزة للإصدار",
      issue: "إصدار الشهادة",
      issueTitle: "هل تريد إصدار هذه الشهادة؟",
      issueMessage:
        "يؤدي الإصدار إلى إغلاق القضية. ويُخطَر كل من الزوجين بشكل خاص وفق استحقاقه. وتبقى الشهادة مخفية عن مقدمي الطلبات حتى تتيحها.",
      issued: "تم إصدار الشهادة وإغلاق القضية.",
      issuedTitle: "الشهادة الصادرة",
      issuedAt: "تاريخ الإصدار",
      unknownIssued: "هذه القضية مغلقة. لا يمكن عرض تفاصيل الشهادة الصادرة وأدوات إتاحتها من هذا الخادم بعد.",
      recipients: "مستحقو الشهادة",
      noRecipients: "لا يستحق أي من الزوجين الشهادة بموجب هذا القرار.",
      notReleased: "لم تُتَح",
      released: "أُتيحت",
      withdrawn: "سُحبت الإتاحة",
      release: "إتاحة الشهادة",
      withdrawAccess: "سحب الإتاحة",
      releaseTitle: "هل تريد إتاحة الشهادة لهذا المستحق؟",
      releaseMessage: "يُخطَر المستحق بشكل خاص ويمكنه عرض الشهادة الموقَّعة وتنزيلها.",
      withdrawTitle: "هل تريد سحب إتاحة الشهادة لهذا المستحق؟",
      withdrawMessage:
        "استخدم هذا فقط إذا أُتيحت الشهادة خطأً. يُمنع العرض والتنزيل لاحقًا؛ ولا يمكن استرجاع النسخ التي نُزِّلت. ولا تتغير الشهادة ولا القضية المغلقة.",
      releaseDone: "تمت إتاحة الشهادة.",
      withdrawDone: "تم سحب الإتاحة.",
      noticeOnly: "إخطار رسمي بالقرار فقط",
      cancel: "إلغاء",
      appeals: "الاستئنافات",
      appeal: "استئناف",
      noAppeals: "لم يُقدَّم أي استئناف في هذه القضية.",
      chooseAppeal: "اختر استئنافًا",
      appellant: "مقدم الاستئناف",
      appeal_draft: "مسودة",
      appeal_submitted: "قيد النظر",
      appeal_accepted: "مقبول",
      appeal_declined: "مرفوض",
      appeal_withdrawn: "مسحوب",
      appealStatement: "بيان الاستئناف والمعلومات الجديدة",
      supplementsPending: "المعلومات الإضافية التي أضافها مقدم الاستئناف بعد التقديم لا تظهر هنا بعد.",
      recordAppealResult: "تسجيل نتيجة المجلس",
      appealResultHelp: "سجّل النتيجة التي انتهى إليها المجلس في جلسة نظر القضية. لكل استئناف نتيجته المستقلة.",
      hearingsUnavailable: "لا يمكن عرض جلسات نظر القضية من هذا الخادم بعد، لذلك لا يمكن تسجيل النتيجة هنا.",
      noHeardHearing: "لم يُنظر هذا الاستئناف بعد. أدرج القضية في جدول أعمال جلسة المجلس واعرضها أولًا.",
      caseHearing: "جلسة نظر القضية",
      chooseHearing: "اختر جلسة نظر القضية.",
      appealResult: "النتيجة",
      acceptAppeal: "قبول الاستئناف",
      declineAppeal: "رفض الاستئناف",
      chooseResult: "اختر القبول أو الرفض.",
      appealExplanation: "توضيح إضافي لمقدم الاستئناف (اختياري)",
      appealExplanationHelp: "يُضاف إلى الإخطار الرسمي. لا تُدرج مداولات المجلس.",
      appealWriterOnly: "يسجّل نتيجة الاستئناف مسؤول القضية المعيَّن أو مسؤول المجلس أو السكرتير فقط.",
      acceptAppealTitle: "هل تريد قبول هذا الاستئناف؟",
      acceptAppealMessage: "يُعاد فتح القضية الأصلية بالرقم نفسه كإجراء استئناف جديد ما لم تكن قد أُعيد فتحها. ويُخطَر مقدما الطلب كلٌّ على حدة. وتبقى الإجراءات السابقة للقراءة فقط.",
      declineAppealTitle: "هل تريد رفض هذا الاستئناف؟",
      declineAppealMessage: "يتلقى مقدم الاستئناف الإخطار الرسمي بالرفض بشكل خاص. وإن لم يُعِد استئناف آخر فتح القضية فإنها تبقى مغلقة. ولا تتغير الشهادة القائمة ولا إتاحتها.",
      appealAccepted: "تم قبول الاستئناف.",
      appealDeclined: "تم رفض الاستئناف وإرسال الإخطار الرسمي.",
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

  // ---------- Views ----------

  function IssuedDecree({ api, lang, manage, decree, decision, record, onChange }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [dialog, setDialog] = R.useState(null); // {party, action}
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    const recipients = entitledParties(decision, record.parties);
    async function act() {
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/decrees/${encodeURIComponent(decree.id)}/release/`, {
          method: "POST",
          body: JSON.stringify({ party_id: dialog.party.id, action: dialog.action }),
        });
        onChange({
          ...decree,
          releases: [...(decree.releases || []), { party_id: dialog.party.id, action: dialog.action, timestamp: new Date().toISOString() }],
        });
        setNotice(dialog.action === "release" ? "releaseDone" : "withdrawDone");
        setDialog(null);
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
        { title: t("issuedTitle") },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("decreeId"), data: true }, decree.reference),
          h(P.PropertyList.Item, { label: t("certificateLanguage") }, t(decree.language)),
          decree.issued_at ? h(P.PropertyList.Item, { label: t("issuedAt"), data: true }, base.formatWhen(decree.issued_at, lang)) : null,
          decree.signer ? h(P.PropertyList.Item, { label: t("signer") }, decree.signer) : null,
          decree.signed_file_id
            ? h(
                P.PropertyList.Item,
                { label: t("storedFile") },
                h(P.Button, { size: "xs", href: `/api/files/${encodeURIComponent(decree.signed_file_id)}/` }, t("download")),
              )
            : null,
        ),
      ),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !dialog ? h(P.Notice, { tone: "danger" }, failure) : null,
      h(
        P.Panel,
        { title: t("recipients") },
        recipients.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...record.parties.map((party) => {
                const entitled = recipients.some((r) => r.id === party.id);
                const status = entitled ? releaseStatus(decree.releases, party.id) : null;
                return h(
                  P.Inline,
                  { key: party.id, justify: "between", wrap: true },
                  h(P.Text, { variant: "strong" }, party.name),
                  entitled
                    ? h(
                        P.Inline,
                        { gap: "xs", wrap: true },
                        h(P.Badge, { tone: status === "released" ? "success" : status === "withdrawn" ? "action-required" : "neutral" }, t(status)),
                        manage && status !== "released"
                          ? h(P.Button, { size: "xs", variant: "primary", onClick: () => setDialog({ party, action: "release" }) }, t("release"))
                          : null,
                        manage && status === "released"
                          ? h(P.Button, { size: "xs", variant: "danger-secondary", onClick: () => setDialog({ party, action: "withdraw" }) }, t("withdrawAccess"))
                          : null,
                      )
                    : h(P.Text, { variant: "secondary" }, t("noticeOnly")),
                );
              }),
            )
          : h(P.EmptyState, { title: t("noRecipients") }),
      ),
      h(
        P.ConfirmDialog,
        {
          open: Boolean(dialog),
          title: t(dialog?.action === "withdraw" ? "withdrawTitle" : "releaseTitle"),
          message: t(dialog?.action === "withdraw" ? "withdrawMessage" : "releaseMessage"),
          confirmLabel: t(dialog?.action === "withdraw" ? "withdrawAccess" : "release"),
          cancelLabel: t("cancel"),
          destructive: dialog?.action === "withdraw",
          onConfirm: act,
          onCancel: () => !pending && setDialog(null),
        },
        dialog ? h(P.Text, { as: "p", variant: "strong" }, dialog.party.name) : null,
        failure && dialog ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function DecreePreparation({ api, lang, record, decision, proceeding, members, onIssued }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [work, setWork] = R.useState({ language: "en", chosen: null, file: null, attested: false });
    const [sign, setSign] = R.useState({ method: "", confirmed: false, note: "" });
    const [problem, setProblem] = R.useState(null);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    const [confirm, setConfirm] = R.useState(false);
    const step = decreeStep(work);
    const signerId = decision.approval?.president_id;
    const signerName = decision.approval?.president || members.find((m) => m.id === signerId)?.name || "";
    const reference = decreeReference(record.number, proceeding);

    async function run(fn) {
      setPending(true);
      setFailure(null);
      setNotice(null);
      try {
        await fn();
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }

    const upload = () => {
      const issue = uploadProblem(work.chosen, work.language);
      setProblem(issue);
      if (issue) return;
      run(async () => {
        const form = new FormData();
        form.append("file", work.chosen);
        form.append("category", "DEC");
        form.append("case_id", record.id);
        form.append("visibility", "council");
        const stored = await api("/api/files/", { method: "POST", body: form });
        setWork((old) => ({ ...old, file: { id: stored.id, name: stored.name, scan_state: stored.scan_state } }));
        setNotice(stored.scan_state === "clean" ? "uploaded" : null);
      });
    };

    const recheck = () =>
      run(async () => {
        const listing = await api(`/api/cases/${encodeURIComponent(record.id)}/files/?history=1`);
        const found = (listing.items || []).find((row) => row.id === work.file.id);
        // The listing only returns files whose latest safety check is clean.
        if (found) {
          setWork((old) => ({ ...old, file: { ...old.file, scan_state: "clean" } }));
          setNotice("uploaded");
        } else setNotice("stillWaiting");
      });

    const attest = () => {
      const issue = attestationProblem(sign);
      setProblem(issue);
      if (issue) return;
      run(async () => {
        await api(`/api/files/${encodeURIComponent(work.file.id)}/signature/`, {
          method: "POST",
          body: JSON.stringify({
            signer_id: signerId,
            method: sign.method,
            evidence: { confirmed_signed: true, note: sign.note.trim() },
          }),
        });
        setWork((old) => ({ ...old, attested: true }));
        setNotice("signatureRecorded");
      });
    };

    const issue = () =>
      run(async () => {
        const created = await api(`/api/decisions/${encodeURIComponent(decision.id)}/decree/`, {
          method: "POST",
          body: JSON.stringify({ file_id: work.file.id, signer_id: signerId, language: work.language }),
        });
        setConfirm(false);
        onIssued({
          id: created.id,
          reference,
          language: work.language,
          issued_at: new Date().toISOString(),
          signer: signerName,
          signed_file_id: work.file.id,
          releases: [],
        });
      });

    const err = (key) => (problem === key ? t(key) : undefined);
    let body;
    if (step === 0)
      body = h(
        P.Stack,
        { gap: "md" },
        h(P.Notice, { tone: "info" }, t("templateNotice")),
        h(P.RadioGroup, {
          label: t("certificateLanguage"),
          value: work.language,
          onChange: (value) => setWork((old) => ({ ...old, language: value })),
          options: LANGS.map((value) => ({ value, label: t(value), disabled: pending })),
        }),
        h(
          P.Field,
          { label: t("signedPdf"), required: true, error: err("chooseFile") || err("pdfOnly") || err("tooLarge") },
          h(P.FileInput, {
            accept: ".pdf,application/pdf",
            disabled: pending,
            onChange: (files) => {
              setWork((old) => ({ ...old, chosen: files && files[0] ? files[0] : null }));
              setProblem(null);
            },
          }),
        ),
        h(P.Inline, null, h(P.Button, { variant: "primary", loading: pending, disabled: pending, onClick: upload }, t("upload"))),
      );
    else if (step === 1)
      body = h(
        P.Stack,
        { gap: "md" },
        h(P.Text, { variant: "data" }, work.file.name || work.file.id),
        h(P.Notice, { tone: "warning" }, t("scanWaiting")),
        h(P.Inline, null, h(P.Button, { loading: pending, disabled: pending, onClick: recheck }, t("checkAgain"))),
      );
    else if (step === 2)
      body = h(
        P.Stack,
        { gap: "md" },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("storedFile") }, h(P.Button, { size: "xs", href: `/api/files/${encodeURIComponent(work.file.id)}/` }, t("download"))),
          h(P.PropertyList.Item, { label: t("signer") }, signerName),
        ),
        h(P.RadioGroup, {
          label: t("method"),
          value: sign.method,
          onChange: (value) => {
            setSign((old) => ({ ...old, method: value }));
            setProblem(null);
          },
          options: METHODS.map((value) => ({ value, label: t(value), disabled: pending })),
        }),
        problem === "chooseMethod" ? h(P.Notice, { tone: "danger" }, t("chooseMethod")) : null,
        h(P.Checkbox, {
          label: t("confirmSignedLabel"),
          checked: sign.confirmed,
          disabled: pending,
          onChange: (e) => {
            setSign((old) => ({ ...old, confirmed: e.target.checked }));
            setProblem(null);
          },
        }),
        problem === "confirmSigned" ? h(P.Notice, { tone: "danger" }, t("confirmSigned")) : null,
        h(
          P.Field,
          { label: t("evidenceNote") },
          h(P.Textarea, { rows: 2, value: sign.note, maxLength: 2000, disabled: pending, onChange: (e) => setSign((old) => ({ ...old, note: e.target.value })) }),
        ),
        h(P.Inline, null, h(P.Button, { variant: "primary", loading: pending, disabled: pending, onClick: attest }, t("recordSignature"))),
      );
    else
      body = h(
        P.Stack,
        { gap: "md" },
        h(
          P.PropertyList,
          null,
          h(P.PropertyList.Item, { label: t("decreeId"), data: true }, reference),
          h(P.PropertyList.Item, { label: t("certificateLanguage") }, t(work.language)),
          h(P.PropertyList.Item, { label: t("signer") }, signerName),
          h(P.PropertyList.Item, { label: t("storedFile") }, h(P.Button, { size: "xs", href: `/api/files/${encodeURIComponent(work.file.id)}/` }, t("download"))),
        ),
        h(P.Inline, null, h(P.Button, { variant: "primary", disabled: pending, onClick: () => setConfirm(true) }, t("issue"))),
      );

    return h(
      P.Stack,
      { gap: "lg" },
      h(P.ProgressSteps, {
        label: t("steps"),
        current: step,
        steps: [{ label: t("stepUpload") }, { label: t("stepScan") }, { label: t("stepSignature") }, { label: t("stepIssue") }],
      }),
      notice ? h(P.Notice, { tone: notice === "stillWaiting" ? "warning" : "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      failure && !confirm ? h(P.Notice, { tone: "danger", onDismiss: () => setFailure(null) }, failure) : null,
      h(P.Panel, { title: t(["stepUpload", "stepScan", "stepSignature", "issueSummary"][step]) }, body),
      h(
        P.ConfirmDialog,
        {
          open: confirm,
          title: t("issueTitle"),
          message: t("issueMessage"),
          confirmLabel: t("issue"),
          cancelLabel: t("cancel"),
          onConfirm: issue,
          onCancel: () => !pending && setConfirm(false),
        },
        failure && confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function DecreeWorkspace({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([api(`/api/cases/${encodeURIComponent(caseId)}/`), api("/api/council/members/")]).then(
          async ([record, members]) => {
            const proceeding = latestProceeding(record);
            let versions = null;
            if (proceeding) {
              try {
                const data = await api(`/api/proceedings/${encodeURIComponent(proceeding.id)}/decision/`);
                versions = Array.isArray(data?.items) ? data.items : null;
              } catch (error) {
                if (error.status !== 405) throw error;
              }
            }
            return { record, members: members.items, proceeding, versions };
          },
        ),
      [caseId],
    );
    const [local, setLocal] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { record, members, proceeding, versions } = state.data;
    const manage = base.canManage(user);
    const current = versions && versions.length ? [...versions].sort((a, b) => b.number - a.number)[0] : null;
    const decree = local || current?.decree || null;
    const eligibility = decreeEligibility(current);
    let content;
    if (versions === null) content = h(P.Notice, { tone: "info" }, t("readMissing"));
    else if (decree)
      content = h(IssuedDecree, { api, lang, manage, decree, decision: current, record, onChange: setLocal });
    else if (record.status === "closed" && current && !eligibility)
      content = h(P.Notice, { tone: "info" }, t("unknownIssued"));
    else if (eligibility) content = h(P.EmptyState, { title: t(eligibility) });
    else if (!manage) content = h(P.Notice, { tone: "info" }, t("adminOnly"));
    else
      content = h(DecreePreparation, {
        api,
        lang,
        record,
        decision: current,
        proceeding,
        members,
        onIssued: (issued) => {
          setLocal(issued);
          setNotice("issued");
        },
      });
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("decree")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      current && !eligibility
        ? h(
            P.Panel,
            { title: t("approvedDecision") },
            h(
              P.PropertyList,
              null,
              h(P.PropertyList.Item, { label: t("decisionType") }, base.typeLabel(current.type)),
              h(P.PropertyList.Item, { label: t("decreeId"), data: true }, decree?.reference || decreeReference(record.number, proceeding)),
              h(P.PropertyList.Item, { label: t("president") }, current.approval?.president || ""),
            ),
          )
        : null,
      !manage && decree ? h(P.Notice, { tone: "info" }, t("adminOnly")) : null,
      content,
    );
  }

  // ---------- Appeals ----------

  function caseAppeals(items, caseId) {
    return (items || [])
      .filter((row) => row && row.kind === "appeal" && row.case_id === caseId)
      .sort((a, b) => String(b.submitted_at || "").localeCompare(String(a.submitted_at || "")));
  }

  function appealResultProblem(form) {
    if (!form.hearing) return "chooseHearing";
    if (!["accept", "decline"].includes(form.result)) return "chooseResult";
    return null;
  }

  // Heard hearings of this case, from session agendas that expose hearing ids.
  function heardHearings(agendas, caseId) {
    const rows = [];
    for (const { session, items } of agendas || []) {
      for (const item of items || []) {
        if (item.case_id === caseId && item.hearing_id)
          rows.push({ id: item.hearing_id, date: session.date, agenda_id: item.id });
      }
    }
    return rows.sort((a, b) => b.date.localeCompare(a.date));
  }

  function AppealDetail({ api, lang, user, row, record, hearings, hearingsKnown, onRecorded }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [form, setForm] = R.useState({ hearing: hearings[0]?.id || "", result: "", explanation: "" });
    const [problem, setProblem] = R.useState(null);
    const [confirm, setConfirm] = R.useState(false);
    const [pending, setPending] = R.useState(false);
    const [failure, setFailure] = R.useState(null);
    const writer =
      base.canManage(user) ||
      (record.assigned_member_id !== undefined ? record.assigned_member_id === user.id : false);
    const pendingAppeal = row.status === "submitted";
    const answers = Object.entries(row.answers || {});
    async function save() {
      setPending(true);
      setFailure(null);
      try {
        await api(`/api/appeals/${encodeURIComponent(row.id)}/result/`, {
          method: "POST",
          body: JSON.stringify({ hearing_id: form.hearing, result: form.result, explanation: form.explanation.trim() }),
        });
        setConfirm(false);
        onRecorded(form.result === "accept" ? "appealAccepted" : "appealDeclined");
      } catch (error) {
        setFailure(base.serverMessage(error, t));
      } finally {
        setPending(false);
      }
    }
    const begin = () => {
      const issue = appealResultProblem(form);
      setProblem(issue);
      if (!issue) setConfirm(true);
    };
    return h(
      P.Stack,
      { gap: "lg" },
      h(
        P.PropertyList,
        null,
        row.applicant_name ? h(P.PropertyList.Item, { label: t("appellant") }, row.applicant_name) : null,
        h(P.PropertyList.Item, { label: t("statusLabel") }, h(P.Badge, { tone: pendingAppeal ? "active" : row.status === "accepted" ? "success" : "neutral" }, t("appeal_" + row.status))),
        row.submitted_at ? h(P.PropertyList.Item, { label: t("submittedAt"), data: true }, base.formatWhen(row.submitted_at, lang)) : null,
        h(P.PropertyList.Item, { label: t("fee") }, row.fee ? t(row.fee.status) : t("unknown")),
      ),
      h(
        P.Panel,
        { title: t("appealStatement") },
        answers.length
          ? h(
              P.PropertyList,
              { layout: "stacked" },
              ...answers.map(([code, value]) =>
                h(P.PropertyList.Item, { key: code, label: base.fieldLabel(row, code, lang) || code }, base.answerText(value, base.translator(lang))),
              ),
            )
          : h(P.EmptyState, { title: t("noAnswers") }),
      ),
      h(P.Notice, { tone: "info" }, t("supplementsPending")),
      pendingAppeal
        ? writer
          ? h(
              P.Panel,
              { title: t("recordAppealResult"), description: t("appealResultHelp") },
              !hearingsKnown
                ? h(P.Notice, { tone: "info" }, t("hearingsUnavailable"))
                : !hearings.length
                  ? h(P.Notice, { tone: "warning" }, t("noHeardHearing"))
                  : h(
                      P.Stack,
                      { gap: "md" },
                      h(
                        P.Field,
                        { label: t("caseHearing"), required: true, error: problem === "chooseHearing" ? t("chooseHearing") : undefined },
                        h(P.Select, {
                          value: form.hearing,
                          disabled: pending,
                          onChange: (e) => setForm({ ...form, hearing: e.target.value }),
                          options: [
                            { value: "", label: t("chooseHearing") },
                            ...hearings.map((x) => ({ value: x.id, label: base.sessionLabel(x.date, base.translator(lang)) })),
                          ],
                        }),
                      ),
                      h(P.RadioGroup, {
                        label: t("appealResult"),
                        layout: "row",
                        value: form.result,
                        onChange: (value) => {
                          setForm({ ...form, result: value });
                          setProblem(null);
                        },
                        options: [
                          { value: "accept", label: t("acceptAppeal"), disabled: pending },
                          { value: "decline", label: t("declineAppeal"), disabled: pending },
                        ],
                      }),
                      problem === "chooseResult" ? h(P.Notice, { tone: "danger" }, t("chooseResult")) : null,
                      h(
                        P.Field,
                        { label: t("appealExplanation"), description: t("appealExplanationHelp") },
                        h(P.Textarea, { rows: 3, value: form.explanation, maxLength: 10000, disabled: pending, onChange: (e) => setForm({ ...form, explanation: e.target.value }) }),
                      ),
                      failure && !confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
                      h(P.Inline, null, h(P.Button, { variant: "primary", disabled: pending, onClick: begin }, t("recordAppealResult"))),
                    ),
            )
          : h(P.Notice, { tone: "info" }, t("appealWriterOnly"))
        : null,
      h(
        P.ConfirmDialog,
        {
          open: confirm,
          title: t(form.result === "accept" ? "acceptAppealTitle" : "declineAppealTitle"),
          message: t(form.result === "accept" ? "acceptAppealMessage" : "declineAppealMessage"),
          confirmLabel: t(form.result === "accept" ? "acceptAppeal" : "declineAppeal"),
          cancelLabel: t("cancel"),
          onConfirm: save,
          onCancel: () => !pending && setConfirm(false),
        },
        failure && confirm ? h(P.Notice, { tone: "danger" }, failure) : null,
      ),
    );
  }

  function AppealsWorkspace({ api, lang, user, caseId }) {
    const R = window.React,
      P = window.Plenix,
      h = R.createElement,
      t = translator(lang);
    const [state, retry] = base.useLoad(
      () =>
        Promise.all([api("/api/applications/"), api(`/api/cases/${encodeURIComponent(caseId)}/`), api("/api/sessions/")]).then(
          async ([apps, record, sessions]) => {
            const recent = (sessions.items || []).slice(0, 24);
            const agendas = await Promise.all(
              recent.map((session) =>
                api(`/api/sessions/${encodeURIComponent(session.id)}/agenda/`).then((data) => ({ session, items: data.items })),
              ),
            );
            const hearingsKnown = agendas.some((a) => (a.items || []).some((item) => "hearing_id" in item));
            return { appeals: caseAppeals(apps.items, caseId), record, hearings: heardHearings(agendas, caseId), hearingsKnown };
          },
        ),
      [caseId],
    );
    const [selected, select] = R.useState(null);
    const [notice, setNotice] = R.useState(null);
    if (state.pending && !state.data) return h(P.Text, { as: "p" }, t("loading"));
    if (state.error) return base.loadFailure(P, h, t, retry, state.error);
    const { appeals, record, hearings, hearingsKnown } = state.data;
    const chosen = appeals.find((row) => row.id === selected);
    return h(
      P.Stack,
      { gap: "lg" },
      h(P.Text, { as: "h1", variant: "title" }, t("appeals")),
      notice ? h(P.Notice, { tone: "success", onDismiss: () => setNotice(null) }, t(notice)) : null,
      h(P.SplitView, {
        label: t("appeals"),
        firstLabel: t("appeals"),
        first: appeals.length
          ? h(
              P.Stack,
              { gap: "sm" },
              ...appeals.map((row) =>
                h(P.Card, {
                  key: row.id,
                  title: row.applicant_name || t("appeal"),
                  meta: [t("appeal_" + row.status), row.submitted_at ? base.formatWhen(row.submitted_at, lang) : null].filter(Boolean).join(" · "),
                  selected: row.id === selected,
                  onOpen: () => {
                    setNotice(null);
                    select(row.id);
                  },
                }),
              ),
            )
          : h(P.EmptyState, { title: t("noAppeals") }),
        second: h(
          P.ReadingPane,
          { label: chosen ? chosen.applicant_name || t("appeal") : t("chooseAppeal"), empty: h(P.EmptyState, { title: t("chooseAppeal") }) },
          chosen
            ? h(AppealDetail, {
                key: chosen.id,
                api,
                lang,
                user,
                row: chosen,
                record,
                hearings,
                hearingsKnown,
                onRecorded: (key) => {
                  setNotice(key);
                  retry();
                },
              })
            : null,
        ),
      }),
    );
  }

  Object.assign(window.CTMCouncil, {
    decreeWords: words,
    decreeTranslator: translator,
    decreeEligibility,
    decreeReference,
    entitledParties,
    releaseStatus,
    decreeStep,
    uploadProblem,
    attestationProblem,
    latestProceeding,
    DecreeWorkspace,
    caseAppeals,
    appealResultProblem,
    heardHearings,
    AppealsWorkspace,
  });
})();
