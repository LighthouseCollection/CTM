import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Fail closed when the present backend lacks required public-deployment protections."

    def handle(self, *args, **options):
        blockers = []
        if settings.DEBUG:
            blockers.append("DEBUG must be disabled")
        if connection.vendor != "postgresql":
            blockers.append("PostgreSQL is required")
        else:
            from tribunal.services.readiness import database_readiness
            blockers.extend(database_readiness()["blockers"])
        if not settings.MICROSOFT_TENANT_ID:
            blockers.append("Council Microsoft tenant/provider setup incomplete")
        for provider in ["microsoft", "google", "apple"]:
            if provider not in settings.SOCIALACCOUNT_PROVIDERS:
                blockers.append(f"{provider} provider credentials absent")
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
            blockers.append("Stripe checkout/webhook not configured")
        if not settings.EMAIL_HOST:
            blockers.append("Email delivery not configured")
        # Deliberate implementation gates: these cannot be cleared by setting an environment flag.
        blockers.extend(
            [
                "Full Plenix applicant/council workflows and Arabic acceptance remain incomplete",
                "151-table contract reconciliation is incomplete",
                "Backup restoration, provider login and end-to-end ten-user demonstration remain unverified",
            ]
        )
        self.stdout.write(
            json.dumps(
                {"public_deployment_ready": not blockers, "blockers": blockers},
                indent=2,
            )
        )
        if blockers:
            raise CommandError(
                "Public deployment is not ready; see the implementation status report."
            )
