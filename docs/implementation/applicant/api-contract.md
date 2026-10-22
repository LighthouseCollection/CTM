# Applicant frontend integration contract

Coordinated on GitHub #1/#2; not an amendment to protected build-spec. Backend PR #7
at `6e690b5` supplies the application projection, own-file/payment history and
expected-version write guards. Governance owns shared shell
integration. Existing backend remains the authorization authority.

## Application projection

Existing GET `/api/applications/{id}/` fields are retained: `id`, `kind`, `status`,
`version`, `answers`, `fee`, case identity. The frontend additionally consumes:

- `questionnaire`: exact bound `id`, integer `version`, `published`, `definition`,
  approved `declaration_en`, `declaration_ar`.
- Explicit server booleans: `can_edit`, `can_checkout`, `can_submit`, `can_resubmit`.
  Missing capabilities never grant an action. Draft privacy, suspension, duplicate
  hold, proceeding state, checkout state, ownership and fee eligibility belong in
  server authorization, not inferred client role strings.
- `duplicate_hold` and latest own `return_instructions` where applicable. Instructions
  are source content shown as escaped text, not rewritten by the frontend.
- Existing fee states consumed: `due`, `paid`, `waived`, `historical_exempt`; unknown
  states show unavailable. USD 250 comes from the approved contract; amount display
  uses the actual server obligation. No client waiver request or inferred success.

After a successful answer save and successful document listing, the frontend reloads
the authoritative application projection before filing. It ignores responses from
older requests, different sessions or different answer versions. Missing/mismatched
refreshes block filing instead of retaining stale ready capabilities. Server-provided
status and case reference are displayed without inferring either from browser URLs.

Returned-correction privacy is enforced by backend `e2f714a`: council receives the
last formal answers/version and exact submitted file manifest until resubmission.
Saved pending answer/file corrections remain available to the owner while council
detail/history/current listing/audit and direct/range/preview/HEAD byte delivery
exclude them. Early correction alerts are not queued to the assigned manager.
Resubmission publishes the corrected formal snapshot while preserving prior
submitted originals. The default real API runner verifies these boundaries; search
integration, legacy queued-alert delivery and PostgreSQL policies remain separate.

Definition fields: `code`, `type`, `label_en`, `label_ar`, `required`, optional
`when:{field,equals}` matching the existing strict backend predicate. Supported
types: text, textarea, date, choice, boolean, list of choices. Choices may be
`{value,label_en,label_ar}` objects, or existing primitive strings with
`choice_labels[value] = {label_en,label_ar}` to retain backend validation compatibility.
Repeated records use `type:"list"` with `item_fields` instead of choices. Each child
has the same bilingual label/type vocabulary; one record level is supported. Child
conditions, nested repeat definitions and editable `id` fields fail closed. Existing
record IDs and unknown keys are retained. New rows receive UUID `id`; contextual
uploads bind that stable ID after the answers are saved. The UI can add/remove local
rows and save a new attributed revision; it does not delete retained original files
or previous answer revisions. Accepted form codes and wording still come from the
approved bound definition, never generated from the field dictionary. This extension
was proposed on #2; backend nested validation and the approved full form content remain
dependencies. No answer flattening or guessed replacement wording is introduced.

## Existing writes

| Endpoint | Frontend request | Required backend guarantee |
| --- | --- | --- |
| POST `/api/applications/` | `{kind:"petition"}` | Reuse active draft; canonical eligibility/claims; published approved questionnaire |
| POST `/api/applications/` | `{kind:"appeal",case_id}` | Own linked case; closed proceeding including reopened-sibling exception; reuse own pending appeal; bound appeal questionnaire; no reopening on start/submit |
| POST `/api/applications/{id}/` | `{answers,expected_version}` | Existing optimistic check, immutable answer revision and attribution |
| POST `/api/applications/{id}/checkout/` | `{attestation:{accepted:true,name},expected_version}` | Add expected-version enforcement under lock; freeze declaration/revision/manifest and reuse provider candidate |
| POST `/api/applications/{id}/submit/` | `{idempotency_key,expected_version,attestation}` | Add expected-version enforcement; genuine fee/waiver; exact attestation and manifest; idempotent finalization |
| Returned submit, same endpoint | `{idempotency_key,expected_version}` | Reuse original signature and fee; no re-sign/checkout |
| POST `/api/files/` | Multipart described below | Existing owner/context, format/size, original retention and real scan gates |

Checkout acknowledgement must include `intent` and HTTPS `checkout.stripe.com`
`checkout_url` for the current Stripe adapter. No `?payment=...` parameter is read
as proof. Submit acknowledgement `{id}` is described as server acknowledgement;
the application must be reloaded to obtain its authoritative current state.
Network uncertainty preserves the original signature/version/payload for retry.

## Own current files projection

Implemented by backend PR #7 at `6e89c22` and exercised through actual HTTP/browser
controls in `browser_applicant_api.py`. Listing uses latest technical scan event;
same-context replacement checks context and visibility server-side as well.

GET `/api/applications/{id}/files/`:

```json
{
  "can_upload": true,
  "items": [
    {
      "id": "file-version-uuid",
      "attachment_id": "attachment-uuid",
      "category": "RO",
      "context": "saved-order-uuid",
      "name": "Server display name.pdf",
      "scan_state": "pending"
    }
  ],
  "requirements": [
    {
      "category": "RO",
      "context": "saved-order-uuid",
      "label_en": "Approved contextual document label",
      "label_ar": "تسمية المستند المعتمدة",
      "required": true
    }
  ]
}
```

This JSON illustrates shape only; labels are not questionnaire approval. Categories
supported by current applicant upload backend: MC, CMC, CDD, PHOTO, SPOUSE_PHOTO,
PET, RO. Each reported order has its own nonempty saved context. Requirements must
reflect current saved answers, filing kind and statement alternative. No baptism
requirement. Optional documents remain optional. Return current originals only,
with unique attachment IDs; no prior versions or council/private sources.

Only technically clean items may supply `download_url: /api/files/{id}/`; the frontend
also checks exact item ID/path before rendering a link. Pending, rejected and unknown
states never count as safe required documents. Server still enforces every byte read.
Current originals outside current requirements remain visible separately. For RO slots,
the frontend may show saved court/case-number values under their bound bilingual
field labels. These captions require matching application ID and saved answer
version, unique saved order IDs and exact requirement context. They never change
transport identity or infer a context from list position; missing/untranslated or
ambiguous source context omits the caption.

Multipart fields: `application_id`, `category`, `context`, `visibility:"own"`, `file`;
same-context correction also carries `attachment_id`. The UI rejects ambiguous or
cross-context replacement and over-25MB applicant files before transport; the server
must still sniff signatures and enforce its own constraints. No delete action exists.
After uncertain upload the UI requires listing refresh before another upload. The
server should provide idempotent upload handling if reliable automatic retry is added.

## Shared API adapter

Use same-origin credentials, CSRF and no-store. Attach HTTP `status` on all failed
responses. JSON requests retain Content-Type application/json; FormData must omit it
so the browser supplies the real multipart boundary. No production mock endpoint or
fixture login is introduced by these modules. Browser fixtures are test-only scripts.

## Private appointment read projection

Existing write: POST `/api/appointments/{id}/response/` with
`{version,response:"confirm"|"reject",explanation:""}`. The applicant module sends
the exact displayed invitation version; explanation is optional for rejection and
empty for confirmation. An acknowledgement locks local actions until refresh.
Stale, unauthorized or uncertain responses also require authoritative refresh;
there is no automatic retry because the existing response write is not idempotent.

GET `/api/appointments/` at backend `7684169` returns only this account's private invitations:

```json
{"items":[{"id":"appointment-uuid","case_id":"case-uuid","date":"2026-12-01",
"starts_at":"2026-12-01T10:00:00-08:00","ends_at":"2026-12-01T10:30:00-08:00",
"instructions":"Server invitation instructions","version":2,"state":"invited",
"response":null,"can_respond":true}]}
```

`response` is null, confirm or reject for the current invitation version only.
Rescheduling must create a fresh invitation version and invalidate previous response
eligibility. `can_respond` is authoritative and false for cancelled/completed or
otherwise ineligible invitations. The frontend additionally requires state invited.
Timestamps must include UTC offsets; the frontend displays both supplied times
without guessing an end/duration/timezone. No session/agenda/member/other-party
fields are requested. Missing/invalid projection fails closed and never falls back
to council agenda. No self-rescheduling is provided. The actual projection supplies
case identity without a display number; the UI uses a generic localized invitation
heading instead of showing the raw UUID. A supplied display number remains supported.
Real API/browser acceptance now covers own listing, confirmation, staff rescheduling
to a fresh version, stale422, rejection reason, cancellation and outsider denial.
Session lifecycle and private invitation PostgreSQL policies remain separate from
the isolated SQLite browser acceptance.

## Own payment history

GET `/api/applications/{id}/payments/` is available at backend `6e690b5`:
`{fee:{amount_minor,currency,status},verified_payment:boolean,events:[],checkouts:[]}`.
Events carry `id,kind,amount_minor,currency,amount_basis,timestamp`; checkout rows
carry `id,state,version,timestamp`. No provider reference/secret is requested.
The view only reads these server facts, never enables a filing action or performs
reconciliation. Waiver/historical exemption are not verified provider payment.
Processing, pending, paid-but-not-finalized and needs_review remain distinct from
application submission. Unknown statuses show unavailable, not success. Refunded
event amounts have `amount_basis:"cumulative_refunded"` and are labelled as a
cumulative total, never added together as separate refunds. Other events use
`amount_basis:"event"`. Invalid/unauthorized refresh clears previously shown facts.
Refresh is explicit and also follows answer-version/application-status/fee changes.
The pending-candidate attestation/resume contract remains a separate dependency;
this read projection does not supply a checkout URL or original attestation.

## Appeal entry and supplement dependencies

The appeal starter consumes the actual application acknowledgement, requiring
matching `case_id`, `kind:"appeal"` and a valid application UUID before navigation.
The shared shell proposal preserves both closed-case and reopened-sibling contexts
through the authorized proceeding list; eligibility remains server-owned. A stale
start acknowledgement cannot navigate after the case view has been left.

The existing bound editor handles new-information draft answers, required originals,
declaration/fee and submission. Submitted appeal answers are immutable. Supplements
will use existing POST `/api/appeals/{id}/additions/` with `{text,file_ids}` only after
own authoritative `can_supplement` and supplement history are projected. Own history
must include attributed text, exact safe evidence versions and timestamps without
other spouse/council content. An uncertain append needs authoritative refresh because
the existing endpoint does not supply idempotent retry semantics.

The prepared supplement UI proposes this extension to the own application read:

```json
{"id":"<application UUID>","kind":"appeal","status":"submitted","can_supplement":true,"supplements":[{"id":"<supplement UUID>","text":"Additional information","actor":"Applicant","timestamp":"2026-10-21T12:00:00Z","manifest":[{"id":"<file UUID>","name":"Evidence.pdf","scan_state":"clean","download_url":"/api/files/<file UUID>/"}]}]}
```

This is a proposed contract, not an existing backend response. Missing or malformed
capability/history clears displayed history and disables append. Only clean own
current files with exact authorized download paths can be selected. Review precedes
POST; any uncertain response freezes that local attempt. Authoritative refresh and
explicit clearing are required before starting another entry. The current real-API
test verifies missing-contract controls stay disabled; append success is fixture-only.

## Own released decree read

The case panel reads GET `/api/cases/{id}/` and requires an explicit
`released_decrees` array. Backend 444bad8 supplies this extension and private no-store case reads. Absence
remains unavailable, never an empty list or a grant inferred from case closure.
Row fields: UUID `id`, nonempty `reference`, `language` (`en`, `ar`,
`bilingual`), offset-aware `released_at`, and `signed_file` with UUID `id`, `name`,
`scan_state:"clean"` and exact `/api/files/{id}/` `download_url`. An empty array
means the server confirms no currently released certificates for this account.

The backend must filter to the authenticated recipient's latest active release,
exclude revoked/unreleased certificates and other recipients' release history,
and authorize the exact stored signed PDF on every full, range, HEAD and preview
request. Issuance, entitlement, notice receipt and appeal state alone grant no PDF
access. Retained links must fail after revocation. Existing authorized_file checks
latest recipient release, but transport/cache/revocation acceptance is not proven
by the new UI fixtures. No replacement, signing or release write is exposed here.
Refresh clears old links before fetching; failed/malformed reads clear them too.


## Actual own request workspace (480a246)

GET `/api/cases/{id}/requests/` supplies sent own intake/medical/psychological
requests, including previously sent closed rows. Staff drafts, interviews, external
requests and other subjects are excluded. The client validates nonnull sent timestamps,
bound question wording, UUID `proceeding_id`, opaque 64-hex `request_version`, and
boolean `can_respond`, `can_upload`, `can_sign_release`. This fingerprint is not an
integer response version. Own `response` receipts and exact `signed_releases` are
retained. Supplied EN/AR text is escaped and displayed without invented translations.

GET `/api/requests/{id}/files/` must match request/proceeding/fingerprint. Only latest
own originals are selectable; clean files may link only to their exact `/api/files/{id}/`
route. Pending/rejected files expose no byte link. Multipart POST `/api/files/` sends
`request_id`, `expected_request_version`, `category`, `file`; the server derives ownership
and context. Consent accepts PDF/PNG/JPEG; clinical report originals are distinct.

The exact published `release_definition` contains ID, version and both declarations.
The applicant selects an own safe CONSENT original, explicitly accepts the displayed
declaration, reviews, then POSTs `/api/requests/{id}/release/` with
`{expected_version:request_version,declaration_id,accepted:true,file_id,scope:{council:true}}`.
Retained scope must match council, kind purpose, request and proceeding. No report
upload implies consent. An uncertain attempt blocks writes until authoritative refresh;
only the matching declaration/signature/scope recovers consent success.

POST `/api/requests/{id}/complete/` sends
`{expected_version:request_version,answers:{question_code:string,files:[report_ids]}}`.
All bound questions require answers. Clinical responses require signed exact scope and
nonempty safe report originals; CONSENT cannot be report evidence. No applicant
observations are sent. Review precedes submission. The report UUID acknowledges the
response; exact replay returns the same receipt, including after closure, while a
changed replay is rejected. Local answers/evidence and navigation/unload guards survive
refresh or lost acknowledgement. Stale evidence requires explicit removal and review.
Uploads and consent/response attempts block competing writes and pending navigation.

## Prepared lifecycle actions

Prepared lifecycle controls require `can_delete_draft:true` on a draft or
`can_withdraw:true` on a submitted/returned/accepted petition or appeal. They send
`expected_version` to existing delete-draft/withdraw routes after distinct explicit
confirmation. No reason/approval/refund demand is introduced; no other-party notice
or guaranteed case closure is promised. The server owns participating-party and
joint-case rules. Missing capabilities show no controls. Acknowledged/uncertain
attempts stay locked until authoritative application refresh; all competing filing,
file/answer/supplement controls remain disabled, including delayed action responses.
The backend must project capabilities and enforce the requested version before
these controls can be enabled in real integration.

## Actual checkout guard and proposed resume snapshot

The filing panel reads own payment history before enabling draft filing controls.
Pending, processing, paid-but-unfinalized, needs_review, unknown or malformed history
blocks a new checkout/signature. Read failure also blocks it. This prevents a fresh
signature from pretending to replace the retained pending candidate's attestation.
Returned correction resubmission does not enter the draft checkout recovery gate.

Proposed own application extension: `can_resume_checkout:true`, and
`pending_checkout:{id,version,checkout_url,attestation:{accepted:true,name},
declaration_en,declaration_ar}`. Candidate UUID and answer version must match the
single pending row in own payment history and current application version. Unknown
history or any processing/paid/reconciliation state disables resume. Only the exact
HTTPS checkout.stripe.com host is accepted. Resume displays original declaration
and signer and navigates to the existing URL; it never POSTs, re-signs, creates a
candidate or interprets return query parameters as payment success. Backend must
supply the original immutable snapshot and currently authorized URL. Missing data
keeps the hold visible, with refresh/contact guidance.

## Current verification: ten batches (2026-10-21)

Backend `480a246118cce8c4ac338c32c71c79cde74816d2` supplies the own request
fingerprint, capabilities, scoped originals, published declaration and retained
consent/response receipts. Intake and assessment workspaces now use these actual
contracts. The previously reported closure disclosure is resolved and independently
verified: never-sent drafts remain private; previously sent closed requests remain
readable, and exact submitted responses recover their original receipts after closure.
The default closure gate remains enabled.

Final local checks: 66 frontend tests, 42 real API/browser scenario groups, five
assessment interruption groups, nine next-batch groups, nine shell groups and four
request-reader groups pass. The real API runner uses isolated SQLite, synthetic
accounts/content, temporary backend archives and a scanner test policy. It does not
establish PostgreSQL, live provider/payment/antivirus, institutional wording approval,
signature issuance or operational delivery acceptance. See the consolidated ten-batch report and JSON evidence.

Released-decree reads and exact-byte withdrawal remain verified with synthetic
stored DEC bytes. Real signing/issuance and PostgreSQL acceptance remain separate.
