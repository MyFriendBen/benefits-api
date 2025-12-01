import json
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from programs.models import Program
from screener.models import Screen, WhiteLabel
from validations.models import Validation


class ImportValidationsCommandTest(TestCase):
    """Tests for the import_validations management command"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        # Create white labels
        cls.co_white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.tx_white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

        # Create test programs using the manager method
        cls.snap_program = Program.objects.new_program(white_label="co", name_abbreviated="snap")
        cls.lifeline_program = Program.objects.new_program(white_label="co", name_abbreviated="lifeline")
        cls.tx_aca_program = Program.objects.new_program(white_label="tx", name_abbreviated="tx_aca")

    def setUp(self):
        """Set up for each test"""
        self.out = StringIO()
        self.err = StringIO()

    def _create_test_case_file(self, test_cases):
        """Helper to create a temporary JSON file with test cases"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(test_cases, temp_file)
        temp_file.close()
        return temp_file.name

    def test_import_single_test_case_success(self):
        """Test importing a single valid test case"""
        test_case = {
            "notes": "CO SNAP - Test household",
            "household": {
                "white_label": "co",
                "is_test": True,
                "agree_to_tos": True,
                "is_13_or_older": True,
                "zipcode": "80202",
                "county": "Denver County",
                "household_size": 2,
                "household_assets": 1000.00,
                "household_members": [
                    {
                        "relationship": "headOfHousehold",
                        "age": 30,
                        "has_income": True,
                        "income_streams": [{"type": "wages", "amount": 1500.00, "frequency": "monthly"}],
                        "insurance": {"none": True},
                    }
                ],
                "expenses": [],
            },
            "expected_results": {
                "program_name": "snap",
                "eligible": True,
                "value": 250.00,
            },
        }

        file_path = self._create_test_case_file([test_case])

        try:
            call_command("import_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify screen was created
            self.assertEqual(Screen.objects.filter(is_test_data=True).count(), 1)
            screen = Screen.objects.filter(is_test_data=True).first()
            self.assertEqual(screen.white_label.code, "co")
            self.assertTrue(screen.is_test)
            self.assertTrue(screen.is_test_data)

            # Verify validation was created
            self.assertEqual(Validation.objects.count(), 1)
            validation = Validation.objects.first()
            self.assertEqual(validation.screen, screen)
            self.assertEqual(validation.program_name, "snap")
            self.assertTrue(validation.eligible)
            self.assertEqual(validation.value, Decimal("250.00"))
            self.assertEqual(validation.notes, "CO SNAP - Test household")

            # Verify screen is frozen
            self.assertTrue(screen.frozen)

        finally:
            Path(file_path).unlink()

    def test_import_multiple_test_cases(self):
        """Test importing multiple test cases"""
        test_cases = [
            {
                "notes": "CO SNAP - Case 1",
                "household": {
                    "white_label": "co",
                    "is_test": True,
                    "agree_to_tos": True,
                    "is_13_or_older": True,
                    "zipcode": "80202",
                    "household_size": 1,
                    "household_members": [
                        {
                            "relationship": "headOfHousehold",
                            "age": 25,
                            "has_income": False,
                            "income_streams": [],
                            "insurance": {"none": True},
                        }
                    ],
                    "expenses": [],
                },
                "expected_results": {"program_name": "snap", "eligible": True, "value": 200.00},
            },
            {
                "notes": "TX ACA - Case 2",
                "household": {
                    "white_label": "tx",
                    "is_test": True,
                    "agree_to_tos": True,
                    "is_13_or_older": True,
                    "zipcode": "78701",
                    "household_size": 1,
                    "household_members": [
                        {
                            "relationship": "headOfHousehold",
                            "age": 40,
                            "has_income": True,
                            "income_streams": [{"type": "wages", "amount": 5000.00, "frequency": "monthly"}],
                            "insurance": {"none": False, "employer": True},
                        }
                    ],
                    "expenses": [],
                },
                "expected_results": {"program_name": "tx_aca", "eligible": False, "value": 0},
            },
        ]

        file_path = self._create_test_case_file(test_cases)

        try:
            call_command("import_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify both screens were created
            self.assertEqual(Screen.objects.filter(is_test_data=True).count(), 2)

            # Verify both validations were created
            self.assertEqual(Validation.objects.count(), 2)

        finally:
            Path(file_path).unlink()

    def test_import_multiple_validations_per_screen(self):
        """Test importing a test case with multiple expected results"""
        test_case = {
            "notes": "Multiple programs test",
            "household": {
                "white_label": "co",
                "is_test": True,
                "agree_to_tos": True,
                "is_13_or_older": True,
                "zipcode": "80202",
                "household_size": 1,
                "household_members": [
                    {
                        "relationship": "headOfHousehold",
                        "age": 30,
                        "has_income": False,
                        "income_streams": [],
                        "insurance": {"none": True},
                    }
                ],
                "expenses": [],
            },
            "expected_results": [
                {"program_name": "snap", "eligible": True, "value": 250.00},
                {"program_name": "lifeline", "eligible": False, "value": 0},
            ],
        }

        file_path = self._create_test_case_file([test_case])

        try:
            call_command("import_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify one screen was created
            self.assertEqual(Screen.objects.filter(is_test_data=True).count(), 1)

            # Verify two validations were created
            self.assertEqual(Validation.objects.count(), 2)

            screen = Screen.objects.filter(is_test_data=True).first()
            self.assertEqual(screen.validations.count(), 2)

        finally:
            Path(file_path).unlink()

    def test_nonexistent_program_fails(self):
        """Test that referencing a non-existent program fails validation"""
        test_case = {
            "notes": "Invalid program test",
            "household": {
                "white_label": "co",
                "is_test": True,
                "agree_to_tos": True,
                "is_13_or_older": True,
                "zipcode": "80202",
                "household_size": 1,
                "household_members": [
                    {
                        "relationship": "headOfHousehold",
                        "age": 30,
                        "has_income": False,
                        "income_streams": [],
                        "insurance": {"none": True},
                    }
                ],
                "expenses": [],
            },
            "expected_results": {
                "program_name": "nonexistent_program",
                "eligible": True,
                "value": 100.00,
            },
        }

        file_path = self._create_test_case_file([test_case])

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("import_validations", file_path, stdout=self.out, stderr=self.err)

            self.assertIn("nonexistent_program", str(cm.exception))
            self.assertIn("does not exist", str(cm.exception))

        finally:
            Path(file_path).unlink()

    def test_invalid_json_file(self):
        """Test that invalid JSON file raises error"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        temp_file.write("{ invalid json }")
        temp_file.close()

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("import_validations", temp_file.name, stdout=self.out, stderr=self.err)

            self.assertIn("Invalid JSON", str(cm.exception))

        finally:
            Path(temp_file.name).unlink()

    def test_file_not_found(self):
        """Test that missing file raises error"""
        with self.assertRaises(CommandError) as cm:
            call_command("import_validations", "/nonexistent/file.json")

        self.assertIn("File not found", str(cm.exception))

    def test_output_summary(self):
        """Test that command outputs a comprehensive summary"""
        test_cases = [
            {
                "notes": "Success case",
                "household": {
                    "white_label": "co",
                    "is_test": True,
                    "agree_to_tos": True,
                    "is_13_or_older": True,
                    "zipcode": "80202",
                    "household_size": 1,
                    "household_members": [
                        {
                            "relationship": "headOfHousehold",
                            "age": 30,
                            "has_income": False,
                            "income_streams": [],
                            "insurance": {"none": True},
                        }
                    ],
                    "expenses": [],
                },
                "expected_results": {"program_name": "snap", "eligible": True, "value": 250.00},
            }
        ]

        file_path = self._create_test_case_file(test_cases)

        try:
            call_command("import_validations", file_path, stdout=self.out, stderr=self.err)

            output = self.out.getvalue()

            # Verify summary components
            self.assertIn("IMPORT SUMMARY", output)
            self.assertIn("Total test cases:", output)
            self.assertIn("test cases imported successfully", output)
            self.assertIn("Screens created:", output)
            self.assertIn("Screen UUID:", output)
            self.assertIn("Screen URL:", output)
            self.assertIn("http://localhost:3000/co/", output)
            self.assertIn("Success case", output)

        finally:
            Path(file_path).unlink()
