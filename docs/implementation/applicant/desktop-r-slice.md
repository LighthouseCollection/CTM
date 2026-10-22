# Applicant workflow implementation slice

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
