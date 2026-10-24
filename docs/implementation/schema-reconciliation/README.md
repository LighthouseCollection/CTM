# Schema reconciliation: 151 approved tables vs. the Django implementation

Independent, read-only check of how much of the approved database contract the
backend implements. Requested by governance (#4). Related: #14 (PA27/PA28, full
schema equivalence) and backend issue #2. Documentation only: no migrations, code,
database, Docker or protected build-spec files were touched.

**Result at backend `db82099`: 3 tables implemented, 110 partial, 37 missing,
1 decision needed. 12 are P1, 73 P2, 66 P3.** The 151-table contract stands.
"Partial" usually means the data is stored, but in a combined table or a JSON
field, without the approved history, provenance or constraints.

## Pinned sources

| What | Ref | Notes |
| --- | --- | --- |
| Backend head (analysed) | PR #7 `work/vm-frm-backend` @ `db820990dd2fc15e80560bd630d90ec9b22276e5` | 63 models, migrations through 0039 |
| Integration | PR #16 `governance/integration-20261021` @ `8572195b45bbd5e5b533fc80ae3e03c222602327` | `tribunal/models.py`, `tribunal/migrations/`, `tribunal/services/`, `tribunal/policy.py` and the build spec are byte-identical to `db82099`. The findings apply to both. |
| main | `b38e70a15b85c0c28f98515ddcd73f5c48ebdf05` | 58 models, forced RLS on 23, migrations through 0012. Far behind; not analysed further. |
| Approved contract | `docs/architecture/build-spec/schema.json`, version `ctm-build-contract-2026-10-21-v1` | Identical on main and backend (checked by the script). |
| Applicant mapping | PR #5 @ `1d20bfa353fb1d0e2ef0818f0fd3f14596c754d7`, `docs/implementation/applicant/schema-reconciliation/` | Its comparison is pinned to older backend `d724ba5`. |

Other sources used: `data-dictionary.md`, `permissions.md`,
`transactions-and-acceptance.md`, `interface-contract.md`,
`docs/implementation/reviews/owner-clarifications-2026-10-21.md`, and owner
decisions posted on #4 and #14 up to 2026-10-22 06:35 UTC.

## Files

| File | Contents |
| --- | --- |
| [`matrix.csv`](matrix.csv) / [`matrix.json`](matrix.json) | One row per approved table (151): status, priority, adapter model and `models.py` line, column counts (exact/alias/missing), missing columns, constraint gaps, history and permission gaps, forced-RLS coverage, and a check of the backend's own claim for that table. |
| [`evidence.json`](evidence.json) | Per approved column: which adapter field matches it (exact or alias) and its Django definition. Per adapter: forced-RLS migration, DB triggers and runtime grants. |
| [`backend-gap-list.md`](backend-gap-list.md) | Gaps the backend stream (#2) can act on, with priority. Draft for #2. Not posted. |
| [`curation.json`](curation.json) | Reviewer judgment per table (status, priority, aliases, gap text). |
| [`reconcile.py`](reconcile.py) | Regenerates the matrix from the pinned refs. |

Regenerate (static and read-only; uses `git show`, no Django import, no DB):

```bash
python docs/implementation/schema-reconciliation/reconcile.py --backend-ref db820990dd2fc15e80560bd630d90ec9b22276e5 --main-ref b38e70a15b85c0c28f98515ddcd73f5c48ebdf05
```

## Method

1. Parse `schema.json` (151 tables, 1,235 columns, 55 CHECK and 104 UNIQUE
   constraints or indexes).
2. Parse `tribunal/models.py` with Python `ast`: models, `db_table`, fields,
   FK targets, `Meta.constraints`, `Immutable` base class.
3. Scan `tribunal/migrations/*.py|*.sql` for forced RLS (`FORCE ROW LEVEL SECURITY`
   and the `MODELS` list it loops over), triggers (including loop-installed
   `immutable_update` and `preserve_history` from 0002/0007/0009/0016), and
   0038 runtime grants (`ctm_app` / `ctm_worker`).
4. For each approved table, choose the model(s) that hold its data today. Alias
   columns only where the field holds the same fact under another name. Each
   alias was read in `models.py`, and every alias in `curation.json` resolves.
5. Read the services where storage alone does not answer the question: identity
   overwrite, file delivery auditing, search, sessions, retention, configuration,
   reports and payments.
6. Check each row of the backend's `docs/implementation/schema-reconciliation.json`
   and the summary documents.

Status meanings: **implemented**: every approved column maps, and the key
constraints, history and RLS are present. **partial**: an adapter stores some or
all of the data, but columns, constraints, history or typed relations are
missing. **missing**: nothing in the database stores it. **decision needed**:
sources conflict or an owner answer is missing. Priority meanings: **P1**
privacy, security or data loss. **P2** blocks a workflow. **P3** completeness.

**Verified versus inferred.** 141 rows are `verified_in_code`: the model,
migration or service was read at the pinned SHA. 10 rows are `inferred` from
model shape plus the absence of a matching model or service: `case_lifecycle_events`,
`draft_schema_migrations`, `file_name_events`, `upload_sessions`,
`template_publication_submissions`, `report_source_links`, `appeal_withdrawals`,
`notification_batches`, `translation_prompt_versions` and `ui_resource_versions`.
Nothing was executed, so runtime behaviour (policy predicates, service guards) is
claimed only where code was read. RLS policy *predicates* were not audited for
correctness; that remains QA/backend acceptance work.

## Summary

| Domain | Tables | Implemented | Partial | Missing | Decision |
| --- | --- | --- | --- | --- | --- |
| identity | 16 | 2 | 7 | 7 | 0 |
| cases | 15 | 0 | 13 | 2 | 0 |
| filings | 21 | 0 | 18 | 2 | 1 |
| files | 11 | 0 | 7 | 4 | 0 |
| payments | 6 | 0 | 5 | 1 | 0 |
| reports | 22 | 0 | 17 | 5 | 0 |
| medical | 6 | 0 | 4 | 2 | 0 |
| review | 4 | 0 | 4 | 0 | 0 |
| sessions | 11 | 1 | 9 | 1 | 0 |
| decisions | 10 | 0 | 8 | 2 | 0 |
| appeals | 7 | 0 | 6 | 1 | 0 |
| communications | 11 | 0 | 7 | 4 | 0 |
| operations | 11 | 0 | 5 | 6 | 0 |
| **Total** | **151** | **3** | **110** | **37** | **1** |

Columns: 1,235 approved. 410 match exactly, 185 match an aliased adapter field,
and 640 have no adapter column. Many of the 640 are stored in JSON, for example
the application assertions in `AnswerRevision.answers`.

What is solid: all 63 adapter tables have forced RLS (statically confirmed).
Every `Immutable` model has a database update trigger. History tables are
append-only. Runtime grants go to existing non-owner roles only (0038).

## P1 gaps (privacy, security, data loss)

| # | Table | Gap | Evidence |
| --- | --- | --- | --- |
| 1 | `person_identity_versions` / `persons` | Filing overwrites `Person.first_name/last_name/birth_date/gender` in place, with no identity version, actor or request. Prior values are lost for staff and historical entries. | `tribunal/services/applications.py:434-439` |
| 2 | `app_sessions` | Django's default database session store keeps the **raw** session key, not `session_hash`. Sessions have no account, provider-identity or revocation columns, and `django_session` has DML grants to `ctm_app` without forced RLS. | `ctm/settings.py` (no `SESSION_ENGINE`), `0038_runtime_grants.py` |
| 3 | `account_identities` | Provider binding is `Account.microsoft_subject` plus allauth `socialaccount_*`. There is no issuer, tenant, revocation or link-time row, and no `UNIQUE(issuer,subject)`. allauth tables have no forced RLS. | `models.py:122,128-134`, `0038` |
| 4 | `decree_entitlements` | Per-party certificate vs. notice-only entitlement exists only in `DecisionRevision.entitlements` JSON. There is no typed row or `UNIQUE(decree_id,party_id)`. The owner (D7) requires explicit per-party entitlements. | `models.py:728` |
| 5 | `decree_release_events` | `DecreeRelease` works per party but has no FK to an entitlement or certificate and no action CHECK. | `models.py:768-772` |
| 6 | `evaluation_release_attestations` | `MedicalRelease` has no exact text, language or purpose, and its subject is an Account, not a person. The approved subject = signer CHECK cannot be expressed. | `models.py:687-693` |
| 7 | `evaluation_release_scopes` | Release scope is JSON. Disclosures cannot reference the exact scope applied. | `models.py:692` |
| 8 | `evaluation_reports` | No stored authorization state, kept separate from receipt and OCR readiness. Medical reports are plain `Report` rows. | `models.py:619-624` |
| 9 | `evaluation_disclosures` | No disclosure log. Generic `file_viewed`/`file_downloaded` audit rows do not record the release scope. | `tribunal/file_delivery.py:104-108` |
| 10 | `external_report_links` | The token hash and 30-day expiry are on `ReportRequest`. Reissuing a link overwrites the hash, so revocation and use history are lost. | `tribunal/services/reports.py:145-146` |
| 11 | `declaration_versions` | Declaration wording is embedded in `QuestionnaireVersion` (and reused for the medical release). There is no independent identity, digest or publisher for the exact signed wording. | `models.py:223-236` |

## Top P2 gaps (workflow-blocking)

- **Typed application facts.** All 13 assertion, repeat and answer tables are
  JSON inside `AnswerRevision.answers`. This blocks building the owner-approved
  shared factual overview with discrepancy flags (#14, 2026-10-22) and PA01–PA05
  on typed data.
- **Decree production.** `decision_types` and `decree_template_versions` are
  missing (PA23). `decrees` lacks `UNIQUE(proceeding_id)`: the decree is
  one-to-one with a decision *revision*, so two revisions of one proceeding could
  each get a decree.
- **Payments.** `payment_allocations` is missing. `CheckoutIntent` serves as both
  filing candidate and payment attempt. Refunds have no authorizing actor or
  reason.
- **Communications.** There are no inbound email routes, receipts or delivery
  events, and no external recipients or subject (PA21). Outbox rows are not
  linked to the recipient or notification they deliver.
- **Sessions and hearings.** `agenda_requests` is missing. `case_hearings` has no
  `occurred_at` or result. Hearing outcomes are unversioned and not linked to the
  applicant message sent. `hearing_appeals` is missing.
- **Identity workflow.** There are no identity consolidations, duplicate-hold
  resolution provenance, case-association evidence or email history. One draft
  or open case is enforced per *account*, not per canonical *person*.
- **Search.** There is no `search_documents` provenance, so the Meilisearch index
  cannot be rebuilt or reconciled from the database.
- **Integrations.** Provider configuration comes from environment variables.
  There are no `integration_configurations` rows with secret references.

## Cross-cutting gaps

| ID | Gap | Scope |
| --- | --- | --- |
| X1 | `request_id` correlation missing | 40 of the 42 attributed tables that carry it. Present only on `agenda_transfer_events` and `testimony_appointment_versions`. (`request_id` on `external_report_links` and `reports` is an FK to `report_requests` and is mapped.) |
| X2 | `row_version` missing | 8 of 8 tables (persons, accounts, cases, applications, files, document_categories, report_requests, reports). Services use `expected_version` against revision numbers or counters instead. |
| X3 | Staff references point at `Account`, not `staff_memberships` | case_assignments, council_votes, presidential_approvals, case_hearings, session/hearing attendance, report_templates, text_review_events, decree_certificates. The membership and role in force at action time is not captured. `Account.role` also duplicates `StaffRole`. |
| X4 | `digest` missing | 9 of 9 (questionnaire, declaration, application revision, submission, template, report revision, decree template, translation prompt, UI resource versions). |
| X5 | Enumeration CHECKs mostly absent | 73 constraint gaps are recorded across 151 rows. Most enumerations are only Django `choices` or service checks, with no DB CHECK. Some vocabularies differ: `Attachment.visibility='own'` vs. `applicant_own`, and `ReportRequest.kind='intake'` vs. `applicant_intake`. |
| X6 | Framework tables outside RLS | `django_session`, `socialaccount_*` and `account_emailaddress` get DML from 0038 to `ctm_app` with no forced RLS. These are app-only, but they hold session and provider identity data (see P1 #2 and #3). |

## Backend inventory check

The backend's `schema-reconciliation.json` at `db82099` maps each of the 151
tables to candidate adapters (122 mapped, 29 unmapped). Per-row verdicts are in
the matrix (`backend_claim_verdict`):

| Verdict | Rows | Meaning |
| --- | --- | --- |
| confirmed | 75 | Candidate and missing columns are accurate. |
| confirmed_with_name_only_noise | 45 | The gap is real, but some "missing" columns exist under another name. 185 such columns overall. |
| wrong_adapter | 14 | The named candidate does not hold the data. Examples: `account_events` is in `AuditEvent`, not `Account`. `decree_entitlements` is in `DecisionRevision` JSON, not `Decree`. `evaluation_disclosures` is not in `MedicalRelease`. `integration_configurations` is env vars, not `SettingRevision`. Also `agenda_requests`, `hearing_appeals`, `appeal_withdrawals`, `delivery_events`, `report_source_links`, `file_name_events`, `payment_allocations`, `registration_invitation_events`, `template_publication_submissions`, `case_lifecycle_events`. |
| incomplete | 10 | Marked unmapped or complete, but a partial adapter or a constraint gap exists: `app_sessions`, `account_identities`, `identity_review_holds`, `file_access_events`, `question_categories` (unmapped but partially stored), `staff_memberships`, `testimony_appointment_versions`, `session_agenda_items`, `session/hearing_attendance` (complete-looking but missing constraints). |
| false_gap_name_only | 6 | Listed gaps are alias-only: `persons.canonical_person_id`, `accounts` locales and status, `marriages` DOB bounds, `fee_obligations`, `notifications`, `system_setting_versions`. The backend's prose review already says this, so the JSON is inconsistent with it. |
| unverified | 1 | `translation_prompt_versions` → `SettingRevision`: no such setting key was found. |

Other backend claims:

| Claim | Source | Verdict |
| --- | --- | --- |
| 63 domain models | `model-inventory.json`, `vm-frm-progress.md` | **Confirmed** (63 non-abstract models in `models.py`). |
| 63/63 tables have forced RLS | `backend-status.md`, `core-policy-completion.md` | **Confirmed statically**: union of `MODELS` lists in 0011–0037 forced-RLS migrations plus explicit tables (CallRecord 0025, PendingPartyLink 0029, CaseNumberCounter 0031) = 63. |
| Only new migrations 0036/0037/0038 in that delivery | `schema-gap-review.md` | **Confirmed** (0039 added later for the filing snapshot guard). |
| "forced RLS on 23 private-source and council tables" | `status.md:53` | **Stale** (now 63). |
| `implemented_domain_models: 58` | `validation-results.json` | **Stale** (now 63). |
| Gap families in `schema-gap-review.md` (identity versions, account/provider history, marriage/related facts, case/party history, typed questions, typed citations, institution scope, delivery associations) | `schema-gap-review.md` | **Confirmed**. This review adds concrete items it does not name: raw session key, `staff_current_account` index, `decrees UNIQUE(proceeding_id)`, the Person overwrite path, and the enumeration CHECKs. |

Applicant mapping (PR #5, AS01–AS08), against current backend `db82099`:
AS01–AS08 are **confirmed** at the current backend. Their table targets are
still unimplemented in the same way. Its counts (101 tables / 839 columns, 37
with candidates) were computed against `d724ba5`, before 0028–0039. The new
migrations added constraints and guards, not new approved tables, so the
table-level conclusions still hold. The column counts were not re-derived.

## Decisions needed

**DN-1: where later spouse filings against a closed case live.**
- Owner D3 (`owner-clarifications-2026-10-21.md`): "A spouse who did not
  previously file may submit against the closed case. It goes to the queue …
  Acceptance based on new information reopens the original case, similar to
  appeals."
- `schema.json` `applications`: `CHECK(purpose IN ('petition','appeal'))`.
  `appeal_applications` requires `challenged_decision_id`/`challenged_decree_id`.
- Implementation: `Application.origin='closed_case_intake'`, a third shape that
  is neither (`models.py:249,271-275`).

Question: should this filing be stored as an `appeal_applications` row (purpose
`appeal`), or does the contract need another purpose? Normalizing `applications`
and the appeal tables waits on this answer.

**DN-2: who records a party withdrawal** (matrix status `decision_needed`:
`party_withdrawals`).
- `data-dictionary.md`: "Own petition withdrawal; admin may act for all; no
  reason or approval."
- Owner D5: "if they both agree to withdraw yes" … "do not infer permission for
  unilateral withdrawal on behalf of another person." The same document lists
  "joint-secretary withdrawal authority" as an open question.

Question: does `on_behalf` stay admin-only? How is joint agreement recorded: two
rows, or a link? Can a secretary record it?

**DN-3: council session time, location and presiding member.** Prototype audit
PA16 (#14, P1): "Session timing/location/presiding metadata lacks explicit
storage." Approved `council_sessions` has only `session_date`, `reference`,
`state`, `created_by_id` and `closed_at`. #14 also says "Missing UI does not
automatically require new tables." Question: add these columns to the contract,
or drop them from the UI? The row stays `partial` because the defined columns are
mostly present.

**DN-4: profile photo.** #14 addendum: "the reported unsupported photo
field/mapping is unresolved. Do not … reuse case evidence storage without an
explicit approved ownership/access mapping." No approved table holds an account
portrait. The applicant and spouse photos in `CTM-build-specification.md:80` are
filing documents (`files`). An owner mapping is needed before any migration.
This has no matrix row.

**DN-5: answer states.** #14 (2026-10-22): "Detailed equality/unknown and
correction-source behavior still need specification before implementation."
`application_answers.answer_state` and the `answer_states` JSON columns on the
assertion tables need these semantics before normalization.

**DN-6: natural-key exceptions.** `case_number_counters` (date PK) and
`person_open_case_claims` (person PK) have no UUID `id`/`created_at`, which the
contract requires on every table. The backend asks for an explicit contract
exception. Governance should accept the exception or require the columns.

## Limitations

- Static read only. No migration, test or query was run. Trigger and grant
  detection uses literal SQL plus the known loop lists; a trigger built entirely
  dynamically could be missed. None was found by manual reading.
- "Implemented" is a schema judgment. It is not acceptance of the policy
  predicates or the UI.
- Aliases are semantic judgments by this reviewer. Each one is listed in
  `curation.json` for challenge.
- No real personal data is used. The repository and this output contain
  fictional or no data.
