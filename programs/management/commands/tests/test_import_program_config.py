import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase

from programs.models import Program, ProgramCategory
from screener.models import WhiteLabel


class ImportProgramConfigTestCase(TransactionTestCase):
    """
    Tests for import_program_config management command.

    Uses TransactionTestCase to properly test transaction rollback behavior.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Create white label for testing
        self.white_label = WhiteLabel.objects.create(
            code="test_wl",
            name="Test White Label",
        )

        # Create a minimal valid config
        self.base_config = {
            "white_label": {"code": "test_wl"},
            "program_category": {
                "external_name": "test_category",
                "icon": "test_icon",
                "name": "Test Category",
                "description": "Test category description",
            },
            "program": {
                "name_abbreviated": "TEST_PROGRAM",
                "external_name": "test_program",
                "name": "Test Program Name",
                "description": "Test program description",
                "active": True,
            },
        }

        # Mock Google Translate to avoid slow API calls and missing credentials in CI
        self.translate_patcher = patch("integrations.clients.google_translate.Translate")
        mock_translate_class = self.translate_patcher.start()

        # Create a mock instance with bulk_translate method
        mock_instance = mock_translate_class.return_value
        mock_instance.bulk_translate.side_effect = lambda langs, texts: {
            text: {lang: f"{text} (translated to {lang})" for lang in langs} for text in texts
        }

    def tearDown(self):
        """Clean up mocks."""
        self.translate_patcher.stop()

    def _create_temp_config(self, config: dict) -> str:
        """Create a temporary JSON config file and return its path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            return f.name

    def test_create_new_program_shows_created_message(self):
        """Test that creating a new program shows 'created' in success message."""
        config_file = self._create_temp_config(self.base_config)
        out = StringIO()

        try:
            call_command("import_program_config", config_file, stdout=out)
            output = out.getvalue()

            # Verify program was created
            self.assertTrue(Program.objects.filter(name_abbreviated="TEST_PROGRAM").exists())

            # Verify success message says "created" (not "recreated")
            self.assertIn("Successfully created program: TEST_PROGRAM", output)
            self.assertNotIn("Successfully recreated program", output)
        finally:
            Path(config_file).unlink()

    def test_override_existing_program_shows_recreated_message(self):
        """Test that overriding an existing program shows 'recreated' in success message."""
        # First, create a program
        config_file = self._create_temp_config(self.base_config)
        call_command("import_program_config", config_file, stdout=StringIO())

        # Verify program exists
        original_program = Program.objects.get(name_abbreviated="TEST_PROGRAM")
        original_id = original_program.id

        # Now override it
        out = StringIO()
        call_command("import_program_config", config_file, "--override", stdout=out)
        output = out.getvalue()

        # Verify program was recreated (new ID)
        new_program = Program.objects.get(name_abbreviated="TEST_PROGRAM")
        self.assertNotEqual(original_id, new_program.id)

        # Verify success message says "recreated" (not "created")
        self.assertIn("Successfully recreated program: TEST_PROGRAM", output)
        self.assertNotIn("Successfully created program: TEST_PROGRAM", output)

        Path(config_file).unlink()

    def test_failed_override_rolls_back_deletion(self):
        """
        Test that if import fails after deletion in override mode,
        the deletion is rolled back and the original program is preserved.

        Uses mocking to force a failure during the transaction after deletion.
        """
        # First, create a valid program (without mocking)
        config_file = self._create_temp_config(self.base_config)
        call_command("import_program_config", config_file, stdout=StringIO())

        # Get the original program
        original_program = Program.objects.get(name_abbreviated="TEST_PROGRAM")
        original_id = original_program.id

        # Now use mock to force failure during override
        with patch("programs.models.Program.objects.new_program") as mock_new_program:
            # Mock new_program to raise an exception (simulating a failure during import)
            mock_new_program.side_effect = RuntimeError("Simulated import failure")

            # Attempt to override with the same config (should fail due to mock)
            with self.assertRaises(RuntimeError):
                call_command("import_program_config", config_file, "--override", stdout=StringIO())

        # Verify original program still exists (deletion was rolled back)
        self.assertTrue(Program.objects.filter(id=original_id).exists())
        program = Program.objects.get(id=original_id)
        self.assertEqual(program.name_abbreviated, "TEST_PROGRAM")

        # Clean up
        Path(config_file).unlink()

    def test_override_flag_without_existing_program(self):
        """Test that --override flag works correctly when program doesn't exist yet."""
        config_file = self._create_temp_config(self.base_config)
        out = StringIO()

        # Call with --override even though program doesn't exist
        call_command("import_program_config", config_file, "--override", stdout=out)
        output = out.getvalue()

        # Verify program was created
        self.assertTrue(Program.objects.filter(name_abbreviated="TEST_PROGRAM").exists())

        # Verify success message says "created" (not "recreated")
        # because there was nothing to override
        self.assertIn("Successfully created program: TEST_PROGRAM", output)
        self.assertNotIn("Successfully recreated program", output)

        Path(config_file).unlink()

    def test_existing_program_without_override_flag_skips_import(self):
        """Test that existing program without --override flag skips import."""
        # First, create a program
        config_file = self._create_temp_config(self.base_config)
        call_command("import_program_config", config_file, stdout=StringIO())

        # Get the original program
        original_program = Program.objects.get(name_abbreviated="TEST_PROGRAM")
        original_id = original_program.id

        # Try to import again without --override
        out = StringIO()
        call_command("import_program_config", config_file, stdout=out)
        output = out.getvalue()

        # Verify warning message
        self.assertIn("already exists", output)
        self.assertIn("Use --override", output)

        # Verify original program unchanged
        program = Program.objects.get(name_abbreviated="TEST_PROGRAM")
        self.assertEqual(program.id, original_id)

        Path(config_file).unlink()

    def test_transaction_rollback_on_category_creation_error(self):
        """
        Test that transaction rollback works when category creation fails
        during override operation.
        """
        # Create initial program
        config_file = self._create_temp_config(self.base_config)
        call_command("import_program_config", config_file, stdout=StringIO())

        original_program = Program.objects.get(name_abbreviated="TEST_PROGRAM")
        original_id = original_program.id

        # Create config with new category missing required fields
        # This will raise CommandError inside the transaction during _import_program_category
        # (called after deletion), so the deletion should be rolled back
        invalid_config = self.base_config.copy()
        invalid_config["program_category"] = {
            "external_name": "new_category",
            # Missing "icon" and "name" required for new categories
        }
        invalid_config_file = self._create_temp_config(invalid_config)

        # CommandError raised inside transaction during category validation
        with self.assertRaises(CommandError):
            call_command("import_program_config", invalid_config_file, "--override", stdout=StringIO())

        # Verify original program still exists
        # Note: Since the error happens during category import (inside transaction),
        # the deletion should be rolled back
        self.assertTrue(Program.objects.filter(id=original_id).exists())

        # Verify new category was not created
        self.assertFalse(ProgramCategory.objects.filter(external_name="new_category").exists())

        Path(config_file).unlink()
        Path(invalid_config_file).unlink()
