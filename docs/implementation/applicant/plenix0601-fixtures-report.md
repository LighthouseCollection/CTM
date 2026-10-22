# Applicant fixture alignment with Plenix 0.60.1

Updated the twelve standalone applicant browser fixture scripts from CDN0.58.0 to owner-authorized0.60.1, matching governance integrationbd6e5c8. This changes fixture dependencies and result scope labels only. Existing historical evidence is unchanged. [Run results and script hashes](plenix0601-fixtures-result.json).

All twelve suites have successful runs: editor19, linked-entry6, appointments5, assessments5, decrees4, lifecycle/recovery11, payments4, requests4, supplements9, history/notifications8, messages8 and repeat-sections9 groups. No page errors were reported by successful runs. These overlapping synthetic fixture scopes are not a full application acceptance count. Repeat coverage includes the latest applicant row-local conditions, local hidden-value preservation and Arabic/mobile assertions on the new CDN.

The initial supplement run timed out after receipt recovery because Review supplement remained disabled. A fresh unchanged rerun passed9 groups. Cause is unverified and the first failure remains explicitly recorded; no assertion or product behavior was changed to obtain a pass.

No production/shared UI code, CSS or protected spec changed. Governance owns the separate stale Python shell-CDN assertion causing hosted integration CI failure; these fixture passes do not override that red check. Latest applicant/backend integration, coordinated Docker VM recovery, reviewed full bilingual institutional content, normalized schema reconciliation and live-service acceptance remain open. No merge, deployment or infrastructure restart occurred.
