from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from tribunal.models import Account, QuestionnaireVersion


class Command(BaseCommand):
    help = "Create synthetic unusable-password accounts, only on an explicitly enabled isolated demo database."

    def handle(self, *args, **options):
        import os

        if os.environ.get("CTM_SYNTHETIC_DEMO") != "true":
            raise CommandError(
                "Set CTM_SYNTHETIC_DEMO=true only for an isolated synthetic database."
            )
        for role in ["applicant", "member", "president", "admin", "secretary"]:
            if not Account.objects.filter(email=f"{role}@ctm.example.test").exists():
                Account.objects.create_user(
                    email=f"{role}@ctm.example.test",
                    role=role,
                    first_name=role.title(),
                    last_name="Synthetic",
                    email_verified=True,
                )
        for purpose in ["petition", "appeal"]:
            previous = (
                QuestionnaireVersion.objects.filter(purpose=purpose)
                .order_by("-number")
                .first()
            )
            if previous and not previous.published:
                QuestionnaireVersion.objects.get_or_create(
                    purpose=purpose,
                    number=previous.number + 1,
                    defaults={
                        "definition": previous.definition,
                        "declaration_en": "SYNTHETIC DEMO ONLY — I confirm this fictional submission.",
                        "declaration_ar": "عرض تجريبي فقط — أؤكد هذا الطلب الافتراضي.",
                        "published": True,
                    },
                )
        self.stdout.write(
            "Synthetic accounts created with unusable passwords; no production login bypass provided."
        )
