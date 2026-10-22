# Backend priority ledger

User priority: priest workflows first, remaining settings consumers second.
The older governance deferral of OCR/audio does not override that direction.
Backend owns issue2; council owns its UI; governance owns integration/operational
migrations; independent QA accepts the exact integrated successor SHA.

## Completed backend contracts

- Link issue/reissue/cancel, draft preservation, scoped browser entry, status and
  minimal completion receipt, council link lifecycle metadata.
- Paper-completion API through0049: clean current request-bound council PDF,
  actual recorder/received date, explicit completion, retained original and
  idempotent recovery. Upload/scan alone does not complete a request.
- Blank council request print view and direct downloadable PDF using stored
  wording. Council UI integration and content acceptance remain pending; see
  priest-request-pdf.md.
- Existing report/appointment recording association, finalization, processing
  state and exact-transcript review contracts. These do not yet establish a
  complete external-priest recording journey.

## Unfinished implementation, in priority order

1. External-priest recording journey: connect original capture/upload to the
   appropriate request/report lifecycle; preserve notice, original media,
   scan, source association, designated reviewer and exact-version approval.
   `deliver()` currently rejects transcription jobs as provider unconfigured;
   recording finalization is not successful transcription.
2. Printable request: council link/download integration and approved-content
   acceptance. Browser print and direct generated PDF are implemented.
3. Wrong-upload correction: narrow exception to remove the wrong original and
   its derivatives while preserving correction evidence; coordinate retained
   source and capability state with council. No universal deletion endpoint.
4. Paper OCR integration: local extractor exists, with integrity/scan checks,
   native PDF first and eng+ara fallback. Request/worker orchestration, status,
   retriable failures, council presentation and derivative-review boundary are
   unfinished. Standalone extraction is not integrated OCR acceptance.
5. Actual email invitations: `send_request()` returns a random capability once,
   stores its digest and expires it after30days; no invitation is enqueued.
   Implement protected recoverable delivery, current-link source evidence,
   stale/reissued/cancelled suppression and truthful provider acknowledgement.
   Do not put plaintext capabilities into general audit or queue projections.
6. Settings allocation: B-S1 issue24 assigns tribunal_contact and
   recommended_doctors consumers exclusively to Desktop-R on a separate branch.
   Translation prompt/routing and broader configured email kinds remain
   unassigned by that order. Existing consumers are account status email
   templates and filing document labels; storage alone is not runtime activation.

These are backend implementation gaps, not all credential blockers.

## Blocked operational acceptance: exact dependencies

- Actual invitation delivery: completed invitation implementation, then
  operator-provided/configured SMTP transport, sender authority and a controlled
  recipient for observed delivery. Provider acknowledgement is not inbox receipt.
- Transcription: completed adapter and authorized provider/model/secret binding,
  followed by an observed processing run; no fake transcript success.
- OCR: worker orchestration and installed local PDF/OCR engines plus English and
  Arabic language data in the accepted runtime. No cloud OCR credential is
  required by the existing local extractor.
- Combined workflows: council integration, governance-selected successor commit
  and test-server migration (if needed), then independent QA against that SHA.

This ledger does not claim that credentials are absent from the live server:
their configuration and operational acceptance are outside this checkout.
Nothing here authorizes backend to merge, deploy or run shared-server migrations.

## Additional user account scope

User explicitly added member creation/editing. The next delivered member slice
provides admin-only explicit tribunal enrollment and versioned display-name
edits; see member-administration.md. Broader contact/portrait, verified email,
provider, role-change and user self-profile workflows remain unfinished. This
addition does not claim the priest or remaining settings priorities completed.
