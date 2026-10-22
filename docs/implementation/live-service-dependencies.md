# Live-service acceptance dependencies (separate from schema/policy work)

No operational secrets were inspected, created or changed. Isolated tests use
synthetic credentials/events and in-memory mail. Their success is not live-service
acceptance. Availability in the operational deployment has not been verified here.

| Acceptance not established | Exact dependency / owner |
| --- | --- |
| Live Microsoft council login | Operator supplies specific tenant application binding, callback registration and secret; institution preauthorizes immutable council object subject. Preserve prior locally verified login; rerun genuine login on the accepted integration commit. |
| Google/Apple applicant login | Operator supplies approved provider application IDs/secrets/signing configuration and callbacks plus authorized test accounts. Synthetic SocialLogin does not establish live provider behavior. |
| Payment and webhook acceptance | Operator supplies Stripe account/API and webhook secret bindings, configured price/currency and callback; institution approves amount/waiver policy. Independently exercise a genuine provider checkout and signed webhook replay. No fabricated paid state. |
| Email acceptance | Operator supplies SMTP host/port/transport/auth and approved sender/domain; authorized test mailboxes confirm actual receipt and privacy. Test backend acknowledgement is not delivery evidence. |
| Search and malware service | Operator supplies approved Meilisearch endpoint/key and ClamAV connectivity; run genuine service health/index/scan acceptance. Network endpoint availability differs from credential absence. |
| Transcription/OCR | Explicit deferred scope/provider and institutional processing approval. No completed transcript or extraction is claimed from a placeholder. |
| Browser/integration acceptance | Governance integrates the selected backend SHA serially; council first fixes unsaved sidebar text; QA reruns preserved failed scenarios against the exact successor integration SHA. |

Policy/grant migrations are reviewable code, not evidence that runtime roles were
provisioned safely in production. Governance/operator must inspect actual role
attributes, owner memberships, grants and readiness gates before any authorized
operational migration or deployment. This stream must not perform those actions.
