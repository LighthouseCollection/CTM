# Applicant frontend integration contract

Coordinated on GitHub #1/#2; not an amendment to protected build-spec. Backend PR #7
at `07c35ed` supplies the application projection and expected-version write guards;
the proposed own-file listing remains pending there. Governance owns shared shell
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

## Own current files projection requested

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
Current originals outside current requirements remain visible separately.

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
