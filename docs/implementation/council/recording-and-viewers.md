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
- The embedded PDF viewer is unavailable until PDF.js files are packaged (issue #4); browser PDF viewing is used meanwhile.

## Evidence of testing

**Fixture only (not actual-backend acceptance):** `node scripts/council_fixture.cjs <port> member --contract=pr7` in the built-in Chromium browser, with real Plenix CDN components and a real `MediaRecorder` fed by a synthetic oscillator as the microphone. Verified: notice required; permission-denied message; recording with pause/resume (timer stable while paused); playback (`readyState` 4); chunks in IndexedDB; recovery after reload; submission order and exact payloads; local audio cleared after finalize; interruption keeps audio; upload failure shows the server message and keeps audio; interview capture moves to the saved report; image, full-screen viewer, audio playback from the authorized route, PDF and Word fallbacks; Arabic RTL at 390 px with no overflow or application inline styles.

**Not yet accepted against the real backend:** actual upload/scan with ClamAV, real `create_recording`/`finalize` against PostgreSQL, the transcription worker, real iOS/Android devices and microphones, long recordings, and range playback through Django. Governance integration should run these with the combined build.

## Open dependencies

D19 report authorship/`can_revise` (revisions), D20 recordings/transcript read and retry, D21 recording category, worker format acceptance, resumable upload, duration/notice detail (issue #2); PDF.js packaging (issue #4). OCR stays with the backend stream; council processing status and retry displays will follow D20.
