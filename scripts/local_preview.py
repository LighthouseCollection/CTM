"""Loopback-only review server with synthetic records and test sessions.

This script is outside the application/image. It does not implement provider login
or serve operational data. Visit /__preview/manager, /__preview/admin or
/__preview/applicant to select a synthetic role.
"""

from http.cookies import SimpleCookie
from wsgiref.simple_server import make_server, WSGIRequestHandler
from browser_fixture import prepare_fixture

fixture = prepare_fixture("local-preview-")
from django.conf import settings
from django.test import Client
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application

accounts = {
    "manager": fixture.manager,
    "admin": fixture.admin,
    "applicant": fixture.applicant,
}
sessions = {}


def issue(role):
    client = Client()
    client.force_login(
        accounts[role], backend="allauth.account.auth_backends.AuthenticationBackend"
    )
    sessions[role] = client.cookies[settings.SESSION_COOKIE_NAME].value


for role in accounts:
    issue(role)
application = StaticFilesHandler(get_wsgi_application())


def preview(environ, start_response):
    if environ.get("REMOTE_ADDR") != "127.0.0.1":
        start_response("403 Forbidden", [("Content-Type", "text/plain")])
        return [b"Loopback only"]
    path = environ.get("PATH_INFO", "/")
    cookies = SimpleCookie(environ.get("HTTP_COOKIE", ""))
    if path.startswith("/__preview/"):
        role = path.removeprefix("/__preview/").strip("/")
        if role not in accounts or environ.get("REQUEST_METHOD") != "GET":
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Unknown preview role"]
        issue(role)
        start_response(
            "302 Found",
            [
                ("Location", "/"),
                ("Cache-Control", "no-store"),
                (
                    "Set-Cookie",
                    f"ctm_preview_role={role}; Path=/; HttpOnly; SameSite=Strict",
                ),
            ],
        )
        return [b""]
    role = (
        cookies["ctm_preview_role"].value
        if "ctm_preview_role" in cookies
        else "manager"
    )
    if role not in accounts:
        role = "manager"
    cookies[settings.SESSION_COOKIE_NAME] = sessions[role]
    environ["HTTP_COOKIE"] = "; ".join(
        f"{key}={morsel.coded_value}" for key, morsel in cookies.items()
    )
    return application(environ, start_response)


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


print(
    "CTM LOCAL PREVIEW: http://127.0.0.1:18843/ (synthetic records; no provider login)",
    flush=True,
)
print("Roles: /__preview/manager /__preview/admin /__preview/applicant", flush=True)
print(f"Isolated data: {fixture.run_dir}", flush=True)
with make_server("127.0.0.1", 18843, preview, handler_class=Quiet) as server:
    server.serve_forever()
