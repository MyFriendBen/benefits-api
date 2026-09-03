from django.core.management.base import BaseCommand

from programs.fpl_values import sync_fpl_values


class Command(BaseCommand):
    help = (
        "Rewrite the FederalPovertyLimitValue table from the _FPL_DEFAULTS constant. "
        "Runs on deploy; run it by hand after adding a year to the constant outside "
        "a release. Idempotent. --dry-run reports the diff and exits non-zero if the "
        "table is out of date, so it can be used as a drift check."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing. Exits 1 if anything would change.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        counts = sync_fpl_values(dry_run=dry_run)
        changed = counts["created"] + counts["updated"] + counts["deleted"]
        summary = f"{counts['created']} created, {counts['updated']} updated, {counts['deleted']} deleted"

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"FPL values synced: {summary}."))
            return

        if changed:
            # Non-zero so this can be wired up as a drift alarm. A table that is out
            # of date means the dashboard is banding households against stale
            # thresholds, which is a wrong number rather than a missing one.
            self.stderr.write(self.style.ERROR(f"FPL values are OUT OF DATE: would be {summary}."))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("FPL values are up to date."))
