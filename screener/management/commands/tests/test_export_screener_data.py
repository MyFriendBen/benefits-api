"""
Unit tests for export_screener_data management command.
"""

import csv
import os
import tempfile
from datetime import datetime
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from screener.models import (
    CurrentBenefit,
    Expense,
    HouseholdMember,
    IncomeStream,
    Screen,
    WhiteLabel,
)
from screener.tests.helpers import seed_program


def make_screen(white_label: WhiteLabel, **kwargs) -> Screen:
    """Create a valid exportable screen (completed, agreed to ToS, not test data)."""
    defaults = {
        "white_label": white_label,
        "zipcode": "80203",
        "county": "Denver",
        "household_size": 1,
        "agree_to_tos": True,
        "completed": True,
        "is_test": False,
        "is_test_data": False,
        "submission_date": timezone.make_aware(datetime(2024, 6, 1)),
    }
    defaults.update(kwargs)
    return Screen.objects.create(**defaults)


class ExportScreenerDataCommandTest(TestCase):
    """Tests for the export_screener_data management command."""

    def setUp(self):
        self.out = StringIO()
        self.err = StringIO()
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def _call(self, output_dir: str, **kwargs) -> None:
        call_command(
            "export_screener_data",
            output_dir=output_dir,
            stdout=self.out,
            stderr=self.err,
            **kwargs,
        )

    def _read_csv(self, output_dir: str, filename: str) -> list[dict]:
        path = os.path.join(output_dir, filename)
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    # ------------------------------------------------------------------
    # File creation
    # ------------------------------------------------------------------

    def test_creates_all_expected_csv_files(self):
        make_screen(self.white_label)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            expected_files = [
                "screens.csv",
                "household_members.csv",
                "income_streams.csv",
                "expenses.csv",
                "insurance.csv",
                "current_benefits.csv",
                "program_eligibility.csv",
                "white_labels.csv",
                "data_dictionary.csv",
            ]
            for filename in expected_files:
                self.assertTrue(
                    os.path.exists(os.path.join(output_dir, filename)),
                    f"Expected {filename} to be created",
                )

    # ------------------------------------------------------------------
    # Row counts
    # ------------------------------------------------------------------

    def test_exports_correct_number_of_screens(self):
        make_screen(self.white_label)
        make_screen(self.white_label)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 2)

    def test_exports_household_members(self):
        screen = make_screen(self.white_label)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=30)
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=28)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "household_members.csv")
            self.assertEqual(len(rows), 2)

    def test_exports_income_streams(self):
        screen = make_screen(self.white_label)
        member = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=30)
        IncomeStream.objects.create(
            screen=screen, household_member=member, type="wages", amount=2000, frequency="monthly"
        )
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "income_streams.csv")
            self.assertEqual(len(rows), 1)

    def test_exports_expenses(self):
        screen = make_screen(self.white_label)
        Expense.objects.create(screen=screen, type="rent", amount=1000, frequency="monthly")
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "expenses.csv")
            self.assertEqual(len(rows), 1)

    def test_exports_current_benefits(self):
        screen = make_screen(self.white_label)
        seed_program(self.white_label, "snap")
        from programs.models import Program

        program = Program.objects.get(name_abbreviated="snap")
        CurrentBenefit.objects.create(screen=screen, program=program)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "current_benefits.csv")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["screen_id"], str(screen.id))
            self.assertEqual(rows[0]["program_id"], str(program.id))

    def test_exports_white_labels_for_exported_screens_only(self):
        other_wl = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")
        make_screen(self.white_label)
        # Screen on other_wl is test data — should not appear
        make_screen(other_wl, is_test=True)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "white_labels.csv")
            codes = [r["code"] for r in rows]
            self.assertIn("test", codes)
            self.assertNotIn("other", codes)

    # ------------------------------------------------------------------
    # Test data exclusion
    # ------------------------------------------------------------------

    def test_excludes_is_test_screens(self):
        make_screen(self.white_label, is_test=True)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            # Command exits early with a warning when no exportable screens are found
            self.assertIn("No screens found", self.out.getvalue())
            self.assertFalse(os.path.exists(os.path.join(output_dir, "screens.csv")))

    def test_excludes_is_test_data_screens(self):
        make_screen(self.white_label, is_test_data=True)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            self.assertIn("No screens found", self.out.getvalue())
            self.assertFalse(os.path.exists(os.path.join(output_dir, "screens.csv")))

    def test_excludes_screens_without_agree_to_tos(self):
        make_screen(self.white_label, agree_to_tos=False)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            self.assertIn("No screens found", self.out.getvalue())
            self.assertFalse(os.path.exists(os.path.join(output_dir, "screens.csv")))

    # ------------------------------------------------------------------
    # Incomplete screens
    # ------------------------------------------------------------------

    def test_excludes_incomplete_screens_by_default(self):
        make_screen(self.white_label, completed=False)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            self.assertIn("No screens found", self.out.getvalue())
            self.assertFalse(os.path.exists(os.path.join(output_dir, "screens.csv")))

    def test_includes_incomplete_screens_with_flag(self):
        make_screen(self.white_label, completed=False)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, include_incomplete=True)
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 1)

    # ------------------------------------------------------------------
    # Date range filtering
    # ------------------------------------------------------------------

    def test_filters_by_start_date(self):
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 1, 15)))
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 6, 1)))
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, start_date="2024-06-01")
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 1)

    def test_filters_by_end_date(self):
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 1, 15)))
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 6, 1)))
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, end_date="2024-03-01")
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 1)

    def test_filters_by_date_range(self):
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 1, 1)))
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 6, 15)))
        make_screen(self.white_label, submission_date=timezone.make_aware(datetime(2024, 12, 31)))
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, start_date="2024-06-01", end_date="2024-07-01")
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 1)

    # ------------------------------------------------------------------
    # White label filtering
    # ------------------------------------------------------------------

    def test_filters_by_white_label(self):
        other_wl = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")
        make_screen(self.white_label)
        make_screen(other_wl)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, white_label=["test"])
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 1)

    def test_filters_by_multiple_white_labels(self):
        wl2 = WhiteLabel.objects.create(name="State Two", code="st2", state_code="S2")
        wl3 = WhiteLabel.objects.create(name="State Three", code="st3", state_code="S3")
        make_screen(self.white_label)
        make_screen(wl2)
        make_screen(wl3)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, white_label=["test", "st2"])
            rows = self._read_csv(output_dir, "screens.csv")
            self.assertEqual(len(rows), 2)

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def test_dry_run_creates_no_files(self):
        make_screen(self.white_label)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, dry_run=True)
            self.assertEqual(os.listdir(output_dir), [])

    def test_dry_run_outputs_counts(self):
        make_screen(self.white_label)
        HouseholdMember.objects.create(screen=Screen.objects.first(), relationship="headOfHousehold", age=30)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir, dry_run=True)
        output = self.out.getvalue()
        self.assertIn("Screens:", output)
        self.assertIn("Household members:", output)
        self.assertIn("Current benefit records:", output)

    # ------------------------------------------------------------------
    # Data dictionary
    # ------------------------------------------------------------------

    def test_data_dictionary_includes_current_benefit_fields(self):
        make_screen(self.white_label)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            rows = self._read_csv(output_dir, "data_dictionary.csv")
            tables = {r["table"] for r in rows}
            self.assertIn("current_benefit", tables)

    def test_data_dictionary_has_no_missing_descriptions(self):
        make_screen(self.white_label)
        with tempfile.TemporaryDirectory() as output_dir:
            self._call(output_dir)
            err_output = self.err.getvalue()
            self.assertNotIn("missing descriptions", err_output)
