# D20 recording status, exact transcript review and retry

Backend issue #2 / draft PR #7. These batches extend the existing model adapter;
approved151-table sources stay unchanged. Live transcription remains unconfigured.

## Council read contracts

`GET /api/reports/{id}/recordings/` returns council-only `{items:[...]}`:

- Recording `{id,file_id,mime_type,byte_count,notice_recorded,created_at,finalized_at}`.
  `duration_ms` and `captured_by` retain supplied measurement and actual association
  actor for new captures; unknown legacy facts remain null. `recording_notice` retains
  supplied acknowledgement detail. See twenty-batch-continuation.md for new inputs.
  File uploader identity is not substituted for the capture author.
- `download_url` is the existing authorized file route only while the original is
  safe. Unsafe originals receive null; the file route independently reauthorizes
  every byte/range/preview request.
- `processing` is null or latest `{run_id,state,attempt,engine,safe_error,updated_at,
  can_retry}`. Stored `completed` maps to API `succeeded`; queued/running/failed
  retain their names. Raw diagnostic errors are not serialized. `updated_at` is
  null because the current run model has no such recorded timestamp. A queued job
  means queued work, not provider acceptance or successful transcription.
- `transcripts` contains metadata only for exact output versions the caller may
  read: `{id,kind,language,version,reviewed,actor,timestamp}`. Unreviewed versions are
  absent for ordinary council readers. No text/segments are included in this list.
- `can_finalize` requires current write authority, safe original, recorded notice
  and an open case/proceeding, with no prior finalization.

`GET /api/transcripts/{revision_id}/` returns exact
`{id,recording_id,run_id,kind,language,version,text,segments,reviewed,can_review,timestamp}`.
Applicant/anonymous access is denied. The output must match the finalized safe
recording and a completed transcription run. Before review, only the currently
authorized reviewer can read it; afterward other council may read that exact
version. Another version never inherits review. Assessment material is excluded
from the ordinary recording/transcript workflow even if a medical release exists.
All API responses remain private/no-store.

## Review and retry

`POST /api/transcripts/{revision_id}/review/` takes an empty JSON object and returns
the retained review `{id}` with201. Only current case writer/admin/secretary may
review report output; testimony review requires admin/secretary. It validates the
latest version for that recording/language/kind and the safe completed source.
Repeated same-actor/version review returns the same record/audit. Earlier reviewed
versions remain readable history; later versions need their own review. Historical
review does not reopen substantive closed-case writes.

`POST /api/processing/{run_id}/retry/` takes an empty JSON object and returns the
new `{id,attempt,state:'queued'}` with201. It requires a failed transcription run,
safe finalized source, current reviewer authority and an open original proceeding.
It creates a new numbered attempt and outbox job, retaining the original run and
every prior output. Repeating/concurrently retrying that same failed run returns
its already-created successor instead of another job. Queued/running/completed
attempts cannot be restarted through this endpoint. Repeated recording finalize
continues to return original attempt1; intentional retry uses the separate route.

Migration0026 replaces the single file/purpose identity with unique
`file,purpose,attempt`. Migration0027 forces RLS on Recording, ProcessingRun,
TranscriptRevision and TranscriptReview. It scopes council reads, hides unreviewed
generated content, protects source/run identity and prevents applicant access,
forged review and runtime impersonation of provider output. Application roles can
queue eligible attempts; provider-output insertion/state transitions remain denied
until a separate reviewed worker scope exists. No worker success is fabricated.

## Remaining boundaries

This does not configure a provider, certify WebM/MP4 processing, approve recording
notice wording/category or provide unlimited/chunked
streaming. Existing500MB uploads remain a limitation. Council browser/device/range
acceptance remains independent of synthetic backend tests. Rollback of the attempt
schema after multiple attempts exist requires retaining/reconciling that history;
it cannot silently collapse it into one run.

55 of63 domain tables now have forced RLS;8 remain for review. Full151-table
reconciliation, institutional/provider acceptance and operational deployment remain
separate. No operational migrations, credentials, deployment or merge occurred.
