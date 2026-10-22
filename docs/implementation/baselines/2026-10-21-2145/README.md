# CTM B 01 — implementation and integration baseline

**Snapshot, not a release.** Captured 2026-10-21T 21: 48: 38.841924-07: 00 (Los Angeles). Main remains unchanged; no public deployment confirmed.

## Baseline reference

- Tested integration commit: `35e 02f 7ab 8cece 9ffdffa 200472d 95b 46cbfc 43f`.
- Immutable checkpoint tag: `baseline/integration-20261021-2145`.
- Main: `b 38e 70a 15b 85c 0c 28f 98515ddcd 73f 5c 48ebdf 05`.
- Screen map: [45 screens with implemented/missing features](https://github.com/LighthouseCollection/CTM/blob/35e 02f 7ab 8cece 9ffdffa 200472d 95b 46cbfc 43f/docs/implementation/integration/README.md).
- Prototype reconciliation: issue #14 / documentation PR #13, 33 pages/30 findings/48 field-review rows.
- Do not use the earlier approximate 65% estimate as a measured completion baseline. Use capability stages below.

## Check-in and merge register

| Stream | Published head | Checks at capture | Integrated in B 01? | Main merge |
|---|---|---|---|---|
| [#16](https://github.com/LighthouseCollection/CTM/pull/16) Integrate applicant council and backend with screen-by-screen coverage | `35e 02f 7ab 8cece 9ffdffa 200472d 95b 46cbfc 43f` | SUCCESS / SUCCESS | This integration checkpoint | Not merged; draft |
| [#13](https://github.com/LighthouseCollection/CTM/pull/13) Governance: council prototype page and schema coverage audit | `08da 00b 91b 723a 9a 085417d 39e 07a 4ed 95792003` | SUCCESS / SUCCESS | Documentation separate | Not merged; draft |
| [#7](https://github.com/LighthouseCollection/CTM/pull/7) VM-FRM: filing privacy, reconsideration, council and payment contracts | `1ce 1259ba 4c 5339af 816e 1c 06ef 6f 684c 79c 5ec 3` | SUCCESS / SUCCESS | Only through 37d 6ed 7; 2 newer commits excluded | Not merged; draft |
| [#6](https://github.com/LighthouseCollection/CTM/pull/6) Council workspace: review, sessions, reports, decision, decree, appeals and case pages | `65fa 3893758ab 298beee 8aa 921a 544a 8cd 489ebc` | SUCCESS / SUCCESS | Yes through 65fa 389 | Not merged; draft |
| [#5](https://github.com/LighthouseCollection/CTM/pull/5) Applicant filing, appeals, contextual documents, payment history and invitations | `34314d 8c 59dd 6e 6a 72f 0126e 174b 4e 288da 4e 6d 0` | SUCCESS / SUCCESS | Only through 2ae 4541; 1 newer commit excluded | Not merged; draft |

## What is actually checked

- Integration B 01: 490 PostgreSQL passed/2 skipped; 180 frontend tests; 66 isolated actual-Django/SQLite browser/API groups; 18 council read screens; 3 SQLite seed checks; 1 additional shipped-JS-to-PostgreSQL report save/replay/conflict test.
- Integration hosted CI passed at 35e 02f 7, including frontend tests, PostgreSQL, schema structural checks, non-root application image build, private-volume initialization and production-style HTTP/static serving in CI.
- Latest backend separately reports 556 PostgreSQL passed/1 skipped at 1ce 1259, migrations through 0035, 56 forced-RLS tables/63 domain models, 91 routes. Seven core policy reviews remain. This is not B 01 coverage.
- Latest applicant separately reports 92 frontend tests and 74 actual-API/browser groups at 34314d 8 against backend 37d 6ed 7. New history/modal/private-notification work is not yet in B 01.
- Independent QA 15 run 1: 89 pass/10 fail on old heads. Run 2 rechecks newer heads; no final acceptance yet. Do not add suite counts together or imply all combinations passed.
- Browser/API runs use synthetic test sessions and controlled provider/scan behavior. Genuine Microsoft sign-in was previously verified locally; current synthetic browser checks are not fresh provider acceptance.
- Separate local Docker build failed with BuildKit EOF after the shared engine was restarted. Hosted CI image build passed; do not conflate them.

## What has been implemented

| Area | Implemented and checked scope | Still incomplete |
|---|---|---|
| Applicant | Draft editing/contextual files, review/submission/returned privacy, fee gating/history/recovery, appointments, request/consent responses, appeals/supplements, private messaging | Full approved bilingual content, full later-spouse UI journey, live providers, all profile/account settings |
| Applicant newer than B 01 | Field-history modal/actor/timestamp and private notifications, 74 API/browser groups reported | Integrate shell/modules and rerun combined checks |
| Council | Review, sessions/agenda/assignment/attendance, hearings/testimony, reports/templates/revision UI, assessments, voting/approval, signed-PDF issue/release, appeals, case views/search/statistics | Many screens partial; full factual profile/marriage/separation, full analytics/admin and certificate generation absent |
| Backend | Formal snapshots/privacy, case/open-claim constraints, fee/payment contracts, queue/delivery/retry/file safeguards, council/report/media contracts and version/history guards | Seven core policies, worker grants, full 151 schema/identity equivalence and operational acceptance |
| Media | Recorder and evidence viewer UI; protected file routes; recording/transcript/review/retry backend contracts | Live OCR/transcription pipeline, long resumable upload, D 20 council screens and device/scan acceptance |
| UI | Search label corrected; nav/Panel icons committed; Plenix-based modules and read evidence | General visual acceptance not granted; active header/navigation/split changes uncommitted at capture; Card icon and PDF CDN gaps |
| Governance |33-page audit, 45-screen map, per-stage definitions, QA work order 15, version-pinned integration | Close findings with exact evidence, not broad completion claims |

## Seven-stage baseline

| Capability group | Workflow | Schema | Database | Coded | Working | UI | Testing/QA |
|---|---|---|---|---|---|---|---|
| Core filing / case journey | Mostly defined | Partial semantic mapping | Adapter implemented/partial policies | Substantial | Scoped combined tests pass | Partial, not approved overall | Partial; independent/live acceptance open |
| Factual Marriage/Separation/Spouses/children | Mostly defined; correction-source detail open | Planned, field mapping open | Generic/assertion adapter partial | Missing/partial views | Not complete | Not complete | Missing page acceptance |
| Account/admin/settings | Fragmented, consolidation required | Portrait/identity/setting semantics open | Partial | Mostly missing UI | Not complete | Not complete | Pending |
| OCR/transcription/search ingestion | Defined at high level | Planned/contracts partial | Partial | Processing incomplete | Live processing not established | Recorder/viewers partial | Device/live processing pending |
| Decree | Defined; approved template text blocked | Planned/adapter partial | Lifecycle implemented | Upload/issue/release coded; generation absent | Scoped backend tests | Partial | Institutional/full journey pending |

## Remaining work, in order

1. Finish/validate/check in active UI changes; preserve ownership and do not stage unfinished or unrelated files.
2. Integrate the 2 backend and 1 applicant commits newer than B 01 in a clean isolated candidate; update shell contracts and run combined tests. Do not imply published heads are already in localhost.
3. Complete independent QA 15 on the exact next candidate. Reproduce/resolve surviving permission-error handling, unsaved-navigation, lost-ack and concurrency findings.
4. Finish seven core database-policy reviews and worker grants; reconcile all 151-table semantics, identity/roles and JSON/provenance mappings. Name matching is not equivalence.
5. Reconcile/implement prototype gaps: Marriage, Separation, rich Spouses/children, factual Summary/timeline, queues/pagination, advanced search, member history, session metadata/summary, management/account settings and meaningful analytics (issue 14).
6. Resolve CDN PDF assets/base/error behavior and standard Card.icon support upstream; do not add CTM workarounds contrary to owner instruction.
7. Obtain reviewed Arabic question wording, signed professional-release text and approved decree templates. No sample text is institutional approval.
8. Connect/test live payment/email/inbound/provider auth, scan/search ingestion, OCR/transcription, recordings/resumable uploads and backup/restore; keep external sensitive-document restrictions.
9. Actual visual/EN-AR/mobile acceptance per screen; then decide main merge and separately production deployment. Public URL currently returns 502.

## Active local files outside the baseline

The local preview serves the working tree, including the UI stream's active edits. Those edits are NOT part of tag B 01. Their owner was asked to checkpoint after validation. This audit does not commit them blindly.

| Status | Path | Snapshot SHA 256 |
|---|---|---|
|  M | `static/ctm/app.js` | `2e 25b 70d 6e 086064cfeacb 2c 66b 7c 17e 3df 3557064938a 72be 90ed 68fe 4c 6ee 7` |
|  M | `static/ctm/council-case.js` | `02806465c 0ca 6bbe 064a 8714ff 91866404e 918e 0608db 6af 51ff 041763446dcb` |
|  M | `static/ctm/council-decree.js` | `1dae 338944408da 2bb 759f 485402f 5955b 9d 3b 88e 6f 0f 88a 5c 76fb 91eb 2c 7b 87` |
|  M | `static/ctm/council-media.js` | `6ba 748c 53bb 105622fcb 2b 64987e 2f 046dc 082423e 5a 64d 8e 8145f 9d 8261a 007` |
|  M | `static/ctm/council.js` | `59f 5378cd 224e 19cb 6d 77fef 37335cebb 93ed 1b 87e 03851d 5d 89f 43328ae 75b 2` |
|  M | `tests/test_account_preferences.py` | `410074abfc 001c 6b 3f 29534505ff 2213af 9d 0a 9d 48333ea 816a 97381dd 2fd 0fc` |
|  M | `tribunal/api.py` | `7ae 1715a 407a 2e 7dd 6965bb 0dec 3c 577bba 04aa 8fc 2eaa 303d 157cccfe 9fd 705` |
|  M | `tribunal/templates/tribunal/shell.html` | `6db 1179b 15da 26d 37173e 490252755489c 13974960c 16753c 519107759770e 82` |
| ?? | `docs/implementation/integration/split-view-regression.md` | `617e 5662c 5a 32275d 6aa 766a 2a 01b 443372e 11d 60b 976111f 80060794bfb 24ac` |
| ?? | `scripts/browser_header_account.py` | `709cd 5096ba 8184060f 05fbbae 3bc 947fa 4b 8deeacd 458a 37d 3c 99327cbae 5c 0` |
| ?? | `scripts/browser_navigation.py` | `09fa 4861403c 70f 6ea 7cd 3110ae 42af 099294436d 6aaafc 6806d 0191743828e 2` |
| ?? | `scripts/browser_split_workspaces.py` | `a 2ef 597624a 027a 3adf 4e 104866ff 589d 072daab 918f 3281150f 822f 00bf 83ec` |
| ?? | `static/ctm/shell-layout.js` | `879fb 75ed 815000b 63926dbd 015ca 10c 29bcfa 5c 96a 9e 58160d 7b 179092da 3ce` |
| ?? | `static/ctm/tribunal-logo-cropped.svg` | `7609b 08dfd 082a 62c 7c 988c 5b 77e 2905320cfddf 9ec 88b 524a 0361eb 159c 4afd` |

## Coordination and next acceptance

- Backend/applicant streams are idle after published checkpoints at capture; council has its published checkpoint. UI stream and independent QA are active. No worker was interrupted.
- Issue 4 remains the governance register; 15 is independent QA; 14 is prototype gaps. Issues 1-3 and 8-12 remain open, not automatically closed based on passing unit tests.
- Main merge is zero across all listed PRs. Integration merges exist only on the integration branch.
- Local preview HTTP 200; public HTTPS 502. No operational migration/deployment or credential change is part of this baseline.
- Machine-readable register: baseline.json; all source status is timestamped, so later updates should produce a successor baseline rather than silently overwrite B 01.

## Post-capture UI checkpoint

After B 01 capture, governance reviewed and checked in the UI stream at integration commit 0527500 (PR 16). The integration working tree is now clean. Fresh checks: 180 frontend tests, 10 PostgreSQL account tests, 14 fixture split screens, navigation and header browser checks passed. Hosted checks for successor 0527500 have now passed; B 01's previous green hosted results do not apply automatically to it. This successor does not include the two newer backend commits or one applicant commit identified above. The immutable B 01 tag and captured JSON remain historical evidence and are not rewritten.

Follow-up record: https://github.com/LighthouseCollection/CTM/blob/0527500/docs/implementation/integration/ui-checkpoint-B 01-followup.md


## Stream synchronization rule

Integration-only changes to stream-owned files must be reconciled back into that stream before further feature work. Use the integration fix as the source; do not overwrite it with an older stream file. In particular, report revisions require expected_version, already fixed in integration but absent from council head 65fa389. Retest the exact assembled candidate; standalone branch checks are not combined acceptance.
