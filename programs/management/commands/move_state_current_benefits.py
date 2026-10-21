"""Move "already has" rows from retired state program rows onto a federal program.

The data migration that ships with a federal move does this when it runs, but only if the
federal row already exists. An environment that deployed before importing the program
record is left with the rows on the state programs; this command finishes the move once
the federal row is there.

    python manage.py move_state_current_benefits federal_ctc
    python manage.py move_state_current_benefits federal_ctc --from co:ctc --from tx:tx_ctc

Idempotent: a second run finds nothing to move.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from programs.current_benefits_moves import FEDERAL_WHITE_LABEL, STATE_ROWS_BY_FEDERAL_PROGRAM, move_current_benefits
from programs.models import Program
from screener.models import CurrentBenefit, WhiteLabel


class Command(BaseCommand):
    help = "Repoint CurrentBenefit rows on retired state program rows at their federal replacement."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "federal_program",
            help="name_abbreviated of the federal program the rows move to, e.g. federal_ctc.",
        )
        parser.add_argument(
            "--from",
            dest="state_rows",
            action="append",
            metavar="WHITE_LABEL:NAME",
            help=(
                "A state row to move from, as <white label code>:<name_abbreviated>. Repeatable. "
                "Defaults to the rows recorded for the federal program."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        federal_program: str = options["federal_program"]
        state_rows = self._state_rows(federal_program, options.get("state_rows"))

        self.stdout.write(f"Moving current benefits onto federal/{federal_program}:")
        result = move_current_benefits(
            Program, WhiteLabel, CurrentBenefit, federal_program, state_rows, out=self.stdout.write
        )
        if not result.federal_found:
            raise CommandError(f"federal/{federal_program} does not exist; import the program record first.")

    @staticmethod
    def _state_rows(federal_program: str, given: list[str] | None) -> tuple[tuple[str, str], ...]:
        if given:
            rows = []
            for item in given:
                white_label, sep, name = item.partition(":")
                if not sep or not white_label or not name:
                    raise CommandError(f"--from expects <white label code>:<name_abbreviated>, got {item!r}")
                if white_label == FEDERAL_WHITE_LABEL:
                    raise CommandError(
                        f"--from {item!r} names the federal white label; rows move onto a federal program, not from one."
                    )
                rows.append((white_label, name))
            return tuple(rows)

        if federal_program not in STATE_ROWS_BY_FEDERAL_PROGRAM:
            raise CommandError(
                f"No state rows are recorded for {federal_program}; pass them with --from <white label>:<name>."
            )
        return STATE_ROWS_BY_FEDERAL_PROGRAM[federal_program]
