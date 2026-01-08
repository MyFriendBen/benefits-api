"""
Export screener data to CSV files.

Exports completed screener data from the following tables:
- Screen
- HouseholdMember
- IncomeStream
- Expense
- Insurance
- ProgramEligibility (merged from EligibilitySnapshot + ProgramEligibilitySnapshot,
  only the most recent snapshot per screen to match current screen data)

Note: Test data (is_test=True or is_test_data=True) is always excluded from exports.

Usage:
    # Export CSV files
    python manage.py export_screener_data --output-dir /path/to/exports

    # Export with date range
    python manage.py export_screener_data --start-date 2024-01-01 --end-date 2024-12-31 --output-dir /path/to/exports

    # Filter by white label
    python manage.py export_screener_data --output-dir /path/to/exports --white-label co nc
"""

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils import timezone
from screener.models import (
    Screen,
    HouseholdMember,
    IncomeStream,
    Expense,
    Insurance,
    EligibilitySnapshot,
    ProgramEligibilitySnapshot,
)


class Command(BaseCommand):
    help = """
    Export screener data to CSV files for completed screeners within a date range.
    Test data is always excluded.
    """

    # Fields to exclude from export (test flags, internal fields, etc.)
    EXCLUDED_FIELDS = {"is_test", "is_test_data", "frontend_id", "user", "uid", "content"}

    def _get_model_fields(self, model):
        """Get exportable field names from a model, excluding reverse relations and specified fields."""
        fields = []
        for field in model._meta.get_fields():
            # Skip reverse relations and many-to-many
            if field.one_to_many or field.many_to_many:
                continue
            # Skip excluded fields
            if field.name in self.EXCLUDED_FIELDS:
                continue
            # For foreign keys, use the _id suffix
            if field.is_relation and field.many_to_one:
                fields.append(f"{field.name}_id")
            else:
                fields.append(field.name)
        return fields

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            type=str,
            required=False,
            help="Start date for export range (YYYY-MM-DD). If not provided, exports from the beginning.",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            required=False,
            help="End date for export range (YYYY-MM-DD). If not provided, exports all data from start date onward.",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            required=True,
            help="Directory to save CSV files",
        )
        parser.add_argument(
            "--white-label",
            type=str,
            nargs="+",
            required=False,
            help="Filter by white label code(s) (e.g., --white-label co nc)",
        )

    def handle(self, *args, **options):
        # Parse dates
        start_date = None
        if options["start_date"]:
            try:
                start_date = timezone.make_aware(datetime.strptime(options["start_date"], "%Y-%m-%d"))
            except ValueError:
                raise CommandError("Invalid start date format. Use YYYY-MM-DD.")

        end_date = None
        if options["end_date"]:
            try:
                end_date = timezone.make_aware(datetime.strptime(options["end_date"], "%Y-%m-%d"))
            except ValueError:
                raise CommandError("Invalid end date format. Use YYYY-MM-DD.")

        output_dir = options["output_dir"]
        white_label = options.get("white_label")

        # Validate output directory
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.stdout.write(f"Created output directory: {output_dir}")
            except OSError as e:
                raise CommandError(f"Could not create output directory: {e}")

        # Build the queryset
        screens = Screen.objects.filter(
            completed=True,
            agree_to_tos=True,
            is_test=False,
            is_test_data=False,
        )

        if start_date:
            screens = screens.filter(submission_date__gte=start_date)

        if end_date:
            screens = screens.filter(submission_date__lte=end_date)

        if white_label:
            screens = screens.filter(white_label__code__in=white_label)

        screens = screens.order_by("submission_date")

        screen_count = screens.count()
        if screen_count == 0:
            self.stdout.write(self.style.WARNING("No screens found matching the criteria."))
            return

        self.stdout.write(f"Found {screen_count} screens to export.")

        self._export(screens, output_dir)

        self.stdout.write(self.style.SUCCESS(f"Export completed to {output_dir}"))

    def _export(self, screens, output_dir):
        """Export data as separate CSV files, one per table."""
        screen_ids = list(screens.values_list("id", flat=True))

        # Get field lists dynamically
        screen_fields = self._get_model_fields(Screen)
        household_member_fields = self._get_model_fields(HouseholdMember)
        income_stream_fields = self._get_model_fields(IncomeStream)
        expense_fields = self._get_model_fields(Expense)
        insurance_fields = self._get_model_fields(Insurance)

        # Export screens
        self._write_csv(
            os.path.join(output_dir, "screens.csv"),
            screen_fields,
            screens.values(*screen_fields),
        )
        self.stdout.write(f"  Exported {screens.count()} screens")

        # Export household members
        household_members = HouseholdMember.objects.filter(screen_id__in=screen_ids)
        member_ids = list(household_members.values_list("id", flat=True))
        self._write_csv(
            os.path.join(output_dir, "household_members.csv"),
            household_member_fields,
            household_members.values(*household_member_fields),
        )
        self.stdout.write(f"  Exported {household_members.count()} household members")

        # Export income streams
        income_streams = IncomeStream.objects.filter(screen_id__in=screen_ids)
        self._write_csv(
            os.path.join(output_dir, "income_streams.csv"),
            income_stream_fields,
            income_streams.values(*income_stream_fields),
        )
        self.stdout.write(f"  Exported {income_streams.count()} income streams")

        # Export expenses
        expenses = Expense.objects.filter(screen_id__in=screen_ids)
        self._write_csv(
            os.path.join(output_dir, "expenses.csv"),
            expense_fields,
            expenses.values(*expense_fields),
        )
        self.stdout.write(f"  Exported {expenses.count()} expenses")

        # Export insurance (linked via household_member_id)
        insurance_records = Insurance.objects.filter(household_member_id__in=member_ids)
        self._write_csv(
            os.path.join(output_dir, "insurance.csv"),
            insurance_fields,
            insurance_records.values(*insurance_fields),
        )
        self.stdout.write(f"  Exported {insurance_records.count()} insurance records")

        # Export program eligibility (merged table with screen_id, only most recent snapshot per screen)
        self._export_program_eligibility(screen_ids, output_dir)

    def _export_program_eligibility(self, screen_ids, output_dir):
        """Export merged eligibility data with screen_id, only the most recent snapshot per screen."""
        # Get the most recent snapshot ID for each screen
        latest_snapshot_ids = (
            EligibilitySnapshot.objects.filter(screen_id__in=screen_ids)
            .values("screen_id")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )

        # Build a mapping of snapshot_id -> screen_id
        snapshot_to_screen = dict(
            EligibilitySnapshot.objects.filter(id__in=latest_snapshot_ids).values_list("id", "screen_id")
        )

        # Get program eligibility fields, excluding the snapshot FK
        program_fields = self._get_model_fields(ProgramEligibilitySnapshot)
        program_fields = [f for f in program_fields if f != "eligibility_snapshot_id"]

        # Add screen_id as the first column
        headers = ["screen_id"] + program_fields

        # Get the program snapshots for the latest snapshots only
        program_snapshots = ProgramEligibilitySnapshot.objects.filter(
            eligibility_snapshot_id__in=latest_snapshot_ids
        ).order_by("eligibility_snapshot_id", "id")

        # Write the merged CSV
        output_path = os.path.join(output_dir, "program_eligibility.csv")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for prog in program_snapshots:
                screen_id = snapshot_to_screen.get(prog.eligibility_snapshot_id)
                row = [screen_id]
                for field in program_fields:
                    row.append(getattr(prog, field, ""))
                writer.writerow(row)

        self.stdout.write(f"  Exported {program_snapshots.count()} program eligibility records")

    def _write_csv(self, filepath, headers, data):
        """Write a queryset to a CSV file."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
