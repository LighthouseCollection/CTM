# Direct blank priest-request PDF

`GET /api/requests/{request_id}/print.pdf` returns an actual PDF attachment named
`priest-request-{UUID}.pdf`. The existing HTML browser-print endpoint remains.
Council owns download controls and final screen/content acceptance.

## Source and authorization

The existing printable_priest_request projection is authoritative: active council
case writer (admin/secretary/assigned manager), open case and proceeding, unfinished
draft/sent external_priest request. A recipient bearer capability cannot authorize
this endpoint. Completed/cancelled/closed/other-kind requests are rejected before
the renderer starts. Unknown IDs404; unsigned session401; non-GET405.

The saved title/instructions, subject/priest display names, request ID and blank
writing lines are the entire document content. No generated question, sample
wording, signature, submitted answer, saved response, email address, capability,
hash or provider identity is passed to the renderer. GET creates no attachment,
audit, report, completion, invitation or new online link. Original request data
is retained unchanged.

Django escapes all text before rendering. First-strong Unicode direction is
calculated explicitly for each saved text block, preserving its characters;
this handles mixed Latin/Arabic text in PDF engines that do not implement HTML
dir=auto consistently. DejaVu Sans is installed locally and embedded/subset into
the PDF. Arabic shapes/RTL and a one-page A4 synthetic document were inspected;
approved-content and council UI acceptance remain separate.

## Runtime and failure contract

Pinned WeasyPrint70.0 renders the fixed template in a disposable Python process.
All URL fetches are rejected, including http/https/file/data. There is no document
API upload, script, remote CSS/font, arbitrary template, shell interpolation or
user-selected output path. The process uses stdin/stdout; the service persists
no generated document or temporary source file. Renderer stderr is discarded and
saved wording is not included in diagnostic messages.

Limits:512,000 UTF-8 HTML bytes before execution (oversize422, no truncation),
30seconds parent wall timeout,40 output pages and8,000,000 PDF bytes. On POSIX,
the child also has20CPU seconds,768MiB address space and disabled core dumps.
The parent rejects non-PDF or oversized output. Native-library/import failures,
timeout, process failure or invalid output return503 `pdf_unavailable` with an
instruction to use browser printing, never a successful empty/fake PDF. On
platforms without resource limits, the fixed-input bound and parent wall timeout
still apply; the native renderer libraries must be installed for success.

Success includes application/pdf, safe UUID filename, private/no-store,
no-referrer, nosniff and a restrictive CSP. Normal authenticated CSRF/session
rules and private response middleware remain in effect.

## Dependencies and integration

pyproject.toml/uv.lock and exported deploy/requirements.txt include the pinned
renderer and its resolved dependencies. deploy/Dockerfile adds PangoFT2,
HarfBuzz subset and DejaVu fonts; CI installs the same native libraries/fonts
and Poppler utilities for real output/font checks. The application already used
Pango/Cairo-related packages. Governance must build the updated image before
expecting PDF generation; old runtimes fail503 rather than faking success.

The new endpoint is in tribunal/priest_pdf_api.py to avoid simultaneous edits to
the shared API module while B-S1 owns its additive wrappers. The coordinated
ctm/urls.py patch adds only its import and the print.pdf route. No migrations,
runtime grants, settings descriptors or B-S1 service files are changed.0051
remains reserved for B-S1; UI metadata sequencing stays with governance.

Missing live-service credentials do not block this local renderer. No email,
transcription or OCR success is claimed. Paper upload/completion remains a
separate workflow and never follows automatically from printing a blank PDF.

Primary implementation references: [WeasyPrint first steps and local dependencies](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html),
[public API and URL fetchers](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html).

## Validation

Final924 PostgreSQL passed,1 skipped; no model drift.22 new PDF regressions
plus11 existing print regressions pass, including real font/content inspection,
restricted app SQL sessions, EN/AR/both, secret exclusion, writer/open-source
authorization, oversized complete content, crash/timeout/missing renderer and
invalid output. SQLite real-PDF HTTP contract separately passed.

A production-style image built from the updated dependency export/native-library
Dockerfile rendered a10,053-byte one-page A4 Arabic PDF as UID1000 with read-only
filesystem and network none. Its synthetic Arabic output was rasterized and
visually inspected. The build used a temporary equivalent Dockerfile with a
build-secret CA mount for this environment, without persisting that CA. This is
local evidence, not a shared-server deployment or council content acceptance.
