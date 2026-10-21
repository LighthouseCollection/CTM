"""Authorized private originals with bounded streaming and single-range playback."""

import os
import re
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils.http import (
    content_disposition_header,
    http_date,
    parse_http_date_safe,
)
from tribunal.services.files import (
    authorized_file,
    private_path,
    display_filename,
    INLINE_TYPES_FOR_LIST,
)
from tribunal.services.common import audit


def byte_range(value, size):
    """None means ignore unsupported range forms; ValueError means unsatisfiable."""
    if not value:
        return None
    unit, separator, spec = value.partition("=")
    if not separator or unit.strip().lower() != "bytes" or "," in spec:
        return None
    if len(spec) > 64:
        raise ValueError("Range exceeds supported length")
    match = re.fullmatch(r"([0-9]*)-([0-9]*)", spec.strip())
    if not match or not any(match.groups()) or size == 0:
        raise ValueError("Invalid or unsatisfiable range")
    first, last = match.groups()
    if first:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
        if start >= size or end < start:
            raise ValueError("Unsatisfiable range")
    else:
        suffix = int(last)
        if suffix == 0:
            raise ValueError("Empty suffix range")
        start, end = max(0, size - suffix), size - 1
    return start, end


class RangeStream:
    def __init__(self, handle, start, count):
        self.handle, self.start, self.count = handle, start, count

    def __iter__(self):
        try:
            self.handle.seek(self.start)
            remaining = self.count
            while remaining:
                block = self.handle.read(min(remaining, 64 * 1024))
                if not block:
                    break
                remaining -= len(block)
                yield block
        finally:
            self.close()

    def close(self):
        self.handle.close()


def deliver_file(request, file_id):
    # Authorization and technical validation precede size, validators or range parsing.
    source = authorized_file(request.user, file_id)
    try:
        handle = private_path(source.object_key).open("rb")
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return JsonResponse({"error": "source_unavailable"}, status=503)
    try:
        size = os.fstat(handle.fileno()).st_size
        etag = f'"{source.sha256}"'
        modified = int(source.created_at.timestamp())
        requested = request.headers.get("Range", "") if request.method == "GET" else ""
        condition = request.headers.get("If-Range")
        if (
            condition
            and condition != etag
            and parse_http_date_safe(condition) != modified
        ):
            requested = ""
        inline = (
            request.GET.get("view") == "1" and source.mime_type in INLINE_TYPES_FOR_LIST
        )
        try:
            selected = byte_range(requested, size)
        except ValueError:
            handle.close()
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            response["Cache-Control"] = "private, no-store"
            response["Accept-Ranges"] = "bytes"
            return response
        action = (
            "file_metadata_accessed"
            if request.method == "HEAD"
            else "file_viewed"
            if inline
            else "file_downloaded"
        )
        audit(
            request.user,
            action,
            source,
            source.attachment.case
            or (
                source.attachment.application.case
                if source.attachment.application
                else None
            ),
            metadata={"partial": selected is not None},
        )
        if request.method == "HEAD":
            handle.close()
            response = HttpResponse(content_type=source.mime_type)
        elif selected:
            start, end = selected
            response = StreamingHttpResponse(
                RangeStream(handle, start, end - start + 1),
                status=206,
                content_type=source.mime_type,
            )
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        else:
            response = FileResponse(handle, content_type=source.mime_type)
        response["Content-Length"] = str(
            selected[1] - selected[0] + 1 if selected else size
        )
        response["Content-Disposition"] = content_disposition_header(
            not inline, display_filename(source)
        )
        response["Accept-Ranges"] = "bytes"
        response["ETag"] = etag
        response["Last-Modified"] = http_date(modified)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        if inline:
            response["X-Frame-Options"] = "SAMEORIGIN"
            response["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'self'"
            )
        return response
    except BaseException:
        handle.close()
        raise
