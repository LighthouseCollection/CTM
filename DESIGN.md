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
- The app opens in the 1366px frame: `AppShell frame="centered"` (D-0063, owner
  D-0093 in Plenix). People expand it to the full window and back with the
  header's toggle, remembered per person. A page that should be narrow gets it
  from its page kind (form, settings); a page that looks cramped is fixed in its
  own layout, never by dropping the frame.
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

### Read-only fields and card headings (D-0050, owner 2026-11-07, #195, plenix-ds/pds#946)

The owner chose this from the study `docs/design/read-only-field-study.html`
(open it in a browser; the ★ preset is the decision, every other preset is a
rejected alternative kept for reference). Plenix implements it as the default
read-only field and card styles; CTM uses those components and adds no CSS.

| Level | Decision |
|---|---|
| Card heading | 14 px, bold, dark grey (secondary ink), UPPERCASE, icon shown; soft vertical glow from the card top to the heading line in the field tint; line under the heading **inset** (not edge to edge) |
| Group heading (Case, Parties, Marriage …) | 13 px, medium, gold, sentence case, no line; 40 px above each group |
| Field label | 11 px, regular, diocese navy (brand), sentence case |
| Value | 13 px, semibold, dark grey (secondary ink) |
| Field surface | each field on a porcelain tile (very soft warm neutral, not yellow) with a 1 px border in a deeper shade of the same tint; never the grey used for card borders |
| Status | a Plenix status badge, never plain text |

Rules that come with it: the label is always lighter than its value; label
and value colours keep at least 4.5 : 1 contrast on the tile (navy about
8 : 1); every level stays distinct (card heading › group heading › value ›
label). The owner chose label 11 px and value 13 px knowing the study flags
them under the 12 px / 14 px readability guidance; the decision stands.

**Section headings (D-0055, owner 2026-11-07).** A heading that introduces a
table or a block of content on a page (for example "Hearings" and "To assign"
on a session page) uses the **card heading** style above: 14 px, bold, dark
grey, UPPERCASE, with its icon. Never a separate, smaller "page section" style.
Where a page has several such sections, each section is its own card: the
heading is the card header (glow, inset line) and the table sits inside the
card body. The session agenda (Hearings, To assign) is built this way.

### Case timeline (D-0058, owner 2026-11-07, #242)

Decided from `docs/design/timeline-study.html` (open it in a browser; its
defaults are the decision). Plenix ships it as a Timeline variation
("grouped by year, by category"); CTM uses that component.

- **Grouped by year**, latest year first. Each year starts with the year as a
  heading (20 px bold, secondary ink) and a 72 px x 2 px soft line under it;
  80 px between years; no dividing rule.
- **Watermark year:** beside every event card, a very faint copy of the year
  (about 7% ink), rotated, centred on the card and left-aligned with the year
  heading; 8 px from the card. It never overlaps the heading or another mark.
- **Each event is its own container** (6 px radius, Plenix card radius): a soft
  tint of its case-area colour with a matching faint border, the title in the
  area colour, the description in secondary ink, and the area label on the
  end side. Upcoming events have a dashed outline. No timeline dots.
- **Date** sits at the start of the container inside a calendar icon (6 px
  corners): a top band in the case-area colour with two binder rings, the
  month in extra-bold uppercase and the day large and bold. Upcoming events
  show a grey band and "Pending". The date column is as wide as the widest
  date; 10 px to the event.
- **Case areas and colours** (light / dark tokens, Plenix category set):
  Marriage (plum), Application (slate), Filing (teal), Assignment (violet),
  Interviews & hearings (copper), Council decision (navy), Decree (green),
  Communications (gold). A legend can filter areas.

**Three heading levels, never mixed (applies D-0050/D-0055, #217):**

| Heading | What it is | Plenix |
|---|---|---|
| **Page title** | Names the page; one per page; it receives focus on route change (§6). Kept even when the nav names the page | The page template's own title: `RecordPage.Header`, `ListingPage` title, `SettingsLayout` title, or for My Account the profile header. Never restyled as a card heading |
| **Card heading** | Introduces one block (table, fields, form) | `Panel` title (D-0055) |
| **Group heading** | Groups fields inside a card, **or** groups several cards that belong together (for example one card per recording) | `SectionHeading` (D-0050 group style); a card never holds cards |

A page with a single full-height list keeps the list as the page's listing
under the page title, with no card around it, so the fill layout stays. A page
with several sections (for example Security sessions plus Audit) puts each
section in its own `Panel`. The list inside then uses `DataGrid mode="pages"`
in place of fill.

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
