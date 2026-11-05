import argparse
import json
import sys
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError

from programs.management.commands._program_record_sync import record_from_database
from programs.models import Program

BEGIN_MARKER = "----- BEGIN PROGRAM RECORD -----"
END_MARKER = "----- END PROGRAM RECORD -----"


class Command(BaseCommand):
    help = """
    Print a program's current state as a program-ops record.

    This is how an edit made in the admin gets back into program-ops: export the program, and
    the record file picks up what the database holds. Pass the current record with --record so the
    export keeps its references, optional keys and ordering; applying the result changes nothing.

    The record is printed between marker lines, so a caller reading `heroku run` output can find it.

    Usage:
      python manage.py export_program_record co co_nf
      python manage.py export_program_record co co_nf --record - < co_nf_program_record.json
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("white_label", help="The program's white label code, e.g. co")
        parser.add_argument("program", help="The program's name_abbreviated, e.g. co_nf")
        parser.add_argument(
            "--record",
            help="The program's current record file, or - to read it from stdin. Keeps its shape in the export.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        program = (
            Program.objects.filter(white_label__code=options["white_label"], name_abbreviated=options["program"])
            .select_related("white_label", "category", "year")
            .first()
        )
        if program is None:
            raise CommandError(f"No program '{options['program']}' in white label '{options['white_label']}'.")

        record = record_from_database(program, self._existing_record(options.get("record")))
        self.stdout.write(BEGIN_MARKER)
        self.stdout.write(json.dumps(record, indent=2, ensure_ascii=False))
        self.stdout.write(END_MARKER)

    def _existing_record(self, source: Optional[str]) -> Optional[dict[str, Any]]:
        if not source:
            return None
        try:
            text = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
            record = json.loads(text)
        except (OSError, ValueError) as e:
            raise CommandError(f"Can't read the record: {e}") from None
        if not isinstance(record, dict):
            raise CommandError("The record isn't a JSON object.")
        return record
