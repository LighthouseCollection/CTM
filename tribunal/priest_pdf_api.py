"""Separate endpoint module to avoid concurrent edits to the shared API module."""
from django.http import HttpResponse, JsonResponse
from tribunal.api import endpoint
from tribunal.services.priest_pdf import priest_request_pdf, PDFUnavailable


@endpoint()
def download_priest_request_pdf(request, request_id):
    try:
        pdf = priest_request_pdf(request.user, request_id)
    except PDFUnavailable:
        return JsonResponse({'error': 'pdf_unavailable',
                             'detail': 'PDF generation is unavailable; use the browser print view.'}, status=503)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="priest-request-{request_id}.pdf"'
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'; sandbox"
    return response
