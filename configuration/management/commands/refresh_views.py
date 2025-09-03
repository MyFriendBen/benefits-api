from django.core.management.base import BaseCommand
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
        with connection.cursor() as cursor:
            for view in VIEWS:

                try:
                    self.stdout.write(f"Refreshing {view}...")
                    cursor.execute(f"REFRESH MATERIALIZED VIEW {view};")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to refresh {view}: {e}\n"))
        self.stdout.write(self.style.SUCCESS("All materialized views refreshed!"))
