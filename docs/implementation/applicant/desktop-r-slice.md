# Applicant workflow implementation slice

## Current linked first-petition checkpoint

Linked-spouse first-petition entry is implemented; actual two-filer and closed-case first-petition submission coverage replaces prior constructed-filing state.94 frontend tests, six entry fixture groups and nine shell groups pass. Unmodified integration104e4fd passes75 applicant API/browser groups; the explicit local review candidate with the named module/minimal hook passes76. This is not an integrated successor or institutional acceptance. [Report and blockers](linked-petition-report.md) | [Candidate JSON](linked-petition-api-result.json). Earlier counts and fixture gaps below are historical snapshots.

## Current private message integration (2026-10-21)

Applicant-only messaging now integrates backend db6dfa3: exact own thread binding,
50-row private history continuation, reviewed sending with stable replay keys,
receipt recovery and explicit own portal-copy read acknowledgements. Portal read
evidence is displayed separately from email delivery. Shared shell changes remain
a governance integration patch; no council/shared source is edited directly.

Current checks: 83 frontend tests, 66 real API/browser groups, eight message
interruption/EN–AR fixture groups and nine shell groups pass. These use isolated
SQLite/synthetic sessions and scanner test policy; controlled provider output is
still a fixture. Earlier per-feature counts below retain their recorded snapshots.
PostgreSQL, live email/payment/provider/antivirus and institutional content/issuance
acceptance remain separate. [Report](message-integration-report.md) and
[Download JSON](message-integration-result.json).

## Current supplement integration (2026-10-21)

Backend a0bd138 now supplies own supplement history/capability, version checks and
idempotent recovery. The applicant workspace consumes actual hash-only manifests,
freezes the displayed version and one key, recovers matching own receipts, and offers
explicit exact retry after refresh. It supports appeal and closed-case first-filing
reconsideration; the latter is verified with controller/contract browser fixtures.

Current checks: 78 frontend tests, 61 real API/browser scenario groups, nine
supplement interruption/EN–AR groups and nine shell groups pass. The real runner
uses isolated SQLite, synthetic sessions/content and scanner test policy. Controlled
provider output remains a fixture. No PostgreSQL/live-provider/antivirus/institutional
wording/signature/issuance acceptance is claimed. [Report](supplement-integration-report.md)
and [Download JSON](supplement-integration-result.json).

## Current filing/recovery verification (2026-10-21)

The next ten batches integrate backend `d724ba56b8bd5cf501d55fbbca416470108f963a`
(including filing contracts introduced in acafe29). Own draft deletion and withdrawal
now use the server capabilities and current answer version. Original checkout recovery
uses the retained candidate, attestation, exact declaration and future provider expiry.
Local expiry removes resume only; it never reconciles a payment or enables a new charge.

Current checks: 68 frontend tests, 54 real API/browser scenario groups, 11 response/
recovery/lifecycle fixture groups and nine shell groups pass. The earlier 66/42 results
below are historical snapshots. All backend data is isolated/synthetic; one controlled
provider-create output verifies retained adapter behavior without network or a charge.
The second joint filing and pending appeal state are explicit fixtures. PostgreSQL,
live provider callbacks/antivirus, institutional wording and document issuance remain
outside this acceptance. [Report](filing-recovery-batch-report.md) and
[Download JSON](filing-recovery-batch-result.json).

## Earlier verification: first ten batches (2026-10-21)

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

## Earlier evidence (historical snapshots)

Earlier missing-contract and closure-failure statements below describe their recorded backend versions; the current verification above supersedes those statuses.

Implements issue #1 under governance #4 and the approved build-spec. This document
records implementation boundaries, not replacement product or questionnaire approval.

## Workflow modules

`static/ctm/applicant.js` exports `window.CTMApplicant.ApplicationEditor` accepting
`applicationId`, the existing CSRF-aware `api` function, `lang` (`en`/`ar`) and
`onBack`, plus `onNavigationGuard` for parent navigation. The `api` adapter must
attach `status` to every failed HTTP response, including 403/404. Governance loads
the module before `app.js` and owns navigation wiring.
The editor fetches only the selected application's authorized projection. Published
questionnaire wording and stable answer codes come from its bound server version;
missing wording or unsupported definitions block editing rather than invent content.
The council interview bank is not a substitute applicant questionnaire.

`StartApplication` delegates draft creation/reuse and eligibility to the existing
POST endpoint; it does not allocate a case number or manufacture a case claim.
The proposed applications-page hook displays fee/document preparation guidance
before the user starts. Text, textarea, date, choice, list-of-choices and boolean
fields render from approved server definitions. Boolean unanswered and false are
distinct; contextual hidden answers remain preserved.

`applicant-appeals.js` supplies `StartAppeal` for authorized case context. It sends
only kind/case identity to existing application creation, validates a same-case appeal
acknowledgement and opens the bound editor. No case status change is issued. Closed
proceedings remain an entry context when a sibling appeal has reopened the case;
the server resolves eligibility/reuse. Concurrent starts are suppressed and late
acknowledgements cannot navigate after unmount. Remaining applicant features and
dependencies are tracked in [remaining work](remaining-work.md).

Saved drafts retain incomplete answers and unknown keys. Explicit save sends the
complete answer object and `expected_version`; only server acknowledgement updates
the version and saved indicator. Failed/stale saves keep local input and offer
explicit reload, never automatic overwrite. No case answers enter browser storage.
Read-only review reflects local answers and marks unsaved changes. Arabic uses the
same answer codes and values with approved Arabic labels and semantic RTL.

## Dependencies and ownership

VM-FRM owns the questionnaire projection and server `can_edit` capability requested
on issue #1. Proposed definition follows seed `fields` with `code`, `type`,
`required`, plus `label_en`, `label_ar`; choices need stable values and both labels.
The renderer accepts object choices `{value,label_en,label_ar}` or existing
primitive `choices` plus `choice_labels[value] = {label_en,label_ar}`. The latter
preserves current backend choice validation. Existing `when: {field,equals}` uses
the backend's strict equality predicate; hidden answers are retained. Unsupported
conditional vocabularies remain blocked until a shared contract exists. Repeated
records use the proposed `list.item_fields` vocabulary in `api-contract.md`, retain
existing IDs/unknown keys and generate IDs only for new rows. Approved full repeat
definitions and backend nested validation remain dependencies.
This proposal must be reconciled with the backend owner's response before claiming
API integration complete. Draft save already accepts `{answers, expected_version}`.
No migrations, backend edits, shared shell edits or protected build-spec changes.

`applicant-files.js` implements contextual originals and current-file checklist;
`applicant-filing.js` implements approved declaration, fee/waiver display, checkout,
submission and returned correction actions. They require the projections documented
in `api-contract.md`; missing capabilities or file requirements block filing.
Every acknowledged answer-version change reloads contextual document requirements.
Upload attempts invalidate the previous review; uncertain uploads require a fresh
listing, safe required originals and explicit review before filing. Original file
versions are never deleted or exposed as applicant attachment history.

First submissions and checkouts freeze the reviewed version and signature for
uncertain retries. Submission retries retain their idempotency key. Attempted filing
blocks editing/uploads/document refresh until retry or explicit application-status
reload. Returned corrections reuse the original signature and fee. Filing capability
is independent of answer-edit permission; read-only answers can be reviewed.
No payment completion is inferred from checkout or browser navigation. No local
passwords, invented declaration, waiver request or fabricated external processing.

`applicant-appointments.js` exports `CTMApplicantAppointments.Appointments({api,lang})`.
It displays private invitation instructions, supplied offset start/end times and
current-version response. Confirm/Reject sends the exact invitation version;
rejection explanation is optional. Successful acknowledgement, stale version,
permission failure and network uncertainty lock actions until an explicit refresh.
Cancellation/ineligibility removes response controls. No council schedule fallback
or self-rescheduling exists. Its owner-only read route is integrated at backend
`7684169`; actual API/browser checks cover confirmation, rescheduling, rejection,
cancellation and isolation. A generic invitation heading accommodates the actual
case-ID projection without exposing a raw UUID. The shared shell patch proposes
applicant-only My appointments navigation and module loading, without modifying
shared source files in this branch.

`applicant-payments.js` exports `CTMApplicantPayments.PaymentHistory` for the own
application's real payment read projection. It distinguishes outstanding fee,
authorized waiver, verified provider payment, checkout processing/reconciliation
and refund/dispute facts. Cumulative refund amounts are labelled without summing
them. This view makes GET requests only and does not grant filing capabilities or
offer applicant reconciliation/refund writes. Failed or invalid refresh clears old
financial facts. Browser/API tests verify a real authorized fixture waiver remains
distinct from provider payment; no provider success is invented.

## Proposed shell patch

`shell-integration.patch` is for governance to review/apply serially, not an applied
change to shared surfaces in this branch. It loads the separate module, opens it
from application cards, passes the server-session CSRF helper and preserves failed
HTTP status codes. It registers an editor navigation guard so sidebar navigation
cannot silently discard changes. Back already passes through the editor guard,
so its callback bypasses a second guard invocation after explicit discard.
Language-preference failures use a separate notice without unmounting the editor.
The patch loads files/filing modules before the editor and omits JSON Content-Type
for FormData, allowing the browser's multipart boundary while retaining CSRF.

Check against the target branch before applying:

```sh
git apply --check docs/implementation/applicant/shell-integration.patch
git apply docs/implementation/applicant/shell-integration.patch
```

`scripts/browser_applicant_shell.py` copies shared sources into an ignored `.tmp`
directory and applies this patch there. It does not modify the shared checkout
files. Reconcile the patch if council/governance changes its contexts.

## Validation

Prepared appeal supplements render separately from immutable submitted answers.
The editor guards navigation and unload while local supplement text/evidence or an
append is pending. The module requires explicit own capability/history, reviews
escaped text and clean evidence, and locks uncertain attempts against blind retry.
Backend read/capability integration remains pending; the current server cannot
enable the append controls. Shared loading is supplied through the proposed patch.

Behavior tests cover question-definition rejection, stable keys, partial draft save,
preservation of unknown fields, optimistic versions, stale/error recovery and language
switching without losing input. Real pinned-CDN browser checks cover accessible
labels, review/save, EN/AR RTL, runtime `[style]` and horizontal overflow. Synthetic
API/CDN UI checks do not establish production identity or PostgreSQL readiness.


## Released decree panel prepared

`applicant-decrees.js` supplies a separate applicant case panel through the proposed
shell patch. It displays explicit own active release metadata and authorized signed
PDF actions with Plenix controls. No filing-order or closed-case entitlement guess
is made. Refresh clears stale links; denied or malformed responses show unavailable.
The own case release-list extension is supplied by backend 444bad8 and verified
through actual API/browser integration.
Synthetic presentation fixtures remain separate from the real API release/read/
withdraw checks; signing/issuance and operational acceptance remain pending.


## Own request reader

`applicant-requests.js` reads the actual private case request endpoint through the
proposed shell integration. It shows sent request instructions and bound question
wording, switches bilingual snapshots with locale, and clears stale content on
failed/malformed refresh. Staff drafts, interviews and external requests are rejected
by the client contract as well as filtered by the server. The actual backend cannot enable the prepared intake response editor; own action
capabilities/concurrency and approved signed-release/scope contracts remain pending.
No professional upload or consent checkbox is exposed without those contracts. Intake responses and professional
report/release submission are therefore not complete.


## Five-task batch

Prepared response/recovery/lifecycle modules load through the shared patch. Intake
responses are capability/version gated, reviewed and guarded against silent loss or
blind retries. Lifecycle confirmations distinguish draft removal from own withdrawal;
competing writes are locked through uncertain acknowledgement until status refresh.
Actual payment history blocks fresh checkout/signature while candidates are unresolved;
resume uses only a matching original server snapshot and existing safe URL.

Supplement owner writes and decree byte-route release/withdrawal are verified through
actual isolated APIs. Their own read projections still require backend integration.
Professional signed release and approved bilingual content remain institutional/backend
dependencies. The technical candidate checker and reference inventory make wording
coverage reviewable; they do not approve or publish content. Default acceptance is
blocked by reproduced unsent staff-request disclosure after closure (GitHub #2).
