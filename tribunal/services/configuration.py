from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from tribunal.models import (
    SettingRevision,
    ReportTemplate,
    TemplateVersion,
    ReportQuestion,
    QuestionnaireVersion,
)
from tribunal.policy import administrator, staff
from .common import audit, lock_key

SECRET_KEYS = {
    "api_key",
    "secret",
    "password",
    "token",
    "private_key",
    "client_secret",
    "webhook_secret",
}


def safe_configuration(value):
    if isinstance(value, dict):
        if any(str(key).lower() in SECRET_KEYS for key in value):
            raise ValidationError(
                "Store provider credentials in protected server secrets, not readable settings."
            )
        for child in value.values():
            safe_configuration(child)
    elif isinstance(value, list):
        for child in value:
            safe_configuration(child)


@transaction.atomic
def save_setting(actor, key, value):
    administrator(actor)
    if key not in {
        "translation_prompt",
        "translation_routing",
        "tribunal_contact",
        "email_templates",
        "document_categories",
        "recommended_doctors",
    }:
        raise ValidationError("Unsupported setting key.")
    safe_configuration(value)
    lock_key(f"setting:{key}")
    number = (
        SettingRevision.objects.filter(key=key).aggregate(n=Max("number"))["n"] or 0
    ) + 1
    record = SettingRevision.objects.create(
        key=key, number=number, value=value, actor=actor
    )
    audit(actor, "setting_saved", record)
    return record


@transaction.atomic
def create_template(actor, title, questions, shared=False):
    staff(actor)
    if shared:
        administrator(actor)
    snapshots = []
    for code in questions:
        question = ReportQuestion.objects.filter(code=code).order_by("-version").first()
        if not question:
            raise ValidationError("Question is not published.")
        snapshots.append(
            {
                "code": question.code,
                "version": question.version,
                "en": question.wording_en,
                "ar": question.wording_ar,
            }
        )
    template = ReportTemplate.objects.create(
        title=title, shared=shared, owner=None if shared else actor
    )
    TemplateVersion.objects.create(
        template=template, number=1, questions=snapshots, actor=actor
    )
    audit(actor, "template_created", template)
    return template


@transaction.atomic
def publish_personal_template(actor, template_id):
    administrator(actor)
    source = ReportTemplate.objects.get(pk=template_id, shared=False, retired=False)
    version = (
        TemplateVersion.objects.filter(template=source).order_by("-number").first()
    )
    target = ReportTemplate.objects.create(title=source.title, shared=True)
    TemplateVersion.objects.create(
        template=target, number=1, questions=version.questions, actor=actor
    )
    audit(
        actor,
        "template_published",
        target,
        metadata={"source_template": str(source.pk)},
    )
    return target


@transaction.atomic
def publish_questionnaire(actor, purpose, definition, declaration_en, declaration_ar):
    administrator(actor)
    if (
        purpose not in {"petition", "appeal", "medical_release"}
        or not declaration_en.strip()
        or not declaration_ar.strip()
    ):
        raise ValidationError(
            "Approved English and Arabic declaration text is required."
        )
    if not isinstance(definition, dict):
        raise ValidationError("Invalid questionnaire definition.")
    for field in definition.get("fields", []):
        if (
            not isinstance(field, dict)
            or not field.get("code")
            or field.get("type") not in {"text", "date", "choice", "boolean", "list"}
        ):
            raise ValidationError("Invalid configured field definition.")
        if field.get("when") and (
            not isinstance(field["when"], dict)
            or "field" not in field["when"]
            or "equals" not in field["when"]
        ):
            raise ValidationError("Invalid conditional field rule.")
    lock_key(f"questionnaire:{purpose}")
    number = (
        QuestionnaireVersion.objects.filter(purpose=purpose).aggregate(n=Max("number"))[
            "n"
        ]
        or 0
    ) + 1
    version = QuestionnaireVersion.objects.create(
        purpose=purpose,
        number=number,
        definition=definition,
        declaration_en=declaration_en,
        declaration_ar=declaration_ar,
        published=True,
    )
    from tribunal.models import Application, AnswerRevision

    for app in Application.objects.select_for_update(of=("self",)).filter(
        kind=purpose, status="draft", submitted_at__isnull=True
    ):
        if app.checkoutintent_set.filter(
            state__in=["pending", "paid", "needs_review"]
        ).exists():
            continue
        app.questionnaire = version
        app.save(update_fields=["questionnaire"])
        from .common import notify

        notify(
            app.owner,
            "questionnaire_updated",
            version,
            payload={"new_required_questions": True},
        )
    audit(actor, "questionnaire_published", version)
    return version
