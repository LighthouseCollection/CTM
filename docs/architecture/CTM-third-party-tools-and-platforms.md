# CTM third-party tools and application foundation shortlist

> Current consolidated technology reference: [CTM stack register](CTM-technology-and-open-source-stack.md). Earlier comparisons below are research history; later register qualifications take precedence.

Research date: 2026-10-20. Recommendations for evaluation, not accepted architecture changes, installed software or a security certification. Existing PostgreSQL/data/permission requirements remain authoritative until a platform is selected. No platform replaces CTM-specific privacy and lifecycle rules automatically.

## Application foundation

Preferred fit to current architecture: Django + PostgreSQL with Plenix-rendered CTM portals. Django is a framework, not an off-the-shelf tribunal platform. Reuses database/migration/form/session/localization machinery while CTM supplies case logic, fine-grained authorization and immutable histories. django-allauth lists Microsoft, Google and Apple providers; configure provider-only access, disable local password routes, preserve admin-only council membership and no automatic account linking by an untrusted email.

Most relevant higher-level platform candidate: Frappe Framework, MIT licensed. DocTypes, permissions, file handling and generated APIs can reduce generic application work. Build a separate Plenix-facing interface through controlled server methods/APIs rather than assuming Frappe Desk can be restyled by adding a CDN. Generic CRUD endpoints must not bypass CTM invariants. Frappe's current development documentation is inconsistent about PostgreSQL maturity: prerequisites lists support, database administration describes PostgreSQL as experimental. Select a release and verify PostgreSQL migrations, transactions and all intended apps before adoption; do not equate ERPNext app compatibility with base-framework compatibility. A MariaDB decision would reopen the confirmed PostgreSQL choice and requires explicit approval.

Directus is technically relevant for database-backed APIs, files and access policies. Its official current overview identifies MSCL licensing, not an unrestricted MIT-style open-source proposition. Confirm current release licensing, SSO and permission entitlement before considering it. No pricing or nonprofit eligibility is assumed. Not the leading recommendation for this request for a fully open-source base.

No candidate comes with CTM appeals, one-open-case enforcement, private spouse submissions, report invitations, release restrictions, decrees or provider-only account enrollment ready and verified. A foundation reduces reusable infrastructure work; it does not remove custom CTM domain work.

## Component shortlist

| Need | Candidate | CTM evaluation requirement |
|---|---|---|
| Microphone recording | Uppy Audio | Desktop/mobile microphone capture; report-wide audio. Integrate Plenix UI without assuming library UI styles comply automatically. Test pause/resume, supported codecs, permissions, device sleep and iOS interruptions. |
| Resumable file transfer | Uppy Tus plus compatible self-hosted tus server | Transport restart support is not recovery of an unfinished live recording. Persist captured audio portions with sequence/provenance; test capture recovery separately. No Transloadit hosted processing is required. |
| Scanned PDF OCR | OCRmyPDF + Tesseract eng/ara | Local worker. Install Arabic explicitly; do not assume default container contains it. Keep original bytes unchanged, produce a derivative and extracted text. Test Arabic certificates, stamps, mixed scripts and page layouts; handwriting/Coptic accuracy is unproven. |
| Born-digital PDF/Word text | Apache Tika | Local extraction complements OCR; file parsing isolated with resource limits. Do not OCR every Word document or confuse a PDF viewer with OCR. |
| Search default candidate | Meilisearch | Arabic tokenizer/normalization documented. Test Arabic names, spelling variants, English/Arabic mixed queries, exact case IDs and typo behavior. Private index; CTM-authorized filtering before hits/snippets/facets/counts; permissions remain authoritative in CTM. |
| Search alternative | OpenSearch | Explicit Arabic analyzer/normalization/stemming with more configurable analysis; additional operational complexity. Evaluate if linguistic/search requirements exceed simpler option. |
| Local transcription candidate | whisper.cpp | Local speech-to-text candidate, independent from recorder and OCR. CPU/RAM/model and mixed Arabic/English quality must be benchmarked. Reliable council/applicant speaker attribution and Arabic translation are separate requirements, not assumed bundled features. |
| Provider authentication in Django | django-allauth | Microsoft/Google/Apple provider adapters, restricted tenant/enrollment and provider-only routes. CTM owns permissions and account status, not user passwords. |

Keep source files in private managed storage behind CTM authorization; PostgreSQL stores identities, metadata, associations and histories. OCR/search are derived local data, not alternative authoritative case databases. Original file access, derivative text, medical scopes and every historical version need the same security policy. Search rebuilds cannot index private drafts, unreleased transcripts or unauthorized medical text merely because a worker can read a folder.

## Decision before commitment

Compare Django and Frappe on one representative CTM scenario in an isolated evaluation: applicant A/B isolation; admin-created Microsoft member plus Google/Apple applicant; no password fallback; immutable submitted intake/follow-up; authorized report attachment; local bilingual OCR and permission-safe search. No real case records. Measure release-specific database support, code/customization cost, update compatibility and Plenix UI separation. This is the recommended next evaluation, not an already executed test.

## Primary sources

- Django overview: https://docs.djangoproject.com/en/5.2/intro/overview/
- django-allauth providers: https://docs.allauth.org/en/latest/socialaccount/providers/index.html
- Frappe overview: https://docs.frappe.io/framework/user/en/basics
- Frappe API/files: https://docs.frappe.io/framework/user/en/api/rest
- Frappe license: https://github.com/frappe/frappe/blob/develop/LICENSE
- Frappe PostgreSQL prerequisites: https://docs.frappe.io/framework-git/getting-started/prerequisites
- Frappe database-administration caveat: https://docs.frappe.io/framework-git/administration/database-administration
- Directus/current licensing: https://directus.com/docs/getting-started/overview
- Uppy Audio: https://uppy.io/docs/audio/
- Uppy Tus: https://uppy.io/docs/tus/
- OCR language packs: https://ocrmypdf.readthedocs.io/en/latest/languages.html
- Tika: https://tika.apache.org/
- Meilisearch Arabic normalization: https://github.com/meilisearch/charabia/blob/main/charabia/README.md
- OpenSearch Arabic analyzer: https://docs.opensearch.org/latest/analyzers/language-analyzers/arabic/
- whisper.cpp: https://github.com/ggml-org/whisper.cpp


## Plenix search decision supplied by user — 2026-10-20

The user provided the prior Plenix Universal Search decision dated June 5, 2026: Meilisearch selected as the primary backend search engine; Typesense acceptable alternative; OpenSearch and Elasticsearch considered but not selected. This is user-supplied project authority, not independently retrieved historical evidence or verification of a running deployment.

Plenix Advanced Search is a separate UI component within the main workspace container, not a replacement engine and not dependent on Quick Search. CTM should align its recommended search integration with Meilisearch rather than reopen the Plenix selection. The Plenix CDN supplies presentation, not the search server or credentials.

Sharing a product choice does not establish that CTM may share an existing running instance. Inventory the existing service/version, capacity, access policy, backup and network configuration first. If shared hosting is suitable, CTM requires dedicated indexes and scoped server-side access, with no Plenix-wide key or cross-program search exposing tribunal records. Alternatively deploy a dedicated Meilisearch instance for CTM. Do not let a unified search UI bypass applicant/council permissions, medical-release scope, draft privacy or reviewed-transcript restrictions. All hits, snippets, facets and counts must respect the authorized search scope.


## Aligned Plenix processing stack and added evidence components — 2026-10-20

User requests inclusion of audio recording, image viewing and video playback. Reuse Plenix document tool choices: PaddleOCR for images/screenshots; OCRmyPDF + Tesseract for scanned PDFs; Docling as primary structural parser; Unstructured complementary; Meilisearch search. Route per document rather than run every tool on every file. Apache Tika is no longer a default requirement; retain only as a candidate if format testing reveals a real gap. Plenix AI summaries/classification/smart naming are not automatically adopted for CTM.

| Added component | Candidate | Integration boundary |
|---|---|---|
| Audio recording | Uppy Audio, with Tus resumable upload transport | Whole-report browser microphone capture; self-hosted uploads. Capture interruption recovery/pause/resume must be validated separately; no claim that upload resumption alone recovers unfinished audio. Transcription starts after finished recording submission. |
| Image evidence viewer | PhotoSwipe | Zoomable touch-friendly image dialog. It is not the inline report split-view itself; use a normal authorized preview there and open the viewer for enlargement. Explicit fullscreen/rotation needs version/plugin evaluation, not assumed defaults. |
| Video evidence player | Video.js | Playback within CTM's evidence panel; Plenix controls/styles adapter, selected release and browser codec validation. No public video host required. |
| PDF evidence viewer | PDF.js | View authorized PDFs and generated derivatives; no claim that PDF viewing performs OCR. |
| Audio evidence playback | Browser audio element initially | Plenix-styled player controls; add a waveform/timestamp library only if required later. Recording and playback remain distinct. |

These are browser libraries integrated into CTM, not separate file-storage applications or automatically separate containers. Serve evidence through authorized endpoints, including seek/range requests; preserve original files and audit meaningful view/download access without treating every media range request as a separate human view. Any preview/transcoded playback copy retains original-version provenance and permissions. Do not expose permanent public file URLs, introduce applicant access to council testimony, mirror media timelines for RTL, or change evidence while generating previews.

Official references: https://uppy.io/docs/audio/ ; https://uppy.io/docs/tus/ ; https://photoswipe.com/ ; https://videojs.org/ ; https://mozilla.github.io/pdf.js/ . Versions and actual Plenix adapter compatibility require evaluation before production installation. No library or real recording/media pipeline was installed by this documentation update.


## Consolidated technology register — 2026-10-20

[Technology, open-source tools and deployment plan](CTM-technology-and-open-source-stack.md) is the current consolidated reference for Django/Rails/Frappe comparison, performance considerations, the Plenix-aligned processing/search stack, browser recorder/viewers, private storage responsibilities, container/service reuse and unresolved technical choices. It distinguishes agreed requirements, reuse baseline, candidates and external services. No application framework or pinned tool version is selected by documenting this register. No installation or performance benchmark has been run.
