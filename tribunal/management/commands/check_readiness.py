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
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
                )
                privileged = cursor.fetchone()
                if privileged and any(privileged):
                    blockers.append(
                        "Runtime DB role must not be superuser or bypass RLS"
                    )
                cursor.execute(
                    "SELECT relname FROM pg_class WHERE relnamespace='public'::regnamespace AND relname LIKE 'tribunal_%%' AND relkind='r' AND (NOT relrowsecurity OR NOT relforcerowsecurity)"
                )
                missing = [row[0] for row in cursor.fetchall()]
                if missing:
                    blockers.append(
                        f"Forced row-level security is not installed on {len(missing)} domain tables"
                    )
                cursor.execute(
                    "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relname LIKE 'tribunal_%%' AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)"
                )
                if cursor.fetchone()[0]:
                    blockers.append(
                        "Runtime DB role owns domain tables; use separate migration ownership"
                    )
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
                "Plenix applicant/council UI and Arabic acceptance tests remain unimplemented",
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
