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
from screener.serializers import ScreenSerializer
from validations.models import Validation


class UpdateValidationsCommandTest(TestCase):
    """Tests for the update_validations management command"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        cls.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.program = Program.objects.new_program(white_label="co", name_abbreviated="snap")

    def setUp(self):
        """Set up for each test"""
        self.out = StringIO()
        self.err = StringIO()

        # Create a test screen using ScreenSerializer (like import_validations does)
        screen_data = {
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
        }
        serializer = ScreenSerializer(data=screen_data)
        serializer.is_valid(raise_exception=True)
        self.screen = serializer.save()

        self.validation = Validation.objects.create(
            screen=self.screen,
            program_name="snap",
            eligible=True,
            value=Decimal("250.00"),
            notes="Original notes",
        )

    def _create_test_file(self, data):
        """Helper to create a temporary JSON file with update data"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        json.dump(data, temp_file)
        temp_file.close()
        return temp_file.name

    def test_update_eligible_field(self):
        """Test updating the eligible field of a validation"""
        update_data = {
            "description": "Update SNAP eligibility",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "eligible": False,
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify the validation was updated
            self.validation.refresh_from_db()
            self.assertFalse(self.validation.eligible)

            output = self.out.getvalue()
            self.assertIn("eligible: True → False", output)

        finally:
            Path(file_path).unlink()

    def test_update_value_field(self):
        """Test updating the value field of a validation"""
        update_data = {
            "description": "Update SNAP value",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "value": 300.00,
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify the validation was updated
            self.validation.refresh_from_db()
            self.assertEqual(self.validation.value, Decimal("300.00"))

            output = self.out.getvalue()
            self.assertIn("value:", output)

        finally:
            Path(file_path).unlink()

    def test_update_notes_field(self):
        """Test updating the notes field of a validation"""
        update_data = {
            "description": "Update SNAP notes",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "notes": "Updated notes",
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify the validation was updated
            self.validation.refresh_from_db()
            self.assertEqual(self.validation.notes, "Updated notes")

            output = self.out.getvalue()
            self.assertIn("notes:", output)

        finally:
            Path(file_path).unlink()

    def test_update_multiple_fields(self):
        """Test updating multiple fields at once"""
        update_data = {
            "description": "Update multiple fields",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "eligible": False,
                    "value": 0,
                    "notes": "No longer eligible",
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            # Verify all fields were updated
            self.validation.refresh_from_db()
            self.assertFalse(self.validation.eligible)
            self.assertEqual(self.validation.value, Decimal("0"))
            self.assertEqual(self.validation.notes, "No longer eligible")

        finally:
            Path(file_path).unlink()

    def test_dry_run_does_not_modify_database(self):
        """Test that --dry-run shows changes but doesn't modify the database"""
        original_eligible = self.validation.eligible
        original_value = self.validation.value

        update_data = {
            "description": "Dry run test",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "eligible": False,
                    "value": 0,
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, "--dry-run", stdout=self.out, stderr=self.err)

            # Verify the validation was NOT updated
            self.validation.refresh_from_db()
            self.assertEqual(self.validation.eligible, original_eligible)
            self.assertEqual(self.validation.value, original_value)

            output = self.out.getvalue()
            self.assertIn("Dry run - no changes made", output)
            self.assertIn("DRY RUN SUMMARY", output)

        finally:
            Path(file_path).unlink()

    def test_nonexistent_screen_fails(self):
        """Test that referencing a non-existent screen fails"""
        update_data = {
            "description": "Invalid screen test",
            "updates": [
                {
                    "screen_uuid": "00000000-0000-0000-0000-000000000000",
                    "program_name": "snap",
                    "eligible": False,
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            self.assertIn("does not exist", str(cm.exception))

        finally:
            Path(file_path).unlink()

    def test_nonexistent_validation_fails(self):
        """Test that referencing a non-existent validation fails"""
        update_data = {
            "description": "Invalid validation test",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "nonexistent_program",
                    "eligible": False,
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            self.assertIn("does not exist", str(cm.exception))

        finally:
            Path(file_path).unlink()

    def test_missing_description_fails_validation(self):
        """Test that missing description fails schema validation"""
        update_data = {
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "eligible": True,
                }
            ]
        }

        file_path = self._create_test_file(update_data)

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            self.assertIn("validation failed", str(cm.exception))

        finally:
            Path(file_path).unlink()

    def test_empty_updates_fails_validation(self):
        """Test that empty updates array fails schema validation"""
        update_data = {"description": "Empty updates", "updates": []}

        file_path = self._create_test_file(update_data)

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            self.assertIn("validation failed", str(cm.exception))

        finally:
            Path(file_path).unlink()

    def test_update_without_any_fields_fails(self):
        """Test that an update without eligible, value, or notes fails"""
        update_data = {
            "description": "No fields to update",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    # No eligible, value, or notes
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            self.assertIn("validation failed", str(cm.exception))

        finally:
            Path(file_path).unlink()

    def test_invalid_json_file(self):
        """Test that invalid JSON file raises error"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        temp_file.write("{ invalid json }")
        temp_file.close()

        try:
            with self.assertRaises(CommandError) as cm:
                call_command("update_validations", temp_file.name, stdout=self.out, stderr=self.err)

            self.assertIn("Invalid JSON", str(cm.exception))

        finally:
            Path(temp_file.name).unlink()

    def test_file_not_found(self):
        """Test that missing file raises error"""
        with self.assertRaises(CommandError) as cm:
            call_command("update_validations", "/nonexistent/file.json")

        self.assertIn("File not found", str(cm.exception))

    def test_output_summary(self):
        """Test that command outputs a comprehensive summary"""
        update_data = {
            "description": "Test update summary",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "eligible": False,
                    "value": 0,
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            output = self.out.getvalue()

            # Verify summary components
            self.assertIn("UPDATE SUMMARY", output)
            self.assertIn("Description:", output)
            self.assertIn("Total updates processed:", output)
            self.assertIn("Validations modified:", output)
            self.assertIn("Programs affected:", output)
            self.assertIn("snap", output)

        finally:
            Path(file_path).unlink()

    def test_no_change_when_values_same(self):
        """Test that no changes are recorded when values are the same"""
        update_data = {
            "description": "No actual changes",
            "updates": [
                {
                    "screen_uuid": str(self.screen.uuid),
                    "program_name": "snap",
                    "eligible": True,  # Same as current
                    "value": 250.00,  # Same as current
                }
            ],
        }

        file_path = self._create_test_file(update_data)

        try:
            call_command("update_validations", file_path, stdout=self.out, stderr=self.err)

            output = self.out.getvalue()
            self.assertIn("Validations modified: 0", output)

        finally:
            Path(file_path).unlink()
