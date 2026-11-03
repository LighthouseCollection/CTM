---
name: ctm-payments
description: Payment checklist for CTM's Stripe filing and appeal fees - use when designing, building or reviewing anything that touches tribunal/services/payments.py, the Stripe webhook, fees, waivers, refunds, chargebacks or payment reconciliation.
---

# CTM payments checklist

Adapted from msitarzewski/agency-agents `engineering-payments-billing-engineer`
(MIT) for CTM's fee rules. CTM's integration already follows most of these;
keep it that way and close the listed gaps.

## Fixed CTM rules (from the contract)

- 250 USD per independently filing party and per appeal filer; linking as the
  other party is free; authorized waivers are explicit; payment or waiver
  before submission; nonrefundable after submission except accidental
  duplicates refunded by authorized staff; a chargeback never removes a
  submission (PAY01, PAY02).
- No real charges in development or tests. Missing credentials are a blocker,
  never a fake success.

## Rules

1. **No card data in CTM.** Stripe-hosted Checkout only (smallest PCI scope).
2. **Every money mutation is idempotent**, keyed by the business operation
   (`ctm-checkout:<intent>`), never a random key per HTTP call.
3. **The verified webhook is the truth**, never the browser return page.
   Verify the signature; reject unsigned/invalid payloads (400); if storage
   fails return 5xx so Stripe retries.
4. **Duplicate and out-of-order events are normal.** Deduplicate by provider
   event id. Before acting on a state change, re-check the current Checkout
   Session / PaymentIntent state with Stripe (or prove ordering cannot matter).
5. **Money as integers in minor units with a currency.** The fee amount comes
   from one setting/record, not literals repeated in code.
6. **Model every state**: open, processing, paid, expired, failed, refunded,
   disputed (warning, lost, won), needs reconciliation. Unhappy states are
   normal states with UI and audit.
7. **Reconcile.** A daily job compares Stripe payouts and balance transactions
   with CTM payment events; any drift is an alert for finance, not a log line.
   Track dispute response deadlines.
8. **Test the failure catalog** in Stripe test mode: declined card, insufficient
   funds, 3-D Secure challenge, abandoned checkout, expired session, duplicate
   webhook, out-of-order webhook, crash after payment before submission,
   refund, chargeback. A flow tested only with the success card is untested.

## Known gaps on main (2026-11-03)

- `25000` appears on 7 lines of `payments.py` and 2 more elsewhere in
  `tribunal/` -> one fee source.
- Webhook handlers act on the delivered event without re-checking current
  Stripe state (rule 4).
- No payout-to-ledger reconciliation job or dispute-deadline monitor (rule 7).
- Failure-catalog tests need Stripe test credentials (known blocker).

## Review output (security reviewer, payments mode)

`[file:line] PAY-rule-n problem - risk in money or filings - fix - test`
