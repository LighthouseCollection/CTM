"""POST /api/lists/<name>/ (#312). Search text travels in the body, so nothing about the
request is logged here; the access log has the path only."""
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

from tribunal.api import body, endpoint
from tribunal.lists import REGISTRY, run_list


@endpoint(("POST",))
def list_view(request, name):
    spec = REGISTRY.get(name)
    if spec is None:
        raise ObjectDoesNotExist(name)
    return JsonResponse(run_list(spec, request.user, body(request)))
