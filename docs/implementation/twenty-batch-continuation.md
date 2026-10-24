# Twenty functional backend batches

Issue #2 / draft PR #7. No operational migrations, credentials, deployment or merge.
The current model count stays63. The approved151-table sources remain unchanged.

## Delivered batches

1. Own pending-filing supplement history and `can_supplement` in application detail.
2. Applicant supplement writes require current `expected_version` under application lock.
3. Supplement `idempotency_key` binds original text/file IDs; exact retries recover
   the retained receipt, including after withdrawal. Changed retries fail.
4. Supplement evidence must be latest, safe, own, ordinary and same application/case;
   request/consent sources, duplicate IDs and malformed lists are rejected.
5. Recording capture accepts nullable measured `duration_ms` and optional bounded
   `recording_notice` object with literal `acknowledged:true`; actual entering actor
   is retained as `captured_by`. This records supplied facts, not wording approval.
6. Recording retries preserve capture identity/metadata; changed replay facts and
   raw metadata rewrites fail. Legacy facts stay null; no fabricated backfill.
7. Attributed transcript corrections create a new immutable numbered version with
   current reviewer, source, version and input checks. Exact retry recovers it;
   stale changed writes fail and review never transfers to the correction.
8. Recording list pagination (50 rows) and transcript metadata pagination (100 rows)
   reject invalid offsets and supply continuation offsets.
9. Ordinary council gets sanitized processing status through a scoped database
   projection; raw processing-run diagnostics are restricted to reviewers. Exact
   reviewed transcript reading does not depend on access to raw diagnostic rows.
10. Reproducible151-to-current-adapter reconciliation inventory, without automatic
    missing-table or completion claims:122 candidate associations and29 unmapped
    concepts requiring review. This is a review map, not122 completed features.
11. Pending-party input validates email, name types, lengths and normalization.
12. Same-case/email pending association is reused; conflicting names require review;
    a partial unique constraint prevents duplicate pending intents.
13. Authorized party linking serializes person/case access and rechecks current case
    state and existing claims. Concurrent same-person links reuse one party/claim.
14. Registration cannot activate an intent from suspended/no-longer-authorized staff;
    it retains a `needs_review` intent without linking. Actual verification actor
    and original authorization actor remain distinct in audit evidence.
15. Admin/secretary cancellation of a pending intent retains history and prevents
    later registration activation. Activated associations require separate correction.
16. PendingPartyLink gains forced RLS, verified-subject matching, activation checks,
    retained authorization provenance and delete/rebinding guards.
17. Historical publication requires the staging creator; another admin cannot
    publish that private workspace. Published payload/author binding is retained.
18. Historical payload validation rejects malformed/duplicate slots and invalid or
    duplicate account links before creating a case. Unknown historic dates stay unknown.
19. Council enrollment validates provider-subject/email/name inputs. Suspension needs
    a literal boolean and cannot remove the final active admin; local passwords stay disabled.
20. Council request cancellation requires the displayed request fingerprint, current
    authority and unfinished/open source. Cancelled requests reject later response,
    upload/send and external-token access; matching cancellation replay is retained.

## Applicant contracts

Own `GET /api/applications/{id}/` adds, for reconsideration filings only:
`can_supplement` and `supplements:[{id,text,manifest,timestamp,idempotency_key}]`.
Only the owner/actual supplement actor's history is returned. Council hearing and
disposition controls remain absent from the own projection. Existing own checkout
resume and delete/withdraw capability contracts remain available from earlier heads.

`POST /api/appeals/{id}/additions/` now requires:

```json
{"text":"additional information","file_ids":[],"expected_version":1,"idempotency_key":"client-created stable key"}
```

Use a fresh key for a new supplement, retain it through interrupted/concurrent retries,
and re-read own history to recover. Success remains `{id}`,201. Existing formal
answers/signature/fee are untouched. Pending withdrawal/decline still does not notify
the other spouse. An exact saved retry creates no extra supplement or alert.

## Council contracts

- Existing `POST /api/recordings/` adds optional `duration_ms` (non-negative integer
  below signed64-bit storage bound) and `recording_notice` (object up to10KB with
  `acknowledged:true`). The server chooses `captured_by`. Supplied notice text is an
  attributed snapshot, not institutional approval or a substitute for the existing
  `notice_recorded` finalization gate. Category approval and streaming remain open.
- `GET /api/reports/{id}/recordings/?offset=0&transcript_offset=0` adds outer
  `next_offset` and per-recording `transcripts_next_offset`. Capture fields now
  contain actual retained values when known. Legacy fields remain null.
- `POST /api/transcripts/{revision_id}/correct/` accepts
  `{expected_version:1,text:'corrected source',segments:[]}`. It returns
  `{id,version,reviewed}` with201. New versions are unreviewed. Current reviewer
  authority, completed safe source and open original proceeding are required.
  Closed-case historical correction remains a separately gated reconciliation
  because the existing database guard locks original proceeding writes.
- Council request rows now include `request_version` for
  `POST /api/requests/{id}/cancel/ {expected_version:request_version}`.
- `POST /api/pending-party-links/{id}/cancel/` is admin/secretary-only. It returns
  `{id,state}`. No account or case-party record is erased or reassigned.

## Schema/security evidence and limits

Migrations0028/0029 retain capture/replay fields, enforce pending-intent uniqueness,
and add PendingPartyLink forced RLS/provenance, typed source guards and narrowly
attributed correction writes.55 of63 domain tables have forced RLS;8 core table
reviews remain. This does not imply that remaining provider, role, identity,
field-semantic and cross-stream acceptance work is complete.

Run `python docs/implementation/build_reconciliation.py` after refreshing the model
inventory to regenerate `schema-reconciliation.json`. Every approved table has a
candidate or unmapped review disposition, purpose and direct-column difference list.
Same names/columns are not semantic equivalence. Multiple approved concepts may
share an adapter/JSON field and still need constraints, history or field work.
Neither29 unmapped concepts nor88 arithmetic model/table difference is a table-build
quota. Governance must review actual gaps and any consolidation before integration.

Independent applicant/council browser acceptance, approved bilingual wording,
provider/output-worker integration, unlimited media uploads and the PDF CDN defect
remain separate. No live scan, payment, mail or transcription success is fabricated.
