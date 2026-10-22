# Twenty report authoring and configuration batches

Issue #2 / draft PR #7. Implements council D19's report revision race follow-up.
This increment adds no domain models, routes or additional RLS tables. The current
inventory remains63 domain models,88 routes and56 forced-RLS tables. Seven core
table policy reviews and semantic schema reconciliation remain outstanding.

## Delivered batches

1. Report revision HTTP and service calls require a positive integer
   `expected_version`; missing/string/boolean/zero input cannot append a revision.
2. A stale report write returns HTTP409 with `error:version_conflict` and
   `current_version`, without exposing the other author's narrative.
3. Narrative saves lock the stable proceeding before checking closure/latest
   revision, serializing competing saves and proceeding closure.
4. An exact retry of the immediate successor returns its retained receipt without
   another revision/audit. Recovery still requires current author/write authority
   and disclosure; closure does not erase the receipt or permit a new narrative.
5. Revised answers must be a nonempty bounded strict-JSON object; observations are
   bounded text. Nonfinite, deeply nested, invalid Unicode and null-character
   payloads fail before publication. JSON booleans/numbers differ on replay.
6. A revision must answer every question in the frozen sent request, preserving
   its snapshot rather than validating against a later question-bank version.
7. Evidence identifiers are bounded/distinct UUIDs and must reference current,
   clean files with the exact request/case/proceeding/subject/category/visibility.
   Consent sources, unrelated files and unsafe/superseded versions are refused.
8. Medical narrative writes and receipt recovery require the exact subject/request
   release with literal JSON boolean council scope. Read history uses this same
   disclosure gate; administrator authority alone cannot grant disclosure.
9. History adds authoritative `current_version` and `can_revise`, derived from the
   retained rows/current author/assignment/open state. POST returns saved version.
10. Template creation validates nonblank bounded titles and literal boolean
    `shared`, retaining existing owner/admin publication boundaries.
11. Template question selection requires a bounded list of distinct published
    string codes; malformed input cannot create a partial template/version.
12. Questionnaire publication requires bounded, nonblank English and Arabic
    declaration strings, preserving actual configured wording without fabrication.
13. Configured fields require a bounded list of objects, unique nonblank codes and
    supported runtime types; invalid publication leaves drafts bound as before.
14. Required flags must be booleans and choice fields need nonempty distinct string
    options compatible with the answer validator.
15. Conditions reference existing configured fields, use supported equality values
    and cannot contain self/dependency cycles or unsupported condition operators.
16. Required document categories must be a distinct list of supported filing codes,
    preventing unusable requirements from being published into active drafts.
17. Settings enforce strict JSON, finite values, string object keys, bounded depth
    and100KB serialized UTF8 size, including direct service callers.
18. Nested settings reject recognized credential-key spelling variants after case
    and separator normalization, including Authorization/access/refresh tokens.
19. Settings support optional nonnegative `expected_version` under their existing
    advisory lock; concurrent stale saves fail409 and retain attributed history.
20. PostgreSQL notification guards retain source/recipient/key/kind/payload/time
    and the first read timestamp; runtime acknowledgement is recipient-only and
    historical notifications cannot be deleted through ordinary row mutations.

## Council report contract

`GET /api/reports/{id}/revisions/` retains `items` and adds
`current_version:number` and `can_revise:boolean`. Keep the version from the row
the author actually edited. Re-reading immediately before saving is insufficient
to prevent concurrent overwrites; do not replace the edited version with that
fresh version while retaining stale local answers.

`POST /api/reports/{id}/revisions/` now requires:

```json
{"expected_version":1,"answers":{"QUESTION-CODE":"Response"},"observations":""}
```

Success returns201 `{id,version}`. A stale changed write returns409:

```json
{"error":"version_conflict","current_version":2}
```

Retain local edits, load current history and reconcile explicitly before a new
save. An exact retry uses the original version/body and returns the original
success receipt only while that revision is the immediate saved successor.
It does not replay through intervening newer edits or restore revoked authority.
Applicant/external source narratives remain read-only to council; the original
authorized council author restriction and private medical scope remain enforced.

## Configuration and notification boundaries

`POST /api/system/settings/` accepts optional `expected_version` (0 for no prior
revision) and returns `{id,version}`. GET retains the latest version per setting.
Callers omitting the field retain the legacy serialized append behavior; those
callers cannot claim stale-edit protection. Setting conflicts use the same409
envelope. Values are not automatically provider configuration or credentials.
Secret-key recognition is a targeted safeguard, not content-based secret detection.

Questionnaire/template routes keep their existing shapes and now reject invalid
definitions before writes/rebinding/notifications. Conditions must reference the
published definition's own configured fields; filing categories use the current
supported backend vocabulary. Empty personal template selections remain permitted.
Existing frozen checkout handling, accepted question seed and protected build-spec
sources are unchanged. Publication does not approve institutional wording itself.

Migration0032 adds notification mutation guards without broadening row access.
Exact report receipt recovery uses readable retained roots under a proceeding lock;
it does not request UPDATE authority on closed report/request rows. Independent
non-owner PostgreSQL checks cover this recovery and notification mutation attempts.
No UI/browser acceptance, live provider success, operational migration, deployment
or merge is claimed. Validation evidence is recorded in vm-frm-progress.md.
