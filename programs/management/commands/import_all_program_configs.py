from django.core.management.base import BaseCommand
from django.core.management import call_command
from programs.models import ProgramConfigImport, Program
from screener.models import WhiteLabel
from pathlib import Path
from typing import Any
import argparse
import json


class Command(BaseCommand):
    help = """
    Import all program configurations that haven't been imported yet.

    This command scans the import_program_config_data/data/ directory for JSON
    configuration files and imports any that haven't already been processed.
    It works similar to Django migrations - tracking which imports have been run.

    Usage:
      python manage.py import_all_program_configs
      python manage.py import_all_program_configs --dry-run
      python manage.py import_all_program_configs --list

    Options:
      --dry-run    Show which configs would be imported without making changes
      --list       Show status of all config files (imported or pending)
      --file       Import a specific file only (still tracks it)
    """

    # Path to the data directory containing JSON config files
    DATA_DIR = Path(__file__).parent / "import_program_config_data" / "data"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making any changes",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_status",
            help="List all config files and their import status",
        )
        parser.add_argument(
            "--file",
            type=str,
            dest="single_file",
            help="Import a specific file only (by filename, not full path)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options.get("dry_run", False)
        list_status = options.get("list_status", False)
        single_file = options.get("single_file")

        # Verify data directory exists
        if not self.DATA_DIR.exists():
            self.stderr.write(self.style.ERROR(f"Data directory not found: {self.DATA_DIR}"))
            return

        # Get all JSON files in the data directory
        json_files = sorted(self.DATA_DIR.glob("*.json"))

        if not json_files:
            self.stdout.write(self.style.WARNING("No JSON configuration files found in data directory."))
            return

        # Get already imported files
        imported_files = set(ProgramConfigImport.objects.values_list("filename", flat=True))

        # If --list flag, show status and exit
        if list_status:
            self._show_status(json_files, imported_files)
            return

        # If --file flag, filter to just that file
        if single_file:
            json_files = [f for f in json_files if f.name == single_file]
            if not json_files:
                self.stderr.write(self.style.ERROR(f"File not found: {single_file}"))
                return

        # Find pending imports
        pending_files = [f for f in json_files if f.name not in imported_files]

        if not pending_files:
            self.stdout.write(self.style.SUCCESS("\n✓ All program configurations have already been imported.\n"))
            self._show_summary(len(json_files), len(imported_files), 0)
            return

        self.stdout.write(f"Found {len(pending_files)} pending program config import(s)\n")

        # Show what will be imported
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}\n"))

        self.stdout.write(f"Found {len(pending_files)} pending import(s):\n")
        for f in pending_files:
            program_info = self._get_program_info(f)
            self.stdout.write(f"  • {f.name}")
            if program_info:
                self.stdout.write(f"    └─ {program_info['white_label']}/{program_info['program_name']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[Dry run] No imports executed.\n"))
            return

        # Confirm before proceeding
        self.stdout.write("")

        # Process each pending file
        successful = 0
        failed = 0
        skipped = 0

        for config_file in pending_files:
            self.stdout.write(self.style.WARNING(f"\n{'─' * 60}"))
            self.stdout.write(f"Importing: {config_file.name}")
            self.stdout.write(self.style.WARNING(f"{'─' * 60}"))

            try:
                result = self._import_config(config_file)
                if result["status"] == "success":
                    successful += 1
                    # Record the successful import
                    ProgramConfigImport.objects.get_or_create(
                        filename=config_file.name,
                        defaults={
                            "program_name": result["program_name"],
                            "white_label_code": result["white_label_code"],
                        },
                    )

                    self.stdout.write(self.style.SUCCESS(f"✓ Imported and recorded: {config_file.name}"))
                elif result["status"] == "skipped":
                    skipped += 1
                    # Program already exists - record it as imported anyway
                    ProgramConfigImport.objects.get_or_create(
                        filename=config_file.name,
                        defaults={
                            "program_name": result["program_name"],
                            "white_label_code": result["white_label_code"],
                        },
                    )

                    self.stdout.write(
                        self.style.WARNING(f"⊘ Skipped (program exists): {config_file.name} - recorded as imported")
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed: {config_file.name} - {result.get('error', 'Unknown error')}")
                    )
            except Exception as e:
                failed += 1

                self.stdout.write(self.style.ERROR(f"✗ Error importing {config_file.name}: {str(e)}"))

        # Final summary
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS("Import Complete"))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}"))
        self.stdout.write(f"  Successful: {successful}")
        self.stdout.write(f"  Skipped:    {skipped}")
        self.stdout.write(f"  Failed:     {failed}")
        self.stdout.write("")

    def _show_status(self, json_files: list[Path], imported_files: set[str]) -> None:
        """Display the import status of all config files."""
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write("Program Config Import Status")
        self.stdout.write(self.style.WARNING(f"{'=' * 60}\n"))

        pending_count = 0
        imported_count = 0

        for config_file in json_files:
            program_info = self._get_program_info(config_file)
            program_desc = ""
            if program_info:
                program_desc = f" ({program_info['white_label']}/{program_info['program_name']})"

            if config_file.name in imported_files:
                imported_count += 1
                # Get import record for timestamp
                record = ProgramConfigImport.objects.filter(filename=config_file.name).first()
                timestamp = record.imported_at.strftime("%Y-%m-%d %H:%M") if record else "unknown"
                self.stdout.write(self.style.SUCCESS(f"  ✓ {config_file.name}{program_desc}"))
                self.stdout.write(f"      Imported: {timestamp}")
            else:
                pending_count += 1
                self.stdout.write(self.style.WARNING(f"  ○ {config_file.name}{program_desc}"))
                self.stdout.write("      Status: pending")

        self._show_summary(len(json_files), imported_count, pending_count)

    def _show_summary(self, total: int, imported: int, pending: int) -> None:
        """Display summary counts."""
        self.stdout.write(self.style.WARNING(f"\n{'─' * 60}"))
        self.stdout.write(f"Total: {total} | Imported: {imported} | Pending: {pending}")
        self.stdout.write(self.style.WARNING(f"{'─' * 60}\n"))

    def _get_program_info(self, config_file: Path) -> dict[str, str] | None:
        """Extract program info from a config file."""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return {
                    "white_label": config.get("white_label", {}).get("code", "unknown"),
                    "program_name": config.get("program", {}).get("name_abbreviated", "unknown"),
                }
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            return None

    def _import_config(self, config_file: Path) -> dict[str, Any]:
        """
        Import a single configuration file.

        Returns a dict with:
            status: 'success', 'skipped', or 'error'
            program_name: the program's name_abbreviated
            white_label_code: the white label code
            error: error message if status is 'error'
        """
        # Read and parse the config file
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Invalid JSON: {e}"}

        if not isinstance(config, dict):
            return {"status": "error", "error": "Config file does not contain a JSON object"}

        # Extract program info
        white_label_code = config.get("white_label", {}).get("code")
        program_name = config.get("program", {}).get("name_abbreviated")

        if not white_label_code or not program_name:
            return {"status": "error", "error": "Missing white_label.code or program.name_abbreviated"}

        # Check if program already exists
        try:
            white_label = WhiteLabel.objects.get(code=white_label_code)
            existing_program = Program.objects.filter(name_abbreviated=program_name, white_label=white_label).first()

            if existing_program:
                return {
                    "status": "skipped",
                    "program_name": program_name,
                    "white_label_code": white_label_code,
                }
        except WhiteLabel.DoesNotExist:
            return {
                "status": "error",
                "error": f"WhiteLabel '{white_label_code}' not found",
                "program_name": program_name,
                "white_label_code": white_label_code,
            }

        # Call the import_program_config command
        try:
            call_command(
                "import_program_config",
                str(config_file),
                stdout=self.stdout,
                stderr=self.stderr,
            )
            return {
                "status": "success",
                "program_name": program_name,
                "white_label_code": white_label_code,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "program_name": program_name,
                "white_label_code": white_label_code,
            }
