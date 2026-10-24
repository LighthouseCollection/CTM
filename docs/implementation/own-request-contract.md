# Own requested reports and disclosure consent

Backend draft PR #7 / issue #2. This contract supplies no institutional wording,
live-collection approval or release-revocation workflow. Governance approval of
wording and unsupported release changes remains required.

## Read and bind

`GET /api/cases/{case_id}/requests/` exposes only the authenticated applicant's
sent requests, excluding interviews/external requests. A non-null `sent_at` is
required even after closure: unsent drafts remain private; sent closed requests
remain readable. Responses are private/no-store. Additional own fields:

- `proceeding_id`, `request_version`: opaque server fingerprint binding exact
  request, proceeding, subject and frozen sent content. Reload on stale identity.
- `can_respond`, `can_upload`, `can_sign_release`: current capabilities, rechecked
  under locks on writes. Never enable writes merely from `state:'sent'`.
- `release_definition`: null or `{id,version,definition,declaration_en,declaration_ar}`
  from the latest published `medical_release` definition. Both language texts are
  required. Render this exact approved version; never invent missing text.
- `release_status`: `none|out_of_scope|signed`; `signed_releases`: own retained
  `{id,declaration_id,signature_file_id,scope,signed_at}` rows. New scope binds
  `{council:true,purpose:medical|psychological,request_id,proceeding_id}` server-side.
  Existing out-of-scope consent cannot be broadened through this endpoint.
- `response`: null or own `{id,submitted_at,version:1}` receipt. Staff observations,
  internal/external responses and other subjects' consent are excluded.

## Safe files

`GET /api/requests/{request_id}/files/` is applicant-subject-only. It returns
`{request_id,proceeding_id,request_version,can_upload,items}`. Each latest own original
has `{id,attachment_id,category,purpose,name,version,scan_state}`. Category `CONSENT`
means purpose `consent`; other categories mean `report`. Only a currently clean,
authorized file gets `download_url`. Pending/rejected scans never grant links.
No historical versions, raw storage keys or other subjects' files are included.

Use multipart `POST /api/files/` with `request_id`, `expected_request_version`,
`category`, `file`, and existing `attachment_id` for same-context replacements.
Server derives owner/case/proceeding/visibility. Applicant interview/external
uploads fail. Signed `CONSENT` originals cannot be replaced. Completed, closed
and cancelled requests reject uploads. Safe own listing remains readable afterward.

## Sign and submit

`POST /api/requests/{request_id}/release/` JSON:

```json
{"expected_version":"request_version","declaration_id":"displayed release_definition.id","accepted":true,"file_id":"CONSENT file UUID","scope":{"council":true}}
```

Requires active applicant subject, open assessment request, exact latest published
bilingual declaration, literal boolean acceptance and exact council recipient scope.
Strings/numbers, extra recipients, unsafe/old files and ordinary report evidence
are rejected. Signature originals must be PDF/PNG/JPEG. The server binds purpose,
request and proceeding. A matching retry while pending returns the same release;
different consent is rejected. Re-read retained own rows after interruption.
Uploading a file never implies consent.

`POST /api/requests/{request_id}/complete/` JSON:

```json
{"expected_version":"request_version","answers":{"question_code":"answer"}}
```

Requires nonempty answer object covering each frozen question. Assessments also
require existing exact-subject council consent and nonempty `answers.files`.
All response file references must be distinct, latest, clean and bound to the
same request/case/proceeding/subject with report purpose. `CONSENT` cannot serve
as assessment evidence. Applicant observations are forbidden.

Success remains `{id:report_id}`, status201. Exact retries with the original
answers return that receipt, even after later closure, without another response,
revision or notification. Changed retries fail. Reload own receipt/reports after
interruption. The fingerprint survives completion for recovery. Existing council
completion remains compatible; an explicitly supplied fingerprint is checked.

## Database enforcement and limits

Migration0023 adds forced RLS for request/report roots, frozen sent-content and
report-provenance guards, and restrictive insert policies for consent, own response
revisions and request originals. External read/save/submit uses exact token context
before lookup; invalid/expired/replaced tokens grant no rows. Closure and own writes
serialize on proceeding then request. Published institutional content stays immutable.

This is still a partial63-model adapter for the approved151-table contract.49 domain
tables have forced RLS;14 remain for review. Independent browser acceptance,
institutional/provider approval and wider schema reconciliation remain separate.
No operational migrations, configuration, credentials, merge or deployment occurred.
