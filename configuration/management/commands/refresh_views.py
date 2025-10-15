from django.db.utils import DatabaseError, ProgrammingError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


VIEWS = {
    "v2_dependencies": ["data_referrer_codes", "data"],
    "v2_batch_1": [
        "data_current_benefits",
        "data_householdmembers",
        "data_immediate_needs",
        "data_previous_benefits",
        "data_programs",
    ],
    "v1_dependencies": ["reference_data"],
    "v1_batch_1": [
        "reference_data_211co_previous_benefits",
        "reference_data_211co",
        "reference_data_achd",
        "reference_data_achs_previous_benefits",
        "reference_data_achs",
        "reference_data_bia_previous_benefits",
        "reference_data_bia",
        "reference_data_brightbytext_previous_benefits",
        "reference_data_brightbytext",
    ],
    "v1_batch_2": [
        "reference_data_cch_previous_benefits",
        "reference_data_cch",
        "reference_data_ccig_previous_benefits",
        "reference_data_ccig",
        "reference_data_cedp_previous_benefits",
        "reference_data_cedp",
        "reference_data_dhs_previous_benefits",
        "reference_data_dhs",
    ],
    "v1_batch_3": [
        "reference_data_eaglecounty_previous_benefits",
        "reference_data_eaglecounty",
        "reference_data_eligibility",
        "reference_data_gac_previous_benefits",
        "reference_data_gac",
        "reference_data_jeffcohs_previous_benefits",
        "reference_data_jeffcohs",
    ],
    "v1_batch_4": [
        "reference_data_larimercounty_previous_benefits",
        "reference_data_larimercounty",
        "reference_data_lgs_previous_benefits",
        "reference_data_lgs",
        "reference_data_previous_benefits",
        "reference_data_pueblocounty_previous_benefits",
        "reference_data_pueblocounty",
    ],
    "v1_batch_5": [
        "reference_data_salud_previous_benefits",
        "reference_data_salud",
        "reference_data_tellercounty_previous_benefits",
        "reference_data_tellercounty",
        "reference_data_villageexchange_previous_benefits",
        "reference_data_villageexchange",
    ],
}


class Command(BaseCommand):
    help = "Refresh all materialized views"

    def add_arguments(self, parser):
        parser.add_argument(
            "--views",
            nargs="+",
            help="Specify which group of views to refresh (e.g., v1_batch_1). If omitted, refreshes all groups.",
        )

    def handle(self, *args, **options):
        selected_groups = options.get("views")
        db_errors = []
        skipped = []
        failures = []

        # Determine which views to refresh
        if selected_groups:
            invalid_groups = [g for g in selected_groups if g not in VIEWS]

            if invalid_groups:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid group(s): {', '.join(invalid_groups)}. Available groups: {', '.join(VIEWS.keys())}"
                    )
                )
                return

            # Build dictionary of only requested groups
            groups_to_refresh = {g: VIEWS[g] for g in selected_groups}
        else:
            groups_to_refresh = VIEWS  # Refresh all groups if none specified

        # Process each group
        for group_name, views in groups_to_refresh.items():
            self.stdout.write(self.style.NOTICE(f"Refreshing group: {group_name} ({len(views)} views)"))

            with connection.cursor() as cursor:
                for view in views:

                    try:
                        msg = f"Refreshing {view}... {self.style.SUCCESS('Done')}"
                        ident = connection.ops.quote_name(view)  # safe for unqualified names
                        cursor.execute(f"REFRESH MATERIALIZED VIEW {ident};")
                        self.stdout.write(msg)
                    except DatabaseError as e:
                        db_errors.append((view, str(e)))
                    except ProgrammingError as e:
                        skipped.append((view, str(e)))
                        msg = f"Refreshing {view}... {self.style.WARNING('Skipped')}"
                        self.stdout.write(msg)
                    except Exception as e:
                        failures.append((view, str(e)))

        if db_errors:
            db_errors_list = ", ".join(v for v, _ in db_errors)
            self.stdout.write(self.style.WARNING(f"Database errors for materialized views: {db_errors_list}"))

        if skipped:
            skipped_list = ", ".join(v for v, _ in skipped)
            self.stdout.write(self.style.WARNING(f"Skipped materialized views: {skipped_list}"))

        if failures:
            failed_list = ", ".join(v for v, _ in failures)
            raise CommandError(f"Materialized view refresh failed for: {failed_list}")

        self.stdout.write(self.style.SUCCESS("All available materialized views refreshed."))
