# CTM messaging standard

Owner: `ctm3-technical-writer`. Applies to every error, warning, confirmation,
success, empty state, loading and help message in CTM, in English and Arabic.
Terms come from `docs/implementation/glossary.md`; Arabic follows
`docs/i18n/arabic.md`. Sources: jakubkrehel *better-writing*, ui-craft
*clarify*, plugin87 *ux-writing*, the Plenix content rules (sentence case,
approved action verbs).

| Type | Pattern | Example |
|---|---|---|
| Error | What happened + why (if known) + how to fix it. Never blame the user; no codes alone | "Couldn't save the case. The connection dropped. Try again." |
| Field validation | What is needed, beside the field, as soon as it is relevant | "Enter a date after the filing date." |
| Destructive confirm | Name the object and the consequence; the button repeats the verb | "Withdraw this application? The council stops reviewing it." -> **Withdraw application** |
| Success | Short, past tense, undo when possible; only after the server confirmed | "Hearing scheduled. Undo" |
| Empty state | What goes here + one action to fill it | "No hearings yet. Schedule a hearing" |
| Loading | Only past ~1 second; say what is loading | "Loading hearings…" |
| Help / tooltip | One sentence; never repeats the label | |
| Unavailable | Honest; say what still works | "Audio transcription isn't available yet. You can still listen to the recording." |
| Forbidden | Say it is not available to this account; no hint about the data | "You don't have access to this case." |

## Rules (checked by `scripts/check_i18n.cjs` and reviewers)

- Every component that can fail shows an error message with a fix.
- No raw error codes, stack text or server field names shown to users.
- A confirmation button uses the same verb as the question.
- Irreversible actions (send, issue, release, vote, submit, withdraw) always
  confirm.
- Every message key has both EN and AR entries; no sentences built from
  translated fragments; one key with placeholders.
- Sentence case. Buttons name action and object ("Issue decree", never "OK").
- The same action has the same label in every module.
- Institutional wording (questions, declarations, decree text) is quoted from
  its approved source, never rewritten.
