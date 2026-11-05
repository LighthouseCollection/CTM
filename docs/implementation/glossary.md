# CTM terminology glossary (English / Arabic)

One term per concept, used the same way in every module, email, PDF and
notice. Agents reuse these before adding new `t()` keys. Arabic below is
copied from the existing CTM dictionaries (`static/ctm/*.js`, main `9fa6386`);
do not improvise Arabic for institutional or doctrinal wording - new terms go
through the approved translation workflow and the institutional prompt.
Status `Accepted` = from the contract/decisions; `In code` = current code
label, not yet confirmed against the contract.

| Concept | English | Arabic | Source | Status / note |
|---|---|---|---|---|
| Council session | Council Session YYYY-MM-DD | جلسة المجلس | Contract; `councilSession` | Accepted |
| Hearing title | Case Hearing of [first last] vs. [first last] | جلسة نظر قضية … ضد … | Contract; `caseHearingOf`, `versus` | Accepted |
| Send now | Send Immediately | إرسال فوري | Contract; `sendImmediately` | Accepted |
| Send later | Send after council session | الإرسال بعد جلسة المجلس | Contract; `sendAfterSession` | Accepted |
| Appeal | Appeal | استئناف | `appeal` | In code |
| Withdraw (applicant) | Withdraw my filing | سحب طلبي | `withdraw` | In code |
| Cases (nav) | Cases | القضايا | Locked nav; `cases` | Accepted |
| Home (nav) | Home | الرئيسية | Locked nav | Accepted |
| Search (nav) | Search | البحث | Locked nav | Accepted |
| Archived (nav) | Archived | الأرشيف | Locked nav | Accepted |
| Statistics and Reports (nav) | Statistics and Reports | — | Locked nav | Code shows "Reports" / التقارير, the same as the case Reports section (DR-007) |
| Reports (case section) | Reports | التقارير | Locked nav | Accepted |
| Communications (case) | Communications | — | Locked nav | Code shows "Email" / البريد الإلكتروني (DR-007) |
| Parties (case overview) | Parties | — | Locked nav | Code shows "Spouses" / الزوجان (DR-007) |
| Petition | Petition | الطلب | Locked nav; `petition` | Accepted |
| Evidence | Evidence | الأدلة | Locked nav | Accepted |
| Calls (case) | Calls | المكالمات | `calls` | Proposed (D-0012, #50) |
| Hearings | Hearings | مناقشات القضية | Locked nav; `hearings` | Arabic reads "case discussions" - confirm |
| Decision | Decision | القرار | Locked nav | Accepted |
| Decree | Decree | الشهادة | Locked nav; `decree` | Arabic reads "certificate" - confirm against decree wording |
| Timeline | Timeline | التسلسل الزمني | Locked nav | Accepted |
| Case audit | Case Audit | سجل القضية | Locked nav | Accepted |
| Professional Assessments | Professional Assessments | — | Contract | Arabic to confirm |
| Case number | YYYYMMDD-## | (Latin digits, isolated in RTL) | Contract | Accepted |
| Decree id | DCR-YYYYMMDD-## (appeal: -A1) | (Latin, isolated in RTL) | Contract | Accepted |

## Tone

- Notices and errors: calm, plain, no blame; say what happened, why, and the
  next step. Destructive or irreversible actions name exactly what will happen.
- Formal, commonly understood Egyptian-facing Arabic, as approved.
- Buttons name the action and its object ("Issue decree", "Return application").
