# ctm3-229 — council attendance roster (G2 design)

Issue: LighthouseCollection/CTM#229. Owner, 2026-11-07, said the Attendance dialog is "ugly" (D-0053). Plenix 0.93.1. Desktop only, EN/AR, RTL.

## Why it looked like a dropdown

The three attendance views (session `SessionAttendance` in `app.js`, hearing attendance in `council.js` around line 2051, and the case hearing dialog in `council-case.js` around line 3616) all put a `SegmentedControl` inside a narrow `Table` column. The control's default `fold: "auto"` folds it into a dropdown when it doesn't fit.

## One component: `AttendanceRoster`

There is one shared component, used by all three views (and any future one). It has no CTM CSS and no className.

| Part | Plenix | Content |
|---|---|---|
| Summary (top) | `Text` (strong) + `Button` | "**7 of 9 present**", then "· 2 not recorded" when any are unrecorded, with numbers through `Intl`. At the end of the line: secondary `Button icon="check"`, labelled **Mark all present** when nobody is recorded yet and **Mark the rest present** otherwise; disabled when everyone is present or the user can't record |
| List | `Stack gap="none"` of rows, each followed by a `Divider` except the last | No `Table`/`DataGrid`, no column headers |
| Row | `UserCard variant="compact"` | `name` = member name (value style); `src` = council photo when present, otherwise initials; `secondary` = "Presiding · Voting" / "Secretary · Non-voting" / "Member · Voting" (label style, D-0050) |
| Toggle | `SegmentedControl size="sm" fold="never"` in the row's `actions` | Options **Present** (icon `check`) / **Absent** (icon `close`). No value when not recorded, so neither is selected. `label` = "Attendance: {name}". State is shown in words and icon, never colour alone |
| Errors | `Notice tone="danger"` under the list | Names the members whose change failed |

**Order:** presiding, then secretary, then the other seat holders by name. Former members who have a record for this session stay at the end, read-only (as today).

**Who is listed (backend):** the **seat holders** (D-0043), not accounts with the `member` role. Each row carries `seat` (`voting` / `non_voting`) and `photo_url`. This is ctm3-backend-engineer's part of #229, together with the duplicate Fr. Youhanna Youssef seed account.

## Behaviour (saving rule, recorded in decisions/screens.md)

- **Save per toggle**, as today. The row changes at once and the change is posted. If the post fails, the row goes back and the error Notice shows. There is no undo button: clicking the other option is the undo.
- **Mark all present / Mark the rest present** sets every member **without a record** to Present. It never overwrites an explicit **Absent**. It posts one change per member. Members whose post fails go back and are named in the Notice.
- **Read-only:** a closed session, or a user without `can_record_attendance`. Wrap the roster in `ReadOnly`, so the control shows the recorded choice and the button is hidden.
- **Dialogs:** `Dialog size="md"` (the list is narrow) with the existing titles and help text; Close only, since changes are already saved.

## States

| Loading | Empty | Error | Forbidden | Read-only | Conflict |
|---|---|---|---|---|---|
| `Skeleton` rows | `EmptyState` "No council seat holders" | `Notice` + retry (load); row revert + `Notice` (save) | dialog not offered | `ReadOnly` | last write wins, as today |

## Strings (EN / AR proposal, in `docs/i18n/arabic-proposals.md`)

- "{present} of {total} present" / "{present} من {total} حاضرون"
- "{n} not recorded" / "{n} لم يُسجَّل حضورهم"
- "Mark all present" / "تسجيل حضور الجميع"
- "Mark the rest present" / "تسجيل حضور الباقين"
- "Voting" / "Non-voting": reuse the D-0043 settings strings if they exist

## Tests (frontend)

- No `Table` or `DataGrid` in any attendance view; every one renders `AttendanceRoster`.
- `SegmentedControl` has `fold: "never"`.
- "Mark the rest present" skips members already marked Absent.
- The summary counts are correct.
- Read-only hides the button.
