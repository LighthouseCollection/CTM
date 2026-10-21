# CTM council Home dashboard — prototype review and content plan

Date: 2026-10-21. User approved My Cases, Needs Attention, Upcoming Council Session, Outstanding Requests and requested review of the current dashboard. Source inspection: ctm-admin/admin-index.html. No rendered-browser review or production UI changes were performed. All eventual presentation must follow Plenix CDN 0.58.0; component availability must be verified before implementation.

## Existing dashboard evidence

| Current source | Observed content | Proposed disposition |
|---|---|---|
| admin-index.html:483–509 | Upcoming meeting date/time, president, location, cases to assign, hearings, View Session, Add to Calendar; prior-session summary | Keep session information and previous-summary link. Rename consistently to Council Session. Calendar action is currently #; its implementation is not established by the prototype. |
| admin-index.html:512–556 | New Cases, year-filtered Total Cases and Avg. Case Duration | Retain compact operational counts where useful; place historical/year comparisons in Statistics and Reports. New Cases label currently says this month but links to unassigned cases: fix filter/count semantic mismatch. |
| admin-index.html:561–573 | Council members with avatars/roles and active-case counts | Useful tribunal overview; recommend compact/secondary placement rather than above all assigned work. Avatar/count must not imply broader editing authority. |
| admin-index.html:581–797 | Council workload, Cases by Reason, Granted vs Submitted, gender/background, Education vs Divorce Rate, duration before divorce charts | Recommend Statistics and Reports rather than main Home. No deletion of this conceptual content is approved by review alone. |
| admin-index.html:802–858 | Latest submissions table with case number, parties, reason, submitted date/status | Useful operational list, especially admin/secretary completeness review. Keep submitted-only, map row links to actual case, and use confirmed case identifiers/statuses/grounds. |
| admin-index.html:871 onward | Hardcoded year totals and chart datasets | Demo samples only; not live metrics or evidence of backend implementation. |

The prototype imports Chart.js directly and contains custom colors/styles and legacy classes. Its visual code is not an approved implementation starting point under the strict CDN rule. Reuse requirements/content, not custom dashboard CSS or chart configuration.

## Approved Home content

1. **My Cases** — currently assigned cases, status and latest relevant activity; open the selected case workspace. All authorized council members can still browse all submitted cases via Cases. Home prioritization does not restrict their existing read entitlement.
2. **Needs Attention** — unread messages, new applicant submissions/responses, new reports and permitted new/corrected documents. Use source statuses and recipient read state; do not show a waived fee as unpaid, OCR queued as rejected, or a staff correction as an applicant-change notification.
3. **Upcoming Council Session** — nearest scheduled active session date/time/location, agenda link and the user's scheduled cases. Show assignment/hearing counts with their stated scope. No scheduled session means an honest empty state, not a fabricated date. Keep a compact link to the previous session summary where available.
4. **Outstanding Requests** — applicant intakes, external-priest reports and medical/psychological requests, including follow-up relationships and real statuses. No arbitrary completion deadline or overdue label because request workflows have no deadline. Priest-link expiry is distinct from report completion deadline. Cancelled, closed and completed requests do not count as outstanding.

## Recommended arrangement — not a copied prototype layout

Upcoming Council Session context first; Needs Attention and My Cases as the main working area; Outstanding Requests close to that area. Admin/secretary can use a tribunal-wide operational scope including submitted applications awaiting review and unassigned accepted cases. Avoid a separate dashboard implementation per role where the same content queries/components can be scoped. System-wide authority does not route all routine notifications to admin/secretary.

The previous-session link, compact case counts, council workload summary and latest submissions are retained as useful candidate content from the prototype. Large analytics/charts are recommended for Statistics and Reports; this recommendation is not a newly approved deletion or replacement of the earlier dashboard. Exact layout, chart component, information density and responsive behavior follow documented Plenix capabilities, not invented grid sizes.

## Metric semantics and privacy

- Distinguish a case from multiple applications/appeals; linked spouse applications must not inflate case counts.
- Count My Cases by current assignment. Closed cases do not count as active. Preserve historical workload events independently of current assignment.
- Case identifiers use the agreed YYYYMMDD-## scheme or retained historical numbers; do not import sample 2026-00061 as a new numbering format.
- Grounds are multi-select and use the configured six-ground list. Multiple grounds can exceed the number of cases; label aggregates rather than pretending they are exclusive shares.
- New Cases, unassigned cases and applications awaiting initial review are different populations. The count and its destination filter must match.
- Define elapsed duration and whether appeal periods are included before publishing averages; historical missing dates must not become fabricated durations.
- “Education vs. Divorce Rate” cannot be inferred as population divorce prevalence from tribunal filings alone. If retained, describe the dataset as a breakdown/association within recorded tribunal cases and disclose its denominator; no causal claim.
- Home links, text snippets, report/medical summaries, counts and search all respect existing authorization/release/review scope. Do not leak restricted content through an attention card.
- Read/unread/new state is per user and distinct from report acceptance, resolved request workflow or case stage. No extra Request completed action is introduced.

## Integration requirements

Use authenticated Django queries/endpoints over authoritative records. Permanent business records are not generated from card state, browser localStorage or chart datasets. Pagination/filtering and bounded lists prevent downloading every case just to render Home. Dashboard counters can be derived/cached with authorization-safe invalidation; no performance target or production test is claimed.

The single sidebar avatar/name account trigger, universal login routing and case navigation remain as locked in CTM-council-navigation-and-layout.md. Dashboard approval does not authorize departing from Plenix to recreate the prototype's hero/cards/charts.
