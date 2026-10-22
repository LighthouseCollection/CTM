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

# Slice 2 — report requests and Decision & Voting

Module `static/ctm/council-case.js` (loads after `council.js`, extends `window.CTMCouncil`), tests `tests/frontend/council-case.test.cjs`.

| Area | Behavior | Endpoints used (existing) |
|---|---|---|
| Reports → Requests tab | Completed reports stay in the shell's existing reader (first tab). Requests tab: split list/detail. Assigned manager or admin/secretary composes an applicant intake: subject (registered parties only), title, language (English / Arabic / both), questions grouped by reusable category with latest published version, foundational questions always included and locked, optional follow-up parent report and instructions. Saved as draft, then the frozen question snapshot is shown before **Send to applicant** (confirmation). Arabic/both is blocked when any question sent lacks approved Arabic wording. Members see read-only notice. | `GET /api/report-questions/`, `GET/POST /api/cases/{id}/requests/`, `POST /api/requests/{id}/send/` |
| Decision & Voting (new case nav item under Decision) | Writer records a version: exact prototype type catalog (8 server types; withdrawal/reconciliation excluded), grounds required, per-party entitlement required for granting types, Nullity requires both certificate, conditional types require stated conditions. Shows what is being voted on first. Full council roster with latest vote per member and tally. Own vote for all council; admin/secretary may record on behalf. President approves own; admin/secretary records President's approval (President selected). Petition Denied approval shows the closing warning. Revised version notice: earlier votes/approval stay with earlier version. | `POST /api/proceedings/{id}/decision/`, `POST /api/decisions/{id}/vote/`, `POST /api/decisions/{id}/approve/`, `GET /api/council/members/`, `GET /api/cases/{id}/` |

Evidence: `node --test tests/frontend/` 28 passed (catalog test reads `decisions.py` and `prototype-decision-types.json` so drift fails). Browser on synthetic fixture (same caveat as slice 1): empty composer blocked with no request; Arabic request blocked without approved wording; draft posts exact payload; frozen questions shown; send confirmation; decision Nullity entitlement rule blocked before request; recorded version shown first; own vote and on-behalf vote payloads (`member_id` only on behalf); on-behalf approval posts `president_id`; denial warning; member: no entitlements for denial, own vote only, no approval control, no write controls on another member's case; EN/AR at 1280 and 390 px with RTL, zero `[style]`, no overflow.

Not implemented on purpose: external priest requests (no priest-facing page or email delivery yet); interview conducted by the manager (D7); Arabic decision-type labels (not approved — English approved label shown with notice); voting is not blocked after approval (no contract rule).

Additional backend dependencies (posted on #2): D7 interview kind should not notify the applicant on send, or a separate "record interview" command; D8 decision read `GET /api/proceedings/{id}/decision/` → `{items:[{id, number, type, grounds, entitlements, conditions, actor, timestamp, votes:[{member_id, choice, actor_id, timestamp}], approval:{president_id, president, actor, timestamp}|null}]}`; D9 topic groups and Arabic category names in `/api/report-questions/`; D10 external priest capability page/email delivery; D11 request projection fields (subject party id/name, language, created/sent time, parent report, author).

## Remaining council work

Hearing outcome and applicant update editor, testimony scheduling, report intake authoring (question bank selection), decision/voting, decree preparation/issue/release, appeals, communications refinements, case overview pages.
