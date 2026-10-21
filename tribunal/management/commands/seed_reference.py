import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from tribunal.models import ReportQuestion, QuestionnaireVersion


class Command(BaseCommand):
    help = "Load exact approved question bank and versioned form configuration, not real case data."

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "tribunal/reference/question-bank.json"
        bank = json.loads(path.read_text(encoding="utf-8"))["questions"]
        for q in bank:
            ReportQuestion.objects.get_or_create(
                code=q["code"],
                version=1,
                defaults={
                    "category": q["category"],
                    "wording_en": q["wording_en"],
                    "foundational": q["foundational"],
                    "guidance": q["conditional_guidance"],
                },
            )
        fields = [
            {"code": k, "type": t, "required": True}
            for k, t in [
                ("first_name", "text"),
                ("last_name", "text"),
                ("birth_date", "date"),
                ("gender", "choice"),
                ("marriage_date", "date"),
                ("grounds", "list"),
            ]
        ]
        fields[3]["choices"] = ["M", "F"]
        # Do not publish institution-unapproved declaration text or medical release wording.
        QuestionnaireVersion.objects.get_or_create(
            purpose="petition",
            number=1,
            defaults={
                "definition": {
                    "fields": fields,
                    "required_document_categories": ["CMC"],
                },
                "published": False,
            },
        )
        QuestionnaireVersion.objects.get_or_create(
            purpose="appeal",
            number=1,
            defaults={
                "definition": {
                    "fields": [
                        {"code": "statement", "type": "text", "required": True},
                        {"code": "new_information", "type": "text", "required": True},
                    ]
                },
                "published": False,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(bank)} exact English questions; form definitions remain unpublished pending declaration/content validation."
            )
        )
