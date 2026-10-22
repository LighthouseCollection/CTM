# Later resolution notes

The source audit remains pinned to backend d724ba5 and applicant 72ee829; its JSON
and mapping findings are historical evidence and are not rewritten as current facts.

AS09's missing own supplement history/capability/recovery dependency is resolved in
local applicant integration against backend a0bd138. Own hash-only history, stable key,
version enforcement, receipt recovery and exact replay are now integrated and tested.
See [current supplement report](../supplement-integration-report.md).

AS09's separate appeal root/claim/provenance schema mapping and the other schema
reconciliation findings remain owner-managed work. This is not a full schema parity
or PostgreSQL/live-service acceptance claim.
