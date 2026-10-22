# Twenty communication, delivery and integrity batches

Issue #2 / backend draft PR #7. Full isolated PostgreSQL suite: **433 passed,
1 skipped**; no model drift; rollback/reapply through0031, restricted-role and
concurrency checks pass. Protected151-table sources stay unchanged.

## Delivered batches

1. Typed message text/recipient/channel/timing validation, including own portal-only
   applicant routing and rejection of empty/invalid recipient collections.
2. Optional client-stable message idempotency keys: exact repeated/concurrent send
   returns the original message and creates no duplicate recipient copy/alert/job.
3. Intended-recipient-only first read acknowledgement, idempotent on repeat.
4. Private receipt projection: applicants receive only their own recipient copy's
   status; sender/case/recipient identity and first acknowledgement cannot be rebound.
5. Bounded message history pagination with explicit continuation offsets.
6. Dispatch rechecks the actual message-to-case-party-to-current-verified-account
   recipient binding; obsolete recipients are discarded without delivered evidence.
7. Applicant-message emails resolve the current manager; invalid/suspended manager
   authority cannot receive private portal notifications. Administrative security
   review alerts replace that invalid routing, without sharing message content.
8. Draft-expiry warnings recheck the original filing, owner and exact current180-day
   deadline, pending checkout and submission/deletion status before sending.
9. Durable random lease tokens fence worker journal updates. An expired/reassigned
   worker cannot mark the new lease delivered or overwrite its retry/discard state.
10. Dispatch batches are explicitly bounded; failed provider actions use exponential
    retry delay capped at120 minutes, retaining generic errors and original jobs.
11. Digest edits serialize with claiming and recheck the quiet deadline before send;
    a newly extended quiet window defers work without counting a provider failure.
12. Numbering accepts aware server timestamps only and retains LA-date allocation.
13. CaseNumberCounter gains forced RLS; runtime table reads/direct writes are denied.
    Allocation goes through a restricted function bound to the eligible filing.
14. Counter identity cannot be rebound/reset/deleted; increments remain monotonic
    with the99-per-day cap. Capacity failure retains state and reports validation.
    Transaction-local context cleanup now allows rollback instead of masking errors.
15. Malformed search response shapes fail closed without returning cached contents.
16. Invalid candidate objects/IDs are ignored and valid hits still reauthorize source.
17. Unsafe document derivatives are excluded from index writes before provider I/O.
18. Local extraction verifies stored original size/checksum before starting engines.
19. DOCX extraction rejects encrypted/oversize XML and entity declarations including
    UTF16 forms. Identical extraction reuses the derivative under a source lock and
    rechecks scan state before persistence; different retained results are not erased.
20. File GET/HEAD/range delivery rejects an original with an unexpected stored length
    before releasing bytes, validators or range metadata.

## Communication contracts

Existing `POST /api/cases/{case_id}/messages/` adds optional
`idempotency_key` (nonempty string up to100 characters). Keep it stable for one
message's retries; use a new key for a new message. Text, case, exact recipients,
channel, email timing/session and file IDs are bound. Changed reuse fails. Existing
callers without a key remain compatible, but cannot claim replay protection.
Applicants may send only to their own portal thread in immediate mode. Staff may
record the supported communication channel and explicit session timing as before.

`GET /api/cases/{case_id}/messages/?offset=0` returns up to50 rows plus `next_offset`.
Each row adds `receipts:[{party_id,read_at}]`; applicants see only their own receipt.
The sender alone receives the stored `idempotency_key`. UI must follow continuation
offsets to load further history. This change is backend-tested, not browser-accepted.

`POST /api/messages/{message_id}/read/ {}` returns `{id,read_at}` for the caller's
intended recipient copy. Other council membership/sender authority cannot mark a
different party's copy read. Portal read evidence never represents email delivery.

## Queue, numbering and source boundaries

Migration0030 adds message replay identity and outbox lease tokens.0031 adds recipient
and journal provenance, worker source-validation helpers and counter RLS/allocator.
SMTP remains externally at-least-once: fencing protects the database journal and
stable Message-ID helps correlation; it cannot guarantee provider exactly-once
delivery when a network result is lost. No fake delivery timestamp is written on
failure, deferral or discarded sources. Retries remain durable; the capped interval
is not a permanent attempt limit. All email bodies remain generic private-portal
alerts; raw provider errors, message bodies and medical data are not sent in alerts.

Runtime allocation requires the current LA date, trusted transaction-local eligible
first-petition context, verified active owner and satisfied fee. Direct counter
access is denied. Migration-owner isolated tests retain deterministic historic-date
allocation. This does not apply operational roles/grants or bypass other filing
validation. Daily exhaustion rolls back filing allocation rather than consuming a
case number or fabricating a submitted filing.

File delivery's new check is stored length, not full streaming checksum validation.
Extraction performs the full checksum check. Existing technical-scan, release,
returned-correction and byte authorization gates still run independently. No
external-index purge, provider setup or OCR/transcription success is claimed.

56 of63 domain tables now have forced RLS;7 core reviews remain (including Outbox).
The source/schema reconciliation map still requires field/lifecycle acceptance;
the63-model count is unchanged. Institution/provider and cross-stream browser
acceptance remain gates. No operational migrations, credential changes, deployment
or merge occurred.
