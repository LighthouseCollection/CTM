# Fees, checkout candidates and financial history

Source-only candidates at backend `d724ba56b8bd5cf501d55fbbca416470108f963a` and applicant `72ee829eb1eabc436c19a084f81235b6a029528c`.
No row proves physical schema parity, production readiness or a security failure.

| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |
| --- | --- | --- | --- |
| `fee_obligations` | `tribunal.FeeObligation` | `assessed_at` | None mapped |
| `fee_waivers` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `obligation_id`, `reason` | tribunal.FeeObligation.waived_by_id |
| `payment_attempts` | `tribunal.CheckoutIntent` | `obligation_id`, `candidate_id`, `provider`, `idempotency_key`, `amount_minor`, `currency` | None mapped |
| `payment_events` | `tribunal.PaymentEvent` | `attempt_id`, `verified_at`, `safe_payload` | None mapped |
| `payment_allocations` | `No standalone mapping` | `id`, `created_at`, `attempt_id`, `obligation_id`, `submission_id`, `amount_minor` | tribunal.PaymentEvent.application_id |
| `refund_events` | `No standalone mapping` | `id`, `created_at`, `actor_id`, `request_id`, `attempt_id`, `provider_refund_id`, `status`, `amount_minor`, `reason` | tribunal.PaymentEvent.kind |

[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)
