# Twenty council revision and historical recovery batches

Issue #2 / draft PR #7. Continues substantive edit/retry integrity after the D19
report work. Adds no domain models or newly protected RLS tables. Seven core-table
policy reviews and broader semantic schema/identity reconciliation remain open.

## Delivered batches

1. Notes require nonblank bounded text, including strict Unicode/null-character
   checks, before creating a root or revision.
2. Note edits accept optional `expected_version` and compare under the stable
   proceeding lock; changed stale saves return409/current_version.
3. An exact immediate-successor edit retry for a known `note_id` returns the saved
   root/version without another revision or audit, retaining original authorship.
4. PostgreSQL uniqueness enforces one revision number per note.
5. Only the newest note revision advertises `current:true` and `can_edit`; old
   revisions remain readable. Original-author/current-write/open-state gates remain.
6. Findings validate bounded fact codes and strict, bounded JSON values.
7. Finding sources accept distinct scoped note/report/file citations, validate the
   original proceeding and reapply file authorization or medical disclosure.
8. Findings accept optional compare-and-save versions per proceeding/fact code.
9. Exact immediate-successor finding retries reuse the retained revision; changed
   stale content conflicts and another recorder cannot claim the receipt.
10. PostgreSQL uniqueness enforces one finding revision per proceeding/code/number.
11. Decision type, grounds, conditions and entitlement values are validated before
    persistence; malformed/unbounded content cannot create partial versions.
12. Decision writes accept optional edited-version checks under their existing
    case/proceeding locks.
13. Exact immediate-successor decision retries retain one version and audit; new
    decision versions still do not inherit votes or presidential approval.
14. Decision history adds `current_version` and current-write `can_record`.
15. Vote writes accept optional bounded string `idempotency_key`.
16. Vote key replay binds the exact decision/member/choice/actual recorder. Changed
    choice or another recorder's reuse fails; a new key can record a later vote.
17. Database key uniqueness and existing decision locks serialize concurrent vote
    retries to one retained vote/audit. Legacy unkeyed voting remains append-only.
18. Historical staging accepts bounded strict JSON and adds original-admin-only
    read/recovery of workspace payload, version and finalized case ID.
19. Existing historical drafts accept optional edited-version checks and exact
    immediate-successor retry; publication can bind the version actually reviewed.
    JSON numeric scale/exponent normalization does not fabricate a new edit;
    booleans remain distinct from numbers.
20. PostgreSQL workspace guards retain actor/identity/creation/publication facts
    and monotonic payload versions; finalized content cannot be reset or rebound.

## Optional edit-version contract

Existing note, finding and decision POST routes add optional nonnegative
`expected_version`. Use0 where no revision exists, and the version actually edited
for a revision. Values must be integers, excluding booleans. Stale changed saves
return409 `{error:"version_conflict",current_version:number}`. Exact retries of
the immediate successor return the prior receipt after current authority, input
validation and open-state checks. Recovery does not bypass closure or revocation.
Do not put a freshly fetched version onto unreconciled stale local content.

Callers omitting the field retain serialized legacy append behavior and cannot
claim stale-edit protection. The earlier report revision route still REQUIRES
`expected_version`; this increment does not relax that requirement.

Note POST adds saved `version` to its existing root `id` response. Note GET keeps
all prior rows and adds `current`; only the latest row can advertise `can_edit`.
First creation without a known `note_id` has no replay identity; callers must not
claim retry-safe new-note creation. Finding and decision receipts keep their
existing revision IDs; their GET histories provide revision numbers. Decision GET
adds `current_version` and `can_record` alongside existing `items`.

## Source and vote contracts

Finding `sources` defaults to[] and is a list of up to100 distinct singleton
objects: `{note_id:uuid}`, `{report_id:uuid}` or `{file_id:uuid}`. Notes/reports must
belong to the same proceeding. Reports require actual scoped disclosure; files
must be authorized safe sources in the same case/proceeding. Unknown citation
shapes and cross-proceeding sources fail before persistence. These are retained
root/version-file references, not a claim of complete field-level equivalence to
the approved finding-source schema. The cited note/report root retains its own
revision history; a citation does not freeze a new text snapshot.

`POST /api/decisions/{id}/vote/` adds optional `idempotency_key` (nonblank string,
up to100 characters). Preserve the key/body for retries and use a new key for a
new action. Exact repeated/concurrent sends retain one vote and actual recorder.
Another recorder's key cannot be replayed as their own work. Old/superseded or
closed decisions remain unwritable, including keyed retries. No new voting or
presidential authority is granted, and no approval/decree success is fabricated.

## Historical workspace contract

`POST /api/historical/` keeps `{payload,workspace_id?}` and adds optional
`expected_version` only when editing an existing workspace. Success returns
`{id,version}`. New workspaces start at1; changed payload saves increment once.
Identical saves do not advance versions. An exact retry of the immediate
successor edit returns its retained version; changed stale payloads conflict.

`GET /api/historical/{id}/` returns `{id,version,payload,finalized_case_id}` only to
the original active administrator, with private/no-store response headers.
Other administrators receive404; secretary/applicant access is denied.

`POST /api/historical/{id}/publish/` adds optional `expected_version` to bind the
reviewed draft. Stale publication creates no case. Successful publication remains
idempotent, returns the existing case receipt and freezes the workspace. Existing
legacy workspaces receive version1 without invented earlier edit history. Full
historical field/lifecycle reconciliation remains outstanding.

Migrations0033/0034 add fields, uniqueness and provenance guards. No operational
migrations, credential changes, deployment or merge occurred. No frontend/browser
or live provider acceptance is claimed. Full validation is recorded in
vm-frm-progress.md; domain models remain63, routes89, forced-RLS tables56.
