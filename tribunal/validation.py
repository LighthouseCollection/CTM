from datetime import date
import json
from django.core.exceptions import ValidationError


class VersionConflict(ValidationError):
    def __init__(self, current_version):
        self.current_version = current_version
        super().__init__("The saved version changed. Reload before saving.")


UNBOUND_VERSION = object()


def json_equivalent(left, right):
    """JSONB equality: numeric scale is immaterial, booleans are distinct."""
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        from decimal import Decimal
        return Decimal(str(left)) == Decimal(str(right))
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equivalent(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equivalent(a, b) for a, b in zip(left, right))
    return left == right


def revision_replay(latest, actor, expected_version, **values):
    """Called under the resource's stable lock, after current authorization."""
    if expected_version is UNBOUND_VERSION:
        return False
    if type(expected_version) is not int or expected_version < 0:
        raise ValidationError("expected_version must be a non-negative integer.")
    current = latest.number if latest else 0
    if latest and current == expected_version + 1 and latest.actor_id == actor.pk:
        if all(json_equivalent(getattr(latest, key), value) for key, value in values.items()):
            return True
    if expected_version != current:
        raise VersionConflict(current)
    return False


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
    """Validate final answers recursively using the published field vocabulary."""
    import uuid
    validate_json_value(answers)
    if not isinstance(answers, dict):
        raise ValidationError("Answers must be an object.")

    def fields_in(fields, values, path=""):
        for field in fields:
            code = field["code"]
            location = f"{path}.{code}" if path else code
            condition = field.get("when")
            if condition and values.get(condition["field"]) != condition["equals"]:
                continue
            value = values.get(code)
            if field.get("required") and (value is None or value == "" or value == []
                    or (isinstance(value, str) and not value.strip())):
                raise ValidationError(f"Required answer missing: {location}")
            if value is None or value == "":
                continue
            kind = field.get("type", "text")
            if kind not in {"text", "textarea", "date", "choice", "boolean", "list"}:
                raise ValidationError(f"Unsupported answer type: {location}")
            if kind in {"text", "textarea", "date", "choice"} and not isinstance(value, str):
                raise ValidationError(f"Invalid answer type: {location}")
            if kind == "date":
                try:
                    date.fromisoformat(value)
                except ValueError:
                    raise ValidationError(f"Invalid date: {location}")
            if kind == "boolean" and type(value) is not bool:
                raise ValidationError(f"Invalid boolean: {location}")
            if kind == "choice" and value not in field.get("choices", []):
                raise ValidationError(f"Invalid choice: {location}")
            if kind == "list":
                if not isinstance(value, list):
                    raise ValidationError(f"Invalid list: {location}")
                if "item_fields" in field:
                    identities = set()
                    for index, row in enumerate(value):
                        row_path = f"{location}[{index}]"
                        if not isinstance(row, dict):
                            raise ValidationError(f"Repeat rows must be objects: {row_path}")
                        try:
                            identity = uuid.UUID(row.get("id", "")) if isinstance(row.get("id"), str) else None
                        except ValueError:
                            identity = None
                        if identity is None or identity in identities:
                            raise ValidationError(f"Repeat rows require distinct stable UUIDs: {row_path}")
                        identities.add(identity)
                        fields_in(field["item_fields"], row, row_path)
                elif "choices" in field and any(not isinstance(item, str) or item not in field["choices"] for item in value):
                    raise ValidationError(f"Invalid list choice: {location}")

    fields_in(schema.definition.get("fields", []), answers)


def validate_attestation(value):
    if (
        not isinstance(value, dict)
        or value.get("accepted") is not True
        or not isinstance(value.get("name"), str)
        or not value["name"].strip()
    ):
        raise ValidationError("Accept the declaration and provide your full name.")
