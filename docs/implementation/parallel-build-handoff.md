# Parallel implementation boundaries

Use the application repository `LighthouseCollection/CTM`, not the historical
prototype in `ctm-alpha`. Each contributor needs an independent clone/branch.
Reconcile against the protected `docs/architecture/build-spec/` contracts.
Do not edit approved architecture files to make implementation checks pass.

## Codex integration owner

Microsoft authentication, account authorization, database migrations and access
policies, deployment configuration, integration and acceptance testing. Keep
provider credentials outside Git. Genuine Microsoft callback acceptance is still
pending user authentication; synthetic preview sessions are not provider tests.

## Applicant workflow contributor

Build applicant draft editing, question rendering, review, required attachments,
submission and returned-application correction screens using documented APIs.
Use Plenix CDN 0.58.0 components and tokens exclusively. Preserve EN/AR and RTL.
Do not introduce local passwords, change schema or invent payment-success states.
Coordinate changes to shared app.js with the integration owner before merging.
If API functionality is missing, document the exact required contract instead of
creating mock success responses in the application.

## Reports contributor

Build report request/question selection and response workflows from approved
question snapshots, preserving report authorship, visibility and history rules.
Use separate frontend modules where practical to avoid app.js merge conflicts.
Recording and OCR are explicitly low priority for this demo; labelled unavailable
placeholders are accepted. Do not claim an upload has been transcribed or OCR'd
when no processing occurred. Existing file privacy and scan checks still apply.

## Integration checks

Submit commits with a concise description and meaningful checks. No contributor
should deploy directly to the operational VM, alter shared credentials or run
operational migrations independently. The integration owner reviews and runs
PostgreSQL CI and browser checks after combining changes. No real charges or
outbound case emails are part of synthetic acceptance testing.
