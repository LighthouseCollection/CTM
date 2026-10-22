# Applicant compatibility with backend db82099

The explicit review candidate using backend db820990dd2fc15e80560bd630d90ec9b22276e5 and current applicant editor/linked-entry modules passes 76 actual-Django SQLite API/browser groups, with no page errors. [Exact result and module hashes](backend-db82099-api-result.json).

This candidate retains the older integrated104e4fd shared frontend/report-version fixes and applies the named minimal linked-entry hook in an ignored archive. It is not the published governance8572195 successor, and it does not include newer council/UI work. The separate unmodified8572195 result remains authoritative for that baseline. Earlier ff85717 evidence was preserved in its original file.

Backend changes since ff85717 add bounded actual SQL-session tests, denial-contract evidence and pagination for cases/case-audit/system-audit. Source inspection found no direct applicant-module consumer of those three list endpoints; shared navigation/control continuation belongs to UI/governance. Applicant per-case messages use their separate existing continuation contract. No shared files were edited.

SQLite compatibility does not verify forced-RLS denial semantics. Backend reports hidden/nonexistent private-history404 and explicit visible-rule403 under its restricted SQL tests. The earlier applicant strict403 PostgreSQL run remains failed; new exact-role browser acceptance must be separately recorded after coordinated infrastructure recovery. No new container was started and no shared engine was restarted.

Completed: latest-backend applicant compatibility check and immutable evidence separation. Awaiting governance: latest applicant/backend integration preserving council/UI fixes and exact successor QA. Blocked: coordinated Docker VM recovery, institution-approved full EN/AR publication/exact Arabic civil wording, normalized schema acceptance and live-service credentials/acceptance. Nothing merged or deployed.
