# Filing document-category label consumer

Owner-only GET /api/applications/<uuid>/files/ now applies the latest valid
configured document_categories label_en/label_ar pairs to its requirement labels.
The response shape is unchanged. Stored category codes, required flags, contextual
RO identifiers, file items/scan state/download authorization and signed answer/
manifest evidence remain unchanged. Required_documents and document_requirements
remain pure business rules; submission/recovery workers do not read label settings.
A configured label cannot remove MC/CMC/CDD/PHOTO, waive a contextual RO original,
change a file's meaning, or bypass scan/mime/size/ownership checks.

0044_document_category_labels adds one app-only, stable SECURITY DEFINER label
projection with a fixed pg_catalog/public path, explicit source table and no caller
parameters. It selects only the latest document_categories revision. Active actor
required; PUBLIC execute revoked, worker not granted/also rejected. Output is only
code, bilingual labels and configuration version, never the settings row, other
configuration keys, editor, credentials or provider fields. Account/settings row
policies are unchanged; applicant still cannot enumerate SettingRevision.

The SQL projection validates the complete value before returning anything: exact
root/categories array shape, exact entry fields, known seven codes, unique codes,
bilingual nonblank strings up to300 characters and bounded JSON bytes. No recursive
secret traversal is required because every accepted key/value shape is fixed. Python
revalidates the projected categories with the same typed wire validator. SQLite
validates the same latest stored shape before projection. The maximum shape has
seven distinct category records and no arbitrary nested objects.

No setting or empty categories means existing built-in labels. Missing configured
codes retain their built-in labels. Invalid/unsafe latest legacy content fails closed
to the existing labels, with no partial use and no activation of an older revision.
No revision is rewritten, no sample content is seeded, and no content approval is
inferred from schema validity. Institutional content owners remain responsible for
approved English/Arabic wording, including civil-certificate terminology. Valid
saves affect subsequent owner file listings immediately; there is no separate
activation operation. The settings descriptor truthfully exposes
runtime_consumers=[filing_document_labels] for document_categories while
activation_supported=false retains that operation meaning.

Thirteen restrictedctm_app tests cover bilingual overrides, latest revision and
explicit empty reset, unchanged requiredness/RO contexts, hidden settings rows,
malformed/unsafe/duplicate/oversized/unknown-code legacy values, no actor/worker
denial and consumer descriptor. Full PostgreSQL764 passed,1 skipped; rollback/
reapply through0044.99routes/63models/63forced tables unchanged.0010-to-current
roundtrip and the earlier C05 strict medical guard tests restore this latest leaf.

Governance integrates0042→0043→0044 serially after applied0041 with snapshot.
Existingctm_app receives execute at migration install; if created after migrations,
apply0044.grant_runtime after0038 base and0043 projection grant plans in owner
provisioning context. No role creation, credentials, row-policy widening or
operational migration by this stream. UI PR22's separate unapplied metadata0040
must use a unique coordinated successor (proposed0045after0044), preserving applied
0040/0041; this stream has not edited its branch or applied anything to the server.

UI/institution checks actual configured content on the exact combined successor;
QA independently verifies defaults/invalid fallback and unchanged filing rules.
Other settings consumers, profile/identity workflows, C05 capability/paper/email,
normalized schema and live-service/full acceptance remain unfinished. No merge/deploy.
