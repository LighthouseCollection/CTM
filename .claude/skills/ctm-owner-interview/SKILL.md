---
name: ctm-owner-interview
description: Settle an open CTM owner choice (screen layout, action, wording, state, workflow intent) without stopping the work - post a decision card on the GitHub issue, apply the recommended option at once, and record it in decisions.yaml and decisions/screens.md. Use when a spec or screen spec lists an owner question, or when new owner feedback would change a locked decision.
---

# Owner decision cards

Adapted from JacobLinCool/ux-discovery-interviewer-skill (MIT): Known /
Inferred / Unknown labels and the "what changed / what stays the same" update,
in the PDS 1.0 form: **agents never wait for the owner**.

## Before a card

- Read `decisions.yaml`, the rows for this screen in
  `docs/implementation/decisions/screens.md`, `DESIGN.md` and the spec.
- No card when the answer is already recorded, is in the codebase or the build
  spec, or the change is cheap to reverse: apply the default and say so in the
  issue comment.
- Cards cover only choices Plenix can offer (template, primary and destructive
  actions, visible columns/fields, icon from the Plenix set, EN/AR wording,
  empty/error text, step order). **Never colors, spacing, fonts or styling.**
- Up to 3 cards per issue at once.

## The card (a comment on the issue, signed by the role)

```
D-0123 · <area>: <one-line question>
Context: one sentence of what we understood.
Known: ... · Inferred: ... · Unknown: ...
A (Recommended) — <choice> — risk: ...
B — <choice> — risk: ...
Applied: A. To switch, reply B. If switched, we redo: <cost>.
```

Options in words. Screenshots of real Plenix components only when the owner
asked to see options; Arabic pictures only on request.

## Record (same commit as the change)

1. `decisions.yaml` entry: id, date, area, decision, why, options, decided_by
   (`agent:<role>` for an applied default, `owner` once the owner answers),
   status, and the `check` that enforces it (or `review_only` with a reason).
2. Screen decisions also get a row in `decisions/screens.md`:
   `| YYYY-MM-DD | screen | element | decision | D-0123 | Locked |`.
3. Label the issue `decision`.

## When the owner replies

- Owner picks another option: new decision entry, old one `superseded`
  (linked), redo the listed work. Never edit or delete old rows.
- Later feedback on a locked decision: classify it (clarification, new need,
  pain point, workflow change, edge case), answer with **What changed / What
  stays the same**, and apply it as a new card. An unrecorded reversal is an
  automatic G5b failure.
