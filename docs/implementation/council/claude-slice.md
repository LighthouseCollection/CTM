# Council workspace — Claude stream

Branch `work/claude-council`, draft PR #6, issue #3. UI only: no backend, migration or protected build-spec edits. Status 2026-10-21: awaiting governance review.

## Modules

| File | Contents |
|---|---|
| `static/ctm/council.js` | `window.CTMCouncil`: shared helpers (translator, `useLoad`, server messages, dates in Los Angeles time), council Home, completeness review, Tribunal Sessions (create, agenda, assignment, present, attendance slot, hearing outcome, testimony, close), Search. |
| `static/ctm/council-case.js` | Reports → Requests (intake and in-person interview), Decision & Voting, Case Audit, call records, Professional Assessments, Spouses, case Hearings. |
| `static/ctm/council-decree.js` | Decree (signed PDF, safety check, signature record, issue, release/withdraw) and Appeals. |
| `static/ctm/app.js`, `tribunal/templates/tribunal/shell.html` | Shell hook (separate commits): load the three modules before `app.js`; route council pages; enable locked-navigation items only when the module is loaded; `api()` errors carry `status`/server JSON; `FormData` bodies keep the browser's multipart type. |
| `tests/frontend/council*.test.cjs` | `node --test tests/frontend/` (56 tests). Catalog test reads `decisions.py` and `prototype-decision-types.json`. |
| `scripts/council_fixture.cjs` | Synthetic browser fixture: `node scripts/council_fixture.cjs [port] [role] [--contract=pr7] [--decree-read]`. Not a real-API, database or provider-login test. |

## Behavior by area

| Area | Behavior | Existing endpoints |
|---|---|---|
| Home | Upcoming sessions, needs attention (unread notifications; completeness queue for admin/secretary), own open cases. No analytics. | `/api/dashboard/`, `/api/cases/`, `/api/notifications/` |
| Completeness review | Queue and split reader; applicant, submission time, bound questionnaire labels, submitted manifest (download only after clean scan), previous returns; Accept (confirm) / Return with required instructions. | `/api/applications/?state=awaiting_review`, `/review/` |
| Sessions | One session per date; Part 1 placement and President-authorized assignment; Part 2 placement; formal hearing title; presenter-only Present (attendance hint); recommendations and applicant update (first save sends standard update, revisions silent, history); testimony invitation (LA times, private instructions, response state); close with carryover rules; read-only when closed. | sessions, agenda, attendance, assignment, hear, hearings, outcome, testimony, close |
| Reports | Completed reports (existing reader) and Requests tab: intake to applicant, or interview recorded by the manager (offered only with the PR #7 boundary); category or topic-group view of one selection; foundational questions locked; Arabic/bilingual blocked without approved Arabic wording; frozen snapshot before send/start. | report-questions, requests, send, complete |
| Decision & Voting | Exact catalog (Deferred excluded as a hearing outcome); grounds required; named per-spouse entitlements; nullity and conditional rules; full roster tally; own and on-behalf votes; President approval or recorded approval; denial closing warning; saved versions and earlier versions with PR #7. | decision, vote, approve |
| Decree | Admin/secretary only: store signed PDF (`DEC`, council-only, ≤25 MB), safety check, President signature record, confirmed issue (closes case), release/withdraw per entitled spouse. Template generation stated as unavailable. No replacement workflow. | files, signature, decree, release |
| Appeals | Split list/detail; Accept/Decline against a heard case hearing, optional explanation; consequences stated. | applications, sessions/agenda, appeals result |
| Professional Assessments | Separate section; medical/psychological requests with optional recommended doctors; contents hidden without council-scope release; excluded from ordinary Requests. | requests, reports |
| Communications | Existing messages plus manual call records (who, when with time zone, outcome, notes). | calls |
| Case Audit | Searchable audit events with EN/AR labels for known codes. | audit |
| Search | Split results with server-authorized excerpts; earlier versions optional; server errors shown as returned. | search |
| Spouses / Hearings | Owner-approved "Spouses" wording; add the other spouse (admin/secretary); case agenda appearances. | case detail, parties, sessions |

## Evidence

- `node --test tests/frontend/`: 56 passed.
- Built-in Chromium with the real Plenix 0.58.0 CDN and real modules against the synthetic fixture, in both `main` and `--contract=pr7` modes. Every slice was checked as secretary and as member (and on the assigned/unassigned split). Checks covered: validation blocking with no request sent, exact request payloads, server error text shown, EN/AR at 1280 and 390 px, `dir=rtl`, zero `[style]` attributes, no horizontal overflow, and no console errors apart from the expected 405 decision probe on `main`.
- Python/PostgreSQL: no Python/uv/Docker on this machine; GitHub Actions on PR #6 has passed on each push checked.

## Backend dependencies (issue #2)

D1–D8 and D11 are delivered in backend PR #7 and are consumed when present. Open: D9 Arabic topic/category names and reviewed Arabic wording; D10 external priest page and delivery; D12 decree read inside the decision projection; D13 file scan status; D14 approved decree templates; D15 appeal supplements, disposition and eligible hearings; D16 assessment release status. Backend note from review F27: the server still accepts `deferred` as a decision type.

## Not built on purpose

External priest requests (no capability page or delivery), Arabic decision-type labels (not approved), replacement/clerical decree workflow (removed by contract), Statistics and Reports (needs a valid-denominator definition and aggregates endpoint), timeline/marriage/separation overview pages (no projection yet).
