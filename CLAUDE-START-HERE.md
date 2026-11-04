# CTM — Complete project handoff for Claude

Prepared: 2026-10-21, America/Los_Angeles.

## Start instruction

Build the council workspace of CTM as a real application, using the existing
Django implementation and approved architecture. Begin implementation after
reading the sources below. Do not stop at a plan or recreate the prototype.
Continue independent authorized work when a dependency is blocked; record the
blocker in GitHub. Do not claim functionality that is only mocked or unfinished.

This document explains the whole project so you can understand your workstream.
It does not transfer ownership of the other two streams to you. GitHub is the
shared coordination system; the original Codex conversation is governance.

## Repository and coordination

- Application: https://github.com/LighthouseCollection/CTM — private repository.
- Historical prototype: https://github.com/LighthouseCollection/ctm-alpha.
- Your issue: https://github.com/LighthouseCollection/CTM/issues/3.
- Governance tracker: https://github.com/LighthouseCollection/CTM/issues/4.
- Applicant stream: https://github.com/LighthouseCollection/CTM/issues/1.
- Backend/security stream: https://github.com/LighthouseCollection/CTM/issues/2.
- Your branch: `work/claude-council`.

Clone the application into your own new working directory. Do not share another
agent's checkout. Fetch current main before starting; newer commits may exist.

```sh
git clone https://github.com/LighthouseCollection/CTM.git CTM-Claude
cd CTM-Claude
git switch -c work/claude-council origin/main
```

On Desktop-R, `D:\Documents\Projects\Projects_Applications\CTM-Application`
is the integration checkout. The adjacent `CTM` directory is the earlier
prototype. Do not edit either in parallel with its owner. Paths on VM-FRM may
differ; use your own clone.

| Owner | Work |
| --- | --- |
| Codex Desktop-R | Applicant portal implementation |
| Codex VM-FRM | Shared backend/services, schema migrations, database security and integrations |
| Claude | Council workspace implementation |
| Governance chat | Shared contracts/shell coordination, review, merges, integration acceptance and deployment |

Post progress, dependencies and test evidence on issue3 and your PR. Open a draft
PR early. Never merge your own work or push implementation to main. Do not deploy
or run operational migrations independently. Shared backend changes belong to
VM-FRM: request exact endpoint/behavior changes in GitHub rather than editing them
without coordination. Separate council frontend modules from applicant modules;
coordinate `static/ctm/app.js` and shared script loading before changing them.

## Read these sources first

The approved contract is more detailed than this handoff. These are repository
paths, not installed packages:

1. `docs/implementation/governance.md` and `stream-claude.md`.
2. `docs/architecture/build-spec/README.md`.
3. `docs/architecture/build-spec/CTM-build-specification.md`, especially resolved
   precedence corrections: later decisions override earlier prototype behavior.
4. `schema.json`, `data-dictionary.md`, `permissions.md`, `interface-contract.md`
   and `transactions-and-acceptance.md` in that same build-spec directory.
5. `docs/architecture/CTM-Plenix-CDN-contract.md`.
6. `docs/implementation/status.md` and `validation-results.json` — read the latest
   entries; older status sections remain historical and can be superseded.
7. Current code in `tribunal/`, `ctm/`, `static/ctm/`, `templates/` and `tests/`.

Protected build-spec sources must not be edited to make implementation pass.
The approved contract plans151 physical tables. The current Django implementation
is partial, with58 domain models at the last reconciliation. Do not treat the
smaller implementation as a replacement architecture. Do not execute structural
`schema.sql` beside Django migrations; migrations are the implementation path.

If two sources conflict, apply documented precedence corrections and raise the
exact remaining conflict in GitHub. Do not invent missing answers or resurrect
earlier rejected workflows.

## Product and delivery objective

CTM is a Coptic Orthodox church tribunal case-management application. One server
application, one shared PostgreSQL database, and one login entry route people to
an applicant workspace or council workspace according to server authorization.
There is one tribunal. Authorized council members can read all submitted cases;
applicants cannot read each other's information, even within the same case.

The immediate goal is a functional demo for about10 users, then deployment at
`https://ctm.lighthouseway.org`. Hosting is initially a dedicated Linux VM and
must remain portable to Azure or another private server. The user wants rapid,
continuous implementation. Do not promise a finished production system without
evidence. OCR and audio recording are explicitly low priority: clearly labelled
unavailable placeholders are acceptable for the demo. File access/scan safety is
not deferred with those features.

## Finalized technology direction

| Capability | Selected direction |
| --- | --- |
| Application | Django5.2 modular monolith; Python3.12 baseline; transactional services |
| UI | React18 with pinned Plenix CDN 0.76.0, not a copy of the prototype UI |
| Relational data | PostgreSQL16; ORM migrations, constraints, explicit authorization and RLS |
| Background processing | Celery, Redis, Celery Beat, durable transactional outbox |
| Search | Meilisearch; authorized source filtering and derived indexes |
| Private binaries | Managed private media storage; metadata/ownership/version records in PostgreSQL |
| Malware scanning | ClamAV; unclean or unprocessed files cannot be treated as safe |
| Scanned PDF OCR | OCRmyPDF + Tesseract, English and Arabic, server processing |
| Image OCR | PaddleOCR, server processing |
| Document understanding | Docling primary; Unstructured complementary, where actually needed |
| Media processing | FFmpeg worker; recorder integrated into report UI later |
| PDF generation | Existing image/tooling includes WeasyPrint; verify current implementation |
| Council identity | Microsoft Entra provider-only sign-in; preauthorized tenant/object identity |
| Applicant identity | Google/Apple provider-only direction; live integration still incomplete |
| Online fees | Stripe adapter exists; credentials/live acceptance still required |
| Packaging | Docker Compose, Gunicorn, WhiteNoise, Nginx Proxy Manager HTTPS ingress |

Not every selected tool is operationally integrated. Check the current Compose
and worker images. Database stores structured data/transcript text/metadata;
private file storage holds PDFs, Office files, images, audio and video. Meilisearch
is a derived index, never the authoritative record or file store. Do not introduce
a standalone file-manager product that bypasses CTM permissions/versioning.

Keep document OCR on CTM's server. Audio transcription can use configured server
processing or an approved AI API; this exception is not blanket authorization to
send medical documents or all evidence externally. Preserve originals.

## Mandatory Plenix rules

Read published component documentation before using a component. Base:
`https://design-system.lighthouseway.org/cdn/0.76.0/`.

```html
<html lang="en" data-plx-density-policy="compact">
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/theme-boot.js"></script>
<link rel="stylesheet" href="https://design-system.lighthouseway.org/cdn/0.76.0/fonts.css">
<link rel="stylesheet" href="https://design-system.lighthouseway.org/cdn/0.76.0/plenix.css">
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/vendor/react.production.min.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/vendor/react-dom.production.min.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/plenix.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/plenix-icons-plenix.js"></script>
<script src="https://design-system.lighthouseway.org/cdn/0.76.0/plenix-engines.js"></script>
```

`plenix-engines.js` is needed only on a page that shows a rich-text editor, a chart or a PDF.

- Use `window.Plenix`, documented components/patterns and `plx-` classes.
- Use `--plx-sys-*`/`--plx-comp-*` tokens; no raw colors or numeric font sizes.
- No application inline styles, `!important`, copied CDN files or substitute UI kit.
- Documentation: `docs/index.json`, then `docs/<id>.md` under the pinned base.
- Missing component/value is a dependency to report, not permission to invent one.
- English/Arabic equivalents cover labels, questions, help, validation, comments,
  prompts and notices. Use formal/common Egyptian-facing Arabic as approved.
- RTL patch is the explicitly permitted temporary exception. Keep it separate
  and replaceable by the later Arabic Plenix CDN; preserve bidirectional IDs/email.
- Translation uses the accepted editable institutional prompt and configured
  primary/fallback engines. Do not improvise doctrinal translations or alter the
  English question bank to fit a translation engine.

## Core data and privacy rules

- Internal UUIDs are stable identifiers. Human references never grant access.
- Case number: `YYYYMMDD-##`, based on creation date in Los Angeles;99/day accepted.
- Case-based CTM party reference example: `20261020-01-JS19850314M`.
  English first/last initials, DOB and M/F form the reference. Corrections preserve
  an already-issued CTM reference. See approved contract for identity lifecycle.
- Many lifetime cases, at most one open case per applicant. One unfinished new
  case draft. New drafts blocked while a case is open, with documented same-case
  spouse filing rules. Pending appeals do not themselves reopen a case.
- Independent spouses' filings match automatically using exact marriage date
  and both spouses' exact DOBs as an unordered pair. Exact names/venue spelling
  is not required. Certificate conflicts do not defeat the exact three-date match.
  Ambiguity requires review; a match never automatically merges person identities.
- Pending spouse association uses first name, last name and email. Connect after
  matching provider registration and verified email; existing verified account
  links automatically. No separate invitation acceptance workflow.
- Applicant drafts remain private. Council sees formal submissions, including
  closed cases. Original submissions, corrections and attributable history persist.
- Applicant sees own answers/history and latest own attachments, not the spouse's
  content or attachment version history. Council sees authorized histories.
- Assigned case manager controls case work. All council members can read; only
  authorized actors mutate. Admin/secretary are not automatically copied into
  day-to-day assigned-case notifications. System/intake/finance roles retain their
  specifically approved authority. Read the permission matrix per action.
- Closed proceedings are read-only; approved exceptions include communications
  and the defined appeal process. Cases are never deleted.

## Applicant journey (other stream; understand the handoffs)

Provider registration and email verification precede filing. Inform applicants
of the250 USD fee before they start. Save drafts and uploads before payment;
successful payment or authorized fee waiver is required before submission.
Each independently filing party pays; linking as the other party alone is free.
Fees are nonrefundable after submission, except accidental duplicates can be
refunded by authorized staff. No applicant waiver-request UI.

The approved questionnaire requires marriage certificate, finalized civil divorce
decree, CMC and applicant photo; spouse photo is optional if unavailable. Petition
statement can be typed or PDF/Word. Unknown spouse details are permitted where
approved. Restraining orders are repeatable with required copies. Children collect
approved details with Unknown where allowed. Baptism certificates are not required.
Use the contract for exact field/conditional requirements, not this summary alone.

Grounds are multi-select: Infidelity; Desertion/abandonment; Abuse; Leaving or
changing the faith; Addiction; Misrepresentation/concealment prior to marriage.
No imprisonment ground. Preserve each party's independent answers.

Drafts expire after180 days inactivity with a7-day warning. Returned applications
retain case number/payment; correction instructions are required. Saved open-case
corrections preserve actor/time/history without a reason or new signature.
Applicant changes notify the assigned case manager immediately in the portal,
with email summary after10 minutes inactivity. Staff corrections follow the
approved notification-free rule. Consult final routing exceptions in the contract.

## Council workflow — your implementation priority

1. **Completeness review:** authorized intake staff accept or return submitted
   applications with a required explanation. Returning is not a final case denial.
2. **Agenda:** Part1 accepted new cases for assignment; Part2 ongoing case hearings.
   Assigned members can mark their cases for an upcoming session.
3. **Assignment:** president authorizes; authorized admin/secretary records.
   Exactly one assigned member at a time, full history and assignment notifications.
4. **Council session:** one per calendar date. Friendly name Council Session
   YYYY-MM-DD, date-derived internal ID. Follow the approved reschedule/carryover
   distinctions; do not invent an automatic next session when no date exists.
5. **Attendance:** baseline session roster plus hearing-specific presence.
   Only assigned member presents; absence defers hearing for manual placement.
6. **Investigation:** reports, evidence, findings and internal notes. Council
   findings never overwrite either applicant's statement.
7. **Hearing:** Case Hearing of [first last] vs. [first last]. Internal discussion;
   applicant testimony is exceptional and separately scheduled, never both parties
   together. Confirm/Reject invitation, optional rejection explanation; no applicant
   reschedule request. Keep case on agenda even if testimony is rejected.
8. **Recommendations/messages:** rich text internal recommendations and separate
   applicant message. Sending records communication; revisions preserve history
   without an automatic resend. Support private individual/both-party recipients.
9. **Decision/voting:** explicit decision type and grounds/reason before votes.
   All council members remain listed regardless of attendance. President can
   approve with or without votes; authorized recording on another's behalf keeps
   approver, recorder and timestamp. Revised type/grounds requires fresh approval.
10. **Decree:** only authorized admin/secretary prepare/manage certificate; case
    manager does not manage it. Appropriate type-specific template, president's
    digital signature or uploaded signed scan/PDF. Signed file required before
    issuance. Decree ID example `DCR-20261020-01`; English, Arabic or bilingual,
    with one bilingual certificate when both are selected.
11. **Closure/release:** issued decree closes case. Entitlement determines decree
    versus official decision notice. Certificate remains hidden until explicitly
    released; release notifies entitled recipient, permits PDF view/download.
    Erroneous portal release may be withdrawn with history. Petition Denied closes
    with official notice and no certificate. Replacement-decree orchestration was
    explicitly removed: do not build the earlier clerical replacement proposal.
12. **Withdrawal:** no approval. Single participant withdrawal closes; with two
    participating parties both must withdraw or a decision must close the case.
    Authorized staff can record on behalf of parties under the defined rules.

Use `prototype-decision-types.json` and the actual approved templates for decree
types/entitlements. Do not invent church law from Catholic sample forms.

## Reports, intakes and question bank

Reports are a council section with split list/detail (Outlook-style). Each intake
builds a saved report; follow-ups are separate reports linked to the original and
case, with their own identifier/date/status, also visible in the reports list.

The assigned case-manager priest selects questions, conducts the intake himself
or sends selected questions to the applicant. Foundation/identity questions are
included as specified. Organize by Topic groups and reusable Question categories;
do not confuse these two levels. Accepted current bank has59 primary English
questions and separately adopted context-sensitive guidance. Preserve exact
accepted wording; no generic helper rewrite or removed EVD accusation blocks.

Templates/questions support English/Arabic/both. Sent question sets are frozen;
draft template refresh follows the explicit approved behavior. Applicant can read
their own submitted answers read-only, not internal observations or other reports.
All authorized council members can read case reports. Edit authority follows
authorship; preserve revisions. Follow-up information belongs in a linked report.

External priest reports are distinct from applicant intake. Create request first;
it identifies the eventual response and attachments. Email capability link or
print a PDF for handwritten completion; upload original, retain OCR as derivative.
Link expires after30 days. Title convention includes priest name and completion
date; allow user-defined distinguishing text for multiple reports on one date.

Recording is optional and covers the entire report, not individual questions.
Future capture lives in reporting UI, supports mobile web and uploaded audio.
Transcription starts only after recording is finished/submitted. Retain original
audio, original AI output, corrections and reviewed translations. Mixed speech
keeps mixed original plus full English and Arabic. Review gates and editing rights
follow the approved contract. OCR/audio can remain honest demo placeholders.

## Professional Assessments

Medical/psychological requests and reports have a separate section. A signed
release with exact subject/request/scope gates access; this is not an ordinary
attachment category. Case manager can request reports and supply recommended
doctors. Preserve originals/history and server-side scope checks. Never leak
assessments through ordinary documents, report lists, search or AI processing.

## Appeals

Either applicant may file after closure without a deadline. Draft allowed; one
pending appeal per applicant per case. Each separately pays250 USD or receives an
authorized waiver. Application includes statement, new information and evidence.
Pending appeals leave original case/decree/release unchanged. Additions are
append-only supplements, not replacement of the original appeal statement.

Both parties' appeals share one case hearing agenda item, with individual
Accept/Decline outcomes. Original case manager presents unless president
reassigns. Acceptance reopens the original case/number as a new proceeding, with
prior proceedings preserved read-only. Decline leaves closed and sends an
automatic notice; additional explanation optional. Appeal may be withdrawn before
decision without refund. Later appeal decree example `DCR-20261020-01-A1` follows
normal decree rules. Do not create a second simultaneously open case.

## Files, communications and search

- Final filename direction: case number + document code + upload date/time HHMM;
  no applicant ID in filename. Keep ownership separately; enforce collision-safe
  internal identity using the contract. DCR identifies decrees; distinguish CDD.
- Accept replacements automatically, latest accepted default; retain submitted
  versions, council history only. Explicit wrong-file report exception must not
  become blanket permission to delete submitted case evidence.
- Ordinary limits: PDF/image/Word25 MB, video500 MB, audio100 MB; no count limit.
  Report/session recording exceptions are documented separately. Do not conflate.
- Documents belong in their contextual sections, never stored as message uploads.
  Private in-app and email conversation history; incoming email attachments are
  refused with portal-submission instructions, not ingested as evidence.
- Sending options exactly **Send Immediately** / **Send after council session**.
  The second is tied to session completion, not a fabricated fixed5pm scheduler.
- Calling is a manual call record, no phone dialer or call-recording integration.
- Council search covers open/closed cases and extracted English/Arabic content;
  latest file versions by default, optional history. Enforce source access before
  snippets/counts/downloads. Applicant isolation must hold through every surface.

## Locked council navigation

```text
Home
Tribunal Sessions
Cases
Search
Archived
Statistics and Reports

Within an opened case:
Back to Cases
Case Overview
  Summary / Timeline / Parties / Marriage / Separation
Communications
Case Review
  Petition / Reports / Hearings / Evidence / Documents / Professional Assessments
Decision
  Decision & Voting / Decree / Appeals
Case Audit
```

Cases are a workspace list/table, never individual entries inside navigation.
Reports/Search/Appeals use split list/detail; document/evidence/communications
patterns follow the approved interface contract. Use the documented Plenix avatar
menu pattern for profile/settings, not a permanent expanded account menu.

## Current implementation: verify, then extend

Implemented partial persistent services include drafts/versioned answers,
submission/payment gating, matching, assignments, council sessions/attendance,
reports/revisions, private communications/outbox, decisions/decrees/appeals and
file delivery. Existing APIs are in `tribunal/api.py` and `ctm/urls.py`; authorized
commands in `tribunal/services/`; models/migrations in `tribunal/`.

Browser UI already includes role routing, case lists, communications,
document/evidence split readers, report/revision reading, notifications and session
attendance. Many workflow editors are unfinished or destinations disabled.
Do not mistake endpoint presence for a completed usable workflow.

Real Microsoft login completed locally as Fr. Raphael Maher using
frraphaelmaher@lacopts.org. It uses preauthorized tenant/object identity, not email
alone. Current settings include `ACCOUNT_USER_MODEL_USERNAME_FIELD=None` for the
email-only account; preserve this callback fix. No CTM password system.

At the last completed baseline, PostgreSQL CI passed185 tests; a later12-test
subset validated the callback display fix. Check latest GitHub Actions rather
than assuming current totals. RLS is forced on23 tables, with remaining policies,
runtime grants and full151-table reconciliation unfinished. Production readiness
checks intentionally fail until real blockers are resolved. Do not remove them.

## Development and validation

Use the lockfile and existing commands; Linux PostgreSQL CI is authoritative.
Windows Python has shown intermittent native crashes. Do not spend hours retrying
those or claim they prove application failure. Use isolated Linux validation.

```sh
uv sync --frozen
uv run pytest -q
uv run python manage.py check --settings=ctm.settings_test
uv run python manage.py makemigrations --check --dry-run --settings=ctm.settings_test

# Set CTM_TEST_DATABASE_URL to an isolated disposable PostgreSQL database first.
uv run pytest --ds=ctm.settings_postgres_test -q

uv sync --frozen --group browser
uv run --group browser playwright install chromium
uv run --group browser python scripts/browser_integration.py
```

`browser_smoke.py` uses synthetic API fixtures; `browser_integration.py` uses real
Django APIs with isolated synthetic records and test-issued sessions. Neither is
a real provider-login acceptance test. The separately verified Microsoft callback
is genuine OAuth. Keep this distinction in reports.

Never use `ctm.settings_test`/`settings_postgres_test` publicly. Their relaxed
transport/scan settings are isolated-test settings. Use disposable database users
with appropriate pytest permissions; never run pytest against operational data.

## Infrastructure — context, not deployment authorization

Reported/previously inspected CTM VM: Proxmox VM107, Debian12,8vCPU,16GB RAM,
120GB disk,10.0.0.40/22. SSH alias `ctm` is available on the governance PC; your
session may not have its key. Never copy private keys or ask for secrets in GitHub.

Public DNS/TLS and NPM proxy host30 point ctm.lighthouseway.org to10.0.0.40:8000.
At last verification the application was not serving there;502 was expected.
Recheck current state before infrastructure conclusions. Local review port18844
is an isolated OAuth server, not the production deployment.

Deployment code lives under `deploy/`: Compose, Dockerfiles, private storage
initialization, environment example and PostgreSQL role initialization. Keep
runtime app/worker roles least-privileged and ingress restricted. Existing secrets
stay in protected VM files/process environment; never print or commit them.
Azure/private-server relocation remains a deployment requirement, not a mandate
to rebuild on Azure-managed services now.

## First practical slice for Claude

1. Inspect current council endpoints/components and issue3 dependencies.
2. Post your concrete slice and proposed shared-shell hook on issue3.
3. Build completeness review/return UI against existing services, then session
   assignment/hearing actions. Follow with report intake authoring and decision/
   decree screens, delivering usable increments rather than a giant rewrite.
4. If backend contract is missing, post the exact dependency to issue2 and keep
   working on independent council UI; do not add fake successful responses.
5. Push your branch and draft PR linked to issue3, with screenshots/test evidence,
   affected files, remaining work and risks. Governance handles review/integration.

No real charges, case emails, real case-data processing, operational migrations
or public exposure are part of synthetic development acceptance.
