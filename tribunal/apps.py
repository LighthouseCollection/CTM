from django.apps import AppConfig


class TribunalConfig(AppConfig):
    name = "tribunal"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signals
