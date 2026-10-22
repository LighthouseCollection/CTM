Current continuation: email_templates now supplies frozen account_suspended and
account_reactivated messages only; other kinds retain existing generic delivery.
Descriptors expose runtime_consumers (email_templates: account_status_email; other
families: empty). Subjects reject CR/LF. activation_supported remains false because
there is no separate activation operation. See account-administration-contract.md.
The647-test/0039 evidence below describes the earlier storage-only checkpoint.

# Typed settings editing contract

**Final isolated PostgreSQL: 647 passed, 1 skipped.** No model drift; migration
rollback/reapply remains through0039. Protected architecture unchanged.

Backend issue #2 response to UI's per-family settings schema dependency. This is
versioned nonsecret configuration storage, not a provider, translation engine,
email-template delivery or approved content publication pipeline. No UI/shell,
credential, operational migration, merge or deployment action is included.

## Read and write

GET /api/system/settings/ retains `items` (latest revision per key). Each item keeps
id/key/version/value and adds schema_version=1 and validation_state. Root `schemas`
is keyed by the six supported setting names; each descriptor provides the complete
value_schema, schema_version=1, current_version (0 when absent),
expected_version_required=true and activation_supported=false. Field codes are API
identifiers, not approved EN/AR labels. No sample/default content is seeded.

The exposed schema uses JSON Schema object/array/string/boolean/integer shapes,
required fields, enums, numeric/text bounds, nonblank text patterns, routing
if/then conditions and additionalProperties=false. Descriptors also expose the
shared max_json_bytes=100000 and max_json_depth=20. The
uniqueBy array extension is enforced by the server (normalized UUID identity where
applicable); clients must not assume a generic schema renderer enforces it.

POST /api/system/settings/ accepts only key, value, expected_version and optional
schema_version (defaults1). expected_version is mandatory, integer and nonnegative;
0 creates the first revision. A stale saved version returns409/version_conflict
with current_version. Invalid fields/types, unsupported schema versions, duplicates,
credentials and missing expected_version return422. A valid save returns201 with
id/version/schema_version. Exact retry with an old expected_version still returns409;
GET the latest version to reconcile a lost response. No stale overwrite is accepted.

Admin/secretary authority is unchanged. Applicants/member/president cannot read
schemas or values or write settings. Actual server actor and time, immutable
SettingRevision history, advisory serialization and audits remain in place. Direct
legacy service callers may omit expected_version as before; only callers supplying
it and the mandatory HTTP contract have conflict detection.

## Family values (schema_version1)

| Key | Value fields / bounds |
| --- | --- |
| translation_prompt | Object with required nonblank text, up to100000 characters and the shared JSON byte bound. Text is retained verbatim, never trimmed or executed. |
| translation_routing | Required mode ai/local. Optional primary/fallback slots each require provider/model text, enabled boolean, timeout_seconds integer1–300 and max_retries integer0–5. ai requires an explicitly enabled primary; local rejects enabled external slots. No endpoint, credential, header or secret locator is accepted. |
| tribunal_contact | Nonempty object with supported display, email, phone, address text fields; email syntax checked. No arbitrary profile/role/provider data. |
| email_templates | Required templates array; each record requires distinct supported notification code plus nonblank subject_en/subject_ar/body_en/body_ar. This stores versions; only account status notices now consume these templates; other worker messages remain generic. |
| document_categories | Required categories array; distinct supported code plus nonblank label_en/label_ar. No requiredness, permissions, byte limits or arbitrary new categories. Filing rules and the MC church/CMC civil meanings cannot be relaxed through this setting. Stored labels do not yet replace the authoritative filing labels. |
| recommended_doctors | Required doctors array; each record requires stable UUID id, name, specialty (medical/psychological/both), contact and active boolean. UUID duplicates are rejected even when spelled differently. No patient data, doctor portal or clinical automation is added. |

Full field bounds and permitted notification/document codes are returned in each
value_schema. All values also pass existing bounded valid-JSON/depth/100000-byte
and recursive secret-key rejection. No provider/model, local engine, institution,
doctor, prompt, translation register or bilingual content is chosen by the server.
Provider identifiers remain inert configuration data until a separate protected
adapter/credential and authorized runtime integration exists; enabled is requested
slot configuration, not evidence of a working integration.

## Legacy data and compatibility

No revision is rewritten or automatically coerced. Latest safe values matching the
current schema are valid. Safe incompatible shapes retain their original value and
are flagged legacy_requires_review; replace only through an explicit typed save
with the current expected_version. Unsafe/oversized legacy values are returned as
null with unsafe_legacy_value; unsupported legacy keys are redacted with
unsupported_legacy_key. Redacted values never appear in error messages. Historical
records remain untouched for separately authorized remediation; this stream does
not rotate secrets or inspect operational values.

schema_version describes the wire validator applied to the response/write. There
is no newly asserted stored schema-version column on historical records. The
current adapter remains SettingRevision; normalized system_setting_versions and
translation_prompt_versions/job provenance still require the approved-schema work.
No new model, route, grant or migration is introduced.

## Verification and remaining acceptance

Tests exercise every family through the existing HTTP endpoint under actual app SQL
session identity, compare/save conflicts, invalid field/type/version rejection,
duplicate identities, routing bounds, credential/endpoint rejection, legacy
preservation/redaction, and unauthorized schema/value access. Existing concurrent
setting-author tests, immutable-history and raw non-owner provenance checks remain.

Awaiting UI binding to these schema/version fields, governance serial integration,
approved bilingual labels/content and exact successor-SHA acceptance. Provider
activation, real translations, use of stored email/document/doctor configuration in
consumer workflows, prompt job provenance/history UI and full normalized schema
acceptance are distinct unfinished work; typed storage does not establish them.
