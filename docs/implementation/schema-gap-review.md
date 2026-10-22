# Approved schema versus implemented adapter: gap review

The protected151-table schema remains authoritative. The63 Django models are a
functional adapter, not a declaration that88 tables are unnecessary. Conversely,
151 minus63 is not a count of missing migrations: several approved history and
association concepts share one current model or frozen JSON snapshot.

`schema-reconciliation.json` associates122 approved tables with candidate adapters
and leaves29 without candidates. Those associations are unaccepted hypotheses.
`schema-field-gap-inventory.json` expands all151 approved tables to every approved
column, its exact type/nullability/reference/default, same-named Django field
expressions where present, and approved constraints/indexes. A spelling match is
explicitly not semantic equivalence. Missing same-named columns may be aliases or
JSON adapters; inspect the actual service lifecycle before deciding a migration.

## Confirmed substantive gaps and required migration families

| Contract area | Implemented evidence | Actual gap / required migration |
| --- | --- | --- |
| Stable identity and versions | Person.canonical, current name/DOB/gender; AnswerRevision snapshots; Party.reference retained | No attributed Person identity-version history, identity state/optimistic row version, consolidation event or review-hold model. Add retained identity versions and consolidation/hold roots; backfill current facts with explicit unknown provenance, never invented original actors/dates. Canonical FK is an alias for canonical_person_id, not a missing relationship. |
| Account and provider lifecycle | Account role/status flags/locales, microsoft_subject; allauth SocialAccount/SocialToken/EmailAddress and Django sessions | Flags/locales adapt status/ui_locale/notification_locale but lack equivalent versioned account events, email history, staff membership/role history and institutional scope. Add explicit retained account/provider/email/membership history with unique provider subject and event provenance. Do not migrate usable passwords. Allauth tables alone do not establish approved lifecycle equivalence. |
| Marriage and related people | Case marriage date/sorted spouse birth dates, linked Party; application answer JSON | Typed marriage, separation, spouses/children and related fact histories are not normalized approved roots. Add fact roots and version/source links; backfill from frozen submissions with per-field provenance and explicit unknowns. Require approved application-field mapping from issue #1 to avoid inventing missing questions or Arabic content. |
| Case and party history | Case/Party/Proceeding, assignments, events, frozen references, claim/counter infrastructure | Current mutable projections do not replace every approved case/party identity event/version. Add attributed correction/version records and backfill actual recorded events only. Infrastructure natural keys/counters do not mirror universal UUID/created_at columns; review explicit contract exception or migrate keys with compatibility FKs. |
| Questions and filings | Published QuestionnaireVersion, AnswerRevision, immutable Submission declarations/manifests | JSON holds question structure and submitted content. It does not prove accepted field/repeat/question/citation mapping. Normalize approved question/choice/repeat/answer/version relations only after mapping acceptance; preserve original JSON, question text, language and declaration evidence. |
| Decisions, evidence and citations | Hearing, findings/decision revisions, votes, approval and decree; constrained citation lists | Several approved typed source associations/citation/history tables are represented by JSON arrays or combined adapter records. Add typed links with source-version FKs and same-case/proceeding constraints; retain current frozen content and map actual source IDs, never synthesize evidence. |
| Institution, reference and template structures | Settings/reference/template adapters and versioned questionnaire configuration | Candidate adapters do not supply complete diocesan/parish/tribunal membership scope or all approved reference/template versions. Add scoped roots and immutable version/usage links after institutional owners accept canonical records. Missing supplied content is an acceptance dependency, not a reason to seed sample content. |
| Sessions, notifications, files and worker infrastructure | Framework sessions, Notification/Outbox, file versions/events, private storage and cleanup | Approved session/version/recipient/delivery/processing associations may share adapter tables. Keep storage keys private and preserve existing journals; add missing typed association/history roots after field-level review. Outbox queued_by is added in0036; seven core policy coverage is added in0037; existing-role grants/retention in0038. These are the only new migrations in this delivery. |

## Migration sequence and acceptance

1. Governance accepts the field/relationship mapping against the protected contract;
   backend owns migration design. Applicant owns approved question/repeat mapping;
   institution owns canonical membership/content and correction authority.
2. Add missing roots and version/link tables without dropping current evidence.
   Write explicit dual-read adapters, bounded backfills and conflict reports.
3. Validate source/type/nullability/FK/uniqueness and lifecycle transitions under
   non-owner policies, including historical unknowns and retained original actors.
4. Independently compare backfilled records with frozen evidence before switching
   reads. Remove an adapter only after explicit acceptance and a separate migration.

The detailed inventory is evidence for review, not a complete semantic sign-off.
Full approved-schema implementation remains unfinished; this assignment's
reconciliation deliverable identifies the gaps and required migrations rather than
silently creating151 tables or changing the approved source to fit63 models.
