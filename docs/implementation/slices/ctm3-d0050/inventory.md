# D-0050 inventory: read-only fields and card headers (#217)

Owner decision D-0050 (DESIGN.md §4, study `docs/design/read-only-field-study.html`, ★ preset; PR #216) is
implemented by Plenix as the **default** styles of its read-only field / description list and its card
header (plenix-ds/pds#946). CTM gets it with no CSS of its own, but only where a screen uses those
components. This inventory lists every card or section header and every read-only field display in
`static/ctm/*.js` (main on 2026-11-07), what each uses today, and what has to change.

**How it was made:** a script lists every `P.Panel`, `P.Card`, `P.EntityHeader`, `P.SectionHeading` and
`P.PropertyList` call with its title, icon and the components in its body, grouped by the screen function
that draws it. Hand-built label/value markup and plain-text status were found by search and checked by
reading the code.

## What D-0050 needs from CTM (Plenix components only)

| Level | Plenix component CTM must use | Today in CTM |
|---|---|---|
| Card heading (icon, UPPERCASE, glow, inset line) | `Panel` (or `Card`) with `title` **and** `icon` | `Panel` almost everywhere; a few Panels and headings have **no icon** (marked "(no icon)" below) |
| Group heading (gold, 40 px above) | the group heading pds#946 ships (expected: `SectionHeading` or a FormSection title inside a Panel) | only spouse profiles and the timeline use `SectionHeading`; cards with more than about 8 fields have **no groups yet** (decision asked of ctm3-design-director) |
| Field label and value (navy label, semibold value, porcelain tile) | `PropertyList` / `PropertyList.Item` (the Plenix description list) | `PropertyList` (stacked) in most read views, on the case pages through `CaseReadFields`; a few hand-built "Label: value" texts (G6, G8, G9, G11) |
| Status | `Badge` | `Badge` in most places; **plain text** in G1, G9, G10, G13 |

## Gaps to fix (one PR per area)

| # | Area | Where | Today | Change |
|---|---|---|---|---|
| G1 | Case summary | `council-case.js` CaseSummary (`summaryReadFields`) | Status as plain text ("Active") inside `CaseReadFields`; 10 fields in one card | Status as `Badge`; groups Case / Parties / Marriage once ctm3-design-director decides |
| G2 | Separation | `council-case.js` CaseSeparation, 4 × `CouncilEditablePanel` | **English only**: card titles ("Separation Details", "Civil Divorce", "Restraining Order", "Reconciliation"), every field label, "Edit" and "Save", and "Applicant"/"Spouse" in the initiator value | EN/AR keys; fields that hold a state ("Civil Divorce Status") as `Badge` |
| G3 | Marriage and spouses | `CaseMarriage`, `CaseParties` (spouse Panel without icon), `SpouseContactSection`, `SpouseProfileEditor` | Spouse Panel without icon; spouse profile has many fields in one card | Icon; groups Identity / Contact / Faith and background (ctm3-design-director) |
| G4 | Case record header | `CaseRecordPage` | `EntityHeader` + `SectionHeading` | Already Plenix; check after #946 |
| G5 | Editable case cards | `CouncilEditablePanel` | `Panel` (no icon when the caller passes none); read view through `CaseReadFields`; English "Edit"/"Save" | Every caller passes an icon; EN/AR buttons (with G2) |
| G6 | Session pages | `council.js` SessionList archived parts ("Assigned cases", "Cases presented": Panels without icon); `AgendaItemCard` compact line "Assigned: …" | Panels without icon; hand-built "Label: value" inside a table cell | Icons; the compact line is a table cell, not a field: no change |
| G7 | Home | `CouncilHome`, `HomeStatChart` | `Panel` (with icon) + `PropertyList` + `MetricCard` | Already Plenix |
| G8 | Decision and approval | `council-case.js` DecisionVersion: "Recorded by: …" as `Text` | Hand-built "Label: value" | `PropertyList.Item` |
| G9 | Reports and recordings | `council-media.js` RecordingStatusList: notice state as plain text; ReportRevisionEditor conflict rows: label as secondary `Text` | Plain-text status; hand-built label | `Badge`; `PropertyList.Item` |
| G10 | Appeals | `council-decree.js` AppealDetail: fee status as plain text | Plain text | `Badge` |
| G11 | Applicant portal | `applicant.js` "Case reference: …" as `Text`; `applicant-appeals.js` StartPetition and `applicant-history.js` History: Panels without icon | Hand-built label; Panels without icon | `PropertyList.Item`; icons |
| G12 | Account and settings | `ui-workspaces.js` My Account: `SettingsLayout` / `SettingsSection` / `SettingsRow` (an edit form, not a read view) | Plenix settings page | Settings rows are form rows: they follow the Plenix settings styles; no change unless pds#946 covers them |
| G13 | Historical case entry | `historical-entry.js` | `PropertyList`; status as `t(status)` text | `Badge` for status |
| G14 | Edit forms (#197, #198) | every `Form` inside a Panel (case summary, marriage, separation, spouses) | `Field` + `Columns`; textarea capped at 600 px; grey FormActions band | The Plenix fixes (pds#947, pds#948) arrive by auto-upgrade; CTM keeps `Field` and orders and groups the edit fields exactly as the read fields |

## Every site, by screen

Columns: counts of Panel (P), Card (C), EntityHeader (EH), PropertyList (PL) and SectionHeading (SH);
then each header with its line, icon and title. "(no icon)" marks a header that D-0050 would draw without
its icon.

### App shell, account and settings

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `app.js · App` | 5P 2C 0EH 0PL 0SH | Panel:1761(fields) t("interfaceLanguage") · Panel:1762(hdr-bell) t("notificationLanguage") · Panel:1810(doc-text) t("parties") · Panel:1818(doc-text) t("timeline") · Panel:1907(doc-text) t(part === 1 ? "assignment" : "hearing") · Card:1913(doc-text) row.case_number · Card:1930(calendar) `${t("councilSession") |
| `app.js · CaseFiles` | 0P 1C 0EH 0PL 0SH | Card:907(doc-text) row.name |
| `app.js · ReportDetail` | 2P 0C 0EH 0PL 0SH | Panel:800(doc-text) question?.[lang] ·· question?.en ·· t("response") · Panel:810(document) t("observations") |

### Applicant portal

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `applicant-appeals.js · StartAppeal` | 1P 0C 0EH 0PL 0SH | Panel:59(doc-text) t("title") |
| `applicant-appeals.js · StartPetition` | 1P 0C 0EH 0PL 0SH | Panel:83(no icon) t("title") |
| `applicant-appointments.js · Invitation` | 1P 0C 0EH 0PL 0SH | Panel:71(doc-text) t("instructions") |
| `applicant-assessments.js · Workspace` | 5P 0C 0EH 0PL 0SH | Panel:128(lock) t("files") · Panel:143(lock) t("consent") · Panel:149(lock) t("declaration") · Panel:162(lock) request.title · Panel:167(lock) t("receipt") |
| `applicant-decrees.js · ReleasedDecrees` | 1P 0C 0EH 0PL 0SH | Panel:37(doc-text) t("title") |
| `applicant-files.js · ApplicationFiles` | 3P 0C 0EH 0PL 0SH | Panel:130(doc-text) t("title") · Panel:143(doc-text) requirement[lang==="ar"?"label_ar":"label_en"] · Panel:158(doc-text) t("additional") |
| `applicant-filing.js · FilingActions` | 3P 0C 0EH 0PL 0SH | Panel:130(doc-text) t("title") · Panel:137(doc-text) t("returned") · Panel:147(doc-text) t("declaration") |
| `applicant-history.js · History` | 1P 0C 0EH 0PL 0SH | Panel:60(no icon) t('title') |
| `applicant-lifecycle.js · Actions` | 1P 0C 0EH 0PL 0SH | Panel:49(doc-text) t("title") |
| `applicant-messages.js · Thread` | 2P 0C 0EH 0PL 0SH | Panel:110(doc-text) row.sender · Panel:117(doc-text) t('review') |
| `applicant-payments.js · PaymentHistory` | 1P 0C 0EH 0PL 0SH | Panel:54(doc-text) t("title") |
| `applicant-recovery.js · Recovery` | 2P 0C 0EH 0PL 0SH | Panel:54(doc-text) t("title") · Panel:59(doc-text) t("original") |
| `applicant-requests.js · Requests` | 3P 0C 0EH 0PL 0SH | Panel:56(doc-text) t("instructions") · Panel:57(doc-text) t("questions") · Panel:66(doc-text) t("title") |
| `applicant-responses.js · ResponseEditor` | 1P 0C 0EH 0PL 0SH | Panel:64(doc-text) request.title |
| `applicant-supplements.js · Supplements` | 4P 0C 0EH 0PL 0SH | Panel:108(doc-text) t("title") · Panel:113(progress) t("history") · Panel:115(doc-text) t("ownEntry") · Panel:122(doc-text) t("review") |
| `applicant.js · ApplicationEditor` | 2P 0C 0EH 2PL 0SH | Panel:340(doc-text) fieldLabel · Panel:343(doc-text) `${fieldLabel |
| `applicant.js · StartApplication` | 1P 0C 0EH 0PL 0SH | Panel:215(doc-text) t("start") |

### Council case pages

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `council-case.js · AssessmentsWorkspace` | 2P 3C 0EH 0PL 0SH | Panel:3010(lock) t("assessmentRequests") · Card:3020(doc-text) row.title · Panel:3038(doc-text) t("assessmentReports") · Card:3047(lock) t("restrictedAssessment") · Card:3048(doc-text) row.title |
| `council-case.js · CaseHearings` | 1P 0C 1EH 0PL 0SH | Panel:3581(document) t("outcome") · EntityHeader:3591(calendar) title(current) |
| `council-case.js · CaseMarriage` | 1P 0C 0EH 0PL 0SH | Panel:3905(settings-users) t("churchMarriage") |
| `council-case.js · CaseParties` | 1P 0C 0EH 0PL 0SH | Panel:3456(no icon) spouseHeaderTitle(P |
| `council-case.js · CaseReadFields` | 0P 0C 0EH 2PL 0SH | — |
| `council-case.js · CaseRecordPage` | 0P 0C 1EH 3PL 1SH | EntityHeader:3148(no icon) · SectionHeading:3184(no icon) t(label) |
| `council-case.js · CaseSummary` | 2P 0C 0EH 0PL 0SH | Panel:4285(document) t("caseSummary") · Panel:4301(calendar) t("keyDates") |
| `council-case.js · CaseTimeline` | 0P 0C 0EH 0PL 1SH | SectionHeading:4042(no icon) event.label |
| `council-case.js · CouncilEditablePanel` | 1P 0C 0EH 0PL 0SH | Panel:3941(no icon) title |
| `council-case.js · CouncilVoteRecord` | 1P 0C 0EH 0PL 0SH | Panel:2317(check-square) t("councilVote") |
| `council-case.js · DecisionVersion` | 3P 0C 0EH 8PL 0SH | Panel:2420(doc-text) t("votedOn") · Panel:2445(doc-text) t("votes") · Panel:2499(doc-text) t("approval") |
| `council-case.js · DecisionWorkspace` | 2P 0C 0EH 0PL 0SH | Panel:2625(doc-text) t("earlierVersions") · Panel:2658(doc-text) t("decisionVoting") |
| `council-case.js · ExternalLinkPanel` | 1P 0C 0EH 4PL 0SH | Panel:1661(link) t("externalLinkTitle") |
| `council-case.js · PetitionWorkspace` | 1P 0C 0EH 2PL 0SH | Panel:3695(doc-text) h(P.Inline |
| `council-case.js · RequestComposer` | 1P 0C 0EH 0PL 0SH | Panel:1439(no icon) t("questionCategories") |
| `council-case.js · RequestDetail` | 2P 0C 0EH 10PL 0SH | Panel:2054(doc-text) t("questions") · Panel:2062(doc-text) t(external ? "priestInstructions" : "instructions" |
| `council-case.js · RequestsPanel` | 0P 1C 0EH 0PL 0SH | Card:2124(doc-text) row.title |
| `council-case.js · ReturnedResponsePanel` | 2P 0C 0EH 4PL 0SH | Panel:1937(doc-text) w("Title") · Panel:1943(doc-text) w("Title") |
| `council-case.js · SpouseContactSection` | 0P 0C 0EH 1PL 1SH | SectionHeading:3308(no icon) t("contact") |
| `council-case.js · SpouseProfileEditor` | 0P 0C 0EH 0PL 1SH | SectionHeading:3239(no icon) |

### Council case: decision, decree, appeals

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `council-decree.js · AppealDetail` | 4P 1C 0EH 11PL 0SH | Panel:867(doc-text) t(isLaterFiling(row) ? "laterFilingStatement" : "a · Panel:881(doc-text) t("supplementsTitle") · Card:889(doc-text) base.formatWhen(s.timestamp · Panel:903(doc-text) t("appealOutcome") · Panel:917(doc-text) t("recordAppealResult") |
| `council-decree.js · DecreePreparation` | 1P 0C 0EH 8PL 0SH | Panel:663(doc-text) t(["stepUpload" |
| `council-decree.js · DecreeProtocolGuide` | 1P 0C 0EH 0PL 0SH | Panel:682(doc-text) t("decree") |
| `council-decree.js · DecreeTemplateDraft` | 1P 0C 0EH 4PL 0SH | Panel:445(doc-text) base.typeLabel(decision.type) |
| `council-decree.js · DecreeWorkspace` | 1P 0C 0EH 4PL 0SH | Panel:749(doc-text) t("approvedDecision") |
| `council-decree.js · IssuedDecree` | 2P 0C 0EH 6PL 0SH | Panel:370(doc-text) t("issuedTitle") · Panel:391(doc-text) t("recipients") |

### Council case: reports, recordings, transcripts

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `council-media.js · FilePreview` | 0P 0C 0EH 5PL 0SH | — |
| `council-media.js · RecordingStatusList` | 1P 0C 0EH 5PL 0SH | Panel:1497(triangle-right) t("recordingItem" |
| `council-media.js · ReportDetailTabs` | 4P 0C 0EH 7PL 0SH | Panel:1912(document) t("paperOriginal") · Panel:1918(document) t("recordedOriginal") · Panel:1925(document) label · Panel:1927(document) t("observations") |
| `council-media.js · ReportRecorder` | 1P 0C 0EH 0PL 0SH | Panel:984(doc-text) t("recordingTitle") |
| `council-media.js · ReportRevisionEditor` | 1P 0C 0EH 0PL 0SH | Panel:1357(document) t("latestVersionTitle" |
| `council-media.js · TranscriptViewer` | 2P 0C 0EH 6PL 0SH | Panel:1697(document) t("transcriptText") · Panel:1699(clock) t("segmentsTitle") |
| `council-media.js · TranscriptsPanel` | 1P 0C 0EH 0PL 0SH | Panel:1761(document) `${codeLabel(t |

### Council sessions, Home, review

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `council.js · CouncilHome` | 4P 0C 0EH 10PL 0SH | Panel:3240(calendar) t("upcomingSession") · Panel:3258(calendar) sessionLabel(date · Panel:3313(folder-open) t("myCases") · Panel:3333(settings-users) t("councilMembers") |
| `council.js · HearingOutcomeDialog` | 1P 0C 0EH 0PL 0SH | Panel:2065(progress) t("outcomeHistory") |
| `council.js · HomeStatChart` | 1P 0C 0EH 0PL 0SH | Panel:3181(no icon) |
| `council.js · ReviewDetail` | 3P 0C 0EH 9PL 0SH | Panel:1397(progress) t("previousReturns") · Panel:1407(attachment) t("manifest") · Panel:1435(doc-text) t("answers") |
| `council.js · ReviewQueuePanel` | 1P 1C 0EH 0PL 0SH | Panel:1310(doc-text) t("reviewQueue") · Card:1328(doc-text) row.case_number ·· t("unnumbered") |
| `council.js · SessionAnswers` | 1P 0C 0EH 0PL 0SH | Panel:2397(event_available) t("sessionAnswers") |
| `council.js · SessionList` | 2P 0C 0EH 0PL 0SH | Panel:1752(no icon) t("assignedCases") · Panel:1759(no icon) t("casesPresented") |
| `council.js · SessionWorkspace` | 0P 0C 1EH 0PL 0SH | EntityHeader:2729(calendar) sessionLabel(session.date |

### External priest report

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `external-report.js · ExternalReportPage` | 1P 0C 0EH 5PL 0SH | Panel:264(doc-text) t("instructions") |

### Historical case entry

| Screen | Components | Headers (line, icon, title) |
|---|---|---|
| `historical-entry.js · Workspace` | 0P 0C 0EH 9PL 0SH | — |

## After Plenix ships pds#946

ctm3-design-critic checks every screen above against DESIGN.md §4 and the study's ★ preset, with EN/AR desktop screenshots of fictional data on #217.

— ctm3-frontend-engineer
