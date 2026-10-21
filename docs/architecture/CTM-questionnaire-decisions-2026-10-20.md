# Questionnaire decisions reconciled

> **Current authority — latest corrections (2026-10-20):** [Access and workflow corrections](CTM-current-access-workflow-corrections.md) supersede conflicting older passages below. Admin/secretary retain functional case authority; case workers do not manage decrees; only existing admins add council members; no council membership requests. Microsoft for council and Google/Apple for applicants handle authentication/recovery; CTM has no local password system or fallback. Replacement-decree workflow is removed. The settled exact marriage-date/both-DOB matching rule is not an open decision.


Source: user's pasted answers to `ctm-architecture-review-2026-10-20-v1`. Clarifications take precedence over radio choices. This register supplements the confirmed decisions and workflow database design. Documentation only; no software, migrations or provider setup performed.

## Case linking

- **L01 confirmed:** retain the first-created case number. Other allocated numbers become permanent historical references to the retained case; all submissions/payments/actors remain preserved.
- **L02 delegated engineering choice:** either check timing is acceptable. Design choice: check for an existing match before allocating a number and recheck under the submission transaction; this avoids unnecessary numbering/consolidation without changing matching policy.
- **L03 confirmed:** multiple matching marriage records require admin/secretary review rather than arbitrary automatic selection.
- **L04 clarification changes prior rule:** certificate number and/or both birth dates provide alternative evidence. Unknown or incorrect birth dates must not categorically prevent certificate-based matching. Exact marriage date remains mandatory from the earlier rule. The minimum certificate route needs one focused confirmation: whether exact marriage date plus exact certificate number suffices despite missing/different birth dates. Do not silently treat certificate number alone as globally unique or discard conflicting assertions.
- **L05 confirmed:** later answer changes do not automatically move an established case link; only explicit admin/secretary association correction does.
- **L06 confirmed:** admin/secretary can correct wrong associations, preserving every source case number, submission, payment and audit event. Do not conflate case association correction with merging person identities.
- **L07 confirmed:** ambiguous applicant/spouse mapping requires staff review before activating applicant access, even when a marriage match exists.

## Other-party onboarding

- **O01 clarification:** registration-request email is acceptable only when initiated by admin, secretary or case manager. Do not automatically send it just because a second-party row was added or a matching independent submission was found. Use existing assigned member as case-manager mapping pending clarification if a distinct role is intended; no new role or broader party-link authority is inferred.
- **O02 confirmed:** admin/secretary may correct/cancel pending recipient associations; retain history and prevent stale address activation.
- **O03 confirmed:** verified account email change preserves case links, person identity and history.
- **O04 confirmed:** a linked second party wishing to file completes their own regular application, with existing per-filer fee rules. Joining/responding alone is not a paid filing.

## Intake

- **I01 confirmed:** return sends private portal/email correction instructions immediately.
- **I02 confirmed:** resubmission returns to completeness-review queue and notifies admin/secretary. Channels/timing not separately specified by this answer; use existing notification infrastructure without inventing a new channel requirement.
- **I03 confirmed:** first accepted application can reach assignment agenda while the other application is incomplete/returned. Separate application-review states from shared case lifecycle.
- **I04 confirmed:** conflicting open case for a different marriage pauses linkage for admin/secretary review; never permit two open cases or auto-close one to proceed.

## Decrees

- **D01 confirmed:** granted Declaration of Nullity entitles both parties, but actual certificate access requires admin/secretary release; otherwise send the decision notification. Institution's detailed certificate handover/distribution workflow is deferred explicitly.
- **D02 confirmed:** conditional permission identifies entitled parties and stated conditions explicitly.
- **D03 confirmed:** conditional decree may issue and close the case while conditions remain future remarriage requirements; do not invent pre-issuance fulfilment tracking.
- **D04 confirmed:** subsequent appeal decrees use A2, A3, etc. by decree-producing appeal proceeding, not one suffix per applicant application.
- **D05 confirmed:** earlier released appeal/original certificate access stays until explicitly changed. This concerns access, not continuing decree validity; see H03 clarification below.
- **D06 no:** do not introduce a separate signed-decision-notice requirement/template workflow. A decree is a certificate issued by the Diocese of Los Angeles. Existing ordinary official-notice messaging remains.
- **D07 clarified:** signature and date are captured for either digital signing or a physically signed/dated certificate uploaded to CTM. Preserve separate actual upload/issuance timestamps; the answer does not require a new manually entered physical-signature-date field.

## Appeals

- **A01 confirmed:** another open case blocks acceptance/reopening until admin/secretary resolves the conflict, without erasing the appeal.
- **A02 clarification supersedes closure-only filing:** either party can independently submit an appeal at any time, including while the other party's appeal has reopened that same case. Do not block an otherwise eligible draft solely because the shared case reopened. Existing one draft/pending appeal per applicant/case, fee and new-information rules remain. Do not create a second open case/proceeding just because another appeal is accepted into an already reopened case.
- **A03 confirmed:** new-information appeal may be filed again after decline without waiting for another closure.
- **A04 confirmed:** after withdrawal, a fresh appeal may be filed with a fresh fee; old submission/payment remains.

## Historical records

- **H01 confirmed:** admin may keep historical data-entry work in progress before council publication. Distinguish staff entry workspace from applicant drafts and finalized case records.
- **H02 confirmed:** admin explicitly confirms open/closed status at historical-entry finalization; never fabricate unknown historical dates or decisions. Known open historical cases still count toward one-open-case constraints.
- **H03 confirmed with interpretation boundary:** retain original historical decree numbers. Only one decree may be current/valid at a time; old replaced decrees must be marked void and preserved, not deleted. This does not authorize bulk voiding of all historical decrees merely upon import. Exact voiding trigger and treatment of previously released access need clarification with D05 before physical design.
- **H04 confirmed:** historical signed decree requires explicit recipient release.
- **H05 confirmed:** admin/secretary may correct historical transcription errors after finalization, retaining original and revisions/actors/times. Narrow data-entry correction exception only, not alteration of the signed ruling.

## Communications

- **M01 confirmed:** admin/secretary can version English/Arabic system-message templates; sent content never changes retroactively.
- **M02 confirmed:** failed email deliveries visible to admin/secretary for contact correction/retry; portal/source action remains committed and delivery history retained.
- **M03 confirmed:** applicant notification of assigned-member change uses portal and email.

## Testimony and processing

- **T01 clarification supersedes testimony cap:** no fixed testimony recording duration/file-size cap is wanted; require an open-source audio recording component. Original ordinary audio-attachment limit remains 100 MB unless separately changed; the testimony capture/upload path is the approved exception. Storage, resumable capture, chunking and provider request limits must not become an arbitrary user-visible testimony cutoff. No recorder/provider selected or installed here.
- **T02 confirmed:** rescheduling retains old Confirm/Reject response and requests a fresh response against the new appointment version.
- **T03 confirmed:** admin/secretary can correct speaker labels and map them to actual people, preserving AI source and every revision.
- **T04 confirmed:** audio remains usable if AI processing fails; admin/secretary may retry without losing source material.
- **T05 confirmed:** admin/secretary reviews generated transcripts/translations before making them visible to other council members. Add a staff-review visibility boundary independent of audio access; no applicant access. Preserve reviewed/released exact versions and actor/time. Original AI output and edit history remain retained.
- **General requirement:** an open-source PDF scanning component is needed. Distinct from existing local-only OCR/text extraction. Scanning UI/device integration and component selection remain later work; no external document processing is authorized by this request.

## Proposed relational additions/adjustments

- `case_identifier_aliases`: retained original case number, canonical case FK, consolidation/correction event and actor/time; no number reuse. `case_association_events`: source applications/cases, retained case, cause/matching inputs, actual actor/system and timestamp. Case association correction never rewrites source submission actors or payments.
- `marriage_match_reviews`: candidate/source facts, matching rule version, ambiguity/conflict, review actor/outcome/time. Automatically link only a unique marriage with unambiguous party ownership and valid open-case constraints. Date/certificate inputs retain both applicant assertions, not one overwritten value.
- `registration_invitation_events`: authorized staff sender, pending recipient association, case, exact sent message, delivery/actor/time; reuse existing email/notification infrastructure. Stale/cancelled association cannot activate via late verification.
- `historical_entry_workspaces` and immutable finalization events: entered-by admin, working fields/evidence, explicit open/closed classification, publication, and scoped transcription corrections. Enforce known historical open-case claims before publication where identity is known; no hidden conflicting active cases.
- `decree_validity_events`: active/void status, superseding decree reference, effective event, actual actor/time. Partial unique current-valid decree per case; all old certificates retained. Decree validity is distinct from file access and clerical document versions. Exact invalidation trigger remains unresolved.
- `testimony_text_review_events`: exact transcript/translation version, reviewing admin/secretary, review/release action/time. Other council retrieval/search includes only reviewed/released generated versions. Audio retains existing council-only access; staff processing retains AI original/revisions. No new public workflow screens approved here.

## Follow-up required

1. Confirm the certificate matching route: exact marriage date plus certificate number sufficient when birth dates differ or are missing?
2. Specify when a prior decree is marked void and whether its already released certificate access remains until explicit withdrawal. Single valid decree and retained historical access are separate questions.
3. Confirm whether "case manager" means assigned council member if a distinct role is intended. No new role is created implicitly.
4. Detailed decree-certificate handover and applicant-portal behavior remain deferred by the user. Select open-source recording/scanning components during later technical evaluation.
