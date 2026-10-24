# External priest report (council C-05)

A priest who knows the marriage writes a free-form report through a private link. No council account is created. Issue #3, PR #6.

## Council side (`static/ctm/council-case.js`)

- **New request → "External priest report":**
  - the spouse named in the request (the priest sees only this name and the case number);
  - the priest's name, which titles the request "Report by Fr. [name]";
  - request language (English, Arabic or both) and instructions to the priest;
  - optionally, an earlier report this one follows up.

  There's no question list.
- **Request detail, "Private link for the priest":**
  - **Issue private link** (with confirmation) sends `{external_name, external_email}` to `POST /api/requests/{id}/send/`.
  - The returned token is shown **once** as a link to copy and kept only in page memory. It's never stored or put in messages or notes. The page says honestly that the server does not email it.
  - **Issue a new link** (confirmation) makes the earlier link stop working.
  - **Cancel request** (`POST /api/requests/{id}/cancel/ {expected_version}`, confirmation) also stops the link.
  - Completed or closed requests show their state with no link controls.
  - **Link status (backend `c377706`):** when request rows carry `external_link`, the panel shows the priest's name, the state (not issued, active, expired, report submitted, cancelled, closed, unavailable) and the expiry for active or expired links. Issue, Reissue and Cancel follow the server's `can_issue`, `can_reissue` and `can_cancel` only. Older servers fall back to the request state.
- **Printed request (backend `6a3f6df`, `c0fc9ae`):** for a priest who prefers paper. Shown to a writer while the request is a draft or sent (with the projection, only when the server allows a link control).
  - **Open printable request** opens `GET /api/requests/{id}/print/` in a new tab (`noopener noreferrer`) for the browser's Print.
  - **Download PDF** fetches `GET /api/requests/{id}/print.pdf` same-origin with `no-store`, saves it as `priest-request-{id}.pdf` from an in-memory copy and releases it. Nothing is kept in browser storage.
  - `503 pdf_unavailable` (renderer missing) and `422` (too long) point to the printable page; a non-PDF reply is never presented as a download; refused, signed-out and network failures have their own messages.
  - The printout carries the saved title, instructions and names with blank lines, never the link or token.
- **Paper response (backend `746e5a4`):** for a sent request, a writer (with the projection, only while the server allows cancel) can record the priest's returned paper.
  - **Record a paper response** → choose the scanned PDF (25 MB or less), the date received (Los Angeles today or earlier) and confirm it is the priest's paper as received.
  - **Upload paper original** posts it to `/api/files/` with `category REPORT`, `request_id` and council visibility (owner NULL, council-only per `6fe7d51`). The server's scan state is shown as reported; **Check again** reads `/api/files/{id}/status/`. A rejected file cannot be used; **Use a different file** starts again (the earlier upload stays on record with the request, as the backend retains it).
  - **Record paper response** (confirmation: the link stops working and the original can't be replaced) posts `{file_id, completion_date, expected_version}` to `/api/requests/{id}/paper-completion/`. Refusals keep the dialog open with the server's reason.
  - An upload awaiting its check is remembered in page memory only, so in-app navigation doesn't lose it; nothing is put in browser storage.
  - Completed reports reloads its list after a paper (or interview) response is recorded.
  - **In Completed reports** a paper report shows the method "Paper original recorded by the council", **Recorded by** (the council member), **Paper received** (the date), and the original in the protected PDF viewer (`/api/files/{id}/?view=1`) with a Download button. It is not transcribed and cannot be revised; a follow-up is a separate request.
- **The submitted report** appears in Completed reports as "Report by Fr. [name]" with its date and method "External source link". The free-form answer is labelled **Written testimony**. It isn't revisable (no council author), and a follow-up is a separate linked report.

## Priest page (`static/ctm/external-report.html` and `.js`)

- **The link** is `/static/ctm/external-report.html#r=<request>&t=<token>`. The fragment is never sent to servers, logs or referrers. The page removes it from the address bar at once, keeps it in memory, and reloads cleanly if another link is opened in the same tab.
- **Calls** go to the existing capability route `/external/reports/{id}/` with `Authorization: Bearer`, `credentials: omit`, `cache: no-store` and `referrerPolicy: no-referrer`.
- **Shows** the request title, case number, named spouse, requested language and instructions, and nothing else.
- **Written testimony:**
  - **Save draft** stores it on the server (`{action:"save", answers:{testimony}}`), and the same link restores it until expiry.
  - **Submit report** (with confirmation) posts `{answers:{testimony}}`.
  - An empty report is not sent.
- **States:**
  - loading;
  - incomplete link (no server call);
  - inactive link (expired, replaced, cancelled, already submitted or closed — the server reports all of these as one `403`);
  - thank-you;
  - load failure with retry;
  - while saving or submitting: link stopped (text kept to copy), unconfirmed submit (text kept; it may already be received), and other failures (text kept).
- **No browser storage or cookies.** Unsaved text triggers the leave-page warning.
- English and Arabic (RTL), Plenix 0.60.1 components only.

## Not available yet (backend contracts requested on #2)

- An HTML route at `/external/reports/{id}/` (the static boot page is used meanwhile).
- Distinguishable link states on the priest page (council now sees them through the projection).
- Priest recording upload.
- Email delivery.
- **Privacy defect: fixed in backend `6fe7d51` (migration 0042).** Reproduced on `dccbd63`, where the spouse downloaded the paper. On `f0e97fa` the same upload is stored with no owner and council visibility; the spouse is refused on GET, HEAD and range requests, and council still reads it. Awaiting the governance successor rerun.
- **Council paper listing:** `/api/requests/{id}/files/` is applicant-only, so council can't list papers uploaded to a request. A wrong upload that was replaced in the form stays retained but isn't listed; the backend's wrong-upload correction is also unfinished.

## Testing

- `tests/frontend/external-report.test.cjs` (13), `tests/frontend/council-external.test.cjs` (21) and `tests/frontend/council-paper.test.cjs` (12).
- The fixture (`scripts/council_fixture.cjs --contract=pr7`) models the send token, reissue, cancel, capability route, and print routes (`POST /__pdf_mode/ {mode: "unavailable"|"too_long"}` switches the PDF reply), paper upload, file status (clean on the second check; `POST /__paper_scan/ {state: "rejected"}`), paper completion and the paper original download.
- Actual-backend results are in the #3 report.
- Evidence: `evidence/c05-ar-390-priest-page-real-backend.jpg`, `evidence/c05-ar-390-link-inactive-real-backend.jpg`, `evidence/c05-ar-390-link-expired-projection-real-backend.jpg` (synthetic data).
