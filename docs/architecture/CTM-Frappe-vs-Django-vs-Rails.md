# Frappe versus Django and Rails for CTM

Research date: 2026-10-20. Analysis only; no platform selected or installed. This extends CTM-Django-vs-Rails-analysis.md. Conclusions about fit are engineering judgments, not measured development estimates or security certifications.

## Main finding

Frappe is the closest of these three to a configurable business-application platform. Django and Rails provide reusable web-application foundations with more application assembly. Frappe can save substantial time on record-based administration; that benefit is greatest when using its generated Desk interface. Replacing both applicant and council experiences with Plenix preserves backend reuse but requires custom interface integration and CTM policy code.

## Comparison

| Area | Frappe | Django | Rails |
|---|---|---|---|
| Ready-made record forms/lists | DocTypes generate tables and Desk forms/lists | Built-in model administration, custom portal screens | Custom screens or additional administration library |
| Data conventions | DocType metadata, naming/table conventions, document APIs | Models/migrations and explicit domain structure | Active Record/migrations and explicit domain structure |
| Plenix applicant/council portals | Custom pages/frontend over authorized backend APIs; generated Desk does not become Plenix just by loading CSS | Custom rendered views/endpoints using Plenix | Custom rendered views/endpoints using Plenix |
| Fine-grained case permissions | Roles/user permissions plus document/query hooks; CTM-specific policies needed | Model permissions plus explicit object/query policies | Explicit policy scopes, commonly Pundit |
| PostgreSQL | Documentation recognizes Postgres; exact selected release/custom app compatibility needs validation | Direct established framework integration | Direct established framework integration |
| Provider-only identity | Microsoft/Google/custom social providers documented; Apple and all local-login bypasses need verification | allauth provider adapters and documented SOCIALACCOUNT_ONLY | OmniAuth strategies plus restricted application enrollment |
| Files and correspondence | Record forms integrate attachments/email/comments | Storage abstraction, outbound mail; other integrations assembled | Active Storage, Action Mailer and Action Mailbox |
| Background work | Framework worker/scheduler stack; Bench includes multiple services | Selected production worker/queue | Active Job + Solid Queue or another backend |
| Python OCR/document tools | Python backend can integrate directly or through isolated workers | Same advantage | Calls isolated Python services |
| CTM retained histories | Built-in document versioning/audit not automatically the required unlimited case/file/actor history | Explicit domain history | Explicit domain history |
| Deployment/upgrades | Bench/Frappe stack and custom-app conventions | Application and chosen service stack | Application and chosen service stack |
| Best use in this project | Fast record-oriented application if platform conventions are accepted | Strong fit for controlled Plenix/domain design and Python team | Strong fit for cohesive files/mail/jobs and Rails team |

## Frappe-specific considerations

### What is genuinely reusable

DocTypes describe fields, relationships and behavior and generate database tables and list/form views. Desk forms support attachments, print/PDF, comments and email. These are real advantages, not simply a marketing label. Frappe Framework is the base; installing ERPNext accounting/ERP modules is not required to create a custom CTM app.

A custom CTM app can use document/controller hooks and authorized APIs. This is supported extension, not a claim that every CTM rule can be configured with dropdowns. Standard generic CRUD endpoints must enforce the same rules as Plenix pages; hiding a button does not disable an endpoint.

### Plenix changes the savings

Use generated Desk for internal maintenance if authorized and desired, or build custom Plenix portals over the framework. Rebuilding every generated interaction in Plenix can duplicate form presentation/validation work. There is no tested automatic mapping from Frappe metadata to Plenix components. A fork or wholesale restyling of Desk is not the recommended integration. Keep custom CTM code in a separate app, not edits to framework core.

### Permission scope is not automatic

Frappe's permission_query_conditions hook affects get_list, not get_all. Document has_permission hooks, authorized file routes, background jobs, Meilisearch indexing and custom methods need explicit review. This is not proof Frappe is insecure; it is proof that installing it does not automatically enforce applicant A/B isolation. Administrator defaults must be mapped to CTM's agreed authority rather than granting every council user a platform system-administrator role.

### Submission/history needs a domain mapping

Frappe docstatus uses Draft, Submitted and Cancelled, with selected fields optionally editable after submission. CTM needs separately preserved original applications, attributed answer revisions, report-author revisions while open, locked applicant responses, separate follow-up reports and immutable original closed proceedings. Do not map an accepted appeal to cancellation/erasure of an original report or case.

The documented Audit Trail viewer compares up to five amended versions of a submittable document. That viewer limit is not proof the underlying database retains only five versions. It also does not establish CTM's full actor/access/file-version retention requirement. Implement and validate those explicit records rather than relying on a generic audit label.

### PostgreSQL qualification

Current reachable prerequisites mention MariaDB/Postgres. Earlier framework-git documentation links used in the initial shortlist now return 404; they cannot justify declaring every current Frappe release's PostgreSQL support experimental. Conversely, the prerequisites mention does not prove every release, migration, addon or sample SQL is portable. Evaluate the pinned Frappe release, actual CTM custom app and database invariants. Do not change the agreed PostgreSQL database to MariaDB without a separate decision.

### Scope remains unchanged

Frappe does not replace Meilisearch, Plenix translation resources, original private file storage, Uppy, OCR pipelines or evidence players automatically. Do not adopt generic export/delete/cancel actions that conflict with CTM retention. Do not expose general framework password/signup endpoints merely because Microsoft or Google login has been enabled. Existing external-priest request links and scoped medical releases remain custom domain behavior.

## Recommendation

Django remains the preferred fit if Plenix controls both portals, PostgreSQL remains fixed, and the maintainer has no Rails/Frappe specialization. Rails remains a close alternative for integrated mail/files/jobs. Frappe deserves an evaluation if minimizing generic record administration is the top priority and the team accepts its data/lifecycle/operations conventions. It could be the better choice if selected-platform validation shows most CTM administration can be reused without a large parallel Plenix interface implementation.

No honest percentage-of-code-saved or delivery-date comparison is available without a small proof. Test the same isolated synthetic scenario: two private applicant submissions, one admin-authorized Microsoft council account, provider-only Google/Apple applicant, case assignment, submitted intake with follow-up/revision, authorized evidence retrieval and OCR/search. Confirm the exact PostgreSQL release configuration and preserved historical snapshots. No real case data and no full duplicate implementation needed.

## Primary references

- Frappe overview/generated Desk: https://docs.frappe.io/framework/user/en/basics
- DocTypes: https://docs.frappe.io/framework/user/en/basics/doctypes
- Permissions: https://docs.frappe.io/framework/user/en/basics/users-and-permissions
- Permission/document hooks: https://docs.frappe.io/framework/user/en/python-api/hooks
- APIs: https://docs.frappe.io/framework/user/en/api/rest
- Social login: https://docs.frappe.io/framework/user/en/guides/integration/social_login_key
- Prerequisites including MariaDB/Postgres: https://docs.frappe.io/framework/user/en/prerequisites
- Document lifecycle: https://docs.frappe.io/framework/doctypes/docstatus
- Audit Trail viewer: https://docs.frappe.io/framework/user/en/audit-trail
- Bench/architecture: https://docs.frappe.io/framework/user/en/basics/architecture
- Django permissions: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
- Rails attachment authorization: https://guides.rubyonrails.org/active_storage_overview.html
- Rails jobs: https://guides.rubyonrails.org/active_job_basics.html
