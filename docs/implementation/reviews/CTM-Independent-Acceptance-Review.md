# CTM Independent Acceptance Review

Prepared 2026-10-21 (America/Los_Angeles) for the CTM governance coordinator, for reconciliation into GitHub issues under governance tracker [#4](https://github.com/LighthouseCollection/CTM/issues/4). This is a requirements and acceptance review. It contains no implementation code, credentials or case data.

## Sources and scope of evidence

### Reviewed

The private repository could not be read over the web. The files below were copied from the local Desktop-R applicant checkout of `LighthouseCollection/CTM`. The six build-spec and governance files in the working tree are byte-identical (SHA-256) to the newest `.tmp/applicant-real-api-*` snapshot, dated 2026-10-21 17:07 PT. `CLAUDE-START-HERE.md` exists only in that snapshot, and the copy supplied in chat matches it. Git metadata could not be read (repository ownership check), so **I cannot confirm that this snapshot equals current `origin/main`**.

| Source | Use in this review |
|---|---|
| [CLAUDE-START-HERE.md](https://github.com/LighthouseCollection/CTM/blob/main/CLAUDE-START-HERE.md) | Project handoff, workflow summary |
| [build-spec/CTM-build-specification.md](https://github.com/LighthouseCollection/CTM/blob/main/docs/architecture/build-spec/CTM-build-specification.md) (contract v `ctm-build-contract-2026-10-21-v1`) | Governing requirements, including resolved precedence corrections |
| [build-spec/permissions.md](https://github.com/LighthouseCollection/CTM/blob/main/docs/architecture/build-spec/permissions.md) | Action matrix, notification routing, DB enforcement |
| [build-spec/interface-contract.md](https://github.com/LighthouseCollection/CTM/blob/main/docs/architecture/build-spec/interface-contract.md) | Locked navigation and layouts |
| [build-spec/transactions-and-acceptance.md](https://github.com/LighthouseCollection/CTM/blob/main/docs/architecture/build-spec/transactions-and-acceptance.md) | Transaction rules, required acceptance IDs (SEC01…UI01) |
| [build-spec/data-dictionary.md](https://github.com/LighthouseCollection/CTM/blob/main/docs/architecture/build-spec/data-dictionary.md) | Table/constraint semantics (~45 relevant tables read; not all 151 in full) |
| [docs/implementation/governance.md](https://github.com/LighthouseCollection/CTM/blob/main/docs/implementation/governance.md) | Ownership, demo acceptance order |
| Also read: `build-spec/README.md`, `build-spec/delivery-dependencies.md`, `build-spec/prototype-decision-types.json`, `docs/architecture/CTM-current-access-workflow-corrections.md`, `docs/implementation/status.md`, `stream-*.md`, `parallel-build-handoff.md`, `integration-access.md`, `applicant/api-contract.md`, `applicant/test-evidence.md`, `applicant/desktop-r-slice.md` | Precedence corrections, implementation status (status is not requirements) |

### Unavailable or not reviewed

- GitHub issues #1–#4, PRs (including #5, #7), comments and GitHub Actions results. **Not accessed.** Dependencies already raised there may duplicate findings here.
- `schema.json`, `schema.sql`, `source-register.json`, `validation.json`, `relationships.mmd`, `validation-results.json`. **Not reviewed.**
- `CTM-Plenix-CDN-contract.md`, Plenix 0.58.0 documentation, accepted question seed and bank files, `CTM-confirmed-decisions.md` and other non-build-spec architecture documents. **Not reviewed.** Question-bank wording was deliberately not examined.
- Application code (`tribunal/`, `ctm/`, `static/ctm/`, `templates/`, `tests/`). **Not reviewed.** Every "Verify" item below is a requirement to test, not a proven defect.

### Classification used

- **[Gap]**: confirmed requirement with no defined acceptance proof, or with an untested edge.
- **[Conflict]**: unresolved conflict between sources after applying precedence (detailed in Section 3).
- **[Verify]**: implementation claim or observed implementation evidence that needs confirmation. Not a proven defect.
- **[Decision]**: the sources cannot answer it (Section 5).
- **[Suggestion]**: optional.

### Precedence applied first

I applied the build-spec "Resolved precedence corrections" table and `CTM-current-access-workflow-corrections.md` before flagging any conflict:

- no CTM passwords
- restored admin/secretary functional authority
- only the current manager gets routine alerts
- only an existing admin adds council members
- certificate number is not a matching route
- replacement decrees removed
- filename has no applicant ID
- applicant may read only their own submitted request answers
- 59-question bank
- explicit refresh for unsent intake drafts
- manual calls only
- no fixed 17:00 send

The build-spec README says direct user corrections outrank the build spec. Excluded by instruction: OCR and audio-recording absence (honest placeholders accepted).

---

## 1. Priority findings

| ID | Workflow | Finding | Requirement source and section | Expected behavior | Priority | Suggested owner |
|---|---|---|---|---|---|---|
| F01 | Registration / spouse linking | [Gap] Pending-association auto-link on verified email has no defined behavior when the matching account's canonical person already holds a different open-case claim, is already party A of the same case, or is a staff account. Auto-activation could attach the wrong person to a case. | Build spec, "Identity, login and privacy" ¶5; T&A, "Finalize filing" step 4–5; data dictionary `case_party_onboarding`, `person_open_case_claims` UNIQUE(person_id) | Activate only when the provider-verified email equals `normalized_email` and the person has no conflicting claim. Otherwise keep it pending with an admin/secretary-visible conflict. Never link a council/staff account as an applicant party. Activation reacquires its own claim under the person lock. | P0 | Backend/Security |
| F02 | Registration / spouse linking | [Gap] Apple private-relay address cannot equal a staff-entered address, so that spouse can never auto-link. The only recovery is admin/secretary correction of the pending association, and there is no acceptance proof for it. | Build spec, "Identity, login and privacy" ¶2 and ¶5 | Link stays pending. Admin/secretary corrects the intended email with history. Activation happens only after a new verified match. No email-only merge. | P2 | Backend/Security |
| F03 | Application draft / required answers | [Verify] The applicant stream reports that repeat-record definitions (children, restraining orders with one copy each, prior applications, prior marriages) are "still pending". Without a shared contract, required per-order documents and approved Unknown rules cannot be rendered or validated. | Build spec, "Initial application" step 3–4 and following ¶; applicant `api-contract.md` (implementation doc) | One agreed repeat-entry projection: stable entry IDs, approved labels in EN/AR, per-entry required file context. The server rejects a submission that lacks a restraining-order copy, court, case number or status (no Unknown). | P1 | Governance |
| F04 | Application documents | [Verify] Applicant real-API run reports that `GET /api/applications/{id}/files/` returned 404, which keeps filing disabled. | Applicant `test-evidence.md`; build spec, "Initial application" step 4 | Own current originals only, latest version, scan state, no prior versions or council sources. Requirements reflect current answers. | P1 | Backend/Security |
| F05 | Declaration / submission | [Gap] Submission requires a versioned declaration, but institutional declarations are unpublished. The demo journey cannot reach "submitted" honestly without published text. | Build spec, "Initial application" step 6–7; delivery-dependencies, "Institutional text"; status.md, "Verified in the VM" | Submission blocked when no published declaration version exists. Any demo text must be published as a clearly labelled demo version and never presented as approved. See D8. | P1 | Governance |
| F06 | Payment / waiver | [Gap] Undefined race between an admin/secretary waiver and an open or late-succeeding checkout attempt. Possible results: an obligation both `waived` and allocated, two finalizations, or an unallocated charge. | Build spec, "Initial application" step 6–7 and "Files, search, payments"; data dictionary `fee_obligations` disposition, `payment_allocations` UNIQUE(attempt_id), `refund_events`; T&A, "Finalize filing" (paid-but-blocked) | Waiver and payment success serialize on the obligation. Exactly one satisfies it. A later successful charge on a satisfied obligation creates a staff-visible accidental-duplicate refund candidate. One submission. Never silent loss or double allocation. | P0 | Backend/Security |
| F07 | Payment / finalization | [Gap] Paid filing whose finalization is blocked (duplicate hold, ambiguous match, daily cap of 99, suspended owner, case-number day rollover): the case-number date and the recovery path lack an acceptance test. | Build spec, "Case and marriage invariants" ¶3; T&A, "Finalize filing" final ¶; data dictionary `case_number_counters` | Recoverable paid candidate plus staff-visible reconciliation item. No second charge. Case number allocated at actual finalization commit (LA date). The 100th same-day filing is not lost and is not numbered past 99. | P2 | Backend/Security |
| F08 | Return / resubmission | [Conflict] Visibility to council of saved-but-not-resubmitted corrections on a returned filing is unresolved. See C1 and D1. | Build spec, "Identity…" ¶3 vs "Initial application" step 8 and correction ¶; permissions, notification row 1 | Pending D1, the conservative default is that council sees the last formal submission plus history. Corrections remain attributable revisions either way. | P1 | Governance |
| F09 | Return / resubmission | [Gap] Acceptance proof is missing for:<br>(a) resubmission reusing the original signature and fee;<br>(b) the full safety and required-document recheck;<br>(c) a review binding the exact new submission;<br>(d) two staff reviewing the same submission at once;<br>(e) mandatory instructions on Reject. | Build spec, "Initial application" step 8; T&A, "Correct/resubmit"; data dictionary `application_completeness_reviews` CHECK, `application_submissions.previous_submission_id`; PAY02, VER01 | New immutable submission linked to the previous one. No checkout or re-sign. One review result per submission; the concurrent second reviewer gets a stale-version rejection. Reject without text is refused. | P1 | Council |
| F10 | Completeness review | [Gap] Notification routing is defined only for "No manager yet". It is not defined for a second filer's submission or resubmission into an already-assigned case. | Permissions, notification rows 1 and 5 | Completeness review stays with admin/secretary per build-spec step 8. Whether the current manager is also alerted needs a governance ruling. Without one, use only the documented rows. | P2 | Governance |
| F11 | Marriage matching | [Gap] State of a paid filing awaiting ambiguous-match or person-mapping review is not testably defined: case number, completeness queue, and visibility of either case. | Build spec, "Case and marriage invariants" ¶2–3; T&A, "Finalize filing" steps 3–4 | No access is activated to any candidate case. No case number is consumed until the mapping is resolved. Paid candidate retained. Admin/secretary review item. Neither applicant learns of the other candidate. | P0 | Backend/Security |
| F12 | Marriage matching / one-open-case | [Decision] An independent filing by the second spouse that exactly matches a closed case, or a closed case with a pending appeal, is not addressed. "Reuse matching case" could append a filing to a closed proceeding. See D3. | Build spec, "Case and marriage invariants" ¶1–2; "Appeals" ¶1 | Until D3 is decided, the filing must not reopen a closed case or add a new filing to a closed proceeding. It should go to admin/secretary review. | P2 | Governance |
| F13 | Applicant privacy (cross-surface) | [Gap] Within one case, applicant A's surfaces have no explicit test covering B's events: timeline, notifications, case status, testimony invitations or reminders, hearing outcome copies, pending appeal, withdrawal, rejection explanation. SEC01 lists fields/files/messages but not these. | Build spec, "Identity…" ¶3; "Council sessions" ¶3; permissions, notification rows (withdrawal "never notify other applicant"); T&A SEC01 | A sees only own events and communications addressed to A. No B testimony time or response, no B withdrawal, no B pending appeal or supplement, no B correction notices. | P0 | Backend/Security |
| F14 | Notifications / files | [Gap] There is no acceptance proof that DOB-bearing references (`…-JS19850314M`) are absent from notification and email subjects, alert summaries, presented filenames, object keys and logs. | Build spec, "Case and marriage invariants" ¶4; permissions, "Notification routing" last ¶; "Files…" ¶2 | Subjects and summaries use the case number or neutral text only. Filenames follow `[case]-[code]-[YYYYMMDD]-[HHMM]`. Object keys are UUIDs. | P0 | Backend/Security |
| F15 | Assignment | [Conflict] "separate entering admin/secretary" vs a single person holding both president and admin roles in a ~10-user demo. See C2 and D2. | T&A, "Assignment and sessions" ¶1; build spec, "Council sessions" ¶1; data dictionary `case_assignments` | Pending D2. Both actors are recorded either way. Exactly one current assignment. The outgoing manager, incoming manager and each applicant are notified privately. | P1 | Governance |
| F16 | Agenda | [Conflict] Assigned-manager agenda "request" vs implemented direct part-2 placement. See C3. | Build spec, "Council sessions" ¶2; permissions "Request agenda"; data dictionary `agenda_requests.placed_item_id`; status.md "Assigned-manager agenda placement" | Governance confirms whether placement by the manager is direct or a request that admin/secretary places. Either way: part 1 stays admin/secretary, one item per session/case, rechecked after reassignment. | P2 | Governance |
| F17 | Sessions / communications | [Gap] Planned reschedule transfers agenda cases and testimony appointments, but `Send after council session` deliveries bound to the removed session are not in the listed transfer set. They could be orphaned (never sent) or block deletion. | T&A, "Assignment and sessions" ¶2–3; build spec, "Files, search, payments and communications" last ¶; data dictionary `communications.council_session_id` | Bound deferred deliveries move with the case to the new session, with audit, or explicitly require re-selection. They dispatch exactly once on the new session's close. None are silently dropped. | P1 | Backend/Security |
| F18 | Testimony | [Conflict] "Don't invent end times" vs "must confirm non-overlapping segments" when `ends_at` is null. See C4. | T&A, "Assignment and sessions" ¶4; data dictionary `testimony_appointment_versions` | Pending reconciliation, the conservative interim is to refuse a second same-session invitation when either segment lacks an end time and the start times are not separated by an explicitly entered end. | P2 | Council |
| F19 | Sessions / hearings | [Gap] Assigned manager deactivated or suspended while current: routing of manager alerts, presenter availability and the vote-roster treatment of inactive members are undefined. | Build spec, "Identity…" ¶1; permissions "Notification routing" last ¶; T&A SEC03; status.md "Session attendance interface" | Inactive manager loses access immediately (SEC03). Alerts do not go to an inactive account. The case awaits president-authorized reassignment. The roster rule for inactive members needs governance confirmation. | P2 | Governance |
| F20 | Hearings / communications | [Conflict] Whether the hearing-outcome applicant message offers `Send Immediately` / `Send after council session`, or a single immediate Send. See C5. | Build spec, "Council sessions" ¶4 vs "Files…communications" last ¶; permissions row "Case hearing pending update" | Portal copy immediate. Email timing per C5 resolution. Recommendation revisions never resend. | P2 | Council |
| F21 | Reports / external priest | [Gap] Scoped link: 30-day expiry, reissue disabling the old link, paper upload completing the request, and closure revoking it are covered by REP01/SEC05. Missing is the behavior when no outbound email is configured. The token is stored only as a hash, so staff cannot later retrieve it. | Build spec, "Reports" ¶5; permissions "External priest"; data dictionary `external_report_links`; delivery-dependencies "Email" | Without email, the online-link path reports unavailable honestly. Print-PDF and paper upload remain usable. No plaintext token in audit or logs. Whether staff may see a link once at issuance is D8 (b). | P2 | Backend/Security |
| F22 | Reports / requests | [Gap] Applicant or external response submitted after case closure, cancellation or reassignment. Applicant reading of the own submitted response only. | T&A, "Requests, reports" ¶1–2; permissions rows "Respond to intake", "Read applicant-completed report" | Submission rejected when the proceeding is closed or the request is cancelled. The applicant sees own frozen questions and answers only, with no observations, transcript or other reports. A new manager adds a follow-up and never rewrites the predecessor's narrative. | P1 | Council |
| F23 | Professional Assessments | [Gap] The signed release scope does not follow reassignment. There is no defined acceptance path for a new manager who needs access, or for a doctor-sent report entered by staff. | Build spec, "Professional Assessments"; T&A, "Requests…" ¶3; permissions "Sign medical release", "Respond to intake/request" | Out-of-scope council sees missing-authorization status only. A new release from the subject is required. Staff never sign. Staff entry on behalf (if allowed) stays hidden until a valid release exists. No external AI egress. | P2 | Council |
| F24 | Search / previews | [Gap] Council search must reauthorize every hit, snippet, facet and count against draft privacy, medical scope and the unreviewed-AI-text restriction. Placeholder OCR must not show content as indexed. | Build spec, "Files, search…" ¶3; T&A SEC02, SEC06, REP03 | Out-of-scope items are excluded from counts and facets as well as hits. A file with no OCR shows a "not processed" state. Applicants have no search API or key. | P0 | Backend/Security |
| F25 | Evidence / completeness review | [Verify] Completeness review must show the exact submitted manifest versions. The case-file endpoint defaults to the latest clean version and hides an older clean version while the latest is pending. | Build spec, "Initial application" step 7–8; T&A, "Correct/resubmit" ("Review binds exact submission/manifest"); status.md "Private file delivery" | The review screen lists `submission_file_manifest` versions. Later replacements appear as subsequent versions, not as the reviewed item. | P1 | Council |
| F26 | Decision type / grounds | [Conflict] Catalog labels "(Applicant)" and "(Respondent)" do not map to cases where both spouses filed independently (party slots A/B). See C6 and D7. | `prototype-decision-types.json`; build spec, "Decisions" ¶1; data dictionary `case_decision_versions.party_outcomes`, `decree_entitlements` | Entitlement derives from explicit per-party outcomes recorded in the decision version, never from the label alone. Voters see the named parties first. | P0 | Council |
| F27 | Decision type | [Gap] `deferred` is a hearing outcome. `withdrawn` and `reconciled` are withdrawal. None of them may be voted on, approved or issued as a decision. | `prototype-decision-types.json` dispositions; build spec, "Decisions" ¶4 | Decision & Voting offers only decision-producing types and Petition Denied. Deferral is recorded on the hearing outcome. Reconciliation follows the withdrawal workflow. | P1 | Council |
| F28 | Decree / issuance | [Gap] A signed PDF stored against decision version N while the type or grounds are revised to N+1 needs explicit proof that issuance is then blocked. | T&A, "Decision, issuance" ¶1–2; data dictionary `decrees.decision_version_id`, `decree_issuance_events.approval_id`; DEC01–DEC02 | Issuance requires decree, certificate, approval and decision to reference the same latest approved version. Otherwise issuance is refused and the stale certificate is retained (not deleted). | P0 | Council |
| F29 | Decree / release | [Gap] Release only to the exact entitled party. Issuance never auto-releases. Withdrawal revokes previews and downloads. The behavior for a suspended or unregistered entitled recipient is untested. | Build spec, "Decisions" ¶3; T&A, "Decision, issuance" ¶2; SEC05, DEC02 | Notice-only party never receives the certificate. Withdrawn release returns 403/404 on view, preview and range. A recipient without an active account cannot receive portal release (see D4). | P0 | Council |
| F30 | Withdrawal | [Gap] / [Conflict] In a two-filer case where only one party withdraws, the following are undefined: release of the withdrawn party's open-case claim, notices to the withdrawn party on eventual closure, and secretary entry of a single-party withdrawal on behalf. See C7 and D5. | Build spec, "Decisions" ¶5; T&A, "Decision, issuance" ¶3; permissions "Withdraw own petition/appeal"; data dictionary `party_withdrawals` | Case stays open until all participating filers withdraw or a decision closes it. The other applicant is never notified of the withdrawal. The remaining items depend on D5. | P2 | Governance |
| F31 | Closure immutability | [Gap] After issuance or denial closure: applicant answer and file corrections, report and finding edits, and attendance edits are rejected. Only the listed narrow actions remain (communications, finance, release/withdrawal, transcript corrections, appeal work). | T&A, "Decision, issuance" ¶5; build spec, "Reports" ¶7 | Mutations return a lifecycle rejection with no partial write. Communications and appeal filing still succeed. | P1 | Backend/Security |
| F32 | Appeals / reopening | [Decision] Unclear whether a different open case held by the non-appellant party blocks reopening for the appellant ("locks… all known participating canonical persons… Reject different open-case conflict"). See D6. | T&A, "Appeal acceptance" ¶2; build spec, "Appeals" ¶2 | Appeal is never deleted. No second open case for any person. The result for the non-conflicting appellant depends on D6. | P2 | Governance |
| F33 | Appeals | [Gap] Acceptance proof is missing for: Accept/Decline racing against withdrawal; a supplement after disposition; a second appeal while one is pending; an appeal decree suffix after an original Denied (no base certificate); assignment continuity after closure for the presenter and alerts. | T&A, "Appeal acceptance" ¶1–2; build spec, "Appeals"; data dictionary `pending_appeal_claims`, `appeal_dispositions` UNIQUE(appeal_id), `appeal_withdrawals` UNIQUE | Exactly one of disposition or withdrawal commits. Supplements are rejected after disposition. One pending appeal per person per case. The suffix is allocated per decree-producing appeal proceeding (`DCR-[case]-A1`) even without an original certificate. The original manager remains the presenter unless reassigned. | P1 | Council |
| F34 | English/Arabic | [Gap] There is no acceptance proof that system notices, validation messages and email chrome follow the recipient's `notification_locale`, while staff-authored bodies, return instructions and applicant answers stay in their original language without automatic translation. Also missing: proof that authorization is identical in both locales and that IDs and email addresses stay left-to-right inside RTL text. | Build spec, "Audio, transcription and translation" ¶3; CLAUDE-START "Mandatory Plenix rules"; data dictionary `accounts.notification_locale`; UI01 | EN/AR chrome per recipient. Authored content is shown as authored and escaped. Case numbers and emails are isolated from bidirectional reordering. The same 403/404 behavior applies in both locales. | P2 | Applicant |
| F35 | Duplicate identity | [Gap] The "exact duplicate-person" matching rule that triggers `identity_review_holds` was not found in the reviewed sources (unlike the marriage rule). It may be defined in unreviewed documents. | Build spec, "Initial application" step 6; T&A, "Appeal acceptance and account consolidation" ¶3; data dictionary `identity_review_holds.matching_rule` | Governance cites the authoritative rule. Holds block payment and submission only, never draft saving. Consolidation never auto-merges. | P2 | Governance |
| F36 | Return / one-open-case | [Gap] A returned filing that is never resubmitted keeps its open-case claim indefinitely. Submitted records do not expire, so the only exit is withdrawal by the applicant or by an admin on the applicant's behalf. There is no test for this. | Build spec, "Initial application" step 5 and 8; "Decisions" ¶5 | Returned filing never auto-expires. Withdrawal by owner or admin closes it per the withdrawal rules. No deletion. | P2 | Applicant |

---

## 2. Acceptance scenarios

These scenarios extend the existing T&A IDs; references are given as "Extends". Every scenario assumes synthetic accounts and data only.

### F01 Pending spouse auto-link

**AS-F01-1 (success)**
- Preconditions: Case C has party B pending (first/last name, `b@example.test`). No account is registered yet.
- Actor: B
- Action: Registers with Google; verified email `b@example.test`.
- Expected result: Link activates automatically. B acquires an open-case claim on C. B sees an own projection only. The manager is not notified as for an applicant change.
- Forbidden result: An "Accept invitation" step. B sees A's answers, files or messages.
- Source: Build spec "Identity…" ¶5. Extends SEC01.

**AS-F01-2 (conflict)**
- Preconditions: The verified account for `b@example.test` belongs to a person with a different open case D.
- Actor: System at registration or login
- Action: Activation attempt.
- Expected result: Link stays pending. An admin/secretary-visible conflict is recorded. No claim is acquired.
- Forbidden result: B linked to C while open on D. D closed or altered.
- Source: T&A "Finalize filing" step 5. INV01.

**AS-F01-3 (wrong target)**
- Preconditions: The staff-entered email matches party A's own account, or a council account.
- Actor: Admin/secretary, then System
- Action: Save association; activation.
- Expected result: Rejected or held for review. A council account is never linked as an applicant party.
- Forbidden result: A becomes both parties. A staff account gains an applicant projection.
- Source: Build spec "Identity…" ¶1 and ¶5.

### F02 Apple relay

**AS-F02-1**
- Preconditions: Pending email `b@example.test`. B signs in with Apple using a private-relay address.
- Actor: B, then admin/secretary
- Action: B signs in. Admin corrects the pending email to the relay address with history.
- Expected result: No link before the correction. The link activates only after the corrected address equals the verified address. History shows both values and actors.
- Forbidden result: Linking on name match or on unverified email. Merging an existing account.
- Source: Build spec "Identity…" ¶2 and ¶5.

### F03 / F04 Repeat entries and own files

**AS-F03-1**
- Preconditions: Applicant reports two restraining orders.
- Actor: Applicant
- Action: Uploads a copy for order 1 only; enters "Unknown" for order 2's court; attempts submission.
- Expected result: Submission refused. Each order requires its own copy, court, case number and status. Unknown is not accepted for those fields.
- Forbidden result: One copy satisfies both orders. Unknown accepted.
- Source: Build spec "Initial application" step 4.

**AS-F04-1**
- Preconditions: Applicant A owns a draft. Applicant B is unrelated.
- Actor: A, then B
- Action: A lists `/api/applications/{A}/files/`. B requests the same URL and a known file-version URL.
- Expected result: A receives current originals with scan state. B receives a 404-equivalent with no metadata.
- Forbidden result: Prior versions shown to A. Any bytes or count leaked to B.
- Source: Applicant `api-contract.md`; SEC01.

### F05 Declaration

**AS-F05-1**
- Preconditions: No published declaration version.
- Actor: Applicant
- Action: Attempts checkout or submission.
- Expected result: Blocked with an honest "declaration unavailable" state.
- Forbidden result: Submission with empty, placeholder-unlabelled or reference-draft text.
- Source: Delivery-dependencies "Institutional text".

### F06 Payment vs waiver

**AS-F06-1 (race)**
- Preconditions: Checkout session open for obligation O.
- Actor: Admin/secretary and the payment provider, concurrently
- Action: Waiver recorded; provider then sends a success webhook for O.
- Expected result: Exactly one satisfies O. The other produces a staff-visible accidental-duplicate refund candidate. One submission.
- Forbidden result: O both waived and allocated. Two submissions. A charge with no record.
- Source: Build spec "Files, search, payments" ¶4. PAY01/PAY02.

**AS-F06-2 (redirect not proof)**
- Preconditions: Checkout created.
- Actor: Applicant
- Action: Opens the success return URL without a provider event.
- Expected result: Still unpaid.
- Forbidden result: Submitted.
- Source: Build spec "Initial application" step 7.

### F07 Blocked paid finalization

**AS-F07-1**
- Preconditions: 99 cases already numbered today (LA).
- Actor: System
- Action: Verified payment for a new filing.
- Expected result: Paid candidate retained. Reconciliation item visible. No 100th number.
- Forbidden result: `YYYYMMDD-100`. Lost payment. Second charge.
- Source: INV03; T&A "Finalize filing".

**AS-F07-2**
- Preconditions: Draft started 10/19. Payment verified 10/21 23:59:58 PT. Finalization commits 10/22 00:00:03.
- Actor: System
- Action: Finalize.
- Expected result: Number uses the LA date of the finalization commit, consistently across retries.
- Forbidden result: Draft-start date. Different numbers on retry.
- Source: Build spec "Case and marriage invariants" ¶3.

### F08 / F09 / F36 Return and resubmission

**AS-F09-1 (success)**
- Preconditions: Submission S1 returned with instructions.
- Actor: Applicant, then admin/secretary
- Action: Correct answers, replace one file, resubmit; reviewer accepts S2.
- Expected result: S2 links to S1. Same case number, fee and signature. Full safety and required-document recheck. Review binds S2's manifest. S1 is retained.
- Forbidden result: New checkout or re-sign. S1 overwritten. Old file version shown to the applicant.
- Source: Build spec step 8; VER01.

**AS-F09-2 (missing text)**
- Preconditions: S1 under review.
- Actor: Admin/secretary
- Action: Reject with an empty instruction.
- Expected result: Refused.
- Forbidden result: Returned without instructions.
- Source: Data dictionary CHECK on `application_completeness_reviews`.

**AS-F09-3 (concurrency)**
- Preconditions: S1 under review.
- Actor: Two admins, concurrently
- Action: One accepts and one rejects.
- Expected result: One commits. The other gets a stale-version rejection.
- Forbidden result: Both results recorded.
- Source: T&A shared rules (optimistic versions).

**AS-F08-1 (pending D1)**
- Preconditions: Returned S1. The applicant saves corrections but has not resubmitted.
- Actor: Council member
- Action: Open Petition.
- Expected result: Per D1. Default: S1 plus history is visible; unsaved local edits are never visible.
- Forbidden result: Content never saved to the server appears.
- Source: C1.

**AS-F36-1**
- Preconditions: S1 returned 200 days ago, untouched.
- Actor: System retention job
- Action: Cleanup run.
- Expected result: Not expired or deleted. The open-case claim remains.
- Forbidden result: Deletion of a submitted filing.
- Source: Build spec step 5; RET01.

### F10 Completeness routing

**AS-F10-1**
- Preconditions: Case assigned to M. Second filer B submits.
- Actor: B
- Action: Submit.
- Expected result: Enters the admin/secretary completeness queue. Manager alert per the governance ruling. B's filing is not visible to A.
- Forbidden result: Bypasses completeness review. B's submission content is visible to A.
- Source: Build spec step 8–9.

### F11 / F12 Matching

**AS-F11-1 (ambiguous)**
- Preconditions: Two open cases match the same three dates.
- Actor: Applicant
- Action: Paid finalize.
- Expected result: Paid candidate is held. Review item created. No case number. No access to either case.
- Forbidden result: Auto-link to either case. Candidate case names, numbers or status disclosed.
- Source: INV02; T&A "Finalize filing" step 3.

**AS-F11-2 (reverse role, success)**
- Preconditions: A filed (marriage date and DOB pair). B files with roles reversed and a different certificate number.
- Actor: B
- Action: Paid finalize.
- Expected result: Linked to the same case. No new case number. Both certificate numbers preserved. No person merge.
- Forbidden result: New case. Certificate conflict blocks the match.
- Source: INV02.

**AS-F11-3 (nulls)**
- Preconditions: Spouse DOB unknown in one filing.
- Actor: System
- Action: Finalize.
- Expected result: No automatic match.
- Forbidden result: Null treated as equal.
- Source: T&A step 3.

**AS-F12-1**
- Preconditions: Case C closed. Absent spouse B files independently with exact dates.
- Actor: B
- Action: Paid finalize.
- Expected result: Admin/secretary review hold pending D3.
- Forbidden result: Filing silently attached to the closed proceeding. C reopened.
- Source: D3.

### F13 / F14 Applicant isolation and identifiers

**AS-F13-1**
- Preconditions: A and B are both participating. B is scheduled for testimony at 10:00, rejects with an explanation, withdraws a pending appeal, and edits answers.
- Actor: A
- Action: Views timeline, notifications, appointments, appeals and case status, and replays prior notification links.
- Expected result: Only A's own items and communications addressed to A.
- Forbidden result: B's time, response, explanation, withdrawal, appeal or edits. Counts that reveal them.
- Source: Build spec "Identity…" ¶3; permissions routing. Extends SEC01.

**AS-F13-2**
- Preconditions: A both-recipient hearing update has been sent.
- Actor: A, then B
- Action: Each replies by portal and by email.
- Expected result: Separate private copies. Each reply lands only in the sender's thread.
- Forbidden result: Cross-party reply visibility.
- Source: MSG01.

**AS-F14-1**
- Preconditions: Any notification, email or upload.
- Actor: System
- Action: Generate the subject, summary and presented filename; write logs.
- Expected result: No applicant reference or DOB. Filename `[case]-[code]-[YYYYMMDD]-[HHMM]` plus a discriminator only on a same-minute collision.
- Forbidden result: `JS19850314M` anywhere in those outputs.
- Source: Build spec ¶4 of "Case and marriage invariants"; "Files" ¶2.

### F15 / F16 / F19 Assignment and agenda

**AS-F15-1**
- Preconditions: Accepted case, part 1.
- Actor: President authorizes; secretary records.
- Action: Assign M1, later reassign to M2.
- Expected result: One current assignment. Both actors and times are stored. M1, M2 and each applicant are notified privately. M1 loses assigned-only write immediately.
- Forbidden result: Two current assignments. M1 places the agenda or edits findings afterwards.
- Source: T&A "Assignment and sessions" ¶1; SEC03.

**AS-F15-2 (pending D2)**
- Preconditions: User U holds both president and admin roles.
- Actor: U
- Action: Authorize and record the same assignment.
- Expected result: Per D2.
- Forbidden result: Recorder or authorizer missing.
- Source: C2.

**AS-F16-1**
- Preconditions: Planned session.
- Actor: Assigned manager
- Action: Places own case twice; attempts part 1; attempts after reassignment.
- Expected result: One item. Part 1 refused. Refused after reassignment.
- Forbidden result: Duplicate items.
- Source: Permissions; SES02.

**AS-F19-1**
- Preconditions: Assigned M suspended.
- Actor: Applicant
- Action: Uploads a correction.
- Expected result: M is denied all access. No alert delivered to M. Case awaits reassignment.
- Forbidden result: M retains session access.
- Source: SEC03; permissions routing.

### F17 / F18 / F20 Sessions, testimony, hearing messages

**AS-F17-1**
- Preconditions: Message with email timing `after_council_session` bound to planned session S1.
- Actor: Admin/secretary
- Action: Reschedule S1 to S2, then close S2.
- Expected result: Delivery moved or re-bound with audit. Email dispatched once on S2 close.
- Forbidden result: Email never sent. Sent on S1's removed date. Sent twice.
- Source: T&A sessions ¶2–3; MSG02.

**AS-F17-2**
- Preconditions: Session with a completed hearing.
- Actor: Admin/secretary
- Action: Planned reschedule.
- Expected result: Refused.
- Forbidden result: Completed hearing history deleted.
- Source: SES01.

**AS-F18-1**
- Preconditions: A testifies at 10:00 with an unknown end.
- Actor: Admin/secretary
- Action: Schedules B at 10:30 in the same session.
- Expected result: Per C4. The interim rule refuses until an explicit end time is entered.
- Forbidden result: Overlapping invitations sent.
- Source: SES03.

**AS-F18-2**
- Preconditions: Confirmed appointment v1.
- Actor: Admin/secretary
- Action: Reschedules to v2.
- Expected result: Fresh Confirm/Reject on v2. The v1 response is retained. The reminder targets v2 only. The applicant has no reschedule control.
- Forbidden result: v1 confirmation carries over. A reminder for the cancelled v1 is sent.
- Source: SES03.

**AS-F20-1**
- Preconditions: Hearing outcome with an applicant message.
- Actor: Assigned manager
- Action: Send, then revise the recommendation.
- Expected result: Communication recorded once. The revision does not resend. Portal delivery is immediate; email timing per C5.
- Forbidden result: Automatic resend. Sent text rewritten.
- Source: Build spec "Council sessions" ¶4.

### F21 / F22 Reports

**AS-F21-1**
- Preconditions: No outbound email configured.
- Actor: Manager
- Action: Creates an external priest request; chooses print.
- Expected result: Request exists first. The blank PDF carries the request identity. Paper upload completes the request and disables the online response. The original is retained. The email link path shows unavailable.
- Forbidden result: "Link emailed" shown. A token in logs.
- Source: REP01.

**AS-F21-2**
- Preconditions: Link issued on day 0.
- Actor: Priest
- Action: Opens it on day 31; also opens the old link after a reissue.
- Expected result: Both denied. The draft is preserved for the reissued link.
- Forbidden result: Access or case browsing.
- Source: SEC05.

**AS-F22-1**
- Preconditions: Applicant request sent; case then closes.
- Actor: Applicant
- Action: Submits answers.
- Expected result: Refused. Earlier submitted answers remain readable read-only to that applicant.
- Forbidden result: Write accepted. Internal observations visible.
- Source: T&A "Requests" ¶1.

**AS-F22-2**
- Preconditions: Report authored by M1; reassigned to M2.
- Actor: M2
- Action: Edits M1's narrative.
- Expected result: Refused. M2 creates a linked follow-up with its own identifier and date.
- Forbidden result: Predecessor narrative rewritten.
- Source: Build spec "Reports" ¶7.

### F23 Professional Assessments

**AS-F23-1**
- Preconditions: Release scoped to the M1 recipient role or purpose; report uploaded.
- Actor: M2 (new manager) and an unrelated council member
- Action: Open, download, search, and view the context link.
- Expected result: Missing-authorization status only, outside scope. Disclosure events are recorded for in-scope access.
- Forbidden result: Bytes, OCR, snippets or counts out of scope. Staff signing for the subject.
- Source: SEC06; T&A "Requests" ¶3.

**AS-F23-2**
- Preconditions: Medical file under processing.
- Actor: Background job
- Action: Translation fallback triggered.
- Expected result: Refused. Local processing only.
- Forbidden result: Any external AI request containing medical content.
- Source: SEC06.

### F24 / F25 Search and evidence

**AS-F24-1**
- Preconditions: Out-of-scope medical PDF and an unsubmitted draft contain the term "X".
- Actor: Council member
- Action: Search "X".
- Expected result: Zero hits from those sources, and zero from them in counts and facets.
- Forbidden result: "1 hidden result". A snippet.
- Source: SEC02, SEC06.

**AS-F24-2**
- Preconditions: OCR placeholder active.
- Actor: Council member
- Action: Opens a scanned PDF's search status.
- Expected result: Labelled "not processed".
- Forbidden result: Claim that it was indexed or OCR'd.
- Source: Governance collision rules.

**AS-F25-1**
- Preconditions: S1 manifest has v1. The applicant uploads v2 (pending scan) during review.
- Actor: Admin/secretary
- Action: Opens the completeness review.
- Expected result: Shows manifest v1 as reviewed. v2 is shown as a later version with its scan state.
- Forbidden result: v2 shown as the reviewed file. An unscanned v2 downloadable.
- Source: T&A "Correct/resubmit".

### F26 / F27 / F28 Decisions and decrees

**AS-F26-1**
- Preconditions: Both spouses filed.
- Actor: Manager
- Action: Enters `diss-respondent`.
- Expected result: The UI requires explicit party outcomes and entitlements, which are shown before voting. Entitlements follow those outcomes.
- Forbidden result: Entitlement inferred from the label or the filing order.
- Source: C6.

**AS-F27-1**
- Preconditions: Hearing.
- Actor: Manager
- Action: Attempts to approve or issue "Decision Deferred" or "Reconciled".
- Expected result: Not offered as a votable decision. Deferral is recorded on the hearing. Reconciliation goes to withdrawal.
- Forbidden result: Decree or closure from "deferred".
- Source: `prototype-decision-types.json`.

**AS-F28-1**
- Preconditions: Version N approved. Signed PDF stored for N. Grounds then revised to N+1.
- Actor: Admin/secretary
- Action: Issue.
- Expected result: Refused until N+1 is approved and a certificate signed for N+1 is stored. Votes and approval for N are preserved and do not apply to N+1.
- Forbidden result: Issuance on the stale certificate. Inherited approval.
- Source: DEC01, DEC02.

**AS-F28-2**
- Preconditions: Approved version, no stored signed PDF.
- Actor: Admin/secretary
- Action: Issue.
- Expected result: Refused.
- Forbidden result: Case closed.
- Source: DEC02.

**AS-F28-3**
- Preconditions: Approved; certificate stored.
- Actor: Assigned manager
- Action: Prepares, issues or releases the decree.
- Expected result: Refused.
- Forbidden result: Any decree mutation by the manager.
- Source: Permissions.

**AS-F28-4 (success)**
- Preconditions: As AS-F28-2 with a certificate stored.
- Actor: Admin/secretary
- Action: Issue.
- Expected result: Atomic closure. All open-case claims released. Entitled party gets an availability notice; the other party gets an official decision notice. The certificate stays hidden.
- Forbidden result: Auto-release. Partial closure.
- Source: T&A "Decision, issuance" ¶2.

### F29 Release

**AS-F29-1**
- Preconditions: Issued decree; A entitled to the certificate, B notice-only.
- Actor: Admin/secretary, then A, then B
- Action: Release to A. A downloads. B requests the decree URL.
- Expected result: A downloads the exact PDF. B is denied.
- Forbidden result: B receives bytes or a preview.
- Source: SEC05.

**AS-F29-2**
- Preconditions: Released to A.
- Actor: Admin/secretary
- Action: Withdraws release. A retries a range request and a preview.
- Expected result: Denied. History retained.
- Forbidden result: Cached access.
- Source: SEC05.

### F30 / F31 Withdrawal and closure

**AS-F30-1**
- Preconditions: Two participating filers.
- Actor: A
- Action: Withdraws.
- Expected result: Case stays open. Manager notified. B not notified. Fee retained.
- Forbidden result: Case closed. B notified.
- Source: Build spec "Decisions" ¶5.

**AS-F30-2**
- Preconditions: Only A filed; B is linked but has not filed.
- Actor: A
- Action: Withdraws.
- Expected result: Case closes.
- Forbidden result: B's link treated as a second filer that blocks closure.
- Source: T&A "Decision, issuance" ¶3.

**AS-F30-3**
- Preconditions: Two filers.
- Actor: Secretary
- Action: Records an all-party withdrawal.
- Expected result: Refused (admin only).
- Forbidden result: Accepted.
- Source: Permissions.

**AS-F31-1**
- Preconditions: Case closed.
- Actor: Applicant and manager
- Action: Applicant edits an answer; manager edits a finding; both send messages.
- Expected result: Edits refused. Messages accepted.
- Forbidden result: Edit persisted.
- Source: T&A "Decision, issuance" ¶5.

### F32 / F33 Appeals

**AS-F33-1**
- Preconditions: A and B each file appeals (separate USD 250 fee or authorized waiver each).
- Actor: Manager
- Action: One hearing item; A Accept, B Decline.
- Expected result: One reopened appeal proceeding. B receives a decline notice with optional explanation. Both are notified privately of reopening. The original proceeding stays read-only and the original release is unchanged.
- Forbidden result: Second case. B's decline recloses the case.
- Source: APP01.

**AS-F33-2**
- Preconditions: A's appeal pending.
- Actor: A and manager, concurrently
- Action: A withdraws while the manager records Accept.
- Expected result: Exactly one commits.
- Forbidden result: Both recorded.
- Source: T&A "Appeal acceptance" ¶1.

**AS-F33-3**
- Preconditions: A's appeal disposed.
- Actor: A
- Action: Adds a supplement. Starts a second appeal while the first is still pending (separate run).
- Expected result: Supplement refused after disposition. Second pending appeal refused.
- Forbidden result: Overwrite of the original statement.
- Source: APP02.

**AS-F33-4**
- Preconditions: Original Petition Denied (no certificate); appeal accepted; new decision granted.
- Actor: Admin/secretary
- Action: Issue the appeal decree.
- Expected result: `DCR-[case]-A1`.
- Forbidden result: Base `DCR-[case]` fabricated for the original.
- Source: Build spec "Decisions" ¶3.

**AS-F32-1 (pending D6)**
- Preconditions: B has a different open case; A's appeal is accepted.
- Actor: Manager
- Action: Accept.
- Expected result: Per D6. The appeal is never deleted, and no person ends up with two open cases.
- Forbidden result: B's other case closed or altered.
- Source: APP02.

### F34 / F35 Language and duplicates

**AS-F34-1**
- Preconditions: A uses `notification_locale=ar`. Staff writes return instructions in English.
- Actor: A
- Action: Views the return, the notification and the email.
- Expected result: Arabic chrome. Instructions shown verbatim and escaped. Case number left-to-right inside RTL text. The same permission denials as in English.
- Forbidden result: Automatic AI translation shown as authoritative. Different access in Arabic.
- Source: Build spec translation ¶3; UI01.

**AS-F35-1**
- Preconditions: Exact duplicate-person hold active.
- Actor: Applicant
- Action: Saves a draft; attempts payment.
- Expected result: Save succeeds. Payment and submission are paused.
- Forbidden result: Draft blocked. Automatic merge.
- Source: Build spec step 6.

---

## 3. Conflicts requiring reconciliation

Only conflicts that remain after applying the documented precedence corrections are listed.

**C1. Returned-application corrections vs draft privacy (F08)**
- Build spec "Identity…" says: "Council reads all formally submitted cases… applicant drafts remain private."
- Build spec "Initial application" step 8 says: "Return keeps same case, fee and original signature; preserve corrections/resubmissions." The correction paragraph says corrections "while open preserve original/every field revision".
- Permissions say an applicant answer correction notifies the manager immediately.
- Consequence: In-progress edits to a returned filing could be treated either as live open-case corrections (visible to council and alerting the manager) or as private pre-resubmission work. The applicant and council UIs will diverge without a ruling. → D1.

**C2. Separate assignment actors vs combined roles (F15)**
- T&A says: "require president authorization and separate entering admin/secretary".
- Data dictionary `case_assignments` has separate `president_id` and `recorded_by_id`, but no inequality check.
- Consequence: In a small demo, the president may also hold admin. A distinct-person rule would block assignment and therefore the demo. → D2.

**C3. Agenda request vs direct placement (F16)**
- Build spec says: "Assigned member may request agenda placement for own cases." The data dictionary has `agenda_requests` ("asks to place… no global agenda authority") with `placed_item_id`.
- CLAUDE-START says: "Assigned members can mark their cases for an upcoming session."
- status.md says the manager can "place their case in part 2" directly.
- Consequence: Request-then-place by admin/secretary and direct placement are different workflows. Governance should confirm which one CLAUDE-START's wording authorizes.

**C4. Unknown testimony end time vs a required non-overlap check (F18)**
- T&A says: "Actual durations can be unknown; don't invent end times, but scheduling must confirm non-overlapping segments before invitations for both."
- Consequence: With `ends_at` null, overlap cannot be confirmed. This is either untestable or forces invented durations.

**C5. Hearing applicant message delivery mode (F20)**
- Build spec "Council sessions" says: "Single Send action, no presentation draft/finalize workflow."
- Build spec "Communications" says: "Exact choices `Send Immediately` / `Send after council session` apply email delivery."
- Permissions say: "selected immediate/session delivery semantics apply to manual communications".
- Consequence: It is unclear whether the hearing-update message is a "manual communication" that offers both email timings.

**C6. Decision catalog role labels vs two independent filers (F26)**
- `prototype-decision-types.json` has "Dissolution Granted — Permission to Remarry (Applicant)" and "(Respondent)".
- The build spec says to use the "exact prototype type catalog" and that staff enter "affected parties and conditions". Parties are slots A and B, and both may be filers.
- Consequence: When both spouses filed, "Applicant" and "Respondent" do not identify a party. Inferring entitlement from the label could release a certificate to the wrong person. This review does not propose changing catalog wording. → D7.

**C7. Secretary on-behalf withdrawal (F30)**
- Build spec says: "Admin may withdraw for all."
- Permissions say: "Admin may withdraw parties; secretary no inferred all-party withdrawal."
- CLAUDE-START says: "Authorized staff can record on behalf of parties under the defined rules."
- The correction document says admin and secretary have "default case-operation authority".
- After precedence, the all-party withdrawal is admin only (explicit boundary retained). Still unresolved: whether a secretary may record one party's withdrawal on that party's behalf. → D5.

Checked and resolved by precedence, so not raised: secretary routine alerts, council enrollment, certificate matching, filename convention, report visibility to applicants, the 17:00 cutoff, the replacement decree, and manager answer edits (the explicit matrix says "only if explicitly granted later").

---

## 4. External dependencies

These need credentials, configuration or institutional content. Ordinary implementation work is listed separately below.

| Dependency | Needed for | What is required | Demo impact |
|---|---|---|---|
| Google / Apple applicant sign-in | Registration, linking (F01–F02) | App registrations, callback URLs, server-side secrets | P1. Without them, no genuine applicant login. Synthetic test sessions are not acceptance and must never be used publicly. |
| Microsoft public route | Council sign-in at `ctm.lighthouseway.org` | Production callback (local callback is verified) | Deployment gate only |
| Stripe test mode | Payment (F06–F07) | Test keys and webhook signing secret | The authorized-waiver path can exercise submission. Never show fake success. |
| Outbound and inbound email | Notifications, 10-minute digest, deferred send, priest link, reply routing | Provider, sending domain DNS authentication, inbound routing and webhook validation | Portal-only behavior is demonstrable. Email acceptance (NOT01, MSG01–02, F21) is pending. |
| Institutional text | F05, F23, F28 | Approved bilingual applicant and appeal declarations; medical release wording and scope; type-specific decree templates and signature content; published bilingual applicant form definition, including repeat records | Blocks honest submission, medical collection and decree preparation. The owner must say whether clearly labelled demo versions are acceptable (D8). |
| Reviewed Arabic translations | F34, UI01 | Reviewed translation bundles; the institutional master prompt is already preserved | Partial Arabic can be demonstrated only if labelled |
| President's signature content | Decree issuance | A paper-signed scan is sufficient. No cryptographic signer is selected (do not claim one). | None if a scan is used |
| Transcription / translation provider | Audio, OCR | Deferred (placeholders accepted) | None |
| Backup destination | Live data | Separate recovery location | Not a demo blocker; required before real data |

**Ordinary implementation, not external dependencies:** own-files endpoint (F04), repeat-entry contract (F03, a cross-stream contract), deferred-message transfer on reschedule (F17), completeness review manifest view (F25), search authorization (F24), RLS and grants, ClamAV wiring (the container exists per status.md), decision catalog filtering (F27) and immutability guards (F31).

---

## 5. Decisions requiring the owner

1. **D1:** While a filing is returned, do the applicant's saved corrections become visible to council (and alert the manager) before resubmission, or only on resubmission?
2. **D2:** May one person holding both president and admin roles both authorize and record a manager assignment? Same question for recording their own approval.
3. **D3:** If a spouse who never filed later files independently and exactly matches a closed case, should the filing go to review as a new case, be redirected to the appeal process, or be refused?
4. **D4:** Does a linked spouse who never filed have appeal rights? How are their official notice and any certificate entitlement delivered if they have no CTM account?
5. **D5:** In a two-filer case where one party withdraws:
   - Does the withdrawn party keep the open-case claim until the case closes?
   - Do they receive closure or decision notices?
   - May a secretary record a single party's withdrawal on that party's behalf?
6. **D6:** When an appeal is accepted but the other, non-appealing party has a different open case, does that block reopening for the appellant?
7. **D7:** When both spouses filed, how should "(Applicant)" and "(Respondent)" in the decision catalog map to the two parties? Without changing catalog wording.
8. **D8:** For the demo only:
   - (a) Are clearly labelled demo declaration, release and decree texts acceptable?
   - (b) Without email, may staff see an external priest link once at issuance to deliver it manually?
