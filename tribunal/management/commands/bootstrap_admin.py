from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tribunal.models import Account


class Command(BaseCommand):
    help = "Create first preauthorized Microsoft administrator. No CTM password is created."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--microsoft-subject", required=True)
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        if Account.objects.filter(role="admin").exists():
            raise CommandError(
                "An admin already exists; use existing-admin enrollment."
            )
        user = Account.objects.create_user(
            email=options["email"],
            role="admin",
            first_name=options["first_name"],
            last_name=options["last_name"],
            microsoft_subject=options["microsoft_subject"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Preauthorized admin {user.pk}. Microsoft tenant must be configured before sign-in."
            )
        )
