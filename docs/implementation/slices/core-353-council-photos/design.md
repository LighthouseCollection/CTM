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
| `Notice` | notice.md | save failures (with Try again), forbidden, conflict (with Use my photo), not seated |
| `Toast` | toast.md | "Photo saved." / "Photo removed." only after the server confirmed |
| `Avatar` | avatar.md | The photo in a Settings > Users layout that already draws an avatar (`src`) |
| `EntityHeader` | record-page.md | The session header's Presiding fact, unchanged: facts are `{ icon, label, value, action }` with no picture option, so it keeps its person icon (PLX-028) |
| `MetricCard` | metric-card.md | Council Home member tiles, `type="person"`, `person.src` |
| `UserCard` | user-card.md | Attendance rosters, `variant="compact"`, `src` |
| `Button` | button.md | Only the `xs` buttons inside a `Notice` (Try again, Use my photo); every other button is inside `AvatarUpload` or `ConfirmDialog` |

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
| Today | Row menu item, then `Dialog` | Today's Users table already has a row menu; the item shows only on seated rows (or rows with a photo) and only with `can_edit`. Its name column draws no avatar today (`ui-workspaces.js`, `columns`), and this design adds none: the photo shows in the control only |
| A | Row menu item, then `Dialog` | Table rows stay one line; if the layout's name cell draws an avatar, it shows the saved photo |
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
| Presiding fact, session header (#220, PR #352) | `EntityHeader` fact `{ icon, label, value, action }` (record-page.md, Header style 2) | **No photo yet.** The 1.8.0 spec documents no picture, `src` or element in a fact, so the fact keeps its person icon and the president's name. Requested as PLX-028; the builder adds the photo only once Plenix documents it | The person icon fact, as today |
| Council Home, member tiles | `MetricCard type="person"` | `person.src` = the member's photo URL | As today (Plenix person card without a picture) |
| Attendance roster and hearing attendance | `UserCard variant="compact"` | `src` = the member's photo URL | As today |
| Settings > Users list | `Avatar` or `UserCard`, only in a layout that already draws one (today's list draws none) | `src` = the photo URL | That layout's initials (Plenix `Avatar` default) |

- **G1 AC-353-4, Presiding card.** Until PLX-028 is met, the Presiding card shows the name with the person icon, which
  is the G1 fallback look. The tiles and rosters show the photo now. The builder must not draw a picture into the fact
  by hand (no element in `value`, no CSS).
- **Decorative beside the name.** On every display surface the visible name is right next to the photo, so the photo is
  decorative (no `label` on `Avatar`, empty alt), as G5c accepted on #352. Only inside the control does the picture carry
  a name (`photoAlt`), because there it is the thing being changed.
- **No new avatars.** A photo goes only where a surface already draws a person picture (`MetricCard` person, `UserCard`,
  a Users layout's `Avatar`), at that surface's current size, in place of its initials or icon. No layout moves when
  photos arrive. Surfaces that draw only an icon or a name (the Presiding fact, today's Users list) stay as they are.
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
| Network or server error | Old photo stays; a danger notice under the field with Try again (`retry`), which resends the same file (or the same removal); the chosen file is kept until then | `Notice tone="danger"` + `Button size="xs"` | Yes |
| Forbidden | The server refused (rights changed meanwhile): danger notice, no data hints; the control goes away on reload | `Notice tone="danger"` `photoForbidden` | Yes |
| Not seated | The seat was taken away meanwhile and the server refused an upload: info notice; Remove stays if a photo exists | `Notice tone="info"` `photoNotSeated` | Yes |
| Conflict | Someone else changed or removed the photo first (only if G3 versions photos). The square shows the current saved photo (or initials); a warning notice names who changed it ({actor}). The person's chosen file is kept in the page (not shown as saved) and the notice's "Use my photo" button (`photoUseMine`) sends it again against the new version; dismissing the notice drops it. A conflicting removal has nothing to keep: the notice alone | `Notice tone="warning"` `photoConflict` + `actions` `Button size="xs"` | If G3 adds a version |
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
| `photoSaveFailed` | The photo wasn't saved. Check your connection. | Danger notice under the field; its button is the existing `retry` key ("Try again") |
| `photoRemoveFailed` | The photo wasn't removed. Check your connection. | Same notice and button, after a failed removal |
| `photoForbidden` | You can't change council photos. | Danger notice in place of the control |
| `photoNotSeated` | Only council seat holders can have a council photo. | Info notice under the field |
| `photoConflict` | {actor} changed this photo first. Theirs is shown; yours wasn't saved. | Warning notice under the field |
| `photoUseMine` | Use my photo | The conflict notice's button, at its end side; sends the kept file again |

Existing keys reused: `cancel` (remove dialog) and `retry` ("Try again") on the failure notice's button (`app.js`, `council.js`).
The seat words stay as they are. `{actor}` is the other person's name, isolated like `{name}`. The notices follow
`docs/content/messaging.md`: what happened, then the fix, with the action on the button rather than repeated in the text.

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
  `photoForbidden` and (if versioned) `photoConflict`; anything else is `photoSaveFailed`. A conflict answer carries
  the current `photo_url`, its version and the name of who changed it (for `{actor}`).
- If photo URLs expire, display surfaces need fresh URLs on each load; "Photo fails to load" covers the gap.
- Plenix request PLX-028 (`docs/implementation/plenix-requests.md`): a picture in an `EntityHeader` fact. Until it is
  documented, the Presiding fact keeps its icon.
- The builder must not invent: other file types or sizes, a crop step, a photo on applicant-facing or document surfaces,
  a corner-icon variant, or any Arabic text.

---

# G3 architecture (Solution Architect)

Gate G3. Storage, API contract and permissions for the G2 design above. The decision record is
`docs/adr/0002-council-photos.md`; real request and response examples are in `contract/*.json` (fixtures come from
them, L-04). Checked by `tests/frontend/contract-353-council-photos.test.cjs`.

## G3.1 Approaches

| Approach | Verdict |
|---|---|
| **A. Append-only `CouncilPhotoChange` table + private files + versioned staff-only URL** | **Chosen.** Same shape as council seats (#175, D-0043): history, a version for conflicts, row security, the database clock. Outside every case table, so no case list, search or download can reach it |
| B. `Attachment` + `FileVersion` with a new category | Case-bound rows; `authorized_file` applies case rules and audits every view; reachable through `/api/files/` |
| C. A `photo` column on `Account` | No version (no G2 Conflict state), no history, mixes with account row security |
| D. Signed, expiring URLs | A signing key and refreshes on long-open pages, for no gain over a per-request check inside a signed-in session |

## G3.2 Data

New model in `tribunal/models.py` (database engineer), next to `CouncilSeatChange`:

```python
class CouncilPhotoChange(Immutable):
    """A council photo added, changed or removed (#353). Append-only; the latest version counts."""
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="photo_changes")
    version = models.PositiveIntegerField()                     # 1, 2, 3... per account
    object_key = models.CharField(max_length=250, null=True, unique=True)  # "council-photos/<uuid4 hex>.<jpg|png>"
    mime_type = models.CharField(max_length=20, null=True)     # image/jpeg | image/png
    byte_count = models.PositiveIntegerField(null=True)        # stored bytes, after metadata removal
    sha256 = models.CharField(max_length=64, null=True)        # of the stored bytes; the ETag
    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)
    actor = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="photo_changes_made")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["account", "version"], name="council_photo_version")]
        indexes = [models.Index(fields=["account", "-version"], name="council_photo_latest")]
```

- A **photo row** has every file field set; a **removal row** has every file field null (a check constraint).
  `photo_version` in the API is the latest `version`, or 0 when the account never had a change.
- Migration `tribunal/migrations/0080_council_photos.py` + `.sql` (0079 is taken by open PR #372; renumber if main moves):
  - Check constraint: removal (all null) or photo (`mime_type IN ('image/jpeg','image/png')`, `byte_count` 1 to
    2097152, `sha256 ~ '^[0-9a-f]{64}$'`, `width`/`height` 1 to 8000, `width*height <= 24000000`,
    `object_key LIKE 'council-photos/%'`).
  - Row security, `ENABLE` + `FORCE`, as `0073_council_seat_guards`: `photo_select` for active staff, not the worker
    (`ctm_council_photo_readable()`); `photo_insert` only when the actor role is admin, secretary or president,
    `actor_id = ctm_actor_id()`, the account's role is a staff role, and **for a photo row the account is seated now**
    (`ctm_council_seat(account)->>'seated'`) (`ctm_council_photo_writable(jsonb)`). Applicants read zero rows.
  - Triggers: `BEFORE INSERT` sets `created_at = clock_timestamp()` (unless the migration caller) and refuses a
    `version` other than the account's last version + 1; `BEFORE UPDATE OR DELETE` runs `ctm_reject_history_update()`.
  - Grants to `ctm_app`: `SELECT, INSERT` only, and `EXECUTE` on the two functions. `REVOKE ALL ... FROM PUBLIC`.
  - Reverse: drop the triggers, policies, functions and table.
- **Files:** `MEDIA_ROOT/council-photos/<uuid4 hex>.<jpg|png>`, written with `files.write_private_original` in
  `transaction.on_commit` (0600 file, 0700 folder). Never under `static/` or a `MEDIA_URL`. The pre-deploy restic
  snapshot of the media folder (`deploy/release.sh`) covers it. After a change commits, the previous photo's file is
  deleted (`on_commit`, missing file ignored); the rows keep the history without the image.
- **Audit:** `audit(actor, "council_photo_changed", change, metadata={"account_id", "version", "action": "set"|"removed",
  "mime_type", "byte_count"})`. No image, original file name or hash in the audit (G1 AC-353-5).

## G3.3 Service commands

New module `tribunal/services/council_photos.py` (engineer). Seat rules come from `council_seats.py`; nothing is copied.

```python
PHOTO_EDITORS = SEAT_EDITORS            # {"admin", "secretary", "president"}
MAX_BYTES = 2_097_152                   # G1 2 MB = G2 AvatarUpload maxSize
MAX_SIDE, MAX_PIXELS = 8000, 24_000_000 # browser decode guard; 12 MP phone photos and 24 MP cameras pass

class PhotoRefused(Exception):          # code, status, extra (dict merged into the JSON answer)

def photo_state(account) -> dict        # {"account_id", "photo_url", "photo_version", "changed_by": {"id","name"}|None, "changed_at"|None}
def photo_urls(account_ids) -> dict     # {account_id: url | None}, one query (latest version per account via Subquery)
def clean_image(data) -> CleanImage     # (mime, extension, data, width, height); raises PhotoRefused
def set_photo(actor, account_id, uploaded, expected_version) -> dict      # @transaction.atomic
def remove_photo(actor, account_id, expected_version) -> dict             # @transaction.atomic
def photo_for_delivery(actor, account_id, version) -> CouncilPhotoChange
def photo_rights(actor, seat, state) -> dict  # {"can_add_photo", "can_remove_photo"}
```

**`set_photo` order** (each step's refusal is in G3.6; nothing is stored or audited before the last steps):
1. `active(actor)`; `actor.role in PHOTO_EDITORS`, else `PermissionDenied` (403 `forbidden`). Before any lookup, so an
   applicant or member learns nothing about the target.
2. `expected_version`: a whole number >= 0 (not a bool, not text with spaces), else `expected_version_required`.
3. Size: `uploaded.size > MAX_BYTES` or more than `MAX_BYTES` bytes read (`uploaded.read(MAX_BYTES + 1)`) gives
   `photo_too_large` with `max_bytes`. The limit is the bytes received.
4. `Account.objects.get(pk=account_id, role__in=STAFF_ROLES)` (else 404). `lock_key(f"council-photo:{account.pk}")`.
5. Current state; `expected_version != photo_version` gives `photo_conflict` with `photo_state(account)`.
6. `council_seat(account)["seated"]`, else `not_seated`.
7. `clean_image(data)` (below). Bytes identical (`sha256`) to the current photo: return the current state, no row, no audit.
8. `files.scan(clean.data)`: `"rejected"` gives `photo_rejected`; `"pending"` gives `scan_unavailable`. Only `"clean"` goes on.
9. `with database_actor(actor):` insert the row (`version = photo_version + 1`); an `IntegrityError` on
   `council_photo_version` (a race) is answered as `photo_conflict` with the fresh state. `on_commit`: write the file,
   then delete the previous file. Audit. Return `photo_state(account)` (201).

**`remove_photo`:** steps 1, 2, 4, 5 as above (no seat check: G2 keeps Remove for an unseated account). No current photo:
return the current state (200, no row, no audit). Otherwise insert a removal row, `on_commit` delete the file, audit, 200.

**`clean_image` (content, not the name):** pure Python, no new dependency, pixels never decoded.
- **PNG:** the 8-byte signature; every chunk's length in bounds and CRC valid; `IHDR` first (width/height 1 to
  `MAX_SIDE`, `width*height <= MAX_PIXELS`, valid bit depth and colour type); at least one `IDAT`; `IEND` last with nothing
  after it. Unknown critical chunks (upper-case first letter) are refused. Kept: `IHDR PLTE IDAT IEND tRNS gAMA cHRM
  sRGB iCCP sBIT pHYs bKGD`. Every other ancillary chunk is dropped (`tEXt zTXt iTXt eXIf tIME`, and the animation
  chunks `acTL fcTL fdAT`, which leaves the still first frame).
- **JPEG:** `FFD8` first; every marker segment's length in bounds up to `SOS`; exactly one frame header, baseline or
  progressive (`SOF0`, `SOF1`, `SOF2`) with width/height in the limits above; entropy data runs to an `FFD9`; bytes after
  it are dropped. Kept: `APP0` (JFIF), `APP2` `ICC_PROFILE`, `APP14` Adobe, `DQT DHT DRI SOF SOS` and the scan data.
  Dropped: other `APP1` to `APP15` (EXIF with GPS, XMP, IPTC) and `COM`. If the dropped EXIF had an Orientation (tag
  `0x0112`, value 2 to 8), a minimal `APP1` EXIF holding only that tag is written back, so phone photos stay upright.
- Anything else, or any structure error: `photo_wrong_content`. Too many pixels: `photo_too_many_pixels`.
- The stored `mime_type`, `byte_count`, `sha256`, `width`, `height` describe the cleaned bytes.

**`photo_for_delivery`:** `staff(actor)` first (applicants 403, before any lookup). The latest row for the account; none,
a removal row, or `version` not the latest gives `photo_unavailable` (404).

## G3.4 Authorization and derivative surfaces

| Who | Upload / change | Remove | See a photo (URL and bytes) |
|---|---|---|---|
| Admin, secretary, president | Seated accounts only (service step 6 + RLS) | Any staff account that has a photo | Yes |
| Member | 403 `forbidden` | 403 `forbidden` | Yes |
| Applicant | 403 `forbidden` | 403 `forbidden` | **Never:** 403 on every photo URL; no payload an applicant can call carries a council `photo_url` (AC-353-3) |
| Worker (Celery) | No (RLS) | No (RLS) | No (RLS) |
| Signed out | 401 | 401 | 401 |

Derivatives, per `build-spec/permissions.md`:
- **Search, counts, case files, downloads, documents, reports, exports, emails:** a council photo is in none of their
  tables, and `/api/files/` cannot serve it (it is not a `FileVersion`). No change to those code paths.
- **Payloads that gain `photo_url`** are all staff-only today and stay so: `GET /api/council/seats/` (`seat_list`,
  `staff()`), `GET /api/dashboard/members/` (`members_summary`, `staff()`), the attendance roster
  (`_roster_row` in `api.attendance`, `staff()`). The test suite proves an applicant gets 403 on each (contract
  `get-seats.json`, `get-display-rows.json`) and that no applicant-callable response contains `/api/council/photos/`.
- **Not added (G2):** the Presiding fact (`presiding_member_*` in `projections.py`) stays without a photo until PLX-028;
  the case-assignment picker (`GET /api/members/`, `council-case.js` member options) is not a G2 surface and is left as it is.
- **Viewing is not audited** (ADR 0002): decorative staff-directory image, shown on every Home load. Changes are audited.
- **The image itself:** metadata (GPS and camera EXIF, XMP, IPTC, text) is removed before storage; served with
  `nosniff`, a `sandbox` CSP and `Cross-Origin-Resource-Policy: same-origin`, so it cannot run as a page or be embedded
  by another site.

## G3.5 API contract

Routes in `ctm/urls.py` (engineer), views in `tribunal/api.py` with `@endpoint`, CSRF as every other session write:

| Method and path | View | Body / query | Success | Example |
|---|---|---|---|---|
| `POST /api/council/photos/<uuid:account_id>/` | `council_photo` | multipart: `photo` (file), `expected_version` | 201 `photo_state` | `contract/post-photo.json` |
| `DELETE /api/council/photos/<uuid:account_id>/` | `council_photo` | `?expected_version=N` | 200 `photo_state` | `contract/delete-photo.json` |
| `GET` / `HEAD /api/council/photos/<uuid:account_id>/<int:version>/` | `council_photo_file` | `If-None-Match` | 200 image / 304 | `contract/get-photo.json`, `contract/get-photo-applicant.json` |
| `GET /api/council/seats/` (existing) | `council_seats` | none | rows gain `photo_url`, `photo_version`, `can_add_photo`, `can_remove_photo` | `contract/get-seats.json` |
| `GET /api/dashboard/members/`, attendance roster (existing) | unchanged views | none | `photo_url` from `photo_urls()` instead of `None` | `contract/get-display-rows.json` |

- `photo_url` is always `/api/council/photos/<account_id>/<photo_version>/` or `null`. It changes on every change, so
  no cache shows a replaced photo; an old URL answers 404 and the surface shows its fallback (G2 "Photo fails to load").
  URLs never expire; a long-open page keeps working until the photo changes.
- `photo_state` answer: `{"account_id", "photo_url", "photo_version", "changed_by": {"id", "name"} | null, "changed_at" | null}`.
  The control sets `AvatarUpload src` from `photo_url` and keeps `photo_version` for the next `expected_version`.
- Image answer headers: `Content-Type` (stored type), `Content-Length`, `Content-Disposition: inline`,
  `Cache-Control: private, no-cache`, `ETag: "<sha256>"`, `X-Content-Type-Options: nosniff`,
  `Content-Security-Policy: default-src 'none'; sandbox`, `Cross-Origin-Resource-Policy: same-origin`. A matching
  `If-None-Match` answers 304 after the permission check. No range requests.
- The photo views answer their own codes: they catch `PhotoRefused` and return `{"error": code, **extra}` with its
  status. `@endpoint` keeps 401, 403 `forbidden` (from `PermissionDenied`) and 404 `resource_or_input_invalid`. The
  generic `@endpoint` mapping is not changed.

## G3.6 Failure paths

The control maps the `error` code to a G2 word (`max_bytes` fills `{max}`, formatted through `Intl`; `changed_by.name`
fills `{actor}`). A network failure or any code not listed is `photoSaveFailed` (upload) or `photoRemoveFailed` (removal).

| Status | Code | G2 word | When | State after |
|---|---|---|---|---|
| 422 | `photo_too_large` | `photoTooLarge` | More than `max_bytes` (2097152) received | Nothing stored |
| 422 | `photo_wrong_content` | `photoWrongContent` | Not a well-formed JPEG or PNG by its bytes, whatever the name or declared type | Nothing stored |
| 422 | `photo_too_many_pixels` | `photoTooLarge` | Wider or taller than 8000, or over 24 million pixels (see G3.9) | Nothing stored |
| 422 | `not_seated` | `photoNotSeated` | Upload for an account without a seat now | Nothing stored; Remove still works |
| 403 | `forbidden` | `photoForbidden` | Caller is not admin, secretary or president (or is an applicant) | Nothing stored |
| 409 | `photo_conflict` | `photoConflict` | `expected_version` is not the current version, or a concurrent insert won; answer carries the current `photo_url`, `photo_version`, `changed_by`, `changed_at` | Nothing stored; G2 "Use my photo" resends with the new version |
| 422 | `photo_rejected` | `photoWrongContent` | The safety scan refused the file | Nothing stored |
| 503 | `scan_unavailable` | `photoSaveFailed` | The safety scan could not run (never stored unscanned) | Nothing stored; Try again |
| 422 | `expected_version_required` | `photoSaveFailed` | `expected_version` missing or not a whole number >= 0 (a client bug) | Nothing stored |
| 404 | `resource_or_input_invalid` | `photoSaveFailed` | Unknown account, or not a staff account | Nothing stored |

Delivery (display surfaces never show these; Plenix falls back to initials or the icon): 403 `forbidden` (applicant or
signed-out 401), 404 `photo_unavailable` (not the current version, or removed), 503 `source_unavailable` (file missing
or its size differs from `byte_count`).

Server limit for the record: `max_bytes` = 2097152 (G1 2 MB, G2 `maxSize={2097152}`).

## G3.7 Owners

```owners
architect: docs/implementation/slices/core-353-council-photos/contract/*.json, docs/adr/0002-council-photos.md, tests/frontend/contract-353-council-photos.test.cjs
design: docs/implementation/plenix-requests.md, tests/frontend/design-353-council-photos.test.cjs
database: tribunal/models.py, tribunal/migrations/0080_council_photos.py, tribunal/migrations/0080_council_photos.sql, tests/test_council_photo_rls.py
backend: tribunal/services/council_photos.py, tribunal/services/council_seats.py, tribunal/services/home.py, tribunal/api.py, ctm/urls.py, tests/test_council_photos.py, tests/test_council_photo_image.py, tests/test_council_photo_privacy.py, tests/fixtures/council-photos/*
frontend: static/ctm/ui-workspaces.js, tests/frontend/council-photo-control.test.cjs
i18n: docs/i18n/arabic-proposals.md
```

The slice folder (this file, `contract/`, `evidence.md`) is shared. `council.js` (Home tiles, rosters) needs no change:
it already passes `row.photo_url` to `MetricCard person.src` and `UserCard src`. The database PR carries the label
`agent:ctm3-database-engineer` (`scripts/db_owner_guard.cjs`).

## G3.8 Tasks

Test-first: red, then green, with both outputs in the PR. Run `uv run pytest --ds=ctm.settings_postgres_test -q <file>`
(needs `CTM_TEST_DATABASE_URL`) and `node --test <file>`.

**T1. database: table, row security, migration.** Files: the `database` row. Depends: none.
- Tests first in `tests/test_council_photo_rls.py`, as the `ctm_app` role: staff read rows, an applicant reads none, the
  worker reads none; a member's insert is refused; an editor inserting as someone else is refused; a photo row for an
  unseated account is refused, a removal row for it is allowed; a skipped version is refused; update and delete are
  refused; `created_at` is the database clock; the check constraint refuses a half-filled row.
- Then the model, `0080_council_photos.py` + `.sql`, `makemigrations --check`, `check_migration_diff.cjs`.

**T2. backend: service, image check, API, payloads.** Files: the `backend` row. Depends: T1 merged (or on its branch).
- `tests/test_council_photo_image.py` first: small synthetic JPEG and PNG fixtures built in the test (no real photos,
  the repository is public): a PNG with `tEXt` and `eXIf` comes back without them; a JPEG with EXIF GPS and
  Orientation 6 comes back with only the Orientation; a PDF or GIF renamed `.jpg` is `photo_wrong_content`; a broken
  CRC, a truncated JPEG, an unknown critical PNG chunk, data after `IEND` (dropped), 8001 pixels wide and 5000x5000
  are each refused or cleaned as G3.3 says.
- `tests/test_council_photos.py` first, from `contract/*.json`: every row of the G3.6 table; 201 and 200 answers match
  `post-photo.json` and `delete-photo.json`; no-op removal and identical upload write no row and no audit;
  conflict carries the current state; two racing uploads give one 201 and one 409; the previous file is deleted after
  commit and a rolled-back upload leaves no file; the file is mode 0600 under `council-photos/`; the audit row has
  no image, name or hash (AC-353-1, -2, -5).
- `tests/test_council_photo_privacy.py` first (AC-353-3): an applicant session gets 403 for GET and HEAD of a current
  URL, an old URL and a made-up one, and for POST and DELETE; 403 on `/api/council/seats/`, `/api/dashboard/members/`
  and the attendance roster; and the applicant's own payloads (`/api/session/`, `/api/applications/`, `/api/cases/`, their case and message views,
  search) contain no `/api/council/photos/`. Staff get the image with the G3.5 headers and 304 on `If-None-Match`.
- Then `council_photos.py`, the two views and routes, `photo_urls()` in `seat_list`, `members_summary` and
  `_roster_row` (replace the `None`s), and `photo_rights()` in `seat_list` rows.

**T3. frontend: the Settings photo control.** Files: the `frontend` row. Depends: T2's contract (not its merge; build
against `contract/*.json`).
- `tests/frontend/council-photo-control.test.cjs` first: the G2 control props; hidden without `can_add_photo` or
  `can_remove_photo`; upload sends `expected_version` and sets `src` only from the answer; each G3.6 code maps to its
  G2 word; conflict keeps the file and "Use my photo" resends with the answer's `photo_version`; removal confirms first.
- Then the control in `ui-workspaces.js` per G2 "Where the control lives" (today: row menu item, then `Dialog`), the 19
  English keys, and screenshots EN/AR desktop (AC-353-4) from the browser check.

**T4. i18n: Arabic proposals** for the 19 keys in `docs/i18n/arabic-proposals.md` (D-0012). Depends: T3's keys.

### Acceptance trace

| AC | Proven by |
|---|---|
| AC-353-1 | T2 `test_council_photos.py` (three roles succeed; member and applicant 403), T1 RLS insert tests |
| AC-353-2 | T2 `test_council_photo_image.py` + size cases; T3 code-to-word mapping (EN/AR words from T4) |
| AC-353-3 | T2 `test_council_photo_privacy.py`, T1 applicant reads zero rows, `contract/get-photo-applicant.json` |
| AC-353-4 | Existing `council.js` render of `photo_url` + T2 payloads; T3 screenshots EN/AR; Presiding card keeps its icon until PLX-028 (G2) |
| AC-353-5 | T2 audit assertions (one row per change, none for no-ops, no image data) |

## G3.9 Risks and anything unclear

- **Pixel limit wording.** `photo_too_many_pixels` reuses `photoTooLarge`, whose `{max}` is a file size, which is
  wrong for this case. It is rare (over 24 MP under 2 MB). The technical writer (G7) may add a word such as
  `photoTooManyPixels` in T3; until then the code maps as in G3.6.
- **Unseated or deactivated accounts.** Settings > Users lists active staff only, so a deactivated account's photo can
  only be removed after reactivation. It still shows in attendance history (G2 "Former members"). Raise as a follow-up
  if a member wants deactivation to remove photos.
- **Scanner down** means no photo can be saved (503 `scan_unavailable`), by design (never store unscanned).
- **Migration number** 0080 assumes #372 merges 0079 first; the database engineer renumbers if main moves.
- **PLX-028** (photo in the Presiding fact) is open; when Plenix documents it, a small follow-up adds
  `presiding_member_photo_url` to the session projection from `photo_urls()`.
- PR #352 draws an Avatar inside the Presiding fact; the Design Critic asked for it to be removed (G2 round 2). Not part
  of this slice.
