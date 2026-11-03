---
name: ctm-owner-interview
description: Interview the CTM owner once per screen to lock layout, action, wording and state decisions before building, and record each answer as a dated row in decisions/screens.md. Run in the main session (subagents cannot ask the user). Use when a screen spec lists owner questions, or when new owner feedback would change a locked decision.
---

# Owner screen interview

Adapted from JacobLinCool/ux-discovery-interviewer-skill (MIT): pacing,
Known/Inferred/Unknown labels and the "what changed / what stays the same"
update. Purpose: stop the flip-flops (icons and layouts toggled many times
because owner decisions were never recorded).

## Before asking

- Read the screen spec (`ctm-screen-shape` output) and the existing rows for
  this screen in `docs/implementation/decisions/screens.md`.
- Ask **only** what is not already decided, and only questions whose answer
  changes the build. At most 5 questions per round, one screen at a time, at
  most 2 rounds.
- Ask only about choices Plenix can actually offer: which documented pattern or
  template, primary and destructive actions, which columns/fields the actor
  must see, icon choice from the Plenix icon set, button and label wording in
  EN and AR, what empty/error states say, the order of steps in a flow.
  **Never ask about colors, spacing, fonts or styling.**
- Where possible show options as described variants or screenshots of real
  Plenix components (from the pinned docs or a browser script), not mockups
  with invented styles.

## During

1. Restate the screen's task in 1-2 sentences.
2. Ask the batch (use the AskUserQuestion tool; recommended option first).
3. After each answer, summarize: **Known** (owner said), **Inferred** (your
   reading - confirm it), **Unknown** (still open).

## Recording (required)

Append one row per decided element to `decisions/screens.md`:
`| YYYY-MM-DD | screen | element | decision | owner interview YYYY-MM-DD | Locked |`
Read the new rows back to the owner for confirmation. Unknown items stay as
open questions in the slice brief with a default assumption.

## Later feedback on a locked decision

Classify it: clarification, new need, pain point, workflow change or edge case.
Answer with **What changed / What stays the same**, show the locked row it
would replace, and ask for an explicit decision. If confirmed, mark the old row
`Superseded YYYY-MM-DD` and add the new row - never edit or delete the old one.
Without explicit confirmation nothing changes, and the UI finish gate treats an
unrecorded reversal as an automatic HOLD.
