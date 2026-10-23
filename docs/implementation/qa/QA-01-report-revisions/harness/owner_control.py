"""Control for the 404-vs-403 finding: same denied requests, but connected as the table owner.

The owner has the migration_owner bypass policy (like the backend's pytest database user),
so SELECT ... FOR UPDATE finds the row and the service's own permission checks run.
Every request is rolled back afterwards; nothing is persisted.
"""

import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qa01_settings")
os.environ["QA01_DB_ROLE"] = "qa_owner"
import django  # noqa: E402

django.setup()
from django.db import transaction  # noqa: E402
from django.test import Client  # noqa: E402

from qa_env import EVIDENCE, fixtures  # noqa: E402
from django.db.models import Max  # noqa: E402
from tribunal.models import Account, ReportRevision  # noqa: E402

F = fixtures()
out = []
for who, report in [("wilson", "a_main"), ("miller", "a_main"), ("thompson", "a_intake"), ("wilson", "d_main"),
                    ("wilson", "b_old"), ("thompson", "c_main"), ("collins", "c_main")]:
    client = Client(HTTP_HOST="127.0.0.1")
    client.force_login(Account.objects.get(pk=F["people"][who]["id"]),
                       backend="allauth.account.auth_backends.AuthenticationBackend")
    with transaction.atomic():
        res = client.post(f"/api/reports/{F['reports'][report]}/revisions/",
                          data=json.dumps({"answers": {"QA-HIST": "control"}, "observations": "",
                                           "expected_version": ReportRevision.objects.filter(report_id=F["reports"][report])
                                           .aggregate(n=Max("number"))["n"]}),
                          content_type="application/json")
        transaction.set_rollback(True)
    out.append({"actor": who, "report": report, "status": res.status_code, "body": res.json()})
    print(who, report, res.status_code, res.json())
(EVIDENCE / "owner-role-control.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
