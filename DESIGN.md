---
contract: CTM design contract
version: 1.0
date: 2026-11-04
owner: ctm3-design-director
visual_language: Plenix (PDS) from the CDN, version pinned in ctm/settings.py
languages: [en, ar]
directions: [ltr, rtl]
viewports: { desktop: 1440, mobile: 390 }
checks:
  styling: scripts/check_frontend_contract.cjs, .opengrep/ctm.yml
  cdn: scripts/bump_plenix.cjs --verify, scripts/browser_cdn_smoke.py
  locale: scripts/check_i18n.cjs
  decisions: scripts/check_decisions.py
---

# CTM design contract

CTM is an application that **consumes** the Plenix design system (PDS). Plenix
owns the visual language: colors, type, spacing, corners, density, icons,
motion, dark mode. CTM never restyles it. This file is the layer CTM owns on
top: how pages are composed, which states exist and how data is shown. Agents
follow it instead of improvising. Changing the look needs a new decision
(`decisions.yaml`); fixing a defect inside it does not.

## 1. Visual language: Plenix only

- Documented `window.Plenix` components, `plx-` classes and `--plx-sys-*` /
  `--plx-comp-*` tokens only. Before using a component, read
  `<PLENIX_BASE>docs/<id>.md` at the pinned version.
- No raw colors, numeric font sizes, inline `style`, `!important`, custom CSS,
  copied CDN code, Tailwind or another UI kit. The isolated Arabic styling
  bridge is the only exception and stays replaceable.
- Icons from the Plenix icon set (Material Symbols Sharp). Motion from Plenix;
  CTM adds none.
- Missing capability -> `docs/implementation/plenix-requests.md`, never a
  lookalike.
- Plenix upgrades arrive automatically (`plenix-upgrade.yml`); CTM adapts to
  Plenix, not the reverse.

### Buttons (D-0036, #115)

Buttons only use Plenix `Button` variants. The look of each variant
(fill, border, shadow, glow) comes from Plenix. Since 0.88.0, secondary and
danger-secondary have the same light elevation (plenix-ds/pds#269).
CTM never restyles a button. If two variants look inconsistent, that goes to
`plenix-ds/pds`, not into CTM.

| Variant | Use in CTM |
|---|---|
| `primary` | The one main action of an area (page header, card, dialog footer) |
| `secondary` (default) | Every other visible action, including Edit and Cancel |
| `ghost` | Icon-only or low-emphasis actions in toolbars and table rows |
| `danger-secondary` | A destructive action that must stay visible beside other buttons; it opens a confirmation |
| `danger` | Only the confirm button inside a confirmation `Dialog` / `ConfirmDialog` footer |
| `tertiary` | Not used |
| `tone` | Only for a chosen state (vote Approve / Deny / Abstain), never at rest |

Destructive actions on a record or row go in its action menu (`ActionMenu`,
`rowMenu` item with `danger: true`) when the area already has a menu (#103).
A row of buttons never mixes `primary` with `danger`.

## 2. Pages

- Every new or reworked page starts from its Plenix page template in
  `docs/implementation/plenix-page-templates.md` (`RecordPage`, `ListingPage`,
  `MasterDetailPage`, `SettingsLayout`, `FormFlow`/`Wizard`,
  `SearchWorkspace`). Hand-composing needs a reason in the slice design.
- Locked navigation and split list/detail patterns:
  `build-spec/interface-contract.md` and
  `docs/architecture/CTM-council-navigation-and-layout.md`.
- One thing leads each page; one primary action; extra actions in a menu.
  Related items grouped (space before lines). Pages end on purpose.
- Cases are a workspace table, never navigation entries.
- Pages fill the window: `AppShell frame="full"` (D-0045). A page that should
  be narrow gets it from its page kind (form, settings), never from the frame.
- Navigation panes (D-0047): the main `NavPane` keeps the Plenix shell
  navigation width and folds to its rail while a case is open; the case
  `SecondaryPane` uses `width="md"` (D-0048: the longest term must fit; terms
  are never shortened to fit), stays collapsible and resizable. Every
  nav item uses a Plenix icon (no drawn SVG) so icons and labels line up.
  "Back to sessions" is the way back from a case.

### Council Home (D-0046, #170)

Dashboard page, top to bottom: the next council session leads (one `Panel`,
date and time, location, agenda count, my answer, one primary "Open
session"); one row of equal `MetricCard layout="tile"` stat tiles with short
labels, each linking to its list, no menus; My cases as a `DataGrid`; council
members as `MetricCard type="person"` cards with active case counts; a
statistics summary (cases per member, cases by reason) with a year picker.
Nothing appears twice. Full spec: `docs/implementation/slices/ctm3-170-home/design.md`.

## 3. States (every screen spec has this matrix)

| State | Plenix component | Rule |
|---|---|---|
| Loading | `Skeleton` shaped like the final layout | Only when it takes over ~1 second |
| Empty, first use | `EmptyState` | What goes here + one action |
| Empty, filtered / cleared | `EmptyState` | Say the filter; offer clear |
| Error | `Notice` + `useRetry` | What, why, next step; retry keeps input |
| Forbidden | `Notice` | No data hints in the message |
| Read-only (closed proceeding) | `ReadOnly` | Actions hidden, not just disabled |
| Draft | `DraftState` | Unsaved edits survive in-app navigation or warn |
| Conflict (409) | `Notice` | Show whose change won; keep the user's text |
| Processing unavailable | `Notice` | Honest "unavailable"; never fake OCR/audio |

Build only states the code can reach; list unreachable spec states as missing.
A success message appears only after the server confirmed the change.

## 4. Data display

- Tables: `DataGrid` / `ListingPage`; numeric columns `tabular-nums` and
  end-aligned; long values truncate with a way to the full value.
- Pills and status: Plenix pills; never color alone; equal height in a row.
- Case numbers `YYYYMMDD-##`, decree ids `DCR-...`, emails and ids stay Latin
  and readable in RTL (`dir="auto"`).
- Dates and numbers through `Intl` (`en-US`, `ar-EG`); civil dates never shift
  by time zone.

## 5. Words

All messages follow `docs/content/messaging.md`; terms come from
`docs/implementation/glossary.md`; every string exists in English and Arabic
(`docs/i18n/arabic.md`). Buttons name action and object ("Issue decree").

## 6. Accessibility

WCAG 2.2 AA: keyboard reachable, visible focus, labelled controls, focus
trapped in dialogs and returned, focus to the heading on route change, errors
announced, 320px width and 200% zoom without clipping.

## 7. Screenshots and pictures

Checks take English desktop screenshots by default; mobile when the change
affects layout; Arabic when it changes text or direction. Every screenshot a
check takes is shared (PR, issue, dashboard). Pictures, mock-ups or variants
are made **only when the owner asks**.
