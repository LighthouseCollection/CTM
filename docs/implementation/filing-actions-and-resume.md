# Own filing actions, checkout recovery and council follow-ups

Issue #2, backend draft PR #7. These contracts extend the existing63-model adapter;
the approved151-table specification remains unchanged.

## Applicant actions

Own application detail now supplies `can_delete_draft` and `can_withdraw` alongside
the current answer `version`. Use those capabilities rather than deriving authority
from status. They reflect the existing lifecycle; withdrawal still preserves
participation, fee/history and owner-only pending-appeal rules. No secretary-wide
withdrawal or unilateral two-filer closure permission is introduced.

`POST /api/applications/{id}/delete-draft/` and own
`POST /api/applications/{id}/withdraw/` require JSON `{expected_version:version}`.
The server locks the application and checks the current version before mutation.
Absent/malformed/stale versions fail with422. Draft deletion is unavailable once
any checkout exists or the filing has been submitted. Pending payment candidates
must be reconciled before cleanup. Current admin withdrawal entry remains compatible;
an explicitly supplied version is checked. Another applicant receives no withdrawal
notification or access to the filing.

## Resume the original checkout

Own detail always returns `can_resume_checkout:false,pending_checkout:null`, or:

```json
{"can_resume_checkout":true,"pending_checkout":{"id":"checkout UUID","version":1,"checkout_url":"https://checkout.stripe.com/...","expires_at":"offset ISO timestamp","attestation":{"accepted":true,"name":"original signed name"},"declaration_en":"original declaration","declaration_ar":"original declaration"}}
```

This is a GET projection of the same checkout ID/version in own payment history.
Resume follows that original URL; it performs no POST, provider-create call, new
declaration/signature or payment-success inference. Show the frozen declaration and
attestation, not the current editable form's wording. Application reads remain
private/no-store; the link is not exposed to council or other subjects.

Availability requires one pending candidate, current revision, active verified
owner, no duplicate hold, draft status and due fee. The candidate's exact required
safe-file manifest and accepted attestation must still match. Only an HTTPS URL
on the exact `checkout.stripe.com` host with a real provider expiry in the future
is exposed. Userinfo, alternate hosts/ports and control characters fail closed.
Processing/paid/reconciliation candidates, multiple candidates, changed answers
or files, unsafe originals and elapsed/missing expiry disable resume. A pending
candidate also disables `can_checkout` so UI does not request a fresh signature.

Migration0024 retains the provider URL/expiry on the checkout. Migration0025 guards
binding to the actual owner/provider-create context and prevents replacement of
an already-retained link/expiry. Legacy candidates without this evidence remain
unavailable for resume. Elapsed local time does not fabricate a verified provider
expiry event, cancel a checkout or authorize another charge. Existing webhook
and paid-candidate reconciliation remain authoritative.

## Council and privacy follow-ups

- D19 council report rows add `author_id`, `author`, `submitted_at`, `method` and
  `can_revise`. This flag requires the original council author, current writer
  authority and an open original case/proceeding. Another administrator cannot
  rewrite the source author's report. External sources have null account author.
  Applicant report projections retain their existing own-answer privacy boundary.
- Medical SQL policies now require actual JSON boolean `true`, matching Python's
  strict scope semantics. A historical string `"true"` grants no council release,
  file or narrative access. Original subjects retain their own source access.
  Local extraction additionally matches exact request, subject and file owner.
- Message links require current, safe, authorized originals for the same case and
  exact recipients. Request-bound reports/consent stay in their separate protected
  workflow. Invalid/duplicate link lists fail. A message grants no file permission.
- Call records gain forced RLS: council reads, current manager/admin/secretary
  writes retaining actual actor and same-case party. Closed-case communication
  stays allowed. Applicant/anonymous reads and forged actors fail; update/delete
  are unavailable. Outcome/notes bounds are validated; council rows expose actor ID.
- Recording association checks exact report proceeding and source privacy, literal
  boolean notice, and retained source/finalization. Cancelled testimony cannot
  finalize. Transcript review requires safe finalized recording, matching completed
  transcription run, exact latest language/kind version and authorized reviewer.
  Repeated review of the same actor/version returns the retained review/audit.

These audio changes enforce safety around the existing deferred workflow; they do
not configure transcription, implement D20 read/retry/review routes, approve a
recording category/notice, or satisfy D21 unlimited resumable capture. Existing
500MB upload/container limits remain. No transcription/provider success is claimed.
Broader recording/transcript table RLS review remains outstanding.

After0025,50 of63 domain tables have forced RLS;13 remain for review. Independent
browser/provider/institutional acceptance and schema reconciliation remain gates.
No operational migration, credentials, deployment or merge occurred.
