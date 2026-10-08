"""
Fail when a program is active under both the `federal` white label and a state one.

Federal programs are shown to every white label, so moving a program to `federal` means
deactivating its state rows. A name still active on both sides is a configuration error:
the results page would log it and show only the federal row, which hides the drift rather
than fixing it. Run this by hand during a program's cutover; it exits non-zero on a
duplicate.

It matches on the name alone, so a clean run says nothing about state rows under another
name (`ks_snap`, `tx_eitc`). The cutover ticket's list of rows to switch off covers those.

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
