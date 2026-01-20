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
- WhiteLabel (lookup table for white_label_id)
- DataDictionary (field descriptions for all exported tables)

Note: Test data (is_test=True or is_test_data=True) is always excluded from exports.

Usage:
    # Export CSV files
    python manage.py export_screener_data --output-dir /path/to/exports

    # Export with date range (end date is inclusive)
    python manage.py export_screener_data --start-date 2024-01-01 --end-date 2024-12-31 --output-dir /path/to/exports

    # Filter by white label
    python manage.py export_screener_data --output-dir /path/to/exports --white-label co nc

    # Dry run to see counts without exporting
    python manage.py export_screener_data --output-dir /path/to/exports --dry-run

    # Create compressed zip archive
    python manage.py export_screener_data --output-dir /path/to/exports --compress
"""

import csv
import os
import zipfile
from datetime import datetime, timedelta
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
    WhiteLabel,
)


class Command(BaseCommand):
    help = """
    Export screener data to CSV files for completed screeners within a date range.
    Test data is always excluded.
    """

    # Fields to exclude from export (test flags, internal fields, etc.)
    EXCLUDED_FIELDS = {"is_test", "is_test_data", "frontend_id", "user", "uid", "content"}
    CHUNK_SIZE = 5000

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
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show counts without exporting any data",
        )
        parser.add_argument(
            "--compress",
            action="store_true",
            help="Create a compressed .zip archive of the export",
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
                # Add one day to make end date inclusive (covers entire day)
                end_date = timezone.make_aware(datetime.strptime(options["end_date"], "%Y-%m-%d")) + timedelta(days=1)
            except ValueError:
                raise CommandError("Invalid end date format. Use YYYY-MM-DD.")

        output_dir = options["output_dir"]
        white_label = options.get("white_label")
        dry_run = options.get("dry_run", False)
        compress = options.get("compress", False)

        # Validate output directory (skip for dry run)
        if not dry_run and not os.path.exists(output_dir):
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
            screens = screens.filter(submission_date__lt=end_date)

        if white_label:
            screens = screens.filter(white_label__code__in=white_label)

        screens = screens.order_by("submission_date")

        screen_count = screens.count()
        if screen_count == 0:
            self.stdout.write(self.style.WARNING("No screens found matching the criteria."))
            return

        self.stdout.write(f"Found {screen_count} screens to export.")

        if dry_run:
            self._dry_run(screens)
            return

        self._export(screens, output_dir)

        if compress:
            self._compress_output(output_dir)

        self.stdout.write(self.style.SUCCESS(f"Export completed to {output_dir}"))

    def _export(self, screens, output_dir):
        """Export data as separate CSV files, one per table."""
        # Use subqueries instead of loading all IDs into memory
        screen_ids_subquery = screens.values("id")

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
        household_members = HouseholdMember.objects.filter(screen_id__in=screen_ids_subquery)
        member_ids_subquery = household_members.values("id")
        self._write_csv(
            os.path.join(output_dir, "household_members.csv"),
            household_member_fields,
            household_members.values(*household_member_fields),
        )
        self.stdout.write(f"  Exported {household_members.count()} household members")

        # Export income streams
        income_streams = IncomeStream.objects.filter(screen_id__in=screen_ids_subquery)
        self._write_csv(
            os.path.join(output_dir, "income_streams.csv"),
            income_stream_fields,
            income_streams.values(*income_stream_fields),
        )
        self.stdout.write(f"  Exported {income_streams.count()} income streams")

        # Export expenses
        expenses = Expense.objects.filter(screen_id__in=screen_ids_subquery)
        self._write_csv(
            os.path.join(output_dir, "expenses.csv"),
            expense_fields,
            expenses.values(*expense_fields),
        )
        self.stdout.write(f"  Exported {expenses.count()} expenses")

        # Export insurance (linked via household_member_id)
        insurance_records = Insurance.objects.filter(household_member_id__in=member_ids_subquery)
        self._write_csv(
            os.path.join(output_dir, "insurance.csv"),
            insurance_fields,
            insurance_records.values(*insurance_fields),
        )
        self.stdout.write(f"  Exported {insurance_records.count()} insurance records")

        # Export program eligibility (merged table with screen_id, only most recent snapshot per screen)
        self._export_program_eligibility(screen_ids_subquery, output_dir)

        # Export white label lookup table
        self._export_white_labels(screens, output_dir)

        # Export data dictionary
        self._export_data_dictionary(output_dir)

    def _export_program_eligibility(self, screen_ids_subquery, output_dir):
        """Export merged eligibility data with screen_id, only the most recent snapshot per screen."""
        # Get the most recent snapshot ID for each screen using subquery
        latest_snapshots = (
            EligibilitySnapshot.objects.filter(screen_id__in=screen_ids_subquery)
            .values("screen_id")
            .annotate(latest_id=Max("id"))
        )
        latest_snapshot_ids_subquery = latest_snapshots.values("latest_id")

        # Build a mapping of snapshot_id -> screen_id (this is bounded by number of screens, not records)
        snapshot_to_screen = dict(
            EligibilitySnapshot.objects.filter(id__in=latest_snapshot_ids_subquery).values_list("id", "screen_id")
        )

        # Get program eligibility fields, excluding the snapshot FK
        program_fields = self._get_model_fields(ProgramEligibilitySnapshot)
        program_fields = [f for f in program_fields if f != "eligibility_snapshot_id"]

        # Add screen_id as the first column
        headers = ["screen_id"] + program_fields

        # Get the program snapshots for the latest snapshots only
        program_snapshots = ProgramEligibilitySnapshot.objects.filter(
            eligibility_snapshot_id__in=latest_snapshot_ids_subquery
        ).order_by("eligibility_snapshot_id", "id")

        # Write the merged CSV with iterator for memory efficiency
        output_path = os.path.join(output_dir, "program_eligibility.csv")
        count = 0
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for row in program_snapshots.values("eligibility_snapshot_id", *program_fields).iterator(
                chunk_size=self.CHUNK_SIZE
            ):
                screen_id = snapshot_to_screen.get(row.pop("eligibility_snapshot_id"))
                row["screen_id"] = screen_id
                writer.writerow(row)
                count += 1

        self.stdout.write(f"  Exported {count} program eligibility records")

    def _export_white_labels(self, screens, output_dir):
        """Export white label lookup table for the exported screens."""
        white_label_ids = screens.values_list("white_label_id", flat=True).distinct()
        white_labels = WhiteLabel.objects.filter(id__in=white_label_ids)

        headers = ["id", "code", "name", "state_code"]
        self._write_csv(
            os.path.join(output_dir, "white_labels.csv"),
            headers,
            white_labels.values(*headers),
        )
        self.stdout.write(f"  Exported {white_labels.count()} white labels")

    def _export_data_dictionary(self, output_dir):
        """Export a data dictionary describing all exported fields."""
        dictionary, missing_descriptions = self._build_data_dictionary()

        # Warn about fields missing descriptions
        if missing_descriptions:
            self.stderr.write(
                self.style.WARNING(
                    f"\n  WARNING: {len(missing_descriptions)} field(s) missing descriptions in data dictionary:"
                )
            )
            for field_key in missing_descriptions:
                self.stderr.write(self.style.WARNING(f"    - {field_key}"))
            self.stderr.write("")

        output_path = os.path.join(output_dir, "data_dictionary.csv")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["table", "field", "type", "description"])
            writer.writeheader()
            for entry in dictionary:
                writer.writerow(entry)

        self.stdout.write(f"  Exported data dictionary ({len(dictionary)} fields)")

    def _build_data_dictionary(self):
        """Build data dictionary with field descriptions."""
        # Field descriptions for common/important fields
        descriptions = {
            # Screen fields - core
            "screen.id": "Unique identifier for the screen/household",
            "screen.uuid": "Public unique identifier (UUID format)",
            "screen.submission_date": "Date and time the screener was submitted",
            "screen.start_date": "Date and time the screener was started",
            "screen.completed": "Whether the screener was completed",
            "screen.agree_to_tos": "Whether user agreed to terms of service",
            "screen.is_13_or_older": "Whether user confirmed they are 13 or older",
            "screen.zipcode": "User's 5-digit ZIP code",
            "screen.county": "User's county name",
            "screen.household_size": "Total number of people in household",
            "screen.household_assets": "Total household assets in dollars",
            "screen.housing_situation": "Type of housing (e.g., rent, own, homeless)",
            "screen.referral_source": "How the user found the screener",
            "screen.referrer_code": "Referral tracking code from partner",
            "screen.request_language_code": "Language code requested by user",
            "screen.white_label_id": "Foreign key to white_labels table",
            "screen.external_id": "External system identifier from partner",
            "screen.energy_calculator": "Foreign key to energy calculator screen data (one-to-one)",
            "screen.path": "User type for screener flow (e.g., 'default', 'renter')",
            "screen.last_tax_filing_year": "Tax filing year field (currently unused)",
            "screen.last_email_request_date": "Timestamp when results email was last sent to user",
            "screen.alternate_path": "Secondary screener flow identifier (currently unused)",
            "screen.is_verified": "Whether user identity has been verified (currently unused)",
            # Screen fields - has_* benefits (current enrollment)
            "screen.has_benefits": "Whether user has any current benefits",
            "screen.has_tanf": "Has Temporary Assistance for Needy Families",
            "screen.has_wic": "Has Women, Infants, and Children program",
            "screen.has_snap": "Has Supplemental Nutrition Assistance Program (food stamps)",
            "screen.has_sunbucks": "Has Summer EBT/Sun Bucks program",
            "screen.has_lifeline": "Has Lifeline phone/internet discount",
            "screen.has_acp": "Has Affordable Connectivity Program",
            "screen.has_eitc": "Has Earned Income Tax Credit",
            "screen.has_coeitc": "Has Colorado Earned Income Tax Credit",
            "screen.has_il_eitc": "Has Illinois Earned Income Tax Credit",
            "screen.has_nslp": "Has National School Lunch Program",
            "screen.has_ctc": "Has Child Tax Credit",
            "screen.has_il_ctc": "Has Illinois Child Tax Credit",
            "screen.has_il_transit_reduced_fare": "Has Illinois reduced transit fare",
            "screen.has_il_bap": "Has Illinois Benefit Access Program",
            "screen.has_medicaid": "Has Medicaid health insurance",
            "screen.has_rtdlive": "Has RTD LiVE transit discount (Colorado)",
            "screen.has_ccap": "Has Colorado Child Care Assistance Program",
            "screen.has_mydenver": "Has MyDenver card",
            "screen.has_chp": "Has Child Health Plan Plus (CHP+)",
            "screen.has_ccb": "Has Colorado Child Care Benefit",
            "screen.has_ssi": "Has Supplemental Security Income",
            "screen.has_andcs": "Has Aid to Needy Disabled (Colorado State)",
            "screen.has_chs": "Has Colorado Health Subsidy",
            "screen.has_cpcr": "Has Colorado Property/Rent/Heat Credit",
            "screen.has_cdhcs": "Has Colorado Disabled Health Care Subsidy",
            "screen.has_dpp": "Has Denver Preschool Program",
            "screen.has_ede": "Has Emergency Dental Extraction",
            "screen.has_erc": "Has Energy Resource Center assistance",
            "screen.has_leap": "Has Low-Income Energy Assistance Program (Colorado)",
            "screen.has_il_liheap": "Has Illinois LIHEAP energy assistance",
            "screen.has_ma_heap": "Has Massachusetts HEAP energy assistance",
            "screen.has_nc_lieap": "Has North Carolina LIEAP energy assistance",
            "screen.has_oap": "Has Old Age Pension",
            "screen.has_nccip": "Has NC Care for Children and Infant Program",
            "screen.has_ncscca": "Has NC Senior Center for Creative Arts",
            "screen.has_coctc": "Has Colorado Child Tax Credit",
            "screen.has_upk": "Has Universal Pre-K",
            "screen.has_ssdi": "Has Social Security Disability Insurance",
            "screen.has_cowap": "Has Colorado Weatherization Assistance Program",
            "screen.has_ncwap": "Has North Carolina Weatherization Assistance Program",
            "screen.has_ubp": "Has Utility Bill Payment assistance",
            "screen.has_pell_grant": "Has Pell Grant",
            "screen.has_rag": "Has Refugee Assistance Grant",
            "screen.has_nfp": "Has Nurse-Family Partnership",
            "screen.has_fatc": "Has Food Assistance Tax Credit",
            "screen.has_section_8": "Has Section 8 housing voucher",
            "screen.has_csfp": "Has Commodity Supplemental Food Program",
            "screen.has_ccdf": "Has Child Care and Development Fund",
            "screen.has_aca": "Has Affordable Care Act marketplace insurance",
            "screen.has_ma_eaedc": "Has Massachusetts Emergency Aid to Elderly, Disabled and Children",
            "screen.has_ma_ssp": "Has Massachusetts State Supplement Program",
            "screen.has_ma_mbta": "Has Massachusetts MBTA reduced fare",
            "screen.has_ma_maeitc": "Has Massachusetts Earned Income Tax Credit",
            "screen.has_ma_macfc": "Has Massachusetts Child and Family Tax Credit",
            "screen.has_ma_homebridge": "Has Massachusetts HomeBridge program",
            "screen.has_ma_dhsp_afterschool": "Has Massachusetts DHSP Afterschool program",
            "screen.has_ma_door_to_door": "Has Massachusetts Door to Door transportation",
            "screen.has_head_start": "Has Head Start program",
            "screen.has_early_head_start": "Has Early Head Start program",
            "screen.has_co_andso": "Has Colorado AND-SO (Aid to Needy Disabled - State Only)",
            "screen.has_co_care": "Has Colorado CARE program",
            "screen.has_cfhc": "Has Children's Family Health Coverage",
            "screen.has_shitc": "Has State Health Insurance Tax Credit",
            "screen.has_employer_hi": "Has employer-provided health insurance",
            "screen.has_private_hi": "Has private health insurance",
            "screen.has_medicaid_hi": "Has Medicaid health insurance (duplicate flag)",
            "screen.has_medicare_hi": "Has Medicare health insurance",
            "screen.has_nc_medicare_savings": "Has NC Medicare Savings Program",
            "screen.has_chp_hi": "Has CHP+ health insurance",
            "screen.has_no_hi": "Has no health insurance",
            "screen.has_va": "Has Veterans Affairs benefits",
            "screen.has_project_cope": "Has Project COPE assistance",
            "screen.has_cesn_heap": "Has CESN HEAP energy assistance",
            # Screen fields - needs_* (self-reported needs)
            "screen.needs_food": "User indicated need for food assistance",
            "screen.needs_baby_supplies": "User indicated need for baby supplies",
            "screen.needs_housing_help": "User indicated need for housing assistance",
            "screen.needs_mental_health_help": "User indicated need for mental health services",
            "screen.needs_child_dev_help": "User indicated need for child development help",
            "screen.needs_funeral_help": "User indicated need for funeral assistance",
            "screen.needs_family_planning_help": "User indicated need for family planning services",
            "screen.needs_job_resources": "User indicated need for job resources",
            "screen.needs_dental_care": "User indicated need for dental care",
            "screen.needs_legal_services": "User indicated need for legal services",
            "screen.needs_college_savings": "User indicated need for college savings assistance",
            "screen.needs_veteran_services": "User indicated need for veteran services",
            # Screen fields - UTM tracking
            "screen.utm_id": "UTM tracking: unique identifier",
            "screen.utm_source": "UTM tracking: traffic source",
            "screen.utm_medium": "UTM tracking: marketing medium",
            "screen.utm_campaign": "UTM tracking: campaign name",
            "screen.utm_content": "UTM tracking: content identifier",
            "screen.utm_term": "UTM tracking: search term",
            # HouseholdMember fields
            "household_member.id": "Unique identifier for the household member",
            "household_member.screen_id": "Foreign key to screens table",
            "household_member.relationship": "Relationship to head of household",
            "household_member.age": "Age in years",
            "household_member.birth_year_month": "Birth year and month for precise age calculation",
            "household_member.student": "Whether member is a student",
            "household_member.student_full_time": "Whether member is a full-time student",
            "household_member.pregnant": "Whether member is pregnant",
            "household_member.unemployed": "Whether member is unemployed",
            "household_member.worked_in_last_18_mos": "Whether member worked in last 18 months",
            "household_member.visually_impaired": "Whether member is visually impaired",
            "household_member.disabled": "Whether member has a disability",
            "household_member.long_term_disability": "Whether member has long-term disability",
            "household_member.veteran": "Whether member is a veteran",
            "household_member.medicaid": "Whether member has Medicaid",
            "household_member.disability_medicaid": "Whether member has disability-based Medicaid",
            "household_member.has_income": "Whether member has income",
            "household_member.has_expenses": "Whether member has expenses",
            "household_member.is_care_worker": "Whether member is a care worker",
            "household_member.insurance": "Foreign key to insurance record",
            "household_member.energy_calculator": "Foreign key to energy calculator member data",
            # IncomeStream fields
            "income_stream.id": "Unique identifier for the income stream",
            "income_stream.screen_id": "Foreign key to screens table",
            "income_stream.household_member_id": "Foreign key to household_members table",
            "income_stream.category": "Income category grouping",
            "income_stream.type": "Type of income (wages, selfEmployment, sSI, etc.)",
            "income_stream.amount": "Income amount per frequency period",
            "income_stream.frequency": "Payment frequency (monthly, weekly, etc.)",
            "income_stream.hours_worked": "Hours worked per period (for hourly income)",
            # Expense fields
            "expense.id": "Unique identifier for the expense",
            "expense.screen_id": "Foreign key to screens table",
            "expense.household_member_id": "Foreign key to household_members table (nullable)",
            "expense.type": "Type of expense (rent, childcare, medical, etc.)",
            "expense.amount": "Expense amount per frequency period",
            "expense.frequency": "Payment frequency (monthly, weekly, etc.)",
            # Insurance fields
            "insurance.id": "Unique identifier for the insurance record",
            "insurance.household_member": "Foreign key to household_members table",
            "insurance.household_member_id": "Foreign key to household_members table",
            "insurance.dont_know": "User doesn't know their insurance status",
            "insurance.none": "User has no health insurance",
            "insurance.employer": "Has employer-provided insurance",
            "insurance.private": "Has private insurance",
            "insurance.chp": "Has Children's Health Program",
            "insurance.medicaid": "Has Medicaid",
            "insurance.medicare": "Has Medicare",
            "insurance.emergency_medicaid": "Has emergency Medicaid",
            "insurance.family_planning": "Has family planning coverage",
            "insurance.va": "Has Veterans Affairs coverage",
            "insurance.mass_health": "Has Massachusetts MassHealth (Medicaid/CHIP)",
            # ProgramEligibility fields
            "program_eligibility.screen_id": "Foreign key to screens table",
            "program_eligibility.id": "Unique identifier for the eligibility record",
            "program_eligibility.eligibility_snapshot_id": "Foreign key to eligibility snapshot (internal)",
            "program_eligibility.name": "Full program name",
            "program_eligibility.name_abbreviated": "Program abbreviation/code",
            "program_eligibility.eligible": "Whether user is eligible for this program",
            "program_eligibility.estimated_value": "Estimated annual benefit value in dollars",
            "program_eligibility.value_type": "Type of value (monthly, annual, one-time)",
            "program_eligibility.new": "Whether this is a new benefit for the user",
            "program_eligibility.estimated_delivery_time": "Estimated time to receive benefit",
            "program_eligibility.estimated_application_time": "Estimated time to complete application",
            "program_eligibility.failed_tests": "JSON array of eligibility tests that failed",
            "program_eligibility.passed_tests": "JSON array of eligibility tests that passed",
            # WhiteLabel fields
            "white_label.id": "Unique identifier for the white label",
            "white_label.code": "Short code identifier (e.g., 'co', 'nc')",
            "white_label.name": "Display name of the white label instance",
            "white_label.state_code": "Two-letter state code (e.g., 'CO', 'NC')",
            "white_label.cms_method": "CRM integration type (e.g., 'co_hubspot', 'nc_hubspot')",
        }

        dictionary = []
        missing_descriptions = []
        models_info = [
            ("screen", Screen),
            ("household_member", HouseholdMember),
            ("income_stream", IncomeStream),
            ("expense", Expense),
            ("insurance", Insurance),
            ("program_eligibility", ProgramEligibilitySnapshot),
            ("white_label", WhiteLabel),
        ]

        for table_name, model in models_info:
            fields = self._get_model_fields(model)
            for field_name in fields:
                key = f"{table_name}.{field_name}"
                field_type = self._get_field_type(model, field_name)
                description = descriptions.get(key, "")

                if not description:
                    missing_descriptions.append(key)

                dictionary.append(
                    {
                        "table": table_name,
                        "field": field_name,
                        "type": field_type,
                        "description": description,
                    }
                )

        return dictionary, missing_descriptions

    def _get_field_type(self, model, field_name):
        """Get a human-readable type for a model field."""
        # Handle _id suffix for foreign keys
        lookup_name = field_name[:-3] if field_name.endswith("_id") else field_name

        try:
            field = model._meta.get_field(lookup_name)
            type_name = field.get_internal_type()
            type_map = {
                "AutoField": "integer",
                "BigAutoField": "integer",
                "IntegerField": "integer",
                "PositiveIntegerField": "integer",
                "SmallIntegerField": "integer",
                "CharField": "string",
                "TextField": "string",
                "BooleanField": "boolean",
                "NullBooleanField": "boolean",
                "DateField": "date",
                "DateTimeField": "datetime",
                "DecimalField": "decimal",
                "FloatField": "float",
                "ForeignKey": "integer (foreign key)",
                "OneToOneField": "integer (foreign key)",
                "JSONField": "json",
                "UUIDField": "uuid",
            }
            return type_map.get(type_name, type_name.lower())
        except Exception:
            return "unknown"

    def _dry_run(self, screens):
        """Show counts without exporting any data."""
        # Use subqueries instead of loading all IDs into memory
        screen_ids_subquery = screens.values("id")

        self.stdout.write("\nDry run - no files will be created:\n")
        self.stdout.write(f"  Screens: {screens.count()}")

        household_members = HouseholdMember.objects.filter(screen_id__in=screen_ids_subquery)
        member_ids_subquery = household_members.values("id")
        self.stdout.write(f"  Household members: {household_members.count()}")

        self.stdout.write(f"  Income streams: {IncomeStream.objects.filter(screen_id__in=screen_ids_subquery).count()}")
        self.stdout.write(f"  Expenses: {Expense.objects.filter(screen_id__in=screen_ids_subquery).count()}")
        self.stdout.write(
            f"  Insurance records: {Insurance.objects.filter(household_member_id__in=member_ids_subquery).count()}"
        )

        latest_snapshot_ids_subquery = (
            EligibilitySnapshot.objects.filter(screen_id__in=screen_ids_subquery)
            .values("screen_id")
            .annotate(latest_id=Max("id"))
            .values("latest_id")
        )
        program_count = ProgramEligibilitySnapshot.objects.filter(
            eligibility_snapshot_id__in=latest_snapshot_ids_subquery
        ).count()
        self.stdout.write(f"  Program eligibility records: {program_count}")

        white_label_count = screens.values_list("white_label_id", flat=True).distinct().count()
        self.stdout.write(f"  White labels: {white_label_count}")

    def _compress_output(self, output_dir):
        """Create a zip archive of all CSV files in the output directory."""
        zip_path = f"{output_dir}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(output_dir):
                if filename.endswith(".csv"):
                    file_path = os.path.join(output_dir, filename)
                    zf.write(file_path, filename)

        self.stdout.write(f"  Created compressed archive: {zip_path}")

    def _write_csv(self, filepath, headers, queryset):
        """Write a queryset to a CSV file using iterator for memory efficiency."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in queryset.iterator(chunk_size=self.CHUNK_SIZE):
                writer.writerow(row)
