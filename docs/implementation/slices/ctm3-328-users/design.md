# ctm3-328 — CTM Settings > Users: variations for the owner (G2 design)

Issue: LighthouseCollection/CTM#328. Owner, 2026-11-10: "this looks like crap! Send to designer to come up with variations and suggestions."

- Status: **variations only.** The owner picks one before anything is built (owner rule: show me first).
- Plenix 1.6.1 (the `PLENIX_BASE` pin). Documented parts only, no CTM CSS, no inline styles.
- Pictures: desktop 1440 x 900, EN, fictional people. Mock: `variations/users-variations.html?v=A|B|C|D`.

## Why today's screen looks the way it does

- **The column is narrow.** Users sits inside `SettingsLayout`, whose content column is a reading column (about 640px at 1440). Seven columns do not fit, so the `DataGrid` (`narrow: "auto"`) turns every member into a row card. That is the tall stack of grey pills.
- **The switches take the room.** Each Council seat and Voting cell holds a labeled `Switch`, the widest cells in the row. They are also what makes the card tall.
- **Every value is a pill.** `CTMShell.Table` draws `cells: "pill"`, so name, role, email and status each get a grey pill.
- **"Status: Active" says nothing.** The view is already "Active Members", so every row says Active.

## What the "# 5" is

- It is the member's **number of active cases** (`active_case_count`, column "Active cases").
- In a row card, Plenix puts the first number column in the "primary" slot without its column label (`data-grid.md`, template rule), so it shows as a bare `#` pill.
- **How it should read:** in a list or card, a plural message: "5 active cases", "1 active case", "No active cases" (Arabic plural forms by `ctm3-i18n-engineer`). In a table, a plain number under the "Active cases" header. Never a bare `#`.

## The four variations

All four keep: the `SettingsLayout` and its nav (template map, D-0034), the page title, the `CommandBar` (Add staff user as the one primary, Active/Previous Members, search, the count), and the row menu (Edit, Council seat, Manage access, Archive).

One seat reading for all of them, a `Badge` with an icon (owner rule: statuses are badges with an icon):

| Seat | Badge |
|---|---|
| Voting seat | `tone="success"`, icon `gavel`, "Voting seat" |
| Seat without a vote | `tone="active"`, icon `person`, "Non-voting seat" |
| No seat | `tone="neutral"`, icon `person-cancel`, "No seat" |

### A — Table (`variations/A-table.png`)

- `DataGrid` with text cells, not pills: Name (`kind: "avatar-name"`), Role, Council seat (badge), Active cases (number). Email and Status leave the table (email shows in search and in Edit).
- Seats change through the row menu's "Council seat", which opens a small `Dialog` with the two switches.
- **Pros:** densest; sorts and filters by column; handles 1,000+ rows (virtual rows); closest to the other CTM tables.
- **Cons:** still tight in the 640px column (long names cut); drops email from view; changing a seat takes two clicks; text cells depart from CTM's pill tables (a small decision of its own).

### B — List with a details panel (`variations/B-list-and-side-panel.png`) — **recommended**

- `ResourceList` (avatar variant): one line per person, the avatar, name, "Role · email" under it, the seat badge at the end.
- Choosing a person opens a `SidePanel` at the shell's end (`secondary-pane.md`): avatar and role, `PropertyList` (Email, Active cases, Status), and a `SettingsSection` "Council seat" with the Council seat and Voting switches. Edit, Manage access and the menu sit in its footer.
- **Pros:** calm, readable list that shows every member's seat at a glance; the switches move out of the list, which is what made it tall; seat changes stay one click once a person is open; fits the narrow settings column; follows the owner's attendance ruling ("does not need to be in a data grid, use pictures with proper typography", D-0053).
- **Cons:** you open a person to change a seat (one extra click compared with today); no column sorting; the panel takes room while open.

### C — Grouped people list (`variations/C-grouped-list.png`)

- The same `ResourceList`, grouped into "Council members" and "Staff without a council seat", each person with "N active cases" and the seat badge at the end, and the menu.
- **Pros:** shows the council at once (how many seats, who votes); every fact is visible without opening anyone; fits the narrow column.
- **Cons:** seats change through the menu and a dialog, as in A; grouping by seat hides role order (president and secretary mix with members); a busier row end.

### D — People cards (`variations/D-people-cards.png`)

- `UserCard` in a `ContentGrid` (three across): avatar, name, email, role badge, "Council seat, voting" and "N active cases" as detail lines, Edit and the menu.
- **Pros:** friendliest look; good for a small council.
- **Cons:** tallest of the four (10 members fill about two screens, the same complaint as today); hard to compare seats down a column; long emails wrap inside the card (Plenix, PLX-028).

## Recommendation

- **B**, with C's "N active cases" text at the row end if the owner wants the case count in the list.
- Reason: it fixes the real cause (switches and pills crowding a narrow column) and keeps the list short and readable, in the same direction the owner already chose for attendance.

## Screen spec for the build (once the owner picks; written for B)

1. **Task and actor:** admin, secretary or president checks who is on the council and who votes, adds staff, edits, archives. Decision supported: is this person seated, and do they vote.
2. **Template:** `SettingsLayout` (locked map row) > page title > `CommandBar` > `ResourceList`; the detail in the `AppShell` `panel` as a `SidePanel`. No card around the list (D-0055 row "Users: single full-height listing").
3. **Lead:** the list. P0: name, seat badge. P1: role, email. P2 (panel): active cases, status, seat switches. Primary action: Add staff user. Secondary: Edit, Manage access, Council seat, Archive or Restore.
4. **State matrix:**

| Region | Loading | Empty first-use | Empty filtered | Error | Forbidden | Read-only | Saving | Conflict |
|---|---|---|---|---|---|---|---|---|
| List | `ResourceList` with `Spinner` after about 1s (DelayedSpinner) | `EmptyState` "No active members." + Add staff user | `EmptyState` "No members match" + Clear search | `Notice tone="danger"` + Retry | n/a (the server hides the page) | the list is the same; the menu shows only what the person may do | n/a | n/a |
| Previous Members | same | `EmptyState` "No previous members." | same | same | n/a | Restore only | n/a | n/a |
| Side panel | `Spinner` in the panel | n/a (opens on a chosen row) | n/a | `Notice tone="danger"` in the panel | n/a | seat shown as badges, no switches (`can_edit` false) | `Switch` disabled while a seat saves | `Notice tone="warning"` "changed by someone else", reload (the `expected_version` refusal) |
| Seat switches | n/a | n/a | n/a | the switch goes back, `Notice tone="danger"` | n/a | badges | disabled | as above |

5. **Edge cases:** long names and emails cut with an ellipsis, the full text in the panel; no email shows "—"; 1,000+ members: `ResourceList` is not virtualized, acceptable for a staff list (tens of people); if it ever grows past a few hundred, switch to A. Arabic: every new word (seat badges, "N active cases" plural, panel headings) goes to `ctm3-i18n-engineer`; the list and panel mirror in RTL.
6. **Irreversible actions:** Archive keeps today's `ConfirmDialog` ("Archive {name}? Their account access will be disabled."). Turning a seat off is reversible and needs no confirmation; Voting off when the seat goes off, as today.
7. **The builder must not invent:** seat badge words and icons (table above); the order of the list (role order president, secretary, admin, member, then by name); who may change seats (`can_edit` from `/api/council/seats/`); any new Arabic text.

## Plenix requests

- PLX-019 (open): one settings section at full page width. Would let A breathe; B, C and D do not need it.
- PLX-028 (new): `UserCard` `secondary` wraps an email mid-word ("example.or / g"); it should end in an ellipsis.
- PLX-029 (new): `DataGrid` row card puts a number column in the "primary" slot without its label (the bare "# 5"); the card should show the label or take a plural message.
- PLX-030 (new): `DataGrid` `kind: "avatar-name"` with `cells: "text"`: the initials sit flush against the name and the name cuts without an ellipsis ("Martha Iskande").
