# Applicant workflow implementation slice

Implements issue #1 under governance #4 and the approved build-spec. This document
records implementation boundaries, not replacement product or questionnaire approval.

## First usable slice

`static/ctm/applicant.js` exports `window.CTMApplicant.ApplicationEditor` accepting
`applicationId`, the existing CSRF-aware `api` function, `lang` (`en`/`ar`) and
`onBack`. Governance loads the module before `app.js` and owns navigation wiring.
The editor fetches only the selected application's authorized projection. Published
questionnaire wording and stable answer codes come from its bound server version;
missing wording or unsupported definitions block editing rather than invent content.
The council interview bank is not a substitute applicant questionnaire.

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
This proposal must be reconciled with the backend owner's response before claiming
API integration complete. Draft save already accepts `{answers, expected_version}`.
No migrations, backend edits, shared shell edits or protected build-spec changes.

Required uploads, approved declaration, genuine fee/waiver state, submission and
returned correction actions follow as their projections/contracts become available.
No payment completion is inferred from checkout or browser navigation. No local
passwords, invented declaration, waiver request or fabricated external processing.

## Validation

Behavior tests cover question-definition rejection, stable keys, partial draft save,
preservation of unknown fields, optimistic versions, stale/error recovery and language
switching without losing input. Real pinned-CDN browser checks cover accessible
labels, review/save, EN/AR RTL, runtime `[style]` and horizontal overflow. Synthetic
API/CDN UI checks do not establish production identity or PostgreSQL readiness.
