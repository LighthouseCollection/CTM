# Applicant schema reconciliation: ten batches

Source comparison at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`. Approved contract: `ctm-build-contract-2026-10-21-v1`.

Reviewed **101 contract tables / 839 columns** across ten applicant workflows and their shared dependencies. The remaining 50 contract tables are explicitly listed outside scope in JSON. All 63 domain model names were checked against backend source.

**37 tables have explicit adapter model candidates; 64 have no standalone model mapping.** Of 839 columns, 226 have column candidates and 613 have no direct column mapping. 33 mapped candidates have type, nullability, primary-key or relation-target differences. These are source reconciliation counts, not missing-feature counts or a completion percentage.

JSON, consolidated roots and framework models may implement behavior without the required physical structure. No column is marked parity verified. The report does not recommend duplicating tables or replacing working services without an owner-reviewed migration plan.

[Download full JSON](result.json) · [Download field CSV](field-mapping.csv) · [Explicit mappings](mapping.json) · [Validation snapshot](validation.json)

| Batch | Workflow | Tables | Columns |
| --- | --- | --- | --- |
| 1 | [Identity and case ownership](identity.md) | 27 | 198 |
| 2 | [Questionnaires, declarations and question wording](forms.md) | 6 | 43 |
| 3 | [Draft answers, assertions and repeat identity](drafts.md) | 13 | 136 |
| 4 | [Private originals, context and provenance](files.md) | 11 | 103 |
| 5 | [Filing snapshots, completeness and withdrawal](filing.md) | 6 | 50 |
| 6 | [Fees, checkout candidates and financial history](payments.md) | 6 | 45 |
| 7 | [Private testimony invitations](appointments.md) | 3 | 26 |
| 8 | [Own requests, responses and medical consent](requests.md) | 12 | 115 |
| 9 | [Appeal entry, additions and disposition](appeals.md) | 7 | 42 |
| 10 | [Decision provenance and released certificates](decrees.md) | 10 | 81 |

## Prioritized findings

Priorities describe blockers to full contract/integration acceptance; they are not vulnerability severity ratings. Only AS09 is identified here as a currently blocked frontend integration. Other findings require schema/content reconciliation and preserve the scope of passing behavior tests.

### AS01 — P1 — Separate identity, marriage and ownership records

Classification: `reconciliation_required`.

Current Person/Account/Case/Party adapters consolidate identity, marriage matching and issued references. The contract requires separate versioned identity, applicant, marriage and reference relations; person ownership on applications is not a direct adapter column. This is not a finding that current own API privacy is broken.

Targets: `applications.owner_person_id`, `person_identity_versions.person_id`, `marriages.id`, `applicant_references.issued_components`.

Evidence: [docs/architecture/build-spec/schema.json:1871](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L1871), [docs/architecture/build-spec/schema.json:76](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L76), [docs/architecture/build-spec/schema.json:886](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L886), [docs/architecture/build-spec/schema.json:1180](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L1180), [tribunal/models.py:71](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L71), [tribunal/models.py:104](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L104).

Next action: Backend/governance: map stable person/account/applicant ownership, canonical aliases and immutable reference history before accepting full schema parity. Review allauth/session tables separately.

### AS02 — P1 — Published questionnaire and declaration provenance

Classification: `content_and_schema_dependency`.

QuestionnaireVersion combines questionnaire definition and bilingual declaration text. Separate questionnaire/declaration version identities, digests and publication provenance are not direct mapped columns. The reference seed inventory is not a complete approved bilingual applicant form.

Targets: `questionnaire_versions.digest`, `declaration_versions.text_ar`, `ground_definitions.label_ar`.

Evidence: [docs/architecture/build-spec/schema.json:1769](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L1769), [docs/architecture/build-spec/schema.json:1825](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L1825), [docs/architecture/build-spec/schema.json:2622](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2622), [tribunal/models.py:223](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L223), [scripts/audit_applicant_forms.cjs:3](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/scripts/audit_applicant_forms.cjs#L3).

Next action: Institution supplies approved bilingual definitions; backend maps immutable declaration identity/digest/publication. Run technical form audit on exact bound production candidates; never synthesize approval from test wording.

### AS03 — P1 — Typed assertions and stable repeat-entry relations

Classification: `reconciliation_required`.

The adapter retains immutable AnswerRevision.answers JSON and client repeat UUIDs. Thirteen draft-related contract tables include typed person/marriage/separation assertions, repeat entries, answers and attributed changes. JSON presence does not prove field coverage, normalized relations or backend nested-repeat validation.

Targets: `application_revisions.digest`, `application_person_assertions.revision_id`, `application_children.entry_id`, `application_restraining_orders.entry_id`, `application_answer_changes.question_code`.

Evidence: [docs/architecture/build-spec/schema.json:1998](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L1998), [docs/architecture/build-spec/schema.json:2028](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2028), [docs/architecture/build-spec/schema.json:2343](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2343), [docs/architecture/build-spec/schema.json:2405](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2405), [docs/architecture/build-spec/schema.json:2723](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2723), [tribunal/models.py:279](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L279), [static/ctm/applicant.js:88](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant.js#L88).

Next action: Backend owns typed schema/repeat validation and migration mapping. Reconcile every accepted question and repeat path to its assertion/entry relation, preserving source versions and unknown draft fields.

### AS04 — P1 — Context, manifest and derivative relations

Classification: `reconciliation_required`.

Attachment.context and Submission.manifest provide tested adapter behavior. Separate contextual links, relational submission manifest, derivative and access-event structures are not established by the mapped columns. Existing clean-byte and retained-link tests remain valid within their recorded scope.

Targets: `files.owner_party_id`, `file_context_links.repeat_entry_id`, `submission_file_manifest.file_version_id`, `file_derivatives.source_version_id`, `file_access_events.correlation_id`.

Evidence: [docs/architecture/build-spec/schema.json:3142](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3142), [docs/architecture/build-spec/schema.json:3359](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3359), [docs/architecture/build-spec/schema.json:3421](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3421), [docs/architecture/build-spec/schema.json:3586](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3586), [docs/architecture/build-spec/schema.json:3677](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3677), [tribunal/models.py:370](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L370), [tribunal/models.py:298](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L298).

Next action: Map exact source/version/context/repeat relations and derivative/access retention under backend ownership; preserve current scan gates and private bytes. Independently accept physical storage cleanup and live antivirus.

### AS05 — P1 — Filing candidate and submission provenance

Classification: `reconciliation_required`.

CheckoutIntent is a candidate for filing_candidates while also serving as the payment-attempt adapter. Submission retains revision, manifest, attestation and idempotency key, but the contract candidate/declaration/signature/previous-submission links and standalone withdrawal events are not direct mapped columns.

Targets: `filing_candidates.idempotency_key`, `application_submissions.candidate_id`, `application_submissions.declaration_version_id`, `application_submissions.signature_file_version_id`, `party_withdrawals.on_behalf`.

Evidence: [docs/architecture/build-spec/schema.json:2779](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2779), [docs/architecture/build-spec/schema.json:2836](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2836), [docs/architecture/build-spec/schema.json:2848](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2848), [docs/architecture/build-spec/schema.json:2854](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L2854), [docs/architecture/build-spec/schema.json:3045](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3045), [tribunal/models.py:337](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L337), [tribunal/models.py:298](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L298), [static/ctm/applicant-lifecycle.js:11](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant-lifecycle.js#L11).

Next action: Backend/governance reconcile candidate and receipt identities, immutable signing evidence and withdrawal audit relations. Keep completed version checks and single-attempt UI; do not re-enable actions from status alone.

### AS06 — P1 — Separate payment attempts, allocations and refunds

Classification: `reconciliation_required`.

FeeObligation, CheckoutIntent and PaymentEvent retain adapter financial history. Explicit obligation/candidate/attempt/submission allocation and independently attributed waiver/refund rows are not fully mapped. Current retained checkout recovery tests use controlled provider output, not a charge or callback acceptance.

Targets: `payment_attempts.obligation_id`, `payment_attempts.candidate_id`, `payment_allocations.submission_id`, `fee_waivers.reason`, `refund_events.provider_refund_id`.

Evidence: [docs/architecture/build-spec/schema.json:3878](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3878), [docs/architecture/build-spec/schema.json:3884](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3884), [docs/architecture/build-spec/schema.json:4010](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L4010), [docs/architecture/build-spec/schema.json:3850](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L3850), [docs/architecture/build-spec/schema.json:4063](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L4063), [tribunal/services/payments.py:45](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/services/payments.py#L45), [tribunal/services/payments.py:134](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/services/payments.py#L134), [static/ctm/applicant-recovery.js:12](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant-recovery.js#L12).

Next action: Resolve shared CheckoutIntent mapping before migration; reconcile allocation and verified refund provenance. Separately test provider login/payment callbacks and PostgreSQL races, keeping unresolved holds authoritative.

### AS07 — P2 — Invitation responses reference a version by number

Classification: `reconciliation_required`.

TestimonyAppointmentVersion is a named table candidate. AppointmentResponse stores appointment_id plus integer version, while the contract response references appointment_version_id and party_id. Actual invitation version/stale-response tests pass; exact relational FK/provenance parity remains unverified.

Targets: `testimony_invitation_responses.appointment_version_id`, `testimony_invitation_responses.party_id`, `testimony_appointments.created_by_id`.

Evidence: [docs/architecture/build-spec/schema.json:6561](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L6561), [docs/architecture/build-spec/schema.json:6567](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L6567), [docs/architecture/build-spec/schema.json:6448](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L6448), [tribunal/models.py:834](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L834), [static/ctm/applicant-appointments.js:20](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant-appointments.js#L20).

Next action: Backend maps composite adapter version identity to immutable version-row FK and party provenance. Preserve narrow own response projection and independently accept PostgreSQL invitation policies/delivery.

### AS08 — P1 — Clinical release and report schema remain consolidated

Classification: `reconciliation_required`.

ReportRequest.questions, ReportRevision.answers and MedicalRelease.scope implement tested bound own responses and strict disclosure scope. Separate sent-question, evaluation request, release attestation/scope/report/disclosure entities remain adapter/storage candidates. Exact institutional declaration approval is still external to schema or synthetic tests.

Targets: `sent_intake_question_snapshots.source_question_version_id`, `evaluation_release_attestations.exact_text`, `evaluation_release_scopes.attestation_id`, `evaluation_reports.authorization_state`, `evaluation_disclosures.release_scope_id`.

Evidence: [docs/architecture/build-spec/schema.json:4648](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L4648), [docs/architecture/build-spec/schema.json:5585](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L5585), [docs/architecture/build-spec/schema.json:5625](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L5625), [docs/architecture/build-spec/schema.json:5697](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L5697), [docs/architecture/build-spec/schema.json:5744](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L5744), [tribunal/models.py:678](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L678), [tribunal/services/request_contracts.py:46](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/services/request_contracts.py#L46), [static/ctm/applicant-assessments.js:34](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant-assessments.js#L34).

Next action: Map retained declaration/version/file/person/purpose/recipient provenance to clinical contract entities; obtain institutional wording approval. Preserve exact consent matching, own privacy and current closure/replay safeguards.

### AS09 — P1 — Own supplement history and capability are absent

Classification: `blocked_frontend_integration`.

Actual owner-only supplement POST is verified, but current own application detail does not project supplements or can_supplement. Applicant Supplements requires both, so it intentionally remains unavailable against this backend. The append endpoint has no idempotency key; blind retry could duplicate an addition. Separate appeal root/claim/disposition links also need schema mapping.

Targets: `appeal_supplements.appeal_id`, `appeal_supplements.request_id`, `appeal_applications.challenged_decree_id`, `pending_appeal_claims.person_id`.

Evidence: [docs/architecture/build-spec/schema.json:7312](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7312), [docs/architecture/build-spec/schema.json:7307](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7307), [docs/architecture/build-spec/schema.json:7221](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7221), [docs/architecture/build-spec/schema.json:7263](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7263), [tribunal/api.py:87](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/api.py#L87), [tribunal/services/decisions.py:325](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/services/decisions.py#L325), [static/ctm/applicant-supplements.js:7](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant-supplements.js#L7).

Next action: Backend supplies private own attributed supplement history and authoritative can_supplement plus interruption/recovery semantics. Applicant then integrates actual read/append/recovery; do not infer permission from submitted status or automatically retry.

### AS10 — P1 — Certificate, entitlement and issuance identities

Classification: `reconciliation_required`.

Decree stores decision/reference/language/signed original/signer/issued time; DecreeRelease stores decree/party/action. Own release and withdrawal byte tests pass. The contract separates certificate, issuance event, entitlement and release identities; those are not established by one decree model or a successful download.

Targets: `decrees.template_version_id`, `decree_certificates.signature_metadata`, `decree_issuance_events.approval_id`, `decree_entitlements.entitlement`, `decree_release_events.certificate_id`.

Evidence: [docs/architecture/build-spec/schema.json:6939](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L6939), [docs/architecture/build-spec/schema.json:7006](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7006), [docs/architecture/build-spec/schema.json:7065](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7065), [docs/architecture/build-spec/schema.json:7113](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7113), [docs/architecture/build-spec/schema.json:7161](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/docs/architecture/build-spec/schema.json#L7161), [tribunal/models.py:740](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L740), [tribunal/models.py:749](https://github.com/LighthouseCollection/CTM/blob/d724ba56b8bd5cf501d55fbbca416470108f963a/tribunal/models.py#L749), [static/ctm/applicant-decrees.js:7](https://github.com/LighthouseCollection/CTM/blob/72ee829eb1eabc436c19a084f81235b6a029528c/static/ctm/applicant-decrees.js#L7).

Next action: Backend/governance map exact template/certificate/approval/entitlement/release identities and retain previous decree access. Separately accept genuine signature/issuance and delivery; keep current applicant exact-file withdrawal behavior.

## Clean observations and remaining boundaries

The prior 68 frontend tests / 54 real API-browser groups remain recorded at applicant `72ee829`. This audit changes no product behavior and does not rerun live services. Existing own privacy, exact response replay, retained checkout and revoked decree-byte tests are not invalidated by structural differences. Seven new reconciliation unit tests and a selected-ref replay regression verify count validation, alias safety, JSON non-parity, FK/nullability/type/PK differences, scope and shared adapters.

Review reproduced a selected-ref replay bug: local schema drift could mix source identities. The generator now reads the contract from the selected applicant Git ref; the failing drift regression passes without changing local contract files.

The exact shared adapter is surfaced in JSON: CheckoutIntent is proposed for both filing_candidates and payment_attempts; this is an unresolved entity mapping, not two completed contract roots.

The governance council prototype audit at `7586214` covers a different source/page scope; this applicant field-level comparison does not claim to reproduce its 33-page review.

- Named/renamed columns are candidates, never parity or completion percentages.
- No standalone model mapping is a domain-inventory observation, not proof a business capability is absent.
- Framework authentication/session tables are outside the 63-domain-model inventory.
- Storage candidates do not establish normalized typed relations or field-level content coverage.
- Defaults, lengths, checks, unique constraints, indexes, RLS, migration execution and live database state are not compared.
- Source-reported PostgreSQL results are not independently rerun here; previous local browser evidence retains its recorded scope.

## Reproduce

```powershell
uv run python scripts/build_applicant_schema_audit.py --backend-ref d724ba56b8bd5cf501d55fbbca416470108f963a --applicant-ref 72ee829eb1eabc436c19a084f81235b6a029528c
node --test tests/frontend/applicant-schema-audit.test.cjs
uv run python tests/test_applicant_schema_provenance.py
```

The generator only writes this report directory. It never applies SQL, edits protected schema/backend sources or deploys. Mapping and findings inputs are reviewable JSON; resolved source hashes are retained in result.json.
