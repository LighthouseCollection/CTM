# Case Investigation and Factual Discovery

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

Proposed title for the grouped interview workspace: **Case Investigation and Factual Discovery**. The user requested petition-nature/template organization, reusable common question families, alternative council viewing modes, integrated submitted material, and medical/psychiatric test records with signed release disclosure. This is the architecture and planning specification, not a built CTM feature or final legal release form.

## 1. Organize once, display in different ways

Topic group → Question categories → Questions → attributed answers and source evidence → assembled report. Report identification and foundational questions are always present. There is no additional template selector between Topic group and Question categories.

The assigned member selects the appropriate template/families rather than answering every possible question. The same Children, Money, Intimacy, Evidence or Chronology family may appear in multiple templates. Store one stable family/question definition and version; template membership/order is a relationship, not a separately editable copy. English/Arabic wording remains versioned under the same question meaning.

Two council views use the same data: **By Topic group**, or **By Question categories**. A view change does not change selected questions, delete answers, generate another interview or create different versions of the facts. A question reused across two memberships appears once in a given interview/report unless explicitly repeated for a different event/subject with a separate response instance.

Template groupings are organizational presets, not new canonical grounds or automatic decisions. Earlier rejected communication, multiple-ceremony, full prior-marriage and appeal question templates are not reintroduced. The accepted ordinary appeal process remains. Priest free-form testimony is a separate requested report, not a forced interview question bank.

## 2. Submitted application facts become confirmation context

The interview uses exact original application question/answer revisions, with the submitting person, submission date and field history available to authorized council. For example:

- Source: Applicant A's submitted church-marriage date and linked MC certificate version.
- Question: “Your application states [date]. Please confirm that date or explain what needs clarification.”
- Result: a separate interview answer/confirmation event, not an automatic edit of the signed application or case-number/marriage-match inputs.

Preserve the source version that was displayed during the question. Later source corrections must not retroactively change an earlier interview's displayed context. Authorized application corrections remain explicit, historical and attributed. Unknown/different assertions remain visible as such; do not merge the spouses' accounts.

## 3. Submitted evidence belongs in the guided inquiry

Evidence is not merely an attachment list outside the questionnaire. Link the exact submitted statement/document/audio version to the relevant family, question, alleged ground and event, with the supplying party and timestamp. A statement alleging an affair is an assertion, not proof of the affair.

Example Infidelity inquiry:

1. Source context: [party]'s submitted statement/evidence [version/date].
2. Confirm whether this is the statement/item the interviewee is referring to, within permitted disclosure scope.
3. Ask what the interviewee personally observed, occurrence date versus discovery date, other source of knowledge and what the item supports.
4. Record clarification and exact evidence references alongside the answer; keep council assessment separate.

Source inclusion is council-authored linking/reuse of stored context, not AI extraction into answers. No new evidence-description requirement is imposed on the applicant: AF15 was rejected. Existing correct-location upload rules continue. Do not automatically reveal Applicant B's private evidence or wording to Applicant A during an interview. Evidence visible in the council workspace does not become applicant-visible merely by being linked to a question, a report or a confirmation prompt.

## 4. Medical and psychiatric tests and signed releases

Add a conditional medical/psychiatric evaluation area to applicant submissions and council records. Support existing tests/reports supplied when relevant, and council-requested tests/evaluations. Do not make testing universal, introduce a diagnosis or delay all applications until a test exists. Test type, subject person, request/report provenance and signed authorization are different records.

User requirement: medical/psychiatric testing and disclosure requires signed release disclosure. Track the exact release text/version, subject/signatory, signature/date and intended purpose/provider/recipient scope alongside the relevant evaluation/report. Staff cannot sign as the applicant. A request for a signature is not a completed release; a written test result is not itself authorization to disclose it. Final form wording, permitted signatories, revocation rules and precise request/access sequencing require institutional confirmation. Do not claim the data model alone creates legally valid consent.

Applicant side: see own requested release/test instructions, supply own authorized test/report and complete the required signed release. No other-applicant medical access or global medical-history questionnaire. Council side: track request, release state, provided report/version and authorized disclosure/review. A report offered without its required release must not automatically enter general case-document disclosure/search; preserve receipt in a restricted pending-authorization scope rather than delete it or falsely mark the release signed. Exact permitted pre-release handling must follow the finalized institutional policy.

All source medical files are private/versioned. Retrieval, OCR/search snippets, question context, report assembly and copied links must check the same release/recipient/purpose scope. Signing a release for one evaluation does not authorize every medical record or blanket external sharing. Existing local-only document OCR remains. Previously approved audio AI processing does not authorize sending medical reports or medical documents to an external AI API. No automatic medical-document AI analysis is added.

The previously unresolved exact medical interview question wording remains a content review item; the new signed-release/testing requirement is confirmed independently of that wording.

## 5. Data relationships

| Proposed record / extension | Relationships and preservation |
|---|---|
| `interview_topic_category_memberships` | topic-group version, reusable question-category version and display order; category/question memberships reference stable versioned definitions, no copied answers |
| `interview_question_context_links` | exact interview/question instance; source application-answer revision, assertion or file version; party/proceeding; source role and linking actor/time |
| `interview_confirmation_events` | exact displayed source version; interview answer; confirming person/actual recorder/time; confirmation or explanation distinct from source edit |
| `interview_response_evidence_links` | answer/question/event/family; exact evidence version and providing party; duplicate-safe relationships |
| `evaluation_requests` | case/proceeding; subject person; medical/psychiatric type; requesting authorized staff/time; relevant purpose; provider reference if known |
| `release_form_versions` | exact bilingual release definition/version and digest; publication provenance; not a mutable generic consent flag |
| `evaluation_release_attestations` | evaluation/purpose scope; subject/signatory; exact form version/text/language; retained signature version; signing time and actual capture actor |
| `evaluation_reports` | evaluation/subject; source/uploader; exact retained file version; authorization linkage; pending/released access state within approved policy |
| `evaluation_disclosure_events` | report version, recipient/purpose, authorization reference, actual actor/time and access/audit provenance |

Reuse ordinary signature, file-version, case/person, notification and audit systems. Required relationship checks prevent a release or report belonging to one party being used for the other. Closed original proceedings remain locked; new substantive evaluation material belongs to the authorized open/appeal proceeding. No on-behalf applicant appeal supplements are authorized by this addition.

## 6. Research prompts rather than automatically adding questions

[Category and question research prompts](CTM-category-research-prompts.md) provide a master prompt, one prompt for each family and a focused prompt for each current detailed question. They ask another AI to find narrowly justified factual follow-ups, cite reliable counseling/research sources, avoid diagnostic/legal/canonical conclusions, and identify duplication before proposing additions. They do not authorize source medical upload to an AI. Use anonymized template wording only.

No new researched follow-up is published automatically. Accept useful additions only after reviewing their purpose, branching, redundancy and institutional fit. Keep required opening/identity, author/source histories and the distinction between interview, transcript, medical report and council finding.

## Full bank with optional per-question help

User approved retaining the full question bank and adding collapsed guidance/follow-up prompts under each question, rather than replacing it with a short bank. The planner retains all 78 original IDs/primary wording. Perplexity optional editorial guidance is attached separately, not treated as verified external authority or new required fields. Guidance never becomes an answer or part of the case report. The pending medical wording remains visibly a draft when reviewing the full bank.

Report identification (case, marriage, subject full name, interviewer and date/time) is always first and separate from substantive foundational interview questions. Common recording identity opening, requested outcome/basis, submitted-application confirmation and closing are retained regardless of optional topics. Additional detail can be agreed without silently changing the original bank. Plain investigation labels replace earlier technical grouping phrases. View switching does not alter saved content or selections. Only the planning HTML was updated; no production UI/database was built.

## Confirmed planner terminology and organization

The current planner uses eight Topic groups from the reference comparison and the seventeen Question categories supplied by the user. “Common question family” is replaced by “Question categories.” The authoritative planning mapping is `reference-study/interview-topic-group-model.json`, generated by `build_topic_group_planner.py`. Questions retain their original IDs and wording; categories are reusable across Topic groups, with duplicate question IDs displayed once per interview. Identification and five foundational questions cannot be removed by clearing optional categories. All 78 questions have expandable optional guidance. Selecting an organizational group does not restore rejected supplemental questions. The separate priest report remains free-form.


## Adopted contextual questioning — 2026-10-20

The user accepted the complete [Context-Sensitive Investigative Questions companion](CTM-context-sensitive-investigative-questions.md) for the question bank, intake-template preparation and reporting workflow. This supersedes the earlier presentation rule that every optional probe must be folded into the main question. The 59 existing main questions and agreed category names remain unchanged. The companion headings do not rename or split those categories. No retired question is reactivated; no removed standalone EVD section is restored. References to EVD mean existing evidence/file-version links, not a new EVD questionnaire.

The assigned case manager priest chooses Topic group → Question categories → Questions, with the current foundational questions retained, and can add case-specific questions. Each stable question ID has versioned conditional prompts, a trigger and avoid/reuse guidance. Ask only for missing relevant facts after checking the application, earlier responses, chronology and authorized evidence. Prompts are optional, not required fields or proof thresholds; no automatic branching or automatic inference is adopted. A completed response is referenced rather than collected again. Keep each party's account and evidence permissions separate.

Template preparation and council interviewing can use these prompts as interviewer aids. They are not automatically inserted as extra applicant questions; the case manager may explicitly select or adapt a relevant clarification before sending. The exact sent questions and their order are preserved; the recipient's submitted response remains locked as already agreed. Sending freezes questions, not a copy of all guidance. Follow-up investigations create separate linked intakes/reports. Main wording changes still require an explicit decision; acceptance of the companion does not apply the separate seven-revision review.

Interviewer-only avoid/reuse instructions and the separate council assessment guide remain guidance, not answers, applicant-facing report content or automatic findings. The original main question, optional prompt definition/version and any clarification actually asked must be distinguishable. Human council findings remain separate from attributed answers, source evidence, transcript and priest testimony. No credibility scoring or canonical decision automation is introduced.

Medical signed-release, restricted disclosure and local document processing rules continue. Audio transcription authorization does not authorize external medical-document AI processing. No extra mandatory uploads, child interviews, general witness module or broad medical-history collection is added.

The planner now shows available prompts in collapsed **Conditional follow-up prompts** under the corresponding questions, with no empty helper section. This is a planning artifact only. Full trigger/avoid-reuse guidance and council assessment text remain available in the adopted companion.


## Current medical / psychological workflow authority — 2026-10-20

The user delegated completion of this section using prior CTM choices. [Medical and psychological report workflow](CTM-medical-psychological-report-workflow.md) is authoritative for requests, optional council-recommended doctors, alternative providers, signed release capture, private applicant uploads, council access within authorization, local OCR/search, case-manager-only routine notifications, revisions/follow-ups, reassignment and closure. It specifies architecture only; no production implementation exists.

This supersedes earlier conflicting admin/secretary on-behalf case-operation permissions for this section. Those roles support system-level/cross-program administration; they do not gain operational write access to assigned-case evaluation requests by role alone. Case-manager responsibility does not remove council case-read access or the signed report-disclosure scope. The exact institution-approved release text remains a document-content dependency. No external doctor portal, automatic clinical judgment or external medical-document AI processing is introduced.


## Confirmed template management and closed reports — 2026-10-20

[Template-management workflow](CTM-template-management-workflow.md) is the current authority for system-level shared-library publishing by admin/secretary; case-manager personal reusable templates; submission of personal templates for shared publication while keeping the personal original; retirement without loss of history; preserved unsent drafts with explicit refresh; and immutable sent-question snapshots.

Reports cannot be edited after case closure, including clerical corrections. Earlier report-author editing permissions apply only while the relevant case/proceeding is open. Reopening preserves the prior closed reports; new material follows the authorized appeal proceeding. These are documentation decisions, not implemented database permissions.
