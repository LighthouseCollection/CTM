# Twenty worker reliability and readiness batches

Issue #2 / draft PR #7. No new domain models or additional RLS tables. Outbox
ownership/RLS remains one of seven core-table reviews; these API/worker guards do
not substitute for the remaining database grant and actor-isolation plan.

## Delivered batches

1. Email delivery requires the backend to return exactly one accepted message;
   zero/None/boolean responses retain a failed job without a delivered timestamp.
2. Email recipients must still have active verified accounts at dispatch.
3. Email addresses are validated before invoking the backend, including rejection
   of malformed/newline-bearing destinations.
4. Only supported job kinds can invoke email/provider handlers. Unknown actions
   remain failed for review rather than becoming generic successful emails.
5. Private orphan cleanup has a real local handler, independent of SMTP, with
   idempotent handling of already absent originals.
6. Draft removal journals cleanup durably in the same transaction as metadata
   deletion, instead of relying on an after-commit callback that can be lost.
7. A draft-deletion rollback also rolls back its cleanup jobs, retaining originals;
   cleanup failures keep generic retry evidence without logging paths/errors.
8. Cleanup checks all retained FileVersion references through a restricted
   security-definer helper, including sources hidden from the worker's actor.
9. Cleanup rejects traversal, absolute/redundant relative keys and in-root symlink
   aliases, preventing an alias from bypassing the exact source-key reference check.
10. PostgreSQL serializes the cleanup reference check and FileVersion insertion on
    the same storage-key advisory lock. Existing private original ownership and
    metadata-before-byte publication remain unchanged.
11. Digest claiming obeys the dispatch row budget; a single case cannot cause an
    arbitrarily large materialized/claimed batch.
12. Candidate selection skips active leases, preventing already busy jobs from
    filling the candidate limit and starving available due work.
13. Row claims use SKIP LOCKED so an ordinary job held by another worker is skipped.
14. Candidate and digest selection use deterministic due/creation/ID ordering.
15. Administrative delivery status adds bounded pagination, typed state filters,
    aggregate state counts and sanitized metadata without private payloads.
16. Explicit administrative retries check the observed attempt count, serialize on
    the job row, refuse terminal/active leases and invalidate stale lease tokens.
    Exact repeated retry requests do not create another audit action.
17. PostgreSQL retains queue identity and payload. The supported planned-session
    transfer can update only the session binding matching the retained Message.
18. Readiness detects RLS flags without a SELECT policy and security-definer
    helpers without the expected fixed search path, beyond existing flag counts.
19. Readiness reports PUBLIC domain-table privileges and missing/privileged worker
    roles, without applying grants or treating role presence as acceptance.
20. The public readiness CLI uses the shared inventory-based database checks, so
    non-tribunal-prefixed domain tables are included consistently.

## Administrative queue contract

`GET /api/system/delivery/?state=failed&offset=0` is administrator/secretary only.
`state` is optional: pending, failed, leased, delivered or discarded. Results:

```json
{"counts":{"pending":0,"failed":1,"leased":0,"delivered":0,"discarded":0},"items":[{"id":"uuid","kind":"transcribe","state":"failed","attempts":1,"due_at":"ISO timestamp","created_at":"ISO timestamp"}],"next_offset":null}
```

Items are limited to50; follow `next_offset`. Counts cover all queue states, even
when filtering items. Unknown stored kinds project as `unsupported`. Responses
exclude recipient addresses, storage keys, source payloads, provider errors and
lease tokens. Responses are private/no-store. Applicant/member/president roles
receive403; administrative authority is checked on each request.

`POST /api/system/delivery/{id}/retry/` accepts
`{expected_attempts:positive_integer}`. Success returns
`{id,attempts,queued:true}`; stale attempts return409
`{error:"attempt_conflict",current_attempts:number}`. A terminal or actively leased
job cannot be retried. An eligible failed job becomes due, clears generic failure
and invalidates its expired lease. Existing attempt history is retained. A repeated
request for the already queued same attempt returns the receipt without another
audit. A new worker failure changes the attempt count, requiring a fresh review.
Retry does not change payload/recipient, grant missing authority, configure a
provider or imply email/payment/transcription success. Ordinary privacy/source and
quiet-window checks still run at dispatch.

## Cleanup, claiming and acceptance limits

Draft deletion now removes eligible metadata and retains a durable cleanup action;
private bytes remain until that action executes. Retained formal sources and
pending checkout cleanup holds are unchanged. Cleanup has a hash-based key so long
storage names cannot overflow the journal key. A still referenced source is
discarded without deleting bytes; invalid/unavailable cleanup paths retain a failed
job for review. A successfully absent/unlinked original completes a local action,
not an email. Existing technical-scan/returned-correction/release rules remain.

Migration0035 grants only the orphan-reference helper to an already existing
`ctm_worker` role; it does not create/configure roles or establish their full scope.
Isolated tests explicitly grant the helper to a non-owner validation role to prove
that hidden retained files prevent deletion. Operational worker/retention/payment
and processing grants still require acceptance. Worker role presence or safe
attributes do not clear those gates.

Dispatch remains externally at-least-once. Positive backend acknowledgement is not
recipient inbox/read evidence. A bounded digest can be split across dispatches
when its pending rows exceed the selected limit; no exact one-email-per-unbounded
editing-session claim is made. Digest quiet-deadline rechecks remain. SKIP LOCKED
does not remove the short existing per-case advisory serialization of digest
claims. Lease fencing protects the journal, not atomic SMTP delivery.

Readiness is read-only and always retains outstanding schema/provider/end-to-end
gates. Diagnostic catalog checks are not semantic policy verification. Domain
inventory remains63 models,91 routes,56 forced-RLS tables; seven core reviews
remain, including Outbox. No protected build-spec/accepted question changes,
operational migrations, credentials, deployment or merge occurred. No UI/browser
or live-provider acceptance is claimed. Full validation: vm-frm-progress.md.
