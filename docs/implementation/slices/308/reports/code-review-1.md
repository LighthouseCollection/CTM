# Code review, issue 308, round 1

Reviewer: ctm3-code-reviewer (Code Reviewer #308), 2026-11-10.
Measured against: issue #308 (owner approvals and the background-loading proposal) and
`docs/implementation/performance.md` from PR #315 (rules 3, 4 and 8).

## PR #316, step 1 (head `eee4521`): PASS

```
SPEC: COMPLIANT    QUALITY: APPROVE
```

Strengths:
- The shell stops loading data for council Home and the case summary (`static/ctm/app.js:1148`). The full `/api/cases/` list and the second case read are gone, as rule 3 asks.
- Home reads the lead session from the dashboard card. The backend really sends every field the card uses (`tribunal/services/home.py:55-70`: `state`, `starts_at`, `location`, `agenda_count`, `my_answer`, and `confirmed`/`invited` only for `SENDER_ROLES`). A member still never sees how others answered (#116 AC-5).
- "Your answer" now shows for every council role. That is correct, because `council_recipients()` invites every council role (`session_reminders.py:49-52`).
- The case page starts the record, requests and audit together. Members wait for `can_assign`, except for admin and secretary, and `HeaderAssignment` reuses the summary's list.
- The new round-counting test (`tests/frontend/data-loading.test.cjs`) and the stricter Home test (it fails if Home reads `/api/sessions/`) strengthen the coverage.

Blockers: none.

Minor (fine to merge as is):
- `static/ctm/council-case.js:3350` `ASSIGNERS` repeats a server role list. It only decides whether the members read starts early, and `can_assign` still decides, so a drift costs one extra or one later read.
- `static/ctm/council.js` `sharedReads` becomes redundant once step 2's store shares reads still on their way. Remove it in step 2 or 3.

Cannot verify from diff: the live round counts and timings. They are fixture numbers.

## PR #318, step 2 (head `731b44d`): FAIL

```
SPEC: NOT COMPLIANT    QUALITY: REQUEST CHANGES
```

Strengths:
- Memory only, with `cache: "no-store"` kept. Every method except GET clears the store before and after the save. The epoch check stops a read that started before a save from filling the store. A 401 clears it.
- The allow-list is explicit, and it holds none of these: files, assessments, medical, audit, timeline, notifications, decisions, decrees, payments, messages or the session.
- A quiet refresh never redraws under unsaved edits (`unsavedDrafts`). A refused refresh drops the copy, so the page shows the real error.
- Background reads run at most 2 at a time, give way to user reads, and pause while the tab is hidden.

Blockers:

1. `static/ctm/data.js:63-68`, `static/ctm/app.js:1131`. NEW (rule 4 and rule 8: "cleared ... when the signed-in account changes"). **The store does not clear when the account changes in another tab.**
   - Why: `setAccount` runs only when `/api/session/` loads, which happens at boot and on a retry. Suppose account A signs out in tab 2 and account B signs in. Tab 1 still holds A's kept replies for up to 5 minutes. When B opens a page in tab 1, A's case list or case record is drawn from memory at once and replaced only when the quiet refresh lands. Within 10 seconds of the read, the server is not asked at all.
   - Without the store, the same click reads from the server with B's cookie. This is a privacy regression on a shared or parish computer, the exact case the limits were written for.
   - Fix: notice the account change without a round trip. For example, keep the `csrftoken` cookie value from `setAccount`; Django's `login()` rotates it. In `read()`, `schedule()` and `prefetch()`, clear the store when the cookie value differs. Alternatively, listen for a `BroadcastChannel`/`storage` sign-out or sign-in signal that carries no data. Add a test: the cookie changes, and the next read goes to the server and the store is empty.

2. `static/ctm/data.js:182-194`. NEW (rule 8 "Paused while the user is active" and "Stopped when it costs the user"). **Two of the prefetch limits are missing.**
   - Why: rule 8 says prefetch starts only after 2 seconds with no input, stops at the next key, click, scroll or touch, and never runs on a 2G or slower connection.
   - `idle()` uses `requestIdleCallback(fn, { timeout: 2000 })`. The timeout makes the callback run within 2 seconds even when the browser is busy, which is the opposite of the rule. Nothing listens for input, and nothing checks `navigator.connection.effectiveType`.
   - Fix:
     - Track the last input time (`keydown`, `pointerdown`, `wheel`/`scroll`, `touchstart`; passive listeners).
     - Start prefetch only from an idle callback after 2 seconds with no input. Drop the forcing `timeout`.
     - Have `pump()` stop taking prefetch jobs once input has been seen since the idle period began (quiet refreshes can keep running).
     - Skip prefetch when `effectiveType` is `slow-2g` or `2g`.
     - Add tests for each case.

3. `static/ctm/council.js:3409`. NEW (rule 8 "Small pages: one rule-5 page at a time (at most 50 rows)" and "Never a whole list just in case"; issue #308: "It must not include the heavy `/api/cases/` list more often than today"). **Home prefetches the full case list.**
   - Why: step 1 removed the full `/api/cases/` list from Home because it is the heaviest read (up to 100 cases with parties, applications, revisions and next step). Step 2 puts it back on every Home visit as a background read.
   - Server pages (#312) do not exist yet, so no prefetch of this list can meet the 50-row limit.
   - Fix: prefetch only the agenda until #312 provides a paged case list, then prefetch the first page. Update the test that expects `/api/cases/` among Home's background reads.

Minor:
- `static/ctm/data.js:25`: the case-list pattern keeps any query string. A future `?q=` search or filter on `/api/cases/` would be kept without review, although the PR says search is never kept. Narrow the pattern to `(\?mine=1)?$`.
- `static/ctm/data.js:198-224`, `static/ctm/council.js:1261-1266`: `reader()` adds itself to `readers` during render, before the component mounts. A render that never commits leaves a reader registered. Register it in `open()` only.
- `docs/implementation/slices/308/reports/frontend-task-2.md` lists the before/after timings as Planned. The owner asked for numbers with each step's PR (#308, PM comment).

Cannot verify from diff:
- On the live site, that Entra sign-in rotates `csrftoken`. This matters for the suggested fix to blocker 1.
- Real request counts after the store is in place.

Declined to judge:
- Whether `/api/applications/` (it carries the fee status) may be drawn from memory under "payments always fresh". A payment returns through a full-page redirect, which wipes memory, so I did not count it as a blocker. The lead may rule.
