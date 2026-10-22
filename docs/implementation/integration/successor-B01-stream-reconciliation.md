# Successor to B01: stream reconciliation

The immutable B01 tag remains unchanged. This successor assembles backend `1ce1259ba4c5339af816e1c06ef6f684c79c5ec3`, applicant `34314d8c59dd6e6a72f0126e174b4e288da4e6d0`, council `65fa3893758ab298beee8aa921a544a8cd489ebc`, and integration-only fixes through `0527500`.

Both newer stream merges were clean. The shared shell additionally loads applicant history/notification modules and routes applicant notifications to the private inbox. The report revision expected_version fix and navigation/header/split-view work are retained.

189 frontend tests pass. PostgreSQL results are recorded in the governance tracker after the full run. On Windows, pytest parameter names above 32767 characters prevent environment setup; a temporary plugin hashes only oversized test identifiers without changing test bodies or assertions.

Independent QA evidence is draft PR18, pinned to standalone backend bb3e48b and council 65fa389. It does not establish acceptance of this successor. Missing report expected_version is fixed here; unsaved sidebar navigation remains a reported defect requiring resolution and exact-candidate retesting. No release acceptance, main merge or production deployment is claimed.

The original screen-map and baseline evidence remain timestamped historical snapshots. Do not reinterpret their test counts as successor coverage. Integration-only changes must flow back into stream work before further feature development; do not replace updated files with older stream copies.
