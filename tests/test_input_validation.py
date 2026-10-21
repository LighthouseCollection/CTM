import pytest
from django.core.exceptions import ValidationError
from tribunal.services.applications import save_answers, submit_application
from tribunal.validation import validate_answers

pytestmark = pytest.mark.django_db


def test_null_statement_is_not_a_petition(ready_application):
    app = ready_application
    revision = app.revisions.get(number=1)
    save_answers(app.owner, app.pk, {**revision.answers, "statement": None}, 1)
    with pytest.raises(ValidationError):
        submit_application(
            app.owner,
            app.pk,
            "null-statement",
            {"accepted": True, "name": "John Smith"},
        )


def test_string_false_cannot_attest(ready_application):
    with pytest.raises(ValidationError):
        submit_application(
            ready_application.owner,
            ready_application.pk,
            "bad-attestation",
            {"accepted": "false", "name": "John Smith"},
        )


def test_required_text_cannot_be_whitespace(ready_application):
    from tribunal.models import QuestionnaireVersion

    schema = QuestionnaireVersion(
        definition={"fields": [{"code": "name", "type": "text", "required": True}]}
    )
    with pytest.raises(ValidationError):
        validate_answers(schema, {"name": "   "})
