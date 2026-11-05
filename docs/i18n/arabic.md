# CTM Arabic standard

Owner: `ctm-i18n-engineer`. Same rules as the PDS Arabic workflow (#427), so
CTM and Plenix read as one product. Decision: `decisions.yaml` D-0012.

## Language

- Modern Standard Arabic. Microsoft terminology where a term exists.
- One English term = one Arabic term everywhere; the pair lives in
  `docs/implementation/glossary.md`. Add the term there before using it.
- `ar-EG` CLDR formats for dates and numbers, Arabic-Indic digits in Arabic UI.
- IDs, emails, URLs, case numbers (`YYYYMMDD-##`) and decree ids (`DCR-...`)
  stay Latin.
- Plurals use the six Arabic forms (zero, one, two, few, many, other) or avoid
  counts in prose.

## Who writes Arabic

| Text | Rule |
|---|---|
| UI words (labels, buttons, messages, help) | The i18n Engineer proposes them from the glossary and this standard, ships them, and appends each new word to `arabic-proposals.md` for the owner's batch review. Work never waits. An owner correction becomes a decision and updates the glossary |
| Institutional text (questions, declarations, decree wording, doctrinal text) | Never improvised. Only from the approved source or the configured translation workflow (`docs/architecture/CTM-translation-master-prompt.txt`); otherwise the item is blocked on its issue |

## Checks

`scripts/check_i18n.cjs` (CI, new problems only): missing AR key, AR equal to
EN, empty AR, placeholder mismatch between EN and AR.
