from dataclasses import dataclass, field

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from programs.framework.gates import all_calculator_classes
from programs.management.commands.import_program_config import (
    RECONCILE_SECTIONS,
    Command as ImportProgramConfigCommand,
)
from programs.management.commands._program_record_sync import (
    ADMIN_EDIT,
    CONFLICT,
    RecordSync,
    owned_rows,
    print_plan,
    validate_record,
)
from programs.models import ProgramConfigImport, Program
from screener.models import WhiteLabel
from pathlib import Path, PurePosixPath
from typing import Any, Optional
import argparse
import hashlib
import json
import shutil
import sys
import tempfile


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
    # program-ops records, which are compared with the database on every run.
    records_updated: int = 0
    records_current: int = 0
    admin_edits_kept: int = 0
    conflicts: int = 0
    # (file name, reason) for every config that failed, repeated at the end of the run.
    failures: list[tuple[str, str]] = field(default_factory=list)


class Command(BaseCommand):
    help = """
    Import all program configurations that haven't been imported yet.

    This command scans the import_program_config_data/data/ directory for JSON
    configuration files, plus the program records in a program-ops checkout, and
    imports any that haven't already been processed. It works similar to Django
    migrations - tracking which imports have been run.

    program-ops is the source of truth for the programs it holds a record for, so a
    data directory config for one of them is ignored with a warning. A record is only picked up once
    its program has a registered calculator. Without a program-ops checkout the
    command reads the data directory alone.

    A program-ops record creates its program and, after that, keeps it matching: every run
    compares every record with the database (see _program_record_sync). Differences the record
    made are applied; edits made in the admin are reported and kept unless --revert-admin-edits
    is given; a field changed on both sides is a conflict and is skipped. A data directory config
    only ever creates its program.

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
      --program-ops-dir  Read program records from this program-ops checkout
      --program-ops-stdin  Read program records from a JSON bundle on stdin (for heroku run)
      --revert-admin-edits  Set fields edited in the admin back to what the record says

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

    # A program-ops checkout next to this repo, where the program records it holds live.
    PROGRAM_OPS_DIR = Path(settings.BASE_DIR).parent / "program-ops"
    PROGRAM_OPS_RECORD_GLOB = "programs/**/*_program_record.json"

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
        parser.add_argument(
            "--program-ops-dir",
            type=Path,
            help=f"Path to a program-ops checkout to read program records from. Defaults to {self.PROGRAM_OPS_DIR}.",
        )
        parser.add_argument(
            "--program-ops-stdin",
            action="store_true",
            help='Read program records from stdin, as {"files": {"programs/.../x_program_record.json": "<text>"}}. '
            "This is how program-ops' import script sends its records to a one-off dyno.",
        )
        parser.add_argument(
            "--revert-admin-edits",
            action="store_true",
            help="Apply the record over fields that were edited in the admin. Without it they are reported and kept.",
        )
        parser.add_argument(
            "--skip-translation",
            action="store_true",
            help="Copy English to every language instead of machine-translating it.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Orchestrates the import process based on command options."""
        if not self._validate_data_directory():
            return

        program_ops_dir = options.get("program_ops_dir")
        if program_ops_dir and options.get("program_ops_stdin"):
            raise CommandError("Use --program-ops-dir or --program-ops-stdin, not both.")
        self._bundle_dir: Optional[Path] = None
        if options.get("program_ops_stdin"):
            program_ops_dir = self._unpack_record_bundle(sys.stdin.read())
        elif program_ops_dir and not program_ops_dir.is_dir():
            raise CommandError(f"No program-ops checkout at {program_ops_dir}.")

        try:
            self._run(program_ops_dir, options)
        finally:
            if self._bundle_dir is not None:
                shutil.rmtree(self._bundle_dir, ignore_errors=True)

    def _run(self, program_ops_dir: Optional[Path], options: dict[str, Any]) -> None:
        self.revert_admin_edits = bool(options.get("revert_admin_edits"))
        self.skip_translation = bool(options.get("skip_translation"))
        self.record_files: set[Path] = set()
        json_files = self._discover_config_files(program_ops_dir or self.PROGRAM_OPS_DIR)
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

        record_files = [f for f in target_files if f in self.record_files]
        data_files = [f for f in target_files if f not in self.record_files]

        # A reconcile dry run has to invoke the importer to report what it would change,
        # so it goes through the normal execution path rather than the file listing.
        if dry_run and not reconcile:
            if data_files:
                self._handle_dry_run(data_files)
            if not record_files:
                return
            results = ImportResults()
        elif data_files:
            results = self._execute_imports(data_files, reconcile=reconcile, only=only, dry_run=dry_run)
        else:
            results = ImportResults(reconcile=reconcile)

        if record_files:
            self._sync_records(record_files, results, dry_run=dry_run)
        self._display_final_summary(results, dry_run=dry_run)

    def _validate_data_directory(self) -> bool:
        """Return False and write an error if the data directory doesn't exist."""
        if not self.DATA_DIR.exists():
            self.stderr.write(self.style.ERROR(f"Data directory not found: {self.DATA_DIR}"))
            return False
        return True

    def _discover_config_files(self, program_ops_dir: Path) -> list[Path]:
        """
        Return the data directory's config files followed by the importable program-ops records.

        A data directory config for a program that program-ops also holds is dropped with a
        warning: the record is the source of truth, and a stale copy shouldn't block every
        developer's import until it's deleted. Every record counts, including one still waiting
        for its calculator. Raises if a filename repeats, since tracking rows are keyed by
        filename, or if two records declare one program, since neither can win.
        """
        records = self._find_program_ops_records(program_ops_dir)
        data_files = self._drop_data_copies(sorted(self.DATA_DIR.glob("*.json")), records)
        self._check_for_duplicates(data_files + records)
        self._check_for_shared_owners(records)
        importable = self._importable_records(records)
        self.record_files = set(importable)
        return data_files + importable

    def _drop_data_copies(self, data_files: list[Path], records: list[Path]) -> list[Path]:
        """Return the data directory configs whose program has no program-ops record."""
        recorded = {self._program_key(record): record for record in records}
        kept: list[Path] = []
        for data_file in data_files:
            record = recorded.get(self._program_key(data_file))
            if record:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ignoring {data_file.name}: program-ops holds this program in {record}. "
                        f"Delete the data directory copy."
                    )
                )
            else:
                kept.append(data_file)
        return kept

    def _program_key(self, config_file: Path) -> tuple[str, str] | None:
        """Return (white label, program) for a config, or None if either can't be read."""
        program_info = self._get_program_info(config_file)
        if not program_info or "unknown" in program_info.values():
            return None
        return (program_info["white_label"], program_info["program_name"])

    def _find_program_ops_records(self, program_ops_dir: Path) -> list[Path]:
        """Return every program record in the program-ops checkout, or none without one."""
        if not program_ops_dir.is_dir():
            self.stdout.write(
                self.style.WARNING(f"No program-ops checkout at {program_ops_dir}; reading the data directory only.")
            )
            return []
        return sorted(program_ops_dir.glob(self.PROGRAM_OPS_RECORD_GLOB))

    def _importable_records(self, records: list[Path]) -> list[Path]:
        """
        Return the records whose program has a registered calculator.

        A record is often written before its calculator merges. Importing it then would create
        a row nothing can calculate, so it waits until the calculator ships. A record whose
        program can't be read is kept, so the import reports it rather than it vanishing.
        """
        calculators = all_calculator_classes()
        importable: list[Path] = []
        waiting: list[str] = []
        for record in records:
            program_name = (self._get_program_info(record) or {}).get("program_name", "unknown")
            if program_name != "unknown" and program_name not in calculators:
                waiting.append(record.name)
            else:
                importable.append(record)

        if waiting:
            self.stdout.write(f"Waiting for a calculator, not imported: {', '.join(waiting)}")
        return importable

    def _check_for_duplicates(self, config_files: list[Path]) -> None:
        """Raise if two config files share a filename or declare the same program."""
        by_filename: dict[str, Path] = {}
        by_program: dict[tuple[str, str], Path] = {}
        for config_file in config_files:
            if config_file.name in by_filename:
                raise CommandError(
                    f"Two config files are named {config_file.name}: {by_filename[config_file.name]} and {config_file}."
                )
            by_filename[config_file.name] = config_file

            program = self._program_key(config_file)
            if program is None:
                continue
            if program in by_program:
                raise CommandError(
                    f"{program[0]}/{program[1]} is declared twice: {by_program[program]} and {config_file}."
                )
            by_program[program] = config_file

    def _check_for_shared_owners(self, records: list[Path]) -> None:
        """
        Raise if two records own the same navigator, document or warning message.

        A full entry rewrites the row it names. Two records doing that for one row would each
        overwrite the other on every run, and the row would end up with whichever ran last.
        """
        owners: dict[tuple[str, str], Path] = {}
        for record_file in records:
            try:
                record = json.loads(record_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # reported when the record itself is processed
            if not isinstance(record, dict):
                continue
            for row in owned_rows(record):
                if row in owners:
                    raise CommandError(
                        f"{row[0]} '{row[1]}' is fully described by two records: {owners[row]} and {record_file}. "
                        f"Keep the fields in one and list only its external_name in the other."
                    )
                owners[row] = record_file

    def _unpack_record_bundle(self, bundle_text: str) -> Path:
        """
        Write a stdin bundle of program-ops records into a temporary checkout and return it.

        Only `programs/**/*_program_record.json` paths are accepted, so the bundle can't write
        anywhere else on the dyno.
        """
        try:
            files = json.loads(bundle_text)["files"]
        except (ValueError, KeyError, TypeError) as e:
            raise CommandError(f"--program-ops-stdin needs a JSON bundle with a 'files' object: {e}") from None
        if not isinstance(files, dict) or not files:
            raise CommandError("--program-ops-stdin bundle has no files.")

        for relative, text in files.items():
            path = PurePosixPath(relative)
            if (
                path.is_absolute()
                or ".." in path.parts
                or path.parts[:1] != ("programs",)
                or not path.name.endswith("_program_record.json")
                or not isinstance(text, str)
            ):
                raise CommandError(f"--program-ops-stdin bundle has an unexpected entry: {relative!r}")

        root = Path(tempfile.mkdtemp(prefix="program-ops-"))
        self._bundle_dir = root
        for relative, text in files.items():
            target = root.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        return root

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

        # A record is compared with the database on every run, since an admin edit doesn't
        # change the file and so never makes it pending.
        return [f for f in json_files if f in self.record_files or self._is_pending(f, import_records)]

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
                    results.failures.append((config_file.name, result.get("error", "Unknown error")))
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed: {config_file.name} - {result.get('error', 'Unknown error')}")
                    )
            except Exception as e:
                results.failed += 1
                results.failures.append((config_file.name, str(e)))
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

    def _record_import(
        self, config_file: Path, result: dict[str, Any], applied_record: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Record a config as applied, stamping the content hash it was applied from.

        update_or_create rather than get_or_create so that re-applying an edited config
        refreshes the hash — otherwise the file would stay pending forever. A program-ops
        record also stores what it set, the baseline the next run compares against.
        """
        defaults: dict[str, Any] = {
            "program_name": result["program_name"],
            "white_label_code": result["white_label_code"],
            "content_hash": config_content_hash(config_file),
        }
        if applied_record is not None:
            defaults["applied_record"] = applied_record
        ProgramConfigImport.objects.update_or_create(filename=config_file.name, defaults=defaults)

    def _sync_records(self, record_files: list[Path], results: ImportResults, dry_run: bool) -> None:
        """
        Create each record's program if it's missing, then bring every program in line with its record.

        Programs are created first, all of them, so a record naming another record's program in
        `required_programs` or `eligibility_programs` resolves whichever order they're read in.
        """
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(f"program-ops records ({len(record_files)})" + (" — DRY RUN" if dry_run else ""))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}"))

        loaded: list[tuple[Path, dict[str, Any]]] = []
        for record_file in record_files:
            try:
                record = json.loads(record_file.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                self._record_failed(results, record_file, f"can't be read: {e}")
                continue
            problems = validate_record(record)
            if problems:
                self._record_failed(results, record_file, "; ".join(problems))
                continue
            loaded.append((record_file, record))

        to_sync: list[tuple[Path, dict[str, Any], Program, bool]] = []
        for record_file, record in loaded:
            program = Program.objects.filter(
                white_label__code=record["white_label"]["code"],
                name_abbreviated=record["program"]["name_abbreviated"],
            ).first()
            if program is not None:
                to_sync.append((record_file, record, program, False))
                continue

            self.stdout.write(f"\n{record_file.name}: program doesn't exist yet, creating it")
            if dry_run:
                try:
                    call_command(
                        "import_program_config", str(record_file), dry_run=True, stdout=self.stdout, stderr=self.stderr
                    )
                    results.successful += 1
                except Exception as e:
                    self._record_failed(results, record_file, str(e))
                continue
            result = self._import_config(record_file, skip_translation=self.skip_translation)
            if result["status"] != "success":
                self._record_failed(results, record_file, result.get("error", result.get("reason", "not created")))
                continue
            results.successful += 1
            program = Program.objects.get(
                white_label__code=record["white_label"]["code"],
                name_abbreviated=record["program"]["name_abbreviated"],
            )
            to_sync.append((record_file, record, program, True))

        baselines = dict(
            ProgramConfigImport.objects.filter(filename__in=[f.name for f, *_ in to_sync]).values_list(
                "filename", "applied_record"
            )
        )
        for record_file, record, program, fresh in to_sync:
            self.stdout.write(f"\n{record_file.name} ({program.white_label.code}/{program.name_abbreviated})")
            try:
                sync = RecordSync(record, self.stdout, skip_translation=self.skip_translation)
                plan = sync.plan(program, baselines.get(record_file.name), fresh=fresh)
                print_plan(plan, self.stdout, self.revert_admin_edits, dry_run=dry_run)
                if not dry_run:
                    sync.apply(plan, revert_admin_edits=self.revert_admin_edits)
                    self._record_import(
                        record_file,
                        {"program_name": program.name_abbreviated, "white_label_code": program.white_label.code},
                        applied_record=plan.next_baseline(),
                    )
            except Exception as e:
                self._record_failed(results, record_file, str(e))
                continue

            if fresh:
                continue
            if plan.to_apply(self.revert_admin_edits):
                results.records_updated += 1
            elif not plan.changes:
                results.records_current += 1
            if not self.revert_admin_edits:
                results.admin_edits_kept += len(plan.by_label(ADMIN_EDIT))
            results.conflicts += len(plan.by_label(CONFLICT))

    def _record_failed(self, results: ImportResults, record_file: Path, error: str) -> None:
        results.failed += 1
        results.failures.append((record_file.name, error))
        self.stdout.write(self.style.ERROR(f"✗ Failed: {record_file.name} - {error}"))

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
        if self.record_files:
            updated_label = "Records to update:" if dry_run else "Records updated:"
            self.stdout.write(f"  {updated_label:<20} {results.records_updated}")
            self.stdout.write(f"  {'Records current:':<20} {results.records_current}")
            kept = f"  {'Admin edits kept:':<20} {results.admin_edits_kept}"
            self.stdout.write(self.style.WARNING(kept) if results.admin_edits_kept else kept)
            conflicts = f"  {'Conflicts:':<20} {results.conflicts}"
            self.stdout.write(self.style.ERROR(conflicts) if results.conflicts else conflicts)

        # Printed for every reconcile run, including one where everything skipped, so that the
        # two lines a production repair is gated on are never simply absent from the output.
        if results.reconcile:
            self.stdout.write("")
            self.stdout.write(f"  {'Links to add:':<20} {results.links_to_add}")
            create_line = f"  {'Entities to create:':<20} {len(results.entities_to_create)}"
            # An unexpected entity creation is the signal to stop and look before applying,
            # so it never gets to hide in a wall of green.
            self.stdout.write(self.style.WARNING(create_line) if results.entities_to_create else create_line)

        if results.failures:
            # Repeated here, last, so a failure can't scroll away above a long run's output.
            self.stdout.write(
                self.style.ERROR(f"\n✗ {len(results.failures)} config(s) need fixing before they import:")
            )
            for name, error in results.failures:
                self.stdout.write(self.style.ERROR(f"  ✗ {name}: {error}"))

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
        """
        Extract program info from a config file, or None if it can't be read.

        Never raises: a file that can't be opened or decoded is left for the import itself to
        report as failed, so one bad file doesn't stop every other config. ValueError covers
        both invalid JSON and bytes that aren't UTF-8.
        """
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return {
                    "white_label": config.get("white_label", {}).get("code", "unknown"),
                    "program_name": config.get("program", {}).get("name_abbreviated", "unknown"),
                }
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def _import_config(
        self,
        config_file: Path,
        reconcile: bool = False,
        only: list[str] | None = None,
        dry_run: bool = False,
        skip_translation: bool = False,
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
        if skip_translation:
            command_options["skip_translation"] = True
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
