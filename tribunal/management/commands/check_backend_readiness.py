import json
from django.core.management.base import BaseCommand, CommandError
from tribunal.services.readiness import database_readiness


class Command(BaseCommand):
    help = "Read-only runtime-role/schema readiness gate; never grants privileges or deploys."

    def add_arguments(self, parser):
        parser.add_argument("--report-only", action="store_true", help="Collect blockers without a failing exit code.")

    def handle(self, *args, **options):
        report = database_readiness()
        self.stdout.write(json.dumps(report, indent=2))
        if not report["ready_for_deployment"] and not options["report_only"]:
            raise CommandError("Backend deployment readiness gates are not satisfied.")
