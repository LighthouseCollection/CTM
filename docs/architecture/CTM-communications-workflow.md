# CTM case communications — messaging, email and calls

> **Consolidated build authority (2026-10-21):** Start with [the current build specification](build-spec/README.md). It reconciles and supersedes conflicting requirements below; this document remains source history.

User request, 2026-10-20. Workflow design only; no messages sent, calling server installed or communications UI built. In-app messaging is now explicitly required and supersedes older email-only/no-chat exclusions. It does not imply typing indicators, live presence, group spouse chat or a general cross-program chat platform.

## Communications workspace

Use the agreed list/detail split view: conversations/communication items in the list, selected history and actions in the detail pane. Offer channels for in-app message, email and phone contact. Record actual sender/recipient, case/proceeding, channel, source and server timestamps. Applicant-facing content is private to that applicant. A message to both parties produces separate private deliveries; neither sees the other party's thread, reply or contact details. Existing case-message access and after-closure communication rules remain; messaging cannot silently edit closed case records.

The assigned case manager receives routine case activity notifications. Admin/secretary retain default authorized operational access without automatically receiving every routine case notification. Internal council notes remain distinct from applicant messages.

## In-app messages

Applicants can initiate/reply in their own case communication area; authorized council writers can send/reply within existing role rules. Persist one canonical message and channel-specific delivery/read events; do not count an email notification as a second authored portal message. Use existing portal/email notification behavior, not new real-time infrastructure by assumption. Exact attachment policy for messages is not newly expanded here: formal submissions and evidence use the appropriate portal/request upload locations. No email attachments are ingested as evidence.

## Email

Reuse retained outbound email, inbound-reply routing and recipient verification. Preserve accepted body/header provenance and source association; do not expose another applicant through CC/BCC or a shared conversation. Messages/replies can appear together in the private communication history with channel labels. Email attachments continue to be rejected/returned with the portal submission notice. SMTP/identity credentials are integration settings, never user passwords stored by CTM. Delivery failures have technical status/retry history without pretending that the recipient received the message.

## Calling — two materially different implementations

### Device phone handoff (recommended initial baseline, not yet selected)

A Call action can hand the selected number to the device's registered telephone application using a tel link. CTM can automatically record **Call initiated** at server timestamp, actual user, intended recipient and number used. This is a dial action, not proof of connection. Normal browser telephone links do not return a reliable answer/end/duration/remote-audio event to CTM. Do not label this timestamp as an answered/completed call or capture the device microphone as if it records both sides of a cellular call.

Permit a manual follow-up call log/notes/outcome where needed; distinguish user-entered actual call time/outcome from the system's click timestamp. No platform-level native phone-call interception or browser microphone workaround is added. Incoming/off-platform calls cannot be auto-logged without an actual integration.

### Integrated telephony (optional candidate)

Asterisk is an open-source communications server with call-detail recording and MixMonitor audio recording. It can support automatic answered/end timestamps, call result/duration and recorded audio for calls actually routed through the integrated server. This requires a real SIP/VoIP endpoint, configured users/phones or browser client, CTM integration and a carrier/trunk or equivalent connectivity for ordinary telephone numbers. Open-source software does not make carrier connectivity free. It cannot retroactively capture unrelated personal-phone calls.

Asterisk is a candidate, not an approved installed dependency. Evaluate any existing phone system before adding a PBX to CTM. Enable recording only after the actual routing and institution-approved notice/authorization behavior are configured. Applicable recording obligations are a deployment/content policy dependency, not a blanket assertion about law. Where integrated recording is unavailable, omit that recording feature as requested; do not invent an unreliable replacement.

When a call recording is legitimately available, keep its original private file and provenance linked to the call record, with council-only access by default consistent with internal testimony/report audio. Translation/transcription follows the established recorded-content policy only within authorized scope; call recording must not become a new blanket permission to process medical content externally.

## Proposed data relationships

- communication_threads: case and private recipient scope; access distinct from shared case number.
- communication_messages: authored source body, actual actor/recipient, portal/email channel and immutable sent timestamp; existing source/version and closed-case rules.
- communication_delivery_events: per-channel queued/sent/failed/delivered/read where technically known; deduplication and actual event time.
- call_records: case, participants, actual actor, direction, phone number snapshot, integration/source, initiated/answered/ended timestamps when known, outcome/duration provenance, notes and optional recording links.
- call_event_receipts: authenticated provider/PBX event identity and technical idempotency, distinct from manual call-entry events.
- call_recording_links: private original file version and authorization/notice provenance, processing status and transcription references where authorized.

Existing database entity names may be extended rather than duplicating old correspondence tables. These are proposals, not migrations. Source evidence/claim text is not rewritten by correspondence or derived call transcripts. All activity is case-audited, with sensitive numbers/content excluded from operational error logs.

## Primary references

- Phone links: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/a
- Asterisk overview: https://www.asterisk.org/get-started/
- Call-detail records: https://docs.asterisk.org/Configuration/Reporting/Call-Detail-Records-CDR/
- MixMonitor recording: https://docs.asterisk.org/Asterisk_22_Documentation/API_Documentation/Dialplan_Applications/MixMonitor/

Open decision: device dialer handoff versus an existing/new integrated phone service. Do not confuse documenting software availability with enabling reliable call capture.


## Confirmed integrated messaging decisions — 2026-10-20

- Messaging is native to CTM's signed-in account and existing case authorization. No Zulip or separate messaging identities, account provisioning or manual messaging membership assignment. PostgreSQL retains messages; Plenix supplies the interface. Django Channels is an optional transport for live updates, not a separate account system.
- Sent messages are permanent: no edit or delete action. Corrections are sent as new messages. Preserve actual sender, recipients, case and server timestamp.
- Messages may reference existing case documents or initiate new uploads. Every uploaded file is stored in the appropriate case document category/request with the established naming, version and ownership rules. Messages store references, not a separate attachment repository. Linking alone grants no access; validate recipient authorization before exposing a link or preview. Existing rejection of email attachments remains unchanged.
- No council-only internal chat is needed. Internal material remains in Notes; do not add private council threads to this Communications feature.
- New messages are available immediately in the applicant's authorized portal and council Communications history. Council-side routine message notifications go only to the current assigned case manager, without removing admin/secretary operational authority or council case-read access.
- Email notifications support immediate delivery or inclusion in a summary scheduled for **17:00 America/Los_Angeles**. This is an email-notification schedule, not delayed message sending; do not hide already sent portal messages until the summary. Preserve per-message/per-recipient delivery records so retries and summary generation do not duplicate notices. Time-zone scheduling uses America/Los_Angeles rather than a fixed UTC offset.
- The 17:00 choice concerns communications messages. It does not replace the separately confirmed ten-minute quiet-window summaries for answer corrections, uploads or appeal additions, or mandatory immediate account/security notices.
- Configuration of who chooses the notification mode and handling messages arriving after the daily cutoff has not yet been explicitly decided. Do not silently hold urgent messages or invent a business-day calendar/next-session date. These timing details do not require introducing another messaging account system.

Earlier generic internal-thread or separate messaging-platform proposals are not selected requirements. No communications UI, queue or email integration was built by recording these decisions.


## Current calling and send-action decisions — 2026-10-20

**Calling is resolved for the web version:** manual call documentation only. Record person contacted, user-entered actual call date/time, outcome and notes, plus the actual recording actor and automatic server entry timestamp. Do not confuse the time a record is saved with when the phone call happened. No phone-dial action, live call integration, automatic call-duration detection or telephone-call recording is included. Asterisk and other telephony options remain prior research, not selected dependencies. A future native-phone or phone-system integration requires separate scope.

**Exact message action labels:** `Send Immediately` and `Send after council session`. Both are available. Do not substitute implementation-oriented labels or display a fixed-time label instead. Earlier confirmation retains immediate portal availability; email notification behavior is the scheduled part. The preceding 17:00 America/Los_Angeles assumption remains historical context, not a newly imposed fixed cutoff: the latest label ties the deferred action to the council session. Its scheduler must follow the actual agreed session workflow rather than silently inventing a next-day/business-day rule.

No call or messaging functionality was implemented by this documentation update.
