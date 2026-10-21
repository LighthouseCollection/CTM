# Django versus Ruby on Rails for CTM

Analysis date: 2026-10-20. Decision support, not a selected stack, implementation, benchmark or security certification. Primary sources are linked beside the relevant facts. Compare framework capabilities and CTM-specific consequences separately. Do not infer that an existing framework is a ready-made tribunal application.

## Recommendation

Prefer Django + PostgreSQL if no maintainer has a stronger Rails preference. It fits CTM's relational/permission-heavy architecture, Python document-processing stack and provider-only authentication requirements. This is a moderate preference, not a technical disqualification of Rails. Rails is equally capable of enforcing CTM requirements and has a more integrated attachment/job/mail toolset. If an experienced Rails maintainer will own CTM, that staffing advantage can outweigh the Python integration benefit.

Neither option changes Plenix, PostgreSQL, Meilisearch, PaddleOCR, OCRmyPDF/Tesseract, Docling, Unstructured, Uppy, the evidence viewers, or the approved business rules by itself. No framework guarantees applicant privacy without explicit policies, query scoping and negative tests.

## CTM-specific comparison

| Requirement | Django | Rails | Assessment |
|---|---|---|---|
| PostgreSQL relationships and constraints | ORM, transactions, schema migrations, conditional unique/check constraints | Active Record, transactions, migrations and PostgreSQL-specific schema capabilities | Both fit; enforce one-open-case under concurrent submission in the database, not only form validation. |
| Applicant isolation / council access / assignment writes | Groups/model permissions built in; object-level implementation and case-scoped policy are custom or an add-on | Application authorization policies commonly use Pundit; case-scoped scopes/actions remain custom | No automatic winner. Both must check files, search, drafts, medical scopes and background jobs. |
| Microsoft/Google/Apple without local passwords | django-allauth supports these providers and SOCIALACCOUNT_ONLY | OmniAuth supplies a provider-strategy approach; choose maintained strategies for actual providers | Django advantage for an explicit documented provider-only mode. Rails can satisfy the rule too. Tenant restrictions, admin-only council enrollment and verified identity linking remain custom. |
| Administration | Built-in model-based Django admin | Custom admin UI or an additional administration library | Django advantage for restricted internal maintenance; not a substitute for the Plenix council portal. |
| Forms and validation | Built-in forms and model forms | Integrated model validations, helpers and controllers | Both need custom versioned questionnaire/template definitions and immutable sent snapshots. |
| Plenix interface | Templates/rendered pages or backend endpoints | ERB/rendered pages or backend endpoints | Tie; neither forces React or a different design system. Plenix JS components can be integrated in either. |
| File attachments and storage adapters | FileField/storage abstraction, optional backend packages | Active Storage built in with attachment associations, local/cloud services and derivatives | Rails advantage in integration; CTM version histories, naming, access/release and deletion exceptions remain custom. |
| Private evidence access | Explicit authorized file-serving path; do not expose raw MEDIA URLs | Authenticated controllers required; default Active Storage routes are publicly accessible to anyone with the URL | Both require deliberate configuration. A signed/hard-to-guess URL is not current case authorization. |
| Background jobs | Celery or another production backend; Django 6.0+ Tasks defines jobs but does not supply production execution | Active Job with Solid Queue production integration | Rails advantage for a cohesive default. Separate workers still needed. No automatic requirement for Redis/RabbitMQ in Rails. |
| Incoming/outgoing email | Outbound email support; inbound ingestion adapter/provider integration needs assembly | Action Mailer and Action Mailbox | Rails advantage for built-in inbound routing. CTM still implements safe recipient/case binding, attachment rejection and permanent correspondence records. |
| Document processing | Python workers can reuse Python parsing/OCR libraries directly | Rails jobs call processing services or a separate Python worker | Django integration advantage if workers share Python code; small advantage if existing services already expose stable interfaces. |
| Bilingual UI and RTL | Translation framework and locale handling | I18n framework and locale handling | Both fit. Egyptian Arabic wording, runtime question-bank translations, Plenix RTL adapter and translation approval history are CTM work. |
| Audit and immutable histories | Custom domain revision/events; admin history alone insufficient | Custom domain revision/events; generic auditing gems alone insufficient | Tie. Explicit actor/subject/source-version/proceeding records needed. |
| Fees, appeals and decrees | Custom domain services and constraints | Custom domain services and constraints | Tie. Neither bundles CTM approvals, waivers, payment finalization or decree entitlement. |
| Linux containers and migration to another VM/cloud | Supported deployment patterns and external database/storage connections | Supported deployment patterns and external database/storage connections | Both suitable. Back up database plus private files and preserve secrets/identity callbacks. Container portability alone does not migrate the data. |

## Authentication and authorization

Django's groups/model permissions are useful building blocks but do not implement CTM object permissions automatically. Its documentation explicitly says core has no object-permission implementation. Define an explicit account/person/case/proceeding policy, shared by views, workers, search and downloads. Sources: [Django object permissions](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#handling-object-permissions), [Django auth](https://docs.djangoproject.com/en/5.2/topics/auth/default/).

For Django, django-allauth lists the needed providers and documents SOCIALACCOUNT_ONLY, disabling local account authentication functions. Still verify that no local password endpoints, basic-auth fallback or public council signup remain. For Rails, OmniAuth is a framework for provider strategies, not a verified turnkey set of all CTM identity rules. Configure Microsoft tenant validation, Google/Apple strategies and CSRF-safe callback handling. Do not add Rails' password authentication scaffolding merely because it is available. Sources: [allauth providers](https://docs.allauth.org/en/latest/socialaccount/providers/index.html), [provider-only setting](https://docs.allauth.org/en/latest/socialaccount/configuration.html), [OmniAuth](https://github.com/omniauth/omniauth), [Pundit](https://github.com/varvet/pundit).

Only an existing CTM admin can authorize a council account; provider login cannot enroll one. Admin/secretary operational authority remains subject to the agreed function boundaries; case workers cannot manage decrees. External priest request links remain a separate 30-day scoped access mechanism. The framework choice changes none of this.

## Files, transcripts and retained history

PostgreSQL stores source associations, structured answers, transcript/translation text, actors, audit and revisions. Files remain in private persistent storage. Django and Rails both support storage abstractions; neither requires storing large videos inside PostgreSQL. Rails Active Storage provides a particularly integrated attachment model; Django normally requires more explicit application-level assembly. Sources: [Django files](https://docs.djangoproject.com/en/5.2/topics/files/), [Active Storage](https://guides.rubyonrails.org/active_storage_overview.html).

A key Rails default is unsuitable for CTM unchanged: default Active Storage controllers are publicly accessible to anyone who knows their URL. Use authenticated/policy-checked routes, and disable bypass routes; apply authorization to range requests and preview variants. With Django, similarly do not expose a public media directory for protected files. Neither framework's ordinary attachment API supplies the user's exact version/retention rules. Keep original signed submissions, originals/derivatives, private latest-version access, council history and special mistaken-upload removal distinct.

No automatic cascading purge should delete submitted evidence when records/accounts are deactivated. Original media, generated previews, OCR text and search hits require linked retention and authorization. Search indexes are derivatives and cannot substitute for immutable source records.

## Processing and email

Rails Active Job + Solid Queue integrates durable background work; PostgreSQL can support the queue without making RabbitMQ mandatory. Django 6.0 introduced Tasks, but its documentation states that production execution needs a configured external backend/worker. If using Django 5.2 LTS, that core API is not present; Celery or an evaluated compatible queue remains an option. Select a supported framework release and compatible packages rather than assuming APIs from another series. Sources: [Rails jobs](https://guides.rubyonrails.org/active_job_basics.html), [Django Tasks](https://docs.djangoproject.com/en/6.0/topics/tasks/).

Queue integration is not exactly-once execution. Both need idempotent payment/webhook processing, retry-safe OCR, a transactionally recorded notification outbox, source-version binding and current assignment resolution for notifications. Do not create two divergent case databases merely because a queue backend uses separate tables/databases. Heavy processing workers are isolated from web request handling for either choice.

Rails Action Mailbox reduces inbound-email integration work, but it is an ingestion layer, not permanent CTM case history. Persist the accepted body/header/party/case provenance into domain records before temporary inbound records expire. Reject/return email attachments under the existing policy instead of retaining hidden MIME attachments as evidence. Sources: [Action Mailbox](https://guides.rubyonrails.org/action_mailbox_basics.html). Django needs more explicit assembly of inbound parsing/webhook/transport handling but can implement the same policy.

## UI and language

Both frameworks can render the Plenix UI directly; no additional SPA is required. Keep locale resources, custom Egyptian/formal-common translations and RTL styling separate from case source text. Neither framework automatically translates the bank through the user's master prompt. That needs versioned jobs, approved publishing and the existing provider-failover policy. Dynamic database-held questions are not solved merely by a framework's static message catalog. Sources: [Django localization](https://docs.djangoproject.com/en/5.2/topics/i18n/), [Rails I18n](https://guides.rubyonrails.org/i18n.html).

Django admin is intended as an internal management tool; Django specifically recommends custom views for process-centric interfaces. It does not need to be exposed to council members or substitute for Plenix. Likewise Rails admin add-ons should not become unreviewed paths around CTM's policies. Source: [Django admin](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/).

## Security, operations and maintenance

Both frameworks document protections for common web threats. Framework protections do not enforce business authorization, consent scopes, untrusted document handling or safe secret management automatically. Neither language/framework alone is intrinsically the secure choice for this tribunal. Sources: [Django security](https://docs.djangoproject.com/en/5.2/topics/security/), [Rails security](https://guides.rubyonrails.org/security.html).

Use a supported pinned release and security update plan. Django's published table lists 5.2 LTS extended support through April 2028; Rails' maintenance policy specifies two years of security fixes for minor release series. These are different policies, not a reason to stop applying patches or a claim that every dependency shares the framework's coverage. Source: [Django support](https://www.djangoproject.com/download/), [Rails maintenance](https://guides.rubyonrails.org/maintenance_policy.html).

No measured speed, memory, cost, hiring supply or development-day advantage is claimed here. For CTM, OCR/transcription/database/media workload and the actual deployment matter more than language microbenchmarks. A Rails application can call Python services without rewriting the OCR libraries in Ruby. Do not install two web frameworks simply to connect those services.

## Practical decision

Choose Django if the team is comfortable with Python, values direct control of domain policies, and wants document workers and application services in a common language. Plan explicitly for protected attachments, inbound email and a durable queue.

Choose Rails if the maintainer is stronger in Ruby/Rails or prioritizes integrated attachment, mail and background-job components, and is comfortable operating Python processing services alongside Rails. Plan explicitly for case policies, authenticated file routes and reviewed provider adapters.

My CTM recommendation remains Django + PostgreSQL, moderately rather than decisively. Plenix and the selected server tools make either viable. The biggest remaining unknown is long-term maintainer expertise, not a missing framework feature.

## Fair validation before commitment

Use the same small, synthetic-data evaluation in both only if a real uncertainty justifies it: two applicants in one case with isolated answers; admin-authorized Microsoft council member; Google/Apple applicant without local password; concurrent one-open-case guard; submitted report plus follow-up/revision history; private original/preview/range download; server extraction into permission-scoped Meilisearch; one safely linked inbound email without accepted attachments. Compare policy clarity, number of custom adapters, update burden and maintainer confidence. Do not build two full CTM applications to choose a framework. No such proof-of-concept or benchmark has been run in this analysis.
