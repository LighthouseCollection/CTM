# CTM shared and personal template management

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

Confirmed by the user, 2026-10-20. Architecture documentation only; no application, database or migration was built.

## System-level shared library

Admin or secretary manages and publishes shared templates, shared questions and their English/Arabic versions. This is a system-level permission, not a grant to operate on assigned cases. Version question wording, translation, category membership and template selection/order. Topic groups and question categories reuse stable question identities; publishing does not overwrite earlier versions.

Retiring a shared question or template preserves historical definitions, submissions and references. Retired material is unavailable for new intake requests. The existing rule for a previously saved unsent draft remains: do not silently rewrite it on retirement or publication; retain its saved content until the case manager explicitly refreshes it. This does not make retired material selectable from the current library.

## Case-manager template use

The assigned case manager selects templates and questions for their case, can add case-specific questions, and may save selections as a personal reusable template. Personal templates are owned by that case manager and do not become shared automatically. Reuse question content and ordering, never applicant answers, case attachments, recordings, medical material, findings or private case facts. Case-specific content must not be silently propagated to a shared library.

A case manager can submit a personal template to admin or secretary for publication in the shared library. The system-level publisher reviews and publishes a separate shared template/version. The personal original is retained. Publishing does not convert ownership of the personal original or change it automatically. This approval is for shared content, not case findings or report acceptance.

## Draft and sent intake preservation

An unsent intake draft retains its existing questions when a source template changes. Refreshing is an explicit case-manager action before sending. Preserve entered work and review any affected question associations; do not silently discard answers or turn a template refresh into an applicant response change.

When sent, preserve the exact selected/custom question wording and order. Later shared/personal template publication, retirement or refresh cannot change sent requests. Conditional guidance remains linked to the question bank as already specified; unused helper text is not added to the sent-question snapshot. Additional questions after sending use a new linked follow-up intake.

## Closed-case report rule

After case closure, reports cannot be edited, including clerical corrections. This supersedes any earlier general report-author editing permission where it could be read as extending beyond case closure. Open-case report revisions preserve original authorship, actual editing actor, time and prior versions. New substantive material follows the established appeal process. Reopening does not unlock the original closed proceeding or its reports; new material belongs to the new authorized proceeding.

## Proposed data relationships and permissions

| Proposed record / extension | Required behavior |
|---|---|
| shared_question_versions | stable question identity, immutable wording/language versions, publication actor/time, retirement state; exact earlier versions retained |
| shared_template_versions | stable template identity, immutable publication versions, system publisher and time, retirement state |
| template_question_memberships | template version, question version or explicitly stored custom wording, category/group and order; no response or case-file copying |
| personal_templates / versions | owner case-manager account, saved question selection/order and versions; separate from shared publication |
| template_publication_submissions | personal source version, submitting member/time, reviewing admin/secretary, publication outcome and shared version reference; personal original retained |
| intake_draft_template_links | chosen template version and saved question content, explicit refresh actor/time; source updates do not mutate draft content |
| sent_intake_question_snapshots | request, stable source reference where applicable, exact sent wording/language/order; immutable after send |

Reuse existing signatures, audit and versioning mechanisms where applicable. System publishing cannot modify sent intakes, submitted answers or closed reports. A case-manager role alone cannot publish changes to the shared library. A shared-library publishing role alone cannot edit an assigned case's reports. No new application workflow or production UI was created by these documentation updates.


## Settings and translation authority — 2026-10-20

[Settings and translation architecture](CTM-settings-translation-architecture.md) records inspected prototype system/account settings and the newly requested translation configuration: exact editable/versioned Coptic Orthodox master prompt, primary/fallback AI slots, protected server-side API keys, and a future non-AI on-host engine mode. All translation outputs retain source/version provenance. Local OCR and medical-content restrictions override any provider fallback; prompt OCR instructions do not authorize external document uploads. Account settings cannot change system integrations. Shared question translations are reviewed/versioned before publishing. This specifies architecture only; no live integration or translated question bank was built.
