import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase

from programs.models import Program, ProgramCategory, Navigator, County
from screener.models import WhiteLabel
from configuration.models import Configuration


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
                "name_abbreviated": "test_program",
                "external_name": "test_program",
                "name": "Test Program Name",
                "description": "Test program description",
                "active": True,
            },
        }

        # Mock Google Translate to avoid slow API calls and missing credentials in CI
        # Patch at the import location where it's used, not at the definition site
        self.translate_patcher = patch("programs.management.commands.import_program_config.Translate")
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
            self.assertTrue(Program.objects.filter(name_abbreviated="test_program").exists())

            # Verify success message says "created" (not "recreated")
            self.assertIn("Successfully created program: test_program", output)
            self.assertNotIn("Successfully recreated program", output)
        finally:
            Path(config_file).unlink()

    def test_override_existing_program_shows_recreated_message(self):
        """Test that overriding an existing program shows 'recreated' in success message."""
        # First, create a program
        config_file = self._create_temp_config(self.base_config)
        call_command("import_program_config", config_file, stdout=StringIO())

        # Verify program exists
        original_program = Program.objects.get(name_abbreviated="test_program")
        original_id = original_program.id

        # Now override it
        out = StringIO()
        call_command("import_program_config", config_file, "--override", stdout=out)
        output = out.getvalue()

        # Verify program was recreated (new ID)
        new_program = Program.objects.get(name_abbreviated="test_program")
        self.assertNotEqual(original_id, new_program.id)

        # Verify success message says "recreated" (not "created")
        self.assertIn("Successfully recreated program: test_program", output)
        self.assertNotIn("Successfully created program: test_program", output)

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
        original_program = Program.objects.get(name_abbreviated="test_program")
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
        self.assertEqual(program.name_abbreviated, "test_program")

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
        self.assertTrue(Program.objects.filter(name_abbreviated="test_program").exists())

        # Verify success message says "created" (not "recreated")
        # because there was nothing to override
        self.assertIn("Successfully created program: test_program", output)
        self.assertNotIn("Successfully recreated program", output)

        Path(config_file).unlink()

    def test_existing_program_without_override_flag_skips_import(self):
        """Test that existing program without --override flag skips import."""
        # First, create a program
        config_file = self._create_temp_config(self.base_config)
        call_command("import_program_config", config_file, stdout=StringIO())

        # Get the original program
        original_program = Program.objects.get(name_abbreviated="test_program")
        original_id = original_program.id

        # Try to import again without --override
        out = StringIO()
        call_command("import_program_config", config_file, stdout=out)
        output = out.getvalue()

        # Verify warning message
        self.assertIn("already exists", output)
        self.assertIn("Use --override", output)

        # Verify original program unchanged
        program = Program.objects.get(name_abbreviated="test_program")
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

        original_program = Program.objects.get(name_abbreviated="test_program")
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

    # --- navigator county validation guard ---

    def _navigator_config(self, external_name: str, counties: list) -> dict:
        """Build a minimal new-navigator config carrying the given counties."""
        return {
            "external_name": external_name,
            "name": f"{external_name} Name",
            "email": "help@example.org",
            "description": "Navigator description",
            "assistance_link": "https://example.org/help",
            "counties": counties,
        }

    def _set_counties_by_zipcode(self, mapping: dict) -> None:
        """Create the white label's counties_by_zipcode Configuration row.

        `mapping` is {zipcode: {county_name: display_name}}, matching the real config shape.
        """
        Configuration.objects.create(
            name="counties_by_zipcode",
            white_label=self.white_label,
            data=mapping,
            active=True,
        )

    def test_navigator_county_wrong_convention_fails_loudly(self):
        """A bare county name on a suffixed-convention white label raises and rolls back."""
        # Screener stores the suffixed form for this white label.
        self._set_counties_by_zipcode({"11111": {"Jackson County": "Jackson County"}})

        config = self.base_config.copy()
        config["navigators"] = [self._navigator_config("test_nav", ["Jackson"])]
        config_file = self._create_temp_config(config)

        try:
            with self.assertRaises(CommandError) as ctx:
                call_command("import_program_config", config_file, stdout=StringIO())

            message = str(ctx.exception)
            self.assertIn("Jackson", message)
            self.assertIn("did you mean 'Jackson County'", message)

            # Fails before any writes: nothing should have been created.
            self.assertFalse(Program.objects.filter(name_abbreviated="test_program").exists())
            self.assertFalse(Navigator.objects.filter(external_name="test_nav").exists())
            self.assertFalse(County.objects.filter(name="Jackson", white_label=self.white_label).exists())
        finally:
            Path(config_file).unlink()

    def test_navigator_county_wrong_convention_fails_loudly_in_dry_run(self):
        """The guard also runs under --dry-run: an invalid county raises and creates nothing."""
        self._set_counties_by_zipcode({"11111": {"Jackson County": "Jackson County"}})

        config = self.base_config.copy()
        config["navigators"] = [self._navigator_config("test_nav", ["Jackson"])]
        config_file = self._create_temp_config(config)

        try:
            with self.assertRaises(CommandError) as ctx:
                call_command("import_program_config", config_file, "--dry-run", stdout=StringIO())

            self.assertIn("did you mean 'Jackson County'", str(ctx.exception))
            self.assertFalse(Program.objects.filter(name_abbreviated="test_program").exists())
            self.assertFalse(Navigator.objects.filter(external_name="test_nav").exists())
        finally:
            Path(config_file).unlink()

    def test_navigator_county_matching_convention_succeeds(self):
        """A county name matching the map imports successfully and is linked."""
        self._set_counties_by_zipcode({"11111": {"Jackson County": "Jackson County"}})

        config = self.base_config.copy()
        config["navigators"] = [self._navigator_config("test_nav", ["Jackson County"])]
        config_file = self._create_temp_config(config)

        try:
            call_command("import_program_config", config_file, stdout=StringIO())

            navigator = Navigator.objects.get(external_name="test_nav")
            self.assertEqual(
                list(navigator.counties.values_list("name", flat=True)),
                ["Jackson County"],
            )
        finally:
            Path(config_file).unlink()

    def test_navigator_county_bare_convention_is_respected(self):
        """The guard is convention-driven, not 'always suffix': a bare-map white label
        accepts the bare name and rejects the suffixed one."""
        self._set_counties_by_zipcode({"22222": {"Cook": "Cook"}})

        ok_config = self.base_config.copy()
        ok_config["navigators"] = [self._navigator_config("bare_nav", ["Cook"])]
        ok_file = self._create_temp_config(ok_config)

        bad_config = self.base_config.copy()
        bad_config["program"] = {
            **self.base_config["program"],
            "name_abbreviated": "other_program",
            "external_name": "other_program",
        }
        bad_config["navigators"] = [self._navigator_config("suffixed_nav", ["Cook County"])]
        bad_file = self._create_temp_config(bad_config)

        try:
            call_command("import_program_config", ok_file, stdout=StringIO())
            self.assertTrue(Navigator.objects.filter(external_name="bare_nav").exists())

            with self.assertRaises(CommandError) as ctx:
                call_command("import_program_config", bad_file, stdout=StringIO())
            # Reverse suggestion: strip the erroneous suffix back to the bare map form.
            self.assertIn("did you mean 'Cook'?", str(ctx.exception))
            self.assertFalse(Navigator.objects.filter(external_name="suffixed_nav").exists())
        finally:
            Path(ok_file).unlink()
            Path(bad_file).unlink()

    def test_navigator_county_validation_skipped_without_config(self):
        """With no counties_by_zipcode config, validation is skipped (does not block)."""
        # Intentionally no _set_counties_by_zipcode() — the config row is absent.
        config = self.base_config.copy()
        config["navigators"] = [self._navigator_config("test_nav", ["Anything"])]
        config_file = self._create_temp_config(config)

        try:
            out = StringIO()
            call_command("import_program_config", config_file, stdout=out)
            self.assertIn("skipping navigator county validation", out.getvalue())
            self.assertTrue(Navigator.objects.filter(external_name="test_nav").exists())
        finally:
            Path(config_file).unlink()

    def test_navigator_county_non_string_entry_fails_loudly(self):
        """A non-string county entry raises a CommandError, not a raw AttributeError."""
        self._set_counties_by_zipcode({"11111": {"Jackson County": "Jackson County"}})

        config = self.base_config.copy()
        config["navigators"] = [self._navigator_config("test_nav", [None])]
        config_file = self._create_temp_config(config)

        try:
            with self.assertRaises(CommandError) as ctx:
                call_command("import_program_config", config_file, stdout=StringIO())
            self.assertIn("is not a string", str(ctx.exception))
            self.assertFalse(Navigator.objects.filter(external_name="test_nav").exists())
        finally:
            Path(config_file).unlink()

    def test_navigator_county_not_validated_for_existing_navigator(self):
        """A pre-existing navigator's config counties aren't written on a non-override import,
        so they aren't validated — a bad name there must not block the import."""
        self._set_counties_by_zipcode({"11111": {"Jackson County": "Jackson County"}})

        # First import creates the program and navigator "reused_nav" with a valid county.
        first = self.base_config.copy()
        first["navigators"] = [self._navigator_config("reused_nav", ["Jackson County"])]
        first_file = self._create_temp_config(first)

        # Second import: a different program reuses the now-existing navigator with a BAD county.
        second = self.base_config.copy()
        second["program"] = {
            **self.base_config["program"],
            "name_abbreviated": "test_program_2",
            "external_name": "test_program_2",
        }
        second["navigators"] = [self._navigator_config("reused_nav", ["Jackson"])]
        second_file = self._create_temp_config(second)

        try:
            call_command("import_program_config", first_file, stdout=StringIO())
            # Must NOT raise despite the bad "Jackson": reused_nav already exists, so its
            # counties are ignored on this non-override import.
            call_command("import_program_config", second_file, stdout=StringIO())
            self.assertTrue(Program.objects.filter(name_abbreviated="test_program_2").exists())
        finally:
            Path(first_file).unlink()
            Path(second_file).unlink()

    def test_counties_config_not_a_dict_fails_loudly(self):
        """A counties_by_zipcode config that isn't a JSON object raises a CommandError."""
        Configuration.objects.create(
            name="counties_by_zipcode",
            white_label=self.white_label,
            data=["not", "a", "dict"],
            active=True,
        )

        config = self.base_config.copy()
        config["navigators"] = [self._navigator_config("test_nav", ["Jackson County"])]
        config_file = self._create_temp_config(config)

        try:
            with self.assertRaises(CommandError) as ctx:
                call_command("import_program_config", config_file, stdout=StringIO())
            self.assertIn("must be a JSON object", str(ctx.exception))
        finally:
            Path(config_file).unlink()
