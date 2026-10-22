"""Bounded read-only projections of nonsecret runtime configuration."""

import uuid

from django.core.exceptions import ValidationError
from django.db import connection

from tribunal.db.context import database_actor
from tribunal.models import SettingRevision
from tribunal.policy import active, case_for, staff

from .setting_schemas import validate_setting_value


CONTACT_FIELDS = ("display", "email", "phone", "address")


def tribunal_contact(actor):
    active(actor)
    with database_actor(actor):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT display,email,phone,address,setting_version "
                    "FROM public.ctm_runtime_tribunal_contact()"
                )
                row = cursor.fetchone()
            if not row:
                return {"contact": {}, "version": 0}
            value = {
                field: row[index]
                for index, field in enumerate(CONTACT_FIELDS)
                if row[index] is not None
            }
            version = row[4]
        else:
            current = (
                SettingRevision.objects.filter(key="tribunal_contact")
                .order_by("-number")
                .first()
            )
            if not current:
                return {"contact": {}, "version": 0}
            value = current.value
            version = current.number
    try:
        validate_setting_value("tribunal_contact", value)
    except ValidationError:
        value = {}
    return {"contact": value, "version": version}


def recommended_doctors(actor, case_id, specialty):
    with database_actor(actor):
        staff(actor)
        if specialty not in {"medical", "psychological"}:
            raise ValidationError("Choose medical or psychological specialty.")
        case_for(actor, case_id)
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id,name,specialty,contact,setting_version "
                    "FROM public.ctm_case_recommended_doctors(%s,%s)",
                    [str(case_id), specialty],
                )
                rows = cursor.fetchall()
            version = rows[0][4] if rows else 0
            items = [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "specialty": row[2],
                    "contact": row[3],
                }
                for row in rows
                if row[0] is not None
            ]
            value = {
                "doctors": [
                    {**item, "active": True}
                    for item in items
                ]
            }
        else:
            current = (
                SettingRevision.objects.filter(key="recommended_doctors")
                .order_by("-number")
                .first()
            )
            if not current:
                return {"items": [], "version": 0}
            value = current.value
            version = current.number
    try:
        validate_setting_value("recommended_doctors", value)
    except ValidationError:
        return {"items": [], "version": version}
    items = [
        {
            "id": str(uuid.UUID(row["id"])),
            "name": row["name"],
            "specialty": row["specialty"],
            "contact": row["contact"],
        }
        for row in value["doctors"]
        if row["active"] and row["specialty"] in {specialty, "both"}
    ]
    return {"items": items, "version": version}
