# Database source privacy

Implemented slice: migration `0011_source_privacy`, PostgreSQL only. SQLite tests do not establish database privacy.

## Protected sources

Forced row-level security covers Application, AnswerRevision, Submission, Attachment, FileVersion, FileTechnicalEvent, DocumentText, ReportRevision, MedicalRelease, Message, MessageRecipient, Notification, AuditEvent and HistoricalWorkspace.

Applicants read their own permitted sources; council cannot read unfinished application drafts. Applicants see their latest permitted attachment version and exact released decree file, not other parties' sources, staff narratives or certificate history. Medical documents require the exact request's release. Private messages, notifications and audit projections retain their existing audience rules.

Writes enforce source ownership and contextual relationships. Original application owner/purpose and submitted provenance cannot be reassigned or reset into a disposable draft. Private never-submitted draft graphs retain their cleanup exception. Existing append-only and closed-proceeding triggers remain in force.

## Trusted database context

Authenticated requests receive a transaction-local actor UUID from the authenticated server session. Active role is looked up in the database. Nested contexts restore previous values. Missing/inactive identity fails closed for protected sources.

An external priest has no council identity. The completed response uses a narrow request ID and token digest, with expiry, request kind and open-proceeding checks. Only the matching response, audit and assigned-manager notification writes are permitted.

Payment callbacks clear interactive identity after signature verification. Recovery establishes the filing owner only when the checkout, paid obligation and matching payment event agree. A paid filing that cannot safely finalize remains available for reconciliation.

Private helper functions revoke PUBLIC execution. Only the explicit policy/recovery entrypoints are granted to recognized runtime roles. Security-definer helpers pin their search path.

## Role boundary and deployment gates

The migration owner has an explicit privileged policy for schema/data maintenance. Application and worker credentials must not own these tables, inherit the migration role, be superusers or have BYPASSRLS.

`deploy/provision-isolated-roles.py` prepares a non-login validation role on the isolated VM. The tests grant broad table DML solely to prove that row policies, rather than endpoint filters, enforce this slice. Those grants are not a production configuration.

The trusted actor settings do not defend against arbitrary SQL execution by a compromised database credential. Application authentication, parameterized queries, restricted grants and separate schema ownership remain necessary.

This slice does not complete the remaining domain-table policies, financial/authentication grants, worker processing and retention identities, or reconciliation with the approved 151-table contract. Do not promote the validation container or migration credential to production. The existing isolated base container has not been upgraded by the ephemeral test migrations.

## Evidence

The isolated Linux/PostgreSQL suite passes 92 tests, including raw non-owner queries, request middleware, external responses and notifications, payment signature/cookie isolation, private-helper ACLs and migration reversal/reapplication. Review found four defects during implementation; ownership takeover, submitted-to-draft reset, later unreleased certificate visibility and OCR draft cleanup now have regression coverage. Final read-only review found no further concrete defect in this slice.
