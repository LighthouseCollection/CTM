Current validation: **797 PostgreSQL passed, 1 skipped**; no model drift; migration rollback/reapply through0046. Nine new restricted-role withdrawal regressions;17focused withdrawal/appeal checks passed.

# Withdrawal decision across hidden party rows

Backend issue #2. Required migration0046_withdrawal_case_scope after0045.
Exact integration22d1b6ba8bcb75cf1e585f696ac83df01a33de7a returned500 on owner
withdrawal of a returned petition. A private retained-clone diagnostic ran exact
release source with physical current_user=session_user=ctm_app and an outer
rollback. It captured decisions.py332→close_case→171 case.save() rejected by
tribunal_case RLS; no withdrawal persisted.

The service's remaining-party query saw only the applicant's own party. It
incorrectly attempted closure although another hidden participating party remained.
The existing global SQL closure guard correctly rejected that premature closure.
An independent restricted-role joint-filing regression reproduced the same failure.

0046 adds two app-only private functions; PUBLIC execution is revoked, no worker
grant and no general party/claim/request SELECT expansion:

- ctm_withdrawal_can_close(application): one boolean only, bounded to the server's
  withdraw operation/target, active actor, already-withdrawn formal petition and
  own-account/person/party binding (or existing administrator authority). It checks
  all participating case parties, including hidden rows. The service still checks
  owner/version/status/open proceeding under existing locks and updates only the
  bound party before this decision. Existing ctm_close_allowed is unchanged.
- ctm_closed_case_cleanup(case): no data output; requires server close target,
  active actor, existing authoritative close-reason permission, closed case and
  no open proceeding. Deletes only that case's open claims and transitions only
  unfinished draft/sent requests to cancelled/closed. This prevents hidden claims
  from surviving final closure. Original completed reports, source content,
  recipients, tokens and unrelated cases are unchanged. Existing source triggers
  remain active; all work stays inside the enclosing service transaction.

SQLite retains the equivalent unrestricted ORM checks/cleanup. The server binds
actor context explicitly for helper calls, preserving direct authorized service
callers. No browser role/actor/closure permission is accepted.

Validation covers returned/submitted/accepted joint cases under physicalctm_app:
first withdrawal succeeds without closure or other-filing mutation; final withdrawal
closes case/proceedings, clears both claims, cancels draft and closes sent private
requests. Other party rows remain hidden, original submission revision/manifest/
attestation/actor stay identical, and no other-applicant closure notice is sent.
Stale versions, helper misuse, foreign target, no actor, wrong state and workers
remain denied. Existing appeal/decree closure checks are retained in the full suite.

Governance owns serial integration and migration application.0046 grants functions
to existingctm_app; for roles created after migrations, run0046.grant_runtime after
the documented0038/0043/0044 plans. Uninstall drops both functions; rollback must
use matching service code. Coordinate unapplied UI metadata to a unique successor
(proposed0047), preserving all applied0040–0045 history. No operational database,
merge or deployment was performed by backend. Applicant and independent QA must
rerun the exact combined successor and record its SHA; local tests do not close
that acceptance gate.

Four older closure fixtures used an invented synthetic_close reason under the
owner test connection. They now close through the real authorized owner withdrawal
command; all original unsent-draft, blocked-write/concurrency and private-call
assertions remain. No synthetic closure permission was added to production SQL.
