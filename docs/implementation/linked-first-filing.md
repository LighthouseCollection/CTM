Current validation: **773 PostgreSQL passed, 1 skipped**; no model drift; migration rollback/reapply through0045. Nine new linked-filing regressions.

# Linked party first petition RLS correction

Backend issue #2; successor to 0044 is migration 0045_linked_first_filing.
The exact integration 66cfacb873e4560a5a07c2215562ab153171252b rejected
applications.py:445 party.save() under physical ctm_app with tribunal_party RLS.
A rollback-only diagnostic against the retained private acceptance clone confirmed
this exception. An independent isolated PostgreSQL regression reproduced it before
the fix using actual administrator link_party and first-time linked submission.

start_application stores an authorized case link before it has a formal party or
proceeding binding. Without optional spouse DOB, the previous filing-case helper
could recognize neither the original marriage match nor a returned formal filing.

0045 adds a first-petition path requiring the existing own account/person/party,
its open-case claim, an open case and open proceeding, and consistent optional
formal bindings. Existing filing eligibility still requires an active verified
owner, eligible fee and no duplicate hold. Core writes still require the actor's
own account/person. Unlinked marriage matching and returned formal binding are
unchanged. No public helper execution, new grants, models or routes are added.
Reverse restores 0041's helper exactly; 0042–0044 do not change that helper.

Governance owns serial integration and any test-server migration. Apply through
0045 after 0044; coordinate the unapplied UI metadata migration to a unique
successor (proposed 0046). Do not renumber previously applied backend migrations.
Applicant must rerun the failed linked journey on the exact integrated successor;
QA must independently record that SHA. Local tests do not establish that acceptance.
No shared database, deployment or merge was performed by backend.

Validation: nine new restricted-role regressions cover the complete linked journey,
positive binding and seven denied incomplete/foreign/ineligible binding cases.
The journey reproduced the pre-fix failure independently of the retained clone.
