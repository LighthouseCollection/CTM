# Backend issue #2: core policy and worker grant review

This continuation belongs to VM-FRM, branch `work/vm-frm-backend`, draft PR #7.
It does not authorize operational migration, role creation, credentials, merge or deployment.

## Completed implementation

Migrations0036–0038 add Outbox queue-actor provenance; enable and FORCE RLS on
Account, Person, Case, Party, Proceeding, OpenCaseClaim and Outbox; and define an
explicit grant plan for existing `ctm_app` and `ctm_worker` roles. All63 current
tribunal tables now have forced policies. This is coverage of the implemented
adapter, not acceptance of the151-table approved schema.

| Reviewed table | Read/write boundary |
| --- | --- |
| Account | Authenticated self; council roster/actual case links; administrative enrollment; signed-session bootstrap; validated provider lookup. Immutable authorization/provider identity through preference updates. Guarded status changes retain last administrator. |
| Person | Self and authorized case readers; filing corrections bound to current answer snapshot. Identity consolidation remains a separate missing workflow. |
| Case | Council and actual linked parties; eligible filing creation, explicit assignment authority, attributed approved closure/reconsideration. Source number/marriage identity retained. |
| Party | Applicant raw access restricted to self; safe case-detail projection redacts partner reference. Verified onboarding, bound historical workspace, filing and guarded lifecycle mutations. Immutable case/person/account/slot. |
| Proceeding | Actual case access, filing/historical/reconsideration creation and guarded closure. Immutable case/kind/sequence. |
| OpenCaseClaim | Own-person/council reads; actual open party required on insertion; removal only after authorized closure. |
| Outbox | Actor/source-bound creation, private queue access, worker journal outcomes, explicit administrative retry. No applicant delivery success fabrication. Destination helper exposes only the selected job's validated destination. |

Server session decoding precedes Django AuthenticationMiddleware so account RLS
can bootstrap authentication without accepting browser actor claims. Allauth
lookup is scoped on its validated SocialLogin instance; Microsoft tenant and
preauthorized subject checks remain. Post-login writes receive server actor context.
HTTP case-detail response fields are preserved. Shared auth/API coordination was
posted on issue #4 before editing.

The grant migration refuses privileged or owner-assuming runtime roles. It never
creates roles or changes passwords. Worker privileges exclude framework sessions,
provider fact insertion, unrelated council narrative and general deletion. Paid
filing recovery can obtain only its verified payment owner. Bounded definer
retention handles eligible private drafts with server clock checking, checkout
holds and transactional cleanup journals. It does not grant arbitrary deletion.
App and worker direct helper calls receive explicit EXECUTE; private helpers are
not PUBLIC. Rollback removes this domain grant plan; an operator must explicitly
reapply a reviewed prior plan rather than assume prior ACLs can be reconstructed.

## Verification and limits

**Final isolated PostgreSQL result: 566 passed, 1 skipped.** No model drift;
rollback/reapply through0038 and all63 forced policies verified. Protected schema
structural checks pass (151 tables,354 foreign keys,59 accepted questions preserved).

Validation uses only the isolated ctm-vmfrm PostgreSQL network, never operational
containers. Tests include actual named non-owner app/worker grants, anonymous
core-table denial, filing, immutable identity, session authentication, worker
impersonation/provider-fact/session denial, retention and synthetic email dispatch.
Existing row-security and migration rollback/reapply checks cover earlier domains.
Synthetic email acceptance proves only a test backend acknowledgement, not SMTP
or inbox delivery. Provider tests do not prove genuine live login.

Long pytest parameter IDs are shortened by a deterministic digest only when the
representation exceeds120 characters. Parameter values and assertions are retained.
No server/database change addresses the Windows environment-variable limit.

Acceptance dependencies and actual schema gaps are recorded separately in
[schema-gap-review.md](schema-gap-review.md) and
[live-service-dependencies.md](live-service-dependencies.md).
