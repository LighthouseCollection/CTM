"""Synthetic local-only browser fixtures. Never imported by the application."""

import os
import sys
import uuid
from pathlib import Path
from datetime import date
from types import SimpleNamespace


def prepare_fixture(prefix="browser-integration-"):
    from django.apps import apps
    from django.conf import settings

    if apps.ready or settings.configured:
        raise RuntimeError("Run local fixtures in a fresh, isolated Python process.")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ["DJANGO_SETTINGS_MODULE"] = "ctm.settings_test"
    from django.conf import settings

    run_dir = root / ".tmp" / (prefix + uuid.uuid4().hex)
    run_dir.mkdir(parents=True)
    settings.DATABASES["default"]["NAME"] = str(run_dir / "isolated.sqlite3")
    settings.MEDIA_ROOT = run_dir / "media"
    settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
    settings.DEBUG = True
    import django

    django.setup()
    from django.core.management import call_command
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.wsgi import get_wsgi_application
    from tribunal.models import (
        Account,
        Case,
        Proceeding,
        Party,
        ReportQuestion,
        Notification,
        Message,
    )
    from tribunal.services.council import create_session
    from tribunal.models import Attendance
    from tribunal.services.files import upload
    from tribunal.services.reports import (
        create_request,
        send_request,
        complete_request,
        revise_report,
    )

    call_command("migrate", verbosity=0, interactive=False)
    manager = Account.objects.create_user(
        email="manager@example.test",
        first_name="Council",
        last_name="Tester",
        role="member",
        email_verified=True,
    )
    applicant = Account.objects.create_user(
        email="applicant@example.test",
        first_name="Applicant",
        last_name="Tester",
        email_verified=True,
    )
    outsider = Account.objects.create_user(
        email="outsider@example.test", email_verified=True
    )
    admin = Account.objects.create_user(
        email="admin@example.test",
        first_name="Admin",
        last_name="Tester",
        role="admin",
        email_verified=True,
    )
    session = create_session(admin, date(2030, 1, 2))
    case = Case.objects.create(number="20261021-01", assigned_member=manager)
    proceeding = Proceeding.objects.create(case=case)
    party = Party.objects.create(
        case=case,
        account=applicant,
        slot="A",
        name="Applicant Tester",
        participating=True,
    )
    ReportQuestion.objects.create(
        code="OPEN-TEST",
        category="Identity",
        wording_en="Please state your full name.",
        foundational=True,
    )
    request = create_request(
        manager, proceeding.pk, party.pk, "intake", "Marriage clarification", []
    )
    send_request(manager, request.pk)
    report = complete_request(applicant, request.pk, {"OPEN-TEST": "Applicant Tester"})
    interview_request = create_request(
        manager, proceeding.pk, party.pk, "interview", "Council interview", []
    )
    send_request(manager, interview_request.pk)
    interview_report = complete_request(
        manager, interview_request.pk, {"OPEN-TEST": "Original interview answer"}
    )
    revise_report(
        manager, interview_report.pk, {"OPEN-TEST": "Corrected interview answer"}
    )
    source = upload(
        manager,
        SimpleUploadedFile(
            "marriage.pdf", b"%PDF-1.4\nSynthetic browser validation only."
        ),
        "MC",
        case_id=case.pk,
    )

    return SimpleNamespace(
        root=root,
        run_dir=run_dir,
        manager=manager,
        applicant=applicant,
        outsider=outsider,
        admin=admin,
        session=session,
        case=case,
        source=source,
    )
