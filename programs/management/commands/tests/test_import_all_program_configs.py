import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase

from programs.management.commands.import_all_program_configs import config_content_hash
from programs.models import Program, ProgramConfigImport, ProgramCategory, ProgramNavigator
from screener.models import WhiteLabel


class ImportAllProgramConfigsCommandTest(TestCase):
    """Tests for the import_all_program_configs management command"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        # Create white labels
        cls.co_white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.tx_white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        cls.il_white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")

    def setUp(self):
        """Set up for each test"""
        self.out = StringIO()
        self.err = StringIO()
        # Clear any existing import records
        ProgramConfigImport.objects.all().delete()

    def test_model_creation(self):
        """Test that ProgramConfigImport model works correctly"""
        record = ProgramConfigImport.objects.create(
            filename="test_program.json",
            program_name="test_program",
            white_label_code="co",
        )

        self.assertEqual(record.filename, "test_program.json")
        self.assertEqual(record.program_name, "test_program")
        self.assertEqual(record.white_label_code, "co")
        self.assertIsNotNone(record.imported_at)

    def test_model_unique_filename(self):
        """Test that filename must be unique"""
        ProgramConfigImport.objects.create(
            filename="test_program.json",
            program_name="test_program",
            white_label_code="co",
        )

        with self.assertRaises(IntegrityError):
            ProgramConfigImport.objects.create(
                filename="test_program.json",
                program_name="another_program",
                white_label_code="tx",
            )

    def test_list_status_flag(self):
        """Test the --list flag shows import status"""
        # Create a record for one file
        ProgramConfigImport.objects.create(
            filename="co_jeffco_student_benefits_initial_config.json",
            program_name="jeffco_student_benefits",
            white_label_code="co",
        )

        call_command(
            "import_all_program_configs",
            "--list",
            stdout=self.out,
            stderr=self.err,
        )

        output = self.out.getvalue()
        self.assertIn("Program Config Import Status", output)
        self.assertIn("co_jeffco_student_benefits_initial_config.json", output)

    def test_dry_run_flag(self):
        """Test the --dry-run flag doesn't make changes"""
        initial_count = ProgramConfigImport.objects.count()

        call_command(
            "import_all_program_configs",
            "--dry-run",
            stdout=self.out,
            stderr=self.err,
        )

        output = self.out.getvalue()
        self.assertIn("DRY RUN", output)

        # No new records should be created
        self.assertEqual(ProgramConfigImport.objects.count(), initial_count)

    def test_already_imported_files_are_skipped(self):
        """Test that files already in ProgramConfigImport are skipped"""
        # Create import records for all files
        data_dir = Path(__file__).parent.parent / "import_program_config_data" / "data"
        if data_dir.exists():
            for json_file in data_dir.glob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        config = json.load(f)
                    program_name = config.get("program", {}).get("name_abbreviated", "unknown")
                    white_label = config.get("white_label", {}).get("code", "unknown")
                    ProgramConfigImport.objects.create(
                        filename=json_file.name,
                        program_name=program_name,
                        white_label_code=white_label,
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

        call_command(
            "import_all_program_configs",
            stdout=self.out,
            stderr=self.err,
        )

        output = self.out.getvalue()
        self.assertIn("All program configurations have already been imported", output)

    def test_command_tracks_successful_imports(self):
        """Test that successful imports are recorded in ProgramConfigImport"""
        # This test uses mocking to avoid actually running the import
        with patch("programs.management.commands.import_all_program_configs.Command._import_config") as mock_import:
            mock_import.return_value = {
                "status": "success",
                "program_name": "test_program",
                "white_label_code": "co",
            }

            # Create a temporary test JSON file
            test_config = {
                "white_label": {"code": "co"},
                "program_category": {"external_name": "test_category"},
                "program": {"name_abbreviated": "test_program"},
            }

            # Create temp directory and file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_data_dir = Path(temp_dir) / "data"
                temp_data_dir.mkdir()
                test_file = temp_data_dir / "test_program.json"
                with open(test_file, "w", encoding="utf-8") as f:
                    json.dump(test_config, f)

                # Patch the DATA_DIR to use our temp directory
                with patch.object(
                    type(self)._get_command_class(),
                    "DATA_DIR",
                    temp_data_dir,
                ):
                    call_command(
                        "import_all_program_configs",
                        stdout=self.out,
                        stderr=self.err,
                    )

                # Verify the import was tracked
                self.assertTrue(
                    ProgramConfigImport.objects.filter(filename="test_program.json").exists(),
                    "Expected ProgramConfigImport record to be created",
                )

    @staticmethod
    def _get_command_class():
        """Get the Command class for patching"""
        from programs.management.commands.import_all_program_configs import Command

        return Command

    def test_file_flag_imports_specific_file(self):
        """Test that --file flag targets a specific file"""
        call_command(
            "import_all_program_configs",
            "--file",
            "nonexistent_file.json",
            stdout=self.out,
            stderr=self.err,
        )

        output = self.err.getvalue()
        self.assertIn("File not found", output)


class SkippedConfigTrackingTest(TestCase):
    """
    A skipped config must stay pending.

    Recording a skip as an import is what permanently excluded configs from future runs,
    so their navigators, documents and warning messages were never applied. These tests
    pin the corrected behaviour: nothing applied means nothing recorded.
    """

    def setUp(self):
        self.out = StringIO()
        self.err = StringIO()
        ProgramConfigImport.objects.all().delete()
        WhiteLabel.objects.get_or_create(code="co", defaults={"name": "Colorado", "state_code": "CO"})

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.data_dir.mkdir()

        self.config = {
            "white_label": {"code": "co"},
            "program_category": {"external_name": "test_category", "icon": "icon", "name": "Test Category"},
            "program": {"name_abbreviated": "existing_program"},
        }
        self.config_file = self.data_dir / "existing_program.json"
        self.config_file.write_text(json.dumps(self.config), encoding="utf-8")

        patcher = patch.object(self._command_class(), "DATA_DIR", self.data_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Any test here that imports a config for a program that does not yet exist will
        # create one, and creating a program translates its fields. Translate() reads
        # GOOGLE_APPLICATION_CREDENTIALS at construction and does not consult
        # ENABLE_GOOGLE_INTEGRATIONS, so without this the tests reach the real API where
        # credentials exist and fail outright in CI, where they do not.
        translate_patcher = patch("programs.management.commands.import_program_config.Translate")
        translate = translate_patcher.start()
        translate.return_value.bulk_translate.side_effect = lambda langs, texts: {
            text: {lang: text for lang in langs} for text in texts
        }
        self.addCleanup(translate_patcher.stop)

    @staticmethod
    def _command_class():
        from programs.management.commands.import_all_program_configs import Command

        return Command

    def _create_existing_program(self):
        return Program.objects.new_program(white_label="co", name_abbreviated="existing_program")

    def _run(self, *args):
        out = StringIO()
        call_command("import_all_program_configs", *args, stdout=out, stderr=self.err)
        return out.getvalue()

    def test_skipped_config_is_not_recorded_as_imported(self):
        """The config a skip touched must not gain a tracking row."""
        self._create_existing_program()

        self._run()

        self.assertFalse(
            ProgramConfigImport.objects.filter(filename="existing_program.json").exists(),
            "A skipped config must not be recorded as imported",
        )

    def test_skipped_config_stays_pending_on_the_next_run(self):
        """The exclusion must not be permanent — a skipped config comes back as pending."""
        self._create_existing_program()
        self._run()

        output = self._run("--list")

        self.assertIn("existing_program.json", output)
        self.assertIn("Status: pending", output)

    def test_skip_is_reported_distinctly_from_success(self):
        """A run where everything skipped must not read as a clean import."""
        self._create_existing_program()

        output = self._run()

        self.assertIn("Skipped", output)
        self.assertIn("still pending", output)
        self.assertRegex(output, r"Successful:\s+0")
        self.assertNotIn("recorded as imported", output)

    def test_successful_import_records_a_content_hash(self):
        output = self._run()

        record = ProgramConfigImport.objects.get(filename="existing_program.json")
        self.assertEqual(record.content_hash, config_content_hash(self.config_file))
        self.assertIn("Imported and recorded", output)

    def test_edited_config_becomes_pending_again(self):
        """A tracking row is a claim about specific content, so edits re-open the config."""
        self._run()
        self.assertFalse(self._pending_filenames())

        edited = dict(self.config)
        edited["documents"] = [{"external_name": "new_document", "text": "Bring photo ID"}]
        self.config_file.write_text(json.dumps(edited), encoding="utf-8")

        self.assertIn("existing_program.json", self._pending_filenames())
        self.assertIn("file edited since it was imported", self._run("--list"))

    def test_legacy_record_without_a_hash_is_treated_as_applied(self):
        """Rows that predate hashing must not all re-open at once."""
        ProgramConfigImport.objects.create(
            filename="existing_program.json",
            program_name="existing_program",
            white_label_code="co",
            content_hash="",
        )

        self.assertEqual(self._pending_filenames(), [])

    def test_reconcile_repairs_a_config_that_was_skipped(self):
        """
        End-to-end repair: a program that exists but never had its config applied gets
        its navigators linked by a --reconcile run, and only then is it recorded.
        """
        with_navigator = dict(self.config)
        with_navigator["navigators"] = [
            {
                "external_name": "test_navigator",
                "name": "Test Navigator",
                "email": "navigator@example.com",
                "description": "Helps people apply",
                "assistance_link": "https://example.com/help",
            }
        ]
        self.config_file.write_text(json.dumps(with_navigator), encoding="utf-8")

        program = self._create_existing_program()
        self._run()
        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 0)

        output = self._run("--reconcile")

        self.assertEqual(ProgramNavigator.objects.filter(program=program).count(), 1)
        self.assertIn("Reconciled and recorded", output)
        self.assertTrue(ProgramConfigImport.objects.filter(filename="existing_program.json").exists())

    def test_reconcile_dry_run_records_nothing(self):
        self._create_existing_program()

        self._run("--reconcile", "--dry-run")

        self.assertFalse(ProgramConfigImport.objects.filter(filename="existing_program.json").exists())

    def _pending_filenames(self):
        command = self._command_class()()
        records = command._get_import_records()
        return [f.name for f in self.data_dir.glob("*.json") if command._is_pending(f, records)]


class ProgramConfigImportModelTest(TestCase):
    """Tests for the ProgramConfigImport model"""

    def test_str_representation(self):
        """Test the string representation of the model"""
        record = ProgramConfigImport.objects.create(
            filename="co_snap_config.json",
            program_name="co_snap",
            white_label_code="co",
        )

        str_repr = str(record)
        self.assertIn("co_snap_config.json", str_repr)
        self.assertIn("co_snap", str_repr)

    def test_ordering(self):
        """Test that records are ordered by imported_at descending"""
        record1 = ProgramConfigImport.objects.create(
            filename="first.json",
            program_name="first_program",
            white_label_code="co",
        )
        record2 = ProgramConfigImport.objects.create(
            filename="second.json",
            program_name="second_program",
            white_label_code="tx",
        )

        records = list(ProgramConfigImport.objects.all())
        # Most recent should be first (record2)
        self.assertEqual(records[0].filename, "second.json")
        self.assertEqual(records[1].filename, "first.json")
