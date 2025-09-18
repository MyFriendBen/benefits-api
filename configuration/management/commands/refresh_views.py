from sqlite3 import DatabaseError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


VIEWS = [
    "data",
    "data_current_benefits",
    "data_householdmembers",
    "data_immediate_needs",
    "data_previous_benefits",
    "data_programs",
]


class Command(BaseCommand):
    help = "Refresh all materialized views"

    def handle(self, *args, **kwargs):
        failures = []
        with connection.cursor() as cursor:
            for view in VIEWS:

                try:
                    self.stdout.write(f"Refreshing {view}...")
                    ident = connection.ops.quote_name(view)  # safe for unqualified names
                    cursor.execute(f"REFRESH MATERIALIZED VIEW {ident};")
                except DatabaseError as e:
                    failures.append((view, str(e)))
                    self.stderr.write(self.style.ERROR(f"Failed to refresh {view}: {e}\n"))
        if failures:
            failed_list = ", ".join(v for v, _ in failures)
            raise CommandError(f"Materialized view refresh failed for: {failed_list}")

        self.stdout.write(self.style.SUCCESS("All materialized views refreshed."))
