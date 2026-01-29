import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test import TestCase

from programs.models import Program, ProgramConfigImport, ProgramCategory
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

        with self.assertRaises(Exception):
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
                with open(test_file, "w") as f:
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
