from django.core.management.base import BaseCommand

from programs.fpl_values import sync_fpl_values


class Command(BaseCommand):
    help = (
        "Rewrite the FederalPovertyLimitValue table from the _FPL_DEFAULTS constant. "
        "Run this after adding a year to the constant so SQL-only consumers (the "
        "analytics pipeline) see the new thresholds. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from programs.fpl_values import MAX_MATERIALIZED_SIZE, limits_for_period
            from programs.models import FederalPovertyLimitValue, _get_fpl_data

            wanted = {
                (period, size): limit
                for period, table in _get_fpl_data().items()
                for size, limit in limits_for_period(table, MAX_MATERIALIZED_SIZE).items()
            }
            existing = {
                (row.period, row.household_size): row.annual_limit for row in FederalPovertyLimitValue.objects.all()
            }

            created = sum(1 for key in wanted if key not in existing)
            updated = sum(1 for key, limit in wanted.items() if key in existing and existing[key] != limit)
            deleted = sum(1 for key in existing if key not in wanted)

            self.stdout.write(f"Would create {created}, update {updated}, delete {deleted} row(s).")
            return

        counts = sync_fpl_values()

        self.stdout.write(
            self.style.SUCCESS(
                f"FPL values synced: {counts['created']} created, "
                f"{counts['updated']} updated, {counts['deleted']} deleted."
            )
        )
