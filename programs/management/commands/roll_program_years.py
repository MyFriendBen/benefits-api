"""
Advance program year FKs for prior_tax_year (and future dynamic) programs.

Run once per year after FPL data is added to _FPL_DEFAULTS and PolicyEngine supports
the new year. Programs whose flip_month has not yet been reached are skipped
automatically and picked up on the next run.

    python manage.py roll_program_years --all --dry-run   # preview
    python manage.py roll_program_years --all             # apply
    python manage.py roll_program_years --programs federal_ctc mo_wftc
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from programs.models import FederalPoveryLimit, Program, _get_fpl_data


class Command(BaseCommand):
    help = "Advance year FKs for prior_tax_year programs whose flip month has arrived."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=date.today().year,
            help="Target base year (default: current calendar year).",
        )
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Roll all eligible programs.")
        group.add_argument("--programs", nargs="+", metavar="ABBR", help="Roll specific programs by name_abbreviated.")
        parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing.")

    def handle(self, *args, **options):
        target_year = options["year"]
        dry_run = options["dry_run"]
        today = date.today()

        if str(target_year) not in _get_fpl_data():
            raise CommandError(f"No FPL data for {target_year}. Add to _FPL_DEFAULTS in programs/models.py first.")

        qs = Program.objects.exclude(year_type__in=["hardcoded", "calendar_year", "fiscal_year"]).select_related(
            "white_label", "year"
        )
        if not options["all"]:
            qs = qs.filter(name_abbreviated__in=options["programs"])

        updated, skipped = [], []
        for program in qs:
            label = f"{program.white_label.code}/{program.name_abbreviated}"
            if today.month < program.flip_month:
                skipped.append(f"  SKIP  {label} (flip_month={program.flip_month}, current month={today.month})")
                continue

            period = str(target_year + program.year_offset)
            fpl_row, _ = FederalPoveryLimit.objects.get_or_create(year=period, defaults={"period": period})
            if not dry_run:
                Program.objects.filter(pk=program.pk).update(year=fpl_row)
            prefix = "DRY   " if dry_run else "OK    "
            updated.append(f"  {prefix}{label}: -> {period}")

        header = f"roll_program_years --year {target_year}"
        if dry_run:
            header += " --dry-run"
        self.stdout.write(f"\n{header}")
        for line in updated + skipped:
            self.stdout.write(line)
        self.stdout.write(
            f"\nSummary: {len(updated)} {'would update' if dry_run else 'updated'}, "
            f"{len(skipped)} skipped (flip month not reached)"
        )
