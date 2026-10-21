# CTM settings and translation architecture

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Authority: user request, 2026-10-20. Architecture specification only; no live settings page, API connection, keys, translation engine or translated bank was installed. [Exact supplied master prompt](CTM-translation-master-prompt.txt) is retained byte-for-byte as the initial editable prompt version.

## Prototype settings inventory — source inspection

| Prototype evidence | Observed sections | Architecture treatment |
|---|---|---|
| ctm-admin/admin-management.html:190–194 | Users & Roles, Tribunal Config, Data & Records, Audit & Security | System-level settings; add Translation & Language Services as a settings area, not a case operation. |
| ctm-admin/admin-management.html:317–408 | Diocese settings, canonical reasons, workflow stages, decision outcomes, document templates | Reconcile with confirmed numbering, grounds, workflows and versioned template management. Prototype editable case-prefix control does not override confirmed case-number rules. |
| ctm-admin/admin-management.html:476–502 | Export Cases, Purge | Excluded from production specification: no case export and no deletion of submitted cases. |
| ctm-admin/admin-management.html:529–608 | System audit, active sessions, login history, mobile settings | System scope; prototype localStorage mobile flags are presentation state, not server authorization. |
| ctm-admin/admin-user-account.html:124–258 | Profile, Security, Tribunal Role, Notifications, Activity Log | Own-account settings. Role is informational; users do not grant themselves roles. Own activity is not system audit access. |
| ctm-admin/admin-user-account.html:185–190 | Session timeout selector | Exclude inactivity timeout, following the user's prior decision. |
| ctm-admin/admin-user-account.html:238–248 | Email/SMS notification controls | Portal/email are confirmed channels; prototype SMS is not automatically adopted. Preferences cannot reroute assigned-case notifications to admin/secretary or expose other parties. |
| ctm-public/public-petition.html:35–36; public-signin.html | Account creation and sign-in | No dedicated applicant-settings page was found in the inspected public HTML filenames/content. Specify verified-email change, password/linked sign-in management and English/Arabic notification preference using confirmed account rules. |

These are source findings, not a rendered-browser audit. Original HTML remains unchanged.

## System settings versus account settings

Admin system settings contain integration credentials, translation routing, provider priority, prompt editing/version history, engine health and controlled test connection, plus existing system-level functions. An authorized admin manages secrets and integration settings. Shared content publishing by admin/secretary remains as separately confirmed; secretary status alone does not expose API keys. No applicant or ordinary council account can read provider secrets or change the master prompt. All settings changes record actual actor/time and old/new nonsecret configuration versions. Redact secrets from audit.

Account settings contain the current user's profile/contact details, verified email change, authentication settings and allowed language/notification preferences. Password changes apply to password identities; applicant Google/Apple linking follows the existing verified-account policy. Council accounts remain email/password. Account changes do not silently rewrite submitted application answers, identifiers or signed records. Portal ownership and account suspension checks remain server-enforced.

## Translation master prompt

Use the supplied master prompt for all AI translation jobs: question-bank wording, selected intake questions, templates/declarations, configured messages and notifications, report text and transcripts, and any document translation authorized for that content. Treat this as a translation instruction template, not an executable OCR script. Preserve its wording unchanged initially, including Coptic/Greek, name/number preservation, completeness and uncertainty instructions.

System settings provide a master-prompt editor with save/publish, immutable version history and the ability to publish a prior version as a new current version. Each job references the exact published prompt/version. Prompt edits affect future jobs only; never retroactively alter an issued certificate, sent request, original statement or existing translation. Retain the task block separately as structured job parameters, filling source/target language, output register, input type, terminology and allowed source. Source content is untrusted text, never settings instructions.

The prompt supports English, Egyptian Arabic, formal Arabic, Arabizi input, and Coptic/Greek preservation as described. This does not automatically add more portal interface languages. English/Arabic content versions remain versioned. Target Arabic register is an explicit translation-job setting; keep Egyptian and formal Arabic separate. Do not infer a default register from this document. Batch jobs use the prompt's mark-and-continue policy. Do not invent missing pages or silently truncate long content.

## Two AI providers with ordered failover

Provide two configurable provider slots: primary (priority 1) and fallback (priority 2). Each includes enabled state, provider/adapter identity, server-side endpoint if applicable, selected model and supported capabilities, secret reference/API key, timeout and bounded retry policy. No provider or model is selected by this design.

Store keys in server-side secret storage or encrypted credentials with key material kept outside the database. Browser fields are masked/write-only with configured/not-configured status and explicit replace/remove actions. Never return existing full keys to a client, export them with settings, embed them in HTML/localStorage, or place them in logs. A connection test uses non-sensitive sample text, never case documents by default. Endpoint configuration must not permit arbitrary access to server-internal services.

In AI mode, try primary then eligible fallback for supported transient/provider failures after bounded retries. Unsupported capability, invalid configuration and authentication errors produce explicit provider status; eligible fallback may proceed if configured and allowed. Permission denial, missing medical release, locally restricted content and invalid source are not provider failures and must not trigger an external send. Do not silently treat incomplete/truncated output as successful. Keep each attempt separate, bind the accepted result to one completed attempt, and retain provider/model, timing and failure provenance without raw sensitive log text. Avoid duplicate notifications or publication on retry.

If both fail, mark the job failed/retryable as appropriate, preserve source and partial attempts as incomplete, and allow an authorized retry. Never substitute a summary or publish partial text as complete. Failover uses the same source version, task parameters and prompt version. Do not merge one provider's partial translation with another provider's output without explicit job-level segment provenance.

## Non-AI on-host engine option

Settings support an alternative **Local translation engine** execution mode; the actual non-AI engine, supported languages/registers and adapter are to be defined later. Local mode cannot be enabled as operational until an engine is configured and its capabilities are verified. No engine name or quality claim is invented.

A non-AI engine cannot be assumed to execute natural-language master prompts. Its adapter must expose supported terminology/preservation controls, report unsupported requirements and retain engine/version provenance. Do not label its output as fully prompt-compliant merely because the prompt is saved in settings. Preserve the same source/result versioning and review workflow. No automatic external fallback from local mode: failed local jobs remain local unless an explicitly authorized routing change permits external processing for that content.

## OCR, medical restrictions and transcript boundaries

All document OCR/extraction remains on the CTM server. The master prompt's references to OCR do not authorize uploading original PDFs/images to external AI or replacing the local OCR pipeline. For externally permitted text translation, send only authorized extracted text, not original files. Medical documents and their extracted contents remain local-only under existing policy; an AI fallback cannot bypass that rule. A local non-AI engine may handle them only within the signed release/purpose scope and actual engine capabilities; otherwise record local-processing unavailable, without external transmission.

Audio transcription retains its independently approved local/API workflow and original recording. Apply this prompt to translation of resulting text, not as a substitute for a speech-recognition engine or clinical analysis. Existing transcript review, bilingual/mixed-language outputs, source preservation and revision history remain. Prompt configuration cannot grant case access or expand release permissions.

## Question bank and template publication

Generate translation drafts against an exact source question/template version and stable IDs. Keep original source text, proposed translation, provider/engine/prompt version and review state separately. Existing system-level shared-content publishers review and publish English/Arabic versions; provider success alone is not approval. Preserve earlier published versions and exact already-sent intake wording. Unsent drafts keep saved questions unless the case manager explicitly refreshes them. Translation never changes CTM IDs, case numbers, amounts, source answers or findings.

## Proposed data relationships

| Record / extension | Contents and constraints |
|---|---|
| system_setting_versions | typed integration/routing policy, actor/time and active version; secrets referenced, not serialized into normal settings |
| account_preferences | account-owned language/register preference where offered and permitted notification options; cannot set system credentials or role |
| translation_prompt_versions | immutable exact master prompt text/digest, author/publisher/time, published/current status |
| translation_provider_configs | two ordered AI slots, endpoint/adapter/model/capabilities, enabled state, timeouts/retries, credential reference, config version |
| translation_engine_configs | mode and on-host non-AI adapter/version/capabilities; unavailable until configured |
| integration_secret_refs | server-side secret locator, rotation metadata and masked status; no client plaintext retrieval |
| translation_jobs | exact source object/version, source/target language and register, task-block parameters, routing/privacy scope, prompt/config versions, status |
| translation_attempts | job, provider/engine/model, segment/continuation provenance, timing, failure code and completeness; no secret or sensitive raw-log content |
| translation_outputs / revisions | original source linkage, draft/result text, language/register, attempt provenance, review/publishing actor/time and history |
| integration_test_events | authorized admin, configured integration version, non-sensitive sample, redacted outcome and time |

Settings versioning does not duplicate case access. Read authorization applies to source text, derived translations, queues, search, downloads and diagnostics. No migration, provider SDK, deployed endpoint or real-key test was executed.


## Arabic user interface — confirmed 2026-10-20

The user explicitly extends the same translation service and editable master prompt to Arabic localization of both applicant and council interfaces. This adds English/Arabic interface-language selection, not just questionnaire or notification translation. UI preference is an account preference and remains distinct from notification language, source-answer language and a report translation target. Language selection must also be available on public/sign-in screens before authentication, then honor the saved account preference after sign-in.

Translate versioned resource keys for navigation, headings, buttons, field labels, validation and error messages, statuses, instructions, dialogs and accessibility labels. Generate drafts through the configured translation route and prompt version, review and publish bilingual resource bundles through system-level content management. UI pages read published resources locally; they do not call AI on page load or send current case data for label translation. Missing or failed translations use the available English resource rather than displaying an empty control or fabricated text.

Preserve interpolation variables, plural rules, HTML safety, route/API identifiers and stable status values. Never translate executable code, keys, user identifiers, case numbers, filenames, monetary values or original user answers as part of UI-label localization. Supplied source text and runtime variables remain separate; render escaped data, not provider-generated executable markup. Publish resource version, source/prompt/provider provenance and reviewer history; updating interface wording does not rewrite case records or sent messages.

Arabic mode uses right-to-left page flow and bidirectional handling of mixed Arabic/English text, with readable Latin case numbers, dates, email addresses, names and file codes. Use the Plenix design system's supported localization/layout capabilities when implementation begins, verifying support then. Interface controls may mirror where appropriate; media playback and content-specific direction must retain their intended meaning. No conversion of identifiers or stored timestamps follows merely from choosing Arabic. Exact Arabic register/terminology for UI resources is configured and reviewed without inventing a default in this design.

Proposed records: ui_message_keys (stable key/context and source version), ui_translation_versions (locale/register/text, placeholders, job/output and review/publication provenance), ui_resource_bundle_versions (published immutable resource set and rollback history), and account_preferences.ui_language. Public pre-login choice is presentation-only and grants no access. Interface language and rights are independent; all existing case privacy, release scope and council/applicant authorization applies in either language. No new application UI or actual Arabic resource bundle has been built in this documentation step.


## Temporary Arabic styling patch — 2026-10-20

See [Arabic styling bridge](CTM-arabic-styling-bridge.md). The separate Arabic-scoped CSS is now linked in 49 prototype pages and can be replaced independently when the Plenix Arabic CDN exists. No locale controller or translated resources have been installed. All Arabic UI text follows familiar Egyptian wording/formal-common context as specified by the user; no blanket formal-only default.


## Required package capability: council Microsoft sign-in — 2026-10-20

User confirmed inclusion of Microsoft sign-in in the delivery package. [Council Microsoft sign-in](CTM-microsoft-council-sign-in.md) supersedes the earlier council email/password-only restriction by adding organizational Microsoft authentication. Admin preauthorizes the CTM member and role; a Microsoft/lacopts email alone never grants access. Provider configuration belongs to admin system settings, identity links use validated tenant/object identity, and applicant/external-priest authentication remains separate. This is specified, not deployed; actual tenant/app registration, credentials and callback configuration are required before a live connection.
