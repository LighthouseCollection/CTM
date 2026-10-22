# Desktop-R applicant workflow evidence

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

## Earlier evidence (historical snapshots)

Earlier missing-contract and closure-failure statements below describe their recorded backend versions; the current verification above supersedes those statuses.

Validation performed 2026-10-21 against base `6928c484aeafd580434db794bcdcf4b95052bab2`.
All records are synthetic. No operational data, external payment, provider sign-in,
deployment or production-readiness acceptance is represented by these checks.

| Check | Result | Scope |
| --- | --- | --- |
| `node --test tests/frontend/*.test.cjs` | 66 passed | Bound definitions, repeat stable IDs/opaque fields, incomplete save, optimistic versions, errors/permission lock, boolean false/unanswered, conditional retention, start/reuse, filing eligibility, immutable signature/idempotency retry, private download paths, context replacement, size gates, malformed current-file projection, invitation version/capability and response locks |
| `uv run --group browser python scripts/browser_applicant.py` | 19 scenario groups passed; no page errors | Real Plenix 0.58.0 CDN, synthetic API; escaped review, save, language/RTL, unsaved guards, declaration/fee/signature layout, waived filing, read-only returned resubmission, unsafe checkout, uncertain upload/readiness, boolean conditional save, automatic checklist/capability refresh, repeat add/correct/review/remove in RTL, submitted prompt and bidi case-reference regression, editable/read-only identity-hold notice EN/AR, clean-answer in-flight upload unload guard and cleanup |
| `uv run --group browser python scripts/browser_applicant_shell.py` | 9 scenario groups passed; no page errors | Proposed shell patch applied only to temporary copies; actual helper, sidebar/back, preference success/failure, 403/404 lock, multipart boundary/context/replacement, pending-scan links, Arabic layout, start/reuse/eligibility error, applicant appointment navigation |
| `uv run --group browser python scripts/browser_applicant_api.py` | 42 scenario groups passed; default closure-privacy gate passed | Real Django APIs against backend `480a246118cce8c4ac338c32c71c79cde74816d2`, isolated SQLite/synthetic accounts; start/form/repeat save/preferences, stale history, draft/file privacy, browser required uploads/downloads/correction with retained original bytes, latest synthetic scan-event gates, clean current-file listing/capability refresh, authorized fixture waiver, browser declaration/signature/submit and real key replay, browser returned resubmit, actual status refresh, own payment history and draft-payment privacy, resubmit pending-scan atomic rejection and original attestation linkage, held-draft save with blocked checkout preparation/submission, returned retention/delete safety, two contextual RO copies/cross-order rejection/bilingual saved captions, actual appointment confirmation/reschedule/stale rejection/cancel/isolation, default returned-privacy/owner access/assigned-manager alerts/formal resubmission snapshot, AS-F25 pending replacement preserves formal-file access, appeal start/reuse/save/evidence/waived submit, reopened-sibling entry and missing supplement capability fails closed and actual empty own decree release-list exposes no PDF links; own bound request rendering, staff-only filtering and linked-spouse request isolation; actual pending-checkout guard, supplement owner-only POST, and decree release/withdraw exact-byte full/range/preview/HEAD access. These do not cover real signatures/issuance. Current run also verifies bound intake/assessment responses, scoped uploads, explicit consent, exact replay and closure privacy recovery. |
| `uv run --group browser python scripts/browser_applicant_appointments.py` | 5 scenario groups passed; no page errors | Proposed read-contract fixtures only; private escaped instructions, exact offset times, Confirm/Reject/version, stale/uncertain lock, rescheduled version reset, cancelled controls, Arabic mobile layout, malformed/empty/unavailable listing |
| `uv run --group browser python scripts/browser_applicant_appeals.py` | 3 scenario groups passed; no page errors | Appeal eligibility failure, bilingual mobile layout, exact same-case acknowledgement and late-response navigation guard |
| `uv run --group browser python scripts/browser_applicant_payments.py` | 4 scenario groups passed; no page errors | Payment read facts, processing/reconciliation, cumulative refund labels, Arabic mobile timestamp isolation, denied/malformed refresh clears old data, GET requests only |
| `uv run --group browser python scripts/browser_applicant_supplements.py` | 5 scenario groups passed; no page errors | Proposed contract fixtures only; immutable original answers, escaped attributed history, safe evidence review, EN/AR mobile, uncertain append lock, explicit refresh/new entry, navigation/unload guards and missing/disposed capability |
| `uv run --group browser python scripts/browser_applicant_decrees.py` | 4 scenario groups passed; no page errors | Proposed own release-list fixtures only; escaped decree reference, exact signed-file URL, EN/AR mobile, removed-release/denied/missing-contract refresh clears links, GET only. No actual release/revocation or signed-PDF acceptance. |
| `uv run --group browser python scripts/browser_applicant_requests.py` | 4 scenario groups passed; no page errors | Escaped own instructions/bound questions, EN/AR mobile, assessment report/release distinction, denied/staff-only/malformed refresh removes old content; GET only. No response, signature or disclosure acceptance. |
| `uv run --group browser python scripts/browser_applicant_assessments.py` | 5 scenario groups passed; no page errors | Explicit consent lost-ack recovery, evidence retention during refresh, pending discard blocked during upload, Arabic mobile layout and denied-refresh privacy/dirty guards. |
| `uv run --group browser python scripts/browser_applicant_next_batch.py` | 9 scenario groups passed; no page errors | Prepared intake response/review/navigation/unload/uncertain lock, actual-shaped pending history blocks fresh checkout/signature, proposed original-snapshot resume GET-only, capability-gated deletion/withdrawal confirmation and delayed-action parent filing lock; EN/AR mobile. |
| `CTM_APPLICANT_REQUEST_CLOSURE_AUDIT=1` real API diagnostic | Passed: never-sent draft excluded; sent closed request retained | Backend 480a246 preserves unsent draft privacy; previously sent closed requests remain readable. Sanitized `request-closure-privacy-result.json`; GitHub #2 regression resolved. Default suite includes this gate. Explicit 0 is baseline-only. |
| Backend archive `tests/test_returned_privacy.py tests/test_search_privacy.py -q` | 10 passed | Independently executed backend c16976c tests in isolated archive/settings_test SQLite; controlled search candidates/index suppression, private intermediate revisions, stale queued-job discard; mocked mail send never called |
| `uv run pytest tests/test_workflows.py tests/test_input_validation.py tests/test_row_security.py tests/test_shell.py -q` | 15 passed; 37 skipped | SQLite local regression; PostgreSQL-only checks skipped, not passed |
| `git apply --check docs/implementation/applicant/shell-integration.patch` | Passed | Clean base shared shell; governance must recheck when integrating |
| `git diff --check` | Passed | Whitespace validation |

Browser screenshots and raw result JSON are generated under ignored
`.tmp/applicant-browser/`; real CDN assets stay external. Arabic mobile and desktop
screenshots were inspected. Controls use documented Plenix components and locale
direction. No temporary Arabic CSS or unapproved typography tokens were invented.
Institutional Arabic typography acceptance remains separate from these layout checks.
The diagnostic platform-font check observes Segoe UI Semibold for the Arabic heading
on this Windows test machine. It is recorded without claiming approved font acceptance.
Both desktop/mobile EN/AR runs assert no runtime `[style]` or horizontal overflow.

Independent code review identified that the existing shell API helper discards
403/404 status. The proposed integration patch preserves it, and the isolated shell
browser test verifies editor write-lock behavior through that actual helper. Applying
the loading/navigation hooks without the helper fix would leave this finding open.
Review also caught a failed language-preference request unmounting the dirty editor
through the shell's global error view. The patch uses a separate, non-unmounting
preference error notice. Its browser regression failed before the fix and passes
with local answers retained after the synthetic 500 response.

Follow-up reviews caught and corrected these workflow interactions:

- Filing review must remain available when answer-edit permission is false.
- An uncertain upload invalidates document review and blocks filing until the
  authoritative list is refreshed, required originals are safe and review is explicit.
- Document refresh during a frozen submission retry must be disabled so it cannot
  invalidate review and strand the original idempotency key.
- A saved answer-version change must automatically refresh contextual requirements.

Each has browser regression coverage. Checkout and submission retries retain their
original signature/version; returned resubmission sends no new attestation/payment.

The real-API runner archives the exact backend ref into a fresh ignored temporary
directory, copies applicant assets and applies the proposed shell patch there. It
does not merge branches or modify backend/shared sources in this checkout. There
are no mocked HTTP API responses in this runner. Synthetic test-client sessions
do not verify provider sign-in. Existing HTTP APIs perform required document uploads,
an authorized administrator waiver, first submission/key replay, a completeness
return and resubmission without a new signature/fee. This uses the isolated
`settings_test` scanner bypass policy, not a live antivirus success claim. These
backend filing actions are exercised through real HTTP requests; the browser filing
controls now exercise actual file upload/list/download, review, declaration consent,
signature, waived submit and returned resubmit through the visible browser UI.
Corrected originals retain previous stored bytes and version identity while the
applicant old-version download is denied. Synthetic technical scan events prove
that a later pending result removes the current download and blocks checkout,
and a later clean result restores eligibility. These events are explicit isolated
test setup and do not represent live scanner execution.
Status refresh displays the real submitted state and allocated synthetic case number.
No live provider payment, antivirus, production database or deployment acceptance is claimed.

## Open dependencies

- VM-FRM: nested repeat validation,
  pending-checkout resume projection. Own current-file listing/capabilities and returned
  instructions now pass the isolated real-API integration runner at `6e89c22`.
- Governance/content: approved published bilingual applicant form definition,
  declarations and repeat-field contracts; apply shared shell hooks serially.
- Later acceptance: PostgreSQL lifecycle/races,
  provider payment and live antivirus acceptance. Real-API applicant draft/file
  isolation and waived filing/correction controls are covered in the isolated runner.

The full applicant workflow is not complete. PR #5 remains draft until these
dependencies and subsequent slices are implemented and reviewed.

## Returned-privacy regression now passing

The default real-API runner includes returned privacy. All13 pre-resubmission,
2 owner-access,5 pending-scan and5 post-resubmission predicates pass on backend `e2f714a`.
This replaces the formerly failing7/8 result on7684169. See
[acceptance reconciliation](acceptance-reconciliation.md) and
[sanitized JSON evidence](returned-privacy-result.json). Formal snapshots remain
available to council, pending corrections remain owner-only, and resubmission
publishes the corrected snapshot while preserving previous originals. Ten backend privacy/search pytest checks were independently executed in the isolated
archive, including controlled search and obsolete-job suppression. Live search/mail
integration and PostgreSQL RLS remain separate.

Browser unload regression uses a synthesized cancelable beforeunload event: clean
answers do not suppress the guard while an upload is in flight, and acknowledgement
removes it. Native browser dialog display depends on browser activation/policy and
is not claimed by this check. Existing checkout navigation is unchanged.

Appeal real-API checks use explicit closed/reopened case and linked-spouse state
fixtures. They verify entry, draft reuse, published form/new information, evidence,
authorized test waiver/declaration/submission without reopening, and separate own
appeal for a previously non-filing linked spouse in a reopened-sibling context.
They do not verify council acceptance, decree closure or identity onboarding.


## Five-task batch limits

The source question inventory contains 59 English wording entries and zero Arabic
wording entries; it is a reference snapshot, not proof of complete applicant form
content. `scripts/audit_applicant_forms.cjs` audits an exported bound application
projection and emits technical readiness with exact JSON pointers. Even a clean
result retains `institutional_approval:not_verified`. It never publishes wording.

The default real-API acceptance is currently NOT green because of unsent request
closure disclosure. Its 34 preceding scenario groups include real local release/
withdraw byte-route checks using a synthetic existing PDF; no signature, issuance,
provider checkout or approved consent is represented. The first closure-audit run
hit a transient Django migration registry TypeError; a fresh isolated retry reached
and reproduced the privacy assertion. The delayed-action UI regression first failed
with enabled Submit and passes after the persistent parent filing lock fix.

Local typing during read-only capability refresh is now preserved. A deliberately delayed projection read proves saves/filing stay blocked until it settles; server can_edit and action locks still govern editing/writes.


## Actual own decree release-list integration

Backend 444bad8 now supplies the previously missing release projection. The full
browser/API runner consumes it without HTTP mocks: own bilingual certificate row,
exact PDF action, Arabic390 mobile checks, linked spouse empty list/denied bytes,
withdrawal refresh removes links and retained full/range/preview/HEAD access fails.
The dedicated DEC fixture has stored synthetic bytes and a clean technical event;
actual decision approval/signing/issuance remain separate acceptance. 59 frontend
tests pass. The default API run reaches35 passing groups before the unchanged
unsent-request closure privacy assertion fails. Earlier batch counts/SHAs remain
historical evidence, not a green full-acceptance claim.
