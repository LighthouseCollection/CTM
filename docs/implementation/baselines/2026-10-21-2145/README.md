# CTM B01 — implementation and integration baseline

**Snapshot, not a release.** Captured 2026-10-21T21:48:38.841924-07:00 (Los Angeles). Main remains unchanged; no public deployment confirmed.

## Baseline reference

- Tested integration commit: `35e02f7ab8cece9ffdffa200472d95b46cbfc43f`.
- Immutable checkpoint tag: `baseline/integration-20261021-2145`.
- Main: `b38e70a15b85c0c28f98515ddcd73f5c48ebdf05`.
- Screen map: [45 screens with implemented/missing features](https://github.com/LighthouseCollection/CTM/blob/35e02f7ab8cece9ffdffa200472d95b46cbfc43f/docs/implementation/integration/README.md).
- Prototype reconciliation: issue #14 / documentation PR #13,33 pages/30 findings/48 field-review rows.
- Do not use the earlier approximate65% estimate as a measured completion baseline. Use capability stages below.

## Check-in and merge register

| Stream | Published head | Checks at capture | Integrated in B01? | Main merge |
|---|---|---|---|---|
| [#16](https://github.com/LighthouseCollection/CTM/pull/16) Integrate applicant council and backend with screen-by-screen coverage | `35e02f7ab8cece9ffdffa200472d95b46cbfc43f` | SUCCESS / SUCCESS | This integration checkpoint | Not merged; draft |
| [#13](https://github.com/LighthouseCollection/CTM/pull/13) Governance: council prototype page and schema coverage audit | `08da00b91b723a9a085417d39e07a4ed95792003` | SUCCESS / SUCCESS | Documentation separate | Not merged; draft |
| [#7](https://github.com/LighthouseCollection/CTM/pull/7) VM-FRM: filing privacy, reconsideration, council and payment contracts | `1ce1259ba4c5339af816e1c06ef6f684c79c5ec3` | SUCCESS / SUCCESS | Only through37d6ed7;2 newer commits excluded | Not merged; draft |
| [#6](https://github.com/LighthouseCollection/CTM/pull/6) Council workspace: review, sessions, reports, decision, decree, appeals and case pages | `65fa3893758ab298beee8aa921a544a8cd489ebc` | SUCCESS / SUCCESS | Yes through65fa389 | Not merged; draft |
| [#5](https://github.com/LighthouseCollection/CTM/pull/5) Applicant filing, appeals, contextual documents, payment history and invitations | `34314d8c59dd6e6a72f0126e174b4e288da4e6d0` | SUCCESS / SUCCESS | Only through2ae4541;1 newer commit excluded | Not merged; draft |

## What is actually checked

- Integration B01:490 PostgreSQL passed/2 skipped;180 frontend tests;66 isolated actual-Django/SQLite browser/API groups;18 council read screens;3 SQLite seed checks;1 additional shipped-JS-to-PostgreSQL report save/replay/conflict test.
- Integration hosted CI passed at35e02f7, including frontend tests, PostgreSQL, schema structural checks, non-root application image build, private-volume initialization and production-style HTTP/static serving in CI.
- Latest backend separately reports556 PostgreSQL passed/1 skipped at1ce1259, migrations through0035,56 forced-RLS tables/63 domain models,91 routes. Seven core policy reviews remain. This is not B01 coverage.
- Latest applicant separately reports92 frontend tests and74 actual-API/browser groups at34314d8 against backend37d6ed7. New history/modal/private-notification work is not yet in B01.
- Independent QA15 run1:89 pass/10 fail on old heads. Run2 rechecks newer heads; no final acceptance yet. Do not add suite counts together or imply all combinations passed.
- Browser/API runs use synthetic test sessions and controlled provider/scan behavior. Genuine Microsoft sign-in was previously verified locally; current synthetic browser checks are not fresh provider acceptance.
- Separate local Docker build failed with BuildKit EOF after the shared engine was restarted. Hosted CI image build passed; do not conflate them.

## What has been implemented

| Area | Implemented and checked scope | Still incomplete |
|---|---|---|
| Applicant | Draft editing/contextual files, review/submission/returned privacy, fee gating/history/recovery, appointments, request/consent responses, appeals/supplements, private messaging | Full approved bilingual content, full later-spouse UI journey, live providers, all profile/account settings |
| Applicant newer than B01 | Field-history modal/actor/timestamp and private notifications,74 API/browser groups reported | Integrate shell/modules and rerun combined checks |
| Council | Review, sessions/agenda/assignment/attendance, hearings/testimony, reports/templates/revision UI, assessments, voting/approval, signed-PDF issue/release, appeals, case views/search/statistics | Many screens partial; full factual profile/marriage/separation, full analytics/admin and certificate generation absent |
| Backend | Formal snapshots/privacy, case/open-claim constraints, fee/payment contracts, queue/delivery/retry/file safeguards, council/report/media contracts and version/history guards | Seven core policies, worker grants, full151 schema/identity equivalence and operational acceptance |
| Media | Recorder and evidence viewer UI; protected file routes; recording/transcript/review/retry backend contracts | Live OCR/transcription pipeline, long resumable upload, D20 council screens and device/scan acceptance |
| UI | Search label corrected; nav/Panel icons committed; Plenix-based modules and read evidence | General visual acceptance not granted; active header/navigation/split changes uncommitted at capture; Card icon and PDF CDN gaps |
| Governance |33-page audit,45-screen map, per-stage definitions, QA work order15, version-pinned integration | Close findings with exact evidence, not broad completion claims |

## Seven-stage baseline

| Capability group | Workflow | Schema | Database | Coded | Working | UI | Testing/QA |
|---|---|---|---|---|---|---|
| Core filing / case journey | Mostly defined | Partial semantic mapping | Adapter implemented/partial policies | Substantial | Scoped combined tests pass | Partial, not approved overall | Partial; independent/live acceptance open |
| Factual Marriage/Separation/Spouses/children | Mostly defined; correction-source detail open | Planned, field mapping open | Generic/assertion adapter partial | Missing/partial views | Not complete | Not complete | Missing page acceptance |
| Account/admin/settings | Fragmented, consolidation required | Portrait/identity/setting semantics open | Partial | Mostly missing UI | Not complete | Not complete | Pending |
| OCR/transcription/search ingestion | Defined at high level | Planned/contracts partial | Partial | Processing incomplete | Live processing not established | Recorder/viewers partial | Device/live processing pending |
| Decree | Defined; approved template text blocked | Planned/adapter partial | Lifecycle implemented | Upload/issue/release coded; generation absent | Scoped backend tests | Partial | Institutional/full journey pending |

## Remaining work, in order

1. Finish/validate/check in active UI changes; preserve ownership and do not stage unfinished or unrelated files.
2. Integrate the2 backend and1 applicant commits newer than B01 in a clean isolated candidate; update shell contracts and run combined tests. Do not imply published heads are already in localhost.
3. Complete independent QA15 on the exact next candidate. Reproduce/resolve surviving permission-error handling, unsaved-navigation, lost-ack and concurrency findings.
4. Finish seven core database-policy reviews and worker grants; reconcile all151-table semantics, identity/roles and JSON/provenance mappings. Name matching is not equivalence.
5. Reconcile/implement prototype gaps: Marriage, Separation, rich Spouses/children, factual Summary/timeline, queues/pagination, advanced search, member history, session metadata/summary, management/account settings and meaningful analytics (issue14).
6. Resolve CDN PDF assets/base/error behavior and standard Card.icon support upstream; do not add CTM workarounds contrary to owner instruction.
7. Obtain reviewed Arabic question wording, signed professional-release text and approved decree templates. No sample text is institutional approval.
8. Connect/test live payment/email/inbound/provider auth, scan/search ingestion, OCR/transcription, recordings/resumable uploads and backup/restore; keep external sensitive-document restrictions.
9. Actual visual/EN-AR/mobile acceptance per screen; then decide main merge and separately production deployment. Public URL currently returns502.

## Active local files outside the baseline

The local preview serves the working tree, including the UI stream's active edits. Those edits are NOT part of tag B01. Their owner was asked to checkpoint after validation. This audit does not commit them blindly.

| Status | Path | Snapshot SHA256 |
|---|---|---|
|  M | `static/ctm/app.js` | `2e25b70d6e086064cfeacb2c66b7c17e3df3557064938a72be90ed68fe4c6ee7` |
|  M | `static/ctm/council-case.js` | `02806465c0ca6bbe064a8714ff91866404e918e0608db6af51ff041763446dcb` |
|  M | `static/ctm/council-decree.js` | `1dae338944408da2bb759f485402f5955b9d3b88e6f0f88a5c76fb91eb2c7b87` |
|  M | `static/ctm/council-media.js` | `6ba748c53bb105622fcb2b64987e2f046dc082423e5a64d8e8145f9d8261a007` |
|  M | `static/ctm/council.js` | `59f5378cd224e19cb6d77fef37335cebb93ed1b87e03851d5d89f43328ae75b2` |
|  M | `tests/test_account_preferences.py` | `410074abfc001c6b3f29534505ff2213af9d0a9d48333ea816a97381dd2fd0fc` |
|  M | `tribunal/api.py` | `7ae1715a407a2e7dd6965bb0dec3c577bba04aa8fc2eaa303d157cccfe9fd705` |
|  M | `tribunal/templates/tribunal/shell.html` | `6db1179b15da26d37173e490252755489c13974960c16753c519107759770e82` |
| ?? | `docs/implementation/integration/split-view-regression.md` | `617e5662c5a32275d6aa766a2a01b443372e11d60b976111f80060794bfb24ac` |
| ?? | `scripts/browser_header_account.py` | `709cd5096ba8184060f05fbbae3bc947fa4b8deeacd458a37d3c99327cbae5c0` |
| ?? | `scripts/browser_navigation.py` | `09fa4861403c70f6ea7cd3110ae42af099294436d6aaafc6806d0191743828e2` |
| ?? | `scripts/browser_split_workspaces.py` | `a2ef597624a027a3adf4e104866ff589d072daab918f3281150f822f00bf83ec` |
| ?? | `static/ctm/shell-layout.js` | `879fb75ed815000b63926dbd015ca10c29bcfa5c96a9e58160d7b179092da3ce` |
| ?? | `static/ctm/tribunal-logo-cropped.svg` | `7609b08dfd082a62c7c988c5b77e2905320cfddf9ec88b524a0361eb159c4afd` |

## Coordination and next acceptance

- Backend/applicant streams are idle after published checkpoints at capture; council has its published checkpoint. UI stream and independent QA are active. No worker was interrupted.
- Issue4 remains the governance register;15 is independent QA;14 is prototype gaps. Issues1-3 and8-12 remain open, not automatically closed based on passing unit tests.
- Main merge is zero across all listed PRs. Integration merges exist only on the integration branch.
- Local preview HTTP200; public HTTPS502. No operational migration/deployment or credential change is part of this baseline.
- Machine-readable register: baseline.json; all source status is timestamped, so later updates should produce a successor baseline rather than silently overwrite B01.

## Post-capture UI checkpoint

After B01 capture, governance reviewed and checked in the UI stream at integration commit0527500 (PR16). The integration working tree is now clean. Fresh checks:180 frontend tests,10 PostgreSQL account tests,14 fixture split screens, navigation and header browser checks passed. Hosted checks for this successor are newly queued; B01's previous green hosted results do not apply automatically to it. This successor does not include the two newer backend commits or one applicant commit identified above. The immutable B01 tag and captured JSON remain historical evidence and are not rewritten.

Follow-up record: https://github.com/LighthouseCollection/CTM/blob/0527500/docs/implementation/integration/ui-checkpoint-B01-followup.md
