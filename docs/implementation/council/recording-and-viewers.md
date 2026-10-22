# Council recording, transcription hand-off and evidence viewers

Module: `static/ctm/council-media.js` (loads after `council-decree.js`). Tests: `tests/frontend/council-media.test.cjs`. Branch `work/claude-council`, PR #6.

## Report audio recording

Where: Case → Reports → Completed reports → an interview report → **Recording** tab, and inside the interview answer form (capture mode). One recording covers the whole interview; recording is never per question.

| Step | Behavior |
|---|---|
| Notice | A checkbox ("I told the person that this interview is being recorded, and they understood.") must be ticked before Start. Submission sends `notice_recorded: true`. |
| Capture | Browser `MediaRecorder` with the first supported of `audio/webm;codecs=opus`, `audio/webm`, `audio/mp4` (Safari/iOS), `audio/ogg;codecs=opus`. Start, Pause, Resume, Stop; elapsed time excludes pauses. |
| Safety | A chunk is written to IndexedDB (`ctm-council-recordings`) every 5 seconds and on page hide. A reload, crash or closed tab keeps the captured audio; the Recording tab then shows it as recovered for review, submission or discard. A microphone/device interruption stops the recording and keeps what was captured. A screen wake lock is requested while recording (where supported). Leaving the page during recording asks for confirmation. |
| Playback | Plenix `MediaPlayer` (audio) on a local object URL of the captured audio. |
| Submission | Upload the original (`POST /api/files/`, category `REC`, council-only, context `report:{id}`) → wait for the automatic safety check (`/api/files/{id}/status/`) → `POST /api/recordings/` with `report_id` and `notice_recorded` → `POST /api/recordings/{id}/finalize/`, which queues transcription. Each completed step is remembered locally so a retry never re-uploads. Local audio is deleted only after finalize succeeds. |
| Capture during interview | The interview answer form records without submitting. When the interview is saved, the local audio moves from the request to the new report, where it is submitted. |
| Errors | Permission blocked, no microphone, microphone busy, insecure (non-HTTPS) page, unsupported browser, size limit, upload failure (server text shown), safety check rejected or still pending. In every failure the audio stays on the device. |

Original audio is never altered: the uploaded bytes are the captured container as recorded.

## Transcription

Submission calls the existing finalize route, which creates the transcription processing run and outbox job exactly once. There is no read route yet for recordings, processing state, retries or transcript versions, so the **Transcripts** tab states that status is not available and that the original audio is stored. Contract requested on issue #2 as D20 (recordings list with processing state, retry creating a new run, transcript versions with the review gate). The agreed language/version behavior (original, mixed, English and Arabic versions; review before wider visibility; edits preserved) is left to that contract; the UI does not invent it.

## Report revisions (D19)

Where: Case → Reports → Completed reports → a report → **Report** tab. Contract: backend PR #7 (checked by reading code at `d724ba5`). Council report rows carry `author_id`, `author`, `submitted_at`, `method` and `can_revise`. `GET /api/reports/{id}/revisions/` lists every version, newest first, and `POST` with `{answers, observations}` appends one.

- **Authority:** the Revise button appears only when the row has `can_revise: true` (literal) and the newest version is being viewed. Authority is never inferred from role, author ID or name. When the flag is `false`, the tab says only the original council author can revise while the case and proceeding are open. On a server without the flag (current main), it says revising waits for report authorship.
- **Editor:** a Plenix Form with one Textarea per request question (EN/AR wording from the request's own question data, unchanged) plus council observations. Files and other non-text answers are carried into the new version exactly. Unanswered questions stay absent unless text is entered.
- **History:** each save creates a new version; nothing is overwritten or removed. The version picker shows every version with its date and author. Further investigation is still a separate linked follow-up report.
- **Stale state:** the write route has no expected-version check, so before saving the editor re-reads the history. If someone saved a newer version after editing began, it stops, keeps the text, and offers "Save my text as a new version" or "Discard my changes". A server-side check is requested on #2.
- **Failures:** on a 403 the server's message is shown, the text stays visible to copy and Save is hidden. Other failures show the server's message and keep the text for retry. Unsaved text triggers the browser's leave-page warning. "No change" is caught before any request.

Testing:

- **Unit and fixture:** 97 frontend tests (authority, payload, stale order, question order, refresh after refusal). Fixture (`--contract=pr7`) in the built-in Chromium browser covers the same flows with simulated failures.
- **Actual backend, isolated:** backend #7 at `db6dfa3` merged locally (not pushed) with this branch, Python 3.12.11 (uv 0.8.22) and PostgreSQL 16.11 on 127.0.0.1 only, synthetic accounts, approved question bank loaded by the backend's own `seed_reference`, no operational data. Full backend suite on that database: 435 passed, 2 skipped. A local-only HTTP acceptance test of the exact calls the UI makes (7 passed): only the assigned member author gets `can_revise`; a revision appends v2 and keeps v1 and the structured answer; admin, secretary and president get 403 with a readable `detail`; reassignment and case closure withdraw authority; applicant-authored reports are not revisable; two saves from the same base both succeed (no server version check).
- **Actual backend, browser:** Django dev server with a server-side session for the synthetic member. Verified author fields, no-change catch, save (v2), stale detection against a real save from a second tab (v3) then forced save (v4), refusal after real reassignment (server text shown, text kept, Save hidden, Revise removed after refresh), secretary and applicant-authored rows not revisable, and Arabic RTL at 390 px with screenshots: no overflow, no inline styles.
- **Fixed after real-backend testing:** answers now follow the request's question order (PostgreSQL does not keep JSON key order); rows refresh after a 403 so Revise disappears; English question wording and answers inside the Arabic page are direction-isolated so punctuation stays in place.
- **Observed backend facts:** members lose the case from their lists once reassigned. `seed_reference` loads English wording only, so Arabic pages show English question wording (correct fallback). The revision route doesn't validate answer shape (the original completion does); no file access derives from report answers. Reported on #2.

## Revision conflicts and safe retry (C-02)

Contract (backend #7 `1ce1259`, `tribunal/api.py` `report_revision` and `endpoint()`, `services/reports.py` `revise_report`): `POST /api/reports/{id}/revisions/ {expected_version, answers, observations}`.

| Server answer | Editor behaviour |
|---|---|
| `201 {id, version}`, a new save **or** an exact replay (same author, `expected_version`, answers and observations; jsonb key order immaterial) | Saved as version N; kept text cleared. |
| `409 {"error":"version_conflict","current_version":N}` or `409 {"error":"conflict"}` (write race) | Re-read history. If the newest version is exactly this save (the replay rule), it is a confirmation. Otherwise: warning with the author of version N; text kept; Save withheld; **Show version N** (read-only, in place); **Save my text as a new version** (confirmation names version N+1, then sends `expected_version: N`); **Discard my changes** (confirmation). Never resubmitted automatically. |
| No reply (network failure) or 5xx | Not reported as saved. Text kept; the exact request is kept; **Try again** resends it unchanged (no early history check, which would misread our own stored save as a conflict). If the text was edited meanwhile, the next save recognises the earlier stored save, rebases on it and says later edits are not yet saved. |
| `403 {detail}` | Server reason + "not allowed"; text kept to copy; Save withheld; rows refresh so Revise disappears. |
| `422 {messages}` | Server messages + "correct the text and save again"; Save stays. |
| `401` | Session ended: sign in again in a new tab, then save here; text stays while the page is open. |
| `404` | No longer available; text kept to copy; Save withheld. |

Expected version is always the version the edit is based on. S10 retention (page memory only), the refresh warning and author-only rules are unchanged.

## Evidence viewers

Case → Evidence and Case → Documents (council). Split list/detail, optional earlier versions, load more.

| File | Viewer | Route |
|---|---|---|
| Image | Plenix `DocumentViewer` (images) and a full-screen `MediaViewer` across the section's images | `/api/files/{id}/?view=1` |
| Audio | Plenix `MediaPlayer` (audio) | `/api/files/{id}/` (authorized, byte ranges) |
| Video | Plenix `MediaPlayer` (video) | `/api/files/{id}/` |
| PDF | Opens the authorized inline route in the browser's PDF viewer; the embedded Plenix `DocumentViewer` (PDF.js) is used automatically once `window.CTM_PDF_VIEWER = { moduleUrl, workerUrl }` is configured | `/api/files/{id}/?view=1` |
| Word | Download only | `/api/files/{id}/` |

Only `/api/files/…` routes are ever used; a listing URL that is not an `/api/files/` route is ignored and the id route is used instead. No storage key or object path appears in the client.

## Browser limitations

- Microphone needs HTTPS (or localhost) and user permission. Blocked permission must be re-allowed in browser settings.
- iOS Safari records `audio/mp4`; backgrounding the browser, a phone call or locking the screen can interrupt capture. The UI keeps captured audio and shows the interruption, but cannot continue the same recording after an OS interruption; continuing would need a second recording, which the whole-report rule does not allow, so the user submits what was captured or discards it.
- Firefox/Chrome produce WebM; WebM written in chunks may lack a duration header, so some players show the length only after playing to the end.
- Private browsing or blocked site storage prevents the local copy; the page then warns that the tab must stay open until submission.
- Recordings above 500 MB (WebM/MP4) or 100 MB (Ogg) are blocked by the current server limits; long recordings need the resumable upload requested as D21.
- Audio is kept on the device until submitted: on a shared computer, submit or discard before leaving.
- The embedded PDF viewer is unavailable because of a Plenix 0.58.0 CDN defect (PDF.js not published, and a loader path that resolves against the app origin). See [pdf-viewer-cdn-defect.md](pdf-viewer-cdn-defect.md). Authorized browser PDF viewing is used until the design system is fixed.

## Evidence of testing

**Fixture only (not actual-backend acceptance):** `node scripts/council_fixture.cjs <port> member --contract=pr7` in the built-in Chromium browser, with real Plenix CDN components and a real `MediaRecorder` fed by a synthetic oscillator as the microphone. Verified: notice required; permission-denied message; recording with pause/resume (timer stable while paused); playback (`readyState` 4); chunks in IndexedDB; recovery after reload; submission order and exact payloads; local audio cleared after finalize; interruption keeps audio; upload failure shows the server message and keeps audio; interview capture moves to the saved report; image, full-screen viewer, audio playback from the authorized route, PDF and Word fallbacks; Arabic RTL at 390 px with no overflow or application inline styles.

**Not yet accepted against the real backend:** actual upload/scan with ClamAV, real `create_recording`/`finalize` against PostgreSQL, the transcription worker, real iOS/Android devices and microphones, long recordings, and range playback through Django. Governance integration should run these with the combined build.

## Open dependencies

D19 server-side expected-version check on report revisions (UI done, see above), D20 recordings/transcript read and retry (published in PR #7, UI not yet built), D21 recording category, worker format acceptance, resumable upload, duration/notice detail (issue #2); PDF.js packaging (issue #4). OCR stays with the backend stream; council processing status and retry displays will follow D20.

Evidence files: [`evidence/d19_backend_acceptance.py`](evidence/d19_backend_acceptance.py) (D19 + C-02 server contract; copy into a backend #7 checkout's `tests/` to rerun), [`evidence/d19-arabic-editor-390px-real-backend.jpg`](evidence/d19-arabic-editor-390px-real-backend.jpg), and C-02 screens [`c02-en-390-conflict-real-backend.jpg`](evidence/c02-en-390-conflict-real-backend.jpg), [`c02-ar-390-conflict-real-backend.jpg`](evidence/c02-ar-390-conflict-real-backend.jpg), [`c02-ar-390-unconfirmed-save-real-backend.jpg`](evidence/c02-ar-390-unconfirmed-save-real-backend.jpg) (synthetic data, restricted `ctm_app` role).
