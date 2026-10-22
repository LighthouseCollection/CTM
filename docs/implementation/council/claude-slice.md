# Council workspace — Claude stream, slice 1

Branch `work/claude-council`, issue #3. Status 2026-10-21: draft, awaiting governance review.

## Implemented

| Area | Behavior | Endpoints used (existing) |
|---|---|---|
| Completeness review | Admin/secretary queue panel on Home (locked navigation unchanged). Split list/detail reader of submitted petitions. **Accept** with confirmation; **Return for correction** requires instructions (client check plus existing server rule). Typed instructions are kept if the request fails. Members see no queue. | `GET /api/applications/`, `POST /api/applications/{id}/review/` |
| Tribunal Sessions | List with `Council Session YYYY-MM-DD` and `CSYYYYMMDD` reference. Admin/secretary create a dated session; duplicate date blocked client-side and on server 409. | `GET/POST /api/sessions/` |
| Session agenda | Part 1: admin/secretary place open unassigned cases; record assignment (case manager + authorizing President, both required). Part 2: assigned cases placed by admin/secretary or the shown assigned member. **Present case** only for the assigned member; absent presenter result shown as deferred awaiting manual placement. **Close session** with confirmation that states the carryover rules. Closed session is read-only. | `GET/POST /api/sessions/{id}/agenda/`, `POST /api/cases/{id}/assignment/`, `POST /api/agenda/{id}/hear/`, `POST /api/sessions/{id}/close/`, `GET /api/council/members/`, `GET /api/cases/` |
| Attendance | Existing shell `SessionAttendance` kept; the module supplies fresh attendance/session data after each action so it becomes read-only immediately after close. | `GET/POST /api/sessions/{id}/attendance/` |

All controls are display decisions only; the server enforces permissions. Server validation text is shown verbatim; no success is shown unless the request succeeded.

## Files

- `static/ctm/council.js` — separate `window.CTMCouncil` module (logic + Plenix views, EN/AR words).
- `static/ctm/app.js`, `tribunal/templates/tribunal/shell.html` — small shell hook (separate commit): load `council.js` before `app.js`; delegate Home review panel, `review`, `sessions`, `session` pages; `api()` errors now carry `status` and the server JSON body.
- `tests/frontend/council.test.cjs` — `node --test` logic checks.
- `scripts/council_fixture.cjs` — synthetic contract fixture for browser checks without Python.

## Evidence

- `node --test tests/frontend/council.test.cjs`: 15 passed.
- Browser (built-in Chromium pane, real Plenix 0.58.0 CDN, real `council.js`/`app.js`, **synthetic fixture API — not a real-API, database or provider-login test**): empty return blocked with no request sent; return and accept send the exact payloads; duplicate session date blocked; Part 1 placement and assignment (incomplete form blocked, complete form posts member + president); Part 2 placement; secretary sees no Present button, assigned member does; hearing recorded; close session makes attendance read-only; member sees no review queue, session creation, assignment or close controls; EN/AR at 1280px and 390px: `dir=rtl` in Arabic, zero `[style]` attributes, no horizontal overflow, zero console errors.
- Python/PostgreSQL: this machine has no Python/uv/Docker; GitHub Actions on the branch is the evidence for unchanged backend tests.

## Backend dependencies (posted on #2)

D1 review projection (applicant name, submitted time, manifest, prior returns, questionnaire labels, `can_review`); D2 agenda projection (`hearing_id`, assigned member id/name, party names for the hearing title, `can_present`, testimony); D3 hearing read endpoint with outcome revisions; D4 case capability flags; D5 members/president seed. Additional: D6 — recording a Part 1 assignment does not change the agenda item state, so closing the session marks an assigned Part 1 item "unpresented"; please confirm intended Part 1 completion state.

Until D1 is supplied, answers are shown as stored codes with an explicit notice. Until D2/D3, hearing recommendations/applicant update are not editable from the session view (the existing POST endpoint needs a hearing id the agenda does not return).

## Remaining council work

Hearing outcome and applicant update editor, testimony scheduling, report intake authoring (question bank selection), decision/voting, decree preparation/issue/release, appeals, communications refinements, case overview pages.
