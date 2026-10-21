"""Isolated localhost OAuth review server. Read provider configuration from stdin.

No fixture login, passwords or operational database are used. Secrets remain in
process memory; never run this development server on a public interface.
"""

import os
import logging
import json
import re
import traceback
import secrets
import sys
import uuid
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.chdir(root)
allowed = {
    "MICROSOFT_CLIENT_ID",
    "MICROSOFT_CLIENT_SECRET",
    "MICROSOFT_TENANT_ID",
}
for line in sys.stdin.read().splitlines():
    key, separator, value = line.strip().partition("=")
    if separator and key in allowed:
        os.environ[key] = value.strip().strip("\"'")
if not all(os.environ.get(key) for key in allowed):
    raise SystemExit("Microsoft configuration is incomplete; no server started.")
os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
os.environ["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(48)
from django.conf import settings

run_dir = root / ".tmp" / ("local-microsoft-" + uuid.uuid4().hex)
run_dir.mkdir(parents=True)
settings.DATABASES["default"]["NAME"] = str(run_dir / "isolated.sqlite3")
settings.MEDIA_ROOT = run_dir / "media"
settings.ALLOWED_HOSTS = ["localhost"]
settings.CSRF_TRUSTED_ORIGINS = ["http://localhost:18844"]
settings.SOCIALACCOUNT_STORE_TOKENS = False
settings.SOCIALACCOUNT_PROVIDERS["microsoft"]["AUTH_PARAMS"] = {
    "prompt": "select_account",
    "login_hint": "frraphaelmaher@lacopts.org",
}
settings.SESSION_COOKIE_NAME = "ctm_local_microsoft_session"
settings.DEBUG = False

import django

django.setup()
from tribunal.auth import AccountAdapter


def authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
    # Record categories only, never authorization codes, tokens or provider bodies.
    diagnostic = {
        "exception": type(exception).__name__ if exception else None,
        "error": str(error),
        "state_found": bool((extra_context or {}).get("state")),
        "microsoft_error_codes": re.findall(r"AADSTS\d+", str(exception)),
    }
    (root / ".tmp" / "local-microsoft-diagnostic.json").write_text(
        json.dumps(diagnostic), encoding="utf-8"
    )


AccountAdapter.on_authentication_error = authentication_error
logging.getLogger("django.security.csrf").addHandler(logging.StreamHandler())
from django.core.management import call_command
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application

call_command("migrate", verbosity=0)
call_command(
    "bootstrap_admin",
    email="frraphaelmaher@lacopts.org",
    microsoft_subject="b3683bd7-2bd9-42ba-93f9-374252ed6ca5",
    first_name="Fr. Raphael",
    last_name="Maher",
    verbosity=0,
)
application = StaticFilesHandler(get_wsgi_application())


def csrf_failure(request, reason=""):
    from django.http import HttpResponseForbidden

    print(f"Local CSRF check: {reason}", flush=True)
    return HttpResponseForbidden("Local sign-in CSRF verification failed.")


settings.CSRF_FAILURE_VIEW = csrf_failure


def record_exception(sender, request, **kwargs):
    exc_type, exc, tb = sys.exc_info()
    diagnostic = {
        "exception": exc_type.__name__ if exc_type else None,
        "frames": [
            {"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(tb)
        ],
    }
    (root / ".tmp" / "local-microsoft-server-error.json").write_text(
        json.dumps(diagnostic), encoding="utf-8"
    )


from django.core.signals import got_request_exception

got_request_exception.connect(record_exception, weak=False)


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        # OAuth callback query strings contain temporary authorization codes.
        pass


print("Genuine Microsoft sign-in: http://localhost:18844/", flush=True)
print("Isolated local data; no operational CTM records.", flush=True)
with make_server("127.0.0.1", 18844, application, handler_class=Quiet) as server:
    server.serve_forever()
