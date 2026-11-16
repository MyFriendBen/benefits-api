import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from programs.framework.gates import all_calculator_classes
from programs.management.commands._program_apply import ProgramApply, describe_changes, print_apply_plan
from programs.management.commands._program_payload import PayloadError, ProgramPayload, parse_payload
from programs.models import Program, ProgramImportLog
from screener.models import WhiteLabel


class DryRunRollback(Exception):
    """Raised at the end of a dry run to undo everything it applied."""


class Command(BaseCommand):
    help = """
    Apply one program's payload, rendered from its program-ops v2 spec.

    The payload is checked against a strict model before anything is written
    (`_program_payload.py`). Then:

    - the program is created, switched off, if it doesn't exist yet, once its calculator is
      registered (a payload with `has_calculator: false` doesn't wait for one);
    - the program row and its English text are written to match the payload, and the other
      languages are re-translated unless someone edited them by hand;
    - navigators, documents and warning messages are created when missing and otherwise left as
      they are, then linked to the program. Nothing is unlinked.

    `active` is never changed. Every apply writes a `ProgramImportLog` row. Programs still on a v1
    spec keep using `import_program_records`.

    A dry run applies everything inside a transaction and rolls it back, so it reports exactly
    what a real run would. It copies English into every language rather than calling the
    translation API.

    Usage:
      python manage.py apply_program --file payload.json --dry-run
      python manage.py apply_program --source <spec path> --spec-commit <sha> < payload.json
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--file", type=Path, help="Read the payload from this file instead of stdin.")
        parser.add_argument("--dry-run", action="store_true", help="Report what would change, and change nothing.")
        parser.add_argument(
            "--skip-translation",
            action="store_true",
            help="Copy English to every language instead of machine-translating it.",
        )
        parser.add_argument("--source", default="", help="The spec the payload was rendered from, for the log.")
        parser.add_argument("--spec-commit", default="", help="The program-ops commit of that spec, for the log.")

    def handle(self, *args: Any, **options: Any) -> None:
        data = self._read(options.get("file"))
        try:
            payload = parse_payload(data)
        except PayloadError as e:
            raise CommandError("The payload can't be applied:\n  - " + "\n  - ".join(e.problems)) from None

        dry_run = bool(options.get("dry_run"))
        label = f"{payload.white_label}/{payload.program.name_abbreviated}"
        self.stdout.write(f"\n{label}" + (" — DRY RUN" if dry_run else ""))

        try:
            with transaction.atomic():
                self._apply(payload, data, options, dry_run)
                if dry_run:
                    raise DryRunRollback
        except DryRunRollback:
            self.stdout.write(self.style.SUCCESS("Dry run complete — nothing changed."))
            return
        self.stdout.write(self.style.SUCCESS("Applied."))

    def _read(self, path: Optional[Path]) -> Any:
        try:
            text = path.read_text(encoding="utf-8") if path else sys.stdin.read()
        except OSError as e:
            raise CommandError(f"Can't read the payload: {e}") from None
        try:
            return json.loads(text)
        except ValueError as e:
            raise CommandError(f"The payload isn't valid JSON: {e}") from None

    def _apply(self, payload: ProgramPayload, data: dict[str, Any], options: dict[str, Any], dry_run: bool) -> None:
        if not WhiteLabel.objects.filter(code=payload.white_label).exists():
            raise CommandError(f"No white label '{payload.white_label}'.")

        record = payload.as_record()
        sync = ProgramApply(record, self.stdout, skip_translation=bool(options.get("skip_translation")) or dry_run)
        program = Program.objects.filter(
            white_label__code=payload.white_label, name_abbreviated=payload.program.name_abbreviated
        ).first()
        if program is None:
            self._check_calculator(payload)
            program = sync.create_program()
            self.stdout.write("  New program, created switched off.")

        plan = sync.plan(program)
        print_apply_plan(plan, self.stdout, dry_run=dry_run)
        sync.apply(plan)
        ProgramImportLog.objects.create(
            program=program,
            white_label_code=payload.white_label,
            program_name=payload.program.name_abbreviated,
            payload=data,
            changes=describe_changes(plan),
            source=options.get("source") or "",
            spec_commit=options.get("spec_commit") or "",
        )

    def _check_calculator(self, payload: ProgramPayload) -> None:
        """A new program waits for its calculator, so nothing is created that can't be calculated."""
        key = payload.program.name_abbreviated
        if payload.program.has_calculator and key not in all_calculator_classes():
            raise CommandError(
                f"'{key}' has no registered calculator yet, so it wasn't created. Apply it once its calculator "
                f"has deployed to this environment."
            )
