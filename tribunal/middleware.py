from django.contrib.auth import logout


class ActiveAccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
        return self.get_response(request)


class DatabaseActorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from tribunal.db.context import database_actor

        with database_actor(request.user):
            return self.get_response(request)


class PrivateResponseMiddleware:
    """Keep case/account payloads and capability pages out of intermediary caches."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path == "/" or request.path.startswith(
            ("/api/", "/accounts/", "/external/reports/")
        ):
            response["Cache-Control"] = "private, no-store"
            # Preserve same-origin form POST Origin checks; external navigation
            # still receives no referrer (including OAuth provider redirects).
            response["Referrer-Policy"] = "same-origin"
            response["X-Content-Type-Options"] = "nosniff"
        return response
