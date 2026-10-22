# Western-name workflow review dataset

Dataset: `ctm-western-workflow-demo-v1`. User-requested fictional applicants and
documents, with the supplied real council display roster. All case events,
findings, votes, approvals, notices and certificate samples are fictional fixtures,
not actions taken by the named clergy. PDF originals say DEMO - NOT VALID. The
certificate's signature is explicitly a placeholder, not a real signature.

Loaded into the isolated local Microsoft-review SQLite database, visible at
http://localhost:18844/ after genuine Microsoft login. Not loaded into the
operational PostgreSQL database or public site. Existing Microsoft subject and
credentials are preserved; other staff display profiles have no linked Microsoft
subject and no usable CTM password. No invitations are sent.

| Case | Fictional couple | Scenario |
| --- | --- | --- |
| 20261020-01 | James Carter / Emily Carter | Submitted, awaiting completeness review |
| 20261020-02 | Daniel Brooks / Olivia Brooks | Returned, explanation to upload a legible certificate |
| 20261020-03 | Michael Bennett / Charlotte Bennett | Accepted, agenda Part1 awaiting assignment |
| 20261020-04 | William Hayes / Amelia Hayes | Assigned investigation, both filings, interview report, document versions |
| 20261020-05 | Benjamin Parker / Sophia Parker | Assigned case on upcoming hearing agenda |
| 20261020-06 | Alexander Reed / Grace Reed | Hearing record, decision and sample votes awaiting approval |
| 20261020-07 | Henry Collins / Isabella Collins | Closed, sample decree with explicit demo release |
| 20261020-08 | Samuel Morgan / Victoria Morgan | Closed denied case with pending appeal and supplement |

Thomas Wilson has an additional private unfinished draft. Applicant email domains
are reserved `.example.test`, and photos are generated neutral placeholders,
not real-person photographs. Each applicant participates in at most one open case.

Initial loaded counts:8cases,26accounts (9staff +17fictional applicants),12applications,
48file versions,2reports,3decision revisions,1sample decree,0outbox deliveries.
There are6open and2closed cases. The supplied bishop is president, Fr.Mauritius
Mikhail is secretary, Fr.Raphael Maher is admin, and the six other supplied priests
are members. Display spacing was normalized; emails are case-insensitively matched.

## Execution and boundaries

`seed_workflow_demo` requires `CTM_SYNTHETIC_DEMO=true`, test environment and SQLite.
It refuses non-demo cases and does not edit existing staff roles/credentials.
Repeat runs are no-ops after the dataset audit marker. It creates marked workflow
snapshots directly; this is not a service transition or payment/antivirus test.
Published miniature questionnaire/declarations are explicitly fictional demo
content, not institutional approval of the full applicant form or translations.
The accepted59-question council bank is unchanged.

To load an existing isolated review DB:

```sh
python scripts/seed_review_database.py .tmp/<review-directory>/isolated.sqlite3
```

The wrapper refuses files outside this repository's ignored `.tmp`, nonexistent
databases or a different filename. It does not run migrations against an arbitrary
database. Media lives beside that isolated DB. Sample file clearance has explicit
test-policy metadata and is not evidence of real antivirus scanning. No provider
payments, outbound emails, transcription or OCR are simulated as external success.

The local OAuth tool now retains its review DB and local session-signing key across
restarts. Provider credentials still enter process memory over protected SSH stdin,
not disk or command arguments. Set CTM_LOCAL_REVIEW_DIR to a directory within .tmp
to reopen an existing review dataset; otherwise it uses .tmp/local-microsoft-review.

Tests cover explicit opt-in, repeatability, real PDF structure, no outbox deliveries,
unusable passwords, no automatically linked Microsoft identities, report snapshot
keys and refusal to mix with non-demo cases. Positive seed execution is SQLite-only;
PostgreSQL test runs deliberately skip that fixture test.

## Presentation update

At the user's request, current display text now reads like live case content: report titles, statements, notes, communications and correction instructions omit DEMO labels. Newly generated document previews use ordinary titles with an unsigned-preview footer. Existing PDF originals remain preserved; updated ordinary-file previews are new versions. Existing sample decree/signature provenance is not promoted to a real signed certificate. Internal synthetic metadata, the isolated database and no-delivery policy remain intact. This is a presentation change, not public deployment or approval of institutional declarations.
