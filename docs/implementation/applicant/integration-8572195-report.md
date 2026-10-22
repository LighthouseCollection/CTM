# Applicant verification of governance successor 8572195

The exact unmodified integration commit 8572195b45bbd5e5b533fc80ae3e03c222602327 passes 76 applicant actual-Django API/browser groups with no page errors. No applicant asset or shell overlay was applied. The test runner came from applicant checkpoint 1d20bfa; its exact hash and the pinned integration ref are recorded in [result JSON](integration-8572195-result.json).

This isolated SQLite run covers applicant draft/save/history, private access, document contexts, filing/payment recovery, linked first petitions, appointments, requests, supplements and messaging/notifications. Synthetic accounts/content, fixture waiver and scanner test policy remain in use. It does not establish approved institutional content, PostgreSQL RLS or live payment/email/antivirus acceptance.

The first fresh archive failed during Django migrate with `TypeError: 'Options' object is not iterable`, before browser checks. A second fresh archive passed unchanged. Cause is unverified; the failed launch is retained in the result rather than called successful or attributed to a product defect.

## What changed in the baseline

Governance now includes applicant fcce7c1, backend ff85717, council 87f094f and UI 554dcf6, per its pinned QA-successor-S10-C02 handoff. It preserves shared report-version fixes and includes the linked-petition hook. Latest applicant row-local conditions at 1d20bfa are not included; backend db82099 is also newer than the integrated backend. Coordinate these updates with governance; this verification edits no shared implementation.

## Remaining dependencies

- Governance: serial integration of latest published applicant/backend heads, then independent QA against its exact successor SHA.
- Infrastructure/operator: governance confirmed the owned stuck applicant PostgreSQL container has three uninterruptible D-state children and needs coordinated Docker Linux VM recovery. No engine restart or replacement container was attempted here. This is no longer merely an unanswered cleanup-ownership request.
- Backend: published db82099 defines hidden/nonexistent draft-history404 with identical bodies, and explicit visible permission denials403. The historical strict403 run remains failed. A fresh PostgreSQL acceptance run must use this documented contract after environment recovery; SQLite results do not establish this RLS behavior.
- Institution/configuration owners: reviewed versioned full EN/AR questions, choices/help/branches/requiredness/declarations and exact Arabic civil certificate wording.
- Backend/institution owners: normalized semantic/answer-state reconciliation and guarded migration acceptance. Live-service credentials and acceptance remain separately outstanding.

No merge, deployment, operational migration, shared-source edit or Docker recovery action was performed. Full applicant stream acceptance remains open.
