"""
Export screener data to CSV files.

Exports completed screener data from the following tables:
- Screen
- HouseholdMember
- IncomeStream
- Expense
- Insurance
- EligibilitySnapshot
- ProgramEligibilitySnapshot

Note: Test data (is_test=True or is_test_data=True) is always excluded from exports.

Usage:
    # Export as separate CSV files (default)
    python manage.py export_screener_data --start-date 2024-01-01 --output-dir /path/to/exports

    # Export with end date
    python manage.py export_screener_data --start-date 2024-01-01 --end-date 2024-12-31 --output-dir /path/to/exports

    # Export as single flattened CSV
    python manage.py export_screener_data --start-date 2024-01-01 --output-dir /path/to/exports --format flat

    # Filter by white label
    python manage.py export_screener_data --start-date 2024-01-01 --output-dir /path/to/exports --white-label co
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
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
    Test data is always excluded. Supports two formats:
    - 'separate' (default): One CSV file per table with foreign keys for joining
    - 'flat': Single denormalized CSV with one row per screen
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
            "--format",
            type=str,
            choices=["separate", "flat"],
            default="separate",
            help="Export format: 'separate' (one CSV per table) or 'flat' (single denormalized CSV). Default: separate",
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
        export_format = options["format"]
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

        if export_format == "separate":
            self._export_separate(screens, output_dir)
        else:
            self._export_flat(screens, output_dir)

        self.stdout.write(self.style.SUCCESS(f"Export completed to {output_dir}"))

    def _export_separate(self, screens, output_dir):
        """Export data as separate CSV files, one per table."""
        screen_ids = list(screens.values_list("id", flat=True))

        # Get field lists dynamically
        screen_fields = self._get_model_fields(Screen)
        household_member_fields = self._get_model_fields(HouseholdMember)
        income_stream_fields = self._get_model_fields(IncomeStream)
        expense_fields = self._get_model_fields(Expense)
        insurance_fields = self._get_model_fields(Insurance)
        eligibility_snapshot_fields = self._get_model_fields(EligibilitySnapshot)
        program_eligibility_snapshot_fields = self._get_model_fields(ProgramEligibilitySnapshot)

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

        # Export eligibility snapshots
        eligibility_snapshots = EligibilitySnapshot.objects.filter(screen_id__in=screen_ids)
        snapshot_ids = list(eligibility_snapshots.values_list("id", flat=True))
        self._write_csv(
            os.path.join(output_dir, "eligibility_snapshots.csv"),
            eligibility_snapshot_fields,
            eligibility_snapshots.values(*eligibility_snapshot_fields),
        )
        self.stdout.write(f"  Exported {eligibility_snapshots.count()} eligibility snapshots")

        # Export program eligibility snapshots
        program_snapshots = ProgramEligibilitySnapshot.objects.filter(eligibility_snapshot_id__in=snapshot_ids)
        self._write_csv(
            os.path.join(output_dir, "program_eligibility_snapshots.csv"),
            program_eligibility_snapshot_fields,
            program_snapshots.values(*program_eligibility_snapshot_fields),
        )
        self.stdout.write(f"  Exported {program_snapshots.count()} program eligibility snapshots")

    def _export_flat(self, screens, output_dir):
        """Export data as a single denormalized CSV with one row per screen."""
        screen_ids = list(screens.values_list("id", flat=True))

        # Get field lists dynamically
        screen_fields = self._get_model_fields(Screen)
        household_member_fields = self._get_model_fields(HouseholdMember)
        income_stream_fields = self._get_model_fields(IncomeStream)
        expense_fields = self._get_model_fields(Expense)
        insurance_fields = self._get_model_fields(Insurance)
        eligibility_snapshot_fields = self._get_model_fields(EligibilitySnapshot)
        program_eligibility_snapshot_fields = self._get_model_fields(ProgramEligibilitySnapshot)

        # First pass: determine maximum counts for dynamic columns
        max_members = 0
        max_income_streams_per_member = defaultdict(int)
        max_expenses_per_screen = 0
        max_eligibility_snapshots = 0
        max_programs_per_snapshot = 0

        # Collect all related data
        all_members = {}
        all_income_streams = defaultdict(list)
        all_expenses = defaultdict(list)
        all_insurance = {}
        all_snapshots = defaultdict(list)
        all_program_snapshots = defaultdict(list)

        # Load household members
        for member in HouseholdMember.objects.filter(screen_id__in=screen_ids).order_by("id"):
            if member.screen_id not in all_members:
                all_members[member.screen_id] = []
            all_members[member.screen_id].append(member)

        # Load income streams
        for income in IncomeStream.objects.filter(screen_id__in=screen_ids).order_by("id"):
            all_income_streams[income.household_member_id].append(income)

        # Load expenses
        for expense in Expense.objects.filter(screen_id__in=screen_ids).order_by("id"):
            all_expenses[expense.screen_id].append(expense)

        # Load insurance
        member_ids = list(HouseholdMember.objects.filter(screen_id__in=screen_ids).values_list("id", flat=True))
        for ins in Insurance.objects.filter(household_member_id__in=member_ids):
            all_insurance[ins.household_member_id] = ins

        # Load eligibility snapshots
        for snapshot in EligibilitySnapshot.objects.filter(screen_id__in=screen_ids).order_by("id"):
            all_snapshots[snapshot.screen_id].append(snapshot)

        # Load program eligibility snapshots
        snapshot_ids = list(EligibilitySnapshot.objects.filter(screen_id__in=screen_ids).values_list("id", flat=True))
        for prog in ProgramEligibilitySnapshot.objects.filter(eligibility_snapshot_id__in=snapshot_ids).order_by("id"):
            all_program_snapshots[prog.eligibility_snapshot_id].append(prog)

        # Calculate maximums
        for screen_id in screen_ids:
            members = all_members.get(screen_id, [])
            max_members = max(max_members, len(members))

            for i, member in enumerate(members):
                income_count = len(all_income_streams.get(member.id, []))
                max_income_streams_per_member[i] = max(max_income_streams_per_member[i], income_count)

            max_expenses_per_screen = max(max_expenses_per_screen, len(all_expenses.get(screen_id, [])))

            snapshots = all_snapshots.get(screen_id, [])
            max_eligibility_snapshots = max(max_eligibility_snapshots, len(snapshots))

            for snapshot in snapshots:
                prog_count = len(all_program_snapshots.get(snapshot.id, []))
                max_programs_per_snapshot = max(max_programs_per_snapshot, prog_count)

        # Build dynamic headers
        headers = list(screen_fields)

        # Add household member columns
        member_base_fields = [f for f in household_member_fields if f not in ["id", "screen_id"]]
        insurance_base_fields = [f for f in insurance_fields if f not in ["id", "household_member_id"]]
        income_base_fields = [f for f in income_stream_fields if f not in ["id", "screen_id", "household_member_id"]]

        for m in range(max_members):
            prefix = f"member_{m + 1}_"
            headers.append(f"{prefix}id")
            for field in member_base_fields:
                headers.append(f"{prefix}{field}")
            # Insurance for this member
            for field in insurance_base_fields:
                headers.append(f"{prefix}insurance_{field}")
            # Income streams for this member
            for i in range(max_income_streams_per_member.get(m, 0)):
                income_prefix = f"{prefix}income_{i + 1}_"
                for field in income_base_fields:
                    headers.append(f"{income_prefix}{field}")

        # Add expense columns
        expense_base_fields = [f for f in expense_fields if f not in ["id", "screen_id", "household_member_id"]]
        for e in range(max_expenses_per_screen):
            prefix = f"expense_{e + 1}_"
            headers.append(f"{prefix}household_member_id")
            for field in expense_base_fields:
                headers.append(f"{prefix}{field}")

        # Add eligibility snapshot columns
        snapshot_base_fields = [f for f in eligibility_snapshot_fields if f not in ["id", "screen_id"]]
        program_base_fields = [
            f for f in program_eligibility_snapshot_fields if f not in ["id", "eligibility_snapshot_id"]
        ]

        for s in range(max_eligibility_snapshots):
            prefix = f"snapshot_{s + 1}_"
            headers.append(f"{prefix}id")
            for field in snapshot_base_fields:
                headers.append(f"{prefix}{field}")
            # Program snapshots
            for p in range(max_programs_per_snapshot):
                prog_prefix = f"{prefix}program_{p + 1}_"
                for field in program_base_fields:
                    headers.append(f"{prog_prefix}{field}")

        # Write the flat CSV
        output_path = os.path.join(output_dir, "screener_data_flat.csv")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for screen in screens:
                row = []

                # Screen fields
                for field in screen_fields:
                    row.append(getattr(screen, field, ""))

                # Household members
                members = all_members.get(screen.id, [])
                for m in range(max_members):
                    if m < len(members):
                        member = members[m]
                        row.append(member.id)
                        for field in member_base_fields:
                            row.append(getattr(member, field, ""))
                        # Insurance
                        ins = all_insurance.get(member.id)
                        for field in insurance_base_fields:
                            row.append(getattr(ins, field, "") if ins else "")
                        # Income streams
                        incomes = all_income_streams.get(member.id, [])
                        for i in range(max_income_streams_per_member.get(m, 0)):
                            if i < len(incomes):
                                income = incomes[i]
                                for field in income_base_fields:
                                    row.append(getattr(income, field, ""))
                            else:
                                for _ in income_base_fields:
                                    row.append("")
                    else:
                        # Empty member slot
                        row.append("")  # id
                        for _ in member_base_fields:
                            row.append("")
                        for _ in insurance_base_fields:
                            row.append("")
                        for i in range(max_income_streams_per_member.get(m, 0)):
                            for _ in income_base_fields:
                                row.append("")

                # Expenses
                expenses = all_expenses.get(screen.id, [])
                for e in range(max_expenses_per_screen):
                    if e < len(expenses):
                        expense = expenses[e]
                        row.append(expense.household_member_id or "")
                        for field in expense_base_fields:
                            row.append(getattr(expense, field, ""))
                    else:
                        row.append("")  # household_member_id
                        for _ in expense_base_fields:
                            row.append("")

                # Eligibility snapshots
                snapshots = all_snapshots.get(screen.id, [])
                for s in range(max_eligibility_snapshots):
                    if s < len(snapshots):
                        snapshot = snapshots[s]
                        row.append(snapshot.id)
                        for field in snapshot_base_fields:
                            row.append(getattr(snapshot, field, ""))
                        # Program snapshots
                        programs = all_program_snapshots.get(snapshot.id, [])
                        for p in range(max_programs_per_snapshot):
                            if p < len(programs):
                                prog = programs[p]
                                for field in program_base_fields:
                                    row.append(getattr(prog, field, ""))
                            else:
                                for _ in program_base_fields:
                                    row.append("")
                    else:
                        row.append("")  # id
                        for _ in snapshot_base_fields:
                            row.append("")
                        for p in range(max_programs_per_snapshot):
                            for _ in program_base_fields:
                                row.append("")

                writer.writerow(row)

        self.stdout.write(f"  Exported {screens.count()} screens to flat CSV")

    def _write_csv(self, filepath, headers, data):
        """Write a queryset to a CSV file."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
