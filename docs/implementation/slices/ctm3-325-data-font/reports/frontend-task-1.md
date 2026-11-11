# Issue 325: data font sweep (frontend task 1)

Owner decision (chat, 2026-11-10, issue 325): Reddit Mono, the Plenix data font, is for case numbers, IDs, dates, times, amounts and counts everywhere. Names and words never use it.

## Layout statement

- Template: no new page. Every existing screen keeps its template. Only how values are marked changes.
- What leads: nothing moves. Data values switch to the data font through the documented Plenix markings.
- Density: unchanged.

## How data is marked (Plenix 1.6.1 docs)

- `data-grid` and `table`: a column takes `kind: "data"` or a typed column (`number`, `currency`, `date`, `bytes`).
  - When a column mixes a value with a word fallback ("Not recorded", "Unnumbered", "Time not recorded"), it takes `pill: (value, row) => ({ data: Boolean(row.<raw field>) })`.
  - Plenix's CellValue reads `own.data` first, so the word fallback stays in DM Sans.
- `property-list`: `PropertyList.Item data`.
- `text`: `Text variant="data"`. Inside other text it takes the surrounding size.
- `resource-list`: `items[].meta` "wrap technical values in `<Text variant="data">`".
- DM Mono: CTM has no mention of it left in code, docs or DESIGN.md (checked with grep; the new test keeps it that way).

## Screens and fields changed

| Screen (file) | Field | Before | After |
|---|---|---|---|
| Council reports reader (app.js) | Date received | text column | `kind: "data"` |
| Council communications (app.js) | message date (column and detail) | text / secondary Text | `kind: "data"` / data Text |
| Council notifications (app.js) | time in the row meta | string | data Text in meta |
| Council documents cards (app.js) | category code, version in the card meta | string | data Text |
| Applicant appointments | case number column; start column; start and end in the detail | text | per-value pill data; `kind: "data"`; data Text |
| Applicant assessments | signed at, version, receipt id and time | bdi in plain Text | data Text |
| Applicant filing | fee amount | inside a sentence string | data Text |
| Applicant payments | fee amount; time columns | string; text column | data Text; `kind: "data"` |
| Applicant requests | sent at (detail and column) | bdi / text column | data Text / `kind: "data"` |
| Applicant history, messages, supplements, notifications | timestamps, read time, unread count, case number | bdi in plain Text | data Text |
| Case header (council-case.js) | case number under the names | plain subtitle | data Text subtitle |
| Case summary, marriage, separation (CaseReadFields) | case number, filing, last hearing, marriage, separation, divorce and order dates | plain | `PropertyList.Item data` (not for "—" or a component) |
| Spouse profile | year of graduation | plain | `data` |
| Case audit detail | time | plain Text | data Text |
| Calls | time column and detail | text / secondary | `kind: "data"` / data Text |
| Notes | recorded column; version and time in the detail | text / string | `kind: "data"` / data Text |
| Hearings (past) | session date | text | `kind: "data"` |
| Assessments cards | date in meta | string | data Text |
| Petition panel | submitted time in the description | string | data Text |
| Decision | "recorded by" time; earlier versions (number, time) | string | name in DM Sans, time and number in data Text |
| Decree appeals (council-decree.js) | supplement card title (time); disposition "recorded by" time | string | data Text |
| Transcript, reports, files (council-media.js) | version tiles; segment times | plain | `data` / data Text |
| New applications (council.js) | case number column; submitted column; review cards (case number title, time in meta) | name / text | per-value pill data; data Text |
| Applications for council (council.js) | submitted | text | per-value pill data |
| Sessions list | date; time; adjourned; assigned and hearing counts | name / text | `["name","data"]`; per-value pill data; `type: "number"` |
| Archived agenda | case number | name | `["name","data"]` |
| Hearings agenda | # | name | `["name","data"]` |
| Case picker | filed | text | per-value pill data (`filed_at` kept on the row) |
| Session answers | answered at | text | `kind: "data"` |
| Agenda card | case number title and meta; testimony times | string | data Text |
| Previous returns, outcome history | times | string | data Text |
| Assign dialog | case number | strong Text | data Text |
| Historical entry | version | plain | `data` |
| Settings audit, account activity | date | text / string | `kind: "data"` / data Text |

Names stay in DM Sans everywhere: spouses, members, actors and authors. The check below flags a person's name with the data marking.

## State matrix

This is a marking change only; no states were added or removed.

| Region | loading | empty | error | read-only | data |
|---|---|---|---|---|---|
| every list and record above | unchanged | unchanged | unchanged | unchanged | data marking as listed |

## The check (in CI)

- `scripts/check_data_font.cjs` (`findDataFontProblems`) flags these known data values without the data marking:
  - `formatWhen` / `formatDate` / `formatTime` / `formatBytes` / `formatDuration`, `Intl` formatting, `String(…count|version|length)`, and the `case_number` / `reference` / `version` / `timestamp` / `*_at` / `id` fields.
  - Where it looks: `P.PropertyList.Item`, `P.Text`, a `bdi dir="ltr"`, a list `meta`, grid columns with data field names, and tiles.
- It also flags a person's name with the data marking.
- It runs in two places:
  - `node scripts/check_frontend_contract.cjs`, section 3, the quality workflow.
  - `tests/frontend/data-font.test.cjs`, the whole sweep plus unit cases for each rule.
- A reviewed exception carries `ctm-data-font-allow` on its line. None is used.
- Browser check: `scripts/browser_data_font.py` runs against `scripts/council_fixture.cjs` (fictional data) on the real CDN.
  - English: case numbers and session dates use Reddit Mono; member names and "Time not recorded" do not.
  - Arabic: checked by its pictures.

## TDD evidence

- Ran: the check on origin/main's `static/ctm/*.js` gives `CTM data font: 40 problem(s)` (RED, `.tmp/data-font-red.txt`).
- Ran: the check on this branch gives `CTM data font: OK` (GREEN).
- Ran: the browser check on main's code (label after) fails with 3 findings: session date and case number in DM Sans (`.tmp/browser-data-font-red.txt`). On this branch: `Data font check: OK (after)`.

## Commands

- Ran: `node --test tests/frontend/*.test.cjs`: 571 tests, 571 pass, 0 fail.
- Ran: `node scripts/check_frontend_contract.cjs` and `--base origin/main`: OK (Plenix CDN 1.6.1).
- Ran: `node scripts/check_i18n.cjs --base origin/main`: 0 problems, 0 new. No string keys were added.
- Ran: `node scripts/check_ownership.cjs`: OK (20 changed files).
- Skipped: `opengrep`, which is not installed on this host; CI runs it.
- Skipped: `browser_integration.py` and the SQLite fixture (`scripts/browser_fixture.py`). They fail before any page loads: `OperationalError: near "FUNCTION"`, because the migrations are PostgreSQL-only now. The Node council fixture was used instead.

## Screenshots (fictional data)

- `.tmp/data-font/{before,after}-{cases,case,sessions}-{en,ar}.png`
- Pushed to `ci-screenshots/preview-325/`.

## String keys added

None. EN/AR parity is unchanged.

## Scope self-check

- Only presentation markings changed. No API, backend, migrations or CSS were touched, and there is no inline style.
- Shared files touched:
  - `app.js`: three columns and two meta lines.
  - `ui-workspaces.js`: one column and one list.
  - Neither touches the shell layout or footer (issue 324) or the Home charts (issue 323).
- One existing test pinned the hearings-agenda `#` column as `kind: "name"`; it now pins `["name", "data"]`. Two case header tests now read the subtitle as a data Text.

## Open points

- Plenix: the Timeline `time` slot always uses the data font. Key Dates therefore shows "Pending", "Approved" and "In progress" in Reddit Mono when there is no date. This is a Plenix item: a per-item `data` flag would fix it.
- The case header title is the case number only when a case has no parties; it stays in the heading font.
- Hard-coded English column titles "Completed by" and "Date received" in app.js (ReportReader) were left as they are. They are outside this issue.
- Dates inside translated sentences (for example "Answered on {when}") stay in the text font, so no sentence is built from fragments.
- Native `Select` option labels cannot carry markup.
