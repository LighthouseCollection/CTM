"""Serve the assembled CTM app on 127.0.0.1:18870 as the non-owner ctm_app database role.

Threaded, so two HTTP requests really run at the same time (needed for QA-01 scenario 9).
Loopback only; isolated test settings; never expose publicly.
"""

import os
import socketserver
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qa01_settings")
os.environ["QA01_DB_ROLE"] = "ctm_app"

import django  # noqa: E402

django.setup()

from django.contrib.staticfiles.handlers import StaticFilesHandler  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402
from django.db import connection  # noqa: E402


class ThreadingServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True


class Log(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        # Method, path and status only; no headers, cookies or bodies.
        print("%s %s" % (self.address_string(), fmt % args), flush=True)


with connection.cursor() as cursor:
    cursor.execute("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")
    print("runtime database role:", cursor.fetchone(), flush=True)
connection.close()

server = make_server("127.0.0.1", 18870, StaticFilesHandler(get_wsgi_application()),
                     server_class=ThreadingServer, handler_class=Log)
print("QA-01 server on http://127.0.0.1:18870", flush=True)
server.serve_forever()
