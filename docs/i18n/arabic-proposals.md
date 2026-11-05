# Arabic proposals for owner review

New Arabic UI words, added by `ctm3-i18n-engineer` when they ship (decision
D-0012). The owner reviews in batches; a correction becomes a decision and a
glossary change. Never delete rows: mark them `approved` or `corrected`.

| Date | Key | English | Proposed Arabic | Why | Issue / PR | Status |
|---|---|---|---|---|---|---|
| 2026-11-04 | `calls` | Calls | المكالمات | Case section for the council call log; plain MSA plural of مكالمة, same pattern as `notes` / ملاحظات | #50 | proposed |
| 2026-11-04 | `backNewApplications` | Back to New Applications | العودة إلى الطلبات الجديدة | Reuses `newApplications` (الطلبات الجديدة) with the existing "العودة إلى …" back-link pattern | #50 | proposed |
| 2026-11-04 | `linkEmailUnavailable` | Email delivery is not available yet, so the link was not sent and is not shown here. Use the paper form instead: open or download the printed request below. | البريد الإلكتروني غير متاح بعد، لذلك لم يُرسل الرابط ولا يُعرض هنا. استخدم النموذج الورقي بدلًا من ذلك: افتح الطلب المطبوع أدناه أو نزّله. | D-0030; reuses `printTitle` (الطلب المطبوع) and the existing "غير متاح" unavailable pattern | #55 | proposed |
| 2026-11-04 | `issueMessage` | A link valid for 30 days is created. It is never shown here; CTM sends it by email once email delivery is available. | يُنشأ رابط صالح لمدة 30 يومًا. ولا يُعرض هنا أبدًا؛ ويرسله CTM بالبريد الإلكتروني عندما يصبح البريد متاحًا. | D-0030 rewording of the existing key | #55 | proposed |
| 2026-11-04 | `externalIssued` | Private link issued. It was not sent: email delivery is not available yet. | صدر الرابط الخاص. ولم يُرسل: البريد الإلكتروني غير متاح بعد. | D-0030 rewording of the existing key | #55 | proposed |
| 2026-11-05 | `caseClosedReadOnly` | This case is closed and read-only. | هذه القضية مغلقة ومتاحة للقراءة فقط. | Same pattern as the session key `closedReadOnly` (هذه الجلسة مغلقة ومتاحة للقراءة فقط.) with القضية | #97 | proposed |
| 2026-11-05 | `caseActions` | Case actions | إجراءات القضية | Screen-reader name of the case page ActionBar; إجراءات + القضية | #97 | proposed |
| 2026-11-05 | `moreActions` | More actions | مزيد من الإجراءات | Screen-reader name of the EntityHeader More menu | #97 | proposed |
