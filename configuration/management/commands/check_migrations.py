from typing import Any

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Exit non-zero if any installed app has a model change with no migration, or two migrations on one "
        "parent. CI runs this before migrate; run it locally before pushing a branch that touches models or "
        "migrations. Every app is named explicitly because makemigrations, given no app labels, skips an app "
        "that has models but no migrations package, so a new app would pass while migrate never created its "
        "tables."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        labels = [app_config.label for app_config in apps.get_app_configs()]
        try:
            # A conflict raises CommandError, which propagates with makemigrations' own message
            # (both file names and the --merge fix).
            call_command(
                "makemigrations",
                *labels,
                check=True,
                dry_run=True,
                verbosity=options["verbosity"],
                stdout=self.stdout,
                stderr=self.stderr,
            )
        except SystemExit as exit_:
            # makemigrations --check exits 1 after listing the migrations it would create.
            if exit_.code == 1:
                raise CommandError(
                    "Model changes have no migration (listed above). Run `python manage.py makemigrations` "
                    "and commit the new files."
                ) from None
            raise
        self.stdout.write("Migrations: none missing, none conflicting.")
