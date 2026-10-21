from datetime import date
from django.core.exceptions import ValidationError


def validate_answers(schema, answers):
    """Small declarative field vocabulary; no admin-supplied expressions or code."""
    for field in schema.definition.get("fields", []):
        code = field["code"]
        condition = field.get("when")
        if condition and answers.get(condition["field"]) != condition["equals"]:
            continue
        value = answers.get(code)
        if field.get("required") and (value is None or value == "" or value == []):
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
