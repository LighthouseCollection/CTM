# CTM build specification

Consolidated 2026-10-21. This directory is the current implementation contract. It supersedes conflicting passages in the older architecture discussion documents; those remain source history. Direct user corrections take precedence over this specification.

Start with [the consolidated specification](CTM-build-specification.md), [permissions](permissions.md), [transaction and acceptance requirements](transactions-and-acceptance.md), and [remaining delivery dependencies](delivery-dependencies.md).

[Interface contract](interface-contract.md) locks navigation and layout boundaries. Accepted question wording is copied exactly into `accepted-question-seed.json`; `prototype-decision-types.json` records prototype options and their confirmed workflow treatment. These are seed inputs, not applied database inserts.

Database artifacts:

- `schema.json`: physical table/column/foreign-key catalog, generated from `generate_schema.py`.
- `schema.sql`: PostgreSQL structural baseline, **not a complete secured production migration**. No application database is created by generating it. Django migrations must implement and test its structure, lifecycle guards, grants and row-level policies together before production access.
- `data-dictionary.md`: generated field-level reference.
- `relationships.mmd`: domain-level relationship diagram.
- `source-register.json`: hashes and titles of source architecture documents and accepted question assets.
- `validation.json`: reproducible checks, actual results and limitations.

Regenerate using `python docs/architecture/build-spec/generate_schema.py`. Validate using `python docs/architecture/build-spec/validate_spec.py`. No real case data belongs in these artifacts or development memory.

This is a database design package, not a claim that the working demo, identity integrations, file processing or VM deployment already exists.
