# Current permissions and notifications

All permissions are server-enforced, deny by default and apply to derivatives, links, search and downloads. Role membership does not bypass subject privacy or signed medical scope. Latest restored admin/secretary functional authority applies; author-only restrictions remain explicit.

| Action | Applicant | Other council member | Assigned case manager | Admin / secretary | President |
|---|---|---|---|---|---|
| Read never-submitted applicant draft | Own | No | No | No by default | No |
| Read submitted case | Own permitted projection | All cases | All cases | All cases | All cases if council |
| Read applicant answers/history/files | Own; file history excluded | Submitted all | Submitted all | Submitted all | Council read |
| Correct submitted answers/files while open | Own | No | Files on behalf; answer edits only if explicitly granted later | Yes, actual actor retained | No extra writer grant |
| Read internal findings/notes/report narrative | No | Yes | Yes | Yes | Yes |
| Create/revise findings | No | No | Yes while proceeding open | Yes while open | Only if otherwise authorized |
| Add internal notes | No | No | Yes | Yes | Only if otherwise authorized |
| Edit existing note | No | Own plus current write eligibility | Own plus current write eligibility | Own only | Own plus current write eligibility |
| Prepare intake/report request | No | No | Yes | Operational default, retain manager/author | Only if otherwise authorized |
| Respond to intake/request | Own assigned request | No | Conduct/record own interview | Enter/upload on behalf with provenance | No extra grant |
| Revise report narrative | Submitted own response read-only | Original author plus current authorization/open proceeding | Original author only | Cannot rewrite another author's narrative | No extra grant |
| Read applicant-completed report | Own submitted answers only | Council content | Council content | Council content | Council content |
| Read medical report/OCR | Own | Within release scope | Within release scope | Within release scope | Within release scope |
| Sign medical release | Own subject only | No | No on behalf | No on behalf | No on behalf |
| Read unreviewed generated report text | No | No | Reviewer/authorized processor | Processing/support scope, not blanket publication | No extra grant |
| Review/correct generated interview report text | No | No | Assigned reviewer | On-behalf entry retains manager review | No extra grant |
| Review/correct testimony generated text | No | No by assignment alone | No by assignment alone | Yes | No extra grant |
| Create/reschedule/close council session | No | No | No | Yes | No automatic administrative grant |
| Request agenda for assigned case | No | No | Yes | Manage agenda | If assigned or separate role |
| Present case hearing | No | No | Yes only | Only if assigned presenter | Only if assigned presenter |
| Choose/reassign manager | No | No | No | Records president authorization | Authorizes |
| Vote | No | Own | Own | Own or record another's | Own |
| Enter type/grounds/reason | No | No | Yes | Yes | If separately authorized |
| Final approval | No | No | No | Records president on behalf | Approves |
| Prepare/issue/release decree | No | No | No | Yes | Signs/approves; no inferred system role |
| Download released decree | Exact entitled recipient | Council read | Council read | Council read | Council read |
| Withdraw own petition/appeal | Yes under lifecycle | No | No on behalf | Admin may withdraw parties; secretary no inferred all-party withdrawal | No extra grant |
| Appeal supplements | Own pending appeal only | No | No on behalf | No on behalf | No |
| Record appeal Accept/Decline | No | No | Yes | Yes | If otherwise authorized |
| Send private case message after closure | Own thread within portal | No | Yes | Yes | If otherwise authorized |
| Case audit | Own answer history only | Yes | Yes | Yes | Yes |
| System audit | No | No | No | Yes | Only with admin/secretary role |
| Add council member | No | No | No | Existing admin only | Only with admin role |
| Deactivate/reactivate/change roles | No | No | No | Admin/secretary | Only with appropriate role |
| Shared questions/templates/system settings | No | No | Personal reusable templates only | Yes | Only appropriate role |

External priest has only the unexpired request capability: limited subject context, own unfinished response, writing/recording/upload as permitted, submit once. No case, search, council account or later submitted-response browsing. Store only token hash; no token in audit/body logs. Revoke on replacement/paper completion/cancellation/closure/submission.

## Notification routing

| Trigger | Recipients | Timing |
|---|---|---|
| Applicant answer correction, upload, appeal addition | Current assigned manager | Portal immediate; email after10minutes without another qualifying applicant change |
| New applicant case message | Current assigned manager | Portal immediate; applicable communication email mode |
| Submitted requested report/assessment | Current assigned manager | Immediate portal/email |
| Withdrawal of petition/pending appeal | Current assigned manager | Immediate portal/email; never notify other applicant |
| No manager yet, intake submission/resubmission | Admin/secretary completeness queue | Portal/email intake routing; engineering default immediate |
| Duplicate review hold, chargeback/reversal | Admin and secretary | Immediate portal/email |
| Staff answer/file correction, recommendation revision | Nobody from correction trigger | Retain history; no batch reset |
| Manager assignment change | Outgoing/incoming manager and each applicant privately | Immediate portal/email |
| Testimony scheduled/rescheduled/cancelled | Affected applicant | Immediate portal/email; one-day reminder for active appointment |
| Applicant Confirm/Reject testimony | Current assigned manager | Immediate portal/email; routine secretary subscription superseded |
| Case hearing pending update | Intended applicant(s) separately | Sent private communication; selected immediate/session delivery semantics apply to manual communications |
| Decree issuance, denial, appeal disposition/reopening | Applicable applicant(s) privately | Immediate portal/email; certificate stays unreleased |
| Decree released | Exact entitled recipient | Immediate portal/email |
| Applicant account suspended/reactivated | Affected applicant | Email |
| Draft expiry warning | Draft owner | Seven days before current180day inactivity deadline; portal/email |

Notification services resolve current manager at dispatch, deduplicate role-overlapping accounts and recheck authorization. No DOB-bearing reference, report body or medical content in alert summaries. An administrator's authority to act does not make them a routine subscriber.

## Database enforcement contract

Do not grant API users direct table access. Use a non-owner, non-superuser, non-BYPASSRLS application role and separate migrations/worker credentials. Transaction-local actor context is derived from validated server session, never from browser role/person claims. RLS and object policies must protect applicant-owned sources, council-only sources, medical release scopes, draft privacy and version-specific release. Revocation/suspension is checked on each sensitive request.

Schema DDL declares relationships and some uniqueness/check constraints; it intentionally does not pretend the matrix has been enforced by those alone. RLS migrations, guarded mutation services, cross-case composite identity checks and immutable-row guards are required implementation work. Withhold production runtime grants until these and isolation tests pass. Background processing has narrowly scoped access, not broad council impersonation.
