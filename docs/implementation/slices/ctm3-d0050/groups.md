# D-0050 field groups (ctm3-design-director, 2026-11-07)

Issue: LighthouseCollection/CTM#217. Rule: DESIGN.md §4 "Read-only fields and card headings"
(D-0050). Any card with more than about 8 fields gets group headings: the Plenix group heading
from plenix-ds/pds#946 (13 px, medium, gold, sentence case, no line, 40 px above). Read mode and
edit mode use the **same groups, in the same order, field for field**. Field order inside a group
is as listed. Groups never change what a role may see. A field the role cannot see is left out,
and a group left with no fields is left out too.

Counted on main 2026-11-07, in read mode, from `static/ctm/*.js`.

| Card (file) | Fields | Groups (EN / AR) and fields, in order |
|---|---|---|
| Case summary (`council-case.js` `CaseSummary`, `summaryReadFields`) | 10 | **Case** / **القضية**: case number, filing date, status (Plenix status badge), assigned council member, last hearing date. **Spouses** / **الزوجان** (existing `parties`): applicant, respondent. **Marriage** / **الزواج** (existing): marriage duration, children, reason for divorce |
| Spouse profile, one card per spouse (`council-case.js` `CaseParties`, `SpouseProfileEditor`, `SpouseContactSection`) | 17 | The four existing sections become groups inside one card. **Personal details**: other names, place of birth, nationality, awareness of application. **Contact**: address, mobile, email, immigration status, residing with. **Career**: education, year of graduation, occupation. **Church affiliation**: denomination, bishop, diocese, parish, father of confession. Card heading = the spouse's name and role; the photo stays in the card header |
| Marriage (`council-case.js` `CaseMarriage`) | 9 | **Church marriage** / existing `churchMarriage`: church marriage date, marriage duration, officiating priest, church name, church location, diocese. **Outside the Coptic Church** / **خارج الكنيسة القبطية** (proposal): married outside the Coptic Church, denomination, date of that marriage |
| Request detail (`council-case.js` `RequestDetail`) | 9 | **Request** / **الطلب** (proposal): title, method, subject, language. **Record** / **السجل** (proposal): prepared by, created at, parent request. The questions stay in their own card below |
| Applicant filing answers (`applicant.js`) | many | Groups are the server's question sections, in server order (unchanged); no new headings |

Cards with 8 fields or fewer get **no** group headings: separation, key dates, contact on its own,
decree, session facts, hearings, settings / configuration rows, My Account, external priest report,
historical entry.

New strings: "Case", "Outside the Coptic Church", "Request" and "Record". Each needs EN and AR, and
the Arabic goes to `docs/i18n/arabic-proposals.md` until the institution confirms it.
