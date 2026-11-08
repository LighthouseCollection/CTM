# #240 — spouse cards (D-0057, part of the #217 sweep)

Owner, 2026-11-07: "this is crap. 1) card is not consistent 2) the title in the card should only be name of person with indicator who is applicant and who is [respondent] 3) also the expand/collapse arrow not consistent to card". Plenix 0.93.1. The D-0050 and D-0055 styles come from Plenix, with no CTM CSS. Desktop only, EN/AR, RTL.

## One `Panel` per spouse (`council-case.js` `CaseParties`)

| Part | Plenix | Content |
|---|---|---|
| Card | `Panel collapsible`, controlled by `expanded` / `onToggle` | The same header, body and spacing as every case card. Remove the custom wide row, `spouseHeaderTitle`, the bare › and the separate "Spouses" section heading. The page title stays |
| Media | `Panel.icon` = `Avatar size="sm"` with `name` and `src` (the photo, or initials when there's none) | The icon spot at the start of the header, per Plenix's "icon left of the heading" rule |
| Title | `Panel.title` = `Inline gap="sm"`: the name (plain text) + `Badge` **Applicant** / **Respondent** (`tone="neutral"`, icon `person`) | Nothing else in the title. `strings`: `{ collapse: "Collapse {name}", expand: "Expand {name}" }`, with the name filled in, since the title is not plain text |
| Actions | `Panel.actions` = **Change photo** (see below), then `Button size="sm"` **Edit** | Only for users who may change them. No other header controls |
| Body | Read-only fields (D-0050) in the groups from `groups.md` | **Personal details**: CTM ID (body text, **not** `data`/monospace; `dir="auto"`), portal account (`Badge` Registered / Not registered, with icon), other names, place of birth, nationality, awareness of application. **Contact**: address, mobile, email, immigration status, residing with. **Career**: education, year of graduation, occupation. **Church affiliation**: denomination, bishop, diocese, parish, father of confession. Group heading = `SectionHeading` (see #217). Show only fields CTM stores; date of birth only if the API provides it |
| Edit mode | The same card. The body becomes `Form` + `FormSection` per group, field for field, with `FormActions` Save/Cancel at the end | Contact keeps its own save, but it is moved inside the same edit form so there is one Edit. Change photo is **not** in Edit |

**Order:** the applicant card first, then the respondent. **Expanded by default: both**, because the council compares the two spouses side by side in reading order. Each user's choice is remembered per case with Plenix `useViewState` (key `case:{id}:spouse:{partyId}`).

**Add spouse** (managers, as today) stays below the cards as its own `Panel` with the D-0055 heading. It is not changed here.

## Change photo (owner correction 2026-11-07, applies to spouses, council member cards and My Account)

Discreet, never a full button, never inside Edit, and only for users who may change the photo.

- **Target (Plenix, PLX-027, https://github.com/plenix-ds/pds/issues/977):** a small round icon button in the photo's bottom-end corner, quiet at rest and shown on hover or focus, with the tooltip and name "Change photo". CTM switches to it when it ships.
- **Until then** (no CTM CSS, so no overlay):
  - **Spouse card header:** the first item in `Panel.actions` is `Button variant="ghost" size="sm" icon="photo_camera"`, icon-only, with `aria-label` and `Tooltip` "Change photo" / "تغيير الصورة".
  - **Council member cards and My Account** (a larger photo with room below): `Button variant="ghost" size="sm"` with the text "Change photo", centred under the photo. This is the smallest Plenix action, since Plenix has no link look for actions.
- **Both** open the existing photo flow (`AvatarUpload` file and crop, in a `Dialog`) and save the same way as today.

## States

Loading: `Skeleton` card ×2. No spouses: `EmptyState` "No spouses on this case" (existing `noParties`). Error: `Notice` + retry. Read-only (closed case): no Edit. Save failure: `Notice` inside the edit form, keeping the input.

## Tests (frontend)

- Each spouse renders a `P.Panel` with `collapsible: true`.
- The title holds only the name and a role `Badge`.
- No `variant: "data"` on the CTM ID.
- Change photo is a ghost size "sm" button (icon-only in card headers) and is not inside the edit form.
- The `spouseHeaderTitle` helper is gone.
