# core-353: council member photos (G2 design)

Issue: LighthouseCollection/CTM#353. Spec: G1 in the PM's comment on #353 (option A: upload in Settings > Users & Roles).
Gate: G2, Design Director. Design only: no app code, no pictures (D-0004). Storage, URLs and permissions are G3 (Architect).

- **Plenix:** the version pinned by `PLENIX_BASE` in `ctm/settings.py` (1.8.0 when this was written). Every component
  below was read on its published spec page at that version. No CTM CSS, no inline styles, no new tokens.
- **Settings > Users itself is not decided.** Its redesign (#328, variations in PR #331) is on hold and will be redone.
  So the photo control is **one self-contained block** that drops into whatever layout is picked (see "Where the control
  lives"). It does not depend on a table, list, panel or card.

## Plenix components

| Component | Spec page | Use here |
|---|---|---|
| `AvatarUpload` | avatar-upload.md | The control: shows the current photo (or initials), Add / Change photo, Remove photo, client-side type and size refusal |
| `Field` | field.md | Wraps the control: visible label, help text, the error line |
| `FileInput` | file-input.md | Only as used inside `AvatarUpload` (its picker); CTM does not place one directly |
| `Spinner` | spinner.md | `size="sm"` beside the control while a change saves; label for assistive technology only |
| `ConfirmDialog` | confirmation-dialog.md | Confirms Remove photo (`destructive`) |
| `Dialog` | confirmation-dialog.md | Hosts the control from a row or card menu (`size="sm"`), when the layout has no details panel |
| `ActionMenu` | action-menu.md | The existing row or card menu gets one item, "Council photo" |
| `SettingsSection` | settings-page.md | Hosts the control inside a person's details panel, when the layout has one |
| `Notice` | notice.md | save failures (with Retry), forbidden, conflict, not seated |
| `Toast` | toast.md | "Photo saved." / "Photo removed." only after the server confirmed |
| `Avatar` | avatar.md | The photo on the Presiding fact and in the Settings list |
| `MetricCard` | metric-card.md | Council Home member tiles, `type="person"`, `person.src` |
| `UserCard` | user-card.md | Attendance rosters, `variant="compact"`, `src` |
| `Button` | button.md | Only the `xs` Retry inside a failure `Notice`; every other button is inside `AvatarUpload` or `ConfirmDialog` |

## The control

```jsx
<Field label={t("photoFieldLabel")} description={t("photoFieldHelp")} error={photoError}>
  <AvatarUpload name={fullName} src={photoUrl || undefined}
    size="2xl" actions="buttons" crop={false} removable
    accept="image/png,image/jpeg" maxSize={2097152}
    disabled={saving}
    strings={{ add: t("photoAdd"), change: t("photoChange"), remove: t("photoRemove"),
               tooLarge: t("photoTooLarge"), notImage: t("photoNotImage"), picture: t("photoAlt") }}
    onChange={(pic) => (pic ? upload(pic.file) : askRemove())} />
</Field>
```

- **Why these settings.** `crop={false}`: G1 P1, no in-app cropping; Plenix `Avatar` shows a fixed square. `accept` and
  `maxSize`: G1 P0 (JPEG or PNG, 2 MB); the component refuses early, and the server checks again by content.
  `actions="buttons"`: the words "Add photo" / "Change photo" / "Remove photo" stay visible (not hidden in a corner icon),
  which reads better in a settings surface and in Arabic. `size="2xl"`: the component's default with buttons.
- **The picture changes only after the server confirms.** `src` is the saved photo's URL from the API. The chosen file is
  never shown as if saved (never fake success). While saving, the old photo stays, the control is `disabled` and a
  `Spinner size="sm"` with `label={t("photoSaving")}` sits after the control. On success the API returns the new URL,
  `src` updates and a success `Toast` shows.
- **Replace is Add again.** "Change photo" opens the picker; the new photo replaces the old one when the server accepts
  it. No confirmation: the result is visible at once and the person can change it again (every change is audited).
- **Remove asks first.** `onChange(null)` (the component's Remove photo) opens a `ConfirmDialog destructive` with
  title `photoRemoveTitle`, message `photoRemoveMessage`, confirm label `photoRemove`, cancel the existing `cancel` key.
  Cancel leaves the photo unchanged. Confirm sends the removal; the photo goes only after the server answers.
- **One action at a time.** While a change saves, nothing else in the control can start.
- **Who sees the control.** Only people with the right to change photos (admin, secretary, president; the API's
  `can_edit`, decided in G3). For everyone else the control is not drawn at all (hidden, not disabled: DESIGN.md §3);
  they see the photo only where the display surfaces show it.
- **Which accounts.** Add / Change photo only for an account that holds a council seat. Remove photo stays available on
  any account that still has a photo (for example after its seat was taken away), so an unseated person's photo can
  always be cleared. For an unseated account with no photo the control is not drawn.

## Where the control lives

One rule for any layout: **if the picked Users layout has a details surface for one person, the control is the first
row of that surface's council seat section (a `SettingsSection`), above the seat switches. Otherwise the person's row
or card menu (`ActionMenu`) gets the item "Council photo" (`photoFieldLabel`), which opens a `Dialog size="sm"` titled
"Council photo" whose body is the control.** The dialog has no footer: each change saves on its own, and Plenix's close
button, Escape and the veil close it. Focus returns to the menu button (Plenix).

| Layout | Host | Notes |
|---|---|---|
| Today | Row menu item, then `Dialog` | Today's Users table already has a row menu; the item shows only on seated rows (or rows with a photo) and only with `can_edit` |
| A | Row menu item, then `Dialog` | Table rows stay one line; the list's `avatar-name` cell shows the saved photo |
| B | The details panel's council seat section | First row, above Council seat and Voting; the list row's avatar shows the saved photo |
| C | Row menu item, then `Dialog` | Same as A |
| D | Card menu item, then `Dialog` | The card's own avatar (`UserCard src`) shows the saved photo; the card does not grow |

A redesign done from scratch follows the same rule; it adds nothing to the list row itself (no upload button in a row).

## Where the photo shows

Only signed-in staff surfaces. **Applicants never** receive a council photo, its URL or any hint of it (pages, API,
search, counts, downloads; CLAUDE.md permission rule). Not on documents, decrees, reports, PDFs, emails, exports or the
audit log (the log records actor, time and account, never the image).

| Surface | Component | With a photo | Without one |
|---|---|---|---|
| Presiding fact, session header (#220, PR #352) | `Avatar size="sm"` beside the visible name | `src` = the president's photo URL | The person icon fact, as today |
| Council Home, member tiles | `MetricCard type="person"` | `person.src` = the member's photo URL | As today (Plenix person card without a picture) |
| Attendance roster and hearing attendance | `UserCard variant="compact"` | `src` = the member's photo URL | As today |
| Settings > Users list | The picked layout's avatar (`Avatar`, `UserCard`) | `src` = the photo URL | Initials (Plenix `Avatar` default) |

- **Decorative beside the name.** On every display surface the visible name is right next to the photo, so the photo is
  decorative (no `label` on `Avatar`, empty alt), as G5c accepted on #352. Only inside the control does the picture carry
  a name (`photoAlt`), because there it is the thing being changed.
- **Same size as today.** Each surface keeps its current avatar size; a photo replaces the initials or icon in place, so
  no layout moves when photos arrive.
- **Former members** (shown in attendance history) show their photo while one is stored, like any other staff member.

## States

Control states first, then display states. "Reachable" lists what the builder must build; a state the code cannot reach
is listed as missing in the build PR (DESIGN.md §3).

| State | What the person sees | Plenix | Reachable |
|---|---|---|---|
| No photo | Initials in the square; "Add photo"; help text under it | `AvatarUpload` (no `src`), `Field` | Yes |
| Has photo | The saved photo; "Change photo" and "Remove photo" | `AvatarUpload src` | Yes |
| Uploading | Old photo (or initials) stays; control disabled; small spinner after it, announced "Saving photo" | `disabled`, `Spinner size="sm"` | Yes |
| Saved | New photo in the square; success toast "Photo saved." | `Toast` tone success | Yes |
| Too large | Nothing sent; the field error says the limit | `AvatarUpload` `tooLarge` (client); `Field error` for the server's refusal | Yes |
| Not JPEG or PNG | Nothing saved; the field error asks for a JPEG or PNG | `notImage` (client, by type); `Field error` `photoWrongContent` (server, by content) | Yes |
| Remove: confirm | Dialog: "Remove {name}'s council photo?", Remove photo / Cancel | `ConfirmDialog destructive` | Yes |
| Removing | Photo stays; control disabled; spinner, announced "Saving photo" | `disabled`, `Spinner` | Yes |
| Removed | Initials in the square; toast "Photo removed." | `Toast` tone success | Yes |
| Network or server error | Old photo stays; a danger notice under the field with Retry, which resends the same file (or the same removal) | `Notice tone="danger"` + `Button size="xs"` | Yes |
| Forbidden | The server refused (rights changed meanwhile): danger notice, no data hints; the control goes away on reload | `Notice tone="danger"` `photoForbidden` | Yes |
| Not seated | The seat was taken away meanwhile and the server refused an upload: info notice; Remove stays if a photo exists | `Notice tone="info"` `photoNotSeated` | Yes |
| Conflict | Someone else changed the photo first (only if G3 versions photos): warning notice, the current photo is shown | `Notice tone="warning"` `photoConflict` | If G3 adds a version |
| Read-only | Member role or no `can_edit`: no control; the photo shows only on display surfaces | (not drawn) | Yes |
| Photo fails to load | The URL no longer loads (removed, expired or refused): the surface shows its "without a photo" look, never a broken image | `Avatar` fallback | Yes; builder verifies Plenix falls back, else a Plenix request |

Display surfaces have two states each, "with a photo" and "without one" (table above), plus "Photo fails to load".
Loading on display surfaces is the surface's own loading; the photo adds none.

## Words

English text, its key, and where it sits. **Arabic:** the i18n engineer proposes every Arabic string at build time and
adds the rows to `docs/i18n/arabic-proposals.md` (D-0012); this design writes none. The technical writer checks the
English against `docs/content/messaging.md` (G7). `{name}` is the person's name and `{max}` the size limit, formatted
through `Intl` for the language (Arabic-Indic digits in Arabic, `docs/i18n/arabic.md`); the builder isolates `{name}`
so a Latin name reads correctly inside an Arabic sentence. Plenix mirrors the control, dialog, notices and toasts in RTL;
CTM adds nothing for direction.

| Key | English | Placement (EN; RTL mirrors) |
|---|---|---|
| `photoFieldLabel` | Council photo | Field label above the control, at the start side; also the menu item and the dialog title |
| `photoFieldHelp` | JPEG or PNG, up to {max}. Only council staff see it. | Field help text under the control |
| `photoAdd` | Add photo | `AvatarUpload` button beside the square, at its end side |
| `photoChange` | Change photo | Same place, when a photo exists |
| `photoRemove` | Remove photo | Next to Change photo; also the confirm button of the remove dialog |
| `photoAlt` | {name}'s photo | The picture's accessible name inside the control only (not drawn) |
| `photoTooLarge` | The photo is larger than {max}. Choose a smaller file. | Field error line under the control |
| `photoNotImage` | Choose a JPEG or PNG photo. | Field error line under the control |
| `photoWrongContent` | This file isn't a JPEG or PNG photo. Choose another file. | Field error line (server check by content) |
| `photoSaving` | Saving photo | Spinner label for assistive technology only |
| `photoSaved` | Photo saved. | Success toast |
| `photoRemoveTitle` | Remove {name}'s council photo? | Remove dialog title |
| `photoRemoveMessage` | The council tiles and the Presiding card will show the person icon instead. You can add a new photo at any time. | Remove dialog message |
| `photoRemoved` | Photo removed. | Success toast |
| `photoSaveFailed` | The photo wasn't saved. Check your connection, then try again. | Danger notice under the field, with the existing `retry` key ("Retry") on its button |
| `photoRemoveFailed` | The photo wasn't removed. Try again. | Same notice, after a failed removal |
| `photoForbidden` | You can't change council photos. | Danger notice in place of the control |
| `photoNotSeated` | Only council seat holders can have a council photo. | Info notice under the field |
| `photoConflict` | Someone else changed this photo. The current photo is shown. | Warning notice under the field |

Existing keys reused: `cancel` (remove dialog), `retry` (failure notice). The seat words stay as they are.

## Accessibility

- Keyboard: every action is a Plenix button inside `AvatarUpload`, the menu item, or the dialog; focus is trapped in
  dialogs and returns to the opener (Plenix).
- Errors: the `Field` error is tied to the control and announced; notices use their Plenix roles.
- Saving: the spinner's label is announced; the success toast is announced (Plenix).
- 320 width and 200% zoom: `AvatarUpload` wraps its buttons under the square (Plenix); the builder checks it.

## For G3 (Architect) and the builder

- The API gives, per staff account, `photo_url` (or null) and whether the caller may change it; the upload and removal
  answers return the new `photo_url` (or null) so the control can update without a second request.
- The upload refusals need distinct codes the UI can map to `photoTooLarge`, `photoWrongContent`, `photoNotSeated`,
  `photoForbidden` and (if versioned) `photoConflict`; anything else is `photoSaveFailed`.
- If photo URLs expire, display surfaces need fresh URLs on each load; "Photo fails to load" covers the gap.
- The builder must not invent: other file types or sizes, a crop step, a photo on applicant-facing or document surfaces,
  a corner-icon variant, or any Arabic text.
