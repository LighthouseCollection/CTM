# Privacy data map

Where every kind of personal, medical and financial data lives, why, who can
read it, how long it is kept, and how it leaves. Adapted from agency-agents
`engineering-privacy-engineer` (MIT). CTM cases are never deleted, so most rows
record a **retention exception** rather than a delete path - that is fine, but
it must be written down.

**Rule:** a new field, store, queue, log, index, cache or outside service that
holds such data needs a row here before merge (checked by
`ctm3-security-reviewer`, rule 11a). Rows are filled from code at a named
commit; `ctm3-database-engineer` and `ctm3-drift-auditor` keep it current.

| Data | Category | Stores (incl. derived) | Purpose | Who can read | Retention | Leaves CTM? | Status |
|---|---|---|---|---|---|---|---|
| Applicant identity (names, DOB, sex, email, provider subject) | Direct identifiers | PostgreSQL; search index; email bodies; logs? | Filing, matching, notices | Own applicant; council (submitted) | Case lifetime (never deleted) | Email provider; OAuth provider | To verify |
| Marriage / separation details | Personal | PostgreSQL; search index | Case | Own applicant; council | Case lifetime | No | To verify |
| Uploaded documents and evidence | Personal, may be sensitive | Private media volume; OCR text; search index | Case | Own applicant (latest); council (history) | Case lifetime | No (OCR on server) | To verify |
| Professional Assessments (medical/psychological) | **Special category** | Private media; OCR text | Case, release-scoped | Within signed release scope only | Case lifetime | **Never to external AI** (SEC06) | To verify |
| Report answers, recordings, transcripts | Personal, may be sensitive | PostgreSQL; private media; transcription runs | Investigation | Council; applicant own submitted answers | Case lifetime | Approved AI API for audio only (not medical) | To verify |
| Messages and call records | Personal | PostgreSQL; outbox; email | Communication | Recipient party; council | Case lifetime | Email provider | To verify |
| Payments | Financial | PostgreSQL (`PaymentEvent`, intents); Stripe | Fees | Own applicant; finance roles | Financial record retention | Stripe (no card data in CTM) | To verify |
| Council member accounts | Direct identifiers | PostgreSQL; sessions | Access | Admin | Membership + audit | Microsoft Entra | To verify |
| Unsubmitted drafts | Personal | PostgreSQL; private media | Draft filing | Own applicant only | 180 days inactivity (7-day warning), then cleanup | No | To verify |
| Logs, error traces, Celery task arguments, Redis/cache, backups | Derived | Logs, broker, cache, backups | Operations | Operators | Per ops policy | Backup location | **Audit needed**: no personal data in logs/task args |

Next step: fill "Stores" and "Status" from code (models, tasks, logging,
search indexing, outbox) at a named commit; open a drift entry for anything
that holds personal data without a purpose.
