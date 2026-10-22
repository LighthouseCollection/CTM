from django.contrib.auth import logout


class DatabaseSessionIdentityMiddleware:
    """Only a decoded server session can bootstrap the account read for auth.

    AuthenticationMiddleware still verifies the backend/session authentication hash;
    DatabaseActorMiddleware subsequently replaces this with the authenticated actor.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import uuid
        from tribunal.db.context import database_settings
        try:
            identifier = str(uuid.UUID(str(request.session.get("_auth_user_id", ""))))
        except (ValueError, TypeError):
            identifier = ""
        with database_settings({"ctm.session_account": identifier}):
            return self.get_response(request)


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

        from contextlib import ExitStack

        with database_actor(request.user), ExitStack() as provider_scope:
            # Activated only by the social adapter after provider/CTM validation.
            # Keep allauth's later is_existing/login queries in the same scope.
            request._ctm_provider_scope = provider_scope
            try:
                return self.get_response(request)
            finally:
                del request._ctm_provider_scope


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
            if request.path.startswith("/external/reports/"):
                response["Referrer-Policy"] = "no-referrer"
            else:
                response.setdefault("Referrer-Policy", "same-origin")
            response["X-Content-Type-Options"] = "nosniff"
        return response
