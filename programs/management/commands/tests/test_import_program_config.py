import copy
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase

from programs.models import (
    County,
    FederalPoveryLimit,
    LegalStatus,
    Navigator,
    Program,
    ProgramCategory,
    ProgramNavigator,
    WarningMessage,
)
from screener.models import WhiteLabel
from configuration.models import Configuration
from translations.models import Translation


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

    def test_dynamic_year_row_is_found_by_year_only(self):
        """Dynamic FPL rows have year != period (MFB-564), e.g.
        year="THIS_YEAR_CALENDAR", period="2026". Matching on year AND period
        only ever worked for legacy rows where the two happen to be equal, and
        always missed dynamic rows."""
        fpl, _ = FederalPoveryLimit.objects.get_or_create(year="THIS_YEAR_CALENDAR", defaults={"period": "2026"})
        self.assertNotEqual(fpl.period, fpl.year)
        config = copy.deepcopy(self.base_config)
        config["program"]["year"] = "THIS_YEAR_CALENDAR"
        config_file = self._create_temp_config(config)
        out = StringIO()

        try:
            call_command("import_program_config", config_file, stdout=out)
            program = Program.objects.get(name_abbreviated="test_program")
            self.assertEqual(program.year_id, fpl.id)
            self.assertNotIn("Warning: Year", out.getvalue())
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

        # Verify warning message offers both recovery paths
        self.assertIn("already exists", output)
        self.assertIn("--reconcile", output)
        self.assertIn("--override", output)

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


class ReconcileProgramConfigTestCase(TransactionTestCase):
    """
    Tests for `import_program_config --reconcile` and the --override delete guard.

    Reconcile repairs programs whose config was recorded as imported but never actually
    applied. It has to be strictly additive: navigators created or hand-edited in the
    admin, and any ordering curated there, must survive it untouched.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(code="test_wl", name="Test White Label")

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
            "navigators": [
                {
                    "external_name": "test_navigator",
                    "name": "Test Navigator",
                    "email": "navigator@example.com",
                    "description": "Helps people apply",
                    "assistance_link": "https://example.com/help",
                    "counties": ["Denver County"],
                }
            ],
        }

        self.translate_patcher = patch("programs.management.commands.import_program_config.Translate")
        mock_instance = self.translate_patcher.start().return_value
        mock_instance.bulk_translate.side_effect = lambda langs, texts: {
            text: {lang: f"{text} (translated to {lang})" for lang in langs} for text in texts
        }
        self.addCleanup(self.translate_patcher.stop)

        self._temp_files: list[str] = []
        self.addCleanup(self._cleanup_temp_files)

    def _cleanup_temp_files(self):
        for path in self._temp_files:
            Path(path).unlink(missing_ok=True)

    def _create_temp_config(self, config: dict) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            self._temp_files.append(f.name)
            return f.name

    def _config_without_navigators(self) -> dict:
        config = copy.deepcopy(self.base_config)
        config.pop("navigators")
        return config

    def _make_admin_navigator(self, external_name: str) -> Navigator:
        """Stand in for a navigator someone created by hand in the admin portal."""
        navigator = Navigator.objects.new_navigator(white_label="test_wl", name=external_name, phone_number=None)
        navigator.external_name = external_name
        navigator.save()
        return navigator

    def _english(self, translation: Translation) -> str:
        return Translation.objects.language(settings.LANGUAGE_CODE).get(pk=translation.pk).text

    def _require_suffixed_counties(self) -> None:
        """Make this white label's screener convention the suffixed form."""
        Configuration.objects.create(
            name="counties_by_zipcode",
            white_label=self.white_label,
            data={"80202": {"Denver County": "Denver County"}},
            active=True,
        )

    def _config_with_bad_county(self) -> dict:
        config = copy.deepcopy(self.base_config)
        config["navigators"][0]["counties"] = ["Denver"]
        return config

    def test_reconcile_validates_navigator_counties(self):
        """
        Reconcile creates navigators, and creating one writes its counties, so the county
        guard has to cover this path too — otherwise a repair pass is a way to reintroduce
        the exact mismatch the guard exists to block.
        """
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )
        program = Program.objects.get(name_abbreviated="test_program")
        self._require_suffixed_counties()

        with self.assertRaises(CommandError) as raised:
            call_command(
                "import_program_config",
                self._create_temp_config(self._config_with_bad_county()),
                "--reconcile",
                stdout=StringIO(),
            )

        self.assertIn("did you mean 'Denver County'", str(raised.exception))
        self.assertFalse(Navigator.objects.filter(external_name="test_navigator").exists())
        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 0)

    def test_reconcile_only_documents_does_not_validate_navigator_counties(self):
        """
        The guard is scoped to what a run will write. A documents-only pass never touches
        navigators, so it must not be blocked by a navigator's county names.
        """
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )
        program = Program.objects.get(name_abbreviated="test_program")
        self._require_suffixed_counties()

        config = self._config_with_bad_county()
        config["documents"] = [{"external_name": "test_document", "text": "Bring photo ID"}]

        call_command(
            "import_program_config",
            self._create_temp_config(config),
            "--reconcile",
            "--only",
            "documents",
            stdout=StringIO(),
        )

        self.assertEqual(program.documents.count(), 1)
        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 0)

    def test_override_skips_county_validation_for_a_navigator_it_will_not_recreate(self):
        """
        County validation is scoped to navigators a run will recreate, and that scoping has to
        read the same relation the delete guard does. A navigator shared only through
        ProgramNavigator is kept, so its counties are never rewritten — validating them would
        block an override over a field this run does not touch.
        """
        call_command("import_program_config", self._create_temp_config(self.base_config), stdout=StringIO())
        navigator = Navigator.objects.get(external_name="test_navigator")

        other_program = Program.objects.new_program(white_label="test_wl", name_abbreviated="other_program")
        ProgramNavigator.objects.create(program=other_program, navigator=navigator, order=0)

        self._require_suffixed_counties()

        out = StringIO()
        call_command(
            "import_program_config", self._create_temp_config(self._config_with_bad_county()), "--override", stdout=out
        )

        self.assertIn("Keeping navigator", out.getvalue())
        self.assertTrue(Navigator.objects.filter(external_name="test_navigator").exists())

    def test_reconcile_creates_missing_navigator_link(self):
        """A program imported without its navigators gets them linked by a reconcile pass."""
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )

        program = Program.objects.get(name_abbreviated="test_program")
        original_id = program.id
        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 0)

        out = StringIO()
        call_command("import_program_config", self._create_temp_config(self.base_config), "--reconcile", stdout=out)

        links = ProgramNavigator.objects.filter(program=program)
        self.assertEqual(links.count(), 1)
        self.assertEqual(links.first().navigator.external_name, "test_navigator")

        # The program itself is reused, not recreated
        self.assertEqual(Program.objects.get(name_abbreviated="test_program").id, original_id)
        self.assertIn("Reconciled", out.getvalue())

    def test_reconcile_preserves_navigator_absent_from_config(self):
        """An admin-created navigator is neither deleted nor unlinked by a reconcile pass."""
        call_command("import_program_config", self._create_temp_config(self.base_config), stdout=StringIO())
        program = Program.objects.get(name_abbreviated="test_program")

        admin_navigator = self._make_admin_navigator("admin_only_navigator")
        ProgramNavigator.objects.create(program=program, navigator=admin_navigator, order=1000)

        call_command(
            "import_program_config", self._create_temp_config(self.base_config), "--reconcile", stdout=StringIO()
        )

        self.assertTrue(Navigator.objects.filter(external_name="admin_only_navigator").exists())
        self.assertTrue(ProgramNavigator.objects.filter(program=program, navigator=admin_navigator).exists())

    def test_reconcile_does_not_overwrite_existing_navigator_fields(self):
        """A hand-edited navigator name survives a reconcile pass that declares a different one."""
        call_command("import_program_config", self._create_temp_config(self.base_config), stdout=StringIO())

        navigator = Navigator.objects.get(external_name="test_navigator")
        Translation.objects.edit_translation_by_id(
            navigator.name.id, settings.LANGUAGE_CODE, "Hand Edited In Admin", manual=True
        )

        renamed = copy.deepcopy(self.base_config)
        renamed["navigators"][0]["name"] = "Name From Config"
        call_command("import_program_config", self._create_temp_config(renamed), "--reconcile", stdout=StringIO())

        navigator.refresh_from_db()
        self.assertEqual(self._english(navigator.name), "Hand Edited In Admin")

    def test_reconcile_appends_new_links_after_existing_ones(self):
        """New links go after existing ones so admin-curated ordering is not reshuffled."""
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )
        program = Program.objects.get(name_abbreviated="test_program")

        admin_navigator = self._make_admin_navigator("admin_only_navigator")
        ProgramNavigator.objects.create(program=program, navigator=admin_navigator, order=5)

        call_command(
            "import_program_config", self._create_temp_config(self.base_config), "--reconcile", stdout=StringIO()
        )

        config_link = ProgramNavigator.objects.get(program=program, navigator__external_name="test_navigator")
        self.assertGreater(config_link.order, 5)

    def test_reconcile_dry_run_reports_without_applying(self):
        """A reconcile dry run names what it would add and changes nothing."""
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )
        program = Program.objects.get(name_abbreviated="test_program")

        out = StringIO()
        call_command(
            "import_program_config",
            self._create_temp_config(self.base_config),
            "--reconcile",
            "--dry-run",
            stdout=out,
        )
        output = out.getvalue()

        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 0)
        self.assertIn("test_navigator", output)
        self.assertIn("Dry run", output)

    def test_reconcile_reports_entities_it_would_create(self):
        """A navigator that does not exist yet is flagged distinctly from one that just needs a link."""
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )

        out = StringIO()
        call_command(
            "import_program_config",
            self._create_temp_config(self.base_config),
            "--reconcile",
            "--dry-run",
            stdout=out,
        )

        self.assertIn("entity to create", out.getvalue())

    def test_reconcile_only_limits_sections(self):
        """--only navigators leaves the config's documents alone."""
        with_documents = copy.deepcopy(self._config_without_navigators())
        with_documents["documents"] = [{"external_name": "test_document", "text": "Bring photo ID"}]
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )

        both = copy.deepcopy(self.base_config)
        both["documents"] = with_documents["documents"]

        program = Program.objects.get(name_abbreviated="test_program")
        call_command(
            "import_program_config",
            self._create_temp_config(both),
            "--reconcile",
            "--only",
            "navigators",
            stdout=StringIO(),
        )

        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 1)
        self.assertEqual(program.documents.count(), 0)

    def test_reconcile_is_idempotent(self):
        """Running reconcile twice does not duplicate links."""
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )
        config_file = self._create_temp_config(self.base_config)

        call_command("import_program_config", config_file, "--reconcile", stdout=StringIO())
        out = StringIO()
        call_command("import_program_config", config_file, "--reconcile", stdout=out)

        program = Program.objects.get(name_abbreviated="test_program")
        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 1)
        self.assertIn("Already up to date", out.getvalue())

    def test_reconcile_refuses_to_create_a_missing_program(self):
        """Reconcile repairs existing programs only; it never creates one."""
        out = StringIO()
        call_command("import_program_config", self._create_temp_config(self.base_config), "--reconcile", stdout=out)

        self.assertFalse(Program.objects.filter(name_abbreviated="test_program").exists())
        self.assertIn("does not exist", out.getvalue())

    def test_reconcile_rejects_a_declaration_without_an_external_name(self):
        """
        A malformed declaration must fail loudly, not vanish from the plan.

        Dropping it silently leaves an empty plan, which reads as "already up to date" — so
        the config would report clean, apply nothing, and then be recorded as applied. That
        is the defect this whole change exists to remove, so the plan validates the same
        fields the import path does.
        """
        call_command(
            "import_program_config", self._create_temp_config(self._config_without_navigators()), stdout=StringIO()
        )
        program = Program.objects.get(name_abbreviated="test_program")

        malformed = copy.deepcopy(self.base_config)
        del malformed["navigators"][0]["external_name"]

        with self.assertRaises(CommandError) as raised:
            call_command("import_program_config", self._create_temp_config(malformed), "--reconcile", stdout=StringIO())

        self.assertIn("external_name", str(raised.exception))
        self.assertIn("navigators[0]", str(raised.exception))
        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 0)

    def test_reconcile_and_override_are_mutually_exclusive(self):
        with self.assertRaises(CommandError):
            call_command(
                "import_program_config",
                self._create_temp_config(self.base_config),
                "--reconcile",
                "--override",
                stdout=StringIO(),
            )

    def test_override_keeps_navigator_shared_through_program_navigator(self):
        """
        The --override delete guard has to read the relation the importer actually writes.

        The importer and the admin both populate ProgramNavigator, never the legacy
        `programs` M2M, so a guard that checks only the legacy relation sees every shared
        navigator as unshared and deletes it.
        """
        call_command("import_program_config", self._create_temp_config(self.base_config), stdout=StringIO())
        navigator = Navigator.objects.get(external_name="test_navigator")

        other_program = Program.objects.new_program(white_label="test_wl", name_abbreviated="other_program")
        ProgramNavigator.objects.create(program=other_program, navigator=navigator, order=0)

        out = StringIO()
        call_command("import_program_config", self._create_temp_config(self.base_config), "--override", stdout=out)

        self.assertTrue(
            Navigator.objects.filter(external_name="test_navigator").exists(),
            "A navigator shared with another program must survive --override",
        )
        self.assertTrue(ProgramNavigator.objects.filter(program=other_program, navigator=navigator).exists())
        self.assertIn("Keeping navigator", out.getvalue())


class WarningMessageScopeTestCase(TransactionTestCase):
    """Tests for the legal statuses and counties that narrow a warning's audience."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(code="test_wl", name="Test White Label")
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

        self.translate_patcher = patch("programs.management.commands.import_program_config.Translate")
        mock_instance = self.translate_patcher.start().return_value
        mock_instance.bulk_translate.side_effect = lambda langs, texts: {
            text: {lang: f"{text} (translated to {lang})" for lang in langs} for text in texts
        }

    def tearDown(self):
        self.translate_patcher.stop()

    def _import(self, warning_config: dict) -> WarningMessage:
        config = copy.deepcopy(self.base_config)
        config["warning_message"] = warning_config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            call_command("import_program_config", path, stdout=StringIO())
        finally:
            Path(path).unlink()
        return WarningMessage.objects.get(external_name=warning_config["external_name"])

    def test_legal_statuses_are_applied(self):
        """A warning declaring legal statuses is restricted to them."""
        LegalStatus.objects.create(status="gc_18plus_no5")
        LegalStatus.objects.create(status="otherWithWorkPermission")

        warning = self._import(
            {
                "external_name": "scoped_warning",
                "message": "Scoped message",
                "legal_statuses": ["gc_18plus_no5", "otherWithWorkPermission"],
            }
        )

        self.assertEqual(
            {s.status for s in warning.legal_statuses.all()},
            {"gc_18plus_no5", "otherWithWorkPermission"},
        )

    def test_omitted_legal_statuses_leave_the_warning_unrestricted(self):
        """
        A config without legal statuses produces a warning shown to everyone.

        Empty means "no restriction" on the frontend, so omitting the field has to
        stay equivalent to the behaviour before it was read.
        """
        warning = self._import({"external_name": "unscoped_warning", "message": "Unscoped message"})

        self.assertEqual(warning.legal_statuses.count(), 0)

    def test_unknown_legal_status_warns_without_failing_the_import(self):
        """An unrecognised status is reported and skipped, matching program import."""
        LegalStatus.objects.create(status="gc_18plus_no5")

        config = copy.deepcopy(self.base_config)
        config["warning_message"] = {
            "external_name": "partially_scoped_warning",
            "message": "Partially scoped message",
            "legal_statuses": ["gc_18plus_no5", "not_a_real_status"],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name

        out = StringIO()
        try:
            call_command("import_program_config", path, stdout=out)
        finally:
            Path(path).unlink()

        warning = WarningMessage.objects.get(external_name="partially_scoped_warning")
        self.assertEqual([s.status for s in warning.legal_statuses.all()], ["gc_18plus_no5"])
        self.assertIn("not_a_real_status", out.getvalue())

    def test_counties_are_applied(self):
        """A warning declaring counties is restricted to them."""
        County.objects.create(name="King County", white_label=self.white_label)

        warning = self._import(
            {
                "external_name": "county_scoped_warning",
                "message": "County scoped message",
                "counties": ["King County"],
            }
        )

        self.assertEqual([c.name for c in warning.counties.all()], ["King County"])
