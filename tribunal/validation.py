from datetime import date
import json
from django.core.exceptions import ValidationError


class VersionConflict(ValidationError):
    def __init__(self, current_version):
        self.current_version = current_version
        super().__init__("The saved version changed. Reload before saving.")


def validate_json_value(value, *, maximum=500_000):
    """Accept bounded JSON data, including direct service callers outside HTTP."""
    def visit(node, depth=0):
        if depth > 20:
            raise ValidationError("JSON nesting exceeds the supported limit.")
        if isinstance(node, dict):
            if any(not isinstance(key, str) or "\x00" in key for key in node):
                raise ValidationError("JSON object keys must be strings.")
            for child in node.values():
                visit(child, depth + 1)
        elif isinstance(node, list):
            for child in node:
                visit(child, depth + 1)
        elif isinstance(node, str) and "\x00" in node:
            raise ValidationError("Text cannot contain null characters.")
        elif node is not None and type(node) not in {str, int, float, bool}:
            raise ValidationError("Unsupported JSON value.")
    visit(value)
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False)
        size = len(encoded.encode("utf-8"))
    except (ValueError, TypeError, OverflowError, UnicodeError):
        raise ValidationError("Use finite, valid JSON values.")
    if size > maximum:
        raise ValidationError("JSON content exceeds the supported size.")


def validate_answers(schema, answers):
    """Small declarative field vocabulary; no admin-supplied expressions or code."""
    for field in schema.definition.get("fields", []):
        code = field["code"]
        condition = field.get("when")
        if condition and answers.get(condition["field"]) != condition["equals"]:
            continue
        value = answers.get(code)
        if field.get("required") and (
            value is None
            or value == ""
            or value == []
            or (isinstance(value, str) and not value.strip())
        ):
            raise ValidationError(f"Required answer missing: {code}")
        if value is None or value == "":
            continue
        kind = field.get("type", "text")
        if kind in {"text", "date", "choice"} and not isinstance(value, str):
            raise ValidationError(f"Invalid answer type: {code}")
        if kind == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValidationError(f"Invalid date: {code}")
        if kind == "boolean" and not isinstance(value, bool):
            raise ValidationError(f"Invalid boolean: {code}")
        if kind == "list" and not isinstance(value, list):
            raise ValidationError(f"Invalid list: {code}")
        if kind == "choice" and value not in field.get("choices", []):
            raise ValidationError(f"Invalid choice: {code}")


def validate_attestation(value):
    if (
        not isinstance(value, dict)
        or value.get("accepted") is not True
        or not isinstance(value.get("name"), str)
        or not value["name"].strip()
    ):
        raise ValidationError("Accept the declaration and provide your full name.")
