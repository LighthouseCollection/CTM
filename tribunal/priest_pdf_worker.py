"""Disposable local renderer: stdin HTML, stdout PDF, no database or URL access."""
import logging
import sys

MAX_HTML_BYTES = 512_000
MAX_PDF_BYTES = 8_000_000


def deny_fetch(url, *args, **kwargs):
    raise ValueError('External resources are disabled for request PDFs.')


def main():
    try:
        try:
            import resource
        except ImportError:
            resource = None
        if resource is not None:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
            resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
        source = sys.stdin.buffer.read(MAX_HTML_BYTES + 1)
        if not source or len(source) > MAX_HTML_BYTES:
            return 1
        from weasyprint import HTML
        logging.getLogger('weasyprint').disabled = True
        document = HTML(string=source.decode('utf-8'), url_fetcher=deny_fetch).render()
        if not 1 <= len(document.pages) <= 40:
            return 1
        pdf = document.write_pdf()
        if not pdf.startswith(b'%PDF-') or len(pdf) > MAX_PDF_BYTES:
            return 1
        sys.stdout.buffer.write(pdf)
        return 0
    except Exception:
        # Never send saved wording, URLs or document diagnostics to server logs.
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
