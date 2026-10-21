import os
import time
import uuid
from django.core.management.base import BaseCommand, CommandError
from tribunal.models import Outbox
from tribunal.tasks import dispatch_outbox
from django.conf import settings


class Command(BaseCommand):
    help = "Exercise the real broker/default worker using only the isolated validation database."

    def handle(self, *args, **options):
        if (
            os.environ.get("CTM_ISOLATED_VALIDATION") != "true"
            or settings.CELERY_TASK_ALWAYS_EAGER
        ):
            raise CommandError(
                "Requires isolated validation and a real asynchronous broker."
            )
        event = Outbox.objects.create(
            key="worker-smoke:" + uuid.uuid4().hex, kind="worker_smoke"
        )
        dispatch_outbox.apply_async(queue="default")
        try:
            for _ in range(40):
                event.refresh_from_db()
                if event.attempts:
                    self.stdout.write(
                        "WORKER_SMOKE_OK: default queue consumed and durable retry recorded"
                    )
                    return
                time.sleep(0.5)
            raise CommandError(
                "Worker did not consume the default queue within20 seconds."
            )
        finally:
            Outbox.objects.filter(pk=event.pk).delete()
