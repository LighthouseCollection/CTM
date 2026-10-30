# CTM technology, open-source tools and deployment plan

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

Consolidated: 2026-10-20. Scope: document framework evaluation, document/media tools, storage, deployment, performance and remaining technical choices. Django with Plenix React CDN is selected; it has not been installed or integrated. This is the current consolidated technology register; earlier shortlist discussions remain research history. Business authority is [current access/workflow corrections](CTM-current-access-workflow-corrections.md) and the confirmed workflow documents.

## 1. Status and decision boundaries

- **Confirmed:** PostgreSQL; Plenix presentation; Linux CTM VM; one deployment package with multiple containers; provider-managed sign-in without CTM passwords; server-side document processing; private original storage; English/Arabic; signed disclosure restrictions.
- **Reuse baseline:** align with the user's Plenix tool selections: Meilisearch, PaddleOCR, OCRmyPDF/Tesseract, Docling primary and Unstructured complementary. Their existing deployment and compatibility have not been inspected; this is not a claim they are installed for CTM.
- **Included component candidates:** Uppy Audio/uploads, resumable transport, PhotoSwipe, Video.js and PDF.js. User requested these capabilities and their inclusion in the list. Exact versions/adapters remain subject to validation; no tested production integration is claimed.
- **Selected application foundation:** Django backend with Plenix React CDN presentation. Supporting job/PDF/security/backup tools remain as qualified below.
- **Undecided deployment details:** actual VM capacity; installed-service reuse; AI providers/models; optional server translation engine; scanning component; final integrations and backup destination.

## 2. Application foundation comparison

All three can support a custom CTM application. None ships CTM's privacy, one-open-case guard, decree authority, appeal proceedings or required permanent histories ready and verified.

| Criterion | Django | Ruby on Rails | Frappe Framework |
|---|---|---|---|
| Product type | Python web-application framework | Ruby web-application framework | Python/JavaScript metadata-driven business framework/platform |
| Reusable administration | Built-in model admin; Plenix portals custom | Custom/admin add-on; Plenix portals custom | DocTypes generate tables, forms/lists and Desk administration |
| PostgreSQL | Strong direct integration | Strong direct integration | Documented Postgres option; pinned release/custom-app migrations and constraints must be verified |
| Plenix integration | Custom views/endpoints | Custom views/endpoints | Custom pages/frontend over authorized APIs; not a simple CDN reskin of Desk |
| Provider-only sign-in | allauth adapters and SOCIALACCOUNT_ONLY configuration | OmniAuth strategies and custom enrollment controls | Social-login configuration plus verification of Apple and all local-password bypasses |
| Permission model | Model groups plus explicit case/object policies | Explicit policies, commonly Pundit | Role/user/document/query policies; custom methods and file/search access still require review |
| File/mail/job convenience | Storage and outbound mail foundations; more assembly | Active Storage, Mailer/Mailbox and Active Job/Solid Queue | Integrated attachments/email, record tools and scheduler/workers |
| Document processing | Common Python environment | Uses Python service/worker boundary | Common Python environment |
| Retained history fit | Explicit CTM revision/events | Explicit CTM revision/events | Map document submission/amendment conventions to CTM; generic history is not sufficient evidence of required retention |
| Strongest reason to choose | Direct domain control and Python alignment | Cohesive mail/files/jobs and Rails maintainer | Maximum record-administration reuse if platform conventions and generated screens are useful |
| Main trade-off | Assemble integrations explicitly | Separate Python processing stack; configure attachment authorization | Custom Plenix interface reduces generated-screen savings; more platform assumptions to reconcile |

**Recommendation:** prefer Django + PostgreSQL if no established maintainer favors another framework. This is a moderate architectural preference, not a performance or security ranking. Choose Rails if maintainer expertise or integrated mail/files/jobs outweigh Python convenience. Evaluate Frappe if minimizing generic record administration is the priority. No arbitrary code-savings percentage or development-cost estimate is claimed.

Detailed analyses: [Django versus Rails](CTM-Django-vs-Rails-analysis.md) and [Frappe versus both](CTM-Frappe-vs-Django-vs-Rails.md).

## 3. Open-source component register

Not every row is a standalone application or container. Some are libraries within the app/worker/browser, some are alternative framework paths, and some replace an existing service only if needed.

| Component | Responsibility | Execution location | Status / qualification |
|---|---|---|---|
| PostgreSQL | Authoritative case/person/account/answer/report/payment/audit and version relationships | Private database service | Confirmed database choice |
| Meilisearch | English/Arabic full-text search and filters over authorized derivatives | Private server service | Plenix primary selection; CTM aligned baseline; dedicated CTM instance recommended, shared service subject to isolation review |
| PaddleOCR | OCR for images/screenshots/photographed documents | Server processing worker/service | Reuse baseline; configure Arabic/English models; test mixed text, stamps and photographs |
| OCRmyPDF | Searchable scanned-PDF derivative generation | Server processing worker | Reuse baseline; original upload never overwritten |
| Tesseract | OCR engine/language packs for scanned PDFs | Same OCR processing environment | Reuse baseline; install eng/ara explicitly |
| Docling | Primary document text/layout/table/structure parser | Server processing worker/service | Reuse baseline; native text where available; configure OCR routing to avoid duplicate work |
| Unstructured open-source library | Complementary document partitioning, additional format handling and chunking | Server processing worker/service | Complementary only; not compulsory on every document |
| Uppy Core / upload integration | File selection, descriptions, progress and upload coordination | Browser within Plenix UI | Included candidate; CTM server enforces restrictions independently |
| Uppy Audio | Direct microphone capture for a whole report/testimony | Browser | Included candidate; pause/resume, mobile and interruption recovery need validation |
| Uppy Tus / compatible tus server | Resumable transport to CTM private upload area | Browser client and server endpoint | Included candidate; server implementation to choose; resumable upload is not live-recorder recovery |
| PhotoSwipe | Enlarged image-evidence dialog, zoom and touch navigation | Browser | Included image-viewer candidate; inline split-view preview remains CTM UI; rotation/fullscreen not assumed default |
| Video.js | Video evidence playback | Browser | Included video-player candidate; codec/range playback and Plenix compatibility to validate |
| PDF.js | Authorized PDF viewing | Browser | Included viewer candidate; not an OCR engine |
| Native browser audio element | Recorded testimony/report/evidence playback | Browser | Initial playback approach; separate waveform library not required yet |
| FFmpeg / ffprobe | Media inspection and playback/transcription derivatives | Server worker | Recommended support tool; preserve original and derivative provenance; selected build/license review required |
| whisper.cpp | Optional on-server speech recognition | Server worker | Candidate alternative to configured transcription API; not selected; reliable diarization and bidirectional translation not assumed bundled |
| django-allauth | Microsoft/Google/Apple provider adapters without local passwords | Django app | Conditional on Django selection; explicit provider-only setting and council enrollment policy |
| Celery | Durable job execution integration | Python worker | Django-path candidate; choose compatible queue backend rather than assuming mandatory |
| RabbitMQ | Broker for selected background worker configuration | Server service | Candidate if queue design needs it; reuse suitable existing service only after inspection |
| Pundit / OmniAuth | Rails authorization policy / provider authentication building blocks | Rails app | Conditional Rails-path libraries, not additional Django requirements |
| Active Storage / Active Job / Solid Queue / Action Mailer / Action Mailbox | Rails attachments, jobs and email infrastructure | Rails app/worker; queue database configuration | Rails-path components; do not install a redundant Celery/RabbitMQ stack automatically |
| Frappe scheduler/workers/Bench dependencies | Platform-owned app/job/service operation | Frappe deployment services | Frappe path only; use its supported pinned deployment rather than layering all competing framework components |
| WeasyPrint | Printable requests/forms and authorized decree/receipt PDFs | Server worker | Recommended candidate; bilingual shaping/page layout testing required; no general case export introduced |
| ClamAV | Upload malware scanning | Server service/worker integration | Recommended; scan result is not a guarantee every file is safe; existing technical acceptance pipeline applies |
| Caddy | HTTPS and reverse proxy | Server edge service | Candidate only if existing proxy is unsuitable; no need to replace a working approved proxy |
| Restic | Encrypted backup of file sets and database backup artifacts | Server/backup job | Candidate if existing backup system is insufficient; PostgreSQL-consistent backup strategy and restore tests remain required |
| Docker Engine / Compose | One deployment package with private networks, volumes and multiple services | Linux VM | Agreed deployment approach; exact distribution/configuration not provisioned |

Plenix CDN is the required presentation dependency. It is not described here as open source without a verified license. No assumption that third-party library default styles comply with Plenix; use isolated adapters and approved component interfaces.

## 4. Tools not selected as defaults

- Apache Tika: retain as a fallback candidate for a demonstrated format gap; do not duplicate Docling/Unstructured by default.
- OpenSearch/Elasticsearch: not primary search selections. Typesense remains a Plenix-acceptable alternative, not an additional CTM search requirement.
- Directus: technically relevant but official current documentation identifies MSCL licensing; do not classify it as a selected unrestricted open-source CTM base or assume free SSO/permissions eligibility.
- General-purpose file manager/DAM: not required merely to upload/manage case attachments. CTM handles case associations, permissions and histories over private storage. Existing storage service may be reused after inspection.
- Hosted document-intelligence APIs, automatic AI evidence summaries/classification and smart renaming: not adopted by reuse of the Plenix tools. CTM naming and evidence-attribution rules remain authoritative.
- PDF/document camera-scanning component: capability previously requested, product not selected. Upload, OCR and PDF viewing do not by themselves provide paper capture/device scanning.
- Cryptographic PDF-signature provider: not selected. Existing acceptance of a president's digital signature or uploaded signed document does not establish a certificate-backed signature service or legal certification.

## 5. What stores each kind of information

| Information | Authoritative location | Management rule |
|---|---|---|
| Accounts, people, cases, questionnaires, answers, requests, hearings, decisions and financial metadata | PostgreSQL | CTM lifecycle/permission/transaction logic, not generic platform CRUD alone |
| Transcripts, translations, manual answers and revision metadata | PostgreSQL with original recording/source references | Retain AI original, reviewed revisions and exact source versions distinctly |
| Word/PDF originals, images, audio/video, signed forms and certificates | Private persistent file storage | Opaque storage identifiers; human filenames follow CTM convention; no public directory browsing |
| OCR/parsing derivatives and searchable text | Private derivative storage/database relationships | Same source-version, case/privacy/release scope; do not overwrite originals |
| Search index | Meilisearch data volume | Rebuildable derivative; never the only retained copy; source authorization applies to hits/snippets/counts/facets |
| Business audit/access history | PostgreSQL | Actor, subject, action, source version and timestamp; prescribed visibility and retention |
| Runtime logs/errors | Restricted server/container log storage with rotation | Exclude secrets and sensitive document bodies; log management does not replace business audit |
| Keys and provider credentials | Protected server-side secret storage | No client plaintext retrieval or committed production secrets; masked configuration state |
| Backups | Separate configured destination | Database-consistent snapshots/artifacts plus file/secret recovery strategy; destination not yet chosen |

Private mounted VM storage is an adequate initial storage implementation; a separate object-storage application is optional. Persistent volumes are not backups. Do not store originals solely in container writable layers or put large media in database rows merely because a database supports binary data.

## 6. Processing and viewing flows

1. CTM authorizes an upload against its case/application/request and stores the private original; draft and medical-release restrictions continue.
2. Technical validation and malware checks precede ordinary availability. A submitted business response can be completed while permitted OCR remains queued; processing state is distinct from acceptance.
3. Select a route: image/screenshot → PaddleOCR; scanned PDF → OCRmyPDF/Tesseract derivative; born-digital documents → Docling native parsing. Use further structural processing only where needed, and avoid re-OCR or duplicate parsing of the same accepted output.
4. Unstructured is complementary for specific formats/ingestion/chunking. Do not presume its element model automatically accepts arbitrary Docling output without an adapter; preserve page/element provenance.
5. Retain extracted text/layout with source version, engine/model/configuration, status and timestamp. Every chunk retains the document/version, page/event context and permission scope. Chunking does not imply RAG, embeddings or AI summaries are required.
6. Index authorized content into CTM-scoped Meilisearch. No universal Plenix index or cross-program key exposes case data. Recheck authorization for source downloads, snippets and preview variants.
7. View evidence in the CTM Plenix workspace with PhotoSwipe/Video.js/PDF.js/audio controls. Authorize stream/range requests; record meaningful access without confusing every seek request with a separate user view.
8. Record one whole-report audio track in the reporting UI; retain recoverable captured portions as designed, finalize/submit, then queue transcription/translation. Original audio, source transcript, language versions and reviewed revisions remain separate. Do not transcribe every question independently.

All OCR/parsing executes in services running on the user's server environment, not on the applicant's computer and not via an unapproved cloud document processor. Disable remote-processing/enrichment options and pre-provision required model assets for controlled operation. Medical documents/extracted contents do not leave that environment via provider failover. Microphone capture and viewers necessarily execute in the browser; authoritative storage/processing is on the server.

## 7. External services — not open-source server apps

| Service | Agreed role | Pending setup |
|---|---|---|
| Microsoft organizational identity | Council sign-in/recovery; admin preauthorizes CTM membership | Actual lacopts tenant, app registration, callbacks and credentials |
| Google / Apple | Applicant sign-in/recovery; CTM has no local passwords | Provider apps/configuration, verified identity linking and Apple email behavior |
| Stripe | Likely payment provider for per-filer USD 250 fee, waivers/refunds under approved rules | Final provider commitment, credentials, signed webhooks and deployment setup |
| Email transport/inbound integration | Notifications, private correspondence and reply capture; email attachments rejected/returned | Select/reuse provider, verified sending/inbound domains and safe reply routing |
| Primary/fallback AI providers | Approved audio transcription/translation jobs per configured capability | Vendors/models, terms, keys, limits, review and failure handling |
| Optional non-AI translation engine on server | Alternative configured translation mode | Engine unspecified; cannot assume it executes the natural-language master prompt |

Microsoft/Google/Apple and Stripe are external services, not free/open-source apps installed on the VM. Password recovery remains with identity providers. API integration code does not authorize provider access to all documents.

## 8. Container and reuse plan

One CTM Linux VM, one deployment/Compose package, several services. Typical boundaries: HTTPS proxy; one chosen framework application; PostgreSQL; processing workers; framework-appropriate queue; Meilisearch; private persistent storage; optional separate OCR/parser/scanning services. Browser libraries do not require their own containers. Some processing tools can share a worker image; isolate incompatible/heavy dependencies where useful.

The user may already run relevant containers elsewhere. Before adding duplicates, inventory actual versions, licenses, data directories, network exposure, memory/CPU capacity, access controls, backup ownership and upgrade responsibility. Reusing software does not require sharing the same instance. CTM data, temp files, indexes and credentials must not bleed into other applications. A shared service must have equivalent isolation and access controls; otherwise deploy a dedicated CTM instance.

A move to another VM/Azure/AWS moves or restores database, files and secrets together and updates hostnames/callbacks; copying a Compose file alone does not migrate state.

## 9. Performance analysis

No framework benchmark has been run and no universal Django/Rails/Frappe speed ranking is claimed. Framework choice is unlikely to dominate this application's document/media workloads.

| Workload | Main performance determinants |
|---|---|
| Case/report pages and answer saves | Indexed queries, pagination, joins, object authorization and transaction design |
| Upload and evidence playback | Network, storage, resumable transfer and authenticated streaming/range handling |
| English/Arabic search | Meilisearch schema/ranking, filtering and index updates |
| OCR/transcription/conversion | Worker CPU/GPU/RAM, engine/model and bounded concurrency |
| Concurrent use | Worker/process sizing, DB connections and shared-resource contention |

Django and Rails allow focused custom queries/screens. Frappe adds metadata-driven behavior but that does not prove user-visible slowness. Heavy processing must not starve web/database services: separate containers still share the VM, so enforce resource/concurrency budgets. Do not invent sizing or throughput claims before workload measurement.

Use synthetic or authorized non-sensitive representative Arabic/English samples. Measure case opening, report save, private file download/seek, bilingual search and concurrent uploads while OCR runs. Include long recording interruption, mixed-language transcription, OCR failure/retry and permission revocation. Record p50/p95 latency, resource usage, queue delay, parsing accuracy and isolation results against agreed targets. Target values and VM sizing remain to be determined, not fabricated in this document.

## 10. Package acceptance and remaining technical decisions

- Use the selected Django foundation and choose its supported release; verify dependency compatibility and licenses for pinned versions and model weights. Alternatives are not all installed together.
- Inventory existing containers before selecting shared versus dedicated instances.
- Validate Arabic OCR/search/RTL rendering using CTM-representative samples; language support is not an accuracy guarantee.
- Validate recorder pause/resume/recovery and device permissions, mobile formats and browser behavior; Tus transport alone is insufficient evidence.
- Verify protected files/preview/range endpoints, applicant isolation, medical scope, search counts/snippets and closed-case writes under default admin/secretary and case-manager boundaries.
- Preserve original submissions/files, actor/source provenance and exact questionnaire/declaration/prompt versions; retired/removed question modules stay removed.
- Test backups and restoration of database/files/keys together. Record storage capacity/monitoring and log rotation without adding applicant file-count quotas.
- Select open-source paper-scanning integration and any additional media/signature requirements separately.
- Configure real identity/payment/email/AI providers only at setup; no credentials or live connection have been tested here.

## 11. Primary sources and linked analyses

- [Django/Rails analysis](CTM-Django-vs-Rails-analysis.md)
- [Frappe comparison](CTM-Frappe-vs-Django-vs-Rails.md)
- [Earlier tool research and source links](CTM-third-party-tools-and-platforms.md)
- [Django overview](https://docs.djangoproject.com/en/5.2/intro/overview/), [provider-only identity](https://docs.allauth.org/en/latest/socialaccount/configuration.html)
- [Rails guides](https://guides.rubyonrails.org/getting_started.html), [authenticated files](https://guides.rubyonrails.org/active_storage_overview.html#authenticated-controllers), [jobs](https://guides.rubyonrails.org/active_job_basics.html)
- [Frappe DocTypes](https://docs.frappe.io/framework/user/en/basics/doctypes), [current prerequisites](https://docs.frappe.io/framework/user/en/prerequisites), [permission hooks](https://docs.frappe.io/framework/user/en/python-api/hooks)
- [PaddleOCR Arabic support](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html)
- [OCRmyPDF languages](https://ocrmypdf.readthedocs.io/en/latest/languages.html)
- [Docling formats](https://docling-project.github.io/docling/usage/supported_formats/), [controlled server processing](https://docling-project.github.io/docling/usage/advanced_options/)
- [Unstructured partitioning](https://docs.unstructured.io/open-source/core-functionality/partitioning), [chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [Meilisearch Arabic tokenizer](https://github.com/meilisearch/charabia/blob/main/charabia/README.md), [search security](https://www.meilisearch.com/docs/capabilities/security/overview)
- [Uppy Audio](https://uppy.io/docs/audio/), [Tus](https://uppy.io/docs/tus/)
- [PhotoSwipe](https://photoswipe.com/), [Video.js](https://videojs.org/), [PDF.js](https://mozilla.github.io/pdf.js/)
- [FFmpeg](https://ffmpeg.org/about.html), [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- [WeasyPrint](https://weasyprint.org/), [ClamAV](https://docs.clamav.net/), [Caddy](https://caddyserver.com/docs/automatic-https), [Restic](https://restic.net/)
- [Docker persistent volumes](https://docs.docker.com/engine/storage/volumes/)

Referenced capabilities were researched from primary documentation in this conversation. Installed versions, operational readiness, exact release licensing and actual CTM performance remain unverified until inventory/evaluation. This document makes no changes to live services.


## Hosting clarification — 2026-10-20

Latest user decision: final hosting will be either Azure or a private server at a designated location with VPN access. The choice and network-access details will be discussed later. Do not treat an Azure migration in one week, public internet availability, or a specific VPN product as a committed deployment requirement. The immediate objective is a fully working functional demonstration for approximately 10 users. Use one dedicated Linux CTM VM containing multiple containers managed as one deployment package, with private persistent storage and a tested backup/restore plan. Keep hosting-specific endpoints, secrets, storage paths and provider callbacks configurable so the same application package can be deployed to either destination. Framework selection, VM sizing, distribution and exact software versions remain pending; this hosting clarification does not finalize them.


## Selected Django + Plenix React CDN — 2026-10-20

The user selected Django with Plenix CDN and identified Plenix as React-based. [Django–Plenix integration](CTM-Django-Plenix-integration.md) defines the compatible browser/server roles, same-origin deployment recommendation, protected endpoints and CDN integration verification. Earlier framework comparisons remain decision history; Django versus Rails/Frappe is no longer an open choice. Exact dependency versions, provider configuration and hosting remain deployment details. No actual application was built by recording this selection.


## Pinned Plenix CDN contract — 2026-10-20

[Plenix CDN contract (pinned 0.76.0)](CTM-Plenix-CDN-contract.md) is authoritative: load theme-boot, fonts, plenix CSS, matching React/ReactDOM vendor scripts and plenix.js in the user's specified order, using window.Plenix (or the documented ESM alternative with React 18 peer). Use documented Plenix components/patterns, plx- classes and --plx-sys-*/--plx-comp-* tokens only; no inline styles, raw colors, numeric font sizes or !important. Ask for missing components/values. No CDN assets are copied. The old prototype Arabic bridge is not yet compliant production styling; its necessary behavior must be reconciled against documented tokens before use.


## Initial VM deployment address — confirmed 2026-10-20

The user will initially install CTM on their own VM and access it at **https://ctm.lighthouseway.org**. Both applicant and council portals belong to this application origin; exact portal route paths are implementation details. Django sessions, CSRF origin checks, reverse-proxy/HTTPS settings and approved identity-provider callback registrations must use this canonical address. Payment/email callbacks use the same configured public application base URL where applicable. Do not invent a VM IP, DNS record, reverse proxy product or active provider connection from the supplied hostname.

Application availability at this address does not make case data public. Authentication, admin-only council enrollment, applicant isolation and private file/search access remain required. Database, search, processing services and storage management endpoints stay private. Whether network access will also be restricted by VPN must follow the final access decision; browser reachability and external provider webhook reachability must be configured explicitly rather than assumed.

This selects the initial own-VM deployment, while a later Azure/private-server move remains a separate future discussion. No DNS, certificate, VM, deployment or network setting was changed or verified by documenting the URL. All host-specific settings remain configurable for portability.


## In-app communications and call workflow — 2026-10-20

User explicitly requests in-app messaging, email and calling under Communications. [Communications workflow](CTM-communications-workflow.md) supersedes older email-only/no-chat statements and distinguishes reliable device-dial initiation logging from integrated telephony answered/duration/recording events. Asterisk is an optional open-source candidate only; normal tel links cannot record the other party's telephone audio. Search and Appeals split-view previews are now confirmed in the navigation/layout map. No phone system or UI was installed.


## Confirmed native messaging policy — 2026-10-20

[Communications workflow](CTM-communications-workflow.md) now records permanent sent messages, corrections by new message, existing/new document links backed by normal case storage, no council-only chat, existing-account/case access without separate messaging accounts, immediate portal availability, and immediate or 17:00 America/Los_Angeles email-summary delivery. This does not change other workflow-specific notification schedules. No live messaging service was built.


## Web calling scope finalized — 2026-10-20

Manual call log only: person, actual call date/time, outcome and notes, with separate automatic entry actor/timestamp. No dialling, phone-system integration, automatic duration or telephone recording in the web package. Asterisk is not a selected dependency. Communications uses the exact actions **Send Immediately** and **Send after council session**. See [current Communications rules](CTM-communications-workflow.md).
