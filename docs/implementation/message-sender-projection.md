Current validation: **842 PostgreSQL passed, 1 skipped**; no model drift; rollback/reapply through0048. Eight new physical-role message regressions plus one cross-adapter endpoint contract; SQLite contract separately passed. Exact-successor applicant/QA acceptance remains pending.

# Private messages must not require sender Account visibility

Backend issue #2. Migration0048_message_sender_projection follows0047.
Exact integrationb6f4bf42b4ce76b4e902943dd6660b8755e2fae4, retained private
acceptance clone and physical current_user=session_userctm_app read diagnosis:
51 intended recipient rows and51 messages_for rows were visible, but endpoint
select_related('sender') returned0 rows because the sender administrator Account
was correctly hidden. Closed-case access and recipient/send state were valid.
The rollback-only diagnosis changed no clone data or shared database.

A faithful isolated regression created51 messages using actual admin send_message,
closed-case own recipient and actual runtime grants. The endpoint returned200 with
emptyitems before the fix, matching both browser and direct integration evidence.

The endpoint now pages its already-authorized message queryset without joining
Account. It retrieves actual display names for only the50 serialized message IDs
using a bounded read-only projection. The existing created_at/id ordering,50+1
lookahead/next_offset, recipient filtering, receipts, body, file links and own-only
idempotency key remain unchanged. No sender substitution or invented attribution.

0048 adds ctm_message_sender_names(uuid[]): message UUID + actual current sender
name only. Each ID must pass existing ctm_message_visible; inactive senders retain
their recorded account name. No account UUID/email/role/status is returned. No
actor, worker or input over250 IDs yields no data (worker execution is also denied).
PUBLIC execution is revoked and existingctm_app alone is granted. Message,
MessageRecipient, Party and Account policies/grants remain unchanged. Sender
Accounts remain hidden before and after messages are displayed. There is no new
route or domain model/table. SQLite uses an equivalent batched display lookup
only after existing request/recipient filtering.

Eight physical-role regressions cover51-message closed-case pagination, actual
hidden admin attribution, own-only receipts/key, sibling and outsider isolation,
all council readers, no-actor/worker/oversized denial and inactive sender retention.
One cross-adapter endpoint contract verifies the actual sender/body projection;
SQLite is also run independently. Prior integration findings remain preserved.

Governance integrates d05ed63 (0047/status) then this0048 successor, or the equivalent
complete backend head, and applies migrations serially in its coordinated clone.
Existingctm_app receives execute on install; roles created after migrations require
0048.grant_runtime after existing0038/0043/0044/0046/0047 grant plans. Uninstall drops
the function; revert matching service code too. Coordinate unapplied UI metadata
to a unique later successor (proposed0049); do not renumber applied history.
Applicant reruns the exact51-message journey on the combined successor, and QA
independently records its SHA. Local backend tests do not establish full applicant,
provider or deployment acceptance. No operational migration, merge or deploy by
backend. Broader backend/content/service dependencies remain in backend-status.md.
