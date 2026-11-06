# ctm3-116 — council session reminders, calendar invite, attendance confirmation (brief)

Issue: LighthouseCollection/CTM#116. Decision: D-0039 (product lead, 2026-11-06,
recommended option applied; the owner can change it on #116).
Owner, review deck slide 9: "Send out reminders to council members. Send out
ics (add to calendar). Get confirmation."

## What it does

1. **Invite.** When a planned council session has a start time, every active
   council account (role `member`, `president`, `secretary`, `admin`; never
   `applicant`) with a verified email gets one email with a calendar file
   (`.ics`). If the date, time or location changes, they get an updated file
   (same `UID`, higher `SEQUENCE`). If the session is cancelled or moved to a new
   date, they get a cancellation (`METHOD:CANCEL`) and, for a move, a new invite
   for the new session.
2. **Reminder.** An automatic reminder goes out **2 days before** the start
   time to anyone who has not confirmed yet. It carries the same `.ics`
   file. The secretary, president or admin can also press **Send reminder now**
   on the session. That sends to everyone who has not confirmed, at most once
   per hour.
3. **Confirmation.** The email asks the member to sign in to CTM and choose
   **I will attend** or **I will not attend** on the session. The answer can
   be changed until the session starts. Every answer is kept, with the latest
   one counting. Calendar Accept/Decline is **not** used: CTM cannot read
   replies sent to a mailbox, so the file uses `METHOD:PUBLISH` (a calendar
   entry with no RSVP buttons that would fail without telling anyone).
4. **Secretary view.** The Upcoming sessions list shows "Confirmed n of m". The
   session page lists each council member with Attending, Not attending or No
   answer, and when they answered. This is the *expected* attendance. Recorded
   attendance (`Attendance`) on the day stays separate and is not filled in
   from it.

## Privacy and honesty rules

- The email and `.ics` hold only: "CTM Council Session YYYY-MM-DD", date and
  time, location and the sign-in link `https://ctm.lighthouseway.org`. They
  never include case numbers, names, agenda items or any applicant data.
- No action links that work without signing in (no bearer links, consistent
  with D-0033's refusal of hand-sent bearer links). The confirmation happens
  only in the signed-in session page, with a server permission check: a
  member can answer only for themself.
- Delivery goes through the existing `Outbox` and `dispatch_outbox` path, so
  retries, leases and "the backend acknowledged the email" apply. The UI says
  "sent" only for delivered rows. If `EMAIL_HOST` is not set (#54 not done),
  the session shows "Email is not set up, so reminders cannot be sent"
  and nothing is queued as sent.
- Times in the `.ics` are UTC (`DTSTART:...Z`), with a 2-hour default length
  when there is no end time. The email shows the time in America/Los_Angeles.
- Reminder email wording is ordinary product text, not institutional text. EN
  and AR are both required. The AR text is a proposal in
  `docs/i18n/arabic-proposals.md` until it is confirmed (#120).

## Acceptance

| ID | Done when |
|---|---|
| AC-1 | Giving a planned session a start time queues one invite per active, verified council account and none for applicants or inactive accounts (backend test) |
| AC-2 | The `.ics` passes an RFC 5545 parse: `METHOD:PUBLISH`, a stable `UID` per session, `SEQUENCE` going up on every change, UTC `DTSTART`/`DTEND`, `SUMMARY`, `LOCATION`, `URL`, and no case or applicant data (test parses the file) |
| AC-3 | Changing the date, time or location sends an update. Cancelling or moving sends `METHOD:CANCEL` with the same `UID` (test) |
| AC-4 | The automatic reminder is queued once, 2 days before the start, only for members with no answer. Send reminder now is limited to secretary, president or admin and to once per hour (test, including a 403 for a member) |
| AC-5 | A member can answer Attend or Not attend for themself only, until the session starts. Earlier answers are kept and the latest counts. Another member's answer cannot be read or written, and applicants get nothing (PostgreSQL RLS and API tests) |
| AC-6 | The Upcoming sessions list shows "Confirmed n of m", and the session page shows each member's latest answer and its time (frontend test plus a desktop screenshot, EN and AR) |
| AC-7 | Without `EMAIL_HOST`, nothing is shown as sent and the page says reminders are unavailable (test). With email set, "sent" appears only for Outbox rows with `delivered_at` |
| AC-8 | Every new string has EN and AR (`check_i18n.cjs`) |

## Owners

- `ctm3-database-engineer`: the `SessionResponse` table (append-only: session,
  member, answer, created_at), its RLS and grants, and the `.ics` `sequence`
  counter on `CouncilSession`.
- `ctm3-backend-engineer`: `.ics` builder, Outbox kinds `session_invite`,
  `session_update`, `session_cancel` and `session_reminder`, the Celery beat
  job for the 2-day reminder, the answer and send-now endpoints with
  permission checks, and the "email not set up" state.
- `ctm3-frontend-engineer`: the answer buttons on the session page, the
  per-member list, the "Confirmed n of m" column and the Send reminder now
  button, using Plenix components only, at desktop width.

Out of scope: text-message reminders (needs a provider, #84), reading calendar
replies, and reminders for hearings or applicants.
