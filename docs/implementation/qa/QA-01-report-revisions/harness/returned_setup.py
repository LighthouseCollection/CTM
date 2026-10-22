"""Run 4 setup (owner role, setup only): two ready, fee-waived petition drafts for fictional applicants.

Mirrors the backend's own ready_application fixture (tests/conftest.py): service-created draft,
the four required documents marked clean, authorized fee waiver by an administrator.
Everything after this point is exercised over HTTP as ctm_app by returned_scenarios.py.
"""

import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qa01_settings")
os.environ["QA01_DB_ROLE"] = "qa_owner"
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.test import Client  # noqa: E402

from qa_env import SECRETS_DIR, fixtures  # noqa: E402
from tribunal.models import Account, Attachment, FileTechnicalEvent, FileVersion  # noqa: E402
from tribunal.services.applications import save_answers, start_application, waive_fee  # noqa: E402

F = fixtures()
admin = Account.objects.get(pk=F["people"]["anderson"]["id"])
out = {"applicants": {}}
# A published bilingual petition form is required before any filing (same minimal definition as the
# backend's autouse test fixture). Published through the real admin configuration service.
from tribunal.models import QuestionnaireVersion  # noqa: E402
from tribunal.services.configuration import publish_questionnaire  # noqa: E402

if not QuestionnaireVersion.objects.filter(purpose="petition", published=True).exists():
    try:
        publish_questionnaire(admin, "petition", {"required_document_categories": ["CMC"]},
                              "Fictional QA declaration.", "إقرار تجريبي للاختبار.")
        out["questionnaire"] = "published via services.configuration.publish_questionnaire"
    except Exception as exc:  # record, then fall back to the test fixture's direct row
        QuestionnaireVersion.objects.create(purpose="petition", number=1, published=True,
                                            definition={"required_document_categories": ["CMC"]},
                                            declaration_en="Fictional QA declaration.", declaration_ar="إقرار تجريبي للاختبار.")
        out["questionnaire"] = f"service refused ({type(exc).__name__}: {exc}); created like tests/conftest.py"
print("questionnaire:", out.get("questionnaire", "already published"))
for key, first, last, birth, spouse_known in [("hannah", "Hannah", "Brooks", "1986-02-11", False),
                                              ("olivia", "Olivia", "Parker", "1984-07-23", True)]:
    owner = Account.objects.create_user(email=f"{key}@qa01.test", first_name=first, last_name=last, email_verified=True)
    app = start_application(owner)
    answers = {"first_name": first, "last_name": last, "birth_date": birth, "gender": "F",
               "marriage_date": "2011-06-18", "grounds": ["desertion"], "statement": "Fictional QA statement."}
    if spouse_known:
        answers["spouse_birth_date"] = "1983-09-05"
    save_answers(owner, app.pk, answers, 0)
    for category in ["MC", "CMC", "CDD", "PHOTO"]:
        attachment = Attachment.objects.create(application=app, owner=owner, category=category)
        version = FileVersion.objects.create(
            attachment=attachment, number=1, object_key=f"qa01/{attachment.pk}", original_name="file.pdf",
            display_name="file.pdf", mime_type="image/jpeg" if category == "PHOTO" else "application/pdf",
            byte_count=5, sha256="a" * 64, actor=owner)
        FileTechnicalEvent.objects.create(file=version, task="scan", result="clean")
    waive_fee(admin, app.pk)
    app.refresh_from_db()
    client = Client()
    client.force_login(owner, backend="allauth.account.auth_backends.AuthenticationBackend")
    out["applicants"][key] = {"account_id": str(owner.pk), "application_id": str(app.pk), "version": app.current_version,
                              "spouse_birth_date_known": spouse_known, "name": f"{first} {last}",
                              "cookie": client.cookies[settings.SESSION_COOKIE_NAME].value}
(SECRETS_DIR / "returned.json").write_text(json.dumps(out, indent=2))
print("Prepared", len(out["applicants"]), "fee-waived drafts; ids and test sessions stored outside the repository.")
