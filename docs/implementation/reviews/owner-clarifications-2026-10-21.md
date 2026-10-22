# Owner clarifications following independent review

Source: direct user answers in the CTM governance conversation, 2026-10-21 Pacific.
These answers supersede conflicting earlier proposals. The adjacent Perplexity
review is an external acceptance checklist, not proof of present implementation
defects. It did not inspect current code/PRs or all approved sources. Reconcile
each finding against current PRs before adding work or claiming a defect.

## Recorded owner decisions

| Review item | Owner answer / resulting requirement |
| --- | --- |
| D1 / F08 / C1 | NO: while returned, saved corrections are not visible to council before resubmission. Council receives the last formal submission; pending answer/file changes must not leak through detail/history/manifests/previews/search or routine correction alerts. Resubmission exposes the new formal snapshot and retains originals. |
| D2 / F15 / C2 | YES: one person holding both president and admin authority may authorize and record an assignment. Keep authorizer and recorder fields even when equal; do not require distinct people. This answer explicitly concerns assignment, not every dual-role approval action. Existing direct presidential approval rules still apply. |
| D3 / F12 | A spouse who did not previously file may submit against the closed case. It goes to the queue for council presentation. Acceptance based on new information reopens the original case, similar to appeals; submission alone does not reopen it or append mutations to the closed proceeding. |
| D4 | The owner answered “same as above”: a linked spouse who never filed can use the same later-filing/new-information consideration route. Do not deny access to that route solely for not being an original filer. This did not specify offline delivery to someone with no account. |
| D5 / F30 / C7 | Owner response: “if they both agree to withdraw yes.” Record joint agreement as the prerequisite for closing a two-filer case by withdrawal. This response was to the combined question about one-party withdrawal and secretary recording. It does not define claim release, eventual notices or unilateral secretary authority; do not infer permission for unilateral withdrawal on behalf of another person. Preserve the already-confirmed no-other-party withdrawal notification rule. |
| D6 / F32 | Owner states this will not happen: closing the case closes it for every applicant. Verify shared closure atomically ends every participating applicant's open-case claim. Keep the one-open-case invariant on reopening; this answer does not authorize overwriting or closing another unrelated case. Do not introduce a new user-facing conflict process as though the owner approved one. |
| D7 / F26 / C6 | “Parties” means the husband and wife involved. Use names and explicit per-party entitlements, never infer recipients from who filed first. Suggested user-facing alternative: “Spouses”. This does not settle a deterministic reinterpretation of every legacy Applicant/Respondent label in a two-filer case. |
| D8(a) / F05 | No visible “demo” labels are required. Review/sample content may read like live content. This supersedes the review's recommendation that every sample text carry a visible demo label. Internal fixture provenance, safe isolation, no fake external success and no forged real signatures remain intact. It is not approval of any particular institutional declaration/translation/template wording. |
| D8(b) / F21 | Manual delivery of an external priest capability link was not explicitly answered. Do not treat the answer about visible demo labels as authorization to expose or deliver a bearer link. Keep the requirement tracked. |

## Review coverage and tracking

Preserve F01–F36 and all AS-Fxx scenario references in grouped GitHub acceptance
issues. Each implementation owner should record current code/PR/test evidence and
mark a finding addressed, remaining, superseded or requiring clarification. Do not
repeat already-resolved endpoint404/405 reports as verified current defects.

Remaining questions should be narrow: joint-secretary withdrawal authority if an
implementation actually needs it; precise named-party mapping for legacy labels;
offline delivery for an unregistered recipient; manual priest-link delivery; and
review-only institutional content versus approved published content. Preserve the
owner's answers above instead of reopening all eight original questions.

No protected build-spec source is rewritten by this addendum. Schema/permission
reconciliation must reference this later direct-owner instruction explicitly.
