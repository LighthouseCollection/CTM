"""Generate an authorized blank request PDF without persisting another source."""
from pathlib import Path
import subprocess
import sys
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from tribunal.priest_pdf_worker import MAX_HTML_BYTES, MAX_PDF_BYTES
from .priest_print import printable_priest_request


class PDFUnavailable(Exception):
    pass


def priest_request_pdf(actor, request_id):
    projection = printable_priest_request(actor, request_id)
    source = render_to_string('tribunal/priest_request_print.html', projection).encode('utf-8')
    if len(source) > MAX_HTML_BYTES:
        raise ValidationError('The complete request is too large for PDF generation; use the browser print view.')
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'tribunal.priest_pdf_worker'],
            input=source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parents[2], timeout=30, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        raise PDFUnavailable from None
    if not result.stdout.startswith(b'%PDF-') or len(result.stdout) > MAX_PDF_BYTES:
        raise PDFUnavailable
    return result.stdout
