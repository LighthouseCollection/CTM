# Applicant PostgreSQL full acceptance

## Result

The exact governance successor `f315dc7cddfbfe63b0ec419a431446556fb41c63`
passed the complete applicant PostgreSQL browser/API acceptance run on 2026-10-22.
It contains applicant commit `197c8e6c965808de96bad9ea1af9a59ab6d2b51e`
and the backend fixes already integrated through governance PR #23.

- Full applicant acceptance: **75/75 checks passed**, exit code `0`.
- Separate focused regression run: **7/7 checks passed**.
- Browser page errors: **none**.
- Acceptance run: `applicant-20261022T114843Z-5b5cb7d5`.
- Fresh isolated clone: `ctm_accept_applicant_20261022t114843z_5b5cb7d5`.
- Protected artifacts: `/srv/ctm/acceptance/applicant-20261022T114843Z-5b5cb7d5`.
- Source hash before and after the run:
  `839b622283d46c8bc8912d75574c757a63b82e52e1c2244de3fb3f619e023f32`.

The runtime used a physical `ctm_app` database login. Both `current_user` and
`session_user` were `ctm_app`; the role was `NOSUPERUSER`, `NOBYPASSRLS` and
`NOINHERIT`, with no owner-role memberships. All 63 inspected domain tables had
forced row-level security. The clone contained the verified migration range
0042 through 0048.

## Covered regressions

The successful run includes the previously failing or incomplete applicant gates:

- linked-spouse first submission;
- joint withdrawal and decree-closure behavior;
- request-author display projection;
- private message pagination and sender display;
- known foreign message recipient denial as `403`, while an absent recipient is
  rejected as `422`, without creating messages, notifications or receipts;
- explicit recovery after a lost draft-deletion acknowledgement; and
- the wider applicant API/browser journey, with no browser page errors.

## Scope and remaining dependencies

This result establishes applicant acceptance against a fresh, isolated synthetic
PostgreSQL clone under the restricted physical application role. It does not claim
institutional content approval, live external-service acceptance, independent QA,
merge or deployment.

The applicant implementation and integrated PostgreSQL journey are complete within
that tested scope. Completion of the overall applicant stream still depends on:

- approved bilingual institutional application wording, field mapping and validation;
- genuine Google and Apple applicant authentication acceptance;
- live payment, email, antivirus and other external-service acceptance;
- independent QA against exact integration commit
  `f315dc7cddfbfe63b0ec419a431446556fb41c63`; and
- governance merge and deployment decisions.

The public/shared environment remained at `dccbd63`; this acceptance run did not
merge or deploy anything.

[Download the machine-readable result](postgres-full-acceptance-result.json).
