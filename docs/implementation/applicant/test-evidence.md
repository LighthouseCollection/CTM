# Desktop-R applicant workflow evidence

Validation performed 2026-10-21 against base `6928c484aeafd580434db794bcdcf4b95052bab2`.
All records are synthetic. No operational data, external payment, provider sign-in,
deployment or production-readiness acceptance is represented by these checks.

| Check | Result | Scope |
| --- | --- | --- |
| `node --test tests/frontend/*.test.cjs` | 28 passed | Bound definitions, repeat stable IDs/opaque fields, incomplete save, optimistic versions, errors/permission lock, boolean false/unanswered, conditional retention, start/reuse, filing eligibility, immutable signature/idempotency retry, private download paths, context replacement, size gates, malformed current-file projection |
| `uv run --group browser python scripts/browser_applicant.py` | 16 scenario groups passed; no page errors | Real Plenix 0.58.0 CDN, synthetic API; escaped review, save, language/RTL, unsaved guards, declaration/fee/signature layout, waived filing, read-only returned resubmission, unsafe checkout, uncertain upload/readiness, boolean conditional save, automatic checklist/capability refresh, repeat add/correct/review/remove in RTL |
| `uv run --group browser python scripts/browser_applicant_shell.py` | 8 scenario groups passed; no page errors | Proposed shell patch applied only to temporary copies; actual helper, sidebar/back, preference success/failure, 403/404 lock, multipart boundary/context/replacement, pending-scan links, Arabic layout, start/reuse/eligibility error |
| `uv run --group browser python scripts/browser_applicant_api.py` | 6 scenario groups passed; no page errors | Real Django APIs against backend `07c35ededfcae1c58a4700eb239b7b50be92bc2c`, isolated SQLite/synthetic accounts; start/form/save/preferences, stale conflict and retained history, outsider/council draft denial, actual missing-file-route blocker |
| `uv run pytest tests/test_workflows.py tests/test_input_validation.py tests/test_row_security.py tests/test_shell.py -q` | 15 passed; 37 skipped | SQLite local regression; PostgreSQL-only checks skipped, not passed |
| `git apply --check docs/implementation/applicant/shell-integration.patch` | Passed | Clean base shared shell; governance must recheck when integrating |
| `git diff --check` | Passed | Whitespace validation |

Browser screenshots and raw result JSON are generated under ignored
`.tmp/applicant-browser/`; real CDN assets stay external. Arabic mobile and desktop
screenshots were inspected. Controls use documented Plenix components and locale
direction. No temporary Arabic CSS or unapproved typography tokens were invented.
Institutional Arabic typography acceptance remains separate from these layout checks.
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
do not verify provider sign-in. The file-list endpoint currently returns 404 there;
the frontend displays unavailable access and keeps filing disabled. No live payment,
antivirus, production database or deployment acceptance is claimed.

## Open dependencies

- VM-FRM: bound questionnaire projection, authoritative `can_edit`, own draft-file
  listing, returned instructions/action eligibility, submission/checklist projection.
- Governance/content: approved published bilingual applicant form definition,
  declarations and repeat-field contracts; apply shared shell hooks serially.
- Later acceptance: connect implemented frontend upload/scan/declaration/payment/
  submission/returned controls to agreed real projections; prove real-API applicant
  isolation, PostgreSQL lifecycle/races, provider payment and required-file safety.

The full applicant workflow is not complete. PR #5 remains draft until these
dependencies and subsequent slices are implemented and reviewed.
