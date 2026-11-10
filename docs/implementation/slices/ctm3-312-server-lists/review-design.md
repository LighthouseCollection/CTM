# ctm3-312 design review (G5a, round 1, full)

- Reviewed: PR #317, commit `a9f7e4f` (`design.md`, `contract/post-list-*.json`, ADR 0001, `brief.md`), against `origin/main` `4f030a2`.
- Reviewer: ctm3-code-reviewer. Result: **Fail**. Build tasks are not released until the blockers below are fixed and re-reviewed.

```
SPEC: NOT COMPLIANT    QUALITY: REQUEST CHANGES
```

## Strengths

- Count rules are right and in one place: the total runs on the same scoped, filtered and searched queryset (design.md:93); `Exists()` instead of joins (design.md:99); `total: null` for Python-hidden audit rows (design.md:94).
- Applicant limits are right for SEC01: search on `number` only, no name or manager sort keys, out-of-scope `ids` return an empty page instead of a 403 (design.md:95-98).
- The Los Angeles cases are correct. I checked them by hand: 2026-11-02T07:59Z is 23:59 PST on Nov 1, 08:00Z is the next day, 2026-11-01T07:30Z is 00:30 PDT, and 2026-11-11T07:30Z is 23:30 PST on Nov 10 (design.md:254-255).
- The scoping matches today's code: applicant `Party.account` (api.py:507), `visible_applications` (policy.py:36), `existing_admin` for members (api.py:954), `administrator` for accounts and audit, `staff` + `case_for` for case audit (api.py:1870).
- Ran on the PR head: `node scripts/check_slice_trace.cjs ctm3-312-server-lists` → OK (14 IDs); `node scripts/check_ownership.cjs --slice ctm3-312-server-lists` → OK (10 files).

## Missing / Extra / Misunderstood

- **Missing, AC-9** [design.md:213-217, design.md:74]: see blocker B1.
- **Misunderstood, AC-1** [contract/post-list-applications.json:35-44, contract/post-list-sessions.json:35-36]: see blocker B2.
- Extra: none.

## Blockers (Important)

- **B1 [static/ctm/council.js:3381] NEW: AC-9 lookups of sessions are not planned, and the sessions list cannot do them.**
  - Why: AC-9 says no screen downloads a whole list to find one row. Home finds the lead session with `api("/api/sessions/")` and then `.find(row => row.id === leadId)` (council.js:3381-3385). Five other callers download all sessions and filter in the browser: council.js:2045 (planned sessions for a hearing), council.js:2640 (agenda), council-case.js:3821 (scans the agendas of the first 100 sessions to find this case's hearings), council-decree.js:987 (same, first 24), app.js:1154 (communications). None of them is in the hotspot plan (design.md:213-217) or in T6/T7. The `sessions` list has no `ids` filter (design.md:74). Once more than 100 sessions exist, the GET cap (api.py:1100) silently drops sessions on these screens.
  - Fix: add `ids` (1..100 UUIDs) to the `sessions` filters and contract. Put council.js:3381, council.js:2045 (`state: planned`) and council.js:2640 in T6. For the "hearings of this case" scans (council-case.js:3821, council-decree.js:987), either add a `case` filter on `sessions` (sessions whose agenda holds the case) or list them in design §10 as an explicit follow-up issue, with the reason. Do not leave them unmentioned.

- **B2 [contract/post-list-sessions.json:35] NEW: the contract items and errors do not match what the server sends.**
  - Why: design.md:26 says every item is the existing projection, unchanged, and T2/T3 assert that "item keys equal the contract response" (design.md:241, 249). Both cannot be true:
    - sessions: `can_edit` and `can_delete` do not exist. `session_capabilities` sends `can_manage`, `can_close`, `can_activate`, `can_reschedule`, `can_record_attendance` (projections.py:211).
    - applications (contract/post-list-applications.json:35-44): the council item from `application_data` + `staff_application_data` (api.py:197, projections.py:90-) also has `respondent_name`, `applicant_gender`, `respondent_gender`, `assigned_to`, `submitted_version`, `questionnaire`, `manifest`, `reviews`, `can_review` and more. The contract shows a subset.
    - CSRF (every file, e.g. contract/post-list-cases.json:76): `{"detail": "CSRF Failed"}` is a DRF body. CTM uses Django's `CsrfViewMiddleware` (settings.py:43) without `CSRF_FAILURE_VIEW`, so the real response is an HTML 403 page. In production an unauthenticated POST also gets this 403 before the 401 (middleware order). The test client hides both.
    - members (contract/post-list-members.json:153): `"Administrator required."`, but `existing_admin` raises "An existing administrator must authorize council role grants." (staff_roles.py:55).
  - The frontend tasks (T5-T7) load these files as fixtures, so screens would be built against keys the server never sends. This is the "works only against a fixture" failure.
  - Fix: build each contract item from the real projection (keys, order and nesting), with fictional values. Describe the CSRF case as "403, non-JSON body" and decide what `CTMServerList` does with it. Use the real `existing_admin` message, or state that the engine raises its own.

- **B3 [static/ctm/council.js:3549] NEW: server search no longer finds cases by reason or by the manager's full name.**
  - Why: today the council case search matches the reason (the ground labels shown in EN/AR), the applicant, the respondent and the manager (council.js:3549, 3554). The design searches `number`, `Party.name`, and the manager's `first_name`/`last_name` as separate fields (design.md:72). Typing a ground ("abandonment" or its Arabic label) now finds nothing, and so does "Fr. Demo Member", which spans both name fields. The `ground` filter exists, but no screen sends it (design.md:165-168). A user would expect search to keep finding what it finds today.
  - Fix: pick one and write it into §4/§8 and the tests:
    - (a) add a reason or ground `Select` to the cases command bar that sends `filters.ground`, and tell users the search box no longer covers reason; or
    - (b) map `q` to ground codes on the server from the EN/AR ground labels, if those labels exist server-side.
    - In either case, search the manager by `Concat(first_name, " ", last_name)`.

## Minor

- [design.md:45, design.md:74] `default_sort` is a static tuple, but sessions need `date` asc for `view: upcoming` and `-date` otherwise. Make it `Callable[[Account, dict], tuple]` or name the special case.
- [design.md:46, design.md:62] Step 5 returns 403 for keys that exist only for council roles, but `ListSpec.filters(actor)` returns only the allowed keys, so the engine cannot tell "council-only" from "unknown". Add `council_only: frozenset[str]` (filters and sorts) to `ListSpec`.
- [design.md:47, design.md:73 vs design.md:95] "None: q must be ''" reads as a 422. Rule 3 and the applications contract say 403 for an applicant. Use one rule.
- [api.py:47] `endpoint()` turns `ValueError`, `TypeError` and `KeyError` into a 404 `resource_or_input_invalid`. The validators must raise `ValidationError` themselves, and must reject `bool` (`True` passes `isinstance(x, int)`). Add `page: "1"`, `page: true` and `size: 1.5` to `test_list_common_errors` (design.md:242).
- [design.md:86] Facets run `DISTINCT action`/`DISTINCT source` over the whole audit table on every page-1 load. PostgreSQL has no skip scan for this. Measure it in T4 or cache it per process.
- [api.py:494] Sorting on `status` uses the stored value, while the council sees "Unassigned" (`display_status`). Open cases with and without a manager would interleave under one sorted label. Either sort on a `display_status` annotation or give the Status column no `serverSort`.
- [council.js:3605] The Reason column loses sorting, because it gets no `serverSort`. Accept it and say so in §8, or add a key.
- [design.md:61] The tatweel is removed from `q` only. A stored name that contains a tatweel is still missed. Note it, or normalize both sides with `Replace`.
- [design.md:65] `qs.count()` on the annotated cases queryset carries the subquery annotations. Count before adding the sort annotations.

## Cannot verify from diff (for QA)

- The `fetchRows` `sort`/`filters` shapes and the `strings` keys in Plenix 1.6.1 `data-grid.md` (risk 1). T5 already has a stop rule for this.
- Whether the Plenix header "Filter by this field" menu can be turned off per column in server mode (risk 2).
- The T4 timings.

## Declined to judge (for the lead)

- design.md:327: the applicant case rows carry `respondent_name` and `party_names` (api.py:493). Routing this to ctm3-product-lead is right. It is a projection question outside this slice, and I agree it blocks nothing here.

## Ledger notes (outside this slice)

- `draft_started` audit events are written with the case for an appeal or closed-case draft on an existing case (services/applications.py:131). `audit_visible` does not hide them, so case audit shows the council that an unsubmitted draft exists (SEC02 "including index"). This existed before #312. Refer it to ctm3-security-reviewer.

## Release condition

- Fix B1-B3 in `design.md` and `contract/`, then return the PR for re-review. On Pass, the reviewer lists T1-T8 on #312 for the build workers.
