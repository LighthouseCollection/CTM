# Twenty applicant history and notification batches

Own saved answer history now shows retained values, actual actor and server time in the documented Plenix dialog. Changed-field indicators in the overview open the modal for the selected field; controls inside it can broaden the selected revision. Comparison preserves missing/null/false/zero distinctions, stable repeat IDs and ordering, and unknown escaped field paths. Current form labels are explicitly identified as current; the endpoint supplies no historical question wording. The initial export was removed after review against CTM-confirmed-decisions.md:43, which excludes user-facing exports.

Private notifications use bounded own pages, generic case metadata, explicit own read acknowledgement and authoritative refresh after uncertain responses. Raw payload internals are never rendered. Duplicate or malformed pages and denied refresh clear private data. Pending acknowledgement blocks navigation/unload; a false response never invents read status or count changes.

Verified: 92 frontend tests, 74 isolated real Django API/browser groups, eight history/notification browser fixture groups and nine shell groups. Arabic390px checks found no runtime inline styles or horizontal overflow. The modal closes with Escape and restores opener focus. History inspection/refresh preserves dirty editor answers. Outsider/council requests cannot read the applicant draft history or private notification IDs.

[Download JSON](history-notification-result.json) | [Actual API evidence](history-notification-api-result.json)

| Batch | Work |
| --- | --- |
| 1 | Strict own-history contract |
| 2 | Version and actor provenance |
| 3 | Server timestamps |
| 4 | Absent versus null/false/zero |
| 5 | Stable repeat row identity |
| 6 | Repeat order changes |
| 7 | Unknown field paths |
| 8 | Current-label provenance |
| 9 | Changed-field modal and focus handling |
| 10 | History privacy and dirty-draft preservation |
| 11 | Strict private notification projection |
| 12 | Bounded pagination |
| 13 | Generic metadata without raw payload |
| 14 | Normal authorized case routing |
| 15 | Explicit own read action |
| 16 | Literal acknowledgement validation |
| 17 | Lost acknowledgement recovery |
| 18 | Navigation and unload guards |
| 19 | Arabic mobile and malformed refresh |
| 20 | Integration evidence and shell proposal |

Backend snapshot: `37d6ed7afb000b8959843e42607d56e156f6a851`. The shared shell proposal is updated only in shell-integration.patch; shared application/template sources and protected build specification remain untouched. New modules are applicant-history.js and applicant-notifications.js, with unit tests, pinned Plenix fixtures and actual API acceptance helpers.

These are local integration checks using SQLite, synthetic accounts/content and scanner test policy. PostgreSQL, live providers/payment/email/antivirus, approved bilingual questionnaire content and institutional signing/issuance acceptance remain open. The full normalized schema and migrations remain backend-owned; these batches add no database schema. Governance still needs to integrate the shell patch serially with the council stream.

Independent review confirmed export removal and the corrected indicator-to-modal interaction, with no further concrete findings.
