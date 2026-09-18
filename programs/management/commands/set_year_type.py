import argparse
from typing import Any
from django.core.management.base import BaseCommand
from programs.models import Program


class Command(BaseCommand):
    help = "Assign year_type to programs"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("year_type", choices=["calendar_year", "fiscal_year", "hardcoded"])
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--programs", nargs="+", help="External names to target (e.g. co_snap il_medicaid)")
        target.add_argument("--all", action="store_true", help="Apply to all programs")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many/which programs would be updated without saving changes",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        year_type = options["year_type"]
        dry_run = options["dry_run"]

        if options["all"]:
            programs = Program.objects.all()
        else:
            requested = set(options["programs"])
            programs = Program.objects.filter(external_name__in=requested)
            found = set(programs.values_list("external_name", flat=True))
            missing = requested - found
            if missing:
                self.stdout.write(self.style.WARNING(f"Not found: {', '.join(missing)}"))

        if dry_run:
            names = sorted(programs.values_list("external_name", flat=True))
            self.stdout.write(f"Would update {len(names)} program(s) to year_type='{year_type}':")
            for name in names:
                self.stdout.write(f"  {name}")
            return

        # Save per-instance rather than a bulk .update(): Program.save() is what
        # keeps `year` pointed at the right FederalPoveryLimit row for the chosen
        # year_type, and a queryset .update() bypasses save() entirely.
        updated = 0
        for program in programs:
            program.year_type = year_type
            program.save(update_fields=["year_type", "year"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} program(s) to year_type='{year_type}'"))
