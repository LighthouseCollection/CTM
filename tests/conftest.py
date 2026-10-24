import pytest
from tribunal.models import (
    QuestionnaireVersion,
    Account,
    Attachment,
    FileVersion,
    FileTechnicalEvent,
)


@pytest.fixture(autouse=True)
def published_questionnaires(db):
    for purpose in ["petition", "appeal", "medical_release"]:
        QuestionnaireVersion.objects.create(
            purpose=purpose,
            number=1,
            published=True,
            definition={
                "required_document_categories": ["CMC"] if purpose == "petition" else []
            },
            declaration_en="Test declaration",
            declaration_ar="إقرار تجريبي",
        )


@pytest.fixture
def people(db):
    return {
        role: Account.objects.create_user(
            email=f"{role}@example.test",
            first_name=role,
            last_name="Test",
            role=role,
            email_verified=True,
        )
        for role in ["applicant", "member", "president", "admin", "secretary"]
    }


@pytest.fixture
def unpaid_application(people):
    from tribunal.services.applications import (
        start_application,
        save_answers,
        waive_fee,
    )

    app = start_application(people["applicant"])
    save_answers(
        people["applicant"],
        app.pk,
        {
            "first_name": "John",
            "last_name": "Smith",
            "birth_date": "1985-03-14",
            "gender": "M",
            "marriage_date": "2010-05-01",
            "spouse_birth_date": "1987-04-02",
            "grounds": ["infidelity"],
            "statement": "Statement",
        },
        0,
    )
    for category in ["MC", "CMC", "CDD", "PHOTO"]:
        attachment = Attachment.objects.create(
            application=app, owner=app.owner, category=category
        )
        file = FileVersion.objects.create(
            attachment=attachment,
            number=1,
            object_key=f"test/{attachment.pk}",
            original_name="file.pdf",
            display_name="file.pdf",
            mime_type="image/jpeg" if category == "PHOTO" else "application/pdf",
            byte_count=5,
            sha256="a" * 64,
            actor=app.owner,
        )
        FileTechnicalEvent.objects.create(file=file, task="scan", result="clean")
    app.refresh_from_db()
    return app


@pytest.fixture
def ready_application(unpaid_application, people):
    from tribunal.services.applications import waive_fee

    waive_fee(people["admin"], unpaid_application.pk)
    unpaid_application.refresh_from_db()
    return unpaid_application


def pytest_make_parametrize_id(config, val, argname):
    """Keep parameter names portable without changing test payloads or checks."""
    text = repr(val)
    if len(text) > 120:
        import hashlib
        return f"{argname}-{type(val).__name__}-{hashlib.sha256(text.encode('utf-8', errors='backslashreplace')).hexdigest()[:10]}"
    return None
