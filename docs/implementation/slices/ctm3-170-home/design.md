# ctm3-170 — council Home (G2 design)

Issue: LighthouseCollection/CTM#170 (owner 2026-11-07: "the dashboard looks
like crap", S2). Plenix pinned at 0.93.1. Desktop only. Decisions: D-0045
(full-width shell, every page), D-0046 (Home layout).

## Acceptance

| ID | Done when |
|---|---|
| AC-1 | Every council and sign-in page fills the window: `AppShell` uses `frame: "full"` (no 1366px frame, no grey side bands) |
| AC-2 | Home order: lead session panel → one row of equal stat tiles → My cases grid → council members → statistics summary |
| AC-3 | Stat tiles are equal in width and height on one row, short EN/AR labels, each opens its list, no menus or ⓘ |
| AC-4 | My cases appears once, as a `DataGrid` (case number, spouses, status, next step), each row opens the case |
| AC-5 | Council members and statistics come from aggregate-only endpoints, council roles only, with permission tests; applicants get 403 |
| AC-6 | Every state in the matrix below is built; every new string has EN and AR |
| AC-7 | Before/after EN desktop screenshots (fictional seed data) on #170 |

## 1. Why the page was narrow (shell-wide)

`static/ctm/app.js` passes `frame: "centered"` to `AppShell` (lines 1275 and
2008). In Plenix that draws the whole app in a 1366px frame on a grey
backdrop; with the navigation pane and page padding the content column is
about 850–1000px. Home itself already uses the fluid `workspace` page kind.
**Fix (D-0045):** `frame: "full"` on both shells, the Plenix default.
Every page gets the full width; pages that are meant to be narrow (forms,
settings) stay narrow through their own page kind (`contained`), not the frame.
Applied in this PR.

## 2. Home layout (D-0046)

Page kind `dashboard` (fluid). Plenix `dashboard-page` pattern: metrics above
the queues people act on. One `Stack gap="lg"`:

| # | Region | Plenix | Content |
|---|---|---|---|
| 0 | Page title | `Text as="h1" variant="title"` | "Home" / "الرئيسية" (unchanged) |
| 1 | **Next council session** (leads) | `Panel` (full width) with `icon="calendar"`, title = session name; body `PropertyList layout="columns"` in `Columns count={3}`; one `Button variant="primary"` "Open session" | Date and time (`Intl`, civil date never shifts), location, agenda items (n), my answer (`Badge` Attending / Not attending / Not answered, icon + word), "Confirmed n of m". The last two appear once #116 lands; until then they are not rendered (no placeholder). No session: `EmptyState` "No council session is scheduled" + secondary "Schedule session" for managers only |
| 2 | **Stat tiles** | `WidgetGrid columns={4}` of `MetricCard layout="tile" size="lg" href` (no `menu`, no `info`) | See tiles below. Non-managers see 2 tiles; then `columns={2}` so the row stays even |
| 3 | **My cases** | `Panel title="My cases" flush` with `DataGrid mode="pages" pageSize={10} density="compact"` | Columns: Case (`kind: "data"`, `YYYYMMDD-##`, `dir="auto"`), Spouses (husband · wife), Status (`Badge`), Next step (text, `wrap`). `onRowClick` opens the case. Footer link "All cases" → `/cases/mine` |
| 4 | **Council members** | `Panel title="Council members"` with `WidgetGrid columns={4}` of `MetricCard type="person"` (`person: { name, role, src }`, `value` = active cases, `unit` "active cases", `href` → that member's case list) | Active members only; Presiding first, then Secretary, then Members by name |
| 5 | **Statistics summary** | `WidgetGrid columns={2}`: `BarChart` "Cases per member" (horizontal) and `PieChart variant="donut"` "Cases by reason"; each `Panel` has a `Select size="sm"` year picker in its actions; Panel footer link "All statistics" → Statistics page | Ground labels per D-0035; colors are Plenix data-viz steps (`seriesColor`), never the reference's red/green/brown |

The full statistics set in #170 (granted vs submitted, gender, background,
education, marriage duration) belongs on the **Statistics** page
(`dashboard-grid`), not Home; built after the spec says which fields CTM
stores. Home shows only the two charts above.

### Stat tiles (short labels)

| Tile | EN | AR (proposal, `docs/i18n/arabic-proposals.md`) | Opens | Who |
|---|---|---|---|---|
| My cases | My cases | قضاياي | `/cases/mine` | all council |
| Unread | Unread | غير مقروءة | `/notifications` | all council |
| Review queue | New applications | طلبات جديدة | `/applications/new` (review queue) | managers |
| Consideration | For council | أمام المجلس | consideration queue | managers |

The long wording moves to each tile's `context` line only if the tile needs
it; tiles keep one-line titles so heights match.

## 3. State matrix

| Region | Loading | Empty | Error | Forbidden | Read-only | Draft | Conflict | Unavailable |
|---|---|---|---|---|---|---|---|---|
| Whole page | `Skeleton` per region (shape of panel/tiles/grid) | n/a | `Notice` + `useRetry` per failed region; other regions still show | applicants never routed here; 403 → `Notice` without data hints | n/a | n/a | n/a | n/a |
| Lead session | skeleton | `EmptyState` "No council session is scheduled" | region `Notice` + retry | — | n/a | n/a | n/a | my answer not rendered until #116 |
| Stat tiles | skeleton tiles | value 0 shown as 0 (not hidden) | tile value "—" + region `Notice` | — | n/a | n/a | n/a | n/a |
| My cases | `DataGrid` loading row | `EmptyState` "No open cases are assigned to you" + "All cases" | `Notice` + retry | — | n/a | n/a | n/a | n/a |
| Members | skeleton | `EmptyState` "No active council members" | `Notice` + retry | — | n/a | n/a | n/a | photo missing → initials |
| Statistics | skeleton | `EmptyState` "No cases in {year}" | `Notice` + retry | — | n/a | n/a | n/a | suppressed count shown as "Hidden" (never the number), with the privacy note |

## 4. Data (backend, aggregate only)

| Endpoint | Returns | Rules |
|---|---|---|
| `GET /api/dashboard/` (extend) | `upcoming_sessions[0]`: `starts_at`, `location`, `agenda_count`; after #116 `my_answer`, `confirmed`, `invited` | Council roles only (as today) |
| `GET /api/cases/?mine=1` (extend if missing) | per case: `number`, spouse display names, `status`, `next_step` (EN/AR key) | Existing case permissions |
| `GET /api/dashboard/members/` (new) | active council members: `id`, `name`, `title` (presiding / secretary / member), `photo_url`, `active_cases` | Council roles only; no applicant data; deny by default; tests for applicant 403 and anonymous 401 |
| `GET /api/statistics/summary/?year=` (new) | `cases_per_member[]`, `cases_by_ground[]`, `years[]` | Council roles only; counts only, never rows or links to applicants; Professional Assessments never a source; any count below the privacy threshold is returned as `null` + `suppressed: true`. Threshold **5**, confirmed by ctm3-product-lead on #170: a count below 5 is hidden; if only one cell in a list is hidden, the smallest visible cell is hidden too, and no total is published (#208). Every hidden cell reads **"Hidden"** / **"مخفي"**, never "Fewer than 5", because a second hidden cell can be 5 or more; the panel says once "Counts under 5 are hidden, sometimes with one more so they cannot be worked out." / "الأعداد الأقل من 5 مخفية، وأحيانًا عدد آخر معها حتى لا يمكن استنتاجها." |

## 5. Builder must not invent

- No new colors, menus on tiles, extra primary buttons, or custom CSS.
- Arabic labels above are proposals; institutional wording goes through
  `docs/i18n/arabic-proposals.md`.
- No placeholder for #116 fields; they appear when the data exists.
- Screenshots use `seed_demo` fictional data only.

## Tests

| ID | Check |
|---|---|
| AC-1 | `tests/frontend/shell-frame.test.cjs` (no `frame: "centered"`) |
| AC-2 | frontend test: CouncilHome renders regions in order |
| AC-3 | frontend test: tiles have `href`, no `menu`/`info`; labels from the table |
| AC-4 | frontend test: one My cases region, `DataGrid` with the four columns |
| AC-5 | PostgreSQL tests: members/statistics 403 for applicant, 401 anonymous, suppression below threshold |
| AC-6 | `check_i18n.cjs --base origin/main` |
| AC-7 | screenshots on #170 |

```owners
ctm3-design-director: docs/implementation/slices/ctm3-170-home/**, DESIGN.md, docs/implementation/decisions/screens.md, decisions.yaml, static/ctm/app.js, tests/frontend/shell-frame.test.cjs
ctm3-frontend-engineer: static/ctm/**, tests/frontend/**
ctm3-backend-engineer: tribunal/**, tests/**
```
