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
            #
            # Not interactive: CI has no one to answer, and a renamed field or model makes
            # makemigrations ask "Was x renamed to y? [y/N]" even in a dry run, which crashes
            # with EOFError (or waits forever on a laptop). Without asking, a rename is
            # reported as a remove plus an add.
            call_command(
                "makemigrations",
                *labels,
                check=True,
                dry_run=True,
                interactive=False,
                verbosity=options["verbosity"],
                stdout=self.stdout,
                stderr=self.stderr,
            )
        except SystemExit as exit_:
            # Both codes mean a model change has no migration. 1: --check listed the migrations
            # it would create. 3: a new non-nullable or auto_now_add field (renamed or not) has
            # no default to fill existing rows, and makemigrations printed which one.
            if exit_.code in (1, 3):
                raise CommandError(
                    "Model changes have no migration (see above). Run `python manage.py makemigrations` "
                    "and commit the new files. For an app with no migrations folder yet, name it: "
                    "`python manage.py makemigrations <app_label>`."
                ) from None
            raise
        self.stdout.write("Migrations: none missing, none conflicting.")
