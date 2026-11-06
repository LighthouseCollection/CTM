"""#116 council session answers and Send reminder now (own module, not api.py)."""
from django.http import JsonResponse

from tribunal.api import body, endpoint
from tribunal.services.session_reminders import answer_session, send_reminders_now, session_answers


@endpoint(("POST",))
def answer(request, session_id):
    answer_session(request.user, session_id, body(request).get("answer"))
    return JsonResponse(session_answers(request.user, session_id))


@endpoint(("GET",))
def answers(request, session_id):
    return JsonResponse(session_answers(request.user, session_id))


@endpoint(("POST",))
def reminders(request, session_id):
    return JsonResponse({"queued": send_reminders_now(request.user, session_id)})
