from dataclasses import dataclass, field

from django.core.management.base import BaseCommand
from django.core.management import call_command
from programs.management.commands.import_program_config import (
    RECONCILE_SECTIONS,
    Command as ImportProgramConfigCommand,
)
from programs.models import ProgramConfigImport, Program
from screener.models import WhiteLabel
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json


def config_content_hash(config_file: Path) -> str:
    """
    Return the SHA-256 of a config file's raw bytes.

    Recorded alongside the tracking row so that editing a config re-opens it as
    pending. Migration 0166 duplicates this to backfill existing rows.
    """
    return hashlib.sha256(config_file.read_bytes()).hexdigest()


@dataclass
class ImportResults:
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    reconciled: int = 0
    already_current: int = 0
    links_to_add: int = 0
    # Held by identity, not counted, so an entity declared by several configs is one entity.
    entities_to_create: set[tuple[str, str]] = field(default_factory=set)
    reconcile: bool = False
    partial_pass: bool = False


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
      python manage.py import_all_program_configs --reconcile --dry-run
      python manage.py import_all_program_configs --reconcile --only navigators

    Options:
      --dry-run    Show what would change without making changes
      --list       Show status of all config files (imported or pending)
      --file       Process a specific file only
      --reconcile  Additively apply configs to programs that already exist
      --only       With --reconcile, limit to given sections (repeatable)

    A config whose program already exists is skipped and left pending — a skip is
    never recorded as an import, so nothing becomes permanently unreachable. Use
    --reconcile to additively apply such a config's warning messages, documents and
    navigators to the existing program without touching anything already there.

    Tracking rows store a hash of the config file, so editing a config re-opens it
    as pending on the next run. A row is only written when the whole config was
    applied, so a --only pass records nothing.
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
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="Additively apply configs to programs that already exist, creating missing "
            "warning messages, documents and navigators and their links. Never updates or "
            "deletes anything. Combine with --dry-run to preview.",
        )
        parser.add_argument(
            "--only",
            action="append",
            choices=list(RECONCILE_SECTIONS),
            help="With --reconcile, limit the pass to these sections. Repeatable. Defaults to all of them. "
            "A partial pass records nothing, since only part of each config is applied.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Orchestrates the import process based on command options."""
        if not self._validate_data_directory():
            return

        json_files = self._discover_config_files()
        if not json_files:
            self.stdout.write(self.style.WARNING("No JSON configuration files found in data directory."))
            return

        import_records = self._get_import_records()

        if options["list_status"]:
            return self._show_status(json_files, import_records)

        reconcile = options.get("reconcile", False)
        only = options.get("only")
        if only and not reconcile:
            self.stderr.write(self.style.ERROR("--only has no effect without --reconcile."))
            return

        dry_run = options["dry_run"]

        target_files = self._select_target_files(json_files, import_records, options.get("single_file"), reconcile)
        if target_files is None:  # error already written to stderr
            return

        if not target_files:
            self.stdout.write(self.style.SUCCESS("\n✓ All program configurations have already been imported.\n"))
            self._show_summary(len(json_files), len(json_files), 0)
            return

        # A reconcile dry run has to invoke the importer to report what it would change,
        # so it goes through the normal execution path rather than the file listing.
        if dry_run and not reconcile:
            return self._handle_dry_run(target_files)

        results = self._execute_imports(target_files, reconcile=reconcile, only=only, dry_run=dry_run)
        self._display_final_summary(results, dry_run=dry_run)

    def _validate_data_directory(self) -> bool:
        """Return False and write an error if the data directory doesn't exist."""
        if not self.DATA_DIR.exists():
            self.stderr.write(self.style.ERROR(f"Data directory not found: {self.DATA_DIR}"))
            return False
        return True

    def _discover_config_files(self) -> list[Path]:
        """Return a sorted list of JSON config files in the data directory."""
        return sorted(self.DATA_DIR.glob("*.json"))

    def _get_import_records(self) -> dict[str, str]:
        """Return {filename: content_hash} for every config already recorded as imported."""
        return dict(ProgramConfigImport.objects.values_list("filename", "content_hash"))

    def _is_pending(self, config_file: Path, import_records: dict[str, str]) -> bool:
        """
        Whether a config still needs to be applied.

        Never recorded means pending. A record with an empty hash predates hashing and is
        taken at face value. A record whose hash no longer matches the file means the config
        was edited since it was applied, so it is pending again — the same guarantee Django
        migrations give, and the reason a skip must never write a record.
        """
        if config_file.name not in import_records:
            return True

        recorded_hash = import_records[config_file.name]
        if not recorded_hash:
            return False

        return recorded_hash != config_content_hash(config_file)

    def _select_target_files(
        self,
        json_files: list[Path],
        import_records: dict[str, str],
        single_file: str | None,
        reconcile: bool,
    ) -> list[Path] | None:
        """
        Return the files this run should process.

        A normal run processes pending files only. A --reconcile run considers every
        config, since the point of reconciling is to repair programs whose config was
        recorded but never actually applied.

        If single_file is given, filters to just that file. Returns None (writing to
        stderr) if a requested single file isn't found in the data directory.
        """
        if single_file:
            json_files = [f for f in json_files if f.name == single_file]
            if not json_files:
                self.stderr.write(self.style.ERROR(f"File not found: {single_file}"))
                return None

        if reconcile:
            return json_files

        return [f for f in json_files if self._is_pending(f, import_records)]

    def _handle_dry_run(self, pending_files: list[Path]) -> None:
        """Display what would be imported without making any changes."""
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}\n"))

        self.stdout.write(f"Found {len(pending_files)} pending import(s):\n")
        for f in pending_files:
            program_info = self._get_program_info(f)
            self.stdout.write(f"  • {f.name}")
            if program_info:
                self.stdout.write(f"    └─ {program_info['white_label']}/{program_info['program_name']}")

        self.stdout.write(self.style.WARNING("\n[Dry run] No imports executed.\n"))

    def _execute_imports(
        self,
        target_files: list[Path],
        reconcile: bool = False,
        only: list[str] | None = None,
        dry_run: bool = False,
    ) -> ImportResults:
        """Process each target config file and return the results."""
        results = ImportResults()

        # A --only pass applies part of a config, so it must not stamp a hash covering the
        # whole file — recording a partial apply as complete is the same defect as recording
        # a skip. Reconcile ignores tracking state when selecting files, so a partial pass
        # loses nothing by recording nothing.
        results.reconcile = reconcile
        results.partial_pass = bool(only) and set(only) != set(RECONCILE_SECTIONS)

        verb = "reconcile" if reconcile else "import"
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}\n"))
        self.stdout.write(f"Found {len(target_files)} config(s) to {verb}:\n")
        for f in target_files:
            program_info = self._get_program_info(f)
            self.stdout.write(f"  • {f.name}")
            if program_info:
                self.stdout.write(f"    └─ {program_info['white_label']}/{program_info['program_name']}")

        self.stdout.write("")

        for config_file in target_files:
            self.stdout.write(self.style.WARNING(f"\n{'─' * 60}"))
            self.stdout.write(f"{verb.capitalize()}: {config_file.name}")
            self.stdout.write(self.style.WARNING(f"{'─' * 60}"))

            try:
                result = self._import_config(config_file, reconcile=reconcile, only=only, dry_run=dry_run)
                status = result["status"]

                if status == "success":
                    results.successful += 1
                    self._record_import(config_file, result)
                    self.stdout.write(self.style.SUCCESS(f"✓ Imported and recorded: {config_file.name}"))
                elif status == "reconciled":
                    results.links_to_add += result.get("links_to_add", 0)
                    results.entities_to_create.update(result.get("entities_to_create", ()))
                    record = not dry_run and not results.partial_pass

                    if not result.get("changed"):
                        results.already_current += 1
                        if record:
                            self._record_import(config_file, result)
                        continue

                    results.reconciled += 1
                    if dry_run:
                        self.stdout.write(self.style.WARNING(f"⋯ Would reconcile: {config_file.name}"))
                    elif record:
                        self._record_import(config_file, result)
                        self.stdout.write(self.style.SUCCESS(f"✓ Reconciled and recorded: {config_file.name}"))
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Reconciled: {config_file.name} "
                                f"(left pending — only part of the config was applied)"
                            )
                        )
                elif status == "skipped":
                    # Deliberately no tracking row: nothing in this config was applied, so
                    # recording it would exclude it from every future run.
                    results.skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"⊘ Skipped: {config_file.name} - {result.get('reason', 'program already exists')} "
                            f"(left pending, nothing applied)"
                        )
                    )
                else:
                    results.failed += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed: {config_file.name} - {result.get('error', 'Unknown error')}")
                    )
            except Exception as e:
                results.failed += 1
                self.stdout.write(self.style.ERROR(f"✗ Error importing {config_file.name}: {str(e)}"))

        return results

    def _summarize_reconcile_plan(
        self, program: Program, config: dict[str, Any], only: list[str] | None
    ) -> dict[str, Any]:
        """
        Count what a reconcile pass would change for one program.

        Plan building is a read-only classification, so running it here as well as inside
        the importer costs a few queries and keeps the run summary honest.

        Two things keep the totals comparable between a dry run and an apply. An entity that
        has to be created also gets a link, so it counts towards both. And entities are
        returned by identity rather than counted, because one entity is commonly declared by
        several configs — `wa_211` by five — and a dry run classifies it as missing every
        time, having applied nothing in between. Deduplicating across the run is what makes
        `Entities to create` mean entities rather than declarations.
        """
        sections = tuple(s for s in RECONCILE_SECTIONS if s in (only or RECONCILE_SECTIONS))
        plan = ImportProgramConfigCommand()._build_reconcile_plan(program, config, sections)
        declarations = [(section, name, action) for section, items in plan.items() for name, action in items]

        return {
            "links_to_add": sum(1 for _, _, action in declarations if action != "linked"),
            "entities_to_create": {(section, name) for section, name, action in declarations if action == "create"},
            "changed": any(action != "linked" for _, _, action in declarations),
        }

    def _record_import(self, config_file: Path, result: dict[str, Any]) -> None:
        """
        Record a config as applied, stamping the content hash it was applied from.

        update_or_create rather than get_or_create so that re-applying an edited config
        refreshes the hash — otherwise the file would stay pending forever.
        """
        ProgramConfigImport.objects.update_or_create(
            filename=config_file.name,
            defaults={
                "program_name": result["program_name"],
                "white_label_code": result["white_label_code"],
                "content_hash": config_content_hash(config_file),
            },
        )

    def _display_final_summary(self, results: ImportResults, dry_run: bool = False) -> None:
        """Display a summary of the completed run."""
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS("Dry Run Complete" if dry_run else "Import Complete"))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}"))

        self.stdout.write(f"  {'Successful:':<17} {results.successful}")
        if results.reconcile:
            reconcile_label = "To reconcile:" if dry_run else "Reconciled:"
            self.stdout.write(f"  {reconcile_label:<17} {results.reconciled}")
            self.stdout.write(f"  {'Already current:':<17} {results.already_current}")
        self.stdout.write(f"  {'Skipped:':<17} {results.skipped}  (still pending — nothing was applied)")
        self.stdout.write(f"  {'Failed:':<17} {results.failed}")

        # Printed for every reconcile run, including one where everything skipped, so that the
        # two lines a production repair is gated on are never simply absent from the output.
        if results.reconcile:
            self.stdout.write("")
            self.stdout.write(f"  {'Links to add:':<20} {results.links_to_add}")
            create_line = f"  {'Entities to create:':<20} {len(results.entities_to_create)}"
            # An unexpected entity creation is the signal to stop and look before applying,
            # so it never gets to hide in a wall of green.
            self.stdout.write(self.style.WARNING(create_line) if results.entities_to_create else create_line)

        if results.partial_pass and (results.reconciled or results.already_current):
            self.stdout.write(
                self.style.WARNING(
                    "\n--only applies part of each config, so no config is recorded as imported. "
                    "The remaining sections need their own --reconcile run."
                )
            )

        if results.skipped:
            # The two modes skip for opposite reasons — a plain run skips programs that already
            # exist, a reconcile run skips programs that don't — so the remedy differs. Telling a
            # reconcile run to try --reconcile is circular, and it says so at the repair gate.
            if results.reconcile:
                remedy = (
                    "A reconcile pass only repairs programs that already exist. Run without "
                    "--reconcile to create the missing ones."
                )
            else:
                remedy = (
                    "Run with --reconcile to additively apply their warning messages, documents "
                    "and navigators to the existing programs."
                )
            self.stdout.write(self.style.WARNING(f"\nSkipped configs were not applied. {remedy}"))
        self.stdout.write("")

    def _show_status(self, json_files: list[Path], import_records: dict[str, str]) -> None:
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

            recorded = config_file.name in import_records
            pending = self._is_pending(config_file, import_records)

            if not pending:
                imported_count += 1
                record = ProgramConfigImport.objects.filter(filename=config_file.name).first()
                timestamp = record.imported_at.strftime("%Y-%m-%d %H:%M") if record else "unknown"
                self.stdout.write(self.style.SUCCESS(f"  ✓ {config_file.name}{program_desc}"))
                self.stdout.write(f"      Imported: {timestamp}")
            else:
                pending_count += 1
                self.stdout.write(self.style.WARNING(f"  ○ {config_file.name}{program_desc}"))
                if recorded:
                    self.stdout.write("      Status: pending (file edited since it was imported)")
                else:
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

    def _import_config(
        self,
        config_file: Path,
        reconcile: bool = False,
        only: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Import or reconcile a single configuration file.

        Returns a dict with:
            status: 'success', 'reconciled', 'skipped', or 'error'
            program_name: the program's name_abbreviated
            white_label_code: the white label code
            reason: why it was skipped, if status is 'skipped'
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
        except WhiteLabel.DoesNotExist:
            return {
                "status": "error",
                "error": f"WhiteLabel '{white_label_code}' not found",
                "program_name": program_name,
                "white_label_code": white_label_code,
            }

        if existing_program and not reconcile:
            return {
                "status": "skipped",
                "reason": f"program already exists (ID: {existing_program.id})",
                "program_name": program_name,
                "white_label_code": white_label_code,
            }

        if reconcile and not existing_program:
            # Reconcile repairs existing programs; it never creates one, so that a repair
            # run can't quietly introduce programs nobody asked for.
            return {
                "status": "skipped",
                "reason": "program does not exist yet — run without --reconcile to create it",
                "program_name": program_name,
                "white_label_code": white_label_code,
            }

        # Call the import_program_config command
        command_options: dict[str, Any] = {"stdout": self.stdout, "stderr": self.stderr}
        plan_totals: dict[str, Any] = {}
        if reconcile:
            command_options["reconcile"] = True
            command_options["dry_run"] = dry_run
            if only:
                command_options["only"] = list(only)
            # Build the same plan the importer will, so the run summary can report real
            # counts rather than treating every processed config as a change.
            plan_totals = self._summarize_reconcile_plan(existing_program, config, only)

        try:
            call_command("import_program_config", str(config_file), **command_options)
            return {
                "status": "reconciled" if reconcile else "success",
                "program_name": program_name,
                "white_label_code": white_label_code,
                **plan_totals,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "program_name": program_name,
                "white_label_code": white_label_code,
            }
