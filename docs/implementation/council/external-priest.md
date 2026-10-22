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
- A printable request and paper-response completion.
- Email delivery.
- **Privacy defect: fixed in backend `6fe7d51` (migration 0042).** Reproduced on `dccbd63`, where the spouse downloaded the paper. On `f0e97fa` the same upload is stored with no owner and council visibility; the spouse is refused on GET, HEAD and range requests, and council still reads it. Awaiting the governance successor rerun.
- **Council paper listing:** `/api/requests/{id}/files/` is applicant-only, so council can't list a returned paper on the request. Paper completion is also missing.

## Testing

- `tests/frontend/external-report.test.cjs` (13) and `tests/frontend/council-external.test.cjs` (8).
- The fixture (`scripts/council_fixture.cjs --contract=pr7`) models the send token, reissue, cancel and capability route.
- Actual-backend results are in the #3 report.
- Evidence: `evidence/c05-ar-390-priest-page-real-backend.jpg`, `evidence/c05-ar-390-link-inactive-real-backend.jpg`, `evidence/c05-ar-390-link-expired-projection-real-backend.jpg` (synthetic data).
