# UI reconciliation: session slice

Base reviewed: `104e4fd06c6cde1ae4cdb76ba5f9ab47b8d336fc`. The owner-approved current UI requirements override older architecture text that described a single navigation scope or undecided split destinations.

## Completed

- `static/ctm/app.js`, `SessionAttendance`: removed the disabled Not recorded radio. Unset attendance selects neither Present nor Absent; no data is fabricated. Retained the existing persistence/capability checks and error rollback. Uses documented Panel.collapsible and a user icon.
- `static/ctm/council.js`, `SessionWorkspace`: two agenda tables, each under its own heading, without Panel/Card nesting. Existing assignment, hearing, testimony, cancellation and case-opening controls remain capability-gated. The compact agenda renderer preserves assigned-member context and testimony details. Table mode fill does not add unnecessary pagination for these returned-array agendas.
- `scripts/browser_attendance_ui.py`: first failed against the removed-option regression; then failed against missing agenda tables. Passes after correction, including collapse/reopen selection preservation, adding an assignment candidate and opening the assignment dialog. Run against a fresh synthetic fixture: `node scripts/council_fixture.cjs 18859 secretary --contract=pr7 --decree-read`, then `.venv/Scripts/python.exe scripts/browser_attendance_ui.py`.
- All 14 split workspace checks pass; 189 frontend unit tests pass. Syntax and diff whitespace checks pass. These checks do not establish backend authorization, complete visual acceptance or production readiness.

## Unfinished UI

`ui-reconciliation-register.json` enumerates all 45 approved-map screens, their exact documented gaps and the evidence level for this pass. It is a work register, not a completed interactive audit. Current per-screen content/control review is unfinished. Required next UI work includes responsive/RTL checks, factual-page presentation, account/admin controls, audit/search filters and session metadata. Do not substitute invented approved content or mark missing API projections as verified blockers without inspecting the endpoint.

The next confirmed session UI review must cover narrow-screen action wrapping, Arabic heading/control strings, empty/closed sessions, and all hearing/testimony dialogs. The current fresh fixture covers a planned session and assignment-dialog opening only.

## Blocked / exact dependencies

- Account photos/editing: backend/schema owner must approve and expose the account photo relationship, upload and authorized read contract. Existing legacy static-person mapping/migration is not approved or adopted here.
- CDN-wide avatar background/border and spacing: the pinned CDN owner must provide/document the shared correction; no arbitrary local CSS values were introduced.
- Live-service acceptance: payment/email/scan/storage providers remain their owners' dependencies; not UI implementation completion.
- Unsaved report navigation: council issue #3 owns the fix; QA #15 waits for its integrated successor SHA. This slice does not edit reports, navigation guards or expected_version.

## Awaiting acceptance

Independent combined-backend review, English/Arabic/RTL/mobile visual acceptance, all restored agenda action journeys, and integration of this UI slice. No merge, deployment, migration or backend contract change.


## Responsive/RTL follow-up

Confirmed and fixed: at 390px, case navigation previously occupied 220px and squeezed content to 170px. SecondaryPane now uses documented detailOpen/onBack: narrow screens open full-width selected content, Back shows full-width case navigation, and selecting the same section returns to content. Desktop retains independent main rail/case pane behavior. SecondaryPane control strings and attendance Panel collapse/expand strings are localized in Arabic; no CSS dimensions or custom layout were added.

The synthetic fixture served every static file as JavaScript, so the SVG logo failed image decoding and appeared unavailable in screenshots. Static MIME types now match the requested asset; this is a test-harness correction, not a claim that the production logo was broken.

Fresh regression evidence: browser_case_responsive.py passes English/Arabic at 390 and 1253px, including Back/reselect and no page overflow. browser_session_responsive.py passes English/Arabic at 390, 768 and 1253px, including logo decoding, localized collapse/reopen, semantic direction and content bounds. Both product regressions failed before correction. Independent navigation, all 14 split workspaces, attendance/agenda and all 189 frontend unit tests still pass.

Remaining: responsive/RTL interactions for other case section contents and dialogs, long-text content stress, Arabic institutional-content review and actual-backend acceptance. The register remains an unfinished full-screen audit; these matrix checks cover the session shell and case navigation only. No report guard, expected_version, schema or provider changes.

## Case-section and Search follow-up

Read-only synthetic matrix now covers all ten case split sections in English/Arabic at 390/1253px (40 combinations): Communications, Reports, Hearings, Evidence, Documents, Professional Assessments, Decision & Voting, Appeals, Decree and Case Audit. Each exposes table/detail regions within viewport bounds without page overflow or browser errors. Reports/evidence/documents/audit selection is exercised. This does not accept every dialog, long-text state or backend action.

Confirmed Search defect: the initial view, pending request and failed request all presented no matching documents. SearchWorkspace now uses existing translated help/loading/load-failure/no-match messages for the corresponding states and clears stale results on a new search. No API/payload changes. A held-response browser regression failed before correction, then passed initial/loading/result/empty/error transitions and keyboard Enter selection in English/Arabic at 390/1253px. The actual index/advanced-filter contract remains outside this synthetic test.

The 45-screen JSON register now records these specific verification levels while retaining unfinished acceptance status and existing documented gaps. Unit evidence remains 189 frontend tests passing; independent desktop navigation and original split-view regressions pass. Both UI fixes and test coverage are on PR #19; no merge or deployment.
