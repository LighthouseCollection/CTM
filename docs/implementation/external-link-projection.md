Current validation: **788 PostgreSQL passed, 1 skipped**, including migration rollback/reapply through0045. Fifteen new physical-role council link projection regressions. No model/route/migration/grant changes in this continuation.

# Council external-priest link metadata

Backend issue #2 / council C05 dependency. Existing GET
`/api/cases/{case_id}/requests/` adds `external_link` only to council-visible
external_priest request rows. Existing request fields/version remain unchanged.

Fields: `priest_name` (recorded external_name), `expires_at` (ISO time or null),
`state`, `can_issue`, `can_reissue`, `can_cancel`. No token, token hash, email,
saved response or delivery claim is exposed. No new route/model/migration/grant.

States, evaluated at one timestamp for the response:

- completed/cancelled retain the authoritative terminal request state;
- otherwise a closed case or proceeding yields closed;
- draft yields not_issued;
- sent with a stored hash and expiry yields active before expiry, expired at/after;
- other/incomplete legacy configurations yield unavailable.

This is the current council view, not historical token status. Old/reissued tokens
cannot be recovered. Reissue resets recorded name/expiry as the existing command
requires; the prior capability remains invalid. Existing anonymous capability
errors remain uniformly concealed and do not expose these distinctions.

Management flags require existing writer authority (admin/secretary or actual
assigned manager), open case/proceeding and unfinished draft/sent request. Issue
applies to draft, reissue to sent (including expired/incomplete legacy link),
cancel to either. The commands remain authoritative and recheck state under lock;
a projected flag does not guarantee a later command after concurrent closure.
Request-version compare-and-save requirements remain unchanged.

Proceeding/case are joined once rather than per-row queries. Applicant request
filters and forced RLS remain unchanged; ordinary request rows get no link object.
Council frontend adoption is owned by council; no UI files are edited here.

Remaining C05 backend contracts: HTML boot, capability-safe completion receipts,
recording and paper completion, printable request and actual invitation delivery.
This projection alone does not complete those workflows or claim delivery.
Governance serial integration and independent exact-successor QA remain required.
