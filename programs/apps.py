from django.apps import AppConfig


class ProgramsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "programs"

    def ready(self) -> None:
        # Import signal handlers
        from . import signals

        return super().ready()
