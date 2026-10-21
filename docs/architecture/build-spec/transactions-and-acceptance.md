# Transactions and build acceptance

This is the required behavior accompanying `schema.sql`. Cross-table and external-provider rules cannot be guaranteed by a field dictionary or UUID foreign keys alone. Implement through named Django commands/services, scoped database policies and database constraints/triggers where appropriate. Never expose unguarded CRUD for these tables.

## Shared transaction rules

Lock stable canonical person rows in UUID order before eligibility changes; then lock case, proceeding and resource rows in consistent order. Retry serialization/deadlock conflicts with the same idempotency key. Reject stale optimistic row versions instead of silently overwriting. Every same-case/owner relationship must be checked on insert/update (composite FK or guarded database trigger), including nullable draft-to-case transitions. UUID references alone are insufficient.

Every successful domain write commits its audit/revision and outbox event atomically. Email/payment/OCR APIs run outside that transaction. Jobs have durable leases, backoff, replay-safe keys and visible failure state; PostgreSQL outbox is the source for redispatch. Never hold database locks while waiting for a payment provider or transcription API.

### Start new-case draft

Lock canonical person; reject current open-case claim, except filing into an already linked same case. Acquire unique active draft claim, reuse existing draft instead of duplicating. Store private revision. Appeal drafts use a separate per-person/case pending-appeal claim. Staff historical-entry staging is separate. Unknown spouse data does not block saving.

### Finalize filing

1. Check active verified owner, exact duplicate hold, form version/requiredness, correct contextual file safety and sizes, declaration/signature, fee obligation, immutable frozen candidate.
2. Verify payment success against provider event/amount/USD/filing or authorized waiver/exemption. A normal application cannot become submitted merely by creating checkout.
3. Lock person eligibility. For known exact marriage signature, acquire an advisory transaction lock derived from marriage date+sorted DOB pair; requery candidate matches. Compare unambiguous party mapping. If no exact/known match, do not treat nulls as equality. Review ambiguous mapping before granting access.
4. Reuse matching case or atomically allocate LA date/counter<=99 and create case. Claim only known participating identities. Unregistered absent spouse is not a fictitious applicant/account/open-case claim. A later verified link reacquires its own constraint safely.
5. Preserve independent submissions/payment/party ownership. A second filing into the same case is not a second case or person merge. Release new-case draft claim; acquire open-case claim; enforce no different-case conflict.
6. Store immutable submission/manifest, retain every relevant submitted file version, allocate payment once and enqueue initial review/receipt. Mark candidate finalized. Retried provider callback returns same submission, not another number/charge.

If an externally successful charge arrives while finalization is blocked, keep a recoverable paid candidate and a staff-visible reconciliation issue. Never lose the payment, charge again, bypass privacy or silently fabricate a refund policy. Eligibility and existing records remain intact until resolution.

### Correct/resubmit and cleanup

Corrections lock application, check open current proceeding and permitted writer, create immutable revision/field changes. No reason or re-sign, no second fee for returned filing. Review binds exact submission/manifest. Original and subsequent received versions stay accessible with safe owner projections. Applicant own answer histories remain available; attachment histories council-only.

Cleanup serializes with candidate/payment/submission. Only never-submitted expired/deleted draft graphs are eligible. Remove no retained file references or in-flight successful payment candidate. Warn seven days before180day inactivity expiry; recalculation uses last applicant activity, not OCR/template job activity. Minimal cleanup audit may outlive deleted draft content. Explicit wrong report-upload exception deletes wrong payload/derivatives and keeps a correction event; it is not generic delete permission for signed manifests or a way to erase an attested submission. If a wrong upload is already bound into a formal signed manifest, quarantine and require controlled resolution rather than breaking the manifest silently.

### Assignment and sessions

Reassignment: require president authorization and separate entering admin/secretary, close old interval/create new atomically, preserve history and enqueue correct notifications. Partial unique index ensures one current assignment. Future alert dispatch rechecks assignee.

Planned session reschedule: lock source/destination sessions; reject completed-history rewrite; check unique new date. Create new dated session, transfer every agenda case and affected appointments with snapshots and fresh invitations, remove old draft agenda links/attendance if any; preserve case-level transfer audit without FK dependency on deleted session. Completed case hearing, decision or assignment referencing that session prevents deletion and is outside planned-meeting reschedule path. Do not use cascading deletion. User does not want a cancelled session in session list/history.

Session close: mark completed items; time-exhausted unpresented items carry only to earliest already-dated upcoming session, otherwise awaiting placement. Absent presenter/deliberate deferral always manual placement. Unique target case agenda item prevents duplicates. Bind `Send after council session` deliveries to that exact session and enqueue on close; do not infer a fixed17:00 deadline. Record deliberate session association for deferred messages; without it require selection or immediate mode.

Testimony scheduling locks relevant case/session schedule and rejects overlapping two-applicant testimony. Actual durations can be unknown; don't invent end times, but scheduling must confirm non-overlapping segments before invitations for both. Record old/new appointment versions; responses bind version. Confirmation/rejection doesn't remove internal agenda item. Expired reminder jobs recheck version/cancellation. Assigned absence prevents hearing completion; votes remain full roster independent of attendance.

### Requests, reports and processing

Request send freezes exact selected questions and language, identifies subject and issuer and activates only own-applicant or scoped external capability. Refresh affects unsent draft only. Submission checks case/proceeding still open, request not cancelled/completed, link unexpired/unrevoked where applicable; locks response and disables further recipient writes. All current report content visible council within source privacy; unreviewed AI text remains separately restricted. Applicant readonly own submitted answers do not reveal staff observations/audio.

Original report author may revise authorized narrative while open with every revision; new manager adds linked follow-up. Submitted applicant/external text remains source material; staff interpretation is attributed separately. Record actual entering user when staff captures someone else's response. Entire-report recording finalization enqueues processing exactly once for that version/task; intentional retry gets new run, original AI output retained. Only exact reviewed text versions become searchable/readable to other council. Edits after review require review of the new version.

Medical submission requires exact subject-signed release and scope; invalid/pending authorization content stays hidden. Local-only processing and restricted search use same authorization. Background jobs cannot send medical files/text through generic translation fallback. Reassignment does not rewrite signed recipient scope. Revocation handling needs approved institutional release wording before live medical collection; fail closed for any unsupported release change.

### Decision, issuance and closure

Record exact decision type/grounds/party conditions version before votes. Current tally is latest effective vote per member for that exact version; preserve earlier votes. Only self/admin/secretary entry; distinguish voter/enterer. Approval references exact version/president/enterer and timestamp. New type/grounds version cannot inherit approval or votes.

Issuance locks case/proceeding/decision/decree; verifies authorized issuer, latest approved decision and matching stored signed PDF/signer. Commit issuance and closure/release all canonical-person open-case claims plus notice outbox atomically. Closed original report/note/finding/answer content remains locked. Explicit certificate release is a separate retained action with entitlement/version check; issuance never auto-releases.

Denial closes without decree certificate. Party withdrawal locks all participating-filer withdrawals; only sole filer or all participating filers withdrawn closes. Admin may record for all. Retain participation/fee/history. Neither abandoned unregistered spouse nor a pending invitation is automatically a second filer preventing withdrawal. If linked party has not filed, use participating-filer evidence rather than mere existence of spouse row.

Closed case allows narrow ongoing actions: private communications, finance events/audit, certificate release/access withdrawal, historical transcription corrections and pending appeal work; these do not unlock original substantive proceedings.

### Appeal acceptance and account consolidation

Per-person/case claim covers draft/pending appeal; create exactly one fee obligation per filing. Pending additions owner-only immutable supplements; withdrawal locks disposition, marks withdrawn and releases claim. Accept/Decline is unique and race-protected with withdrawal. Both appeals retain independent results under one hearing.

Acceptance locks case and all known participating canonical persons in order. Reject different open-case conflict without losing appeal. Create one open appeal proceeding if none; sibling acceptance joins it. Close original remains locked. Result+proceeding link+claims+private notices commit together. Declining sibling cannot reclose case. Appeal decree sequence allocated when decree-producing appeal proceeding is identified, not per submitted appeal; preserve original numbering/access.

Identity consolidation locks source/target persons and every affected open-case/draft/pending-appeal claim. Exact matching is only a hold, not a merge. Admin/secretary selects verified primary account, disables duplicate and appends canonical alias without rewriting original actors. Two different open cases require resolution before commit; don't auto-close or erase either submission. Role/provider linkage and case marriage association corrections are distinct operations.

## Required acceptance scenarios

| ID | Required proof |
|---|---|
| SEC01 | Applicant A cannot read B's fields, files, reports, medical release, messages, histories, counts, search snippets or range URLs. |
| SEC02 | Council cannot read unsubmitted applicant draft, including index/preview; historical staging has explicit publisher boundary. |
| SEC03 | Unrelated council member can read submitted case but cannot mutate assigned-only resources; suspension/reassignment invalidates stale permissions. |
| SEC04 | Only existing admin adds council; arbitrary Microsoft email cannot self-enroll; provider subject/issuer/tenant validated. |
| SEC05 | Revoked decree release and expired/reissued priest link deny subsequent requests, previews and downloads. |
| SEC06 | Medical missing/wrong release denies bytes/OCR/search; external AI request capture proves no medical egress. |
| INV01 | Concurrent new-case drafts/submissions/historical links cannot yield two open cases or active new-case drafts for one canonical applicant. |
| INV02 | Exact reverse-role marriage match links same case despite differing certificates; unknown/multiple/ambiguous matches don't auto-link. |
| INV03 | LA midnight numbering, concurrent daily allocation,99cap and legacy alias collisions preserve unique allocated namespace. |
| PAY01 | Retried/out-of-order payment webhook and interrupted browser return produce one allocation/submission; invalid amount/signature doesn't submit. |
| PAY02 | Waiver/exemption explicit; returned resubmission costs nothing extra; chargeback keeps submission; only accidental duplicate refund allowed. |
| VER01 | Corrections retain exact original answers/files/submission declaration, actor/time; own answer history visible, old file versions council-only. |
| VER02 | Applicant draft migration retains answers; report unsent draft explicit refresh; sent questions/published translations unchanged retroactively. |
| SES01 | Planned reschedule moves all agenda cases without retaining cancelled session; completed history cannot be deleted. |
| SES02 | Time-exhausted/no-next-date/absent-presenter/manual-deferral branches behave distinctly and don't duplicate agenda items. |
| SES03 | Separate testimony times, fresh response on reschedule, no applicant deliberation access, version-safe one-day reminder. |
| REP01 | External link30days, replacement preserves draft/disables old, paper upload completes request; follow-up gets own report with parent link. |
| REP02 | Whole recording recoverable, finalize queues task; failed task retains source; original/mixed/EN/AR versions/speaker edits preserved. |
| REP03 | Unreviewed generated text absent from other council/search until exact review; typed answers never overwritten by transcript. |
| DEC01 | Revised type/grounds requires fresh approval/votes; president approves without votes; full roster visible independent of attendance. |
| DEC02 | Issuance impossible without matching stored signed PDF; closes atomically, certificate hidden until release; caseworker cannot manage decree. |
| APP01 | Two appeals, one hearing, independent result; sibling acceptance reopens once; sibling decline/withdrawal doesn't undo reopen. |
| APP02 | Another open case blocks reopening; retained source proceedings remain read-only; repeat appeal/per-filerfee/one-pending guards hold. |
| MSG01 | Both-recipient message has separate private copies; document link grants no additional access; email reply routing idempotent and attachments returned. |
| MSG02 | Session-deferred email dispatches once on selected session close; portal immediate; no unintended17:00 cutoff. |
| NOT01 | Ten-minute applicant quiet digest, current-manager-only delivery, silent staff corrections, explicit admin finance/security alerts. |
| RET01 | Cleanup versus submit/payment races cannot delete retained data;180days/7day warning; wrong-upload exception auditable and narrowly scoped. |
| OPS01 | Restore reconciles database, source files/checksums and secrets; search rebuilt; no public data-service ports or secrets in UI/logs. |
| UI01 | Every screen uses documented Plenix0.58.0; runtime inline-style checks and English/Arabic RTL flows pass; only isolated Arabic exception. |

These are implementation acceptance requirements, not tests claimed to have run against a CTM backend. Structural validation results are separately recorded in `validation.json`.
