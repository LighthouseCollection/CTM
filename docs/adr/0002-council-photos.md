# 0002 Council photos: an append-only photo table, private files, versioned staff-only URLs
2026-11-14 · Status: proposed

Context:
- #353 G1 (option A, applied per D-0003): admin, secretary or president upload, replace or remove a photo for a seated
  council account in Settings > Users & Roles. JPEG or PNG, up to 2 MB, checked by content. Private storage. Served
  only to signed-in staff. Applicants never get a council photo or its URL, including through search, counts,
  downloads or the API (`build-spec/permissions.md`, CLAUDE.md permission rule). Every change is audited without the image.
- G2 (`docs/implementation/slices/core-353-council-photos/design.md`) asks for: the new `photo_url` in the upload and
  removal answers, distinct refusal codes, a conflict answer with the current photo, its version and who changed it,
  and fresh URLs if URLs expire.
- CTM files today are `Attachment` + `FileVersion`, tied to an application, case or report request, and served by
  `/api/files/<id>/` through `authorized_file`, which applies case rules and writes an audit row per view.
- Council seats (#175, D-0043) set the pattern for per-account council facts: an append-only change table (latest row
  counts), row security for staff read and editor insert, the database clock as the change time.

Decision:
- **Table.** A new append-only table `CouncilPhotoChange` (one row per add, change or removal; the latest row per account
  counts). `version` counts the account's changes (1, 2, 3...); unique `(account, version)`. A row is either a photo
  (`object_key`, `mime_type`, `byte_count`, `sha256`, `width`, `height`) or a removal (all null). Row security as for
  seats: staff read; admin, secretary or president insert as themselves for a staff account; no update or delete;
  the database sets `created_at`. Migration `0080_council_photos` (database engineer).
- **Files.** Bytes live under `MEDIA_ROOT/council-photos/<uuid>.<jpg|png>` through `write_private_original` (0600 file,
  0700 folder, no `MEDIA_URL`, written on commit), so the pre-deploy media snapshot covers them. Not an `Attachment`:
  a council photo belongs to an account, not a case, and must never reach a case file list, search or download.
- **Content check.** Size first (2,097,152 bytes, read at most one byte more). Then a pure-Python structure check of
  JPEG or PNG (no new dependency), dimension limits, and metadata removal (EXIF, GPS, XMP, IPTC, comments, text chunks)
  keeping only a JPEG's orientation. Then the existing ClamAV scan; only a clean result is stored.
- **URLs.** `photo_url` = `/api/council/photos/<account_id>/<version>/`. The URL changes with every change, so a browser
  never shows a replaced photo, and an old URL stops loading (404, the G2 "Photo fails to load" fallback). URLs do not
  expire. The image is served with `Cache-Control: private, no-cache` and the hash as `ETag`: the browser keeps it but
  revalidates each time, and every request (including a 304) checks the caller is active staff.
- **API.** `POST /api/council/photos/<account_id>/` (multipart `photo`, `expected_version`) and
  `DELETE /api/council/photos/<account_id>/?expected_version=N`, both answering the saved state (`photo_url`,
  `photo_version`, `changed_by`, `changed_at`); a stale `expected_version` is 409 `photo_conflict` with the current state.
  Existing staff payloads gain `photo_url` (Home member tiles, attendance rosters) and the seats list gains
  `photo_url`, `photo_version`, `can_add_photo`, `can_remove_photo`.
- **Audit.** Each change writes `council_photo_changed` with `{account_id, version, action, mime_type, byte_count}`;
  no image, no file name, no hash. Viewing a photo is not audited (see Consequences).

Consequences:
- Easier: one rule for every surface (any active staff may see any stored council photo); a photo cannot leak through
  case files, search or downloads because it is in none of those tables; cache-safe without signed URLs.
- Harder: each tile revalidates its image (a 304 per photo per page load). Acceptable at council size (tens of accounts).
- Views are not audited: a photo is a decorative staff-directory image shown on every Home load, not case evidence;
  auditing each view would flood the audit log. The security reviewer (G5e) confirms or overturns this.
- Superseded and removed files are deleted from disk after commit; the rows keep the history (who, when, version, size)
  so the audit trail survives while the image does not.
- Migration and rollback: `0080` adds one table, its functions, policies and triggers, and reverses cleanly. Roll back the
  frontend and API first, then the migration. Files left in `council-photos/` after a rollback are removed by hand
  (listed in the build PR).

Alternatives considered:
- `Attachment` + `FileVersion` with a new category: those rows are case-bound, `authorized_file` applies case rules, and
  every view writes an audit row; a council photo would also become reachable through `/api/files/`. Rejected.
- A nullable `photo` column on `Account`: no version for conflicts, no history, and `Account` updates go through other
  row-security rules. Rejected.
- Signed, expiring URLs: needs a signing key and refresh on long-open pages; a permission check per request already
  gives the same protection inside a signed-in session. Rejected.
- Re-encoding with Pillow: strips metadata thoroughly but adds a dependency that decodes untrusted images in the web
  process. The structure walk removes the same metadata without decoding pixels. Rejected for now; revisit if more
  image formats are allowed.
- The Microsoft profile photo (option B): needs a new Graph permission and connection; a member's choice (#353, P2).

Decision log: none new. Option A is the PM's applied decision card on #353 (D-0003); the rest is technical.
