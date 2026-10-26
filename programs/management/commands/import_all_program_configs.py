import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from programs.framework.gates import all_calculator_classes
from programs.management.commands._program_record_sync import (
    ADMIN_EDIT,
    CONFLICT,
    RecordSync,
    owned_rows,
    print_plan,
    validate_record,
)
from programs.models import Program, ProgramConfigImport


def config_content_hash(config_file: Path) -> str:
    """
    Return the SHA-256 of a record file's raw bytes.

    Stored with the tracking row as a record of exactly what was applied. Migration 0166
    duplicates this to backfill existing rows.
    """
    return hashlib.sha256(config_file.read_bytes()).hexdigest()


class DryRunRollback(Exception):
    """Raised at the end of a dry run to undo everything it applied."""


@dataclass
class ImportResults:
    created: int = 0
    updated: int = 0
    current: int = 0
    waiting: int = 0
    admin_edits_kept: int = 0
    conflicts: int = 0
    # (file name, reason) for every record that failed, repeated at the end of the run.
    failures: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class LoadedRecord:
    path: Path
    record: dict[str, Any]
    program: Optional[Program] = None
    fresh: bool = False


class Command(BaseCommand):
    help = """
    Bring every program in line with its program-ops record.

    program-ops is the source of truth for programs. Each run reads every
    `programs/**/*_program_record.json` in a program-ops checkout and compares each record with
    the database (see _program_record_sync):

    - a program that doesn't exist is created, switched off, once its calculator is registered
      (a record with `has_calculator: false` doesn't wait for one);
    - a difference the record made is applied;
    - a difference made in the admin is reported and kept, unless --revert-admin-edits;
    - a field changed on both sides is a conflict and is skipped.

    `active` is never changed: switching a program on is a release decision, made per environment
    in the admin. benefits-api's own config files under import_program_config_data/data/ are no
    longer read.

    A dry run applies everything inside a transaction and rolls it back, so it reports exactly
    what a real run would, failures included. It copies English into every language rather than
    calling the translation API.

    Usage:
      python manage.py import_all_program_configs --dry-run
      python manage.py import_all_program_configs
      python manage.py import_all_program_configs --list
      python manage.py import_all_program_configs --file co_nf_program_record.json
      python manage.py import_all_program_configs --program-ops-stdin < bundle.json
    """

    # A program-ops checkout next to this repo.
    PROGRAM_OPS_DIR = Path(settings.BASE_DIR).parent / "program-ops"
    PROGRAM_OPS_RECORD_GLOB = "programs/**/*_program_record.json"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Report what would change, and change nothing.")
        parser.add_argument(
            "--list", action="store_true", dest="list_status", help="List every record and when it was last applied."
        )
        parser.add_argument("--file", dest="single_file", help="Only this record, by file name.")
        parser.add_argument(
            "--program-ops-dir",
            type=Path,
            help=f"Path to a program-ops checkout. Defaults to {self.PROGRAM_OPS_DIR}.",
        )
        parser.add_argument(
            "--program-ops-stdin",
            action="store_true",
            help='Read records from stdin, as {"files": {"programs/.../x_program_record.json": "<text>"}}. '
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
        if options.get("program_ops_dir") and options.get("program_ops_stdin"):
            raise CommandError("Use --program-ops-dir or --program-ops-stdin, not both.")

        self._bundle_dir: Optional[Path] = None
        if options.get("program_ops_stdin"):
            program_ops_dir = self._unpack_record_bundle(sys.stdin.read())
        else:
            program_ops_dir = options.get("program_ops_dir") or self.PROGRAM_OPS_DIR
            if not program_ops_dir.is_dir():
                raise CommandError(
                    f"No program-ops checkout at {program_ops_dir}. Program records live in program-ops; "
                    f"pass --program-ops-dir or --program-ops-stdin."
                )

        try:
            self._run(program_ops_dir, options)
        finally:
            if self._bundle_dir is not None:
                shutil.rmtree(self._bundle_dir, ignore_errors=True)

    def _run(self, program_ops_dir: Path, options: dict[str, Any]) -> None:
        self.dry_run = bool(options.get("dry_run"))
        self.revert_admin_edits = bool(options.get("revert_admin_edits"))
        self.skip_translation = bool(options.get("skip_translation")) or self.dry_run

        record_files = sorted(program_ops_dir.glob(self.PROGRAM_OPS_RECORD_GLOB))
        if not record_files:
            raise CommandError(f"No program records under {program_ops_dir}.")
        self._check_for_duplicates(record_files)
        self._check_for_shared_owners(record_files)

        single_file = options.get("single_file")
        if single_file:
            record_files = [f for f in record_files if f.name == single_file]
            if not record_files:
                raise CommandError(f"No record named {single_file}.")

        if options.get("list_status"):
            return self._show_status(record_files)

        results = ImportResults()
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(f"program-ops records ({len(record_files)})" + (" — DRY RUN" if self.dry_run else ""))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}"))

        if self.dry_run:
            try:
                with transaction.atomic():
                    self._sync(record_files, results)
                    raise DryRunRollback
            except DryRunRollback:
                pass
        else:
            self._sync(record_files, results)
        self._display_summary(results)

    # ------------------------------------------------------------------ discovery

    def _check_for_duplicates(self, record_files: list[Path]) -> None:
        """Raise if two records share a file name or declare the same program."""
        by_name: dict[str, Path] = {}
        by_program: dict[tuple[str, str], Path] = {}
        for record_file in record_files:
            if record_file.name in by_name:
                raise CommandError(
                    f"Two records are named {record_file.name}: {by_name[record_file.name]} and {record_file}."
                )
            by_name[record_file.name] = record_file

            program = self._program_key(record_file)
            if program is None:
                continue
            if program in by_program:
                raise CommandError(
                    f"{program[0]}/{program[1]} is declared twice: {by_program[program]} and {record_file}."
                )
            by_program[program] = record_file

    def _check_for_shared_owners(self, record_files: list[Path]) -> None:
        """
        Raise if two records own the same navigator, document or warning message.

        A full entry rewrites the row it names. Two records doing that for one row would each
        overwrite the other on every run, and the row would end up with whichever ran last.
        """
        owners: dict[tuple[str, str], Path] = {}
        for record_file in record_files:
            record = self._read(record_file)
            if not isinstance(record, dict):
                continue  # reported when the record itself is processed
            for row in owned_rows(record):
                if row in owners:
                    raise CommandError(
                        f"{row[0]} '{row[1]}' is fully described by two records: {owners[row]} and {record_file}. "
                        f"Keep the fields in one and list only its external_name in the other."
                    )
                owners[row] = record_file

    def _program_key(self, record_file: Path) -> Optional[tuple[str, str]]:
        """Return (white label, program key) for a record, or None if it can't be read."""
        record = self._read(record_file)
        try:
            return (record["white_label"]["code"], record["program"]["name_abbreviated"])
        except (KeyError, TypeError):
            return None

    def _read(self, record_file: Path) -> Any:
        """A record's JSON, or None if it can't be opened or parsed (reported when it's processed)."""
        try:
            return json.loads(record_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

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

    # ------------------------------------------------------------------ syncing

    def _sync(self, record_files: list[Path], results: ImportResults) -> None:
        """
        Create the programs that don't exist yet, then bring every program in line with its record.

        Every new program is created before any record is applied, so a record naming another
        record's program in `required_programs` or `eligibility_programs` resolves whichever
        order they're read in.
        """
        loaded = self._load(record_files, results)
        calculators = all_calculator_classes()

        waiting = []
        to_sync = []
        for item in loaded:
            item.program = Program.objects.filter(
                white_label__code=item.record["white_label"]["code"],
                name_abbreviated=item.record["program"]["name_abbreviated"],
            ).first()
            if item.program is None:
                needs_calculator = item.record["program"].get("has_calculator", True)
                if needs_calculator and item.record["program"]["name_abbreviated"] not in calculators:
                    # A record is often written before its calculator merges. Creating it now
                    # would leave a program nothing can calculate, so it waits.
                    waiting.append(item.path.name)
                    continue
                try:
                    item.program = RecordSync(item.record, self.stdout).create_program()
                except Exception as e:
                    self._failed(results, item.path, f"couldn't create the program: {e}")
                    continue
                item.fresh = True
            to_sync.append(item)

        if waiting:
            results.waiting = len(waiting)
            self.stdout.write(f"\nWaiting for a calculator, not created: {', '.join(waiting)}")

        baselines = dict(
            ProgramConfigImport.objects.filter(filename__in=[item.path.name for item in to_sync]).values_list(
                "filename", "applied_record"
            )
        )
        for item in to_sync:
            self._sync_one(item, baselines.get(item.path.name), results)

    def _load(self, record_files: list[Path], results: ImportResults) -> list[LoadedRecord]:
        loaded = []
        for record_file in record_files:
            try:
                record = json.loads(record_file.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                self._failed(results, record_file, f"can't be read: {e}")
                continue
            problems = validate_record(record)
            if problems:
                self._failed(results, record_file, "; ".join(problems))
                continue
            loaded.append(LoadedRecord(path=record_file, record=record))
        return loaded

    def _sync_one(self, item: LoadedRecord, baseline: Optional[dict[str, Any]], results: ImportResults) -> None:
        program = item.program
        assert program is not None
        label = f"{program.white_label.code}/{program.name_abbreviated}" + (", new" if item.fresh else "")
        self.stdout.write(f"\n{item.path.name} ({label})")
        try:
            # One savepoint per record: a failure undoes that record alone.
            with transaction.atomic():
                sync = RecordSync(item.record, self.stdout, skip_translation=self.skip_translation)
                plan = sync.plan(program, None if item.fresh else baseline, fresh=item.fresh)
                print_plan(plan, self.stdout, self.revert_admin_edits, dry_run=self.dry_run)
                sync.apply(plan, revert_admin_edits=self.revert_admin_edits)
                self._record_import(item.path, program, plan.next_baseline())
        except Exception as e:
            if item.fresh:
                # Don't leave a half-built program behind: the next run would see an existing
                # program with no baseline and report the record's own fields as admin edits.
                program.delete()
            self._failed(results, item.path, str(e))
            return

        if item.fresh:
            results.created += 1
        elif plan.to_apply(self.revert_admin_edits):
            results.updated += 1
        elif not plan.changes:
            results.current += 1
        if not self.revert_admin_edits:
            results.admin_edits_kept += len(plan.by_label(ADMIN_EDIT))
        results.conflicts += len(plan.by_label(CONFLICT))

    def _record_import(self, record_file: Path, program: Program, applied_record: dict[str, Any]) -> None:
        """Store what was applied: the baseline the next run labels differences against."""
        ProgramConfigImport.objects.update_or_create(
            filename=record_file.name,
            defaults={
                "program_name": program.name_abbreviated,
                "white_label_code": program.white_label.code,
                "content_hash": config_content_hash(record_file),
                "applied_record": applied_record,
            },
        )

    def _failed(self, results: ImportResults, record_file: Path, error: str) -> None:
        results.failures.append((record_file.name, error))
        self.stdout.write(self.style.ERROR(f"✗ Failed: {record_file.name} - {error}"))

    # ------------------------------------------------------------------ output

    def _display_summary(self, results: ImportResults) -> None:
        created = "To create:" if self.dry_run else "Created:"
        updated = "To update:" if self.dry_run else "Updated:"
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(
            self.style.SUCCESS("Dry Run Complete — nothing changed" if self.dry_run else "Import Complete")
        )
        self.stdout.write(self.style.WARNING(f"{'=' * 60}"))
        self.stdout.write(f"  {created:<20} {results.created}")
        self.stdout.write(f"  {updated:<20} {results.updated}")
        self.stdout.write(f"  {'Current:':<20} {results.current}")
        self.stdout.write(f"  {'Waiting:':<20} {results.waiting}  (no calculator yet)")
        kept = f"  {'Admin edits kept:':<20} {results.admin_edits_kept}"
        self.stdout.write(self.style.WARNING(kept) if results.admin_edits_kept else kept)
        conflicts = f"  {'Conflicts:':<20} {results.conflicts}"
        self.stdout.write(self.style.ERROR(conflicts) if results.conflicts else conflicts)
        self.stdout.write(f"  {'Failed:':<20} {len(results.failures)}")

        if results.failures:
            # Repeated here, last, so a failure can't scroll away above a long run's output.
            self.stdout.write(
                self.style.ERROR(f"\n✗ {len(results.failures)} record(s) need fixing before they import:")
            )
            for name, error in results.failures:
                self.stdout.write(self.style.ERROR(f"  ✗ {name}: {error}"))
        self.stdout.write("")

    def _show_status(self, record_files: list[Path]) -> None:
        applied = {
            row.filename: row for row in ProgramConfigImport.objects.filter(filename__in=[f.name for f in record_files])
        }
        self.stdout.write(f"\n{len(record_files)} record(s)\n")
        for record_file in record_files:
            row = applied.get(record_file.name)
            if row is None:
                self.stdout.write(self.style.WARNING(f"  ○ {record_file.name}: never applied"))
            else:
                stamp = row.imported_at.strftime("%Y-%m-%d %H:%M")
                changed = " (file changed since)" if row.content_hash != config_content_hash(record_file) else ""
                self.stdout.write(self.style.SUCCESS(f"  ✓ {record_file.name}: applied {stamp}{changed}"))
