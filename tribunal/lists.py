"""Server-paged lists (#312): one rule set per list and role, behind POST /api/lists/<name>/.

The design is docs/implementation/slices/ctm3-312-server-lists/design.md (sections 4 and 5).
Totals count only rows the actor may read, search and filters use Exists() so rows never
repeat, and every key outside a list's rules is refused rather than ignored.
"""
import unicodedata
import uuid
from dataclasses import dataclass
from itertools import islice
from typing import Any, Callable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Exists, F, OuterRef, Q, QuerySet, Subquery, UUIDField, Value
from django.db.models.functions import Coalesce, Concat

from tribunal import models as m
from tribunal.policy import active

BODY_KEYS = {"page", "size", "sort", "q", "filters", "facets"}
MAX_PAGE = 1_000_000
MAX_SIZE = 100
COUNCIL_ONLY = "Council access required."
# Arabic-Indic (U+0660..) and Eastern Arabic-Indic (U+06F0..) digits read as ASCII; tatweel dropped.
_DIGITS = {**{0x0660 + n: str(n) for n in range(10)}, **{0x06F0 + n: str(n) for n in range(10)}, 0x0640: None}


@dataclass(frozen=True)
class ListSpec:
    name: str
    authorize: Callable[[m.Account], None]
    queryset: Callable[[m.Account], QuerySet]
    serialize: Callable[[Any, m.Account], dict]
    sorts: Callable[[m.Account], dict]                      # key -> tuple of ORM expressions/field names
    default_sort: Callable[[m.Account, dict], tuple]        # "id" is always appended
    filters: Callable[[m.Account], dict]                    # key -> applier(qs, value) that validates value
    search: Callable[[m.Account], Callable[[QuerySet, str], QuerySet] | None]
    council_only: frozenset = frozenset()
    visible: Callable[[Any], bool] | None = None
    facets: Callable[[], dict] | None = None
    annotate: Callable[[QuerySet, set], QuerySet] | None = None  # sort-only annotations, added after the count


def _integer(data, key, default, high):
    value = data.get(key, default)
    if type(value) is not int or not 1 <= value <= high:
        raise ValidationError(f"{key} must be an integer from 1 to {high}.")
    return value


def normalize_q(value):
    if not isinstance(value, str):
        raise ValidationError("Search text must be 2 to 200 characters.")
    text = unicodedata.normalize("NFC", value).translate(_DIGITS).strip()
    if text and not 2 <= len(text) <= 200:
        raise ValidationError("Search text must be 2 to 200 characters.")
    return text


def _refuse(spec, actor, key, message):
    # Only a string can name a council-only key; a list or object is a plain 422 (G5a I-1).
    if isinstance(key, str) and key in spec.council_only and actor.role == "applicant":
        raise PermissionDenied(COUNCIL_ONLY)
    raise ValidationError(message)


def _sort(spec, actor, value):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 3 or not all(
            isinstance(row, dict) and set(row) <= {"field", "dir"} and isinstance(row.get("dir"), str)
            and row["dir"] in {"asc", "desc"}
            for row in value):
        raise ValidationError("Use up to 3 sort entries, each with dir asc or desc.")
    allowed = spec.sorts(actor)
    for row in value:
        field = row.get("field")
        if not isinstance(field, str) or field not in allowed:
            _refuse(spec, actor, field, f"Unsupported sort field: {field}.")
    return [(row["field"], row["dir"]) for row in value]


def run_list(spec, actor, data):
    """Validate data, then return {items, page, size, total, has_more[, facets]}."""
    active(actor)
    spec.authorize(actor)
    for key in data:
        if key not in BODY_KEYS:
            raise ValidationError(f"Unsupported list option: {key}.")
    page = _integer(data, "page", 1, MAX_PAGE)
    size = _integer(data, "size", 50, MAX_SIZE)
    sort = _sort(spec, actor, data.get("sort"))
    q = normalize_q(data.get("q", ""))
    filters = data.get("filters", {})
    if not isinstance(filters, dict):
        raise ValidationError("filters must be an object.")
    facets = data.get("facets", False)
    if type(facets) is not bool:
        raise ValidationError("facets must be true or false.")

    qs = spec.queryset(actor)
    appliers = spec.filters(actor)
    for key in sorted(filters):
        if key not in appliers:
            _refuse(spec, actor, key, f"Unsupported filter: {key}.")
        qs = appliers[key](qs, filters[key])
    if q:
        search = spec.search(actor)
        if search is None:
            raise PermissionDenied("Search is not available for this list.")
        qs = search(qs, q)

    total = None if spec.visible else qs.count()
    if spec.annotate and sort:
        qs = spec.annotate(qs, {field for field, _ in sort})
    allowed = spec.sorts(actor)
    order = []
    for field, direction in sort:
        for expr in allowed[field]:
            expr = F(expr) if isinstance(expr, str) else expr
            order.append(expr.asc(nulls_last=True) if direction == "asc" else expr.desc(nulls_last=True))
    order += [*spec.default_sort(actor, filters), "id"]
    qs = qs.order_by(*order)
    start = (page - 1) * size
    if spec.visible is None:
        rows = list(qs[start:start + size + 1])
    else:
        rows = list(islice((row for row in qs.iterator(chunk_size=250) if spec.visible(row)), start, start + size + 1))
    result = {"items": [spec.serialize(row, actor) for row in rows[:size]], "page": page, "size": size,
              "total": total, "has_more": len(rows) > size}
    if facets and spec.facets and page == 1:
        result["facets"] = spec.facets()
    return result


# ---- cases ---------------------------------------------------------------------------------

def applicant_case_item(case, actor):
    """SEC-312-1: an applicant's case row. grounds/reason come only from the actor's own
    newest submitted petition; no other party's names, genders or filing data."""
    from tribunal.api import display_status, encoded
    from tribunal.services.applications import submitted_grounds

    own = [app for app in case.applications.all()
           if app.owner_id == actor.pk and app.kind == "petition" and app.submitted_at is not None]
    filing = max(own, key=lambda app: (app.submitted_at, app.id), default=None)
    revision = next((row for row in filing.revisions.all() if row.number == filing.current_version), None) \
        if filing else None
    grounds = submitted_grounds(revision.answers) if revision else []
    manager = case.assigned_member
    return encoded(
        case, number=case.number, status=case.status, display_status=display_status(case, actor),
        assigned_member_id=str(case.assigned_member_id) if case.assigned_member_id else None,
        assigned_member=f"{manager.first_name} {manager.last_name}".strip() if manager else None,
        grounds=grounds, reason="; ".join(grounds) or None,
        closed_at=case.closed_at.isoformat() if case.closed_at else None,
    )


def council_case_item(case, actor):
    from tribunal.api import _case_list_data, display_status, encoded
    from tribunal.services.home import next_step

    manager = case.assigned_member
    return encoded(
        case, number=case.number, status=case.status, display_status=display_status(case, actor),
        assigned_member_id=str(case.assigned_member_id) if case.assigned_member_id else None,
        assigned_member=f"{manager.first_name} {manager.last_name}".strip() if manager else None,
        **_case_list_data(case), next_step=next_step(case),
    )


def case_item(case, actor):
    return applicant_case_item(case, actor) if actor.role == "applicant" else council_case_item(case, actor)


def case_queryset(actor):
    qs = m.Case.objects.all()
    if actor.role == "applicant":
        qs = qs.filter(Exists(m.Party.objects.filter(case=OuterRef("pk"), account=actor)))
    return qs.select_related("assigned_member").prefetch_related(
        "parties", "applications__party", "applications__revisions")


def _status_filter(qs, value):
    if not isinstance(value, str) or value not in {"open", "closed", "any"}:
        raise ValidationError("status must be open, closed or any.")
    return qs if value == "any" else qs.filter(status=value)


def _ids(value, message):
    if not isinstance(value, list) or not 1 <= len(value) <= 100 or not all(isinstance(x, str) for x in value):
        raise ValidationError(message)
    try:
        return [uuid.UUID(x) for x in value]
    except ValueError:
        raise ValidationError(message) from None


def _case_ground_filter(qs, value):
    from tribunal.services.applications import GROUNDS, LEGACY_GROUNDS
    from tribunal.services.filing_privacy import council_revision_answers_q

    if not isinstance(value, str) or value not in GROUNDS:
        raise ValidationError("ground must be one of the six ground codes.")
    values = [value, *(old for old, new in LEGACY_GROUNDS.items() if new == value)]
    newest = m.Application.objects.filter(
        case=OuterRef("case_id"), kind="petition", submitted_at__isnull=False,
    ).order_by("-submitted_at", "-id").values("pk")[:1]
    filing = m.Application.objects.filter(case=OuterRef("pk"), kind="petition", submitted_at__isnull=False,
                                          pk=Subquery(newest))
    return qs.filter(Exists(filing.filter(council_revision_answers_q(values))))


def _only(expected, message, apply):
    def applier(qs, value):
        if value != expected or type(value) is not type(expected):
            raise ValidationError(message)
        return apply(qs)
    return applier


def case_filters(actor):
    rules = {
        "status": _status_filter,
        "ids": lambda qs, value: qs.filter(pk__in=_ids(value, "ids must list 1 to 100 case ids.")),
    }
    if actor.role != "applicant":
        rules.update({
            "mine": _only(True, "mine must be true.", lambda qs: qs.filter(assigned_member=actor)),
            "assigned": _only("none", "assigned must be none.", lambda qs: qs.filter(assigned_member__isnull=True)),
            "ground": _case_ground_filter,
        })
    return rules


def _number_search(qs, q):
    return qs.filter(number__icontains=q)


def _council_case_search(qs, q):
    party = m.Party.objects.filter(case=OuterRef("pk"), name__icontains=q)
    manager = m.Account.objects.alias(full=Concat("first_name", Value(" "), "last_name")).filter(
        pk=OuterRef("assigned_member_id"), full__icontains=q)
    return qs.filter(Q(number__icontains=q) | Exists(party) | Exists(manager))


def case_sorts(actor):
    if actor.role == "applicant":
        return {"number": ("number",), "created_at": ("created_at",), "status": ("status",)}
    return {
        "number": ("number",), "created_at": ("created_at",), "closed_at": ("closed_at",),
        "applicant_name": ("applicant_name",), "respondent_name": ("respondent_name",),
        "assigned_member": ("assigned_member__last_name", "assigned_member__first_name"),
    }


def case_sort_annotations(qs, keys):
    """Mirror _case_list_data: the applicant is the newest submitted petition's party, else slot A."""
    if not keys & {"applicant_name", "respondent_name"}:
        return qs
    filing_party = m.Application.objects.filter(
        case=OuterRef("pk"), kind="petition", submitted_at__isnull=False, party__isnull=False,
    ).order_by("-submitted_at", "-id").values("party_id")[:1]
    first_party = m.Party.objects.filter(case=OuterRef("pk")).order_by("slot").values("pk")[:1]
    qs = qs.annotate(list_applicant_id=Coalesce(Subquery(filing_party), Subquery(first_party), output_field=UUIDField()))
    return qs.annotate(
        applicant_name=Subquery(m.Party.objects.filter(pk=OuterRef("list_applicant_id")).values("name")[:1]),
        respondent_name=Subquery(m.Party.objects.filter(case=OuterRef("pk")).exclude(
            pk=OuterRef("list_applicant_id")).order_by("slot").values("name")[:1]),
    )


CASES = ListSpec(
    name="cases",
    authorize=active,
    queryset=case_queryset,
    serialize=case_item,
    sorts=case_sorts,
    default_sort=lambda actor, filters: ("-created_at",),
    filters=case_filters,
    search=lambda actor: _number_search if actor.role == "applicant" else _council_case_search,
    council_only=frozenset({"mine", "assigned", "ground", "closed_at", "applicant_name", "respondent_name",
                            "assigned_member"}),
    annotate=case_sort_annotations,
)

REGISTRY = {spec.name: spec for spec in [CASES]}
