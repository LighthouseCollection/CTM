# Performance standard

The owner set this standard on 2026-11-10 for CTM, PDS and every business
database app (CTM#311). It applies to every screen, the applicant portal and
the council workspace alike. Each rule has a decision in `decisions.yaml`
(D-0065 to D-0073) that names the check enforcing it.

Where a rule meets an earlier decision, the earlier decision stays in force:
- Loading regions keep the labeled Plenix spinner shown after about a second
  (D-0064). These rules make the spinner appear less often; they never replace
  it with a skeleton.
- Permissions are decided by the server on every read
  (`docs/architecture/build-spec/permissions.md`). Caching, prefetch and
  paging never widen what a user may see, count or download.

## The rules

### 1. The app frame and its code are cached (D-0065)

- The app frame and its code are cached, so the screen appears at once.
- CTM's static files are precompressed (gzip and brotli) and served under
  content-hashed names with `max-age=315360000, immutable`
  (`ctm/settings.py`, `STORAGES`).
- The shell HTML is not cached long, so every visit gets the current hashed
  names. A changed file gets a new name; nobody bumps a version by hand.
- Plenix CDN files stay on their pinned, versioned, immutable URLs
  (`PLENIX_BASE`).

### 2. Code loads per screen; the next likely screens load while idle (D-0066)

- A screen loads only the code it needs. The signed-out sign-in page loads
  only the shared shell code.
- Applicant screens never load council code, and council screens never load
  applicant code. Shared helpers live in a shared file.
- The code for the next likely screens is fetched while the browser is idle,
  within the limits of rule 8.

### 3. One data request per screen, in parallel, never in a chain (D-0067)

- Each screen asks for its data in one request, or in several requests sent at
  the same time. No request waits for another request's answer.
- The signed-in session is sent with the page HTML, not fetched after the code
  loads.
- The shell never fetches data that the screen fetches itself. The same
  address is never requested twice for one screen; two parts that need it
  share one request.
- After a save, the screen fetches only what the save changed, not every
  source again.
- A screen that needs a field from another list asks the backend to add the
  field to its own reply; it never downloads the whole other list.

### 4. Data already seen shows at once, then refreshes quietly (D-0068)

- A screen whose data is already in memory draws from it at once, then asks
  the server again and updates in place when the answer changed.
- A form being edited is never replaced by a refresh. Saves still send the
  version, so a change made meanwhile shows the existing conflict message.
- Returning to the tab refreshes the screen.
- A save drops every kept reply it can affect (for example, a change under one
  case drops that case and the case lists).
- Always fresh, never drawn from memory: votes, decisions, decree issue and
  release, payments, and anything the user is about to sign or send.
- Kept data is memory only and cleared on sign-out, on a 401 or expired
  session, and when the signed-in account changes (rule 8 limits apply).

### 5. Lists load one page at a time from the server (D-0069)

- Every list asks the server for one page of 25 to 50 rows. Search, sort and
  filters run on the server.
- Totals and counts come from the server and count only rows the user may
  see; a count never reveals a hidden row.
- The pagination contract (request and response, permissions, counts) is
  designed on CTM#312 before any list is built.

### 6. Saves show at once and undo if the server refuses (D-0070)

- A save shows its result on screen at once while the server confirms it.
- When the server refuses, the screen returns to its earlier state and shows
  the server's reason.
- Actions with legal or financial effect wait for the server and are never
  shown before it confirms: votes, decisions, decree issue and release,
  payments, signing and sending. Built on CTM#313.

### 7. Speed is measured, and a slower page fails the build (D-0071)

- Main content appears within 2.5 s (LCP), and a click is answered within
  0.2 s (INP).
- A CI check loads the main pages on fictional data and records LCP, INP (or
  Total Blocking Time as its stand-in), the request count and the JavaScript
  bytes. It fails the build when a page gets slower.
- Agent detail (agent, CTM#314; tunable without the owner): "slower" means
  more than 10% over `main`, above the noise floors; the budgets live in one
  config file.
- A page already over its budget on `main` fails only when it gets slower.
  Built on CTM#314.

### 8. Idle prefetch of larger data, within limits (D-0072, limits D-0073)

The site may fetch larger data in the background while the user is idle, so
it is ready when opened. Every prefetch keeps all of these limits:

- **Only what this user may see:** the same server-checked request the screen
  would send, for the signed-in account only.
- **Only what is likely next:** one step ahead of the current screen (from
  Home: My cases and the next session's agenda; from a list: the row under
  the pointer or keyboard focus; from a case: the summary of its other tabs).
  Never a whole list "just in case".
- **Small pages:** one rule-5 page at a time (at most 50 rows).
- **Paused while the user is active:** it starts only from an idle callback
  after 2 seconds with no input, stops at the next key, click, scroll or
  touch, and resumes only after the next idle period.
- **Few at a time:** at most 2 prefetch requests in flight, and at most 10
  prefetched replies kept per screen. A prefetch never delays a request the
  user asked for.
- **Stopped when it costs the user:** never while the tab is hidden, when the
  browser asks to save data, or on a 2G or slower connection.
- **Never prefetched or kept:**
  - files and their contents (opening a file is audited; a prefetch would
    record a view that never happened)
  - Professional Assessments and the medical section
  - audit pages
  - notifications (marking them read stays a deliberate act)
- **Memory only:** no `localStorage`, `sessionStorage`, IndexedDB, Cache API
  or service-worker cache for API data.
- **Cleared on sign-out:** and on a 401, an expired session, or a change of
  signed-in account.

## Where each rule stands

| Rule | Decision | Enforced by | Work |
|---|---|---|---|
| 1 Frame and code cached | D-0065 | `ctm/settings.py` (`STORAGES`) | Done for CTM code, #309 |
| 2 Code per screen | D-0066 | Review until the #308 test lands | #308 |
| 3 One request per screen | D-0067 | Review until the #308 test lands | #308 |
| 4 Seen data at once | D-0068 | Review until the #308 test lands | #308 |
| 5 Server pages | D-0069 | Review until the #312 tests land | #312 |
| 6 Saves at once, undo | D-0070 | Review until the #313 tests land | #313 |
| 7 Measured, build fails | D-0071 | CI job `speed-budget` in `.github/workflows/performance.yml` | Done, #314 |
| 8 Idle prefetch | D-0072, D-0073 | Review until the #308 test lands | #308 |

When a rule's check lands, its decision's `review_only` reason is replaced by
the `check` that enforces it. Each implementation issue closes with
before-and-after numbers.
