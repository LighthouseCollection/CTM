# Council-recorded external-priest report completion

`POST /api/requests/{request_id}/recording-completion/`

```json
{
  "file_id":"00000000-0000-0000-0000-000000000001",
  "completion_date":"2026-10-22",
  "recording_notice":{"acknowledged":true},
  "duration_ms":1200,
  "expected_version":"existing request_version value"
}
```

The example is synthetic. No source wording, recording or notice is seeded.
The actual council recorder declares that the person was informed; CTM retains
that declaration and actor, not a fabricated signed consent or priest authorship.

## Preconditions and source

An active case writer (admin/secretary/assigned manager) acts on a sent
external_priest request with sent_at and the exact request version. The case and
proceeding must be open for a new completion. Completion date is the supplied
received date in canonical YYYY-MM-DD, no later than Los Angeles today.

First upload a council case/proceeding recording through the existing file API,
category AUDIO, with no application/request/owner association. Supply its current
FileVersion after a latest clean scan. MIME must be audio/* or video/*, visibility
council; it cannot already belong to another Recording. This uses the existing
case-original media contract; do not pass request_id to that upload. The explicit
ReportRevision files link and Recording report link associate it with the request
at completion. Bytes, file hash and storage key are retained, not rewritten.

recording_notice must be bounded valid JSON, with literal acknowledged:true;
string booleans, null bytes, nonfinite values and excessive nesting/size fail.
Optional duration_ms is a nonnegative measured integer, never boolean, or null.
Unknown API fields are rejected.

## Atomic result and recovery

The stable proceeding lock serializes request writers and closure. One transaction
creates Report.method recording with the actual council author/received date,
one immutable revision containing only the original file ID, and Recording with
actual captured_by, declared notice and measured duration. The recording is
finalized before creating the queued transcription attempt and durable outbox
job. The request becomes completed; report_received notifies the current manager;
the completion audit retains the actual council recorder. Audit/queue/source
failure rolls everything back, retaining the uploaded original.

201 returns only id (report), recording_id, method and completion_date. An exact
same-actor/file/date/notice/duration/version retry returns the original receipt
without another recording/run/job/audit. It can recover after closure; changed
retries fail. Current writer authorization is still required. Request.saved_response
is retained as earlier draft evidence; it is not copied into the recorded source.

The old online link cannot submit again. Its separate unexpired status/receipt
endpoint recognizes this method and exposes only the same minimal report ID/time.
No recipient capability can call the council completion endpoint or read audio.
Applicants remain denied originals, recordings and transcripts. All existing
council original-media reads and exact transcript-review boundaries remain.

General narrative edits reject recording reports, and reports-list can_revise is
false. A recording is not replaced with council-written priest testimony. A
follow-up, or a separately attributed transcript correction/review, is required.

## PostgreSQL controls and migration graph

0052_external_recording_completion is an independent backend leaf depending on
0050_member_administration. B-S1's reserved0051 belongs to Desktop-R and is not
included or fabricated here. Before combining both branches, governance must
sequence the unapplied graph with an explicit merge-only successor or coordinated
unapplied dependencies, including UI metadata's later unique identity. Do not run
both leaves against the shared server without that integration step. No applied
migration is renamed and no other stream's code is integrated by this delivery.

New private helpers prove exact request/file/date/notice context, actual writer,
current clean source and absence of an existing recording. The report root and
initial revision require the exact original-file answer and actual actor. The
media INSERT/UPDATE guard for this method additionally proves that the captured
actor/notice/file match the report's retained source. No app/worker direct EXEC
grant to either helper and no new table/runtime grants are introduced. Existing
medical/paper/file-privacy branches remain intact.

Migration round-trip tests restore the actual source graph's tribunal leaves
instead of overwriting either stream's hard-coded migration number. This identical
small restoration change is coordinated with B-S1; grant lists remain unchanged.
Reverse0052 restores0049 report/revision/receipt and the latest media-writing function,
including0029 attributed transcript corrections, then drops only the new helpers. Existing reports/media/audits remain. Matching
application controls are required for retained source protection after rollback;
the older SQL write guards alone are not acceptance of the new source method.

## Remaining recording work and exact dependencies

This makes an already uploaded council recording into a completed report; it
does not finish the whole capture or processing journey. Browser capture,
pause/resume/recoverable chunks, uncapped whole-event transfer, and recipient
recording upload remain unfinished. Existing ordinary upload size limits remain.

Transcription state is **queued**, not succeeded. The current dispatcher rejects
transcribe as unconfigured; a reviewed provider adapter and source-bound worker
write scope still need implementation and operational binding. No transcript,
translation, speaker segmentation or AI review is fabricated by finalization.
An observed provider run and independent review acceptance remain required.

Council owns upload/readiness/completion controls. Governance owns exact successor
integration/image/test migrations; QA independently verifies that combined SHA.
Wrong-upload correction, integrated OCR and actual invitation email are separate
unfinished priest workflows. No merge/deploy/shared-database operation is included.

## Validation

Full run:951 PostgreSQL passed,1 skipped, including27 new recording-completion
checks; no model drift. A separate new rollback regression passed after the full
run, proving that attributed transcript correction works under the actual app
role with0052 reversed, then restoring the source graph leaves. SQLite recording
HTTP completion separately passed. Existing restricted-role correction tests also
passed alongside the new focused checks.

The first broad run exposed an accidentally omitted0029 transcript-correction
branch in the replacement media function; it was restored in forward and reverse
paths before the passing evidence above. Synthetic source bytes and controlled
clean scan/provider fixtures are test evidence, not live scan/transcription or
whole-event capture acceptance.
