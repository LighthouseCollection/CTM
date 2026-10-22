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
from tribunal.validation import validate_json_value, VersionConflict
import re

_UNBOUND = object()

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
        forbidden = {re.sub(r"[^a-z0-9]", "", key) for key in SECRET_KEYS} | {
            "authorization", "bearertoken", "accesskey", "accesstoken", "refreshtoken",
        }
        if any(re.sub(r"[^a-z0-9]", "", str(key).casefold()) in forbidden for key in value):
            raise ValidationError(
                "Store provider credentials in protected server secrets, not readable settings."
            )
        for child in value.values():
            safe_configuration(child)
    elif isinstance(value, list):
        for child in value:
            safe_configuration(child)


@transaction.atomic
def save_setting(actor, key, value, *, expected_version=_UNBOUND, schema_version=1):
    administrator(actor)
    if not isinstance(key, str):
        raise ValidationError("Unsupported setting key.")
    if key not in {
        "translation_prompt",
        "translation_routing",
        "tribunal_contact",
        "email_templates",
        "document_categories",
        "recommended_doctors",
    }:
        raise ValidationError("Unsupported setting key.")
    validate_json_value(value, maximum=100_000)
    safe_configuration(value)
    from .setting_schemas import validate_setting_value
    validate_setting_value(key, value, schema_version=schema_version)
    lock_key(f"setting:{key}")
    number = (
        SettingRevision.objects.filter(key=key).aggregate(n=Max("number"))["n"] or 0
    ) + 1
    if expected_version is not _UNBOUND:
        if type(expected_version) is not int or expected_version < 0:
            raise ValidationError("expected_version must be a non-negative integer.")
        if expected_version != number - 1:
            raise VersionConflict(number - 1)
    record = SettingRevision.objects.create(
        key=key, number=number, value=value, actor=actor
    )
    audit(actor, "setting_saved", record)
    return record


@transaction.atomic
def create_template(actor, title, questions, shared=False):
    staff(actor)
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ValidationError("Provide a template title of1–200 characters.")
    if type(shared) is not bool:
        raise ValidationError("shared must be a boolean.")
    validate_json_value(title)
    if (not isinstance(questions, list) or len(questions) > 500
            or any(not isinstance(code, str) or not code.strip() or len(code) > 100 for code in questions)
            or len(set(questions)) != len(questions)):
        raise ValidationError("Provide at most500 distinct question codes as a list.")
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
        title=title.strip(), shared=shared, owner=None if shared else actor
    )
    TemplateVersion.objects.create(
        template=template, number=1, questions=snapshots, actor=actor
    )
    audit(actor, "template_created", template)
    return template


@transaction.atomic
def publish_personal_template(actor, template_id):
    administrator(actor)
    lock_key(f"template:{template_id}")
    source = ReportTemplate.objects.get(pk=template_id, shared=False, retired=False)
    version = (
        TemplateVersion.objects.filter(template=source).order_by("-number").first()
    )
    if version is None:
        raise ValidationError("A retained template version is required before publication.")
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
def retire_template(actor, template_id):
    staff(actor)
    lock_key(f"template:{template_id}")
    template = ReportTemplate.objects.select_for_update(of=("self",)).get(pk=template_id)
    if template.shared:
        administrator(actor)
    elif template.owner_id != actor.pk:
        raise PermissionDenied("Only the owner may retire a personal template.")
    if not template.retired:
        template.retired = True
        template.save(update_fields=["retired"])
        audit(actor, "template_retired", template)
    return template


@transaction.atomic
def publish_questionnaire(actor, purpose, definition, declaration_en, declaration_ar):
    administrator(actor)
    if (
        not isinstance(purpose, str) or purpose not in {"petition", "appeal", "medical_release"}
        or not isinstance(declaration_en, str) or not declaration_en.strip()
        or not isinstance(declaration_ar, str) or not declaration_ar.strip()
        or len(declaration_en) > 100_000 or len(declaration_ar) > 100_000
    ):
        raise ValidationError(
            "Approved English and Arabic declaration text is required."
        )
    validate_json_value([declaration_en, declaration_ar], maximum=1_000_000)
    validate_questionnaire_definition(definition)
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


def validate_questionnaire_definition(definition):
    if not isinstance(definition, dict):
        raise ValidationError("Invalid questionnaire definition.")
    validate_json_value(definition)
    fields = definition.get("fields", [])
    if not isinstance(fields, list) or len(fields) > 500:
        raise ValidationError("Provide at most500 configured fields as a list.")
    codes = {}
    for field in fields:
        if not isinstance(field, dict):
            raise ValidationError("Invalid configured field definition.")
        code, kind = field.get("code"), field.get("type")
        if (not isinstance(code, str) or not code.strip() or code != code.strip()
                or len(code) > 100 or code in codes
                or not isinstance(kind, str) or kind not in {"text", "textarea", "date", "choice", "boolean", "list"}):
            raise ValidationError("Field codes must be distinct and have a supported type.")
        codes[code] = field
        if "item_fields" in field:
            if kind != "list" or not isinstance(field["item_fields"], list) or not field["item_fields"]:
                raise ValidationError("item_fields requires a nonempty list of repeat field definitions.")
            validate_questionnaire_definition({"fields": field["item_fields"]})
        if "required" in field and type(field["required"]) is not bool:
            raise ValidationError("required must be a boolean.")
        if kind == "choice":
            choices = field.get("choices")
            if (not isinstance(choices, list) or not 1 <= len(choices) <= 500
                    or any(not isinstance(item, str) or not item.strip() for item in choices)
                    or len(set(choices)) != len(choices)):
                raise ValidationError("Choice fields require distinct nonempty string choices.")
    for code, field in codes.items():
        if "when" not in field:
            continue
        rule = field["when"]
        if (not isinstance(rule, dict) or set(rule) != {"field", "equals"}
                or not isinstance(rule["field"], str) or rule["field"] not in codes):
            raise ValidationError("Conditions must reference a configured field and equality value.")
        # Use the same vocabulary as runtime answers, so unreachable conditions
        # cannot silently hide required questions.
        from types import SimpleNamespace
        from tribunal.validation import validate_answers
        source = {**codes[rule["field"]], "required": True}
        source.pop("when", None)
        validate_answers(SimpleNamespace(definition={"fields": [source]}), {source["code"]: rule["equals"]})
    for code in codes:
        seen = set()
        cursor = code
        while "when" in codes[cursor]:
            if cursor in seen:
                raise ValidationError("Conditional fields cannot contain dependency cycles.")
            seen.add(cursor)
            cursor = codes[cursor]["when"]["field"]
    categories = definition.get("required_document_categories", [])
    from .applications import DOCUMENT_LABELS
    if (not isinstance(categories, list) or len(categories) > len(DOCUMENT_LABELS)
            or any(not isinstance(item, str) or item not in DOCUMENT_LABELS for item in categories)
            or len(set(categories)) != len(categories)):
        raise ValidationError("Use distinct supported filing document categories.")
