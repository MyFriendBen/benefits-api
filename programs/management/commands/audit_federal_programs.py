"""
Fail when a program is active under both the `federal` white label and a state one.

Federal programs are shown to every white label, so moving a program to `federal` means
deactivating its state rows. A name still active on both sides is a configuration error:
the results page would log it and show only the federal row, which hides the drift rather
than fixing it. This command surfaces it instead, exiting non-zero so a deploy stops.

Usage:
    python manage.py audit_federal_programs

Read-only: it writes nothing.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from programs.federal import active_duplicates


class Command(BaseCommand):
    help = "Exit non-zero if any program is active under both the federal white label and another one."

    def handle(self, *args: Any, **options: Any) -> None:
        duplicates = active_duplicates()
        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No program is active under both federal and another white label."))
            return

        lines = [f"  {name}: federal and {', '.join(codes)}" for name, codes in sorted(duplicates.items())]
        raise CommandError(
            f"{len(duplicates)} program(s) active under both federal and another white label. "
            "Deactivate the state rows:\n" + "\n".join(lines)
        )
