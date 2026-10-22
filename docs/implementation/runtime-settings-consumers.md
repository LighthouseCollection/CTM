# Runtime settings consumers: tribunal contact and recommended doctors

Status: approved B-S1 design for issue #24. This work starts from backend commit
`1fea78fa9585c5e454b604674a6932ff4b376c4b` on the separate
`work/desktop-r-settings-consumers` branch. Applicant PR #5 remains unchanged.

## Selected design

Two dedicated read-only endpoints expose bounded runtime projections:

- `GET /api/runtime/tribunal-contact/` is available to any active authenticated
  account. It returns `{"contact": {...}, "version": number}`. The contact object
  contains only configured `display`, `email`, `phone` and `address` fields.
- `GET /api/cases/{case_id}/recommended-doctors/?specialty=medical|psychological`
  is council-only. It first requires staff authority, then existing case visibility.
  It returns `{"items": [...], "version": number}` with active matching records
  containing only `id`, `name`, `specialty` and `contact`. A `both` record matches
  either requested specialty.

The current model has no approved persisted association between a recommendation
and an applicant's own report request. Applicants therefore receive no doctor
directory in this slice. A future applicant projection requires an approved,
durable request association; it must not infer one from specialty or case membership.

## Data access and validation

The service reads through two fixed-key PostgreSQL functions:
`ctm_runtime_tribunal_contact()` and
`ctm_case_recommended_doctors(uuid,text)`. Migration
`0051_runtime_settings_consumers` depends on `0050_member_administration`.
The functions are `STABLE SECURITY DEFINER`, use a fixed search path, revoke
`PUBLIC`, grant only `ctm_app`, and deny worker callers. They do not grant general
`SettingRevision` access.

SQL validates the entire latest value before returning any projected row. It
checks the container and field types, allowlisted keys, lengths, UUID validity,
duplicate doctor identifiers, specialty values, strict booleans and total size.
Python then applies the existing `setting_schemas.py` validator as defense in depth.
The service never returns revision history, editor identity or unrelated settings.

When no configuration exists, the endpoint returns an empty projection with version
`0`. When the latest revision is malformed, it returns an empty projection with that
latest revision number. It never partially activates malformed data or silently
falls back to an older valid revision. An explicitly empty doctor list is valid and
returns no recommendations with its current version.

## Authorization and invariants

The contact endpoint calls the existing `active()` policy. The doctor endpoint calls
`staff()` before `case_for()` so a linked applicant cannot use the case endpoint.
The SQL doctor function independently requires a current non-applicant actor and a
case visible under the current runtime context. Read access does not grant settings
editing, case writes, medical consent, request/file disclosure, release authority,
appointment authority or doctor approval.

Only `GET` is accepted. Invalid or duplicate specialty query values are rejected.
Responses use private, no-store caching. No institutional data is seeded, and a
configured doctor is not described as approved, verified or tested.

## Alternatives considered

Embedding contact or doctor values in existing dashboard/request payloads would
couple unrelated responses to settings state and make permission boundaries harder
to review. A general runtime-settings endpoint would expose more keys than either
consumer needs. Dedicated endpoints and fixed-key database functions provide the
smallest reviewable surface and preserve deny-by-default row security.

## Verification

Focused tests cover active applicant and council contact reads; inactive and
anonymous denial; council-only doctor reads; case visibility; medical,
psychological and `both` filtering; inactive rows; missing, empty and malformed
latest values; latest-version refresh; invalid query parameters; response field
allowlists; no writes; no unrelated setting disclosure; direct worker denial; and
physical restricted `ctm_app` execution with forced RLS. SQLite checks remain useful
for the HTTP contract but do not establish acceptance.

Governance owns integration, operational migration application and exact-candidate
acceptance. This branch will open a separate draft PR and will not merge or deploy.
