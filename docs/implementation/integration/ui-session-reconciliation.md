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

