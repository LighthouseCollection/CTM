"""Read-only filing labels; never changes category/context/scan/requiredness rules."""
from django.core.exceptions import ValidationError
from django.db import connection
from tribunal.db.context import database_actor
from tribunal.models import SettingRevision
from tribunal.policy import active
from .setting_schemas import validate_setting_value


def filing_requirement_labels(actor, requirements):
    active(actor)
    with database_actor(actor):
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SELECT code,label_en,label_ar FROM public.ctm_document_category_labels()')
                categories = [dict(zip(('code','label_en','label_ar'), row)) for row in cursor.fetchall()]
        else:
            current = SettingRevision.objects.filter(key='document_categories').order_by('-number').first()
            value = current.value if current else {'categories': []}
            try:
                validate_setting_value('document_categories', value)
            except ValidationError:
                return requirements
            categories = value['categories']
    try:
        validate_setting_value('document_categories', {'categories': categories})
    except ValidationError:
        return requirements
    labels = {row['code']: row for row in categories}
    return [{**row, **({'label_en': labels[row['category']]['label_en'],
                       'label_ar': labels[row['category']]['label_ar']}
                      if row['category'] in labels else {})} for row in requirements]
